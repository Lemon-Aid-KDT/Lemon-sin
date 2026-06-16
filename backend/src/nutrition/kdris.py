"""KDRIs 룩업 모듈.

CSV로 디지털화한 한국인 영양소 섭취기준(KDRIs)을 메모리에 로드하여 사용자
프로필(나이·성별·임신·수유부)에 맞는 권장 섭취량을 조회한다.

기본 데이터 경로는 실행 위치(CWD)에 의존하지 않도록 이 파일 기준 프로젝트
루트에서 해석한다.

Reference:
    docs/dev-guides/05-kdris-lookup.md
    data/kdris/kdris_2020.csv
"""

from __future__ import annotations

import csv
import logging
from functools import lru_cache
from pathlib import Path
from typing import Final

from src.models.schemas.nutrition import KDRIsValue, UserKDRIsContext

logger = logging.getLogger(__name__)

_PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
"""프로젝트 루트 (backend/src/nutrition/kdris.py 기준 3단계 상위)."""

DEFAULT_KDRIS_PATH: Final[Path] = _PROJECT_ROOT / "data" / "kdris" / "kdris_2020.csv"
"""기본 KDRIs CSV 경로."""

_REQUIRED_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "code",
        "name_ko",
        "name_en",
        "unit",
        "sex",
        "age_min",
        "age_max",
        "rda",
        "ai",
        "ear",
        "ul",
        "is_pregnant",
        "is_lactating",
    }
)
"""KDRIs CSV가 가져야 하는 필수 컬럼."""


def _parse_optional_float(value: str) -> float | None:
    """빈 문자열은 None, 그 외에는 float로 변환한다.

    Args:
        value: CSV 셀 문자열.

    Returns:
        변환된 float, 또는 빈 셀이면 None.
    """
    value = value.strip()
    return float(value) if value else None


def _parse_optional_int(value: str) -> int | None:
    """빈 문자열은 None, 그 외에는 int로 변환한다.

    Args:
        value: CSV 셀 문자열.

    Returns:
        변환된 int, 또는 빈 셀이면 None.
    """
    value = value.strip()
    return int(value) if value else None


def _is_true(value: str) -> bool:
    """CSV의 boolean 셀("true"/"false")을 bool로 변환한다.

    Args:
        value: CSV 셀 문자열.

    Returns:
        대소문자 무시 "true"이면 True, 그 외 False.
    """
    return value.strip().lower() == "true"


def load_kdris_csv(path: Path = DEFAULT_KDRIS_PATH) -> list[dict[str, str]]:
    """KDRIs CSV를 로드하여 행 dict 리스트로 반환한다.

    Args:
        path: CSV 파일 경로.

    Returns:
        각 행을 ``dict[str, str]``로 변환한 리스트 (빈 셀은 빈 문자열).

    Raises:
        FileNotFoundError: 파일이 없는 경우.
        ValueError: CSV가 비었거나 필수 컬럼이 누락된 경우.

    Examples:
        >>> rows = load_kdris_csv()
        >>> rows[0]["code"]
        'energy_kcal'
    """
    if not path.exists():
        raise FileNotFoundError(f"KDRIs CSV not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        missing = _REQUIRED_COLUMNS - set(fieldnames)
        if missing:
            raise ValueError(f"KDRIs CSV missing columns: {sorted(missing)} in {path}")
        rows: list[dict[str, str]] = [
            {key: value if isinstance(value, str) else "" for key, value in row.items()}
            for row in reader
        ]

    if not rows:
        raise ValueError(f"KDRIs CSV is empty: {path}")

    logger.info("Loaded %d KDRIs rows from %s", len(rows), path)
    return rows


def lookup_kdris_for_user(
    nutrient_code: str,
    user: UserKDRIsContext,
    rows: list[dict[str, str]] | None = None,
) -> KDRIsValue | None:
    """사용자 컨텍스트에 맞는 KDRIs 값을 조회한다.

    매칭 우선순위:
        1. 임신부 행 (여성 + is_pregnant).
        2. 수유부 행 (여성 + is_lactating).
        3. 성별 + 연령 범위 행 (임신·수유 행 제외).
        4. 성별 "all" + 연령 범위 행.

    임신·수유 전용 행이 없는 영양소는 일반 성별·연령 행으로 폴백된다.

    Args:
        nutrient_code: 영양소 코드 (예: "vitamin_c_mg").
        user: 사용자 컨텍스트.
        rows: 미리 로드한 행 리스트. None이면 기본 경로에서 로드(캐시).

    Returns:
        매칭된 KDRIsValue, 또는 매칭 실패 시 None.

    Raises:
        FileNotFoundError: rows=None인데 기본 CSV가 없는 경우.

    Examples:
        >>> user = UserKDRIsContext(age=50, sex="female")
        >>> result = lookup_kdris_for_user("calcium_mg", user)
        >>> result.rda
        800.0
    """
    if rows is None:
        rows = _load_default_kdris()

    candidates = [row for row in rows if row["code"] == nutrient_code]
    if not candidates:
        logger.warning("No KDRIs rows for nutrient=%s", nutrient_code)
        return None

    if user.sex == "female" and user.is_pregnant:
        special = _find_special_row(candidates, flag="is_pregnant")
        if special is not None:
            return _row_to_kdris_value(special)

    if user.sex == "female" and user.is_lactating:
        special = _find_special_row(candidates, flag="is_lactating")
        if special is not None:
            return _row_to_kdris_value(special)

    for row in candidates:
        if row["sex"] not in (user.sex, "all"):
            continue
        if _is_true(row["is_pregnant"]) or _is_true(row["is_lactating"]):
            continue  # 임신·수유 행은 위 분기에서만 사용
        age_min = _parse_optional_int(row["age_min"])
        age_max = _parse_optional_int(row["age_max"])
        if age_min is None or age_max is None:
            continue
        if age_min <= user.age <= age_max:
            return _row_to_kdris_value(row)

    logger.warning(
        "No KDRIs match for nutrient=%s, age=%d, sex=%s",
        nutrient_code,
        user.age,
        user.sex,
    )
    return None


def _find_special_row(
    candidates: list[dict[str, str]],
    *,
    flag: str,
) -> dict[str, str] | None:
    """후보 행에서 임신부/수유부 플래그가 켜진 여성 행을 찾는다.

    Args:
        candidates: 같은 영양소 코드의 행 리스트.
        flag: "is_pregnant" 또는 "is_lactating".

    Returns:
        첫 매칭 행, 없으면 None.
    """
    for row in candidates:
        if row["sex"] == "female" and _is_true(row[flag]):
            return row
    return None


def _row_to_kdris_value(row: dict[str, str]) -> KDRIsValue:
    """CSV 행을 KDRIsValue로 변환한다.

    Args:
        row: KDRIs CSV 단일 행.

    Returns:
        변환된 KDRIsValue.
    """
    return KDRIsValue(
        code=row["code"],
        name_ko=row["name_ko"],
        name_en=row["name_en"],
        unit=row["unit"],
        rda=_parse_optional_float(row["rda"]),
        ai=_parse_optional_float(row["ai"]),
        ear=_parse_optional_float(row["ear"]),
        ul=_parse_optional_float(row["ul"]),
    )


@lru_cache(maxsize=1)
def _load_default_kdris() -> list[dict[str, str]]:
    """기본 경로에서 KDRIs를 1회만 로드한다 (캐시).

    Returns:
        KDRIs 행 리스트.

    Raises:
        FileNotFoundError: 기본 CSV가 없는 경우.
    """
    return load_kdris_csv()
