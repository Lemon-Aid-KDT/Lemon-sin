# 2026-06-10 PaddleOCR 성능 개선 — 실행 체크리스트

> 전체 설계: `docs/ocr_baseline_reports/2026-06-09-paddleocr-performance-improvement-plan.md`
> 실행 환경 규칙: paddle 실행/벤치는 **`.venv-paddle`(py3.12)** 또는 **A100**. 메인 `.venv`(py3.13)는 paddle 설치 불가. (계획서 §1.5)

---

## 단계 A — Quick Wins (학습 無, 목표 1주)
- [ ] **A1 지표 재정의** — 0.95 char-LCS precision 게이트 폐기 → recall + field_match + 실사진 line-level CER(NFC·단위 정규화 후). `gate_paddleocr_text_extraction_target.py` 기준 수정. *(메인 .venv 가능)*
- [ ] **A1b ROI 텍스트-공간 스코핑** — `parse_label_layout`(`layout_parser.py:218`)로 섹션 텍스트만 채점 대상화 → 무학습 F1 0.33→0.50+ 검증. **최우선 레버.**
- [ ] **A2 server_detection 프로파일** — `LOCAL_OCR_MODEL_PROFILE=server_detection`(server det + 한국어 mobile rec 유지). ⚠️ `server`는 한국어 rec 손실 → 금지. *(.venv-paddle/A100)*
- [ ] **A3 검출 해상도 상향** — `LOCAL_OCR_TEXT_DET_LIMIT_TYPE=max`, `LOCAL_OCR_TEXT_DET_LIMIT_SIDE_LEN=1280`(필요시 1536).
- [ ] **A4 det 노브 배선 + sweep** — `paddle.py:_predict_kwargs`에 `text_det_thresh(0.2)/text_det_box_thresh(0.45)/text_det_unclip_ratio(2.0)/use_dilation` 추가 + `config.py` 필드 + `.env.example`.
- [ ] **A5 `label_enhance` 전처리 모드** — `preprocessing.py`에 OpenCV: CLAHE(2.5,8x8)+denoise+deskew+조건부 업스케일(텍스트<32px), 이진화 금지, `max_side_px` 2048→3000.
- [ ] **A6 ROI 크롭 패딩** — 박스마다 `max(12px,0.12*box_h)` 패딩(Issue #15603 타이트크롭 회피), 섹션별 독립 OCR.
- [ ] **A7 단위 정규화 post-pass** — `ug→μg, mcg→μg, lU/Iu→IU, 숫자 내 O→0`.
- [ ] **A-게이트** — 위 변경의 before/after를 `paddleocr_clova_eval.py` 그리드로 측정, holdout 52에서 recall/field_match **+0.05↑** 확인 후 기본값 채택.

## 단계 B — 도메인 파인튜닝 (A100, 목표 2–4주)
- [ ] **B1 LR 정상화** — 5e-4 → **piecewise [1e-4, 2e-5]**(bs=128).
- [ ] **B2 일반:도메인 1:1 혼합** — `label_file_list=[domain, general]`, `ratio_list=[1.0, 0.1]` (forgetting 방지).
- [ ] **B3 dict 유지** — `korean_dict.txt` 그대로 우선(변경 시 초기 acc=0); 단위 기호 필요 시 최소 확장.
- [ ] **B4 증강 조정** — RecConAug 제거 / RecAug 유지.
- [ ] **B5 학습** — `run_a100_paddleocr_windows_training.ps1 -Mode full -Epochs 100 -BatchSize 128 -LearningRate 0.0001`, eval/500iter, best by acc.
- [ ] **B6 export + 연결** — `export_model.py` → `LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR` 지정 → `ENABLE_LOCAL_OCR=true`.
- [ ] **B7 (선택) det 파인튜닝** — 행 분리 불량 시(>=500장, lr~1e-4, bs=8). `paddle.py`에 `text_detection_model_dir` kwarg 추가 필요.
- [ ] **B-게이트** — holdout 52에서 baseline 전 지표 초과 + 절대하한(field_match ≥0.85, norm_edit_dis ≥0.90) → `gate_paddleocr_finetune_against_baseline.py`.

## 단계 C — 데이터·증류 (전략, 4주+)
- [ ] **C1 teacher 증류 라벨링** — CLOVA+Google Vision 합의(정규화 edit-dist ≤ε) line-crop만 채택. **선결: teacher 원문 보존 정책 예외**(사용자 결정 필요).
- [ ] **C2 StyleText 스타일 합성** — 실 라벨 크롭 스타일로 코퍼스 재렌더(sim-to-real).
- [ ] **C3 SynthTIGER/KoTDG** — 배경/블러/노이즈/롱테일 균형, 희귀 단위 오버샘플.
- [ ] **C4 도메인 코퍼스** — DB 카탈로그에서 성분명·함량+단위·섭취문구 추출 + dict 커버리지 점검.
- [ ] **C5 (선택) CML 증류** — 평문 파인튜닝이 baseline 초과 후 +3–5%.
- [ ] **C6 (선택) VLM 파일럿** — 정체 시 PaddleOCR-VL/surya를 GPU 한정 provider로 추가, 동일 게이트 비교.

## 승격 (단계 A/B/C 게이트 통과 후)
- [ ] **인프라 정합성** — Docker `INSTALL_LOCAL_OCR=true`, `PRELOAD_PADDLEOCR=true`, 모델 dir 포함, paddlepaddle 버전 통일.
- [ ] **전환** — `OCR_PRIMARY_PROVIDER=paddleocr`(CLOVA는 fallback로 강등) + 회귀 모니터.

---

## 환경 메모
- 벤치/학습: `.venv-paddle`(py3.12, CPU) 또는 A100(CUDA). server det은 CPU에서 ~4.3s/img로 느림 → 대량은 GPU.
- 메인 백엔드(`.venv` py3.13)는 paddle import 시 `OCRError`(설치 불가) — 코드 테스트는 mock/provider 격리로.
- 데이터셋·teacher 라벨·게이트 JSON·`.env`는 git 미추적(local-only).
