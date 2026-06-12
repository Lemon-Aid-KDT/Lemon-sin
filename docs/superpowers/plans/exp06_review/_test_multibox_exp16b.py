"""exp16b 다중 음식(multi-dish) 박스 테스트.

wild 필터링(VLM) 때 "multi"로 분류돼 평가셋에서 제외된 실제 카톡 다중요리 사진에서
표본을 뽑아, 데모 앱과 동일한 파이프라인(conf=0.10 + 지원40 classes 필터 + agnostic NMS)으로
exp16b가 박스를 몇 개나 치는지 측정하고 시각화를 저장한다.

GT 박스가 없으므로 정량 mAP는 불가 — ①이미지당 박스 수 분포 ②VLM이 본 음식 수와의 대비
③시각화(사람 눈 검증)로 평가한다. 시각화는 사적 사진이므로 git 밖(D:)에만 저장.

usage: python -u _test_multibox_exp16b.py   (GPU, 학습 중 실행 금지)
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

sys.stdout.reconfigure(encoding="utf-8")
CSV = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_classification_2026-06-04.csv")
BASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
OUT = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\multibox_vis_exp16b")
MODEL = Path(
    r"C:\Lemon-sin\runs\food_yolo"
    r"\exp16b_taxo50_aihubreal_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt"
)
CONFIG = Path(r"C:\Lemon-sin\docs\deliverables\model-handoff-exp16b\exp16b_deploy_config.json")
CONF = 0.10
NMS_IOU = 0.5
N_SAMPLE = 40


def _iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def agnostic_nms_keep(res, iou_thresh: float = 0.5) -> list[int]:
    """클래스 무시 NMS — 겹치는 박스는 최고 신뢰도 1개만 (데모 앱과 동일 로직)."""
    xy = res.boxes.xyxy.cpu().numpy()
    cf = res.boxes.conf.cpu().numpy()
    order = cf.argsort()[::-1]
    keep: list[int] = []
    sup: set[int] = set()
    for i in order:
        if int(i) in sup:
            continue
        keep.append(int(i))
        for j in order:
            if int(j) != int(i) and int(j) not in sup and _iou(xy[i], xy[j]) > iou_thresh:
                sup.add(int(j))
    return sorted(keep)


def count_foods(foods: str) -> int:
    """VLM foods 컬럼의 음식 수를 센다 (구분자: , ; / · + 한국어 '와/과' 미처리=보수적)."""
    if not foods or not foods.strip():
        return 0
    return len([t for t in re.split(r"[,;/·|+]", foods) if t.strip()])


def main():
    rows = list(csv.DictReader(CSV.open(encoding="utf-8-sig")))
    multi = [r for r in rows if r.get("category", "").strip() == "multi"]
    print(f"multi 분류 사진: {len(multi)}장 (전체 {len(rows)})")
    multi.sort(key=lambda r: (r["folder"], r["file"]))
    stride = max(1, len(multi) // N_SAMPLE)
    sample = multi[::stride][:N_SAMPLE]
    print(f"표본 {len(sample)}장 (stride={stride}, 결정적 추출)")

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    classes = cfg["supported_class_indices"]
    m = YOLO(str(MODEL))
    OUT.mkdir(exist_ok=True)

    box_counts = Counter()
    pairs = []  # (file, n_boxes, vlm_n, foods, detected_names)
    for k, r in enumerate(sample):
        p = BASE / r["folder"] / r["file"]
        im = cv2.imread(str(p))
        if im is None:
            print(f"  [skip] 로드 실패: {p}")
            continue
        res = m.predict(im, conf=CONF, classes=classes, verbose=False)[0]
        if len(res.boxes) > 1:
            import torch

            keep = agnostic_nms_keep(res, NMS_IOU)
            res.boxes = res.boxes[torch.tensor(keep, device=res.boxes.cls.device)]
        nb = len(res.boxes)
        box_counts[min(nb, 4)] += 1
        names = [m.names[int(c)] for c in res.boxes.cls.tolist()]
        vlm_n = count_foods(r.get("foods", ""))
        pairs.append((f"{r['folder']}/{r['file']}", nb, vlm_n, r.get("foods", ""), names))
        out_name = f"{k:02d}_{nb}box_{r['folder']}_{r['file']}"
        cv2.imwrite(str(OUT / out_name), res.plot())

    n = len(pairs)
    print(f"\n[박스 수 분포] (conf>={CONF}, 지원40 필터, NMS {NMS_IOU})")
    for k in sorted(box_counts):
        label = f"{k}개" if k < 4 else "4개+"
        print(f"  {label}: {box_counts[k]}장 ({box_counts[k]/n*100:.0f}%)")
    multi_rate = sum(v for k, v in box_counts.items() if k >= 2) / n
    print(f"  >=2개 박스(다중 탐지 작동): {multi_rate*100:.0f}%")
    mean_b = np.mean([b for _, b, _, _, _ in pairs])
    mean_v = np.mean([v for _, _, v, _, _ in pairs if v > 0])
    print(f"  이미지당 평균 박스 {mean_b:.1f}개 vs VLM이 본 음식 평균 {mean_v:.1f}개")
    print("  ※ VLM 음식 수에는 미지원/비대상(반찬 등) 포함 → 박스 수가 적은 것이 정상 범위")

    print(f"\n[이미지별 상세] (박스수 / VLM음식수 / 탐지클래스)")
    for f, nb, vn, foods, names in pairs:
        print(f"  {nb} / {vn}  {f}  -> {names}  | VLM: {foods[:60]}")
    print(f"\n시각화 저장: {OUT} ({n}장)")


if __name__ == "__main__":
    main()
