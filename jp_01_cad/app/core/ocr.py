"""
도면 OCR 텍스트 추출 모듈

PaddleOCR을 사용하여 도면 이미지에서 텍스트(부품번호, 치수, 재질, 주기사항 등)를 추출한다.
PaddleOCR 설치 불가 시 EasyOCR을 폴백으로 사용한다.

Phase 3에서 영역별 OCR(표제란, 치수, 부품표)을 지원하기 위해
RegionOCRResult 및 영역 파싱 메서드를 포함한다.
"""

import re
from pathlib import Path
from dataclasses import dataclass, field

import cv2
import numpy as np
from loguru import logger
from PIL import Image


@dataclass
class RegionOCRResult:
    """영역별 OCR 결과"""
    region_class: str = ""                          # "title_block" | "dimension_area" | "parts_table"
    bbox: tuple[int, int, int, int] = (0, 0, 0, 0)  # (x1, y1, x2, y2) 픽셀 좌표
    text: str = ""                                   # 추출된 텍스트
    confidence: float = 0.0                          # 평균 OCR 신뢰도
    structured_data: dict = field(default_factory=dict)  # 파싱된 구조화 데이터


@dataclass
class OCRResult:
    """OCR 추출 결과"""
    full_text: str                          # 전체 추출 텍스트 (줄바꿈 구분)
    text_blocks: list[dict] = field(default_factory=list)  # [{text, confidence, bbox}]
    part_numbers: list[str] = field(default_factory=list)   # 추출된 부품번호 목록
    dimensions: list[str] = field(default_factory=list)     # 추출된 치수 정보
    materials: list[str] = field(default_factory=list)      # 추출된 재질 정보
    # Phase 3: 영역별 OCR 결과 (기본값으로 하위 호환)
    regions: list[RegionOCRResult] = field(default_factory=list)
    detection_enhanced: bool = False  # 탐지 기반 OCR 사용 여부


# ─── 배치 OCR 워커 (ProcessPoolExecutor용) ───

_worker_ocr: "DrawingOCR | None" = None


def _ocr_worker_init(lang: str, use_gpu: bool, fast_mode: bool) -> None:
    """워커 프로세스 초기화: 프로세스당 OCR 인스턴스 1개 생성."""
    global _worker_ocr
    _worker_ocr = DrawingOCR(lang=lang, use_gpu=use_gpu, fast_mode=fast_mode)


def _ocr_worker_extract(image_path: str) -> "OCRResult":
    """워커 프로세스에서 OCR 실행."""
    assert _worker_ocr is not None, "워커 미초기화"
    return _worker_ocr.extract(image_path)


