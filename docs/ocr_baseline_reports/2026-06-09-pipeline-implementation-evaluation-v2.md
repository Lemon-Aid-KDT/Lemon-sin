# YOLO26 → PaddleOCR → Ollama 파이프라인 구현 평가 (v2)

> 작성일: 2026-06-09
> 범위: 설계 의도(영양제 라벨 영역 인식 → OCR → LLM 검증/추천) 대비 실제 구현 충실도 평가
> 방법: 멀티 에이전트 코드 매핑(5) + 웹 리서치(5) + 적대적 검증(6). 모든 격차는 `file:line` 근거로 재확인됨.
> 분석 브랜치: `chore/ocr-a100-v2-clean-guards`

---

## 0. TL;DR

- **설계의 "컴포넌트"는 거의 다 존재한다.** YOLO 섹션 검출, PaddleOCR 어댑터, Ollama gemma 비전 검증/재추출, qwen 텍스트 RAG 재작성 + 면책문구가 모두 실제 코드로 구현되어 있다. 골격 충실도는 높다.
- **그러나 설계의 "동작 흐름"은 런타임에서 거의 0% 실현되어 있다.** 핵심 단계들이 전부 기본 비활성(flag off) 상태이고, 일부는 production에서 사인오프 없이는 켤 수 없도록 이중 차단되어 있다.
- **결정적 사실 3가지**
  1. 현재 활성 `.env`는 `OCR_PRIMARY_PROVIDER="clova"` — 설계상 "메인 OCR"이어야 할 PaddleOCR이 **런타임 요청 경로에 아예 없다**(clova primary일 때 fallback 어댑터도 비어 있음).
  2. YOLO ROI 크롭 단계가 꺼져 있어 OCR은 **항상 전체 이미지**를 받는다. 학습된 8-class 섹션 검출기(`best.pt`)는 디스크에 있으나 어디에도 **연결되어 있지 않고**, 성능도 mAP50 0.219로 사용 불가 수준이다.
  3. PaddleOCR 정확도 목표(char-LCS F1 0.95)는 **현재 채점 방식에서 수학적으로 도달 불가능**하다 — GT가 섹션 필드만 담고 있어 전체 이미지 OCR의 precision이 구조적으로 ~0.30에 갇힌다.
- **종합 점수: 약 55/100** ("설계대로 만들었으나, 설계대로 켜지 않았다"). 컴포넌트 구현 품질은 양호하나, 통합·활성화·평가 지표 정의에서 격차가 크다.

---

## 1. 설계 대비 구현 요약

| 컴포넌트 | 설계 의도 | 실제 구현 | 일치도 | 상태 |
|---|---|---|---|---|
| **① YOLO26 ROI 검출** | 4개 라벨 섹션(성분/함량/섭취방법/주의사항) bbox 검출 후 크롭 → OCR로 전달 | 어댑터·러너·8-class taxonomy·fail-closed 클래스 계약 모두 실존. 단 기본 비활성, 학습 가중치 미연결, mAP50 0.219로 사용 불가 | **55%** | 부분 구현 |
| **② PaddleOCR (메인 OCR)** | Korean+English 라벨 텍스트를 정확히 추출하는 1순위 엔진 | PP-OCRv5 3.x API로 정확히 구현. 단 런타임에서 CLOVA에 밀려 **호출되지 않음**. 모바일 모델·전처리 부재·튜닝 노브 미배선 | **55%** | 부분 구현 (런타임 우회) |
| **③ Ollama 비전 보조 (gemma4:e4b)** | 이미지 vs OCR 텍스트 비교 → 재추출 재프롬프트 | `extract_text`/`verify_text` 완전 구현. 단 3중 게이트로 기본 OFF, production 금지. **verify→재추출 피드백 루프는 미구현**(불일치 경고만 발행) | **60%** | 부분 구현 (비활성) |
| **④ Ollama 텍스트 RAG + 면책문구 (qwen3.5:9b)** | 사용자 정보 + DB(RAG)로 추천/경고 + "진단 아님, 의사 상담" 문구 | 추천은 **결정론적 규칙 기반**(LLM 생성 아님). LLM은 설명 "재작성"만 담당. RAG는 lexical 스캔 기본, pgvector는 opt-in. **면책문구는 충실히 강제됨** | **62%** | 부분 구현 |
| **⑤ 파이프라인 오케스트레이션** | 단일 자동 흐름: 이미지→크롭→OCR→LLM 검증→추천 | 단계는 명확히 배선됐으나 ROI·멀티모달 전부 게이트 OFF. 추천은 별도 요청으로 분리. 런타임 실제 흐름은 설계와 크게 다름 | **45%** | 부분 구현 |

