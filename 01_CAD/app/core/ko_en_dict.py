"""
한/영 기계 부품 동의어 사전 + 쿼리 확장기.

한글 검색 쿼리를 영문 기술 용어로 확장하여 E5 텍스트 검색 성능을 향상시킨다.
MiSUMi 카테고리 체계 + 산업 기계 부품 표준 용어 기반.
"""

from __future__ import annotations

import re
from loguru import logger


# ── 한→영 동의어 사전 ──
# key: 한글 (정규화된), value: 영문 동의어 리스트
# 카테고리명 + 일반 기계 부품 용어 + 소재/가공 용어

_KO_EN_MAP: dict[str, list[str]] = {
    # ── MiSUMi 카테고리 직접 매핑 ──
    "샤프트": ["shaft", "shafts", "axle"],
    "축": ["shaft", "shafts", "axle", "spindle"],
    "기어": ["gear", "gears", "spur gear"],
    "톱니바퀴": ["gear", "gears", "cogwheel"],
    "베어링": ["bearing", "bearings", "ball bearing"],
    "볼트": ["bolt", "bolts", "hex bolt"],
    "너트": ["nut", "nuts", "hex nut"],
    "나사": ["screw", "screws", "bolt", "fastener"],
    "와셔": ["washer", "washers", "flat washer"],
    "스프링": ["spring", "springs", "coil spring"],
    "핀": ["pin", "pins", "dowel pin"],
    "부시": ["bush", "bushing", "bushings", "sleeve"],
    "슬리브": ["sleeve", "sleeves", "bushing"],
    "커플링": ["coupling", "couplings", "coupler"],
    "풀리": ["pulley", "pulleys", "timing pulley"],
    "벨트": ["belt", "belts", "timing belt"],
    "체인": ["chain", "chains", "roller chain"],
    "스프로킷": ["sprocket", "sprockets"],
    "캠": ["cam", "cams", "cam follower"],
    "클램프": ["clamp", "clamps", "clamping"],
    "브래킷": ["bracket", "brackets", "mounting bracket"],
    "플레이트": ["plate", "plates", "base plate"],
    "블록": ["block", "blocks", "mounting block"],
    "프레임": ["frame", "frames", "aluminum frame"],
    "힌지": ["hinge", "hinges"],
    "레일": ["rail", "rails", "linear rail", "guide rail"],
    "가이드": ["guide", "guides", "linear guide"],
    "리니어": ["linear", "linear motion", "linear guide"],
    "실린더": ["cylinder", "cylinders", "pneumatic cylinder"],
    "피스톤": ["piston", "pistons"],
    "밸브": ["valve", "valves"],
    "노즐": ["nozzle", "nozzles"],
    "플랜지": ["flange", "flanges"],
    "파이프": ["pipe", "pipes", "tube"],
    "튜브": ["tube", "tubes", "pipe"],
    "호스": ["hose", "hoses"],
    "피팅": ["fitting", "fittings", "pipe fitting"],
    "조인트": ["joint", "joints", "universal joint"],
    "씰": ["seal", "seals", "oil seal", "o-ring"],
    "오링": ["o-ring", "o-rings", "seal"],
    "패킹": ["packing", "gasket", "sealing"],
    "가스켓": ["gasket", "gaskets"],
    "모터": ["motor", "motors", "servo motor"],
    "센서": ["sensor", "sensors"],
    "스위치": ["switch", "switches", "limit switch"],
    "커넥터": ["connector", "connectors"],
    "터미널": ["terminal", "terminals"],
    "히터": ["heater", "heaters"],
    "팬": ["fan", "fans", "cooling fan"],
    "필터": ["filter", "filters"],
    "컨베이어": ["conveyor", "conveyors"],
    "그리퍼": ["gripper", "grippers"],
    "액추에이터": ["actuator", "actuators"],
    "댐퍼": ["damper", "dampers", "shock absorber"],
    "롤러": ["roller", "rollers"],
    "휠": ["wheel", "wheels"],
    "캐스터": ["caster", "casters"],
    "손잡이": ["handle", "handles", "knob"],
    "노브": ["knob", "knobs"],
    "레버": ["lever", "levers"],
    "핸들": ["handle", "handles"],
    "지그": ["jig", "jigs", "fixture"],
    "치구": ["fixture", "jig", "work holding"],

    # ── 형상/특징 ──
    "구멍": ["hole", "bore", "holes"],
    "홀": ["hole", "holes", "bore"],
    "탭": ["tap", "tapped hole", "thread"],
    "나사산": ["thread", "threading", "screw thread"],
    "챔퍼": ["chamfer", "chamfers", "bevel"],
    "모따기": ["chamfer", "bevel", "fillet"],
    "필렛": ["fillet", "fillets", "radius"],
    "라운드": ["round", "fillet", "radius"],
    "슬롯": ["slot", "slots", "groove"],
    "홈": ["groove", "slot", "keyway"],
    "키홈": ["keyway", "key slot", "key groove"],
    "스플라인": ["spline", "splines"],
    "단차": ["step", "stepped", "shoulder"],
    "테이퍼": ["taper", "tapered", "conical"],

    # ── 소재 ──
    "스테인리스": ["stainless steel", "SUS", "SUS304", "SUS316"],
    "스텐": ["stainless steel", "SUS", "SUS304"],
    "알루미늄": ["aluminum", "aluminium", "AL", "A5052", "A6061"],
    "철": ["steel", "iron", "carbon steel", "SS400"],
    "강철": ["steel", "carbon steel", "alloy steel"],
    "구리": ["copper", "brass", "bronze"],
    "황동": ["brass"],
    "청동": ["bronze"],
    "티타늄": ["titanium"],
    "수지": ["resin", "plastic", "polymer"],
    "플라스틱": ["plastic", "resin", "nylon", "POM"],
    "나일론": ["nylon", "PA", "polyamide"],
    "고무": ["rubber", "elastomer"],
    "우레탄": ["urethane", "polyurethane", "PU"],

    # ── 가공/처리 ──
    "열처리": ["heat treatment", "hardening", "quenching"],
    "도금": ["plating", "coating", "chrome plating"],
    "아노다이징": ["anodizing", "anodized"],
    "연삭": ["grinding", "ground", "surface grinding"],
    "밀링": ["milling", "milled"],
    "선반": ["lathe", "turning", "turned"],
    "방전": ["EDM", "electrical discharge machining"],
    "레이저": ["laser", "laser cutting"],

    # ── 도면 관련 ──
    "도면": ["drawing", "blueprint", "technical drawing"],
    "조립도": ["assembly drawing", "assembly"],
    "부품도": ["part drawing", "detail drawing"],
    "단면도": ["section view", "cross section"],
    "평면도": ["plan view", "top view"],
    "정면도": ["front view", "elevation"],
    "측면도": ["side view", "profile view"],
    "상세도": ["detail view", "enlarged view"],
    "전개도": ["development", "unfolded view"],
    "치수": ["dimension", "dimensions", "size"],
    "공차": ["tolerance", "tolerances"],
    "표면거칠기": ["surface roughness", "Ra", "surface finish"],
}

