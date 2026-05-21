# 2026-05-20 AIHub YOLO 모델링 TODO

## 오늘 완료

- Roboflow 50개 클래스와 AIHub 데이터 매핑을 재정리했다.
  - 기존 미매칭 5개를 AIHub에 실제 데이터가 있는 음식으로 교체했다.
  - 교체 클래스: `salad`, `korean-blood-sausage`, `takoyaki`, `chicken-galbi`, `udon`
  - 매핑 검증 결과: 50개 클래스, 빈 매핑 0개, 중복 AIHub class_id 0개
- Roboflow 업로드용 AIHub 매칭 완료 CSV를 새로 만들었다.
  - `data/food_images/manifests/roboflow_autolabel_food_prompts_50_aihub_aligned.csv`
- AIHub bbox 특성을 샘플 이미지로 확인했다.
  - 음식 알맹이만 타이트하게 잡은 박스가 아니라, 접시/그릇/포장용기까지 포함하는 서빙 단위 bbox에 가까운 것으로 판단했다.
  - 검수 이미지:
    - `data/food_images/interim/aihub_bbox_review/aihub_bbox_contact_sheet.jpg`
    - `data/food_images/interim/aihub_bbox_review/aihub_bbox_broader_contact_sheet.jpg`
- 직접 라벨링 데이터 운용 기준을 정했다.
  - AIHub는 학습용 단일 음식 데이터로 사용
  - 직접 라벨링 데이터는 검증/테스트 중심으로 사용
  - 메인음식만 명확한 사진과 실제 혼합 상차림 사진은 평가 목적을 분리
- `review_needed` 매핑 9개 클래스를 검토했다.
  - AIHub 세부 음식 24개에서 대표 이미지 1장씩 추출해 검수 시트를 생성했다.
  - 최종 판단: 일단 그대로 포함해서 진행
  - 검수 시트: `data/food_images/interim/review_needed_samples/review_needed_one_each_contact_sheet.jpg`
- `TS.zip` + `TS.z01` ~ `TS.z07` 멀티파트 압축 상태를 확인했다.
  - train 이미지 1장 smoke extraction 성공
  - 전체 압축 해제가 아니라 클래스 chunk 단위 임시 추출 방식으로 진행하기로 결정
- AIHub 50클래스 YOLO 변환 스크립트를 만들고 개선했다.
  - `data/food_images/scripts/convert_aihub_50_to_yolo.py`
  - 주요 기능:
    - Roboflow 50클래스 매핑 적용
    - TS/VS zip에서 필요한 class chunk만 임시 추출
    - 640x640 resize
    - YOLO label 생성
    - `data.yaml` 생성
    - `--resume` 이어받기
    - `--cleanup-mode delete`
    - `--max-runtime-minutes`
- YOLO 데이터셋 변환을 일부 진행했다.
  - 목표: train 108,580장 / val 13,780장
  - 현재: train 72,420장 / val 0장
  - 출력 위치: `D:\Deeplearning\lemon\data\processed\aihub_yolo_50`
  - 임시 추출 파일은 정리 완료
- 모델링 전략을 재정리했다.
  - 단순 학습 결과가 아니라 baseline, 오류 분석, 클래스 설계, 불균형 처리, 실제 테스트셋 평가 흐름으로 구성하기로 했다.

## 다음 TODO

- AIHub 50클래스 YOLO 변환을 완료한다.
  - 반복 실행 명령:

```powershell
$py="C:\Lemon-sin\backend\.venv\Scripts\python.exe"
& $py "C:\Lemon-sin\data\food_images\scripts\convert_aihub_50_to_yolo.py" --cleanup-mode delete --resume --max-runtime-minutes 60
```

- 변환 완료 후 개수를 검증한다.
  - train images: 108,580
  - train labels: 108,580
  - val images: 13,780
  - val labels: 13,780
- `data.yaml`을 확인한다.
  - `nc: 50`
  - names 50개
- YOLO baseline 학습 전 smoke test를 실행한다.
  - `yolov8n.pt`
  - `epochs=1`
  - `workers=0`
- smoke test 성공 후 baseline 학습을 실행한다.
  - `exp01_yolov8n_baseline`
  - `workers=2`
  - `deterministic=true`
- baseline 결과를 정리한다.
  - mAP50
  - mAP50-95
  - precision / recall
  - class별 AP
  - confusion matrix
  - 모델 크기
  - inference speed
- baseline 이후 실험 후보를 설계한다.
  - `exp02_yolov8s_model_size`
  - `exp03_aug_stronger`
  - `exp04_class_design`
  - `exp05_imbalance_sampling`
  - `exp06_realworld_finetune`

## 주의사항

- 원본 AIHub zip, 라벨 JSON, 최종 YOLO 결과물은 삭제하지 않는다.
- 임시 추출 폴더는 ZIP에서 잠깐 풀린 복사본이므로 디스크 보호를 위해 정리 가능하다.
- Git commit은 사용자 승인 후에만 진행한다.
- Push는 사용자가 직접 실행한다.
