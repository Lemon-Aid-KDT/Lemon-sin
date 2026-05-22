# 2026-05-22 AIHub YOLO 모델링 인수인계 문서

작성일: 2026-05-22  
대상 작업: AIHub 음식 이미지 기반 YOLO 50클래스 baseline 학습 및 이후 모델링 실험  
현재 저장소: `C:\Lemon-sin`  
현재 브랜치: `jongpil-tech`

## 1. 프로젝트 목표

현재 작업의 목표는 AIHub 음식 이미지 데이터를 Roboflow 라벨링 기준 50개 음식 클래스로 맞춘 뒤, YOLO 객체 탐지 모델을 학습하고 성능 개선 실험을 이어가는 것이다.

중요한 방향은 단순히 "YOLOv8을 실행했다"가 아니라, 아래 흐름을 남기는 것이다.

1. 데이터 기준을 명확히 정한다.
2. Roboflow 50개 클래스와 AIHub 세부 class_id를 매핑한다.
3. AIHub 원본 데이터를 YOLO 학습 형식으로 변환한다.
4. baseline을 먼저 만든다.
5. baseline 결과에서 약한 클래스를 찾는다.
6. 클래스 설계, 모델 크기, 증강, 불균형 처리, 실제 사진 평가를 순서대로 실험한다.
7. 각 실험의 Before/After를 수치와 근거로 기록한다.

포트폴리오 관점에서 핵심은 최종 mAP 하나가 아니라, 왜 성능이 그렇게 나왔고 어떤 판단으로 무엇을 바꿨는지의 의사결정 기록이다.

## 2. 현재 핵심 결론

- AIHub 50클래스 YOLO 데이터셋 변환은 완료됐다.
- 현재 학습 데이터셋은 `D:\Deeplearning\lemon\data\processed\aihub_yolo_50`에 있다.
- 현재 `exp01_yolov8n_baseline_b48_w4_freshcache` run은 정상 동작 확인용으로 진행 중이다.
- 현재 run은 `deterministic=false`로 실행 중이므로 최종 baseline으로 확정하지 않는다.
- 현재 run은 학습 루프, GPU 사용, cache 재생성, validation 저장이 정상 동작하는지 확인하는 용도다.
- 정상 동작 확인 후 실제 baseline은 `workers=8`, `cache=disk`, `deterministic=true` 조건으로 다시 실행할 계획이다.
- `Fast image access` 이후 hang의 근본 원인은 `labels.cache` 손상으로 판단했다.
- `cache=disk`는 현재 외장 D드라이브 환경에서 비효율적이었다.
- Training 원본 이미지 압축 세트 `TS.zip + TS.z01~TS.z07`은 공간 확보를 위해 삭제된 상태다.
- Validation 원본 이미지 압축 `VS.zip`은 남아 있다.
- 현재 학습은 원본 zip이 아니라 변환 완료된 YOLO 데이터셋만 참조한다.

## 3. 반드시 복사하거나 커밋해야 하는 항목

다른 컴퓨터에서 이어받으려면 Git 저장소만으로는 부족하다. 대용량 데이터와 run 결과는 Git에 들어가지 않는다.

### 3.1 Git으로 가져갈 파일

저장소 경로:

```text
C:\Lemon-sin
```

중요한 작업 파일:

```text
C:\Lemon-sin\data\food_images\scripts\convert_aihub_50_to_yolo.py
C:\Lemon-sin\data\food_images\manifests\roboflow_aihub_class_map_50.csv
C:\Lemon-sin\data\food_images\manifests\roboflow_autolabel_food_prompts_50_aihub_aligned.csv
C:\Lemon-sin\docs\superpowers\plans\2026-05-19-aihub-yolo-todo.md
C:\Lemon-sin\docs\superpowers\plans\2026-05-20-aihub-yolo-modeling-todo.md
C:\Lemon-sin\docs\superpowers\plans\2026-05-21-aihub-yolo-study-guide.md
C:\Lemon-sin\docs\superpowers\plans\2026-05-21-aihub-yolo-baseline-todo.md
C:\Lemon-sin\docs\superpowers\plans\2026-05-21-yolo-baseline-troubleshooting-report.md
C:\Lemon-sin\docs\superpowers\plans\2026-05-22-aihub-yolo-handoff.md
```

주의:

