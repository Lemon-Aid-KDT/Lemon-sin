"""실험 히스토리 wild 재평가 — exp10/12/13/14를 클린 wild 테스트셋에서 측정.

목적: 실험 진행 선그래프(wild 축)를 전 구간 동일 테스트셋·동일 분모로 그리기 위해,
클린 평가(_eval_exp16_clean.py: exp11/15a/16a/16b)에 없는 taxo59 계열 4모델을 추가 측정.
같은 wild 739장(friend, 4+4모델 전부 미학습=누수 0), 같은 top-1 strict/lenient 정의.
산출: _eval_history_perimage.csv (이미지별 0/1 — _eval_exp16_clean_perimage.csv와 동일 포맷,
      지원범위 시나리오는 두 CSV를 합쳐 오프라인 계산).
usage: python -u _eval_history_wild.py   (GPU, 학습 중 실행 금지)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

sys.stdout.reconfigure(encoding="utf-8")
DROP50 = {"cold-ramen", "nagasaki-champon", "tteokbokki-jajang", "tteokbokki-cream-rose",
          "hot-pot", "korean-clear-soup"}
MERGE = {"korean-red-soup": "jjigae-red", "noodle-plain": "kalguksu",
         "pork-cutlet-sauced": "pork-cutlet-dry"}
WILD = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_keep_dedup_list.txt")
WILD_BASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
CONF = 0.10
RUNS = Path(r"C:\Lemon-sin\runs\food_yolo")
MODELS = {
    "exp10": RUNS / "exp10_yolo26s_taxo59bal500_pc1_s42_b16_w8_cache_disk_det_true" / "weights" / "best.pt",
    "exp12": RUNS / "exp12_yolo26s_taxo59tako_pc1_s42_b16_w8_cache_disk_det_true" / "weights" / "best.pt",
    "exp13": RUNS / "exp13_yolo26s_selectstar_pc1_s42_b16_w8_cache_disk_det_true" / "weights" / "best.pt",
    "exp14": RUNS / "exp14_balanced_pc1_s42_b16_w8_cache_disk_det_true" / "weights" / "best.pt",
}
EXCLUDE_45 = {"seafood-jjim", "seafood-spicy-tang", "seafood-clear-tang",
              "squid-dish", "shrimp-dish"}
EXCLUDE_40 = EXCLUDE_45 | {"grilled-beef", "jjamppong", "fried-rice",
                           "dumplings", "rice-bowl"}


def norm(name):
    return MERGE.get(name, name) if name else name


def top1(m, im):
    r = m.predict(im, conf=0.01, verbose=False, device=0)[0]
    if not len(r.boxes):
        return None, 0.0
    bi = int(np.argmax(r.boxes.conf.tolist()))
    return m.names[int(r.boxes.cls[bi])], float(r.boxes.conf[bi])


def main():
    wild = []
    for ln in WILD.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        fp, c = ln.split("\t")
        if c in DROP50:
            continue
        wild.append((norm(c), fp))
    print(f"클린 평가셋 {len(wild)}장 — 대상 4모델(exp10/12/13/14) 전부 미학습(누수 0)")

    res = {}
    for tag, w in MODELS.items():
        if not Path(w).exists():
            print(f"[{tag}] best.pt 없음 -> skip")
            continue
        m = YOLO(str(w))
        recs = []
        for gt, fp in wild:
            im = cv2.imread(str(WILD_BASE / fp))
            if im is None:
                recs.append((gt, 0, 0)); continue
            name, cf = top1(m, im)
            match = norm(name) == gt
            recs.append((gt, int(match and cf >= CONF), int(match)))
        res[tag] = recs
        print(f"[{tag}] 측정 완료 ({len(recs)}장)")
    tags = list(res.keys())

    out = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review") / "_eval_history_perimage.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["image", "gt"] + [f"{t}_strict" for t in tags] + [f"{t}_lenient" for t in tags])
        for i, (gt, fp) in enumerate(wild):
            wr.writerow([fp, gt] + [res[t][i][1] for t in tags] + [res[t][i][2] for t in tags])
    print(f"이미지별 결과: {out.name}")

    for sc_name, excl in [("50클래스 전체", set()), ("지원 45클래스", EXCLUDE_45), ("지원 40클래스", EXCLUDE_40)]:
        idx = [i for i, (c, _) in enumerate(wild) if c not in excl]
        print(f"\n[{sc_name}] n={len(idx)}  top-1 strict / lenient:")
        for t in tags:
            s = sum(res[t][i][1] for i in idx) / len(idx)
            l = sum(res[t][i][2] for i in idx) / len(idx)
            print(f"  {t}: {s:.3f} / {l:.3f}")


if __name__ == "__main__":
    main()
