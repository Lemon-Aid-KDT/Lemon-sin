"""taxo50 빌드 — taxo55에서 drop 2 + merge 3 추가 → 라벨 인덱스 재매핑.

taxo59 기준 순변경:
  DROP(6) : cold-ramen, nagasaki-champon, tteokbokki-jajang, tteokbokki-cream-rose (taxo55때),
            + hot-pot(전골), korean-clear-soup(맑은국)   ← 이번 추가
  MERGE(3): korean-red-soup→jjigae-red, noodle-plain→kalguksu, pork-cutlet-sauced→pork-cutlet-dry
  => 59 - 6(drop) - 3(merge) = 50 클래스
산출:
  aihub_yolo_taxo50            (= exp16a: AIHub bal1500서 remap)
  aihub_taxo50_plus_realworld  (= exp16b: 위 + realworld_collected train)
"""
from __future__ import annotations
import glob, os, shutil, sys
from collections import defaultdict
from pathlib import Path
import yaml

sys.stdout.reconfigure(encoding="utf-8")

DROP = {"cold-ramen", "nagasaki-champon", "tteokbokki-jajang", "tteokbokki-cream-rose",
        "hot-pot", "korean-clear-soup"}
MERGE = {"korean-red-soup": "jjigae-red",
         "noodle-plain": "kalguksu",
         "pork-cutlet-sauced": "pork-cutlet-dry"}

AIHUB = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500")
REAL = Path(r"C:\Lemon-sin\data\food_images\processed\realworld_collected_v1")
DST = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo50")
DSTPLUS = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_taxo50_plus_realworld")

names59 = yaml.safe_load((AIHUB / "data.yaml").read_text(encoding="utf-8"))["names"]
names59 = names59 if isinstance(names59, list) else [names59[i] for i in sorted(names59)]
names50 = [n for n in names59 if n not in DROP and n not in MERGE]
assert len(names50) == 50, f"기대 50, 실제 {len(names50)}"

# old(taxo59 idx) -> new(taxo50 idx). drop=제외, merge=타깃의 new idx, 생존=자기 위치
old2new: dict[int, int] = {}
for i, n in enumerate(names59):
    if n in DROP:
        continue
    tgt = MERGE.get(n, n)
    old2new[i] = names50.index(tgt)

print(f"taxo59 {len(names59)} -> taxo50 {len(names50)}")
print(f"DROP({len(DROP)}): {sorted(DROP)}")
print("MERGE:")
for s, t in MERGE.items():
    print(f"  {s}(old {names59.index(s)}) -> {t}(new {names50.index(t)})")


def hardlink(src, dst):
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def remap_labels(lines):
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
            continue
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
    block = "\n".join(f"  {i}: {n}" for i, n in enumerate(names50))
    (root / "data.yaml").write_text(
        f"path: {root.as_posix()}\ntrain: train/images\nval: val/images\nnc: {len(names50)}\nnames:\n{block}\n",
        encoding="utf-8")


# 1) aihub_yolo_taxo50 (exp16a)
if DST.exists():
    shutil.rmtree(DST)
st = defaultdict(int)
copy_split(AIHUB, DST, "train", st)
copy_split(AIHUB, DST, "val", st)
write_yaml(DST)
print(f"\n[exp16a] aihub_yolo_taxo50: train {st['train']} / val {st['val']}")

# 2) aihub_taxo50_plus_realworld (exp16b)
if DSTPLUS.exists():
    shutil.rmtree(DSTPLUS)
st2 = defaultdict(int)
copy_split(DST, DSTPLUS, "train", st2, remap=False)
copy_split(DST, DSTPLUS, "val", st2, remap=False)
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
print(f"[exp16b] aihub_taxo50_plus_realworld: train {st2['train']}+realworld {rw}={st2['train']+rw} / val {st2['val']}")
print("\nnames50:", names50)
