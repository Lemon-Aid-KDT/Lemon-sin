# aihub_yolo_split (424클래스 재분리) — 다른 컴퓨터 학습 세팅 가이드

> **작성일**: 2026-05-29 · **상태**: 데이터셋 빌드 진행/완료 → 외장 D로 전달 → 타 컴퓨터에서 학습
> **이 문서 목적**: 외장 D드라이브를 학습용 컴퓨터에 연결한 뒤, 재분리된 데이터셋으로 바로 학습을 시작할 수 있게 한다.
> 배경·복구 과정은 [2026-05-29-aihub-class-split-recovery-handoff.md](./2026-05-29-aihub-class-split-recovery-handoff.md) 참고.

---

## 1. 무엇을 만들었나

- 기존 `aihub_yolo_50`(50클래스, 찌개 등 다수 음식이 통합 라벨링) 를 **원본 AI Hub 코드 단위(음식별)로 재분리**한 새 데이터셋.
- **클래스 수: 424개** (427개 코드 중 동일 한글명 3쌍 병합). 클래스명 = 한글 음식명.
- 이미지는 동일(bbox 동일), **라벨의 클래스 인덱스만** 음식별 새 인덱스로 치환.
- 예) 기존 `stew` 1개 → `황태부대찌개 / 김치찜 / 꽁치김치찌개 / 차돌된장찌개 / 해물순두부찌개 / 바지락된장국` 으로 분리.

---

## 2. 데이터셋 위치 & 구성 (외장 D)

**단일 ZIP으로 전달됨** (exFAT에 파일 12만 개를 직접 만들면 매우 느려서 zip 1개로 묶음):

```
D:\Deeplearning\lemon\data\processed\aihub_yolo_split.zip   ← 12.33 GB (검증완료)
└── (압축 풀면) aihub_yolo_split\
    ├── data.yaml                     # nc: 424, names: [...]
    ├── yolo_class_index_split.json   # code → {new_index, korean_name, orig_roboflow_class}
    ├── build_report.json             # 빌드 통계(드롭/val0 클래스 등)
    ├── _audit\class_counts.csv       # 클래스별 train/val 개수
    ├── train\images\*.jpg  +  train\labels\*.txt   (108,140장)
    └── val\images\*.jpg    +  val\labels\*.txt     (13,780장)
```

- zip 내부 엔트리 243,844개 = 이미지 121,920 + 라벨 121,920 + 메타 4. CRC 전수검사 통과.
- ZIP_STORED(무압축)이라 압축 해제가 빠름.
- C: 백업본도 동일 존재: `C:\Lemon-Aid\Lemon-sin\data\food_images\aihub_yolo_split.zip`.

> 원본 50클래스 데이터셋은 그대로 보존됨: `C:\Lemon-Aid\Lemon-sin\data\food_images\aihub_yolo_50\`, `D:\...\processed\aihub_yolo_50\`.

---

## 3. 학습 컴퓨터에서 준비 (압축 해제)

> ⚠️ **exFAT 외장에서 직접 학습하지 말 것** — 작은 파일 읽기가 매우 느림(파일당 ~100ms). 반드시 **로컬 디스크(SSD/NTFS)에 풀어서** 학습.

```powershell
# 외장 드라이브가 E:/F: 등 다른 문자로 잡힐 수 있으니 실제 경로로 교체
# 7-Zip 권장 (빠름). 로컬 폴더에 해제:
& "C:\Program Files\7-Zip\7z.exe" x "E:\Deeplearning\lemon\data\processed\aihub_yolo_split.zip" -o"C:\datasets\"
# 결과: C:\datasets\aihub_yolo_split\  (data.yaml 등 포함)
```

**경로 주의**
- **드라이브 문자**: 외장이 다른 컴퓨터에서 `D:` 가 아닐 수 있음 → 위 zip 경로를 실제 문자로 교체.
- **data.yaml `path`**: 기본 `path: .` (상대). Ultralytics 안전성을 위해 압축 푼 절대경로로 수정 권장:
  ```yaml
  path: C:\datasets\aihub_yolo_split
  train: train/images
  val: val/images
  ```

---

## 4. 학습 실행 (Ultralytics YOLO)

```bash
# 압축 푼 로컬 경로/모델은 환경에 맞게 교체
yolo detect train \
  data="C:\datasets\aihub_yolo_split\data.yaml" \
  model=yolo11s.pt \
  epochs=100 imgsz=640 batch=16 \
  project=runs_split name=yolo11s_424cls
