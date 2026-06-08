"""iso11_B_both 를 '수량매칭' 버전으로 재빌드 (수량 교란 제거).

B_eq: 클래스별 총량 = A(AIHub)와 동일, 단 절반은 AIHub·절반은 selectstar.
  per-class: na = A_count//2 (AIHub), ns = A_count - na (selectstar)
  => B_eq 총량 ≈ A(10,210), 소스 50/50. A vs B = '같은 양에서 절반을 ss로' 순수 비교.
A는 그대로(iso11_A_aihub), 이 스크립트는 iso11_B_both 만 덮어씀.
"""
from __future__ import annotations
import glob, os, shutil
from collections import defaultdict
from pathlib import Path
import yaml

NAMES11 = ["takoyaki", "black-bean-noodles", "udon", "bulgogi", "dim-sum",
           "japanese-ramen", "savory-pancake", "jjigae-red", "raw-fish",
           "rice-noodle-soup", "mixed-rice-bowl"]
BAL = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500")
EXP13 = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_exp13_selectstar")
DSTB = Path(r"C:\Lemon-sin\data\food_images\processed\iso11_B_both")

names59 = yaml.safe_load((BAL / "data.yaml").read_text(encoding="utf-8"))["names"]
names59 = names59 if isinstance(names59, list) else [names59[i] for i in sorted(names59)]
old2new = {names59.index(n): i for i, n in enumerate(NAMES11)}


def hardlink(src, dst):
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def remap(lines):
    out = [f"{old2new[int(p[0])]} {' '.join(p[1:])}" for p in (ln.split() for ln in lines)
           if p and int(p[0]) in old2new]
    return out or None


def collect_by_class(root, split, prefix):
    byc = defaultdict(list)
    for lf in sorted(glob.glob(str(root / split / "labels" / "*.txt"))):
        stem = os.path.basename(lf)[:-4]
        if prefix and not stem.startswith(prefix):
            continue
        new = remap(Path(lf).read_text().splitlines())
        if new is None:
            continue
        img = next((root / split / "images" / f"{stem}{e}" for e in (".jpg", ".png")
                    if (root / split / "images" / f"{stem}{e}").exists()), None)
        if img:
            byc[int(new[0].split()[0])].append((stem, img, new))
    return byc


aih = collect_by_class(BAL, "train", "train_")
ss = collect_by_class(EXP13, "train", "ss_")
val_items = []
for lf in sorted(glob.glob(str(BAL / "val" / "labels" / "*.txt"))):
    stem = os.path.basename(lf)[:-4]
    new = remap(Path(lf).read_text().splitlines())
    if new is None:
        continue
    img = next((BAL / "val" / "images" / f"{stem}{e}" for e in (".jpg", ".png")
                if (BAL / "val" / "images" / f"{stem}{e}").exists()), None)
    if img:
        val_items.append((stem, img, new))

# B_eq 구성: per-class 총량 = A_count, na=//2 AIHub, ns=나머지 selectstar
train_items = []
na_tot = ns_tot = 0
print(f"{'class':20s} {'A_cnt':>5s} {'AIHub':>5s} {'ss':>4s}")
for c in range(11):
    a = aih.get(c, []); s = ss.get(c, [])
    n = len(a); na = n // 2; ns = n - na
    ns = min(ns, len(s))  # ss 가용 한도(800)
    train_items += a[:na] + s[:ns]
    na_tot += na; ns_tot += ns
    print(f"  {NAMES11[c]:20s} {n:5d} {na:5d} {ns:4d}")

# 덮어쓰기
if DSTB.exists():
    shutil.rmtree(DSTB)
for split, items in (("train", train_items), ("val", val_items)):
    (DSTB / split / "images").mkdir(parents=True, exist_ok=True)
    (DSTB / split / "labels").mkdir(parents=True, exist_ok=True)
    for stem, img, lines in items:
        hardlink(str(img), DSTB / split / "images" / img.name)
        (DSTB / split / "labels" / f"{stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
block = "\n".join(f"  {i}: {n}" for i, n in enumerate(NAMES11))
(DSTB / "data.yaml").write_text(
    f"path: {DSTB.as_posix()}\ntrain: train/images\nval: val/images\nnc: 11\nnames:\n{block}\n", encoding="utf-8")
print(f"\n[B_eq] iso11_B_both 재빌드: train {len(train_items)} (AIHub {na_tot} + ss {ns_tot}) / val {len(val_items)}")
print(f"  → A(10210)와 수량매칭, 소스 {na_tot/(na_tot+ns_tot)*100:.0f}% AIHub / {ns_tot/(na_tot+ns_tot)*100:.0f}% ss")