> 일치도는 "코드 존재"가 아니라 "설계된 동작이 기본 구성에서 실제로 일어나는가"를 기준으로 매겼다.

---

## 2. 컴포넌트별 상세 평가

### ① YOLO26 ROI 섹션 검출 — 55/100

**구현된 것 (강점)**
- `YoloLabelDetector`(`src/vision/yolo.py:29`)는 실제 `ultralytics.YOLO`(>=8.1)를 lazy-load해 `model.predict()`를 호출하는 진짜 어댑터다 (`src/vision/ultralytics_runner.py:91-140`).
- 8-class taxonomy가 설계의 4개 클래스를 **포함하고 초과**한다: `ingredient_amounts, supplement_facts, intake_method, precautions` + `product_identity, allergen_warning, other_ingredients, functional_claims` (`src/learning/retraining.py:33-42`).
- **Fail-closed 클래스 계약**(`ultralytics_runner.py:274-296`): 모델이 supplement 섹션 클래스를 노출하지 않으면 로드 시점에 `VisionError`. 잘못된 모델(예: food 모델)이 섹션 검출기로 쓰이는 것을 막는다.
- "YOLO26"은 마케팅이 아니라 실제다 — `yolo26s.pt`에서 305장/3,530박스 실측 데이터셋으로 A100 학습이 수행됨.
- bbox→크롭→OCR 배선이 실제로 존재(`detect_regions → select_best_label_region → crop_image_to_bounding_box`, `supplement_image_analysis.py:1140-1158`).

**격차 (검증 확정)**
| 심각도 | 격차 | 근거 |
|---|---|---|
| critical/high | 런타임에서 섹션 검출기 OFF → OCR은 항상 전체 이미지 | `.env`에 `ENABLE_VISION_CLASSIFIER`/`OCR_ROI_PREPROCESSING_POLICY` 미설정 → 기본 `enable_vision_classifier=False`(`config.py:509-512`), `ocr_roi_preprocessing_policy="disabled"`(`config.py:514-521`). `_detect_label_regions_if_enabled`가 즉시 `()` 반환(`supplement_image_analysis.py:929-930`) |
| high | 리포지토리 루트 `best.pt`는 **영양제 섹션 검출기가 아니라 음식(food) 검출기** | `best.pt` 클래스명이 `barbecue-ribs, doenjang-jjigae...` 등 음식. supplement 섹션 클래스 0개. `src/vision/food_yolo.py`에서만 소비됨(그나마도 `enable_food_yolo_detector=False`로 비활성) |
| high | 실제 학습된 섹션 검출기는 성능 미달 + 미배선 | `training-summary.json`: mAP50 **0.219**, mAP50-95 0.082, P 0.338, R 0.279. `VISION_CLASSIFIER_MODEL`로 연결된 곳 0개(grep 확인). 클래스 계약은 통과하나(올바른 8-class) 가중치가 약하고 배선 안 됨 |
| medium | 기본 태그 `yolo26n.pt`는 COCO 체크포인트 → 클래스 계약 실패 | `config.py:513`. 켜더라도 `VisionError`로 0 ROI |
| low | `VisionError`가 조용히 삼켜짐 | `supplement_image_analysis.py:937-938 except VisionError: return ()` — 검출 실패가 전체-이미지 fallback으로 위장됨, 로그/메트릭 없음 |