# ── 복합어 패턴 (2어절 이상) ──
_KO_EN_COMPOUND: dict[str, list[str]] = {
    "볼 베어링": ["ball bearing"],
    "롤러 베어링": ["roller bearing"],
    "니들 베어링": ["needle bearing"],
    "테이퍼 롤러": ["tapered roller", "tapered roller bearing"],
    "리니어 가이드": ["linear guide", "linear motion guide"],
    "리니어 부시": ["linear bushing", "linear bearing"],
    "타이밍 벨트": ["timing belt"],
    "타이밍 풀리": ["timing pulley"],
    "유니버설 조인트": ["universal joint", "U-joint"],
    "볼 스크류": ["ball screw", "ball screw shaft"],
    "리드 스크류": ["lead screw"],
    "락 너트": ["lock nut", "locknut"],
    "스톱 링": ["retaining ring", "snap ring", "circlip"],
    "멈춤 링": ["retaining ring", "snap ring", "circlip"],
    "오일 씰": ["oil seal"],
    "에어 실린더": ["air cylinder", "pneumatic cylinder"],
    "서보 모터": ["servo motor"],
    "스텝 모터": ["stepper motor", "stepping motor"],
    "리미트 스위치": ["limit switch"],
    "로터리 조인트": ["rotary joint"],
    "육각 볼트": ["hex bolt", "hexagon bolt"],
    "육각 너트": ["hex nut"],
    "접시 머리": ["flat head", "countersunk"],
    "둥근 머리": ["round head", "pan head"],
    "소켓 볼트": ["socket head cap screw", "socket bolt"],
    "스프링 와셔": ["spring washer"],
    "평 와셔": ["flat washer"],
}


