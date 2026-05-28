# 2026-05-28 YOLOv8n 소수 클래스 보강 실험 결과

## 요약

`exp04_yolov8n_minorityaug_train500_val100_pc1_b48_w8_cache_disk_det_true`는
소수 클래스만 offline augmentation으로 500장까지 늘리고, validation도 클래스별 최대
100장으로 제한해 학습한 실험이다.

결론: **채택하지 않는다.** 같은 `valcap100` 기준에서 기존 `exp03` 재검증보다 전체
성능이 낮았다.

## 비교 기준

기존 `exp03`는 full validation 기준으로 학습되어 있었기 때문에, 새 검증셋 기준으로
한 번 더 평가했다.

- 기준 모델: `runs/food_yolo/exp03_yolov8n_balanced500_pc1_b48_w8_cache_disk_det_true/weights/best.pt`
- 기준 재검증: `runs/food_yolo/exp03_yolov8n_balanced500_pc1_valcap100`
- 실험 모델: `runs/food_yolo/exp04_yolov8n_minorityaug_train500_val100_pc1_b48_w8_cache_disk_det_true`
- 공통 검증셋: `data/food_images/processed/aihub_yolo_50_minority_aug_train500_val100/val`

## 데이터셋

`exp04` 데이터셋:

`data/food_images/processed/aihub_yolo_50_minority_aug_train500_val100`

구성:

- train: 25,000 images / 25,000 labels
- val: 4,110 images / 4,110 labels
- train 50개 클래스 모두 500장
- val 클래스별 최대 100장
- 소수 클래스 offline augmentation 추가: 1,970장
- 생성 방식: rotation, crop/resize, horizontal flip, color jitter

보강 대상 13개 클래스:

| class_id | class_name | original | added | final |
|---:|---|---:|---:|---:|
| 4 | rice-soup | 460 | 40 | 500 |
| 9 | fish-cake | 480 | 20 | 500 |
| 13 | takoyaki | 410 | 90 | 500 |
| 19 | spicy-mixed-noodles | 370 | 130 | 500 |
| 21 | black-bean-noodles | 390 | 110 | 500 |
| 25 | grilled-pork-belly | 370 | 130 | 500 |
| 29 | stir-fried-pork | 240 | 260 | 500 |
| 30 | braised-chicken | 430 | 70 | 500 |
| 31 | chicken-galbi | 370 | 130 | 500 |
| 32 | braised-pork-hock | 350 | 150 | 500 |
| 38 | squid-dish | 100 | 400 | 500 |
| 39 | sweet-and-sour-pork | 290 | 210 | 500 |
| 40 | mala-hot-pot | 270 | 230 | 500 |

## 학습 설정

`exp04` 주요 설정:

- model: `yolov8n.pt`
- epochs: 50
- batch: 48
- imgsz: 640
- workers: 8
- cache: disk
- seed: 0
- deterministic: true
- patience: 100
- 기본 YOLO online augmentation 유지

## 결과

| run | validation | mAP50 | mAP50-95 | precision | recall |
|---|---|---:|---:|---:|---:|
| exp03 balanced500 재검증 | valcap100 | 0.826 | 약 0.768 | - | - |
| exp04 minority strong aug | valcap100 | 0.80573 | 0.74159 | 0.78819 | 0.74266 |

비교:

- mAP50: `-0.020`p
- mAP50-95: 약 `-0.026`p

참고:

- `exp03 valcap100`의 mAP50은 `BoxPR_curve.png`에 표시된 값이다.
- `exp03 valcap100` 폴더에는 `results.csv`가 없어서 mAP50-95는 `predictions.json`과
  `valcap100` 라벨로 별도 계산한 근사값이다. 이 계산에서 mAP50은 0.831로 나와 그래프
  표시값 0.826과 근접했다.
- 기존 full validation 기준 exp03 결과는 `mAP50=0.79009`, `mAP50-95=0.72991`이지만,
  검증셋이 달라 exp04와 직접 비교하지 않는다.

## 해석

소수 클래스에 강한 offline augmentation을 적용한 방식은 전체 성능을 낮췄다.

가능한 원인:

- rotation/crop/color jitter가 음식 이미지의 실제 분포보다 강했을 수 있다.
- offline augmentation 위에 YOLO 기본 online augmentation이 겹치면서 변형이 과해졌을 수 있다.
- 소수 클래스 샘플 수는 맞췄지만, 합성 샘플 품질이 원본 분포를 충분히 대표하지 못했을 수 있다.

## 다음 실험

`exp05`는 강한 변형 없이 **소수 클래스 단순 복제 oversampling**만 적용한다.

목적:

- 성능 변화가 "클래스 수 보정" 때문인지, "강한 augmentation" 때문인지 분리한다.

준비된 exp05 데이터셋:

`data/food_images/processed/aihub_yolo_50_minority_dup_train500_val100`

구성:

- train: 25,000 images / 25,000 labels
- val: 4,110 images / 4,110 labels
- train 50개 클래스 모두 500장
- val 클래스별 최대 100장
- 소수 클래스 단순 복제 추가: 1,970장

실행 스크립트:

`docs/superpowers/plans/yolov8n_minority_dup_train500_val100_run.ps1`