> **복합 효과:** 섹션 크롭이 OCR에 도달하려면 (a) `ENABLE_VISION_CLASSIFIER=true`, (b) `OCR_ROI_PREPROCESSING_POLICY=crop_before_primary`, (c) `VISION_CLASSIFIER_MODEL=<쓸만한 mAP의 best.pt>` 세 가지가 모두 필요한데, 셋 다 충족되지 않는다. 게다가 `vision_roi_min_confidence=0.50`(`config.py:632`)이라, 현재의 저-recall 검출기(R 0.279)를 켜도 대부분의 박스가 0.50 미만으로 버려져 사실상 no-op이 된다.

---

### ② PaddleOCR provider (메인 OCR) — 55/100

**구현된 것 (강점)**
- **최신 PP-OCRv5 / PaddleOCR 3.x `predict()` API**를 정확히 사용(레거시 `ocr()` 아님). `paddlepaddle==3.2.0`, `paddleocr>=3.6,<3.7` 핀(`backend/pyproject.toml:24-25`).
- 언어 인식형: `korean_PP-OCRv5_mobile_rec` + `lang='korean'` 기본 — 범용 ch/en 모델이 아니라 한국어 특화 모델을 씀.
- 결과 파싱이 매우 견고: v3.x dict(`rec_texts/rec_scores/rec_polys`), 레거시 튜플, `.json()/.to_dict()` 모두 처리. bbox y-center로 행 그룹핑해 표 형태 영양성분 행을 보존(`paddle.py:441-567`).
- 운영 튜닝 훅 존재: server/server_detection 프로파일, 파인튜닝 recognizer dir, det_limit/rec_score predict 노브, 폐쇄망 preload.
- 저신뢰 텍스트를 드롭하지 않고 보존(다운스트림 LLM 검토용).

**격차 (검증 확정) — "왜 PaddleOCR이 약한가"의 코드 근거**
| 심각도 | 격차 | 근거 |
|---|---|---|
| critical | 런타임에서 PaddleOCR 우회 — `.env`가 CLOVA를 primary로 강제 | `.env:182 OCR_PRIMARY_PROVIDER="clova"`. 코드/compose 기본값(`paddleocr`)을 덮어씀. **clova primary일 때 PaddleOCR은 fallback에도 없음** |
| high | 기본 recognizer가 **경량 모바일 모델** | `korean_PP-OCRv5_mobile_rec`, `local_ocr_model_profile="mobile"`(`config.py:555`). 게다가 **한국어 server recognizer는 존재하지 않음** — `server` 프로파일은 비한국어 `PP-OCRv5_server_rec`로 바뀌어 오히려 한국어 정확도 하락 |
| high | OCR-급 전처리 전무 | 이진화/기울기보정/업스케일 없음. 기본 `autocontrast`는 사실상 항등 대비 스트레치. `det_db/binarize/deskew/unclip/dpi` grep 0건 |
| high | `thumbnail()`은 **축소만** 가능, 확대 불가 | `preprocessing.py:91` — 작은 저DPI 한글 크롭이 절대 확대되지 않음. PP-OCRv5 rec 입력 높이는 48px 고정이라 작은 글자가 치명적 |
| medium | det/rec 튜닝 노브 미배선 | `_predict_kwargs`는 3개(limit_side_len/limit_type/rec_score_thresh)만, 전부 기본 None. `det_db_thresh/box_thresh/unclip_ratio/drop_score` 미존재 |
| medium | 텍스트라인 방향분류 OFF + doc unwarp/orientation **하드코딩 False** | `paddle.py:172-173`. 곡면 병/파우치 라벨 보정 불가 |
| low | confidence가 단순 산술평균 | `_average_scores`(`paddle.py:427-438`) — 큰 글자 몇 줄이 작은 오인식 다수를 가림 → 0.80 fallback 게이트 underfire |

---

### ③ Ollama 비전 보조 (gemma4:e4b) — 60/100

**구현된 것**
- `OllamaVisionAssistAdapter`(`src/llm/ollama_vision.py`)가 `extract_text()`(이미지/ROI에서 텍스트 재추출)와 `verify_text()`(이미지 vs OCR 비교 → match/partial/mismatch/uncertain) 모두 local Ollama·base64·JSON-schema로 구현.
- 강한 프라이버시 게이팅: local-only host 검증, 비활성 시 이미지 바이트 미전송이 테스트로 증명됨.

