# 2026-05-27 작업 TODO

## 완료 ✅

- [x] PC2 환경에서 데이터셋 외장 D드라이브 → 내장 C드라이브 이전
  - 출발지: `D:\Deeplearning\lemon\data\processed\aihub_yolo_50`
  - 도착지: `C:\Lemon-Aid\Lemon-sin\data\food_images\aihub_yolo_50`
  - 복사 범위: train/val의 jpg + txt만 (.npy 제외), 총 11.46 GB
  - 검증: train 108,580 / val 13,780 (전체 일치)
  - 방법: robocopy /MT:16 (jpg는 *.jpg 필터, txt는 *.txt 필터)

- [x] data.yaml path 수정
  - `path: D:/Deeplearning/lemon/data/processed/aihub_yolo_50` → `path: C:/Lemon-Aid/Lemon-sin/data/food_images/aihub_yolo_50`

- [x] baseline_run.ps1 재작성
  - 경로: `C:\Lemon-Aid\Lemon-sin\docs\superpowers\plans\baseline_run.ps1`
  - 이전 버전이 git untracked였고 git checkout 후 사라져서 새로 작성
  - 인터랙티브 Read-Host 프롬프트 제거 → labels.cache 자동 archive 이동
  - 사전 점검 추가 (yolo.exe, data.yaml, GPU, CUDA, 데이터 개수, C 여유)
  - 설정은 handoff §19.4 PC2 baseline 그대로 유지

- [x] cache=ram / cache=False 실험 실패 원인 학습
  - cache=ram: 186GB RAM 필요 → 자동 fallback → GPU 1%로 굶음 (CPU-bound)
  - cache=False: 워커 8개로 부족, 외장 SSD 1GB/s여도 augmentation CPU 병목
  - 결론: handoff 권장대로 cache=disk가 정답

## 진행 중 🔄

- [x] **계획 변경**: yolov8n 풀데이터 baseline 대신 yolo11s + balanced_500으로 방향 전환 (2026-05-27)
  - spec/plan 신규 작성: [2026-05-27-aihub-yolo-balanced500-yolo11s-design.md](2026-05-27-aihub-yolo-balanced500-yolo11s-design.md), [-plan.md](2026-05-27-aihub-yolo-balanced500-yolo11s-plan.md)
  - val도 cap=100으로 다운샘플 (모델 적합성 빠른 검증용)
- [x] exp03 YOLO11s + balanced_500 PC2 학습 완료 (2026-05-28)
  - 50/50 epoch, 10.46 시간 소요
  - best mAP50=0.823, mAP50-95=0.788 (epoch 48)
  - 결과 분석: [2026-05-28-exp03-yolo11s-balanced500-results.md](2026-05-28-exp03-yolo11s-balanced500-results.md)

## 다음 작업 📋

- [x] exp03 validation plots 실행 → confusion_matrix.png, PR/F1/R/P curves, predictions.json 생성 (2026-05-28)
- [x] 약한 클래스 9개 식별 (AP50 < 0.70): mala-hot-pot, stir-fried-pork, sweet-and-sour-pork, spicy-seafood-noodles, noodle-soup, seafood-stew, takoyaki, stew, rice-soup
- [x] 핵심 패턴 파악: 국물·찌개 혼동 군(8개), 돼지고기 혼동 군(2개), 소수 표본 클래스(4개)
- [ ] confusion_matrix.png 시각 확인 → 국물·찌개 8개 클래스 혼동 방향 파악
- [ ] PC1의 yolov8n + balanced_500 결과 입수 → 같은 val 기준 직접 비교
- [ ] exp04 설계 (약한 클래스 보강): cap 증가 / augmentation 강화 / 더 큰 모델 / class-balanced loss 중 선택

## 환경 스냅샷

| 항목 | 값 |
| --- | --- |
| 브랜치 | `docs/data-yolo-food-detection` |
| 최근 커밋 | `c1a2fb2 data(data): exp01 YOLOv8n PC1 baseline 학습 결과 추가` |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU (8188 MiB) |
| Python | 3.13.13 |
| PyTorch | 2.6.0 + CUDA 12.4 |
| Ultralytics | 8.4.51 |
| 데이터셋 | `C:\Lemon-Aid\Lemon-sin\data\food_images\aihub_yolo_50` (11.46 GB) |
| runs 폴더 | `C:\Lemon-Aid\Lemon-sin\runs\food_yolo` (PC1 결과 이미 복사됨) |
| C 드라이브 여유 | 약 416 GB (cache=disk 130 GB 사용 예정) |
| labels.cache | 없음 (fresh scan 예정) |

## 주의사항 (이전 시도에서 학습)

- **cache=ram은 절대 사용 금지**: 186GB RAM 필요로 fallback되어 GPU 1%로 굶음
- **학습 띄운 콘솔은 절대 닫지 말 것**: 이전 세션에서 프로세스 트리 정리하다 학습 죽은 적 있음
- **robocopy 종료 코드 0~7은 모두 정상** (1=정상 복사 완료). PowerShell이 `$LASTEXITCODE=1`을 실패로 잡을 수 있으나 결과만 검증하면 됨
- **인터랙티브 Read-Host는 별도 콘솔 stdin으로 주입 불가** → baseline_run.ps1은 자동 처리하도록 작성됨
- **untracked 파일은 git checkout 시 사라질 수 있음**: baseline_run.ps1이 사라진 사례 발생 → 새로 작성 후 commit 검토 필요

## 참고 문서

- `docs/superpowers/plans/2026-05-22-aihub-yolo-handoff.md` — 전체 인수인계, 병렬 학습 계획
- `docs/superpowers/plans/2026-05-26-aihub-yolo-todo.md` — PC1 baseline 완료 기록, exp02 YOLO11s 시작
- `docs/superpowers/plans/2026-05-25-aihub-yolo-todo.md` — workers/cache 효과 없음 원인 분석
- `docs/superpowers/plans/2026-05-23-aihub-yolo-todo.md` — PC1 baseline 시작 기록
- `docs/superpowers/plans/2026-05-21-yolo-baseline-troubleshooting-report.md` — labels.cache 손상 hang 트러블슈팅
