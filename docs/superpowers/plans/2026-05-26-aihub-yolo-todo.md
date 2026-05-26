# 2026-05-26 작업 TODO

## 완료 ✅

- [x] exp01 YOLOv8n PC1 baseline run 최종 완료
  - 총 epoch: 50 / 50 (patience 미발동, 끝까지 수렴)
  - 총 학습 시간: 69.7시간
  - Best epoch 45 기준: mAP50=0.8465, mAP50-95=0.8181, P=0.8168, R=0.7983
  - 학습 곡선: epoch 1(0.379) → epoch 20(0.827) → epoch 45(0.846, best) → epoch 50(0.839)
  - best.pt / last.pt: C:\Lemon-sin\runs\food_yolo\exp01_yolov8n_baseline_pc1_b48_w8_cache_disk_det_true\weights\

- [x] 데이터 및 runs 경로 C 드라이브로 이전
  - 데이터셋 이동: D:\Deeplearning\... → C:\Lemon-sin\data\food_images\processed\aihub_yolo_50
  - data.yaml path 업데이트 완료
  - runs 폴더 복사: D:\Deeplearning\... → C:\Lemon-sin\runs\food_yolo
  - 외장 D드라이브 연결 해제 (PC2 데이터 전송용으로 이동 예정)

- [x] exp02 YOLO11s 실행 준비 및 시작
  - batch=48 시도 → VRAM 8151 MB 초과, OOM으로 run 폴더 미생성
  - batch=32로 fallback 후 정상 시작
  - name: exp02_yolo11s_pc1_b32_w8_cache_disk_det_true
  - .npy 캐시 재사용 (exp01에서 생성된 108,580개) → 초기 캐싱 없이 바로 epoch 1 진입

- [x] 팀 협업 문서 규칙 파악 및 브랜치 전략 적용 준비
  - BRANCH_STRATEGY.md, COMMIT_CONVENTION.md, DEVELOP_WORKFLOW.md, PR_GUIDELINES.md 숙지
  - 현재 브랜치 jongpil-tech → 규칙 위반 확인 (작업자 이름 기반)
  - origin/develop 존재 확인 (git fetch 후 확인)
  - 새 브랜치 생성 예정: docs/data-yolo-food-detection

## 진행 중 🔄

- [ ] exp02 YOLO11s PC1 run 완료 대기
  - name: exp02_yolo11s_pc1_b32_w8_cache_disk_det_true
  - epochs=50, batch=32, deterministic=true, cache=disk

## 다음 작업 📋

- [ ] exp01 baseline validation plots 실행 (class별 AP, confusion matrix)
- [ ] exp02 YOLO11s 완료 후 exp01 vs exp02 비교 분석
- [ ] PC2 물리 접근 시 외장 D드라이브로 데이터셋 전송 후 PC2 baseline 시작
- [ ] jongpil-tech 브랜치 → docs/data-yolo-food-detection 으로 마이그레이션