**격차**
| 심각도 | 격차 | 근거 |
|---|---|---|
| high | 비전 보조 전체가 3중 게이트로 기본 OFF + production 금지 | `enable_multimodal_llm=False`(`config.py:505-508`), `multimodal_ocr_assist_policy="disabled"`, `enable_multimodal_verification=False`. 어댑터 자체가 None으로 생성조차 안 됨(`factory.py:176-184`). production에선 사인오프 전까지 startup 실패(`config.py:941-959`) |
| medium(설계 불일치) | 설계의 "verify → 재추출 재프롬프트" **피드백 루프 미구현** | verify 단계는 불일치 경고 코드만 반환(`supplement_image_analysis.py:1316-1317`), 교정 텍스트를 파서로 되먹이지 않음. 재추출은 별개의 "primary 약할 때" 경로일 뿐 루프 아님 |

---

### ④ Ollama 텍스트 RAG 추천 + 면책문구 — 62/100

**구현된 것 / 설계와 일치**
- **면책문구는 충실히 강제됨**: `SUPPLEMENT_IMPACT_DISCLAIMER`(`supplement_recommendation.py:27-31`, "…자세한 사항은 반드시 의사·약사 등 전문가와 상담하시기 바랍니다")가 모든 추천/설명 응답에 부착되고, LLM 재작성 결과에도 강제로 덮어씀(`supplement_explanation.py:338,391`).
- **안전 강제**: `FORBIDDEN_TERMS`(진단/치료/처방/복용량 변경) 포함 시 응답 거부(`_reject_forbidden_response`). 면책문구가 금칙어 "진단"을 피하도록 문구가 설계됨.
- **사용자 프로필 반영**: 성별/연령대/임신/수유 + 동의 기반 의료 맥락이 위험분류와 LLM 프롬프트 양쪽에 들어감.
- **RAG 실존**: lexical Markdown 스캔(항상) + opt-in pgvector 하이브리드 시맨틱 검색(entity-link 부스팅, lexical fallback). 임베딩은 local Ollama(`bge-m3`).
- **모델 분리는 배포층에서 실현**: `docker-compose.yml:65`가 텍스트 모델 기본을 `qwen3.5:9b`로, 비전을 `gemma4:e4b`로 주입(`:66`). 단 `.env.example:64`는 텍스트를 gemma로 두어 **환경에 따라 다름**.

**격차**
| 심각도 | 격차 | 근거 |
|---|---|---|
| medium | 추천이 **LLM 생성이 아니라 결정론적 규칙 기반** | `build_supplement_impact_preview`(`supplement_recommendation.py:34-114`)는 KDRI 기여도/위험분류 + 고정 한국어 템플릿. LLM 호출 없음. LLM은 `use_local_llm` 시 설명 "재작성"만 |
| medium | RAG DB(pgvector) opt-in, 기본 OFF | `enable_wiki_vector_rag=False`(`config.py:413`) → 기본은 lexical 스캔 |
| 참고 | 텍스트 모델 불일치(qwen vs gemma) | compose=qwen, .env.example=gemma — 배포 일관성 점검 필요 |

> 설계서가 "Gemma4"를 텍스트/비전 양쪽 메인으로 표현했으나, 실제 의도(검증 확정)는 **텍스트=qwen3.5:9b, 비전=gemma4:e4b** 분리이며 이는 compose에 반영돼 있다. 추천이 "LLM 권고 생성"이라기보다 "규칙 기반 산출 + LLM 문구 재작성"인 점이 설계 표현과의 핵심 간극이다.

---

### ⑤ 파이프라인 오케스트레이션 — 45/100

