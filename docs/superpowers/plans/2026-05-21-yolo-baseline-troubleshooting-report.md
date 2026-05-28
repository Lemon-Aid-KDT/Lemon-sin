# YOLO Baseline 학습 트러블슈팅 보고서

날짜: 2026-05-21  
환경: RTX 5060 Laptop 8GB / Python 3.13 / PyTorch 2.12 / Ultralytics 8.4.51 / Windows 11

## 1. 증상 요약

`yolo detect train` 실행 시 아래 메시지 이후 로그 출력이 멈추고 epoch 루프에 진입하지 못하는 hang이 반복 발생했다.

```text
AMP: checks passed
train: Fast image access (ping: X ms, read: X MB/s, size: 93.6 KB)
```

이후 20~30분 이상 새 출력이 없었다. 프로세스는 살아 있고 CPU 시간은 누적되지만, 실제 학습은 시작되지 않았다.

## 2. 시도 이력

| 순서 | 설정 | 결과 | 비고 |
| --- | --- | --- | --- |
| smoke test | `workers=0`, `batch=16` | 성공 | `labels.cache` 최초 생성 |
| exp01 1차 | `workers=2`, `batch=32` | epoch 진입 | step 725까지 진행 후 수동 중단 |
| exp01 2차 | `workers=4`, `batch=32` | hang | `Fast image access` 후 30분 이상 멈춤 |
| exp01 3차 | `workers=2`, `batch=32` | hang | force kill 이후 동일 증상 |
| cache=disk run | `workers=4`, `batch=48` | 캐싱 시작 | 이미지 캐싱 시간이 과도하게 길어 중단 |
| workers=2 재시도 | `workers=2`, `batch=48` | hang | clean boot 이후에도 동일 |
| workers=0 시도 | `workers=0`, `batch=48` | hang | multiprocessing 문제가 아님을 확인 |
| deterministic=false | `workers=0`, `batch=48` | hang | deterministic 설정 문제가 아님을 확인 |
| labels.cache 제거 후 | `workers=0`, `batch=48` | Scanning 시작 | 원인 확정 |

## 3. 오진 및 제거된 가설

| 가설 | 제거 근거 |
| --- | --- |
| `workers=4` Windows multiprocessing 문제 | `workers=0`에서도 동일하게 hang 발생 |
| force kill 이후 shared memory 잔여물 | PC 재시작 후에도 동일 증상 발생 |
| `deterministic=true` CUDA 충돌 | `deterministic=false`에서도 동일 증상 발생 |
| `cache=disk` 디스크 I/O 부족 | 캐싱 자체는 시작됐으므로 직접 원인은 아님 |
| GPU 수면 상태 | 이미 해결된 별도 문제로 판단 |

## 4. 근본 원인

근본 원인은 `labels.cache` 파일 손상 또는 불완전 쓰기로 판단했다.

대상 파일:

```text
D:\Deeplearning\lemon\data\processed\aihub_yolo_50\train\labels.cache
D:\Deeplearning\lemon\data\processed\aihub_yolo_50\val\labels.cache
```

판단 근거:

- smoke test 또는 첫 번째 run에서 cache가 생성됐다.
- 이후 여러 차례 강제 종료가 발생했다.
- 강제 종료 시점에 YOLO가 cache 파일을 쓰고 있었거나, 파일 핸들이 열린 상태로 종료되었을 가능성이 있다.
- 이후 모든 run에서 `Fast image access` 이후 손상된 cache를 읽으려다 silent hang이 발생한 것으로 판단된다.
- `workers=0`도 `labels.cache`를 읽기 때문에 동일하게 영향을 받았다.
- `labels.cache`를 제거한 뒤 재실행하자 `Scanning...` 진행률이 즉시 출력되며 정상 진행됐다.

첫 번째 run만 성공한 이유는 cache가 없어서 fresh scan을 진행했기 때문으로 판단했다. cache가 생성된 이후부터는 손상된 cache를 재사용하면서 hang이 반복됐다.

## 5. 해결책

`labels.cache`는 Ultralytics가 다시 생성할 수 있는 임시 cache 파일이다. 따라서 손상 의심 시 제거 후 재생성하면 된다.

다만 이 프로젝트의 작업 규칙상 파일을 바로 삭제하기보다 archive 폴더로 이동하는 방식을 기본으로 한다.

권장 조치:

```powershell
$archive = "D:\Deeplearning\lemon\data\archive\labels_cache_corrupt_20260521"
New-Item -ItemType Directory -Force -Path $archive

Move-Item "D:\Deeplearning\lemon\data\processed\aihub_yolo_50\train\labels.cache" $archive -Force
Move-Item "D:\Deeplearning\lemon\data\processed\aihub_yolo_50\val\labels.cache" $archive -Force
```

기술적으로는 삭제해도 재생성 가능한 파일이지만, 기본 운영 원칙은 archive 이동으로 둔다.

## 6. 향후 예방 조치

| 상황 | 조치 |
| --- | --- |
| 학습 중단이 필요할 때 | TaskStop 또는 Ctrl+C로 정상 종료 후 프로세스 완전 종료 확인 |
| 강제 종료 후 재시작 전 | `labels.cache` 상태 확인 |
| `Fast image access` 이후 hang 발생 | `labels.cache` 제거 또는 archive 이동을 1순위 조치로 수행 |
| workers 변경 검토 | cache 손상 가능성을 먼저 제거한 뒤 비교 |
| cache 파일 처리 | 삭제보다 archive 이동을 기본 원칙으로 적용 |

## 7. 현재 상태

`labels.cache` 제거 후 `exp01_yolov8n_baseline_b48_w0_fresh`를 재시작했다.

현재 상태:

- `Scanning...` 정상 진행 확인
- 스캔 속도 약 `295 it/s`
- scanning 완료 후 epoch 루프 진입 예정

## 8. 결론

이번 hang의 핵심 원인은 `workers`, `deterministic`, `cache=disk`, GPU 상태가 아니라 손상된 `labels.cache` 파일이었다.

앞으로 같은 증상이 발생하면 설정을 여러 차례 바꾸기 전에 다음 순서로 확인한다.

1. `labels.cache` 상태 확인
2. 의심 시 archive 이동
3. fresh scan으로 재실행
4. 이후 `workers`, `batch`, `cache` 설정 비교
