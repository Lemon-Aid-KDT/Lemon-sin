# 2026-05-22 AIHub YOLO 병렬 학습 및 Baseline TODO

## 오늘 완료

- 인수인계 문서 `2026-05-22-aihub-yolo-handoff.md`를 수정했다.
  - 현재 Git 기준 `data/` 폴더 구조 추가
  - 현재 학습 진행 상황 최신화
  - 현재 `deterministic=false` run은 최종 baseline이 아니라 정상 동작 확인용 run으로 분류
  - 실제 baseline은 `workers=8`, `cache=disk`, `deterministic=true`로 다시 실행하는 계획 반영

- 현재 baseline run의 성격을 재정의했다.
  - 현재 진행 중인 run:
    - `exp01_yolov8n_baseline_b48_w4_freshcache`
  - 이 run은 `deterministic=false`로 실행 중임을 확인했다.
  - 사용자는 baseline 재현성을 중요하게 보기 때문에, 이 run을 최종 baseline으로 보지 않기로 했다.
  - 현재 run은 학습 루프, GPU 사용, validation 저장, `best.pt` / `last.pt` 저장이 정상인지 확인하는 용도로 사용한다.
  - 실제 baseline은 `deterministic=true`로 다시 실행한다.

- 두 번째 컴퓨터에서 모델 학습을 병렬로 진행하는 방향을 검토했다.
  - 컴퓨터1: RTX 5060 Laptop
  - 컴퓨터2: RTX 4060 Laptop
  - 두 컴퓨터의 GPU 성능과 학습 환경이 다르므로 결과를 단순 비교하면 안 된다고 판단했다.

- 병렬 실험 설계 원칙을 정리했다.
  - 서로 다른 컴퓨터의 결과를 직접 비교하지 않는다.
  - 각 컴퓨터마다 먼저 baseline을 만든다.
  - 이후 실험 결과는 해당 컴퓨터의 baseline 대비 개선폭으로 비교한다.
  - 예:
    - 컴퓨터1 exp02 효과 = 컴퓨터1 exp02 - 컴퓨터1 baseline
    - 컴퓨터2 exp03 효과 = 컴퓨터2 exp03 - 컴퓨터2 baseline

- 컴퓨터2에서 바로 `yolov8s` 실험을 돌리는 계획을 보류했다.
  - 이유: 컴퓨터1 baseline과 컴퓨터2 exp02를 바로 비교하면 모델 차이와 하드웨어 차이가 섞인다.
  - 따라서 컴퓨터2도 먼저 `yolov8n` baseline을 실행하기로 했다.

- 컴퓨터2 baseline 실행 설정을 확정했다.
  - model: `yolov8n.pt`
  - epochs: `50`
  - imgsz: `640`
  - batch: `48`
  - workers: `8`
  - cache: `disk`
  - seed: `42`
  - deterministic: `true`
  - plots: `false`
  - run name: `exp01_yolov8n_baseline_pc2_b48_w8_cache_disk_det_true`

- 컴퓨터2 실행 시 fallback 기준을 정했다.
  - CUDA OOM 발생 시 `batch=32`로 낮춘다.
  - `cache=disk`가 지나치게 오래 걸리면 `cache=false` 전환을 검토한다.
  - `Fast image access` 이후 hang이 발생하면 `labels.cache` 손상을 먼저 의심한다.
  - `labels.cache`는 삭제하지 않고 archive 이동 후 fresh scan으로 재시작한다.

## 오늘 트러블슈팅

### 1. baseline 14epoch까지 진행하기 위한 안정화

- 이전까지 반복되던 `Fast image access` hang 문제는 `labels.cache` 손상이 핵심 원인으로 판단했다.
- `labels.cache`를 fresh scan하도록 정리한 뒤 학습이 정상적으로 epoch 루프에 진입했다.
- 이후 현재 run이 정상적으로 진행되며 baseline 확인용 학습이 14epoch까지 진행됐다.

- 학습 중 GPU 사용률이 일정하게 유지되지 않고 계속 튀는 현상을 확인했다.
  - GPU VRAM은 정상적으로 사용 중이었다.
  - GPU 온도도 안정적이었다.
  - 그러나 GPU utilization은 높게 고정되지 않고 오르내리는 패턴을 보였다.
- 이 현상은 GPU 연산 자체보다 다음 batch를 준비하는 과정에서 대기 시간이 발생하는 데이터 로딩 병목 가능성이 있다고 판단했다.
  - 이미지 파일 읽기
  - 이미지 decode
  - batch 구성
  - CPU/DataLoader worker 처리
  - GPU로 batch 전달