- 현재 `data/food_images/` 전체가 Git에서 untracked로 보인다.
- 다른 컴퓨터에서 Git clone만 할 계획이면 `data/food_images/scripts`와 `data/food_images/manifests`를 반드시 commit하거나 별도로 복사해야 한다.
- `.venv`는 Git에 넣지 않는다. 다른 컴퓨터에서 새로 환경을 만든다.

### 3.2 Git으로 가져가지 않는 대용량 파일

다른 컴퓨터에서 바로 학습하려면 아래 폴더를 별도로 복사해야 한다.

필수:

```text
D:\Deeplearning\lemon\data\processed\aihub_yolo_50
```

현재 baseline을 이어서 학습하려면 추가로 필요:

```text
D:\Deeplearning\lemon\runs\food_yolo\exp01_yolov8n_baseline_b48_w4_freshcache
```

학습 기록 전체를 보존하려면:

```text
D:\Deeplearning\lemon\runs\food_yolo
```

### 3.3 현재 Git data 폴더 구조

현재 저장소의 `data/` 폴더는 코드/문서와 함께 버전 관리되는 경량 데이터 기준 폴더다. 대용량 AIHub 이미지와 YOLO 변환 결과는 Git에 넣지 않는다.

현재 로컬 구조:

```text
C:\Lemon-sin\data
├── README.md
├── food_images/
│   ├── .gitignore
│   ├── README.md
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   ├── splits/
│   ├── manifests/
│   │   ├── roboflow_aihub_class_map_50.csv
│   │   └── roboflow_autolabel_food_prompts_50_aihub_aligned.csv
│   ├── quarantine/
│   └── scripts/
│       └── convert_aihub_50_to_yolo.py
├── meal_vision/
│   ├── README.md
│   ├── classes.yaml
│   ├── dataset.yaml
│   └── mock_predictions.json
└── rda/
    ├── food_aliases.json
    └── korean_foods.csv
```

현재 Git에서 추적 중인 `data/` 파일:

```text
data/README.md
data/meal_vision/README.md
data/meal_vision/classes.yaml
data/meal_vision/dataset.yaml
data/meal_vision/mock_predictions.json
data/rda/food_aliases.json
data/rda/korean_foods.csv
```

주의:

- `data/food_images/`는 현재 로컬에는 있지만 Git 기준으로는 아직 untracked 상태다.
- 다른 컴퓨터에서 Git clone만으로 이어받으려면 `data/food_images/manifests`와 `data/food_images/scripts`를 commit해야 한다.
- `data/food_images/raw`, `interim`, `processed`, `quarantine`, `splits`는 대용량 또는 임시 산출물 위치이므로 `.gitkeep`, README, manifest 등 경량 파일만 Git에 포함하는 것이 원칙이다.
- 실제 학습 데이터셋 `D:\Deeplearning\lemon\data\processed\aihub_yolo_50`는 Git 바깥의 외부 데이터 경로다.

## 4. 데이터셋 상태

YOLO 변환 결과:

```text
D:\Deeplearning\lemon\data\processed\aihub_yolo_50
```

검증된 파일 수:

| split | images | labels |
| --- | ---: | ---: |
| train | 108,580 | 108,580 |
| val | 13,780 | 13,780 |

필수 파일:

```text
D:\Deeplearning\lemon\data\processed\aihub_yolo_50\data.yaml
D:\Deeplearning\lemon\data\processed\aihub_yolo_50\yolo_class_index_50.json
D:\Deeplearning\lemon\data\processed\aihub_yolo_50\train\images
D:\Deeplearning\lemon\data\processed\aihub_yolo_50\train\labels
D:\Deeplearning\lemon\data\processed\aihub_yolo_50\val\images
D:\Deeplearning\lemon\data\processed\aihub_yolo_50\val\labels
```

현재 cache 파일:

```text
D:\Deeplearning\lemon\data\processed\aihub_yolo_50\train\labels.cache
D:\Deeplearning\lemon\data\processed\aihub_yolo_50\val\labels.cache
```

주의:

- `labels.cache`는 재생성 가능한 파일이다.
- 다른 컴퓨터로 복사할 때 cache 파일은 필수가 아니다.
- `Fast image access` 이후 hang이 발생하면 `labels.cache`를 archive 이동 후 fresh scan으로 다시 시작한다.

## 5. 클래스 목록

YOLO `data.yaml` 기준 class order:

| index | class |
| ---: | --- |
| 0 | salad |
| 1 | mixed-rice-bowl |
| 2 | rice-bowl |
| 3 | fried-rice |
| 4 | rice-soup |
| 5 | rice-porridge |
| 6 | seaweed-rice-roll |
| 7 | spicy-rice-cakes |
| 8 | dumplings |
| 9 | fish-cake |
| 10 | fried-food-platter |
| 11 | savory-pancake |
| 12 | korean-blood-sausage |
| 13 | takoyaki |
| 14 | soup |
| 15 | stew |
| 16 | hot-pot |
| 17 | noodle-soup |
| 18 | cold-noodles |
| 19 | spicy-mixed-noodles |
| 20 | ramen |
| 21 | black-bean-noodles |
| 22 | spicy-seafood-noodles |
| 23 | fried-chicken |
| 24 | pork-cutlet |
| 25 | grilled-pork-belly |
| 26 | grilled-beef |
| 27 | barbecue-ribs |
| 28 | bulgogi |
| 29 | stir-fried-pork |
| 30 | braised-chicken |
| 31 | chicken-galbi |
| 32 | braised-pork-hock |
| 33 | grilled-fish |
| 34 | raw-fish |
| 35 | sushi |
| 36 | seafood-stew |
| 37 | shrimp-dish |
| 38 | squid-dish |
| 39 | sweet-and-sour-pork |
| 40 | mala-hot-pot |
| 41 | dim-sum |
| 42 | udon |
| 43 | pasta |
| 44 | pizza |
| 45 | hamburger |
| 46 | sandwich |
| 47 | curry |
| 48 | bread |
| 49 | cake |

## 6. 클래스 매핑 상태

매핑 파일:

```text
C:\Lemon-sin\data\food_images\manifests\roboflow_aihub_class_map_50.csv
```

매핑 상태:

| status | count |
| --- | ---: |
| exact_or_close | 32 |
| broad_semantic | 9 |
| review_needed | 9 |

원본 Roboflow CSV는 수정하지 않았다.

원본:

```text
C:\Users\KDS11\Downloads\roboflow_autolabel_food_prompts_50.csv
```

AIHub 매칭 완료 새 CSV:

```text
C:\Lemon-sin\data\food_images\manifests\roboflow_autolabel_food_prompts_50_aihub_aligned.csv
```

처음 Roboflow 50개 목록 중 AIHub와 직접 매칭이 안 되던 5개는 아래처럼 교체했다.

| 기존 클래스 | 교체 클래스 |
| --- | --- |
| steamed-rice | salad |
| kimchi | korean-blood-sausage |
| vegetable-side-dish | takoyaki |
| boiled-pork | chicken-galbi |
| tempura | udon |

교체 기준:

- AIHub에 실제 이미지/라벨이 존재해야 한다.
- Roboflow 라벨링 목적에 맞게 사용자가 자주 접할 수 있는 음식이어야 한다.
- 50개 클래스 수는 유지한다.
- 원본 다운로드 CSV는 수정하지 않는다.

## 7. AIHub bbox 해석

샘플 시각화 검토 결과, AIHub bbox는 음식 알맹이만 타이트하게 감싸는 방식이 아니라 접시, 그릇, 포장 용기까지 포함한 "음식 제공 단위"에 가깝다.

따라서 현재 모델은 아래 성격으로 보는 것이 맞다.

| 항목 | 해석 |
| --- | --- |
| 모델 종류 | 음식 객체 탐지 |
| bbox 의미 | 음식 + 접시/그릇/용기 포함 가능 |
| 적합한 목적 | 사진 안에서 어떤 음식이 어디 있는지 찾기 |
| 부적합한 목적 | 음식 픽셀만 정확히 분리 |

음식 영역을 픽셀 단위로 분리하려면 detection이 아니라 segmentation 데이터와 모델이 필요하다.

## 8. 직접 라벨링 데이터 운영 기준

AIHub는 단일 음식 중심 이미지가 많다. 직접 라벨링한 실제 사진은 메인 음식과 반찬이 같이 있을 가능성이 높다.

현재 결정:

- AIHub 데이터는 학습/기본 검증용으로 사용한다.
- 직접 라벨링 데이터는 우선 검증/테스트용으로 사용한다.
- 직접 라벨링 이미지는 강제 640x640 resize를 하지 않는다.
- 원본 이미지 비율을 유지하고 YOLO normalized label을 사용한다.
- Ultralytics가 train/val/infer 시 내부 letterbox를 처리하게 두는 것이 더 안전하다.

주의:

- 실제 사진에서 메인 음식만 라벨링하고 반찬을 라벨링하지 않으면, 일반 mAP 평가에서 모델이 반찬을 탐지했을 때 false positive로 잡힐 수 있다.
- 따라서 직접 라벨링 데이터는 `main_only` test와 `real_world_mixed` test를 분리하는 것이 좋다.

