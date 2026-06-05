"""exp14 balanced 검증 — exp11/exp13/exp14를 3개 평가셋에 측정 (S5).

  ① AIHub val per-class AP50 (taxo59 실 GT)
  ② selectstar held-out 1100 인식률 (11클래스)
  ③ wild 783 인식률 (실환경, top1==matched_class) — 핵심 비교

목적: exp14(balanced 보강)가 exp13(불균형 보강)의 wild 잠식을 막았나.
  - exp11=baseline(noSS), exp13=11클래스 +800 초과(잠식), exp14=부족클래스만 1500 균등 채움.
usage: python _eval_exp14_full.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

sys.stdout.reconfigure(encoding="utf-8")

DATA = r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500\data.yaml"
HELDOUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\exp13_selectstar_heldout.tsv")
WILD = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_keep_dedup_list.txt")
WILD_BASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
OUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review")

MODELS = {
    "exp11": r"C:\Lemon-sin\runs\food_yolo\exp11_yolo26s_taxo59bal1500_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp13": r"C:\Lemon-sin\runs\food_yolo\exp13_yolo26s_selectstar_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp14": r"C:\Lemon-sin\runs\food_yolo\exp14_balanced_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
}
SS11 = ["takoyaki", "black-bean-noodles", "udon", "bulgogi", "dim-sum", "japanese-ramen",
        "savory-pancake", "jjigae-red", "raw-fish", "rice-noodle-soup", "mixed-rice-bowl"]
# exp14가 selectstar로 채운 부족 클래스(개수 보강된 핵심)
FILLED = ["takoyaki", "black-bean-noodles", "fried-rice", "udon", "savory-pancake", "bulgogi",
          "dim-sum", "jjigae-red", "mixed-rice-bowl", "hamburger", "western-cream-soup",
          "grilled-pork-belly", "grilled-beef", "tteokbokki-cream-rose"]
CONF = 0.10


def top1(m, im):
    rr = m.predict(im, conf=0.01, verbose=False, device=0)[0]
    if not len(rr.boxes):
        return None, 0.0
    bi = int(np.argmax(rr.boxes.conf.tolist()))
    return m.names[int(rr.boxes.cls[bi])], float(rr.boxes.conf[bi])


def recog(m, items):
    agg = {}
    for cls, path in items:
        im = cv2.imread(path)
        a = agg.setdefault(cls, [0, 0, 0, 0])
        a[0] += 1
        if im is None:
            continue
        name, cf = top1(m, im)
        if name is None:
            continue
        if cf >= CONF:
            a[3] += 1
        if name == cls:
            a[2] += 1
            if cf >= CONF:
                a[1] += 1
    return agg


def main():
    names = yaml.safe_load(Path(DATA).read_text(encoding="utf-8"))["names"]
    names = names if isinstance(names, list) else [names[i] for i in sorted(names)]
    heldout = [(c, p) for c, p in (ln.split("\t") for ln in HELDOUT.read_text(encoding="utf-8").splitlines() if ln.strip())]
    wild = []
    for ln in WILD.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            fp, c = ln.split("\t")
            wild.append((c, str(WILD_BASE / fp)))
    print(f"평가셋: AIHub val | held-out {len(heldout)} | wild {len(wild)}")

    val_ap, val_map, held, wld = {}, {}, {}, {}
    for tag, w in MODELS.items():
        if not Path(w).exists():
            print(f"[{tag}] best.pt 없음 -> skip ({w})")
            continue
        print(f"\n##### {tag} #####")
        m = YOLO(w)
        r = m.val(data=DATA, split="val", imgsz=640, device=0, workers=0, verbose=False, plots=False)
        val_ap[tag] = {names[int(ci)]: float(r.box.ap50[i]) for i, ci in enumerate(r.box.ap_class_index)}
        val_map[tag] = float(r.box.map50)
        print(f"[{tag}] val mAP50={val_map[tag]:.4f}")
        held[tag] = recog(m, heldout)
        wld[tag] = recog(m, wild)
        print(f"[{tag}] held/wild 측정 완료")

    tags = list(val_ap.keys())

    def rate(d, c, idx):
        a = d.get(c, [0, 0, 0, 0])
        return a[idx] / a[0] if a[0] else 0.0

    # CSV: wild per-class (핵심)
    wild_classes = sorted({c for c, _ in wild})
    with (OUT / "_eval_exp14_wild.csv").open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["class", "n", "filled"] + [f"{t}_strict" for t in tags] + [f"{t}_lenient" for t in tags])
        for c in wild_classes:
            n = wld[tags[0]].get(c, [0])[0]
            wr.writerow([c, n, "Y" if c in FILLED else ""]
                        + [f"{rate(wld[t],c,1):.3f}" for t in tags]
                        + [f"{rate(wld[t],c,2):.3f}" for t in tags])
    # CSV: AIHub val per-class
    with (OUT / "_eval_exp14_aihub_val.csv").open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["class", "filled"] + [f"{t}_ap" for t in tags])
        for c in names:
            wr.writerow([c, "Y" if c in FILLED else ""] + [f"{val_ap[t].get(c,0):.4f}" for t in tags])
    # CSV: held-out
    with (OUT / "_eval_exp14_heldout.csv").open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["class", "n"] + [f"{t}_strict" for t in tags])
        for c in SS11:
            n = held[tags[0]].get(c, [0])[0]
            wr.writerow([c, n] + [f"{rate(held[t],c,1):.3f}" for t in tags])

    def overall(d, idx, subset=None):
        items = d.items() if subset is None else [(c, d.get(c, [0, 0, 0, 0])) for c in subset]
        tot = sum(a[0] for _, a in items)
        hit = sum(a[idx] for _, a in items)
        return hit / tot if tot else 0.0

    print("\n================= 요약 =================")
    print("AIHub val mAP50:  " + " | ".join(f"{t} {val_map[t]:.4f}" for t in tags))
    print("\n[WILD 전체 783] strict 인식률:")
    for t in tags:
        print(f"  {t}: strict {overall(wld[t],1):.3f} | lenient {overall(wld[t],2):.3f} | det@0.10 {overall(wld[t],3):.3f}")
    print("\n[WILD] exp14가 채운 클래스(FILLED)만:")
    for t in tags:
        print(f"  {t}: strict {overall(wld[t],1,FILLED):.3f}")
    print("\n[WILD] 채우지 않은 나머지 클래스만(잠식 여부):")
    rest = [c for c in wild_classes if c not in FILLED]
    for t in tags:
        print(f"  {t}: strict {overall(wld[t],1,rest):.3f}")
    print("\nCSV: _eval_exp14_{wild,aihub_val,heldout}.csv")


if __name__ == "__main__":
    main()
