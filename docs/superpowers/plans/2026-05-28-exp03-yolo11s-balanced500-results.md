# exp03 YOLO11s + balanced_500 (PC2) 학습 결과

> 학습 완료: 2026-05-28 오전. 본 문서는 1차 분석 + 약한 클래스 식별.

## 1. 실행 환경

| 항목 | 값 |
|---|---|
| Run name | `exp03_yolo11s_balanced500_pc2_b32_w8_cache_disk_det_true` |
| 컴퓨터 | PC2 (RTX 4060 Laptop 8GB) |
| 모델 | yolo11s.pt (~9.4M params) |
| 데이터셋 | `aihub_yolo_50_balanced_500` (train 23,030 + val 4,110, val cap=100) |
| 설정 | epochs=50, batch=32, imgsz=640, workers=8, cache=disk, seed=42, deterministic=true, patience=15, plots=false |
| 총 학습 시간 | **10시간 28분 (37,651초)** |
| EarlyStopping | 적용 안 됨 (50/50 완주) |
| Best epoch | 48 (마지막 거의 평탄) |

## 2. 전체 성능

| Metric | Best (epoch 48) |
|---:|---:|
| **mAP50** | **0.823** |
| **mAP50-95** | **0.788** |
| Precision | 0.818 |
| Recall | 0.772 |
| Inference speed | 5.5 ms/image (~180 FPS) |

## 3. PC1 yolov8n 풀데이터(108K) baseline 비교

> 주의: val 집합이 다름(PC1=원본 13,780, PC2=balanced 4,110)이라 수치 절대 비교는 신중. trend 해석용.

| 지표 | PC1 yolov8n 풀데이터 | PC2 yolo11s balanced_500 | Δ |
|---|---:|---:|---:|
| mAP50 | 0.839 | 0.823 | **-0.016** |
| mAP50-95 | 0.812 | 0.788 | **-0.024** |
| Train 데이터량 | 108,580 | 23,030 (21%) | -79% |
| 모델 params | ~3M (yolov8n) | ~9.4M (yolo11s) | +3.1x |

### 잠정 해석

- **데이터 79% 감소에도 성능 1.6%p만 하락** → balanced_500 다운샘플이 ROI 매우 높음
- **모델 용량 3배 키웠는데 절대 성능은 비슷** → 이 데이터셋에서 yolo11s의 추가 capacity 이득 미미. 모델 용량 증가만으로는 한계
- **단, val 분포가 다름**: PC2 val은 cap=100으로 클래스 불균형이 완화된 평가셋이라 어려운 클래스 영향이 상대적으로 크게 반영됐을 가능성 → 보수적 평가일 수 있음
- 정확한 비교는 **PC1에서 yolov8n + balanced_500을 같은 val로 돌린 결과** 입수 필요

## 4. 클래스별 분석 (val 기준)

### 🟢 강한 클래스 (mAP50 ≥ 0.95) — 9개
| Class | AP50 | AP50-95 | val n |
|---|---:|---:|---:|
| black-bean-noodles | 0.995 | 0.995 | 50 |
| squid-dish | 0.995 | 0.995 | 20 |
| hamburger | 0.993 | 0.922 | 100 |
| fried-rice | 0.993 | 0.959 | 40 |
| dim-sum | 0.988 | 0.912 | 70 |
| braised-chicken | 0.977 | 0.942 | 70 |
| savory-pancake | 0.973 | 0.909 | 60 |
| braised-pork-hock | 0.972 | 0.972 | 30 |
| grilled-fish | 0.966 | 0.927 | 100 |

→ 시각적 특이성이 명확한 음식(짜장면 검정색, 오징어 모양, 햄버거 모양, 군만두 등)이 잘 잡힘

### 🔴 약한 클래스 (AP50 < 0.70) — 9개 ⭐ 후속 실험 우선 타겟

