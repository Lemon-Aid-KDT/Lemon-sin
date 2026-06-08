"""11클래스 격리 실험(exp17) 데이터셋 빌드 — A/B/C 3-arm.

11클래스(exp13 selectstar 보강 대상)만 떼서 3가지 학습셋 구성:
  A = AIHub만        (iso11_A_aihub)
  B = AIHub+selectstar (iso11_B_both)   ← B = A ∪ C
  C = selectstar만    (iso11_C_ss)
공통 val = AIHub val(11클래스). selectstar는 exp13에 이미 박싱됨(ss_*).
목적: A vs C = AIHub/selectstar 중 wild 전이 우위 / B = 합성효과 / vs exp13 = 격리효과.
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
OUT = Path(r"C:\Lemon-sin\data\food_images\processed")
DST = {"A": OUT / "iso11_A_aihub", "B": OUT / "iso11_B_both", "C": OUT / "iso11_C_ss"}

names59 = yaml.safe_load((BAL / "data.yaml").read_text(encoding="utf-8"))["names"]
names59 = names59 if isinstance(names59, list) else [names59[i] for i in sorted(names59)]
old2new = {names59.index(n): i for i, n in enumerate(NAMES11)}  # taxo59 idx -> 0..10
CLS11 = set(old2new)
print(f"11클래스 taxo59 인덱스: {sorted(CLS11)}")


def hardlink(src, dst):
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def remap(lines):
    out = []
    for ln in lines:
        p = ln.split()
        if p and int(p[0]) in old2new:
            out.append(f"{old2new[int(p[0])]} {' '.join(p[1:])}")
    return out or None


def collect(src_root, split, only_prefix=None):
    """(stem, img_path, new_label_lines) 리스트. only_prefix로 train_/ss_ 필터."""
    items = []
    for lf in glob.glob(str(src_root / split / "labels" / "*.txt")):
        stem = os.path.basename(lf)[:-4]
        if only_prefix and not stem.startswith(only_prefix):
            continue
        new = remap(Path(lf).read_text().splitlines())
        if new is None:
            continue
        img = None
        for ext in (".jpg", ".png"):
            c = src_root / split / "images" / f"{stem}{ext}"
            if c.exists():
                img = c; break
        if img:
            items.append((stem, img, new))
    return items


def write(dst, train_items, val_items):
    if dst.exists():
        shutil.rmtree(dst)
    for split, items in (("train", train_items), ("val", val_items)):
        (dst / split / "images").mkdir(parents=True, exist_ok=True)
        (dst / split / "labels").mkdir(parents=True, exist_ok=True)
        for stem, img, lines in items:
            hardlink(str(img), dst / split / "images" / img.name)
            (dst / split / "labels" / f"{stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    block = "\n".join(f"  {i}: {n}" for i, n in enumerate(NAMES11))
    (dst / "data.yaml").write_text(
        f"path: {dst.as_posix()}\ntrain: train/images\nval: val/images\nnc: 11\nnames:\n{block}\n",
        encoding="utf-8")


# 소스 수집
aihub_train = collect(BAL, "train", only_prefix="train_")   # AIHub 11클래스
ss_train = collect(EXP13, "train", only_prefix="ss_")        # selectstar(이미 박싱)
val = collect(BAL, "val")                                    # 공통 AIHub val(11클래스)

print(f"수집: AIHub train {len(aihub_train)} / selectstar train {len(ss_train)} / val {len(val)}")

write(DST["A"], aihub_train, val)
write(DST["C"], ss_train, val)
write(DST["B"], aihub_train + ss_train, val)

# 요약(클래스별)
def dist(items):
    d = defaultdict(int)
    for _, _, lines in items:
        d[int(lines[0].split()[0])] += 1
    return d
da, dc = dist(aihub_train), dist(ss_train)
print(f"\n[A] iso11_A_aihub  train {len(aihub_train)} / val {len(val)}")
print(f"[C] iso11_C_ss     train {len(ss_train)} / val {len(val)}")
print(f"[B] iso11_B_both   train {len(aihub_train)+len(ss_train)} / val {len(val)}")
print(f"\n{'class':20s} {'AIHub':>6s} {'ss':>6s}")
for i, n in enumerate(NAMES11):
    print(f"  {n:20s} {da[i]:6d} {dc[i]:6d}")
