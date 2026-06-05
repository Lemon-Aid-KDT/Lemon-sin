"""exp13 종합 검증 — exp11/exp12/exp13을 3개 평가셋에 측정.

  ① AIHub val per-class AP50 (taxo59 실 GT) — studio 도메인, 일반화 확인
  ② selectstar held-out 1100 인식률 (11클래스×100, top-det==class) — selectstar 도메인
  ③ wild 783 인식률 (실환경 friend_contributed, top-det==matched_class) — 도메인갭 베이스라인

11 selectstar 보강 클래스: takoyaki, black-bean-noodles, udon, bulgogi, dim-sum,
japanese-ramen, savory-pancake, jjigae-red, raw-fish, rice-noodle-soup, mixed-rice-bowl.

usage: python _eval_exp13_full.py
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
    "exp12": r"C:\Lemon-sin\runs\food_yolo\exp12_yolo26s_taxo59tako_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
    "exp13": r"C:\Lemon-sin\runs\food_yolo\exp13_yolo26s_selectstar_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt",
}
SS11 = ["takoyaki", "black-bean-noodles", "udon", "bulgogi", "dim-sum", "japanese-ramen",
        "savory-pancake", "jjigae-red", "raw-fish", "rice-noodle-soup", "mixed-rice-bowl"]
CONF = 0.10


def top1(m: YOLO, im) -> tuple[str | None, float]:
    """이미지 1장에서 최고신뢰 박스의 (클래스명, conf). 박스 없으면 (None, 0)."""
    rr = m.predict(im, conf=0.01, verbose=False, device=0)[0]
    if not len(rr.boxes):
        return None, 0.0
    bi = int(np.argmax(rr.boxes.conf.tolist()))
    return m.names[int(rr.boxes.cls[bi])], float(rr.boxes.conf[bi])


def recog(m: YOLO, items: list[tuple[str, str]]) -> dict[str, list[int]]:
    """items=[(class, path)] -> {class: [n, strict_hit, lenient_hit, det10]}."""
    agg: dict[str, list[int]] = {}
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
            a[2] += 1  # lenient (conf 무관 top1 정답)
            if cf >= CONF:
                a[1] += 1  # strict (conf>=0.10 정답)
    return agg


def main() -> None:
    names = yaml.safe_load(Path(DATA).read_text(encoding="utf-8"))["names"]
    names = names if isinstance(names, list) else [names[i] for i in sorted(names)]

    heldout = [(c, p) for c, p in (ln.split("\t") for ln in HELDOUT.read_text(encoding="utf-8").splitlines() if ln.strip())]
    wild = []
    for ln in WILD.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        fp, c = ln.split("\t")
        wild.append((c, str(WILD_BASE / fp)))
    print(f"평가셋: AIHub val(59cls) | held-out {len(heldout)} | wild {len(wild)}")

    val_ap: dict[str, dict[str, float]] = {}
    val_map: dict[str, float] = {}
    held: dict[str, dict[str, list[int]]] = {}
    wld: dict[str, dict[str, list[int]]] = {}

    for tag, w in MODELS.items():
        print(f"\n##### {tag} 평가 시작 #####")
        m = YOLO(w)
        print(f"[{tag}] ① AIHub val ...")
        r = m.val(data=DATA, split="val", imgsz=640, device=0, workers=0, verbose=False, plots=False)
        val_ap[tag] = {names[int(ci)]: float(r.box.ap50[i]) for i, ci in enumerate(r.box.ap_class_index)}
        val_map[tag] = float(r.box.map50)
        print(f"[{tag}] val mAP50={val_map[tag]:.4f}")
        print(f"[{tag}] ② held-out 1100 ...")
        held[tag] = recog(m, heldout)
        print(f"[{tag}] ③ wild 783 ...")
        wld[tag] = recog(m, wild)

    # CSV ① AIHub val per-class
    with (OUT / "_eval_exp13_aihub_val.csv").open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["class", "ss11", "exp11_ap", "exp12_ap", "exp13_ap", "d13_11"])
        for c in names:
            a11, a12, a13 = val_ap["exp11"].get(c, 0), val_ap["exp12"].get(c, 0), val_ap["exp13"].get(c, 0)
            wr.writerow([c, "Y" if c in SS11 else "", f"{a11:.4f}", f"{a12:.4f}", f"{a13:.4f}", f"{a13-a11:+.4f}"])

    # CSV ② held-out 인식률 (11클래스)
    def rate(d, c, idx):
        a = d.get(c, [0, 0, 0, 0])
        return a[idx] / a[0] if a[0] else 0.0

    with (OUT / "_eval_exp13_heldout.csv").open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["class", "n", "exp11_strict", "exp12_strict", "exp13_strict", "exp11_lenient", "exp13_lenient"])
        for c in SS11:
            n = held["exp11"].get(c, [0])[0]
            wr.writerow([c, n, f"{rate(held['exp11'],c,1):.3f}", f"{rate(held['exp12'],c,1):.3f}",
                         f"{rate(held['exp13'],c,1):.3f}", f"{rate(held['exp11'],c,2):.3f}", f"{rate(held['exp13'],c,2):.3f}"])

    # CSV ③ wild 인식률 (전체 클래스)
    wild_classes = sorted({c for c, _ in wild})
    with (OUT / "_eval_exp13_wild.csv").open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["class", "n", "exp11_strict", "exp12_strict", "exp13_strict",
                     "exp11_lenient", "exp13_lenient", "exp11_det10", "exp13_det10"])
        for c in wild_classes:
            n = wld["exp11"].get(c, [0])[0]
            wr.writerow([c, n, f"{rate(wld['exp11'],c,1):.3f}", f"{rate(wld['exp12'],c,1):.3f}",
                         f"{rate(wld['exp13'],c,1):.3f}", f"{rate(wld['exp11'],c,2):.3f}",
                         f"{rate(wld['exp13'],c,2):.3f}", f"{rate(wld['exp11'],c,3):.3f}", f"{rate(wld['exp13'],c,3):.3f}"])

    # 요약
    def overall(d, idx):
        tot = sum(a[0] for a in d.values())
        hit = sum(a[idx] for a in d.values())
        return hit / tot if tot else 0.0

    print("\n\n================= 요약 =================")
    print(f"AIHub val mAP50:  exp11 {val_map['exp11']:.4f} | exp12 {val_map['exp12']:.4f} | exp13 {val_map['exp13']:.4f}")
    print(f"\n[11 selectstar 클래스] AIHub val AP 평균:")
    for tag in MODELS:
        avg = sum(val_ap[tag].get(c, 0) for c in SS11) / len(SS11)
        print(f"  {tag}: {avg:.4f}")
    print(f"\nheld-out 인식률(strict conf>=0.10) 전체:")
    for tag in MODELS:
        print(f"  {tag}: {overall(held[tag],1):.3f}")
    print(f"\n[WILD 베이스라인] 783 인식률:")
    for tag in MODELS:
        print(f"  {tag}: strict {overall(wld[tag],1):.3f} | lenient(top1) {overall(wld[tag],2):.3f} | det@0.10 {overall(wld[tag],3):.3f}")
    print(f"\n[WILD] 11 selectstar 클래스만:")
    for tag in MODELS:
        sub = {c: wld[tag].get(c, [0, 0, 0, 0]) for c in SS11}
        tot = sum(a[0] for a in sub.values()); hit = sum(a[1] for a in sub.values())
        lh = sum(a[2] for a in sub.values())
        print(f"  {tag}: strict {hit/tot if tot else 0:.3f} | lenient {lh/tot if tot else 0:.3f} (n={tot})")
    print("\nCSV: _eval_exp13_aihub_val.csv / _eval_exp13_heldout.csv / _eval_exp13_wild.csv")


if __name__ == "__main__":
    main()