```

- 클래스가 50→424 로 늘었으므로 **기존 50클래스 학습 산출물(exp03~05)·balanced_500 모델은 무효** → 새로 학습해야 함.
- 클래스가 많고 일부는 표본이 적으므로 epochs/배치/증강을 데이터 분포에 맞춰 조정.

---

## 5. 알아둘 점 (빌드 시 결정/처리된 내용)

- **드롭된 코드 3개**(이미지 제외됨): `B12091`(hot-pot), `B12104`(stew), `B12160`(grilled-beef) — 한글명 미입력이라 제외.
- **val=0 (train-only) 클래스 존재**: val 원본에 없던 코드(수동 입력 25개 일부 포함)는 검증셋 샘플이 0 → 해당 클래스는 val 지표가 안 나옴. 목록은 `build_report.json` 의 `classes_with_zero_val` 참고.
- **교차 병합 1건**: `갈비치킨` = `B11004`(원래 fried-chicken) + `B12003`(원래 chicken-galbi). 같은 음식명이라 1클래스로 합쳐짐.
- **동일명 병합 2건**: `베이글`(C02106+C02137), `갈비찜`(B12006+B12061).
- 코드↔클래스 정확한 대응은 `yolo_class_index_split.json` 참조.

---

## 6. 빌드 재현 / 출처 (이 컴퓨터에서 수행됨)

| 항목 | 경로 |
|---|---|
| 빌드 스크립트 | `C:\Lemon-Aid\Lemon-sin\scripts\data\build_aihub_split_dataset.py` |
| 코드→한글명 매핑(402 val복구 + 25 수동) | `...\data\food_images\manifests\aihub_code_korean_names.csv` |
| 수동 입력 원본(28개) | `...\data\food_images\manifests\aihub_28_manual_names.csv` |
| 원본 50클래스 인덱스 | `...\aihub_yolo_50\yolo_class_index_50.json` |

재실행: `python scripts\data\build_aihub_split_dataset.py [--force]`
(소스=C: `aihub_yolo_50`, 출력=D: `aihub_yolo_split`. 한글명 매핑 CSV를 수정하면 클래스 체계가 바뀜.)

---

## 7. 빌드 결과 (완료·검증됨 2026-05-29)

| 항목 | 값 |
|---|---|
| 클래스 수 (`nc`) | **424** (유니크 한글명) |
| 매핑된 코드 | 427 |
| 총 이미지 | **121,920** (train **108,140** / val **13,780**) |
| 드롭된 이미지 | 440 (전부 train; 드롭코드 B12091·B12104·B12160 은 val 데이터가 없던 코드) |
| **val=0 (train-only) 클래스** | **22개** |
| zip 크기 | 12.33 GB (=11.48 GiB), CRC 전수검사 통과 |
| zip 엔트리 | 243,844 (img 121,920 + label 121,920 + meta 4) |
| 라벨 클래스 인덱스 | 전 표본 `[0,424)` 범위 확인 |

**val=0 (검증셋 샘플 0, train 전용) 22개 클래스** — 학습엔 쓰이나 val 지표가 안 나옴:
`냉채족발, 족발, 계란빵, 도리야키, 베이글, 커피콩빵, 냉면, 만두, 양념치킨, 치킨, 갈비탕, 비빔밥, 쌀국수, 팥칼국수, 불고기덮밥, 컵밥, 샌드위치, 마라새우, 떡볶이, 짬뽕, 바지락된장국, 전복초밥`
(대부분 수동 입력 28개 중 val 원본에 없던 코드. 정확한 목록은 zip 내 `build_report.json` 의 `classes_with_zero_val` 참조.)

> 빌드 스크립트: `scripts\data\build_aihub_split_zip.py` (zip 스트리밍 방식). 기존 `build_aihub_split_dataset.py` 는 폴더 전개 방식(exFAT엔 느림)으로 미사용.
