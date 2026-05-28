# 2026-05-28 OCR + YOLO + Ollama 구현 진행 요약

## 기준 정보

- 작업 repo: `Lemon-Aid`
- 작업 브랜치: `feat/mobile-ios-xcode-simulator-run`
- 기준 계획: `outputs/todo-list/2026-05-28/2026-05-28-ocr-yolo-ollama-gap-plan.md`
- 팀 원격: `origin/feat/mobile-ios-xcode-simulator-run`
- 개인 기록 원격: `HorangEe02/Project_yeong/feat/mobile-ios-xcode-simulator-run`
- 보안 기준: `.env`, token, raw OCR text, provider raw payload, image bytes, object URI는 문서/커밋에 포함하지 않는다.

## 브랜치/커밋 범위

- `0647446 feat(ocr): 다중 이미지 분석 세션 정렬`
- `e39ee3a feat(mobile): 분석 결과 수동 보정 연결`
- `cdad9ce feat(supplement): 분석 preview Ollama 설명 연결`
- `b53b196 feat(ocr): provider 구조화 benchmark 보강`

## 수행한 작업

### 다중 이미지 분석 흐름

- 백엔드에 다중 이미지 분석 session endpoint와 단기 호환 `analyze-multi` endpoint가 연결되어 있다.
- 모바일 repository/controller/camera screen은 여러 장 이미지와 role metadata를 전송한다.
- `front_label`, `supplement_facts`, `intake_method`, `precautions`, `barcode`, `unknown` 계열 role을 backend contract와 맞춰 사용한다.

### OCR/YOLO 진단 metadata

- 분석 preview에 raw OCR text 없이 pipeline metadata를 제공한다.
- 주요 metadata는 `image_count`, `image_role`, `ocr_provider`, `ocr_text_present`, `ocr_confidence_bucket`, `roi_count`, `section_count`, `parser_contract_version`, `missing_required_sections`이다.
- YOLO는 OCR 전처리 및 review metadata용 ROI로 취급하고, 제품명/성분/효능 판단에는 직접 사용하지 않는다.

### Provider layout 및 parser V3

- Google Vision, PaddleOCR, CLOVA provider는 provider-neutral `OCRResult.pages` contract로 layout을 정렬한다.
- parser/review 흐름은 성분 후보뿐 아니라 `label_sections`, `intake_method`, `precautions`, `functional_claims`, `missing_required_sections`를 다룬다.
- provider benchmark는 다음 구조화 지표를 산출한다.
  - text presence rate
  - ingredient exact match
  - amount/unit exact match
  - intake-method extraction rate
  - precaution extraction rate
  - functional-claim extraction rate
  - section type recall
  - ingredient false hallucination rate

### Ollama 설명 연결

- 등록 전 analysis preview에 대해 안전한 로컬 Ollama 설명 endpoint가 추가되어 있다.
- 설명 payload는 sanitized analysis fields만 사용하며 raw OCR text, provider payload, image bytes, object URI를 전달하지 않는다.
- LLM 결과가 실패하거나 안전 검증에 걸리면 deterministic fallback 설명을 사용한다.

### 모바일 17 Pro 스타일 flow

- 17 Pro 스타일 카메라/분석 결과 UI에서 다중 이미지 추가, provider 선택, missing section 안내, manual correction, 등록 전 Ollama 설명 호출 흐름을 연결했다.
- Android 우선 smoke 흐름에서 카메라 사용이 불안정한 emulator 환경은 gallery/picker fallback을 유지한다.

## 검증 결과

- `PYTHONPATH=backend:backend/Nutrition-backend python -m pytest backend/Nutrition-backend/tests/unit/scripts/test_evaluate_ocr_three_tier.py -q --no-cov`
  - 17 passed
- `PYTHONPATH=backend:backend/Nutrition-backend python -m pytest backend/Nutrition-backend/tests/unit/ocr backend/Nutrition-backend/tests/unit/vision backend/Nutrition-backend/tests/unit/services/test_supplement_image_analysis.py backend/Nutrition-backend/tests/unit/services/test_supplement_parser.py -q --no-cov`
  - 165 passed
- `flutter test test/unit/supplement_repository_test.dart test/unit/supplement_models_test.dart test/unit/app_controller_test.dart test/widget/source_camera_screen_test.dart test/widget/analysis_result_screen_test.dart`
  - 24 passed
- `black --check backend/scripts/evaluate_ocr_three_tier.py backend/Nutrition-backend/tests/unit/scripts/test_evaluate_ocr_three_tier.py`
  - passed
- `/private/tmp/lemon-p1-quality-venv/bin/ruff check backend/scripts/evaluate_ocr_three_tier.py backend/Nutrition-backend/tests/unit/scripts/test_evaluate_ocr_three_tier.py`
  - passed
- `git diff --check`
  - passed
- `detect-secrets scan backend/scripts/evaluate_ocr_three_tier.py backend/Nutrition-backend/tests/unit/scripts/test_evaluate_ocr_three_tier.py`
  - no findings

## 남은 TODO

- live OCR smoke를 provider별로 다시 실행한다.
  - `configured`
  - `paddleocr`
  - `clova`
  - `google_vision`은 credential 상태를 먼저 분리 확인한다.
- 실제 촬영 이미지 fixture로 provider benchmark manifest를 생성하고 `b53b196`의 구조화 지표를 비교한다.
- YOLO ROI가 켜진 Docker/runtime에서 `roi_count`, selected ROI, parser 결과가 review UI에 기대대로 반영되는지 확인한다.
- Android emulator에서 gallery image -> multi-image batch -> review -> manual correction -> registration -> analysis explanation까지 end-to-end smoke를 진행한다.
- iOS simulator는 Xcode/device 상태가 안정화된 뒤 같은 flow로 재검증한다.

## 주의할 파일/커밋 제외 항목

- 기존 untracked 항목은 이번 작업 범위에서 건드리지 않는다.
  - `.omc/`
  - `mobile/Lemon-Aid-ios/`
  - `mobile/assets/mascot/Mascot_AppIcon_Rebuild_Assets/`
  - `mobile/ios-native/`
- 로컬 `.env`, ngrok token, gateway token, provider credential, raw OCR/provider payload, 이미지 원본, object URI는 절대 stage하지 않는다.
- 음식 YOLO `best.pt`는 ignored local artifact이며 supplement label ROI 모델로 오인하지 않는다.
