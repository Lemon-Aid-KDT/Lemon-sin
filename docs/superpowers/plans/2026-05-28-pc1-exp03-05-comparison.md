# PC1 YOLOv8n exp03~05 실험 비교

> 작성: 2026-05-28 | PC1 (RTX 4060 Laptop 8GB) | 모델: YOLOv8n

---

## 실험 개요

| 항목 | exp03 | exp04 | exp05 |
|---|---|---|---|
| 목적 | balanced_500 baseline | 소수 클래스 augmentation 보강 | 소수 클래스 단순 복제 보강 |
| 데이터셋 | `aihub_yolo_50_balanced_500` | `aihub_yolo_50_minority_aug_train500_val100` | `aihub_yolo_50_minority_dup_train500_val100` |
| train 이미지 | 23,030 | 25,000 | 25,000 |
| val 이미지 | 13,780 (full) | 4,110 (cap=100) | 4,110 (cap=100) |
| 보강 방식 | 없음 (다운샘플만) | rotation/crop/flip/color jitter | 단순 복제 |
| 보강 대상 | - | 소수 클래스 13개 | 소수 클래스 13개 |
| model | yolov8n.pt | yolov8n.pt | yolov8n.pt |
| epochs | 50 | 50 | 50 |
| batch | 48 | 48 | 48 |
| patience | 100 | 100 | 100 |
| seed | 0 | 0 | 0 |

---

## 성능 비교 (best epoch 기준)

> 주의: exp03은 full val(13,780장), exp04/05는 valcap100(4,110장) 기준이라 절대값 직접 비교 시 신중 필요.
> exp03 재검증(valcap100) 기준 mAP50=0.826으로, exp04/05와 동일한 val로 비교 가능.

| 지표 | exp03 (full val) | exp03 재검증 (valcap100) | exp04 (aug) | exp05 (dup) |
|---|---:|---:|---:|---:|
| best epoch | 50 | - | 46 | 45 |
| **mAP50** | 0.790 | **0.826** | 0.807 | 0.805 |
| **mAP50-95** | 0.730 | ~0.768 | 0.741 | 0.739 |
| Precision | 0.741 | - | 0.784 | 0.782 |
| Recall | 0.737 | - | 0.741 | 0.749 |

### valcap100 기준 exp03 대비 변화량

| 지표 | exp04 (aug) | exp05 (dup) |
|---|---:|---:|
| mAP50 Δ | **-0.019** | **-0.021** |
| mAP50-95 Δ | ~-0.027 | ~-0.029 |

---

## 해석

### exp04 vs exp03
- augmentation(rotation/crop/color jitter) 적용 후 오히려 mAP50 **하락**
- 원인 추정: 음식 이미지에 강한 변형이 실제 분포와 달라 노이즈로 작용 + YOLO online augmentation과 중복

### exp05 vs exp04
- 단순 복제는 augmentation보다 성능이 소폭 낮음 (-0.002p)
- 두 방식 모두 baseline(exp03 valcap100) 대비 하락 → 소수 클래스 수 맞추기 자체가 문제가 아닐 수 있음

### 핵심 결론
- **소수 클래스 오버샘플링(aug/dup) 단독으로는 성능 개선 효과 없음**
- 성능 저하 원인이 "클래스 불균형"이 아닌 "클래스 자체의 시각적 유사성(혼동)"일 가능성 높음
- 다음 접근: 크롤링으로 **다양한 실제 이미지 추가** → 모델이 클래스 간 구별 특징을 더 잘 학습하도록 유도

---

## 다음 실험 방향

| 옵션 | 설명 | 기대 효과 |
|---|---|---|
| **크롤링 데이터 보강** | 소수 클래스 + AP50 낮은 클래스 실사 이미지 추가 | 도메인 다양성 확보, 실전 성능 향상 |
| cap 증가 (500 → 1000) | 데이터 충분한 약한 클래스 학습량 증가 | noodle-soup, seafood-stew 등 혼동 클래스 개선 |
| 더 큰 모델 (yolo11s → yolo11m) | 모델 용량 증가 | 시각적으로 유사한 클래스 구별력 향상 가능 |

---

## 참조

- exp03 결과 상세: `docs/superpowers/plans/2026-05-28-exp03-yolo11s-balanced500-results.md` (PC2 yolo11s 기준)
- exp04 결과 상세: `docs/superpowers/plans/2026-05-28-yolov8n-minority-augmentation-result.md`
- 클래스별 AP50: `docs/superpowers/plans/2026-05-28-class-dataset-ap50-summary.csv` (`docs/data-yolo-food-detection` 브랜치)
- 크롤링 전략: `docs/superpowers/plans/2026-05-28-cvat-docker-setup.md` (`docs/data-yolo-cvat-setup` 브랜치)
