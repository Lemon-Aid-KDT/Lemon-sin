"""
카테고리별 특화 LLM 프롬프트.

YOLO 분류 결과(Top-1)를 기반으로 해당 부품 유형에 최적화된
분석 지시문을 생성한다. 범용 프롬프트 대비 정확도 대폭 향상.
"""

from __future__ import annotations


# ── 카테고리별 특화 지시문 ──
# key: YOLO 카테고리명 (또는 그 패턴), value: 부품 유형 설명 + 분석 포인트

_CATEGORY_HINTS: dict[str, str] = {
    # ── 축/샤프트 ──
    "Shafts": """This is a SHAFT (축) drawing. Focus on:
- Shaft diameter steps and transitions
- Keyway slots, spline, D-cut, or flat sections
- Thread specifications (M-thread at shaft ends)
- Surface finish requirements (grinding marks)
- Bearing seat diameters and tolerance classes (h6, g6, etc.)
- Chamfers and fillets at diameter transitions
- Total length and individual section lengths""",

    # ── 기어 ──
    "Gears": """This is a GEAR (기어) drawing. Focus on:
- Number of teeth, module, pressure angle
- Pitch circle diameter (PCD)
- Face width, hub dimensions
- Bore diameter and keyway
- Tooth profile (spur, helical, bevel, worm)
- Surface hardness specification (HRC)
- Gear quality grade (JIS/AGMA/DIN)""",

    # ── 베어링 ──
    "Bearings": """This is a BEARING (베어링) drawing. Focus on:
- Bearing type (ball, roller, needle, thrust)
- Inner/outer diameter and width
- Bearing designation number (e.g., 6205, 7010)
- Seal/shield type
- Load rating and speed rating
- Preload or clearance specification""",

    # ── 볼트/나사 ──
    "Bolts": """This is a BOLT/SCREW (볼트/나사) drawing. Focus on:
- Thread specification (M-thread, pitch)
- Head type (hex, socket, countersunk, pan)
- Total length and thread length
- Material grade (8.8, 10.9, A2-70)
- Surface treatment (zinc, black oxide)
- Drive type (hex, Phillips, Torx)""",

    # ── 너트 ──
    "Nuts": """This is a NUT (너트) drawing. Focus on:
- Thread specification and pitch
- Nut type (hex, lock, flange, cap)
- Width across flats and height
- Material grade
- Locking mechanism if any""",

    # ── 와셔 ──
    "Washers": """This is a WASHER (와셔) drawing. Focus on:
- Inner/outer diameter and thickness
- Washer type (flat, spring, belleville, wave)
- Material specification
- Surface treatment""",

    # ── 스프링 ──
    "Springs": """This is a SPRING (스프링) drawing. Focus on:
- Spring type (compression, tension, torsion)
- Wire diameter, coil outer/inner diameter
- Free length, solid height
- Number of active coils and total coils
- Spring rate (N/mm)
- End type (closed, ground)
- Material (SWP, SUS, piano wire)""",

    # ── 핀 ──
    "Pins": """This is a PIN (핀) drawing. Focus on:
- Pin type (dowel, taper, split, spring)
- Diameter and length
- Material and hardness
- Tolerance class (m6, h7)""",

    # ── 부시/슬리브 ──
    "Bushings": """This is a BUSHING/SLEEVE (부시/슬리브) drawing. Focus on:
- Inner and outer diameter
- Length/width
- Material (bronze, oilite, plastic)
- Flange dimensions if flanged
- Oil grooves or lubrication features""",

    # ── 커플링 ──
    "Couplings": """This is a COUPLING (커플링) drawing. Focus on:
- Coupling type (jaw, beam, oldham, disc)
- Bore sizes (both sides)
- Outer diameter and length
- Keyway specifications
- Torque rating
- Misalignment compensation""",

    # ── 풀리 ──
    "Pulleys": """This is a PULLEY (풀리) drawing. Focus on:
- Pulley type (V-belt, timing, flat)
- Pitch diameter and outer diameter
- Number of grooves
- Belt profile (HTD, GT2, etc.)
- Bore and keyway
- Flange details""",

    # ── 플레이트/브래킷 ──
    "Plates": """This is a PLATE/BRACKET (플레이트/브래킷) drawing. Focus on:
- Overall dimensions (length x width x thickness)
- Hole pattern (PCD, spacing)
- Hole sizes and types (through, tapped, counterbored)
- Cutouts, slots, or pockets
- Material and surface treatment
- Bend lines if sheet metal""",

    # ── 가이드/레일 ──
    "Linear_Guides": """This is a LINEAR GUIDE/RAIL (리니어 가이드) drawing. Focus on:
- Rail cross-section profile
- Rail length and mounting hole pattern
- Carriage/block dimensions
- Preload class
- Accuracy grade""",

    # ── 실린더 ──
    "Cylinders": """This is a CYLINDER (실린더) drawing. Focus on:
- Cylinder type (pneumatic, hydraulic)
- Bore size and stroke length
- Rod diameter
- Mounting style (foot, flange, clevis)
- Port thread specification""",
}

