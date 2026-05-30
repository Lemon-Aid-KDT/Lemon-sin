"""exp06 taxonomy v2 매핑 조립: 424코드 -> 최종 클래스.

기본 = orig_roboflow_class. 아래 OVERRIDE로 분할/이동/드롭 반영.
중간 스코프: 오염 정리 전부 + soup/ramen/떡볶이/pork-cutlet 외형분할
+ 앞서 승인한 seafood-stew/noodle-soup/stew/짬뽕 분할.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_split")
OUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\exp06_taxonomy_v2_mapping.csv")

j = json.load(open(ROOT / "yolo_class_index_split.json", encoding="utf-8"))
a2c = j["aihub_to_class"]  # code -> {new_index, korean_name, orig_roboflow_class}
counts = {int(r["class_id"]): (int(r["train_count"]), int(r["val_count"]))
          for r in csv.DictReader(open(ROOT / "_audit" / "class_counts.csv", encoding="utf-8"))}


def grp(name: str, codes: list[str]) -> dict[str, str]:
    return {c: name for c in codes}


OVERRIDE: dict[str, str] = {}
# --- soup 분할 (+ 양식수프 분리) ---
OVERRIDE |= grp("양식수프", ["C04001", "C04003", "C04005", "C04002", "C04004"])
OVERRIDE |= grp("한식맑은국", ["A13030", "A13017", "A13042", "A13004", "A13041", "A13038",
                            "A13043", "A13044", "A13049", "B12063", "B12070"])
OVERRIDE |= grp("한식빨간국", ["A13040", "A13021", "B12111", "B12114", "B12041", "B12123"])
# --- ramen 분할 ---
OVERRIDE |= grp("일본라멘", ["A14086", "A14052", "A14114", "A14084", "A14027"])
OVERRIDE |= grp("한국라면(빨간)", ["B12062", "B12068", "B12166"])
OVERRIDE |= grp("냉라멘", ["A14024"])
# --- 떡볶이 분할 ---
OVERRIDE |= grp("떡볶이(빨간)", ["B11009", "B11096", "B11103", "B11048", "B11038", "B11087"])
OVERRIDE |= grp("떡볶이(크림로제)", ["B11013", "B11119", "B11036", "B11117"])
OVERRIDE |= grp("떡볶이(자장)", ["B11090"])
# --- 돈가스 분할 ---
OVERRIDE |= grp("돈가스(마른)", ["A14034", "A14151", "B12013", "B12015", "B12163"])
OVERRIDE |= grp("돈가스(소스국물)", ["A14126", "A14127", "B11035"])
# --- 앞서 승인: seafood-stew ---
OVERRIDE |= grp("해물매운탕", ["B12021", "B12124", "A13023", "B12165"])
OVERRIDE |= grp("해물맑은탕", ["A13037", "A13036", "A14146", "A13009"])
OVERRIDE |= grp("해물찜", ["A13048", "A13008"])
# --- noodle-soup ---
OVERRIDE |= grp("칼국수", ["A13034", "B12161", "B12150", "B12117", "B12087"])
OVERRIDE |= grp("쌀국수", ["A14025", "A14047", "A14083", "A14094", "A14032", "A14148",
                        "A14043", "A14082", "A14064", "A14085", "A14112"])
OVERRIDE |= grp("국수일반", ["A13029", "A13024", "B12075", "B12016"])
# --- stew ---
OVERRIDE |= grp("찌개류(붉은)", ["B12032", "B12027", "B12167", "A13045"])
OVERRIDE |= grp("된장찌개", ["B12138"])
# --- 짬뽕 (A14110 기본 i=짬뽕) ---
OVERRIDE |= grp("짬뽕", ["B11016", "B11097", "B12110", "B11092", "A14110"])
OVERRIDE |= grp("나가사끼짬뽕", ["A14018"])
# --- 교차-카테고리 오염 이동 ---
OVERRIDE["B12005"] = "한식맑은국"      # 갈비탕 (hot-pot->soup clear)
OVERRIDE["B12086"] = "된장찌개"        # 바지락된장국 (사용자: 된장찌개와 합침)
OVERRIDE["A14150"] = "raw-fish"        # 훈제연어덮밥
OVERRIDE["B12120"] = "raw-fish"        # 연어회덮밥
OVERRIDE["C02122"] = "돈가스(마른)"     # 카레고로케 (fried croquette)
OVERRIDE["B12097"] = "savory-pancake"  # 빈대떡 (전/부침개)
# --- 보류/드롭 (exp06 제외) ---
OVERRIDE["A14111"] = "_DROP"           # 짬뽕차돌쌀국수 (사용자: 다시 제외)
OVERRIDE["A13020"] = "_DROP"           # 소라숙회 (익힌 것)

rows = []
agg = defaultdict(lambda: [0, 0, 0])  # final_class -> [codes, train, val]
for code, v in a2c.items():
    idx = v["new_index"]
    tr, va = counts.get(idx, (0, 0))
    final = OVERRIDE.get(code, v["orig_roboflow_class"])
    rows.append({"aihub_code": code, "korean_name": v["korean_name"],
                 "orig_class": v["orig_roboflow_class"], "final_class": final,
                 "train": tr, "val": va})
    agg[final][0] += 1
    agg[final][1] += tr
    agg[final][2] += va

rows.sort(key=lambda r: (r["final_class"], -r["train"]))
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["final_class", "aihub_code", "korean_name", "orig_class", "train", "val"])
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in ["final_class", "aihub_code", "korean_name", "orig_class", "train", "val"]})

n_classes = len([k for k in agg if k != "_DROP"])
print(f"WROTE {OUT}")
print(f"최종 클래스 수: {n_classes}  (+ _DROP {agg['_DROP'][0]}코드 제외)")
print(f"{'class':28s}{'codes':>6s}{'train':>8s}{'val':>6s}  flag")
changed = {"양식수프", "한식맑은국", "한식빨간국", "일본라멘", "한국라면(빨간)", "냉라멘",
           "떡볶이(빨간)", "떡볶이(크림로제)", "떡볶이(자장)", "돈가스(마른)", "돈가스(소스국물)",
           "해물매운탕", "해물맑은탕", "해물찜", "칼국수", "쌀국수", "국수일반",
           "찌개류(붉은)", "된장찌개", "짬뽕", "나가사끼짬뽕"}
for k in sorted(agg, key=lambda k: (k == "_DROP", -agg[k][1])):
    n, tr, va = agg[k]
    flag = ""
    if k == "_DROP":
        flag = "(제외)"
    elif va == 0:
        flag = "🔴val0"
    elif va < 15:
        flag = "⚠️val<15"
    star = "*" if k in changed else " "
    print(f"{star}{k:27s}{n:6d}{tr:8d}{va:6d}  {flag}")
