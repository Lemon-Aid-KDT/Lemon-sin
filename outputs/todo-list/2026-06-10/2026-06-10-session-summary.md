# 2026-06-10 세션 요약 — 파이프라인 구현 평가(v2) + PaddleOCR 개선 계획 + env-split 검증

## 한 줄 요약
YOLO26→PaddleOCR→Ollama 파이프라인을 **설계 대비 구현 충실도로 재평가**(멀티에이전트 18개: 코드매핑 5 + 웹리서치 5 + 적대적검증 6)하고, **PaddleOCR 성능 개선 계획서**를 작성. 추가로 **"Mac 백엔드 venv에 PaddleOCR 미설치"** 주장을 직접 검증 → 사실이자 **문서화된 env-split**임을 확인하고 두 문서에 반영.

## 완료 항목

### 1) 파이프라인 구현 평가 (v2)
- 산출물: `docs/ocr_baseline_reports/2026-06-09-pipeline-implementation-evaluation-v2.md`
- 결론: **골격 A급, 통합·활성화·지표 C급 → 종합 ~55/100** ("설계대로 만들었으나 설계대로 켜지 않음").
- 컴포넌트별 일치도: YOLO ROI 55% · PaddleOCR 55% · gemma 비전 60% · qwen 텍스트RAG+면책 62% · 오케스트레이션 45%.
- 모든 격차는 `file:line` 근거로 적대적 재검증(거짓 양성 제거). 정정 확보: qwen은 `docker-compose.yml:65` 배포층에서 실제 텍스트 모델로 주입, Google Vision 어댑터 존재(미벤치), 학습된 8-class 섹션 `best.pt`는 디스크에 있으나 `VISION_CLASSIFIER_MODEL` 미연결.

### 2) PaddleOCR 성능 개선 계획서
- 산출물: `docs/ocr_baseline_reports/2026-06-09-paddleocr-performance-improvement-plan.md`
- **저성능 진짜 원인(검증)**: recognizer 한계가 아님 →
  1. **지표가 깨짐** — 섹션-only GT로 전체이미지 채점 → precision ~0.30 캡, char-LCS F1 상한 **0.68–0.71**, 0.95는 **수학적으로 도달 불가**.
  2. **공짜 레버 미사용** — `server_detection`(server det + 한국어 mobile rec 유지) / det 해상도 / CLAHE+업스케일 / ROI 텍스트-공간 스코핑(`parse_label_layout`, 무학습 F1 0.33→0.50+ 예측).
  3. **학습 레시피 오류** — 합성 2-epoch CPU가 catastrophic forgetting(0.518→**0.037**): 일반데이터 미혼합 + 과한 LR(5e-4) + dict 변경.
- 로드맵: **A**(무학습 설정·전처리, 1주) → **B**(A100 도메인 파인튜닝, 2–4주) → **C**(teacher 증류·StyleText/SynthTIGER, 4주+) → 게이트 통과 시 `OCR_PRIMARY_PROVIDER=paddleocr` 승격.
- 함정 명시: **한국어 server recognizer는 없음** → `server` 프로파일은 한국어 정확도 하락, 반드시 `server_detection` 사용.

### 3) env-split 검증 (신규)
- 직접 확인: `.venv`(py3.13.7, 메인 백엔드) → `import paddleocr` **ModuleNotFoundError**(설치 불가) / `.venv-paddle`(py3.12.13) → paddleocr 3.6.0 + paddlepaddle 3.3.1(CPU, `cuda=False`).
- **버그 아님, 문서화된 의도**(`docs/handoff/2026-06-06-clova-gt-paddleocr-prompt.md:45`): macOS arm64 + py3.13 휠 부재 → paddle은 전용 py3.12 env에만. paddle 스크립트는 백엔드를 import하지 않고 독립 실행 → JSONL → py3.13 백엔드 병합.
- **프로덕션은 다름**: `backend/Dockerfile`(linux py3.13) + `INSTALL_LOCAL_OCR=true` → in-image 설치되어 인프로세스 동작 가능.
- 반영: 개선 계획서에 **§1.5 실행 환경 제약(env-split)** 신설, 평가 문서 gap#7(재현성)에 보강.

## 핵심 수치 (측정된 baseline, 변동 없음)
| 구분 | holdout char-LCS F1 | field_match | 95% 게이트 |
|---|---:|---:|---|
| PaddleOCR mobile baseline | (P0.31/R0.51) | 0.560 | 미달 |
| A100 크롤링 파인튜닝 best(p10) | **0.324** (P0.32/R0.53) | 0.562 | 미달(continue_training_loop) |
| 합성 2ep CPU(실패 사례) | — | 0.518→**0.037** | 붕괴 |
| 실사진 7장 CER | 38.27% | — | (입력 품질이 주원인) |

## env / 버전 드리프트 (통일 필요)
| 위치 | paddlepaddle | paddleocr |
|---|---|---|
| pyproject `ocr-local` 핀 | 3.2.0 | >=3.6,<3.7 |
| 로컬 `.venv-paddle` | 3.3.1 | 3.6.0 |
| A100 원격 | 3.2.2(GPU) | 3.6.0 |
| Dockerfile | 3.2.0 | >=3.6,<3.7 |

## 산출물
- `docs/ocr_baseline_reports/2026-06-09-pipeline-implementation-evaluation-v2.md`
- `docs/ocr_baseline_reports/2026-06-09-paddleocr-performance-improvement-plan.md` (§1.5 env-split 포함)
- `outputs/todo-list/2026-06-10/` (본 요약 + next-steps + paddleocr-improvement-todo)

## 비고
- 코드 변경 없음(분석·문서 세션). 평가/계획의 모든 load-bearing 코드 사실은 실제 소스로 재확인됨(`parse_label_layout` 존재, `server_detection`=server det+korean mobile rec, `_predict_kwargs` 3노브만 배선).