**런타임 실제 흐름 (검증 확정)**
```
이미지 업로드 (POST /api/v1/supplements/analyze)
  └─ [YOLO ROI 크롭 ✗ 비활성] → 전체 이미지 그대로
       └─ CLOVA primary OCR  (PaddleOCR은 경로에 없음)
            └─ [gemma 비전 fallback ✗ 비활성]
                 └─ [secondary fallback: primary가 빈/약할 때만]
                      └─ [gemma 비전 verify ✗ 비활성]
                           └─ qwen 텍스트 파서 + 결정론적 패턴 fallback
                                └─ 미리보기(preview) 반환
추천/면책문구 = 별도 요청 (GET /recommendations/latest, POST /recommendations/explain)
```
- 단계 게이팅 설계 자체는 깔끔하다(각 AI 단계가 수동입력으로 우아하게 degrade). 그러나 **설계가 묘사한 자동 단일 흐름은 기본 구성에서 일어나지 않는다.**
- `with_recommendation`는 기본 False라 이미지→추천이 한 요청에 묶이지 않음(`supplements.py:1086`).
- production은 멀티모달/비전/ROI를 이중으로 차단(`config.py:941-959`).

---

## 3. 핵심 격차 — 심각도 순 (검증으로 confirmed된 것만)

1. **[CRITICAL] PaddleOCR-as-primary 설계가 런타임 0% 실현.** `.env`가 CLOVA를 강제하고, clova primary 분기에서 PaddleOCR은 fallback에도 없음 → 전체 PaddleOCR 노력이 오프라인 평가 전용. (`.env:182`, `factory.py:140-146`)
2. **[CRITICAL/구조적] 0.95 char-LCS 목표가 수학적으로 도달 불가.** GT가 섹션 필드만 담아 전체-이미지 OCR의 precision이 ~0.30에 갇힘. recognizer-only 상한 ≈0.68–0.71 (`2026-06-08-text-f1-improvement-design.md`). → **지표를 ROI 스코핑 또는 recall 중심으로 재정의해야 함.**
3. **[HIGH] YOLO 섹션 크롭이 런타임 비활성 + 학습 가중치 미배선 + 성능 미달(mAP50 0.219).** 가장 값싼 고효율 레버(텍스트-공간 스코핑 `parse_label_layout`)가 **미실행** 상태로, 비싼 A100 recognizer/검출기 학습에 먼저 투자됨(우선순위 오류).
4. **[HIGH] 기본 모바일 모델 + 전처리/업스케일 전무 + det 튜닝 미배선** → 조밀한 작은 한글 라벨에서 약한 정확도의 직접 원인.
5. **[HIGH] gemma 비전 검증/재추출이 기본 OFF + verify→재추출 루프 미구현.** OCR 약점을 복구할 안전 채널이 inert.
6. **[MEDIUM] 추천이 결정론적 규칙 기반**(LLM 권고 생성 아님), RAG DB opt-in, 단일 자동 흐름이 두 요청으로 분리.
7. **[MEDIUM] 재현성 부재 + env-split 제약.** 평가 게이트 JSON·데이터셋·teacher 라벨·`.env`가 전부 git 미추적(local-only). 공개 repo로 파이프라인 재현 불가. 추가로 **메인 백엔드 venv(`.venv` py3.13)에는 PaddleOCR이 설치 불가**(macOS arm64 + py3.13 휠 부재) — paddle은 전용 `.venv-paddle`(py3.12, paddleocr 3.6.0 / paddlepaddle 3.3.1, CPU)에만 존재하고 모든 paddle 스크립트는 그 env에서 독립 실행된다(문서화된 의도, `docs/handoff/2026-06-06-clova-gt-paddleocr-prompt.md:45`). Docker 프로덕션(linux py3.13)은 `INSTALL_LOCAL_OCR=true`로 in-image 설치되어 동작 가능. paddlepaddle 버전도 4곳(pyproject 3.2.0 / 로컬 3.3.1 / A100 3.2.2 / Dockerfile 3.2.0)이 제각각이라 통일이 필요하다. → 상세는 개선 계획서 §1.5 참조.

---

## 4. 잘 된 점 (강점)