def expand_query(query: str) -> str:
    """한글 쿼리를 영문 동의어로 확장한다.

    Args:
        query: 원본 검색 쿼리 (예: "스테인리스 샤프트 베어링")

    Returns:
        확장된 쿼리 (예: "스테인리스 샤프트 베어링 stainless steel SUS shaft bearing")
    """
    if not query or not query.strip():
        return query

    additions: list[str] = []
    query_lower = query.lower().strip()

    # 1) 복합어 매칭 (긴 것 우선)
    matched_ranges: list[tuple[int, int]] = []
    for ko, en_list in sorted(_KO_EN_COMPOUND.items(), key=lambda x: -len(x[0])):
        idx = query_lower.find(ko.lower())
        if idx >= 0:
            # 이미 매칭된 범위와 겹치지 않는지 확인
            end = idx + len(ko)
            overlap = any(
                not (end <= ms or idx >= me)
                for ms, me in matched_ranges
            )
            if not overlap:
                matched_ranges.append((idx, end))
                additions.extend(en_list)

    # 2) 단일어 매칭
    for ko, en_list in _KO_EN_MAP.items():
        if ko in query_lower:
            # 복합어에서 이미 매칭된 범위인지 확인
            idx = query_lower.find(ko)
            end = idx + len(ko)
            overlap = any(
                idx >= ms and end <= me
                for ms, me in matched_ranges
            )
            if not overlap:
                additions.extend(en_list)

    if not additions:
        return query

    # 중복 제거 (순서 유지)
    seen: set[str] = set()
    unique: list[str] = []
    for a in additions:
        a_lower = a.lower()
        if a_lower not in seen:
            seen.add(a_lower)
            unique.append(a)

    expanded = f"{query} {' '.join(unique)}"
    logger.debug(f"쿼리 확장: '{query}' → '{expanded}'")
    return expanded


def get_expansions(query: str) -> list[str]:
    """확장된 영문 단어 리스트만 반환한다 (UI 뱃지 표시용).

    expand_query()와 동일한 로직이지만 원본 쿼리 없이
    추가된 영문 단어 리스트만 반환합니다.

    Args:
        query: 원본 검색 쿼리

    Returns:
        확장된 영문 단어 리스트 (중복 제거됨)
        예: ["shaft", "axle", "stainless steel", "SUS"]
    """
    if not query or not query.strip():
        return []

    additions: list[str] = []
    query_lower = query.lower().strip()

    # 1) 복합어 매칭
    matched_ranges: list[tuple[int, int]] = []
    for ko, en_list in sorted(
        _KO_EN_COMPOUND.items(), key=lambda x: -len(x[0])
    ):
        idx = query_lower.find(ko.lower())
        if idx >= 0:
            end = idx + len(ko)
            overlap = any(
                not (end <= ms or idx >= me) for ms, me in matched_ranges
            )
            if not overlap:
                matched_ranges.append((idx, end))
                additions.extend(en_list)

    # 2) 단일어 매칭
    for ko, en_list in _KO_EN_MAP.items():
        if ko in query_lower:
            idx = query_lower.find(ko)
            end = idx + len(ko)
            overlap = any(
                idx >= ms and end <= me for ms, me in matched_ranges
            )
            if not overlap:
                additions.extend(en_list)

    if not additions:
        return []

    # 중복 제거
    seen: set[str] = set()
    unique: list[str] = []
    for a in additions:
        a_lower = a.lower()
        if a_lower not in seen:
            seen.add(a_lower)
            unique.append(a)

    return unique