## 9. 변환 스크립트

스크립트:

```text
C:\Lemon-sin\data\food_images\scripts\convert_aihub_50_to_yolo.py
```

주요 기능:

- Roboflow 50클래스 매핑 적용
- AIHub label JSON 스캔
- TS/VS zip에서 필요한 class chunk만 임시 추출
- 이미지 640x640 직접 resize
- YOLO label txt 생성
- `data.yaml` 생성
- `yolo_class_index_50.json` 생성
- `--resume` 이어받기
- `--cleanup-mode archive|delete|keep`
- `--max-runtime-minutes`

중요한 변환 방식:

- AIHub 변환 이미지는 640x640으로 직접 resize됐다.
- crop이 아니다.
- letterbox가 아니다.
- 원본 비율이 다른 이미지는 약간 찌그러질 수 있다.

이 방식은 AIHub baseline 확보를 위해 유지했다. 직접 라벨링 데이터는 별도 변환 정책을 사용해야 한다.

## 10. 원본 데이터 상태

AIHub 원본 루트:

```text
D:\Deeplearning\lemon\data\raw\aihub\data
```

현재 상태:

| 항목 | 상태 |
| --- | --- |
| Training raw `TS.zip + TS.z01~TS.z07` | 삭제됨 |
| Validation raw `VS.zip` | 남아 있음 |
| Training/Validation label JSON | 남아 있는 것으로 전제 |
| YOLO 변환 완료 데이터셋 | 존재 |

중요:

- Training 원본 이미지 압축 세트는 삭제됐다.
- 따라서 AIHub train 원본 이미지에서 다시 변환해야 하는 작업은 재다운로드 없이는 불가능하다.
- 현재 학습에는 원본 TS 압축 세트가 필요 없다.
- 현재 학습은 `processed\aihub_yolo_50`만 사용한다.

## 11. Python / GPU 환경

사용자 환경:

```text
Python: 3.13.13
venv: C:\Lemon-sin\backend\.venv
PyTorch: 2.12.0.dev + CUDA 12.8
torchvision: 0.27.0.dev + cu128
Ultralytics: 8.4.51
GPU: RTX 5060 Laptop 8GB
OS: Windows 11
```

중요한 배경:

- RTX 5060 Laptop은 Blackwell 계열 GPU다.
- 일반 PyTorch stable CUDA 12.4 조합에서는 sm_120 지원 문제가 있었다.
- PyTorch nightly + CUDA 12.8 조합으로 GPU 인식 문제를 해결했다.

다른 컴퓨터에서 이어받을 때:

- NVIDIA GPU가 Blackwell이면 PyTorch nightly/cu128 이상 조합이 필요할 수 있다.
- NVIDIA GPU가 Ada/Ampere라면 stable PyTorch CUDA 버전으로도 가능할 수 있다.
- 같은 실험을 재현하려면 Python, PyTorch, Ultralytics 버전을 기록해야 한다.

가상환경 활성화:

```powershell
C:\Lemon-sin\backend\.venv\Scripts\Activate.ps1
```

YOLO 실행 파일:

```powershell
C:\Lemon-sin\backend\.venv\Scripts\yolo.exe
```

## 12. 현재 run 상태

현재 진행 중인 정상 동작 확인용 run:

```text
D:\Deeplearning\lemon\runs\food_yolo\exp01_yolov8n_baseline_b48_w4_freshcache
```

현재 run 설정:

| 항목 | 값 |
| --- | --- |
| model | `yolov8n.pt` |
| epochs | 50 |
| imgsz | 640 |
| batch | 48 |
| workers | 4 |
| cache | false |
| device | 0 |
| seed | 42 |
| deterministic | false |
| patience | 15 |
| plots | false |
| val | true |
| amp | true |

주의:

- 사용자는 baseline 재현성을 위해 `deterministic=true`를 선호했다.
- 하지만 현재 실제 실행 중인 run의 `args.yaml`은 `deterministic: false`다.
- 따라서 이 run은 최종 baseline이 아니라 정상 동작 확인용 run으로 본다.
- 이 run으로 학습 루프, GPU 사용, validation 저장, `best.pt`/`last.pt` 저장이 정상임을 확인한다.
- 실제 baseline은 이 run 이후 `workers=8`, `cache=disk`, `deterministic=true`로 다시 실행할 계획이다.

현재 기록된 마지막 결과:

| epoch | precision | recall | mAP50 | mAP50-95 | train box | train cls | train dfl |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 11 | 0.76156 | 0.72832 | 0.79468 | 0.72881 | 0.63296 | 0.94570 | 1.15813 |

현재 결과 파일:

```text
D:\Deeplearning\lemon\runs\food_yolo\exp01_yolov8n_baseline_b48_w4_freshcache\results.csv
D:\Deeplearning\lemon\runs\food_yolo\exp01_yolov8n_baseline_b48_w4_freshcache\weights\best.pt
D:\Deeplearning\lemon\runs\food_yolo\exp01_yolov8n_baseline_b48_w4_freshcache\weights\last.pt
```

현재 GPU 사용 상태 확인 시점:

```text
GPU memory: 약 7296 MB / 8151 MB
GPU temperature: 약 53도
```

## 13. 이전 run 목록

중요 run:

| run | 상태 | 메모 |
| --- | --- | --- |
| `exp00_smoke_yolov8n` | 성공 | `epochs=1`, `batch=16`, `workers=0` |
| `exp01_yolov8n_baseline` | 중단 | `batch=32`, `workers=2`; epoch 진입 성공, step 725 부근까지 진행 |
| `exp01_yolov8n_baseline_w4` | 실패 | `workers=4`; `Fast image access` 후 hang |
| `exp01_yolov8n_baseline_b48_w4_cleanboot_cachefalse` | 실패 | clean boot 후에도 hang; 이후 cache 손상 원인 확인 |
| `exp01_yolov8n_baseline_cache_disk_b48_w4_cleanboot` | 중단 | `cache=disk`; 캐싱 시간이 과도하게 길어 중단 |
| `exp01_yolov8n_baseline_b48_w4_freshcache` | 진행 중 | `labels.cache` fresh scan 후 정상 진행. 최종 baseline이 아니라 정상 동작 확인용 |

중단 run 폴더는 삭제하지 않는다. 정리가 필요하면 archive 폴더로 이동한다.

## 14. 주요 트러블슈팅 결론

### 14.1 Fast image access hang

증상:

```text
AMP: checks passed
train: Fast image access ...
```

이후 epoch 루프에 진입하지 않고 새 로그가 나오지 않았다.

최종 원인:

- `labels.cache` 파일 손상 또는 불완전 쓰기

손상 의심 파일:

```text
D:\Deeplearning\lemon\data\processed\aihub_yolo_50\train\labels.cache
D:\Deeplearning\lemon\data\processed\aihub_yolo_50\val\labels.cache
```

원인 추정:

- 학습 중 force kill 또는 강제 중단이 발생했다.
- Ultralytics가 cache를 쓰거나 읽는 도중 프로세스가 종료됐을 가능성이 있다.
- 이후 모든 run이 손상된 cache를 읽으며 silent hang이 발생했다.

해결:

- `labels.cache`를 archive 이동한다.
- fresh scan으로 재시작한다.

권장 archive 명령:

```powershell
$archive = "D:\Deeplearning\lemon\data\archive\labels_cache_corrupt_20260521"
New-Item -ItemType Directory -Force -Path $archive

Move-Item "D:\Deeplearning\lemon\data\processed\aihub_yolo_50\train\labels.cache" $archive -Force
Move-Item "D:\Deeplearning\lemon\data\processed\aihub_yolo_50\val\labels.cache" $archive -Force
```

기술적으로는 삭제해도 재생성 가능하지만, 프로젝트 규칙상 삭제보다 archive 이동을 기본으로 한다.

### 14.2 workers 문제

초기에는 `workers=4`가 Windows multiprocessing 문제라고 의심했다.

하지만 이후 `workers=0`에서도 동일 hang이 발생했다. 따라서 근본 원인은 workers 수가 아니라 손상된 `labels.cache`로 판단했다.

현재 fresh cache 상태에서는 `workers=4` run이 정상 진행 중이다.

### 14.3 cache=disk 문제

`cache=disk`는 학습 시작 전 train 이미지 전체를 디스크에 캐싱했다.

관측:

```text
50% 진행
약 54,805 / 108,580장
약 62.7GB 사용
경과 약 1시간 26분
속도 약 2.4 it/s까지 하락
남은 캐싱만 5~6시간 예상
```

결론:

- 현재 외장 D드라이브 환경에서는 `cache=disk`가 비효율적이다.
- baseline은 `cache=false`로 진행하는 것이 낫다.

### 14.4 GPU 사용률 해석

