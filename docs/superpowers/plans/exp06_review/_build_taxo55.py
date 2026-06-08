"""taxo55 빌드 — 4클래스 drop + 라벨 인덱스 재매핑.

drop: cold-ramen, nagasaki-champon, tteokbokki-jajang, tteokbokki-cream-rose (혼동·니치).
산출:
  aihub_yolo_taxo55            (= exp15a: AIHub bal1500서 4클래스 제거+remap)
  aihub_taxo55_plus_realworld  (= exp15b: 위 + realworld_collected train)
공통 val = AIHub bal1500 val(taxo55). realworld val은 학습에 안 넣음(별도 평가용).
"""
from __future__ import annotations
import glob, os, shutil
from collections import defaultdict
from pathlib import Path
import yaml

DROP = {"cold-ramen", "nagasaki-champon", "tteokbokki-jajang", "tteokbokki-cream-rose"}
AIHUB = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500")
REAL = Path(r"C:\Lemon-sin\data\food_images\processed\realworld_collected_v1")
DST55 = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo55")
DSTPLUS = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_taxo55_plus_realworld")

names59 = yaml.safe_load((AIHUB / "data.yaml").read_text(encoding="utf-8"))["names"]
names59 = names59 if isinstance(names59, list) else [names59[i] for i in sorted(names59)]
names55 = [n for n in names59 if n not in DROP]
old2new = {i: names55.index(n) for i, n in enumerate(names59) if n not in DROP}
print(f"taxo59 {len(names59)} -> taxo55 {len(names55)} (drop {sorted(DROP)})")
print(f"drop 인덱스(old): {[i for i,n in enumerate(names59) if n in DROP]}")


def hardlink(src, dst):
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def remap_labels(lines):
    """라벨 줄들 -> taxo55 remap. 살아남은 박스만. 전부 drop이면 None."""
    out = []
    for ln in lines:
        p = ln.split()
        if not p:
            continue
        c = int(p[0])
        if c in old2new:
            out.append(f"{old2new[c]} {' '.join(p[1:])}")
    return out or None


def copy_split(src_root, dst_root, split, stat, remap=True):
    (dst_root / split / "images").mkdir(parents=True, exist_ok=True)
    (dst_root / split / "labels").mkdir(parents=True, exist_ok=True)
    for lf in glob.glob(str(src_root / split / "labels" / "*.txt")):
        stem = os.path.basename(lf)[:-4]
        lines = Path(lf).read_text().splitlines()
        new = remap_labels(lines) if remap else ([l for l in lines if l.strip()] or None)
        if new is None:
            continue  # 박스 클래스가 전부 drop -> 이미지 제외
        img = None
        for ext in (".jpg", ".png"):
            cand = src_root / split / "images" / f"{stem}{ext}"
            if cand.exists():
                img = cand
                break
        if img is None:
            continue
        hardlink(str(img), dst_root / split / "images" / img.name)
        (dst_root / split / "labels" / f"{stem}.txt").write_text("\n".join(new) + "\n", encoding="utf-8")
        stat[split] += 1


def write_yaml(root):
    block = "\n".join(f"  {i}: {n}" for i, n in enumerate(names55))
    (root / "data.yaml").write_text(
        f"path: {root.as_posix()}\ntrain: train/images\nval: val/images\nnc: {len(names55)}\nnames:\n{block}\n",
        encoding="utf-8")


# 1) aihub_yolo_taxo55 (exp15a)
if DST55.exists():
    shutil.rmtree(DST55)
st = defaultdict(int)
copy_split(AIHUB, DST55, "train", st)
copy_split(AIHUB, DST55, "val", st)
write_yaml(DST55)
print(f"\n[exp15a] aihub_yolo_taxo55: train {st['train']} / val {st['val']}")

# 2) aihub_taxo55_plus_realworld (exp15b) = taxo55 + realworld train
if DSTPLUS.exists():
    shutil.rmtree(DSTPLUS)
st2 = defaultdict(int)
copy_split(DST55, DSTPLUS, "train", st2, remap=False)   # taxo55 train 복사(이미 remap됨, 재remap 금지)
copy_split(DST55, DSTPLUS, "val", st2, remap=False)     # 동일 val
# realworld train 추가(remap, drop 제거)
(DSTPLUS / "train" / "images").mkdir(parents=True, exist_ok=True)
rw = 0
for lf in glob.glob(str(REAL / "train" / "labels" / "*.txt")):
    stem = os.path.basename(lf)[:-4]
    new = remap_labels(Path(lf).read_text().splitlines())
    if new is None:
        continue
    img = REAL / "train" / "images" / f"{stem}.jpg"
    if not img.exists():
        continue
    hardlink(str(img), DSTPLUS / "train" / "images" / img.name)
    (DSTPLUS / "train" / "labels" / f"{stem}.txt").write_text("\n".join(new) + "\n", encoding="utf-8")
    rw += 1
write_yaml(DSTPLUS)
print(f"[exp15b] aihub_taxo55_plus_realworld: train {st2['train']}+realworld {rw}={st2['train']+rw} / val {st2['val']}")
print("\n빌드 완료. names55 일부:", names55[:5], "...", names55[-3:])
