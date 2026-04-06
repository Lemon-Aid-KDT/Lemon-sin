"""BOM(부품 목록) 자동 추출 모듈

도면에서 부품표(BOM) 영역을 감지하고, OCR + 정규식/LLM으로 구조화된 부품 목록을 추출한다.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import httpx
from loguru import logger


# ─────────────────────────────────────────────
# 데이터 클래스
# ─────────────────────────────────────────────


@dataclass
class BOMEntry:
    """BOM 테이블의 단일 행."""

    item_no: int = 0
    part_name: str = ""
    quantity: int = 1
    material: str = ""
    specification: str = ""
    raw_text: str = ""


@dataclass
class BOMResult:
    """BOM 추출 결과."""

    entries: list[BOMEntry] = field(default_factory=list)
    confidence: float = 0.0  # 0~1
    source: str = ""  # "regex", "llm", "none"
    raw_text: str = ""


# ─────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────

# BOM 헤더 패턴 (Korean / English / Japanese)
_HEADER_PATTERNS_KO = re.compile(
    r"(?:번호|No\.?|항목)"
    r"[\s|]*(?:품명|부품명|명칭|품목)"
    r"[\s|]*(?:수량|수|QTY)"
    r"(?:[\s|]*(?:재질|재료|소재|MATERIAL))?",
    re.IGNORECASE,
)
_HEADER_PATTERNS_EN = re.compile(
    r"(?:No\.?|Item|#)"
    r"[\s|]*(?:Part\s*Name|Name|Description|Component)"
    r"[\s|]*(?:Qty\.?|Quantity|Q'?ty)"
    r"(?:[\s|]*(?:Material|Mat'?l|Matl))?",
    re.IGNORECASE,
)
_HEADER_PATTERNS_JP = re.compile(
    r"(?:品番|番号|No\.?)"
    r"[\s|]*(?:品名|名称|部品名)"
    r"[\s|]*(?:数量|個数)"
    r"(?:[\s|]*(?:材質|材料))?",
    re.IGNORECASE,
)

# 행 파싱 패턴 — 번호, 이름, 수량 (+ 선택적 재질, 규격)
# 다양한 구분자를 지원: 탭, 파이프(|), 2개 이상 공백
_DELIMITER = r"(?:\t+|\s*\|\s*|\s{2,})"

_ROW_PATTERN = re.compile(
    rf"^\s*(\d+)"                         # item_no (숫자)
    rf"{_DELIMITER}"
    rf"([A-Za-z0-9\uAC00-\uD7A3\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]"
    rf"[^\t|]*?)"                          # part_name (알파벳/한글/일본어/한자 시작)
    rf"{_DELIMITER}"
    rf"(\d+)"                              # quantity
    rf"(?:"
    rf"{_DELIMITER}"
    rf"([A-Za-z0-9\uAC00-\uD7A3\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]"
    rf"[^\t|]*?))?"                        # material (optional)
    rf"(?:"
    rf"{_DELIMITER}"
    rf"([^\t|]+?))?"                       # specification (optional)
    rf"\s*$",
    re.MULTILINE,
)

# 프롬프트 인젝션 패턴 (LLM 전송 전 필터링)
_INJECTION_PATTERNS = re.compile(
    r"|".join([
        r"ignore\s+(previous|above|all)",
        r"disregard\s+(previous|above|all)",
        r"new\s+instructions?",
        r"system\s+prompt",
        r"you\s+are\s+now",
        r"forget\s+everything",
        r"override\s+(instructions?|rules?)",
        r"act\s+as\s+(a|an)?",
        r"do\s+not\s+follow",
        r"admin\s+(mode|access|override)",
        r"execute\s+(command|code)",
        r"<\s*/?script",
        r"\beval\s*\(",
        r"\bexec\s*\(",
    ]),
    re.IGNORECASE,
)


# ─────────────────────────────────────────────
# BOM 추출기
# ─────────────────────────────────────────────


class BOMExtractor:
    """BOM 추출기.

    추출 전략:
      1. regex: OCR 텍스트에서 테이블 패턴 매칭
      2. llm: Ollama로 OCR 텍스트 → 구조화 JSON (optional)
    """

    # LLM 호출 설정
    LLM_TIMEOUT: float = 30.0
    MAX_TEXT_LEN: int = 3000  # LLM에 전송할 최대 텍스트 길이

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "",
    ) -> None:
        self._ollama_url = ollama_base_url.rstrip("/")
        self._ollama_model = ollama_model

    # ── 공개 API ──────────────────────────────

    def extract_from_text(self, text: str, use_llm: bool = False) -> BOMResult:
        """OCR 텍스트에서 BOM을 추출한다.

        Args:
            text: OCR로 추출된 원본 텍스트.
            use_llm: True이면 regex 실패 시 LLM 폴백을 시도한다.

        Returns:
            BOMResult: 추출된 BOM 또는 빈 결과.
        """
        if not text or not text.strip():
            logger.debug("BOM 추출 입력 텍스트가 비어 있음")
            return BOMResult(raw_text=text or "", source="none")

        # Step 1: regex 파싱
        result = self._extract_regex(text)
        if result.entries:
            logger.info(
                f"BOM regex 추출 성공: {len(result.entries)}건, "
                f"confidence={result.confidence:.2f}"
            )
            return result

        # Step 2: LLM 폴백 (활성화 + 모델 설정 시)
        if use_llm and self._ollama_model:
            result = self._extract_llm(text)
            if result.entries:
                logger.info(
                    f"BOM LLM 추출 성공: {len(result.entries)}건, "
                    f"confidence={result.confidence:.2f}"
                )
                return result

        logger.debug("BOM 추출 실패: 테이블 구조를 찾을 수 없음")
        return BOMResult(raw_text=text, source="none")

    # ── regex 파싱 ─────────────────────────────

    def _extract_regex(self, text: str) -> BOMResult:
        """정규식으로 BOM 테이블을 파싱한다.

        헤더 감지 → 행 추출 → BOMEntry 생성.
        헤더가 없어도 행 패턴만으로 추출을 시도한다.

        Returns:
            BOMResult: 추출 결과. entries가 비어 있으면 실패.
        """
        has_header = self._detect_header(text)

        # 행 추출
        entries: list[BOMEntry] = []
        for m in _ROW_PATTERN.finditer(text):
            item_no_str, part_name, qty_str, material, spec = m.groups()
            try:
                item_no = int(item_no_str)
                qty = int(qty_str)
            except (ValueError, TypeError):
                continue

            part_name = part_name.strip()
            if not part_name:
                continue

            entries.append(
                BOMEntry(
                    item_no=item_no,
                    part_name=part_name,
                    quantity=qty,
                    material=(material or "").strip(),
                    specification=(spec or "").strip(),
                    raw_text=m.group(0).strip(),
                )
            )

        if not entries:
            return BOMResult(raw_text=text, source="regex")

        # 신뢰도 계산
        confidence = self._calc_confidence(entries, has_header, text)

        return BOMResult(
            entries=entries,
            confidence=confidence,
            source="regex",
            raw_text=text,
        )

    @staticmethod
    def _detect_header(text: str) -> bool:
        """BOM 테이블 헤더가 존재하는지 확인한다."""
        return bool(
            _HEADER_PATTERNS_KO.search(text)
            or _HEADER_PATTERNS_EN.search(text)
            or _HEADER_PATTERNS_JP.search(text)
        )

    @staticmethod
    def _calc_confidence(
        entries: list[BOMEntry], has_header: bool, text: str
    ) -> float:
        """추출 결과의 신뢰도를 계산한다 (0~1).

        기준:
          - 헤더 존재: +0.3
          - 연속 번호: +0.2
          - 항목 수 ≥ 3: +0.2
          - 재질 정보 비율: +0.15
          - 텍스트 대비 매칭 비율: +0.15
        """
        score = 0.0

        # 헤더 존재
        if has_header:
            score += 0.3

        # 연속 번호 체크
        item_nos = [e.item_no for e in entries]
        if item_nos == list(range(item_nos[0], item_nos[0] + len(item_nos))):
            score += 0.2

        # 항목 수
        if len(entries) >= 3:
            score += 0.2
        elif len(entries) >= 1:
            score += 0.1

        # 재질 정보 비율
        has_material = sum(1 for e in entries if e.material)
        if entries:
            mat_ratio = has_material / len(entries)
            score += 0.15 * mat_ratio

        # 텍스트 대비 매칭 비율
        matched_chars = sum(len(e.raw_text) for e in entries)
        text_len = len(text.strip())
        if text_len > 0:
            coverage = min(matched_chars / text_len, 1.0)
            score += 0.15 * coverage

        return min(score, 1.0)

    # ── LLM 폴백 ──────────────────────────────

    def _extract_llm(self, text: str) -> BOMResult:
        """LLM으로 BOM을 추출한다.

        Ollama /api/generate 엔드포인트에 구조화 프롬프트를 전송하고,
        JSON 응답을 파싱하여 BOMResult를 생성한다.

        Returns:
            BOMResult: 추출 결과. 실패 시 entries가 비어 있다.
        """
        # 보안: 인젝션 패턴 제거
        safe_text = self._sanitize_text(text[: self.MAX_TEXT_LEN])

        prompt = self._build_llm_prompt(safe_text)

        try:
            response = httpx.post(
                f"{self._ollama_url}/api/generate",
                json={
                    "model": self._ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 2048,
                    },
                    "format": "json",
                },
                timeout=self.LLM_TIMEOUT,
            )

            if response.status_code != 200:
                logger.warning(
                    f"BOM LLM 추출 HTTP 오류: {response.status_code}"
                )
                return BOMResult(raw_text=text, source="llm")

            data = response.json()
            llm_text = data.get("response", "")
            return self._parse_llm_response(llm_text, text)

        except httpx.TimeoutException:
            logger.warning("BOM LLM 추출 타임아웃")
            return BOMResult(raw_text=text, source="llm")
        except Exception as e:
            logger.error(f"BOM LLM 추출 실패: {e}")
            return BOMResult(raw_text=text, source="llm")

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """OCR 텍스트에서 프롬프트 인젝션 패턴을 제거한다."""
        if not text:
            return text
        if _INJECTION_PATTERNS.search(text):
            logger.warning(
                f"BOM OCR 텍스트에서 인젝션 패턴 감지 → 텍스트 제거 "
                f"(원본 길이: {len(text)})"
            )
            return "[OCR text redacted due to suspicious content]"
        return text

    @staticmethod
    def _build_llm_prompt(text: str) -> str:
        """LLM에 전송할 BOM 추출 프롬프트를 생성한다."""
        return (
            "You are a BOM (Bill of Materials) extraction assistant.\n"
            "Extract the parts table from the following OCR text of an engineering drawing.\n"
            "Return a JSON object with this exact structure:\n"
            '{"entries": [{"item_no": 1, "part_name": "...", "quantity": 1, '
            '"material": "...", "specification": "..."}]}\n'
            "Rules:\n"
            "- item_no must be an integer\n"
            "- quantity must be an integer (default 1 if unclear)\n"
            "- material and specification can be empty strings\n"
            "- Only include rows that are clearly BOM entries\n"
            "- Do NOT invent or hallucinate entries\n"
            f"\nOCR TEXT:\n{text}\n"
        )

    @staticmethod
    def _parse_llm_response(llm_text: str, raw_text: str) -> BOMResult:
        """LLM 응답 JSON을 파싱하여 BOMResult를 생성한다."""
        try:
            parsed = json.loads(llm_text)
        except (json.JSONDecodeError, TypeError):
            # JSON 블록을 텍스트에서 추출 시도
            json_match = re.search(r"\{[\s\S]*\}", llm_text)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                except (json.JSONDecodeError, TypeError):
                    logger.warning("BOM LLM 응답 JSON 파싱 실패")
                    return BOMResult(raw_text=raw_text, source="llm")
            else:
                logger.warning("BOM LLM 응답에서 JSON을 찾을 수 없음")
                return BOMResult(raw_text=raw_text, source="llm")

        raw_entries = parsed.get("entries", [])
        if not isinstance(raw_entries, list):
            return BOMResult(raw_text=raw_text, source="llm")

        entries: list[BOMEntry] = []
        for item in raw_entries:
            if not isinstance(item, dict):
                continue
            try:
                entries.append(
                    BOMEntry(
                        item_no=int(item.get("item_no", 0)),
                        part_name=str(item.get("part_name", "")),
                        quantity=int(item.get("quantity", 1)),
                        material=str(item.get("material", "")),
                        specification=str(item.get("specification", "")),
                    )
                )
            except (ValueError, TypeError):
                continue

        if not entries:
            return BOMResult(raw_text=raw_text, source="llm")

        # LLM 결과는 regex보다 신뢰도를 약간 낮게 설정
        confidence = min(0.6 + 0.05 * len(entries), 0.85)

        return BOMResult(
            entries=entries,
            confidence=confidence,
            source="llm",
            raw_text=raw_text,
        )
