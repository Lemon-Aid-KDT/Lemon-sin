"""taxo55 평가 — exp11/14/15a/15b를 wild(777) + realworld val에 name기반 측정.

drop 4클래스 제외. name 기반(top1 클래스명==GT명)이라 taxo59/taxo55 모델 혼용 비교 가능.
비교: exp15a vs exp11(공통55)=drop효과 / exp15b vs exp15a=realworld효과.
usage: python _eval_taxo55.py   (best.pt 없는 모델은 skip)
"""
from __future__ import annotations
import glob, os, sys
from collections import defaultdict
from pathlib import Path
import cv2, numpy as np, yaml
from ultralytics import YOLO

sys.stdout.reconfigure(encoding="utf-8")
DROP = {"cold-ramen", "nagasaki-champon", "tteokbokki-jajang", "tteokbokki-cream-rose"}
RECOVER = ["japanese-ramen", "udon", "jjigae-red", "tteokbokki-red", "western-cream-soup", "rice-noodle-soup"]  # drop 혼동흡수 클래스(회복 기대)
AIHUB59 = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500")
WILD = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_keep_dedup_list.txt")
WILD_BASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
REAL = Path(r"C:\Lemon-sin\data\food_images\processed\realworld_collected_v1")
CONF = 0.10
MODELS = {
    "exp11": r"C:\Lemon-sin\runs\food_yolo\exp11_yolo26s_taxo59bal1500_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp14": r"C:\Lemon-sin\runs\food_yolo\exp14_balanced_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp15a": r"C:\Lemon-sin\runs\food_yolo\exp15a_taxo55_aihub_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp15b": r"C:\Lemon-sin\runs\food_yolo\exp15b_taxo55_aihubreal_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
}
names59 = yaml.safe_load((AIHUB59 / "data.yaml").read_text(encoding="utf-8"))["names"]
names59 = names59 if isinstance(names59, list) else [names59[i] for i in sorted(names59)]


def top1(m, im):
    r = m.predict(im, conf=0.01, verbose=False, device=0)[0]
    if not len(r.boxes):
        return None, 0.0
    bi = int(np.argmax(r.boxes.conf.tolist()))
    return m.names[int(r.boxes.cls[bi])], float(r.boxes.conf[bi])


def recog(m, items):
    agg = defaultdict(lambda: [0, 0, 0])  # n, strict, lenient
    for cls, p in items:
        im = cv2.imread(str(p))
        a = agg[cls]; a[0] += 1
        if im is None:
            continue
        name, cf = top1(m, im)
        if name == cls:
            a[2] += 1
            if cf >= CONF:
                a[1] += 1
    return agg


def main():
    # wild (taxo55 필터)
    wild = []
    for ln in WILD.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        fp, c = ln.split("\t")
        if c not in DROP:
            wild.append((c, WILD_BASE / fp))
    # realworld val (라벨 idx -> name, taxo55 필터)
    rval = []
    for lf in glob.glob(str(REAL / "val" / "labels" / "*.txt")):
        ln = open(lf).readline().split()
        if not ln:
            continue
        nm = names59[int(ln[0])]
        if nm in DROP:
            continue
        img = REAL / "val" / "images" / (os.path.basename(lf)[:-4] + ".jpg")
        if img.exists():
            rval.append((nm, img))
    print(f"평가셋: wild {len(wild)} (taxo55) | realworld val {len(rval)}")

    res = {}
    for tag, w in MODELS.items():
        if not Path(w).exists():
            print(f"[{tag}] best.pt 없음 -> skip")
            continue
        m = YOLO(w)
        res[tag] = {"wild": recog(m, wild), "rval": recog(m, rval)}
        print(f"[{tag}] 측정 완료")
    tags = list(res.keys())

    def overall(d, idx, subset=None):
        items = d.items() if subset is None else [(c, d.get(c, [0, 0, 0])) for c in subset]
        tot = sum(a[0] for _, a in items); hit = sum(a[idx] for _, a in items)
        return hit / tot if tot else 0.0

    print("\n================= taxo55 평가 요약 =================")
    print("[WILD 777] strict / lenient:")
    for t in tags:
        print(f"  {t}: {overall(res[t]['wild'],1):.3f} / {overall(res[t]['wild'],2):.3f}")
    print("\n[realworld val] strict / lenient:")
    for t in tags:
        print(f"  {t}: {overall(res[t]['rval'],1):.3f} / {overall(res[t]['rval'],2):.3f}")
    print("\n[WILD] drop 혼동흡수 클래스(회복 기대) strict:")
    print(f"  {'class':20s} " + " ".join(f"{t:>7s}" for t in tags))
    for c in RECOVER:
        row = []
        for t in tags:
            a = res[t]['wild'].get(c, [0, 0, 0])
            row.append(f"{a[1]/a[0]:.2f}" if a[0] else "  -")
        print(f"  {c:20s} " + " ".join(f"{v:>7s}" for v in row))
    # CSV (wild per-class)
    classes = sorted({c for c, _ in wild})
    with (Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review") / "_eval_taxo55_wild.csv").open("w", encoding="utf-8-sig", newline="") as f:
        import csv
        wr = csv.writer(f); wr.writerow(["class", "n"] + [f"{t}_strict" for t in tags])
        for c in classes:
            n = res[tags[0]]['wild'].get(c, [0])[0]
            wr.writerow([c, n] + [f"{res[t]['wild'].get(c,[0,0,0])[1]/max(1,n):.3f}" for t in tags])
    print("\nCSV: _eval_taxo55_wild.csv")


if __name__ == "__main__":
    main()
