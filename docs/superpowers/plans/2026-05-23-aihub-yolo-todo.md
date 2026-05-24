# 2026-05-23 작업 TODO

## 완료 ✅

- [x] handoff 문서 업데이트 (`2026-05-22-aihub-yolo-handoff.md`)
  - exp01 탐색 run 완료 상태 반영 (epoch 14, PC 전원 차단 종료, mAP50=0.808)
  - 섹션 12: 현재 run 상태 갱신 (탐색 run 완료 + PC1/PC2 baseline 예정)
  - 섹션 13: run 목록 상태 업데이트
  - 섹션 15.3: baseline 명령어에 pc1 suffix 적용
  - 섹션 17: 기준 수치 epoch 7 → epoch 14 최종으로 교체
  - 섹션 19: 병렬 컴퓨팅 프레임워크 전면 교체 (PC1/PC2 명령, 비교 원칙, cache 주의)
  - 섹션 22: 핵심 한 줄 갱신
  - 데이터셋 크기 오기 수정 (11~12 GB → 240 GB)

- [x] PC2 데이터 전송 방법 결정
  - 클라우드 전송 불가 확인
  - 결정: 물리 접근 가능 시점에 외장 SSD + robocopy로 전송

- [x] PC1 공식 baseline run 시작
  - name: `exp01_yolov8n_baseline_pc1_b48_w8_cache_disk_det_true`
  - 설정: deterministic=true, cache=disk, workers=8, batch=48, seed=42, epochs=50
  - 절전 모드 비활성화 후 실행
  - cache=disk 초기 캐싱 완료: 108,580개 .npy / 124.3 GB

- [x] 학습 진행 분석
  - epoch 9 기준 mAP50=0.776 — 이전 탐색 run과 수렴 패턴 거의 동일 확인
  - cache=disk + workers=8이 epoch 시간에 영향 없음 확인
  - 원인: GPU 연산이 병목 (DataLoader는 GPU보다 10배 이상 빠름)
  - deterministic=true로 인한 약 2~5% 속도 오버헤드 정상 범위

## 진행 중 🔄

- [ ] PC1 baseline run 완료 대기
  - 현재: epoch 9 완료 / 50 epochs 목표
  - epoch당 약 75분, 예상 완료: 5월 25일(일) 저녁

## 다음 작업 📋

- [ ] PC1 baseline 완료 후 validation plots 실행 (섹션 16 참조)
- [ ] PC2 물리 접근 시 데이터셋 전송 (외장 SSD + robocopy, 약 240 GB)
- [ ] PC2 Python/Ultralytics 환경 구성 후 baseline run 시작
- [ ] class별 AP, confusion matrix 분석
