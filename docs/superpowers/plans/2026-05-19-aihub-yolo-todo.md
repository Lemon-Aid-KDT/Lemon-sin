# 2026-05-19 AI Hub YOLO 작업 TODO

> 목적: Roboflow 50개 음식 클래스 기준으로 AI Hub 데이터를 YOLOv8 학습 데이터셋으로 변환하고, 이후 지인 사진 평가까지 이어질 수 있게 준비한다.

## 오늘 완료

- 음식 이미지 분석용 작업 구조를 정리했다.
  - 백엔드: `backend/food_image_analysis/`
  - 데이터: `data/food_images/`
- AI Hub 원본 데이터 위치와 압축 상태를 확인했다.
  - 라벨 데이터는 압축 해제 완료
  - train 이미지 압축은 `TS.z01` ~ `TS.z07` 누락으로 대기 중
- Roboflow 50개 클래스와 AI Hub 800개 세부 클래스를 연결하는 매핑 초안을 만들었다.
  - 매핑 파일: `data/food_images/manifests/roboflow_aihub_class_map_50.csv`
  - AI Hub 세부 class_id 408개를 Roboflow 50개 클래스에 연결
- AI Hub 라벨 기준으로 50클래스 학습 가능 물량을 확인했다.
  - train 103,350개, val 13,000개 라벨이 50클래스 매핑에 포함됨
- Roboflow AI 모델로 샘플 데이터 약 200장을 오토 라벨링해 보았다.

## 확인된 이슈

- `TS.z01` ~ `TS.z07`이 없으면 train 이미지 추출이 불가능하다.
- 현재 변환 산출물은 validation 쪽만 일부 존재한다.
  - train images: 0
  - train labels: 0
  - val images: 150
  - val labels: 150
- Roboflow 50개 클래스 중 AI Hub 직접 대응이 없는 클래스가 5개 있다.
  - `steamed-rice`
  - `kimchi`
  - `vegetable-side-dish`
  - `boiled-pork`
  - `tempura`
- 위 5개는 AI Hub에서 억지 매칭하지 말고, 지인 사진 또는 별도 수집 데이터로 보강하는 편이 안전하다.

## 오늘 남은 TODO

- [ ] `TS.z01` ~ `TS.z07` 다운로드 완료 후 아래 경로에 모두 있는지 확인한다.

```text
D:\Deeplearning\lemon\data\raw\aihub\data\Training\raw_data\
├── TS.z01
├── TS.z02
├── TS.z03
├── TS.z04
├── TS.z05
├── TS.z06
├── TS.z07
└── TS.zip
```

- [ ] 7-Zip이 multi-volume zip을 정상 인식하는지 확인한다.

```powershell
& "C:\Program Files\7-Zip\7z.exe" l "D:\Deeplearning\lemon\data\raw\aihub\data\Training\raw_data\TS.zip" | Select-Object -First 40
```

- [ ] `05_aihub_chunked_resize.py`에 Roboflow 50클래스 매핑 옵션을 추가한다.
  - 입력: `data/food_images/manifests/roboflow_aihub_class_map_50.csv`
  - 출력: 50개 Roboflow 클래스 기준 `data.yaml`
  - AI Hub class_id를 Roboflow class index로 재라벨링
- [ ] 3~5개 클래스만 먼저 smoke 변환한다.
- [ ] smoke 변환 결과의 이미지/라벨 개수를 확인한다.
- [ ] YOLOv8n 또는 YOLOv8s로 2 epoch smoke 학습을 실행한다.

## 권장 실행 순서

1. TS 분할 파일 다운로드 완료 확인
2. 7-Zip 목록 확인
3. Roboflow 50클래스 매핑 기반 변환 스크립트 수정
4. `--limit-classes 3` 수준으로 smoke 변환
5. 변환 산출물 검증
6. YOLOv8n 2 epoch smoke 학습
7. 문제가 없으면 45개 또는 50개 클래스 기준 전체 변환

## 메모

- 원본 Roboflow CSV는 수정하지 않는다.
- AI Hub 원본 라벨도 직접 수정하지 않는다.
- AI Hub 800개 세부 클래스는 별도 매핑 파일로 Roboflow 50개 클래스에 연결한다.
- 파일 삭제가 필요할 때는 삭제 대신 보관 폴더로 이동한다.
- Git 커밋은 사용자 허락 후에만 진행한다.
- Git push는 명령어만 안내하고 사용자가 직접 실행한다.