class DrawingOCR:
    """도면 특화 OCR 엔진"""

    def __init__(self, lang: str = "korean", use_gpu: bool = False, fast_mode: bool = False):
        """
        Args:
            lang: OCR 언어 설정 ("korean", "en", "ch" 등)
            use_gpu: GPU 사용 여부
            fast_mode: 고속 모드 (mobile_det + 전처리 비활성화, 25x 빠름)
                       텍스트 검출 수 동일, 문서 방향/왜곡 보정 없음.
                       CAD 도면 배치 등록에 적합.
        """
        self.lang = lang
        self.use_gpu = use_gpu
        self.fast_mode = fast_mode
        self._engine = None
        self._engine_type = None

    def _init_engine(self):
        """OCR 엔진 초기화 (지연 로딩)"""
        if self._engine is not None:
            return

        # PaddleOCR 시도 (v3.4.0+ 새 API)
        try:
            from paddleocr import PaddleOCR

            lang_map = {"korean": "korean", "en": "en", "ch": "ch"}
            ocr_lang = lang_map.get(self.lang, "en")

            if self.fast_mode:
                # 고속 모드: mobile_det (25x 빠름) + 전처리 비활성화
                # 벤치마크: server_det 255s → mobile_det+no_preproc 10s (동일 텍스트 수)
                self._engine = PaddleOCR(
                    lang=ocr_lang,
                    text_detection_model_name="PP-OCRv5_mobile_det",
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                )
                logger.info(f"PaddleOCR 초기화 완료 (lang={ocr_lang}, FAST mode: mobile_det)")
            else:
                self._engine = PaddleOCR(lang=ocr_lang)
                logger.info(f"PaddleOCR 초기화 완료 (lang={ocr_lang})")
            self._engine_type = "paddleocr"
            return
        except ImportError:
            logger.warning("PaddleOCR 미설치, EasyOCR로 폴백 시도")

        # EasyOCR 폴백
        try:
            import easyocr

            lang_list = ["ko", "en"] if self.lang == "korean" else ["en"]
            self._engine = easyocr.Reader(lang_list, gpu=self.use_gpu)
            self._engine_type = "easyocr"
            logger.info(f"EasyOCR 초기화 완료 (langs={lang_list})")
            return
        except ImportError:
            logger.error("PaddleOCR, EasyOCR 모두 미설치")
            raise RuntimeError(
                "OCR 엔진을 설치해주세요: pip install paddleocr 또는 pip install easyocr"
            )

    # ─────────────────────────────────────────────
    # 배경 반전 전처리 (Dark→Light)
    # ─────────────────────────────────────────────

    @staticmethod
    def _preprocess_invert_if_dark(image_path: str) -> str | None:
        """어두운 배경 도면을 밝은 배경으로 반전하여 임시 파일로 저장한다.

        CAD 도면은 어두운 배경(검정/진회색)에 밝은 선(흰색/녹색)으로 렌더링되는 경우가 많다.
        OCR 엔진은 밝은 배경에 어두운 텍스트를 인식하도록 최적화되어 있으므로,
        배경이 어두운 경우 반전하면 인식률이 크게 향상된다.

        Returns:
            반전된 임시 파일 경로 (반전 불필요 시 None)
        """
        try:
            img = cv2.imread(image_path, cv2.IMREAD_COLOR)
            if img is None:
                return None

            # 그레이스케일로 변환하여 평균 밝기 측정
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            mean_brightness = float(gray.mean())

            # 평균 밝기 < 128이면 어두운 배경으로 판단
            if mean_brightness >= 128:
                return None

            # 반전 + Otsu 이진화 (노이즈 제거)
            inverted = cv2.bitwise_not(gray)
            _, binarized = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 임시 파일에 저장
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            cv2.imwrite(tmp.name, binarized)
            logger.debug(
                f"배경 반전 적용: 평균밝기 {mean_brightness:.0f} → 반전+이진화"
            )
            return tmp.name
        except Exception as e:
            logger.debug(f"배경 반전 전처리 실패 (원본 사용): {e}")
            return None

    # ─────────────────────────────────────────────
    # 파일명 기반 부품번호 추출
    # ─────────────────────────────────────────────

    @staticmethod
    def extract_part_number_from_filename(file_path: str | Path) -> list[str]:
        """파일명에서 부품번호를 추출한다.

        MiSUMi 카탈로그 도면은 파일명 자체가 부품번호이다:
          psfcg20.png → PSFCG20
          geal2.0-50-e.png → GEAL2.0-50-E
          UCP204.png → UCP204

        Args:
            file_path: 도면 이미지 경로

        Returns:
            파일명에서 추출한 부품번호 리스트 (보통 1개)
        """
        stem = Path(file_path).stem  # 확장자 제외
        # UUID 접두사 제거 (등록 시 추가되는 "8f4100f5_" 형태)
        stem = re.sub(r"^[0-9a-f]{8}_", "", stem)
        if not stem or len(stem) < 3:
            return []
        # 파일명을 대문자로 변환하여 부품번호로 사용
        part_number = stem.upper()
        return [part_number]

    def extract(self, image_path: str | Path) -> OCRResult:
        """
        도면 이미지에서 텍스트를 추출한다.

        배경 반전 전처리를 자동 적용하여 어두운 배경 도면의 인식률을 높인다.
        OCR 결과가 부족할 경우 파일명에서 부품번호를 보충한다.

        Args:
            image_path: 도면 이미지 경로

        Returns:
            OCRResult: 추출된 텍스트 및 메타데이터
        """
        self._init_engine()
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"이미지 파일 없음: {image_path}")

        logger.info(f"OCR 처리 시작: {image_path.name}")

        # 배경 반전 전처리 (어두운 배경 도면 자동 감지)
        inverted_path = self._preprocess_invert_if_dark(str(image_path))
        ocr_input_path = inverted_path or str(image_path)

        try:
            if self._engine_type == "paddleocr":
                text_blocks = self._extract_paddle(ocr_input_path)
            else:
                text_blocks = self._extract_easyocr(ocr_input_path)
        finally:
            # 임시 반전 파일 삭제
            if inverted_path:
                try:
                    Path(inverted_path).unlink(missing_ok=True)
                except OSError:
                    pass

        # 전체 텍스트 조합
        full_text = "\n".join([block["text"] for block in text_blocks])

        # 도면 특화 정보 추출
        part_numbers = self._extract_part_numbers(full_text)
        dimensions = self._extract_dimensions(full_text)
        materials = self._extract_materials(full_text)

        # 파일명 기반 부품번호 보충 (OCR에서 부품번호를 못 찾은 경우)
        if not part_numbers:
            filename_parts = self.extract_part_number_from_filename(image_path)
            if filename_parts:
                part_numbers = filename_parts
                logger.info(
                    f"파일명 기반 부품번호 보충: {filename_parts}"
                )

        result = OCRResult(
            full_text=full_text,
            text_blocks=text_blocks,
            part_numbers=part_numbers,
            dimensions=dimensions,
            materials=materials,
        )

        logger.info(
            f"OCR 완료: {len(text_blocks)}개 텍스트 블록, "
            f"{len(part_numbers)}개 부품번호 추출"
        )
        return result

    def _extract_paddle(self, image_path: str) -> list[dict]:
        """PaddleOCR로 텍스트 추출 (v3.4.0+ predict API)"""
        results = self._engine.predict(image_path)
        text_blocks = []

        if results:
            item = results[0]
            texts = item.get("rec_texts", [])
            scores = item.get("rec_scores", [])
            polys = item.get("dt_polys", [])

            for i, text in enumerate(texts):
                if not text or not text.strip():
                    continue
                conf = scores[i] if i < len(scores) else 0.0
                bbox = polys[i].tolist() if i < len(polys) else []
                text_blocks.append({
                    "text": text,
                    "confidence": conf,
                    "bbox": bbox,
                })

        return text_blocks

    def _extract_easyocr(self, image_path: str) -> list[dict]:
        """EasyOCR로 텍스트 추출"""
        results = self._engine.readtext(image_path)
        text_blocks = []

        for bbox, text, confidence in results:
            text_blocks.append({
                "text": text,
                "confidence": confidence,
                "bbox": bbox,
            })

        return text_blocks

    @staticmethod
    def _extract_part_numbers(text: str) -> list[str]:
        """
        도면 텍스트에서 부품번호 패턴을 추출한다.
        일반적인 부품번호 패턴 + MiSUMi 카탈로그 부품번호 패턴 지원.
        """
        patterns = [
            r"[A-Z]{2,4}-\d{4,8}",           # AB-12345
            r"\d{5,10}",                       # 12345678
            r"[A-Z]\d{2,3}-[A-Z]?\d{4,6}",   # A12-B3456
            r"P/N[:\s]*([A-Z0-9\-]+)",        # P/N: AB-1234
            r"PART[:\s#]*([A-Z0-9\-]+)",      # PART: AB-1234
            # ── MiSUMi 카탈로그 부품번호 패턴 ──
            r"[A-Z]{2,6}\d{1,5}",             # ABNZM06, BGBW6005, CLSG13
            r"[A-Z]{2,6}\d{1,5}-[\d.]+(?:-[\w.]+)*",  # ABNZM06-2.5, AHTFW16-AT10150-12
            r"[A-Z]{2,6}\d{1,5}[A-Z]{0,3}\d*",     # BGBW6005ZZ, BGSN6900ZZ
            r"[A-Z]+\d+[A-Z]*[-+]\w+",       # UKFS306+H2306X, BE2KF28-340-30
            r"[A-Z]{1,4}\d[A-Z]\d{1,5}",     # BS2M26 (알파+숫자 혼재)
        ]
        # 제외 패턴: 단순 치수나 일반 텍스트
        exclude_patterns = {
            r"^M\d+$",           # M5, M10 (나사 치수)
            r"^\d+MM$",          # 100MM (치수)
            r"^R\d+$",           # R10 (반지름)
            r"^[A-Z]$",         # 단일 문자
            r"^ISO\d+",         # ISO 표준
        }

        part_numbers = []
        upper_text = text.upper()
        # 알파-숫자 사이 공백만 제거 (OCR이 "CLSG 13", "BYHZ 5" 등 삽입)
        # 전체 공백 제거는 "PART 12345678" → "PART12345678" 오매칭 유발
        compact_lines = [
            re.sub(r"([A-Z])\s+(\d)", r"\1\2", line)
            for line in upper_text.split("\n")
        ]
        text_variants = [upper_text]
        compact_text = "\n".join(compact_lines)
        if compact_text != upper_text:
            text_variants.append(compact_text)
        for variant in text_variants:
            for pattern in patterns:
                matches = re.findall(pattern, variant)
                part_numbers.extend(matches)

        # 제외 필터 적용 + 최소 길이 3자
        filtered = []
        for pn in part_numbers:
            if len(pn) < 3:
                continue
            excluded = False
            for ex_pat in exclude_patterns:
                if re.match(ex_pat, pn):
                    excluded = True
                    break
            if not excluded:
                filtered.append(pn)

        unique = list(set(filtered))

        # 서브스트링 + 리딩제로 정규화 중복 제거
        # 예: ["ABNZM6", "ABNZM6-1.5-100"] → ["ABNZM6-1.5-100"]
        # 예: ["BMSFC07", "BMSFC7"] → ["BMSFC07"]
        def _norm_pn(s: str) -> str:
            """리딩제로 제거 + O↔0 정규화"""
            n = re.sub(r"(?<=[A-Z])0+(?=\d)", "", s)
            n = n.replace("O", "0")
            return n

        unique.sort(key=len, reverse=True)
        deduped: list[str] = []
        deduped_norms: list[str] = []
        for pn in unique:
            pn_norm = _norm_pn(pn)
            is_dup = False
            for existing, existing_norm in zip(deduped, deduped_norms):
                # 접두어 매칭: "ABNZM6"이 "ABNZM6-1.5-100"의 접두어 → 중복
                # (서브스트링은 과도: "12345678"이 "PART12345678"에서 제거됨)
                # 또는 정규화 완전 매칭: "BMSFC07" == "BMSFC7" (리딩제로)
                if existing.startswith(pn) or pn_norm == existing_norm:
                    is_dup = True
                    break
            if not is_dup:
                deduped.append(pn)
                deduped_norms.append(pn_norm)

        return deduped

    @staticmethod
    def _extract_dimensions(text: str) -> list[str]:
        """치수 정보 추출 (예: 100mm, 25.4±0.1, Ø50)"""
        patterns = [
            r"\d+\.?\d*\s*(?:mm|cm|m|in|inch)",      # 100mm, 25.4cm
            r"[ØφΦ]\s*\d+\.?\d*",                     # Ø50
            r"\d+\.?\d*\s*[±]\s*\d+\.?\d*",           # 25.4±0.1
            r"R\s*\d+\.?\d*",                          # R10
            r"\d+\.?\d*\s*[xX×]\s*\d+\.?\d*",         # 100x50
        ]
        dimensions = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            dimensions.extend(matches)

        return list(set(dimensions))

    @staticmethod
    def _extract_materials(text: str) -> list[str]:
        """재질 정보 추출 (정규식 경계 매칭으로 오탐 최소화)"""
        # 정규식 패턴으로 단어 경계 매칭 (예: "AL"이 "BALL"에 매칭되지 않도록)
        material_patterns = [
            r"\bSUS\d*\b",                    # SUS304, SUS316
            r"\bS45C\b", r"\bSM45C\b",        # 탄소강
            r"\bSS400\b",                      # 일반 구조용 강
            r"\bSCM\d*\b",                     # 크롬몰리강
            r"\bSTS\d*\b",                     # 스테인리스
            r"\bA[56]\d{3}\b",                 # A6061, A5052 (알루미늄)
            r"\bAL\d{4}\b",                    # AL6061
            r"\bGC\d{3}\b",                    # GC200 (주철)
            r"\bSPC[CDHEH]*\b",               # SPCC, SPHC
            r"\bFC\d{3}\b",                    # FC200 (주철)
            r"\bSKD\d+\b",                     # SKD11 (금형강)
            r"\bSKH\d+\b",                     # SKH51 (하이스)
            r"\bSUJ\d\b",                      # SUJ2 (베어링강)
            r"\bC\d{4}\b",                     # C3604 (황동)
            r"\bMCNYLON\b",                    # MC 나일론
            r"\bPOM\b", r"\bPEEK\b",          # 엔지니어링 플라스틱
        ]
        # 단순 키워드 (단독으로 출현 시)
        simple_keywords = [
            "STEEL", "ALUMINUM", "COPPER", "BRASS", "IRON",
            "TITANIUM", "PLASTIC", "RUBBER", "STAINLESS",
            "스틸", "알루미늄", "스테인리스", "구리", "황동", "주철",
        ]

        found = []
        upper_text = text.upper()

        for pat in material_patterns:
            matches = re.findall(pat, upper_text)
            found.extend(matches)

        for keyword in simple_keywords:
            if keyword.upper() in upper_text:
                found.append(keyword)

        return list(set(found))

    # ─────────────────────────────────────────────
    # 배치 OCR (병렬 처리)
    # ─────────────────────────────────────────────

    def extract_batch(
        self,
        image_paths: list[str | Path],
        workers: int = 4,
    ) -> list[OCRResult]:
        """여러 이미지를 병렬로 OCR 처리.

        Args:
            image_paths: 이미지 경로 리스트
            workers: 병렬 워커 수 (0이면 순차 처리)

        Returns:
            OCRResult 리스트 (입력 순서 유지)
        """
        if not image_paths:
            return []

        if workers <= 0 or len(image_paths) <= 2:
            # 순차 처리
            return [self.extract(p) for p in image_paths]

        from concurrent.futures import ProcessPoolExecutor, as_completed

        # 워커별 독립 OCR 처리 (PaddleOCR는 프로세스당 1 인스턴스)
        results: list[tuple[int, OCRResult]] = []

        with ProcessPoolExecutor(
            max_workers=min(workers, len(image_paths)),
            initializer=_ocr_worker_init,
            initargs=(self.lang, self.use_gpu, self.fast_mode),
        ) as executor:
            futures = {
                executor.submit(_ocr_worker_extract, str(p)): i
                for i, p in enumerate(image_paths)
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    results.append((idx, result))
                except Exception as e:
                    logger.warning(f"배치 OCR 실패 [{idx}]: {e}")
                    results.append((idx, OCRResult(
                        full_text="", text_blocks=[], part_numbers=[],
                        dimensions=[], materials=[],
                    )))

        # 원래 순서대로 정렬
        results.sort(key=lambda x: x[0])
        return [r for _, r in results]

    # ─────────────────────────────────────────────
    # Phase 3: 영역별 OCR
    # ─────────────────────────────────────────────

    def extract_region(
        self,
        image: Image.Image,
        region_class: str = "",
    ) -> RegionOCRResult:
        """
        크롭된 영역 이미지에서 OCR을 수행한다.

        PIL Image 객체를 직접 받아 numpy 배열로 변환한 후 OCR을 실행한다.
        영역 타입에 따라 전용 파서를 적용하여 구조화 데이터를 추출한다.

        Args:
            image: 크롭된 영역 이미지 (PIL Image)
            region_class: 영역 유형 ("title_block", "dimension_area", "parts_table")

        Returns:
            RegionOCRResult: 영역 OCR 결과 (텍스트 + 구조화 데이터)
        """
        self._init_engine()

        # 작은 크롭 영역의 OCR 정확도를 위해 업스케일
        min_dim = min(image.width, image.height)
        if min_dim < 200:
            scale = max(2.0, 400 / min_dim)
            new_w = int(image.width * scale)
            new_h = int(image.height * scale)
            image = image.resize((new_w, new_h), Image.LANCZOS)

        img_array = np.array(image.convert("RGB"))

        # OCR 실행 (numpy 배열 입력)
        if self._engine_type == "paddleocr":
            text_blocks = self._extract_paddle_from_array(img_array)
        else:
            text_blocks = self._extract_easyocr_from_array(img_array)

        full_text = "\n".join([b["text"] for b in text_blocks])
        avg_confidence = (
            sum(b["confidence"] for b in text_blocks) / len(text_blocks)
            if text_blocks else 0.0
        )

        # 영역 타입별 구조화 파싱
        structured_data = {}
        if region_class == "title_block":
            structured_data = self._parse_title_block(full_text)
        elif region_class == "parts_table":
            structured_data = self._parse_parts_table(full_text)
        elif region_class == "dimension_area":
            structured_data = self._parse_dimension_area(full_text)

        return RegionOCRResult(
            region_class=region_class,
            text=full_text,
            confidence=round(avg_confidence, 4),
            structured_data=structured_data,
        )

    def _extract_paddle_from_array(self, img_array: np.ndarray) -> list[dict]:
        """PaddleOCR로 numpy 배열에서 텍스트 추출 (v3.4.0+ predict API)"""
        # PaddleOCR 3.4.0: RGB 3채널 필요
        if img_array.ndim == 2:
            img_array = np.stack([img_array] * 3, axis=-1)
        elif img_array.ndim == 3 and img_array.shape[2] == 4:
            img_array = img_array[:, :, :3]

        results = self._engine.predict(img_array)
        text_blocks = []

        if results:
            item = results[0]
            texts = item.get("rec_texts", [])
            scores = item.get("rec_scores", [])
            polys = item.get("dt_polys", [])

            for i, text in enumerate(texts):
                if not text or not text.strip():
                    continue
                conf = scores[i] if i < len(scores) else 0.0
                bbox = polys[i].tolist() if i < len(polys) else []
                text_blocks.append({
                    "text": text,
                    "confidence": conf,
                    "bbox": bbox,
                })

        return text_blocks

    def _extract_easyocr_from_array(self, img_array: np.ndarray) -> list[dict]:
        """EasyOCR로 numpy 배열에서 텍스트 추출"""
        results = self._engine.readtext(img_array)
        text_blocks = []

        for bbox, text, confidence in results:
            text_blocks.append({
                "text": text,
                "confidence": confidence,
                "bbox": bbox,
            })

        return text_blocks

    @staticmethod
    def _parse_title_block(text: str) -> dict:
        """
        표제란 텍스트에서 구조화된 정보를 추출한다.

        한국어/영어 혼용 CAD 도면의 표제란에서 도번, 재질, 척도,
        날짜, 작성자, 승인자, 회사명 등을 정규식으로 파싱한다.

        Args:
            text: 표제란 영역 OCR 텍스트

        Returns:
            dict: 파싱된 구조화 데이터
        """
        data: dict[str, str] = {}
        if not text:
            return data

        upper_text = text.upper()

        # 도면번호 / Drawing Number
        dwg_patterns = [
            r"(?:도면번호|도번|DWG\.?\s*N[oO]\.?|DRAWING\s*N[oO]\.?)[:\s]*([A-Z0-9\-_.]+)",
            r"(?:도면\s*번호|도\s*번)[:\s]*([A-Za-z0-9\-_.]+)",
        ]
        for pat in dwg_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data["drawing_number"] = m.group(1).strip()
                break

        # 레이블 매칭 실패 시 → MiSUMi 부품번호 직접 추출
        if "drawing_number" not in data:
            misumi_patterns = [
                r"([A-Z]{2,8}\d{1,5}(?:[-+][\w.]+)*(?:ZZ|ST)?)",   # ABNZM06, BGBW6005ZZ
                r"([A-Z]{2,8}-\d+(?:-[A-Z0-9.]+)*)",               # ACHLB-6-E, BE2KF28-340-30
                r"([A-Z]+\d+[A-Z]*[+][A-Z]+\d+[A-Z]*)",           # UKFS306+H2306X
                r"([A-Z]{1,4}\d[A-Z]\d{1,5})",                      # BS2M26 (알파+숫자 혼재)
            ]
            # 공백/줄바꿈 제거 버전도 시도 (OCR이 "CLSG 13", "BYHZ 5" 등 공백 삽입)
            text_variants = [upper_text]
            # 각 줄에서 공백 제거
            nospace_lines = [line.replace(" ", "") for line in upper_text.split("\n")]
            nospace_text = "\n".join(nospace_lines)
            if nospace_text != upper_text:
                text_variants.append(nospace_text)
            # 완전 연결 (줄바꿈+공백 모두 제거) — 줄 경계 걸친 부품번호 처리
            concat_text = upper_text.replace("\n", "").replace(" ", "")
            if concat_text not in text_variants:
                text_variants.append(concat_text)

            best_match = ""
            for variant in text_variants:
                for pat in misumi_patterns:
                    matches = re.findall(pat, variant)
                    for m in matches:
                        if len(m) > len(best_match) and len(m) >= 4:
                            if re.search(r"[A-Z]", m) and re.search(r"\d", m):
                                best_match = m
            if best_match:
                data["drawing_number"] = best_match

        # 품명 / Part Name
        name_patterns = [
            r"(?:품명|PART\s*NAME|NAME|품\s*명)[:\s]*(.+?)(?:\n|$)",
            r"(?:명칭|DESCRIPTION|DESC)[:\s]*(.+?)(?:\n|$)",
        ]
        for pat in name_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data["part_name"] = m.group(1).strip()
                break

        # 재질 / Material
        mat_patterns = [
            r"(?:재질|재료|MATERIAL|MAT'?L)[:\s]*([A-Za-z0-9\s\-]+?)(?:\n|$)",
        ]
        for pat in mat_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data["material"] = m.group(1).strip()
                break

        # 척도 / Scale
        scale_patterns = [
            r"(?:척도|SCALE)[:\s]*([\d]+\s*[:]\s*[\d]+|NTS|N\.?T\.?S\.?|FULL)",
        ]
        for pat in scale_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data["scale"] = m.group(1).strip()
                break

        # 날짜 / Date
        date_patterns = [
            r"(?:일자|DATE|작성일|날짜)[:\s]*(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})",
            r"(?:일자|DATE|작성일|날짜)[:\s]*(\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2})",
        ]
        for pat in date_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data["date"] = m.group(1).strip()
                break

        # 작성자 / Drawn By
        drawn_patterns = [
            r"(?:작성|설계|DRAWN\s*BY|DRAWN|설계자)[:\s]*([A-Za-z가-힣]+)",
        ]
        for pat in drawn_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data["drawn_by"] = m.group(1).strip()
                break

        # 승인자 / Approved By
        approved_patterns = [
            r"(?:승인|검토|APPROVED|CHECKED|APP'?D)[:\s]*([A-Za-z가-힣]+)",
        ]
        for pat in approved_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data["approved_by"] = m.group(1).strip()
                break

        # 회사명 (text 내 일반적인 회사 표기)
        company_patterns = [
            r"(?:회사|COMPANY|사명)[:\s]*(.+?)(?:\n|$)",
            r"((?:주\)|\(주\)|㈜|CO\.?,?\s*LTD\.?|INC\.?|CORP\.?).*?)(?:\n|$)",
        ]
        for pat in company_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data["company"] = m.group(1).strip()
                break

        return data

    @staticmethod
    def _parse_parts_table(text: str) -> dict:
        """
        부품표(BOM) 텍스트에서 구조화된 정보를 추출한다.

        Args:
            text: 부품표 영역 OCR 텍스트

        Returns:
            dict: {"items": [{"item_no": str, "part_name": str,
                              "quantity": str, "material": str}, ...]}
        """
        data: dict = {"items": []}
        if not text:
            return data

        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 행 패턴: 번호 + 품명 + 수량 + (재질)
            # 예: "1  Shaft Assembly  2  SUS304"
            # 예: "01  볼트 M10x30  4  SM45C"
            row_pattern = r"(\d{1,3})\s+(.+?)\s+(\d{1,5})\s*(.*)$"
            m = re.match(row_pattern, line)
            if m:
                item = {
                    "item_no": m.group(1).strip(),
                    "part_name": m.group(2).strip(),
                    "quantity": m.group(3).strip(),
                    "material": m.group(4).strip() if m.group(4) else "",
                }
                data["items"].append(item)

        return data

    @staticmethod
    def _parse_dimension_area(text: str) -> dict:
        """
        치수 영역 텍스트에서 구조화된 치수 정보를 추출한다.

        영역 분리로 도면 선분/표제란 노이즈가 제거되어
        기존 _extract_dimensions()보다 높은 정확도를 제공한다.

        Args:
            text: 치수 영역 OCR 텍스트

        Returns:
            dict: {"dimensions": [...], "tolerances": [...], "diameters": [...]}
        """
        data: dict[str, list[str]] = {
            "dimensions": [],
            "tolerances": [],
            "diameters": [],
        }
        if not text:
            return data

        # 일반 치수 (mm, cm, m, inch)
        dim_patterns = [
            r"\d+\.?\d*\s*(?:mm|cm|m|in|inch)",
            r"\d+\.?\d*\s*[xX×]\s*\d+\.?\d*",
        ]
        for pat in dim_patterns:
            matches = re.findall(pat, text)
            data["dimensions"].extend(matches)

        # 공차 (±)
        tol_patterns = [
            r"\d+\.?\d*\s*[±]\s*\d+\.?\d*",
            r"[+\-]\d+\.?\d*\s*/\s*[+\-]?\d+\.?\d*",  # +0.05/-0.02
        ]
        for pat in tol_patterns:
            matches = re.findall(pat, text)
            data["tolerances"].extend(matches)

        # 지름 (Ø, φ)
        dia_patterns = [
            r"[ØφΦ]\s*\d+\.?\d*",
        ]
        for pat in dia_patterns:
            matches = re.findall(pat, text)
            data["diameters"].extend(matches)

        # 반지름 (R)
        r_pattern = r"R\s*\d+\.?\d*"
        r_matches = re.findall(r_pattern, text)
        data["dimensions"].extend(r_matches)

        # 중복 제거
        data["dimensions"] = list(set(data["dimensions"]))
        data["tolerances"] = list(set(data["tolerances"]))
        data["diameters"] = list(set(data["diameters"]))

        return data