- **엔진/모델 선택이 옳다.** PP-OCRv5(최신), 한국어 특화 recognizer, ultralytics 실모델, 8-class 섹션 taxonomy — 토대 결정이 정확하다.
- **방어적 설계.** fail-closed 클래스 계약, 외부 OCR/LLM 전송 차단, production 사인오프 게이트, 저신뢰 텍스트 보존 — 의료성 도메인에 맞는 안전 우선 설계.
- **면책문구·금칙어 강제가 견고하다.** 진단성 표현을 코드 레벨에서 거부.
- **이미 방대한 평가/파인튜닝 인프라가 존재한다.** 203-fixture 벤치마크, baseline/gate 스크립트, A100 학습 스크립트, teacher(CLOVA) pseudo-GT — 개선을 "처음부터"가 아니라 "그 위에" 쌓을 수 있다.
- **운영 튜닝 훅이 풍부하다.** profile/recognizer-dir/predict 노브를 코드 변경 없이 환경변수로 실험 가능.

---

## 5. 측정된 성능 현황 (참고)

| 항목 | 측정값 | 출처 |
|---|---|---|
| PaddleOCR mobile baseline (203 fixture) | field_match 0.560 macro / 0.552 micro, LCS recall 0.514 | `reconciled/paddleocr-baseline-mobile-v3.json` |
| det 튜닝(무학습) 후 | field_match 0.560→0.586, LCS recall +0.041 | 채택됨 |
| A100 크롤링 파인튜닝 best(p10), holdout 52 | field_match 0.562, LCS P **0.320** / R 0.529 / **F1 0.324** | `paddleocr-eval-a100-p10.json` |
| 95% 게이트 | `paddleocr_target_reached=false`, `status=continue_training_loop` | `paddleocr-text-target-gate.finetuned-crawling-p10.json` |
| 합성 2-epoch CPU 파인튜닝 | holdout 0.518 → **0.037 (catastrophic forgetting)** | `2026-06-07-cpu-finetune-results.md` |
| 실사진 7장 CER | **38.27%** (목표 5%); 깨끗한 정면 박스는 8.5% | `v3/final_summary.md` |
| recognizer val line-acc | ≈0.80 ("충분히 좋음" 판정 — 병목은 recognizer가 아니라 스코핑) | 동일 |

> 핵심 해석: **precision은 ~0.30에서 정체, recall만 0.49→0.53으로 상승.** 즉 recognizer를 키우는 것이 아니라 **무엇을 채점/추출하느냐(ROI·텍스트 스코핑 + 지표 정의)**가 진짜 레버다. 실사진 CER 38%의 주원인은 모델 한계가 아니라 **입력 이미지 품질(각도/곡면/반사)**로 귀인됨.

---

## 6. 종합 결론

**골격은 A급, 통합·활성화·지표는 C급.** 설계가 명세한 모든 컴포넌트가 실제 코드로 존재하고 안전 설계도 훌륭하지만, (1) 메인이어야 할 PaddleOCR이 런타임에서 빠져 있고, (2) ROI·비전 검증 등 정확도를 끌어올릴 단계가 전부 꺼져 있으며, (3) 성공을 판정하는 지표가 구조적으로 도달 불가능하게 정의되어 있다.

→ **다음 작업의 우선순위는 "새 모델 학습"이 아니라 "이미 만든 것을 켜고, 지표를 고치고, 값싼 스코핑 레버를 먼저 실행"하는 것이다.** 구체적 실행 계획은 동반 문서 [`2026-06-09-paddleocr-performance-improvement-plan.md`](./2026-06-09-paddleocr-performance-improvement-plan.md) 참조.

---

### 부록: 참조한 핵심 파일
- `backend/Nutrition-backend/src/ocr/providers/paddle.py`, `preprocessing.py`, `factory.py`
- `backend/Nutrition-backend/src/vision/{yolo.py, ultralytics_runner.py, taxonomy.py, food_yolo.py}`
- `backend/Nutrition-backend/src/llm/{ollama_vision.py, ollama.py}`
- `backend/Nutrition-backend/src/services/{supplement_image_analysis.py, supplement_recommendation.py, supplement_explanation.py, llm_wiki_retrieval.py, supplement_parser.py}`
- `backend/Nutrition-backend/src/config.py`, `.env`, `docker-compose.yml`, `backend/pyproject.toml`
- `docs/ocr_baseline_reports/{2026-06-06-paddleocr-95pct-findings-and-finetune-recipe.md, 2026-06-07-cpu-finetune-results.md, 2026-06-08-text-f1-improvement-design.md, v3/final_summary.md}`
