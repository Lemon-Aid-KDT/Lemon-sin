# 2026-05-25 작업 TODO

## 완료 ✅

- [x] exp01 PC1 baseline run 진행 모니터링
  - epoch 42 기준 mAP50=0.844 확인, 예상 완료 5월 26일(일) 오전

- [x] 이전 탐색 run vs 현재 공식 baseline 비교 분석
  - det=false(탐색) vs det=true(공식) 수렴 패턴 epoch별 비교
  - mAP50 차이 ±0.02 이내 — 사실상 동일한 학습 궤도 확인
  - 손실값(box_loss, cls_loss) 모두 epoch마다 0.001~0.02 이내 차이

- [x] workers=8 효과 없는 원인 분석
  - GPU 연산이 병목 (DataLoader는 GPU 대비 10배 이상 빠름)
  - batch=48, imgsz=640 기준 .npy 1 batch 로딩 약 0.1~0.2초 vs GPU 연산 약 1.9초
  - deterministic=true 로 인한 2~5% 속도 오버헤드는 정상 범위
  - 결론: workers/cache 튜닝이 아닌 GPU 업그레이드 또는 batch 증가가 속도 개선 방향

## 진행 중 🔄

- [ ] exp01 PC1 baseline run 완료 대기
  - epoch 42 / 50 완료, epoch당 약 75분
  - 예상 완료: 5월 26일(일) 오전
