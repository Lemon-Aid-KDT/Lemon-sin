# 2026-05-21 AIHub YOLO Baseline TODO

## 오늘 완료

- AIHub 50클래스 YOLO 변환 결과를 최종 검증했다.
  - train images: 108,580
  - train labels: 108,580
  - val images: 13,780
  - val labels: 13,780
  - `data.yaml`의 `nc: 50` 및 클래스 50개 확인

- YOLO smoke test를 진행했다.
  - `yolov8n.pt`
  - `epochs=1`
  - `batch=16`
  - `workers=0`
  - smoke test run 결과 파일과 weight 생성 확인

- baseline 학습 설정을 검토하고 실제 baseline 진행 단계로 들어갔다.
  - 기본 모델: `yolov8n.pt`
  - 입력 크기: `imgsz=640`
  - seed: `42`
  - baseline 재현성을 위해 `deterministic=true` 유지 결정
  - 시각화 파일 생성 부담을 줄이기 위해 `plots=false` 사용 결정
  - `cache=disk`는 현재 환경에서 비효율적이라고 판단해 `cache=false`로 전환
  - 최종 시각화는 baseline 완료 후 별도 validation에서 생성하기로 결정

- GPU/CPU 리소스 사용 상태를 점검했다.
  - RTX 5060 Laptop GPU 8GB VRAM 사용 확인
  - Intel Arc 내장그래픽은 CUDA 학습용으로 적합하지 않으므로 RTX 5060 사용 유지
  - GPU 메모리 사용은 Windows 작업관리자 GPU 탭과 `nvidia-smi` 기준으로 확인했다.
  - baseline 진행 중 RTX 5060 전용 GPU 메모리가 약 5.6GB / 8GB 수준으로 사용되는 것을 확인했다.
  - GPU 온도는 약 55~56도 수준으로 확인되어 과열이나 thermal throttling 가능성은 낮다고 판단했다.
  - GPU 사용률이 오르내리는 원인은 내장그래픽 비활성화 문제가 아니라 DataLoader/CPU 데이터 공급 병목 가능성으로 판단했다.

## 오늘 트러블슈팅

### 1. baseline 학습 속도 문제

- 초기 baseline 설정은 `batch=32`, `workers=2`, `cache=false`였다.
- 실제 epoch에는 진입했지만 학습 속도가 약 `1 it/s` 수준으로 관측됐다.
- 50 epoch 전체 예상 시간이 약 46시간으로 계산되어 설정 최적화가 필요하다고 판단했다.

### 2. GPU 사용률이 낮아 보이는 문제

- 작업관리자 기준 GPU 사용률이 1~45% 사이에서 오르내리는 현상을 확인했다.
- 전용 GPU 메모리는 정상적으로 사용 중이었고, `nvidia-smi`와 작업관리자에서 VRAM 사용량 및 온도가 안정적인 것을 확인했다.
- batch 계산 후 다음 batch를 기다리는 패턴으로 해석했다.
- 원인은 GPU 자체 문제가 아니라 이미지 로딩, decode, DataLoader worker, Windows multiprocessing 병목 가능성이 높다고 판단했다.

### 3. `workers=4` 전환 후 Fast image access hang

- 속도 개선을 위해 `workers=4`를 시도했다.
- 이후 `Fast image access` 단계에서 장시간 멈추는 현상이 발생했다.
- 이후 `workers=2`로 되돌린 run에서도 같은 단계에서 멈춤이 발생했다.
- 따라서 `workers=4` 자체 문제라기보다, 이전 run 중단 후 Windows multiprocessing 리소스가 완전히 정리되지 않은 상태일 가능성을 검토했다.
  - shared memory
  - named pipe
  - CUDA context
  - Python child process
  - file handle

### 4. clean boot 필요성 판단

- run 간 중단/재시작 이후 DataLoader 초기화 문제가 반복됐다.
- PC 재시작을 통해 GPU 상태, Python worker, Windows multiprocessing 리소스를 초기화하는 방향으로 판단했다.
- 재시작 후 clean boot 상태에서 다시 baseline을 진행하기로 했다.

### 5. `cache=disk` 실험 중단

- 학습 속도 개선을 위해 `cache=disk`를 적용했다.
- 그러나 학습 시작 전에 전체 train 이미지 캐싱이 먼저 진행됐다.
- 캐싱 진행 상황:
  - 50% 진행
  - 약 54,805 / 108,580장
  - 약 62.7GB 사용
  - 경과 약 1시간 26분
  - 속도 약 `2.4 it/s`까지 하락
  - 남은 캐싱만 5~6시간 예상
- 실제 학습이 시작되기 전 대기 시간이 너무 길어 `cache=disk`는 현재 환경에 부적합하다고 판단했다.
- `cache=disk` run은 중단하고 `cache=false` baseline으로 전환하기로 했다.

## 최종 판단

- `cache=disk`는 현재 외장 D드라이브 환경에서 비효율적이다.
- baseline은 `cache=false`로 진행한다.
- baseline 비교 신뢰도를 위해 `deterministic=true`를 유지한다.
- `plots=false`로 학습 중 부가 시각화 생성을 줄이고, 학습 완료 후 별도 validation에서 시각화 결과를 생성한다.
- batch는 먼저 `48`을 시도하고, CUDA OOM 발생 시 `32`로 낮춘다.
- workers는 clean boot 후 `4`를 다시 시도하되, 같은 문제가 반복되면 `2`로 낮춘다.

## 다음 TODO

- baseline 완료 후 결과를 정리한다.
  - `results.csv`
  - `best.pt`
  - `last.pt`
  - mAP50
  - mAP50-95
  - precision
  - recall
  - epoch별 학습 시간
  - 최종 모델 크기

- baseline 완료 후 별도 validation을 실행한다.
  - `plots=true`
  - confusion matrix 생성
  - PR curve 생성
  - F1 curve 생성
  - results plot 생성

- baseline 결과를 바탕으로 다음 실험을 설계한다.
  - `yolov8s` 모델 크기 실험
  - 클래스별 AP 분석
  - confusion matrix 기반 혼동 클래스 분석
  - 소수 클래스 성능 분석
  - 직접 라벨링 데이터 기반 실제 환경 test 설계