- 따라서 실제 baseline 재실행에서는 데이터 공급 병목을 줄이기 위해 `workers=8`로 올리고 `cache=disk`를 다시 시도하기로 했다.
  - `workers=8`: DataLoader 병렬 처리 증가 목적
  - `cache=disk`: 반복 epoch에서 이미지 로딩 비용 감소 목적
  - 단, `cache=disk`는 이전에 캐싱 시간이 길었던 이력이 있으므로 캐싱 속도와 epoch 진입 여부를 반드시 확인해야 한다.

- 확인한 사항:
  - `results.csv`가 epoch별로 갱신됨
  - `best.pt`, `last.pt` 생성 및 갱신됨
  - GPU VRAM 사용량 유지
  - GPU 온도 안정적
  - 학습 loss가 감소 추세
  - validation mAP가 상승 추세

- 판단:
  - 모델 학습 파이프라인 자체는 정상 작동한다.
  - 문제는 YOLO 설정 자체가 아니라 손상된 cache와 run 관리 방식에 있었다.
  - 추가로 GPU 사용률이 튀는 현상은 데이터 로딩 병목 가능성이 있으므로, 실제 baseline에서는 `workers=8`, `cache=disk` 설정으로 다시 검증한다.

## 오늘 판단한 핵심 내용

- 실험 신뢰도를 위해 두 컴퓨터 모두 baseline을 먼저 확보하는 방향이 더 타당하다.
- 속도 효율만 보면 컴퓨터1 baseline, 컴퓨터2 exp02 병렬 실행이 빠르지만, 포트폴리오용 실험 설계로는 설명력이 약하다.
- 이후 실험은 “절대 점수”보다 “각 컴퓨터 baseline 대비 개선폭”으로 해석해야 한다.
- 현재 `deterministic=false` run은 최종 baseline이 아니라 정상 동작 확인용으로만 사용한다.
- 실제 baseline은 `workers=8`, `cache=disk`, `deterministic=true` 조건으로 다시 실행한다.

## 진행 예정

- 컴퓨터2에 YOLO 변환 데이터셋을 복사한다.
  - 필수 경로:
    - `D:\Deeplearning\lemon\data\processed\aihub_yolo_50`
  - 포함 항목:
    - `data.yaml`
    - `yolo_class_index_50.json`
    - `train/images`
    - `train/labels`
    - `val/images`
    - `val/labels`
  - `labels.cache`는 복사하지 않아도 된다.

- 컴퓨터2에서 경로를 확인한다.
  - 경로가 같으면 `data.yaml` 수정 불필요
  - 경로가 다르면 `data.yaml`의 `path:` 수정 필요

- 컴퓨터2 Python/YOLO 환경을 확인한다.
  - Python 버전
  - PyTorch CUDA 사용 가능 여부
  - Ultralytics 버전
  - GPU 인식 여부
  - VRAM 용량

- 컴퓨터2 baseline을 실행한다.
  - 1차: `batch=48`, `workers=8`, `cache=disk`, `deterministic=true`
  - OOM 시: `batch=32`
  - cache 병목 심할 시: `cache=false` 검토

## 다음 TODO

- 컴퓨터1 정상 동작 확인용 run 상태를 최종 확인한다.
  - `exp01_yolov8n_baseline_b48_w4_freshcache`
  - 14epoch 이후 진행 상황 확인
  - 결과는 참고용으로만 보관

- 컴퓨터1 실제 baseline을 다시 실행한다.
  - `workers=8`
  - `cache=disk`
  - `deterministic=true`
  - cache 속도와 epoch 진입 여부 확인

- 컴퓨터1/컴퓨터2 baseline 완료 후 결과를 비교한다.
  - 단, 절대 점수 직접 비교가 아니라 각 컴퓨터 내부 기준으로 해석
  - mAP50
  - mAP50-95
  - precision
  - recall
  - epoch별 학습 시간
  - GPU/VRAM 사용량
  - best.pt 크기

- baseline 완료 후 다음 실험을 분배한다.
  - 컴퓨터1: `exp02_yolov8s_model_size`
  - 컴퓨터2: `exp03_augmentation` 또는 다른 단일 변수 실험

## 주의사항

- 서로 다른 컴퓨터의 실험 결과를 직접 비교하지 않는다.
- 각 실험은 반드시 같은 컴퓨터의 baseline 대비 개선폭으로 해석한다.
- 한 실험에서 여러 변수를 동시에 바꾸지 않는다.
- 대용량 데이터셋은 Git에 올리지 않는다.
- `data/food_images/scripts`, `data/food_images/manifests`는 Git에 포함되어야 다른 컴퓨터에서 재현 가능하다.
- `labels.cache`는 복사하지 않아도 되며, hang 발생 시 가장 먼저 의심한다.
- 압축이나 대용량 파일 복사는 학습 중 D드라이브 I/O 병목을 만들 수 있으므로 학습 시간과 분리해서 진행한다.
