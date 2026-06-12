"""실험 히스토리 wild 재평가 ② — exp10 이전 모델(exp06/07/09)을 클린 wild 테스트셋에서 측정.

_eval_history_wild.py(exp10/12/13/14)의 확장: 선그래프 wild 축을 exp06까지 연장.
exp06/07=taxo63, exp09=taxo62 — 유지 클래스명은 taxo59와 동일하므로 같은 norm(MERGE3) 적용.
모델이 지원하지 않는 GT 클래스(체계 차이)는 자동 오답 = "그 모델의 서비스 성능" 그대로.
각 모델별로 GT에 있는데 모델 클래스에 없는 이름을 출력해 투명하게 기록.
exp01~05(yolov8n 초기 50클래스 체계)는 클래스 매핑 신뢰성 문제로 제외.
산출: _eval_history_pre10_perimage.csv (동일 포맷)
usage: python -u _eval_history_pre10.py   (GPU, 학습 중 실행 금지)
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
    "exp06": RUNS / "exp06_yolo11s_taxo63bal500_pc1_b32_w8_cache_disk_det_true" / "weights" / "best.pt",
    "exp07": RUNS / "exp07_yolo26s_taxo63bal500_pc1_b16_w8_cache_disk_det_true" / "weights" / "best.pt",
    "exp09": RUNS / "exp09_yolo26s_taxo62bal500_pc1_b16_w8_cache_disk_det_true" / "weights" / "best.pt",
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
    gt_classes = sorted({c for c, _ in wild})
    print(f"클린 평가셋 {len(wild)}장 ({len(gt_classes)}클래스) — 대상 3모델(exp06/07/09) 전부 미학습(누수 0)")

    res = {}
    for tag, w in MODELS.items():
        if not Path(w).exists():
            print(f"[{tag}] best.pt 없음 -> skip")
            continue
        m = YOLO(str(w))
        model_norm = {norm(n) for n in m.names.values()}
        missing = [c for c in gt_classes if c not in model_norm]
        print(f"[{tag}] nc={len(m.names)} | GT에 있으나 모델에 없는 클래스 {len(missing)}개: {missing or '없음'}")
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

    out = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review") / "_eval_history_pre10_perimage.csv"
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
