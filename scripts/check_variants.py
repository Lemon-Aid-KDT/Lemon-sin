# -*- coding: utf-8 -*-
"""nutrition_map_enriched.json 변형 검증 — 매핑 품질 확인용."""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

p = Path(__file__).with_name("nutrition_map_enriched.json")
nut = json.loads(p.read_text(encoding="utf-8"))

# 전체 통계
total = len(nut)
with_var = sum(1 for v in nut.values() if v.get("variants"))
total_var = sum(len(v.get("variants", [])) for v in nut.values())
avg = total_var / max(1, with_var)
print(f"=== 전체 통계 ===")
print(f"  총 코드      : {total}")
print(f"  변형 있는 코드: {with_var}")
print(f"  총 변형 항목  : {total_var}")
print(f"  코드당 평균  : {avg:.1f}")
print()

# 변형 가장 많은 top 10
top = sorted(
    [(c, v.get("name_ko", "?"), len(v.get("variants", [])))
     for c, v in nut.items()],
    key=lambda x: -x[2])[:10]
print(f"=== 변형 많은 top 10 ===")
for code, name, vc in top:
    print(f"  {code} ({name:12s}): {vc}개")
print()

# 검증 — 4가지 음식 변형 풀 출력
samples = [
    ("06012005", "불고기"),
    ("04019001", "김치찌개"),
    ("01014004", "비빔밥"),
    ("08014001", "떡볶이"),
]
for code, expected_name in samples:
    v = nut.get(code)
    if not v:
        print(f"--- {code} ({expected_name}): 없음 ---")
        continue
    actual = v.get("name_ko", "?")
    variants = v.get("variants", [])
    print(f"=== {code} = {actual} (변형 {len(variants)}개) ===")
    for var in variants[:15]:
        print(f"  {var.get('label', '?'):25s} = {var.get('name', '?')}")
    if len(variants) > 15:
        print(f"  ... 외 {len(variants) - 15}개")
    print()