작업관리자 GPU 사용률은 CUDA 학습 상태를 정확히 보여주지 못할 수 있다.

더 신뢰할 기준:

```powershell
nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader,nounits
```

해석:

- VRAM이 안정적으로 올라가 있으면 모델과 batch는 GPU에 올라간 상태다.
- GPU 사용률이 톱니처럼 오르내릴 수 있다.
- 이는 batch 계산과 데이터 준비가 반복되는 정상 패턴일 수 있다.
- GPU 온도와 VRAM 사용량도 함께 봐야 한다.

## 15. 다른 컴퓨터에서 이어받는 방법

### 15.1 데이터 복사

다른 컴퓨터에서도 같은 경로를 쓰는 것이 가장 편하다.

권장 경로:

```text
D:\Deeplearning\lemon\data\processed\aihub_yolo_50
D:\Deeplearning\lemon\runs\food_yolo
C:\Lemon-sin
```

경로가 달라지면 `data.yaml`의 `path`를 수정해야 한다.

현재 `data.yaml`은 아래를 가리킨다.

```yaml
path: D:/Deeplearning/lemon/data/processed/aihub_yolo_50
train: train/images
val: val/images
nc: 50
```

### 15.2 현재 baseline을 resume하는 명령

현재 run을 다른 컴퓨터에서 이어서 돌릴 경우:

```powershell
$yolo = "C:\Lemon-sin\backend\.venv\Scripts\yolo.exe"

& $yolo detect train `
  model="D:\Deeplearning\lemon\runs\food_yolo\exp01_yolov8n_baseline_b48_w4_freshcache\weights\last.pt" `
  resume=true
```

주의:

- resume은 기존 `args.yaml` 설정을 따라간다.
- 현재 run은 `deterministic=false`다.
- 다른 컴퓨터에서 GPU/Ultralytics 버전이 다르면 완전히 같은 결과가 나오지 않을 수 있다.

### 15.3 실제 baseline을 새로 시작하는 명령

현재 `deterministic=false` run은 정상 동작 확인용이다. 실제 baseline은 아래 설정으로 새로 시작한다.

계획 설정:

| 항목 | 값 |
| --- | --- |
| model | `yolov8n.pt` |
| epochs | 50 |
| imgsz | 640 |
| batch | 48 |
| workers | 8 |
| cache | disk |
| device | 0 |
| seed | 42 |
| deterministic | true |
| patience | 15 |
| plots | false |

의도:

- `deterministic=true`: baseline 비교 신뢰도를 위해 재현성을 우선한다.
- `workers=8`: fresh cache 상태에서 DataLoader 병렬성을 높여 학습 속도 개선을 시도한다.
- `cache=disk`: epoch 반복 시 이미지 로딩 비용을 줄이는 방향으로 다시 실험한다.
- `plots=false`: 학습 중 부가 시각화 생성을 줄이고, 완료 후 별도 validation에서 plots를 생성한다.

주의:

- 이전 `cache=disk`는 외장 D드라이브에서 캐싱 시간이 과도하게 길어 중단한 이력이 있다.
- 따라서 실제 baseline 시작 전 D드라이브 여유 공간, 캐싱 속도, epoch 진입 여부를 반드시 확인한다.
- `Fast image access` 이후 hang이 발생하면 가장 먼저 `labels.cache` 손상 여부를 확인한다.

```powershell
$yolo = "C:\Lemon-sin\backend\.venv\Scripts\yolo.exe"

& $yolo detect train `
  model=yolov8n.pt `
  data="D:\Deeplearning\lemon\data\processed\aihub_yolo_50\data.yaml" `
  epochs=50 `
  imgsz=640 `
  batch=48 `
  workers=8 `
  cache=disk `
  device=0 `
  seed=42 `
  deterministic=true `
  patience=15 `
  plots=false `
  project="D:\Deeplearning\lemon\runs\food_yolo" `
  name=exp01_yolov8n_baseline_b48_w8_cache_disk_det_true
```

OOM 발생 시:

```powershell
batch=32
```

hang 발생 시 가장 먼저 확인할 것:

```text
labels.cache 손상 여부
```

## 16. 학습 완료 후 validation 명령

현재 학습은 `plots=false`로 진행 중이다. 따라서 학습 완료 후 별도 validation에서 시각화 결과를 만든다.