# ── 범용 패턴 매칭 (카테고리명에 키워드가 포함된 경우) ──
_PATTERN_HINTS: dict[str, str] = {
    "shaft": _CATEGORY_HINTS["Shafts"],
    "gear": _CATEGORY_HINTS["Gears"],
    "bearing": _CATEGORY_HINTS["Bearings"],
    "bolt": _CATEGORY_HINTS["Bolts"],
    "screw": _CATEGORY_HINTS["Bolts"],
    "nut": _CATEGORY_HINTS["Nuts"],
    "washer": _CATEGORY_HINTS["Washers"],
    "spring": _CATEGORY_HINTS["Springs"],
    "pin": _CATEGORY_HINTS["Pins"],
    "bush": _CATEGORY_HINTS["Bushings"],
    "sleeve": _CATEGORY_HINTS["Bushings"],
    "coupling": _CATEGORY_HINTS["Couplings"],
    "pulley": _CATEGORY_HINTS["Pulleys"],
    "plate": _CATEGORY_HINTS["Plates"],
    "bracket": _CATEGORY_HINTS["Plates"],
    "guide": _CATEGORY_HINTS["Linear_Guides"],
    "rail": _CATEGORY_HINTS["Linear_Guides"],
    "linear": _CATEGORY_HINTS["Linear_Guides"],
    "cylinder": _CATEGORY_HINTS["Cylinders"],
}


def get_category_prompt(category: str, confidence: float = 0.0) -> str:
    """YOLO 카테고리에 맞는 특화 프롬프트 섹션을 반환.

    Args:
        category: YOLO 분류 카테고리명
        confidence: 분류 신뢰도 (0.0~1.0)

    Returns:
        카테고리 특화 지시문. 매칭 안 되면 빈 문자열.
    """
    if not category:
        return ""

    # 1) 정확한 카테고리명 매칭
    if category in _CATEGORY_HINTS:
        hint = _CATEGORY_HINTS[category]
        conf_label = "HIGH" if confidence >= 0.8 else "MEDIUM" if confidence >= 0.5 else "LOW"
        return (
            f"\n=== CATEGORY-SPECIFIC ANALYSIS GUIDE (YOLO: {category}, confidence: {conf_label}) ===\n"
            f"{hint}\n"
            f"=== END CATEGORY GUIDE ===\n"
        )

    # 2) 패턴 매칭 (카테고리명의 언더스코어/공백 제거 후 소문자 비교)
    cat_lower = category.lower().replace("_", " ")
    for pattern, hint in _PATTERN_HINTS.items():
        if pattern in cat_lower:
            conf_label = "HIGH" if confidence >= 0.8 else "MEDIUM" if confidence >= 0.5 else "LOW"
            return (
                f"\n=== CATEGORY-SPECIFIC ANALYSIS GUIDE (YOLO: {category}, confidence: {conf_label}) ===\n"
                f"{hint}\n"
                f"=== END CATEGORY GUIDE ===\n"
            )

    return ""


def build_yolo_correction_directive(
    category: str, confidence: float, top_k: list[tuple[str, float]] | None = None,
) -> str:
    """YOLO 교정 지시문. 높은 신뢰도일 때 LLM이 모순하지 않도록 강제.

    Returns:
        교정 지시문 문자열.
    """
    if not category or confidence < 0.5:
        return ""

    parts = []
    if confidence >= 0.8:
        parts.append(
            f"\n**IMPORTANT**: The automated YOLO classifier identified this as "
            f"'{category}' with {confidence:.0%} confidence. "
            f"This classification is highly reliable. "
            f"Do NOT contradict this classification unless you see clear visual evidence otherwise. "
            f"If you agree, confirm it. If you disagree, explain specifically what you see that differs."
        )
    elif confidence >= 0.5:
        parts.append(
            f"\n**Note**: The automated classifier suggests this is '{category}' "
            f"({confidence:.0%} confidence). "
            f"Verify this classification based on the image. "
            f"If it seems incorrect, suggest the correct category."
        )

    if top_k and len(top_k) > 1:
        alt = ", ".join(f"{c}({s:.0%})" for c, s in top_k[1:4])
        parts.append(f"Alternative candidates: {alt}")

    return "\n".join(parts)
