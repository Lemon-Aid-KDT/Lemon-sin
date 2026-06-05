"""selectstar per-image 분류 청크 집계 -> 클린 per-class 하베스트 + 누락 감지(gap-fill용).

usage: python _harvest_ss_clean.py <chunk1.output> <chunk2.output> <chunk3.output> ...
"""
import sys
import csv
import glob
import json
import os
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SS = Path(r"C:\Lemon-sin\data\food_images\raw\selectstar")
OUTDIR = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review")
RELEVANT = [
    "jajangmyeon", "baguette", "bulgogi", "cake", "curry", "dim_sum", "chicken", "burger",
    "ramen", "kimchi_stew", "pasta", "pizza", "rice_noodle", "salad", "sandwich",
    "korean_pancake", "gimbap", "sushi", "takoyaki", "tteokbokki", "udon", "soup",
    "pound_cake", "nasi_goreng", "seaweed_soup", "bibimbap", "sashimi", "banh_mi",
    "croissant", "caprese", "croque_monsieur", "BBQ", "galbi", "steak", "soba",
]
MINED = ["grilled-beef", "grilled-pork-belly", "barbecue-ribs"]

# 기대 ID 집합 (누락 감지)
expected = set()
for f in RELEVANT:
    for p in glob.glob(str(SS / f / "png" / "*.png")):
        b = os.path.basename(p)
        if not b.startswith("._"):
            expected.add(f"{f}/{b}")

rows = []
for path in sys.argv[1:]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    rows += d["result"]["rows"]

seen = {r["file"]: r for r in rows}  # 파일 단위 dedup
missing = sorted(expected - set(seen))
print(f"기대 {len(expected)} / 라벨 {len(seen)} / 누락 {len(missing)}")
if missing:
    (OUTDIR / "_ssclassify_missing.txt").write_text("\n".join(missing) + "\n", encoding="utf-8")
    print(f"  -> 누락 목록 _ssclassify_missing.txt (gap-fill 대상)")

mapped = [r for r in seen.values() if r.get("cls") not in ("none", "", None)]
clean = [r for r in mapped if r.get("conf") in ("high", "medium")]
bycls = defaultdict(list)
conf_split = defaultdict(lambda: [0, 0])
for r in clean:
    bycls[r["cls"]].append(r["file"])
    conf_split[r["cls"]][0 if r["conf"] == "high" else 1] += 1

with (OUTDIR / "ss_harvest_clean_list.tsv").open("w", encoding="utf-8") as f:
    for cls in bycls:
        for fl in bycls[cls]:
            f.write(f"{cls}\t{fl}\n")
with (OUTDIR / "ss_harvest_by_class.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["taxo59_class", "n_clean", "n_high", "n_med"])
    for cls in sorted(bycls, key=lambda c: -len(bycls[c])):
        h, m = conf_split[cls]
        w.writerow([cls, len(bycls[cls]), h, m])

print(f"\nmapped {len(mapped)} / clean(high+med) {len(clean)} / 보유 클래스 {len(bycls)}/59")
print(f"채굴(OOD폴더서 건진) 성과: " + ", ".join(f"{c}={len(bycls.get(c,[]))}" for c in MINED))
print("\n클래스별 클린 장수:")
for cls in sorted(bycls, key=lambda c: -len(bycls[c])):
    h, m = conf_split[cls]
    print(f"  {cls:22s} {len(bycls[cls]):4d}  (h{h}/m{m})")