```powershell
$yolo = "C:\Lemon-sin\backend\.venv\Scripts\yolo.exe"

& $yolo detect val `
  model="D:\Deeplearning\lemon\runs\food_yolo\exp01_yolov8n_baseline_b48_w4_freshcache\weights\best.pt" `
  data="D:\Deeplearning\lemon\data\processed\aihub_yolo_50\data.yaml" `
  imgsz=640 `
  batch=48 `
  workers=4 `
  device=0 `
  plots=true `
  project="D:\Deeplearning\lemon\runs\food_yolo" `
  name=exp01_yolov8n_baseline_val_plots
```

생성해야 할 결과:

- confusion matrix
- PR curve
- F1 curve
- P curve
- R curve
- class별 metric

## 17. baseline 완료 후 정리할 지표

반드시 기록:

| 항목 | 설명 |
| --- | --- |
| mAP50 | IoU 0.5 기준 평균 AP |
| mAP50-95 | 더 엄격한 평균 AP |
| precision | 모델이 찾았다고 한 것 중 맞은 비율 |
| recall | 실제 객체 중 모델이 찾은 비율 |
| class별 AP | 약한 클래스 분석용 |
| confusion matrix | 어떤 클래스를 헷갈리는지 확인 |
| inference speed | 배포 가능성 판단 |
| model size | `best.pt` 크기 |
| epoch time | 학습 비용 기록 |

현재 epoch 7 기준:

```text
precision: 0.70223
recall: 0.70299
mAP50: 0.75363
mAP50-95: 0.68376
```

이 수치는 최종 결과가 아니다. 학습이 계속 진행 중이므로 완료 후 다시 정리해야 한다.

## 18. 다음 모델링 실험 계획

baseline 완료 후 아래 순서로 진행한다.

### exp02: 모델 크기 실험

목적:

- `yolov8n`에서 `yolov8s`로 키웠을 때 정확도 상승폭 확인

예상:

- mAP 상승 가능
- VRAM 사용량 증가
- 학습/추론 속도 감소

후보 명령:

```powershell
& $yolo detect train `
  model=yolov8s.pt `
  data="D:\Deeplearning\lemon\data\processed\aihub_yolo_50\data.yaml" `
  epochs=50 `
  imgsz=640 `
  batch=24 `
  workers=4 `
  cache=false `
  device=0 `
  seed=42 `
  deterministic=true `
  patience=15 `
  plots=false `
  project="D:\Deeplearning\lemon\runs\food_yolo" `
  name=exp02_yolov8s_model_size
