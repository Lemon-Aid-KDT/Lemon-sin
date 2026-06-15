# 2026-06-10 다음 단계 / 사용자 액션

> 근거 문서: `docs/ocr_baseline_reports/2026-06-09-paddleocr-performance-improvement-plan.md` (단계 A/B/C), 동 `-pipeline-implementation-evaluation-v2.md`.

## 사용자가 직접 해야 하는 것 (에이전트 차단/권한)
1. **A100 본학습 실행** — 에이전트 SSH(155.230.153.222) 차단(publickey). VS Code 원격에서 `run_a100_paddleocr_windows_training.ps1`로 직접. **단, 레시피 교정 필수**: `-LearningRate 0.0001`(기존 5e-4→1e-4), 일반:도메인 1:1 혼합(`ratio_list`), RecConAug 제거. (계획서 §6)
2. **개인 GitHub 푸시** — 에이전트 하드 차단(크로스-계정). `git push personal <branch>` 사용자 직접.
3. **(정책 결정) teacher 원문 보존 예외** — 단계 C(teacher 증류 라벨링)는 CLOVA/Google Vision 원문 전사가 학습 타깃으로 필요. 현재 redaction이 이를 지워 candidate 0건. **학습 전용·접근통제 저장소** 허용 여부 결정 필요. (계획서 §7 C1)
4. **(환경 결정) paddlepaddle 버전 통일** — 로컬 3.3.1 / pyproject 3.2.0 / A100 3.2.2 / Dockerfile 3.2.0 불일치. 학습에 쓸 버전 1개로 고정 후 pyproject·Dockerfile 핀 반영. (계획서 §1.5.3)

## 에이전트가 이어서 할 수 있는 것 (우선순위 순)
1. **[단계 A·최우선] 지표 재정의** — 0.95 char-LCS precision 게이트 폐기 → recall + field_match + 실사진 line-level CER로 전환. (계획서 §3) — *코드/스크립트 수정, .venv-paddle 불필요*
2. **[단계 A] ROI 텍스트-공간 스코핑 측정** — `src/parsing/layout_parser.py:218 parse_label_layout`로 섹션 텍스트만 채점 → 무학습 F1 0.33→0.50+ 검증. **가장 값싼 고효율 레버, 아직 미실행.**
3. **[단계 A] `server_detection` + det 해상도 + `label_enhance` 전처리 벤치** — `.venv-paddle` 또는 A100에서 `paddleocr_clova_eval.py` 그리드 sweep. (계획서 §4·§5) — *메인 `.venv`에선 paddle 실행 불가*
4. **[단계 A] det 노브 배선** — `paddle.py:_predict_kwargs`에 `text_det_box_thresh / text_det_unclip_ratio / text_det_thresh / use_dilation` 추가 + `config.py` 필드. (현재 3노브만)
5. **[단계 B] A100 모델 회수 후** — holdout 재평가 + 승격 게이트(`gate_paddleocr_text_extraction_target.py`).
6. **[평가 후속] 미배선 자산 연결 설계** — 학습된 8-class 섹션 `best.pt`(mAP50 0.219)는 성능 미달이라 재학습 필요; `VISION_CLASSIFIER_MODEL` 연결은 쓸만한 mAP 확보 후.

## 게이트/활성화 현황
| 항목 | 상태 |
|---|---|
| OCR benchmark (teacher-eval ready) | 통과 |
| PaddleOCR 95% target | **미달** (지표 자체가 도달 불가 → §3 재정의 선행) |
| YOLO section detector | 가중치 존재하나 mAP50 0.219 + 미배선 |
| 런타임 OCR primary | `clova` (Mac은 paddle 설치 불가가 근본 이유 중 하나) |
| 멀티모달 비전/ROI | 기본 OFF + prod 사인오프 필요 |

## 우선순위 추천
1. **지표 재정의 + ROI 텍스트-공간 스코핑**(§3·§2 A) — 학습 없이 가장 큰 임팩트, 며칠 내 측정 가능.
2. **단계 A 설정/전처리 벤치**(`.venv-paddle`) — server_detection·해상도·CLAHE.
3. **단계 B A100 재학습**(교정된 레시피) — primary 승격 도전.
4. **env/버전 통일 + Docker primary 검증** — 승격 전 인프라 정합성.