| 순위 | Class | AP50 | AP50-95 | Recall | val n | 추정 원인 |
|---:|---|---:|---:|---:|---:|---|
| 1 | mala-hot-pot | **0.266** | 0.229 | 0.217 | 60 | hot-pot/stew류 시각 혼동 |
| 2 | stir-fried-pork | **0.267** | 0.247 | **0.054** | 20 | val 표본 작음 + 다른 pork 혼동 |
| 3 | sweet-and-sour-pork | 0.443 | 0.426 | 0.256 | 40 | 갈색 소스 음식 혼동 |
| 4 | spicy-seafood-noodles | 0.478 | 0.466 | 0.520 | 100 | ramen/noodle-soup 혼동 |
| 5 | noodle-soup | 0.551 | 0.516 | 0.528 | 100 | ramen/spicy류 혼동 |
| 6 | seafood-stew | 0.556 | 0.521 | 0.600 | 100 | stew/hot-pot류 혼동 |
| 7 | takoyaki | 0.581 | 0.498 | 0.305 | 40 | dumplings류 혼동, val 작음 |
| 8 | stew | 0.622 | 0.603 | 0.680 | 100 | soup/hot-pot/seafood-stew 혼동 |
| 9 | rice-soup | 0.693 | 0.678 | 0.586 | 70 | porridge/soup 혼동 |

### 핵심 패턴 — 3개 혼동 군집

1. **국물·찌개 혼동 군 (8개)**: `soup`, `stew`, `hot-pot`, `noodle-soup`, `spicy-seafood-noodles`, `seafood-stew`, `rice-soup`, `mala-hot-pot`
   - 가장 큰 약점. 8개가 서로 시각적 유사 → confusion matrix 확인 필요
2. **돼지고기 요리 혼동 군**: `stir-fried-pork`, `sweet-and-sour-pork` (vs `grilled-pork-belly`, `pork-cutlet`)
3. **소수 표본 클래스**: `stir-fried-pork`(20), `squid-dish`(20), `chicken-galbi`(30), `braised-pork-hock`(30)
   - 일부는 좋고 일부는 나쁨 → val 부족이 결정 원인 아님. **train 표본의 다양성/질이 더 결정적**

## 5. 산출물 위치

- 학습: `runs/food_yolo/exp03_yolo11s_balanced500_pc2_b32_w8_cache_disk_det_true/`
  - `weights/best.pt` (19.2 MB), `weights/last.pt`
  - `results.csv`, `args.yaml`
- Validation: `runs/food_yolo/exp03_yolo11s_balanced500_pc2_val/`
  - `confusion_matrix.png`, `confusion_matrix_normalized.png`
  - `PR_curve.png`, `F1_curve.png`, `R_curve.png`, `P_curve.png`
  - `predictions.json`

## 6. 다음 작업

- [ ] confusion_matrix.png 시각 확인 → 국물·찌개 혼동 군 8개의 실제 혼동 방향 파악
- [ ] PC1의 yolov8n + balanced_500 결과 입수 → 같은 val 기준 직접 비교
- [ ] 비교 분석 후 exp04 설계 (옵션 후보):
  - (a) 약한 클래스 cap 상한 증가 (500 → 1000) 재학습
  - (b) augmentation 강화 (mosaic, mixup, copy-paste)
  - (c) yolo11m 등 더 큰 모델 시도 (단, batch=16 필요 예상)
  - (d) class-balanced loss 또는 focal loss 적용
- [ ] handoff §18 후속 실험 로드맵 갱신

## 7. 참조

- Spec: [docs/superpowers/specs/2026-05-27-aihub-yolo-balanced500-yolo11s-design.md](docs/superpowers/specs/2026-05-27-aihub-yolo-balanced500-yolo11s-design.md)
- Plan: [docs/superpowers/plans/2026-05-27-aihub-yolo-balanced500-yolo11s-plan.md](docs/superpowers/plans/2026-05-27-aihub-yolo-balanced500-yolo11s-plan.md)
- 일일 todo: [docs/superpowers/plans/2026-05-27-aihub-yolo-todo.md](docs/superpowers/plans/2026-05-27-aihub-yolo-todo.md)
