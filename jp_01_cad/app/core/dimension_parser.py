"""
도면 치수 파싱 및 비교 모듈

OCR 텍스트에서 치수(길이, 각도, 나사산, 공차, 지름)를 추출하고,
두 치수 목록 간 차이를 비교한다.
OCR 노이즈('O'→'0', 공백 등)에 대한 보정을 포함한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from loguru import logger


# ─────────────────────────────────────────────
# 데이터 클래스
# ─────────────────────────────────────────────


@dataclass
class ParsedDimension:
    """파싱된 단일 치수"""

    value: float
    unit: str = "mm"  # mm, cm, m, °, deg
    dim_type: str = "length"  # length, angle, thread, tolerance, diameter
    label: str = ""  # 원본 라벨 (예: "M8", "Φ20")
    raw_text: str = ""
    tolerance_plus: float = 0.0
    tolerance_minus: float = 0.0


@dataclass
class DimensionDiff:
    """두 치수 목록 비교 결과"""

    matched: list[tuple[ParsedDimension, ParsedDimension]] = field(
        default_factory=list,
    )  # 일치 쌍
    changed: list[tuple[ParsedDimension, ParsedDimension, float]] = field(
        default_factory=list,
    )  # (a, b, diff)
    only_in_a: list[ParsedDimension] = field(default_factory=list)
    only_in_b: list[ParsedDimension] = field(default_factory=list)
    similarity: float = 0.0  # 0~1


# ─────────────────────────────────────────────
# OCR 노이즈 보정
# ─────────────────────────────────────────────

# 숫자 문맥에서 흔한 OCR 치환
_OCR_DIGIT_MAP: dict[str, str] = {
    "O": "0",
    "o": "0",
    "l": "1",
    "I": "1",
    "S": "5",
    "B": "8",
    "G": "6",
    "Z": "2",
}


def _clean_ocr_number(text: str) -> str:
    """숫자 문맥의 OCR 노이즈를 보정한다.

    - 'O' → '0', 'l' → '1' 등
    - 숫자 사이 공백 제거 ('1 0 0' → '100')
    - 콤마 구분자 제거 ('1,000' → '1000')
    """
    # 먼저 문자→숫자 치환
    cleaned = []
    for ch in text:
        if ch in _OCR_DIGIT_MAP:
            cleaned.append(_OCR_DIGIT_MAP[ch])
        else:
            cleaned.append(ch)
    result = "".join(cleaned)

    # 숫자 사이 공백 제거 (예: "1 0 0" → "100")
    result = re.sub(r"(\d)\s+(\d)", r"\1\2", result)
    # 반복 적용 (3자리 이상 연속 공백)
    result = re.sub(r"(\d)\s+(\d)", r"\1\2", result)

    # 콤마 구분자 제거 (예: "1,000.5" → "1000.5")
    result = re.sub(r"(\d),(\d{3})", r"\1\2", result)

    return result


def _safe_float(text: str) -> float | None:
    """문자열을 float로 변환, 실패 시 None 반환."""
    try:
        return float(_clean_ocr_number(text.strip()))
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────
# 치수 파싱
# ─────────────────────────────────────────────

# 나사산: M8, M8x1.25, M10×1.5, M 8
_RE_THREAD = re.compile(
    r"(M)\s*(\d+(?:\.\d+)?)"
    r"(?:\s*[x×]\s*(\d+(?:\.\d+)?))?",
    re.IGNORECASE,
)

# 지름: Φ20, φ20, ø20, ⌀20
_RE_DIAMETER = re.compile(
    r"[Φφø⌀]\s*(\d+(?:\.\d+)?)",
)

# 공차 ±: 50±0.05
_RE_TOLERANCE_PM = re.compile(
    r"(\d+(?:\.\d+)?)\s*[±]\s*(\d+(?:\.\d+)?)",
)

# 공차 +/-: 50+0.1/-0.05 또는 50+/-0.05
_RE_TOLERANCE_SPLIT = re.compile(
    r"(\d+(?:\.\d+)?)\s*"
    r"\+\s*(\d+(?:\.\d+)?)\s*/\s*-\s*(\d+(?:\.\d+)?)",
)

_RE_TOLERANCE_SYMMETRIC = re.compile(
    r"(\d+(?:\.\d+)?)\s*\+/-\s*(\d+(?:\.\d+)?)",
)

# 각도: 45°, 45 deg, 90°
_RE_ANGLE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:°|deg\b)",
    re.IGNORECASE,
)

# 단위 포함 길이: 50mm, 100cm, 2.5m (m 뒤에 다른 글자 없을 때)
_RE_LENGTH_UNIT = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mm|cm|m)\b",
    re.IGNORECASE,
)

# 순수 숫자 (다른 패턴에 잡히지 않은 것, mm로 가정)
_RE_PLAIN_NUMBER = re.compile(
    r"(?<![A-Za-zΦφø⌀×])\b(\d+(?:\.\d+)?)\b(?!\s*(?:°|deg|mm|cm|m)\b)",
)


def parse_dimensions(text: str) -> list[ParsedDimension]:
    """OCR 텍스트에서 치수를 추출한다.

    지원 패턴:
      1. 나사산: M8, M8x1.25, M10×1.5
      2. 지름: Φ20, φ20, ø20
      3. 공차: 50±0.05, 50+0.1/-0.05, 50+/-0.05
      4. 각도: 45°, 45deg
      5. 단위 포함 길이: 50mm, 100cm, 2.5m
      6. 순수 숫자(mm 가정): 50, 100.5

    중복은 (value, dim_type, label) 기준으로 제거한다.
    """
    if not text or not text.strip():
        logger.debug("빈 텍스트, 치수 없음")
        return []

    cleaned = _clean_ocr_number(text)
    results: list[ParsedDimension] = []
    # 이미 소비된 span을 추적하여 중복 매칭 방지
    consumed: set[tuple[int, int]] = set()

    def _overlaps(start: int, end: int) -> bool:
        for cs, ce in consumed:
            if start < ce and end > cs:
                return True
        return False

    def _consume(start: int, end: int) -> None:
        consumed.add((start, end))

    # 1. 나사산
    for m in _RE_THREAD.finditer(cleaned):
        if _overlaps(m.start(), m.end()):
            continue
        val = _safe_float(m.group(2))
        if val is None:
            continue
        pitch = m.group(3)
        label = f"M{m.group(2)}"
        if pitch:
            label += f"x{pitch}"
        results.append(
            ParsedDimension(
                value=val,
                unit="mm",
                dim_type="thread",
                label=label,
                raw_text=m.group(0).strip(),
            ),
        )
        _consume(m.start(), m.end())

    # 2. 지름
    for m in _RE_DIAMETER.finditer(cleaned):
        if _overlaps(m.start(), m.end()):
            continue
        val = _safe_float(m.group(1))
        if val is None:
            continue
        results.append(
            ParsedDimension(
                value=val,
                unit="mm",
                dim_type="diameter",
                label=f"\u03a6{m.group(1)}",
                raw_text=m.group(0).strip(),
            ),
        )
        _consume(m.start(), m.end())

    # 3. 공차 (±)
    for m in _RE_TOLERANCE_PM.finditer(cleaned):
        if _overlaps(m.start(), m.end()):
            continue
        val = _safe_float(m.group(1))
        tol = _safe_float(m.group(2))
        if val is None or tol is None:
            continue
        results.append(
            ParsedDimension(
                value=val,
                unit="mm",
                dim_type="tolerance",
                label=f"{m.group(1)}\u00b1{m.group(2)}",
                raw_text=m.group(0).strip(),
                tolerance_plus=tol,
                tolerance_minus=tol,
            ),
        )
        _consume(m.start(), m.end())

    # 3b. 공차 (+val/-val)
    for m in _RE_TOLERANCE_SPLIT.finditer(cleaned):
        if _overlaps(m.start(), m.end()):
            continue
        val = _safe_float(m.group(1))
        tp = _safe_float(m.group(2))
        tm = _safe_float(m.group(3))
        if val is None or tp is None or tm is None:
            continue
        results.append(
            ParsedDimension(
                value=val,
                unit="mm",
                dim_type="tolerance",
                label=f"{m.group(1)}+{m.group(2)}/-{m.group(3)}",
                raw_text=m.group(0).strip(),
                tolerance_plus=tp,
                tolerance_minus=tm,
            ),
        )
        _consume(m.start(), m.end())

    # 3c. 공차 (+/- symmetric)
    for m in _RE_TOLERANCE_SYMMETRIC.finditer(cleaned):
        if _overlaps(m.start(), m.end()):
            continue
        val = _safe_float(m.group(1))
        tol = _safe_float(m.group(2))
        if val is None or tol is None:
            continue
        results.append(
            ParsedDimension(
                value=val,
                unit="mm",
                dim_type="tolerance",
                label=f"{m.group(1)}\u00b1{m.group(2)}",
                raw_text=m.group(0).strip(),
                tolerance_plus=tol,
                tolerance_minus=tol,
            ),
        )
        _consume(m.start(), m.end())

    # 4. 각도
    for m in _RE_ANGLE.finditer(cleaned):
        if _overlaps(m.start(), m.end()):
            continue
        val = _safe_float(m.group(1))
        if val is None:
            continue
        results.append(
            ParsedDimension(
                value=val,
                unit="\u00b0",
                dim_type="angle",
                label=f"{m.group(1)}\u00b0",
                raw_text=m.group(0).strip(),
            ),
        )
        _consume(m.start(), m.end())

    # 5. 단위 포함 길이
    for m in _RE_LENGTH_UNIT.finditer(cleaned):
        if _overlaps(m.start(), m.end()):
            continue
        val = _safe_float(m.group(1))
        if val is None:
            continue
        unit = m.group(2).lower()
        results.append(
            ParsedDimension(
                value=val,
                unit=unit,
                dim_type="length",
                label=f"{m.group(1)}{unit}",
                raw_text=m.group(0).strip(),
            ),
        )
        _consume(m.start(), m.end())

    # 6. 순수 숫자 (mm 가정)
    for m in _RE_PLAIN_NUMBER.finditer(cleaned):
        if _overlaps(m.start(), m.end()):
            continue
        val = _safe_float(m.group(1))
        if val is None:
            continue
        results.append(
            ParsedDimension(
                value=val,
                unit="mm",
                dim_type="length",
                label="",
                raw_text=m.group(0).strip(),
            ),
        )
        _consume(m.start(), m.end())

    # 중복 제거: (value, dim_type, label)
    seen: set[tuple[float, str, str]] = set()
    deduped: list[ParsedDimension] = []
    for d in results:
        key = (d.value, d.dim_type, d.label)
        if key not in seen:
            seen.add(key)
            deduped.append(d)

    logger.debug("치수 {}개 추출 (입력 {}자)", len(deduped), len(text))
    return deduped


# ─────────────────────────────────────────────
# 치수 비교
# ─────────────────────────────────────────────

_MATCH_TOLERANCE = 0.001  # 값 차이 이 이하면 일치로 판정


def compare_dimensions(
    dims_a: list[ParsedDimension],
    dims_b: list[ParsedDimension],
) -> DimensionDiff:
    """두 치수 목록을 비교한다.

    매칭 전략:
      1. 같은 dim_type끼리 매칭을 시도한다.
      2. 같은 타입 내에서 값이 가장 가까운 쌍을 우선 매칭한다.
      3. abs(diff) < MATCH_TOLERANCE 이면 matched (일치).
      4. 같은 타입이지만 값이 다르면 changed.
      5. 매칭되지 않은 것은 only_in_a / only_in_b.
      6. similarity = len(matched) / max(len(a), len(b)).
    """
    diff = DimensionDiff()

    if not dims_a and not dims_b:
        diff.similarity = 1.0
        return diff

    if not dims_a:
        diff.only_in_b = list(dims_b)
        diff.similarity = 0.0
        return diff

    if not dims_b:
        diff.only_in_a = list(dims_a)
        diff.similarity = 0.0
        return diff

    # 타입별 그룹화
    types_a: dict[str, list[ParsedDimension]] = {}
    types_b: dict[str, list[ParsedDimension]] = {}
    for d in dims_a:
        types_a.setdefault(d.dim_type, []).append(d)
    for d in dims_b:
        types_b.setdefault(d.dim_type, []).append(d)

    all_types = set(types_a.keys()) | set(types_b.keys())
    used_a: set[int] = set()
    used_b: set[int] = set()

    # ID 기반으로 사용 추적 (원본 리스트 인덱스)
    id_map_a = {id(d): i for i, d in enumerate(dims_a)}
    id_map_b = {id(d): i for i, d in enumerate(dims_b)}

    for dtype in all_types:
        group_a = types_a.get(dtype, [])
        group_b = types_b.get(dtype, [])

        # 사용되지 않은 것만 필터
        avail_a = [d for d in group_a if id_map_a[id(d)] not in used_a]
        avail_b = [d for d in group_b if id_map_b[id(d)] not in used_b]

        # 모든 쌍의 거리 계산 후 가장 가까운 것부터 매칭 (greedy)
        pairs: list[tuple[float, ParsedDimension, ParsedDimension]] = []
        for da in avail_a:
            for db in avail_b:
                pairs.append((abs(da.value - db.value), da, db))
        pairs.sort(key=lambda x: x[0])

        local_used_a: set[int] = set()
        local_used_b: set[int] = set()

        for dist, da, db in pairs:
            ia = id_map_a[id(da)]
            ib = id_map_b[id(db)]
            if ia in local_used_a or ib in local_used_b:
                continue
            local_used_a.add(ia)
            local_used_b.add(ib)
            used_a.add(ia)
            used_b.add(ib)

            if dist < _MATCH_TOLERANCE:
                diff.matched.append((da, db))
            else:
                diff.changed.append((da, db, da.value - db.value))

    # 매칭되지 않은 나머지
    diff.only_in_a = [d for i, d in enumerate(dims_a) if i not in used_a]
    diff.only_in_b = [d for i, d in enumerate(dims_b) if i not in used_b]

    total = max(len(dims_a), len(dims_b))
    diff.similarity = len(diff.matched) / total if total > 0 else 1.0

    logger.debug(
        "치수 비교: matched={}, changed={}, only_a={}, only_b={}, sim={:.3f}",
        len(diff.matched),
        len(diff.changed),
        len(diff.only_in_a),
        len(diff.only_in_b),
        diff.similarity,
    )
    return diff