```

### exp03: 이미지 크기 실험

목적:

- 작은 음식이나 여러 음식이 들어간 실제 사진 대응 가능성 확인

후보:

```text
imgsz=800
```

주의:

- VRAM 증가
- 학습 시간 증가
- 추론 속도 감소

### exp04: 증강 실험

기본 baseline과 비교할 증강 후보:

| 옵션 | 목적 |
| --- | --- |
| HSV 조정 | 조명/색감 변화 대응 |
| translate | 음식 위치 변화 대응 |
| scale | 음식 크기 변화 대응 |
| fliplr | 좌우 반전 일반화 |
| mosaic | 다양한 위치/크기 조합 학습 |

주의:

- 한 번에 너무 많은 옵션을 바꾸지 않는다.
- 실험 하나에서 핵심 변수 하나만 바꾸는 것이 해석에 좋다.

### exp05: 클래스 불균형 처리

사전 watchlist:

```text
squid-dish
fried-rice
mala-hot-pot
sweet-and-sour-pork
grilled-pork-belly
takoyaki
dim-sum
hamburger
rice-soup
```

가능한 방법:

- 소수 클래스 oversampling
- rare class만 별도 fine-tuning
- class merge 또는 class 제거 검토

주의:

- Ultralytics `cls` 옵션은 class별 weight가 아니라 classification loss gain에 가깝다.
- class별 loss weighting은 현재 버전에서 실제 지원 여부를 확인해야 한다.

### exp06: 클래스 설계 재검토

Confusion matrix를 보고 판단한다.

혼동 가능성이 높은 쌍:

| 후보 | 이유 |
| --- | --- |
| rice-bowl vs mixed-rice-bowl | 밥 위 토핑 형태가 유사 |
| soup vs stew | 국물류 구분이 시각적으로 애매 |
| noodle-soup vs udon | 면 + 국물 구조 유사 |
| grilled-beef vs barbecue-ribs | 고기류 형태 유사 |
| fish-cake vs fried-food-platter | 튀김류 형태 유사 |

### exp07: 직접 라벨링 데이터 실제 환경 평가

AIHub val 성능이 좋아도 실제 사진에서 성능이 떨어질 수 있다.

필수 분리:

```text
main_only_test
real_world_mixed_test
```

평가 방식:

- main food detection hit
- top-1/top-3 class correctness
- mAP은 라벨링 정책에 따라 해석 주의

### exp08: TTA / threshold tuning

학습 후 검증/추론 단계에서 비교:

```powershell
augment=true
conf=0.25 / 0.35 / 0.5
iou=0.5 / 0.7
```

주의:

- TTA는 정확도를 올릴 수 있지만 추론 속도가 느려진다.
- 서비스형 모델에서는 속도와 정확도 균형이 중요하다.

## 19. 다른 컴퓨터에서 다른 방식으로 모델을 돌릴 때 우선순위

다른 컴퓨터가 더 좋은 GPU를 가지고 있다면 아래 순서를 추천한다.

1. 현재 `yolov8n` baseline을 끝까지 완료한다.
2. 같은 데이터로 `yolov8s`를 실행한다.
3. `yolov8s` 결과가 의미 있게 좋으면 `yolov8m`을 검토한다.
4. `imgsz=800` 실험은 모델 크기 실험 이후 진행한다.
5. direct labeled real-world test는 학습보다 평가용으로 먼저 사용한다.
6. 모델 성능 개선은 class별 AP와 confusion matrix를 본 뒤 결정한다.

바로 하지 말아야 할 것:

- baseline 결과 없이 augmentation을 과하게 바꾸기
- AIHub와 직접 라벨링 데이터를 무작정 섞기
- class merge를 수치 없이 감으로 결정하기
- raw zip이 삭제된 상태에서 재변환을 시도하기

## 20. Git 상태와 커밋 주의

현재 Git 상태에서 주의할 점:

```text
M .gitignore
M backend/.env.example
M backend/src/config.py
?? .claude/
?? AGENTS.md
?? backend/food_image_analysis/
?? data/food_images/
?? docs/superpowers/plans/2026-05-21-aihub-yolo-study-guide.md
```

중요:

- `data/food_images/`가 untracked면 매핑 파일과 변환 스크립트가 다른 PC에 전달되지 않는다.
- 다른 PC에서 Git clone으로 이어받으려면 관련 파일을 commit해야 한다.
- 대용량 이미지 데이터는 commit하지 않는다.
- `.venv`는 commit하지 않는다.
- 커밋은 사용자 허락 후에만 진행한다.
- push는 사용자가 직접 한다.

권장 commit 대상:

```text
data/food_images/scripts/convert_aihub_50_to_yolo.py
data/food_images/manifests/roboflow_aihub_class_map_50.csv
data/food_images/manifests/roboflow_autolabel_food_prompts_50_aihub_aligned.csv
docs/superpowers/plans/2026-05-22-aihub-yolo-handoff.md
```

대용량 데이터 제외:

```text
D:\Deeplearning\lemon\data\processed\aihub_yolo_50
D:\Deeplearning\lemon\runs\food_yolo
```

이 두 폴더는 Git이 아니라 외장 드라이브, NAS, 압축 파일, 별도 데이터 저장소 방식으로 옮긴다.

## 21. 최종 체크리스트

다른 컴퓨터에서 이어받기 전:

- [ ] Git 저장소 최신 상태 확인
- [ ] 매핑 파일 commit 또는 별도 복사
- [ ] 변환 스크립트 commit 또는 별도 복사
- [ ] `processed\aihub_yolo_50` 전체 복사
- [ ] 진행 중 run을 resume하려면 `runs\food_yolo` 복사
- [ ] Python/Ultralytics/PyTorch 버전 기록
- [ ] `data.yaml` path가 새 컴퓨터 경로와 맞는지 확인
- [ ] `labels.cache`는 의심스러우면 archive 이동 후 fresh scan
- [ ] baseline 완료 후 validation plots 생성
- [ ] class별 AP와 confusion matrix 분석

## 22. 이 문서의 핵심 한 줄

현재 프로젝트는 AIHub 50클래스 YOLO 데이터셋 변환을 끝내고 `yolov8n` baseline 학습을 진행 중이며, 가장 중요한 교훈은 `Fast image access` hang을 설정 문제가 아니라 손상된 `labels.cache` 문제로 식별했다는 점이다. 다른 컴퓨터에서는 데이터셋과 run 폴더를 별도로 옮기고, baseline 완료 후 class별 AP와 confusion matrix를 기준으로 다음 실험을 설계하면 된다.
