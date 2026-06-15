# 다음 세션 이어가기 프롬프트 v2 (2026-06-12 세션 종료 시점)

> 아래 블록을 다음 세션의 첫 메시지로 그대로 붙여넣으면 됩니다. (v1을 대체 — v1은 이 세션 시작 시점 기준)

---

Lemon-Aid 프로젝트 작업을 이어서 진행해줘. 아래는 직전 세션까지의 정확한 상태다.

## 저장소 / 환경
- 로컬 루트: `/Volumes/Corsair EX400U Media/yeong_offload/99_me/00_github/03_lemon_healthcare/Lemon-Aid` (경로 공백 — 셸에서 항상 따옴표. 작업 전 `git rev-parse --show-toplevel`로 루트 확인)
- 브랜치: `feat/ai-agent-chat-import` · 리모트 `origin`=팀(Lemon-Aid-KDT/Lemon-sin, PR 대상 develop), `personal`=개인(HorangEe02/Project_yeong). **양 리모트 `6bc52340`까지 푸시 완료, 미푸시 커밋 없음**
- 빌드 타깃: Pixel 10 Pro(AVD `Pixel_10_Pro`, `ANDROID_SDK_ROOT=~/Library/Android/sdk` 필수, **반드시 `--flavor dev`** — 미지정 시 "No application found") / iPhone 17 Pro **iOS 26.5 = UDID `7B2E1A72-B3C9-4102-8E3C-0009CCBFB4FB` 필수 지정**(동명 기기가 26.3/26.4 런타임에도 존재 — 이름 선택 금지. 구 문서의 `71FB0384…`는 26.3 기기였음)
- dev 스택: `docker compose up -d db backend` (db=pgvector pg16, backend 127.0.0.1:8000, AUTH_MODE=disabled, dev 오너 subject=`local-development::local-dev-user`). DB는 alembic **0042까지 적용**. `PERSIST_DAILY_HEALTH_SCORE` compose 기본 **true**. 컨테이너에 Ollama 없음 → LLM 결정론 폴백(코칭 ~18초 정상)
- MEDICAL-WIKI 코퍼스: `/Volumes/Corsair EX400U Media/LLM-WIKI/MEDICAL-WIKI/`가 진본(원본 디렉터리는 삭제 완료). 백엔드 기대 경로는 심링크 `…/03_lemon_healthcare/MEDICAL-WIKI → LLM-WIKI/MEDICAL-WIKI`(레포 밖). reviewed_claims 42·eval inputs 84·fixtures 94. **컨테이너 런타임은 이 코퍼스를 안 읽음**(스크립트/eval 전용 — medical_wiki_claims는 런타임 import 체인에 없음)
- 에뮬레이터 카메라 라이브 프리뷰는 `mobile/scripts/dev_mac_camera_bridge.py`(8755) 필요 — 미가동이 기본, 갤러리 경로가 공식 대체

## 완료된 것 (이 세션 — 전부 검증·커밋·푸시됨)
1. **Android 통합 테스트 마감**: 진짜 원인은 flavor가 아니라 flutter_local_notifications 22.0.0 desugaring 미설정 → build.gradle.kts 수정, `flutter test integration_test -d emulator-5556 --flavor dev` 통과 (2a232d19)
2. **iOS 26.3 오설치 문제 해결**: UDID 교정(위 환경 참조) + 핸드오프/메모리 갱신 (4041bae0)
3. **챗 스냅샷↔대시보드 422 계약 버그 수정**: 챗 승인 영속(`{analysis_kind,snapshot}`)이 같은 `analysis_type='nutrition_analysis'`를 공유해 홈 대시보드 422 유발 → `nutrition_diagnosis.py` 최신행 조회에 JSONB `result_snapshot ? 'results'` 필터. TEST_DATABASE_URL 옵트인 회귀 테스트 2건(실PG 통과), 라이브 422→200 (013384d2)
4. **UI 풀사이클 워크스루(Android 완주)**: 챗 승인 루프 2단계+영속+대시보드 200 회귀 / FAB→분할동의→카메라(2슬롯)→갤러리→analyze 202→후보(저장1·검토3)→`POST /supplements` 201→홈 반영 / 캘린더·분석·설정 렌더. 스크린샷 /tmp/lemon-aid-walkthrough/. **iOS는 빌드·설치·홈 렌더만 검증**(에뮬레이터 입력 불안정으로 iOS 인터랙티브 미수행)
5. **Figma Dev Mode 감사+적용**: 시맨틱 20·yellow 5단계·타이포 크기 일치 확인. 결정 반영 — brand_palette를 Figma에 정렬(+deep/tint 추가, 33cbda56), 마지막 v3 import였던 medical_disclaimer를 v2 마이그레이션(9f3d6294, **v3 파일은 import 0건 — 별도 PR 삭제 가능**), 자간은 현행 0 유지(Figma 측 수정 항목). 감사 보고서: `outputs/todo-list/2026-06-12/2026-06-12-figma-design-system-audit.md`
6. **가이드 06 결정 #7 채택+구현**: 점수 영속 flag 기본화 + 목록 응답에 score/measured_date/label 요약 필드 + 모바일 `_TrendChartCard`(CustomPainter, 7일 미만 잠금) (f8e1c07d). 시드 검증 후 시드 삭제 — DB는 유기적 상태
7. **Supabase Auth 채택 ADR**: `docs/Integration-docs/39-auth-backend-adr-supabase-auth.md` (PR#4 임포트로 36→39 리네임됨)
8. **가이드 10 UIUX 패리티 감사+P1**: `mobile/uiux/implementation-guides/10-uiux-parity-audit-plan.md` (P1/P2/P3 분류·플랫폼별 절차). P1 적용 — 챗 상시 면책 라인(+금칙어 가드 정확일치 허용), 분석 탭 '오늘 실천 추가하기' CTA+다이얼로그(세션 로컬), 카메라 전환 버튼은 기구현 확인(bridge 모드만 숨김) (1e4c666d)
9. **팀원 PR#4 경로 단위 병합 완료(Phase 0~5)**: 분석 보고서 `outputs/todo-list/2026-06-12/2026-06-12-pr4-delta-analysis-and-merge-plan.md`가 권위. 코어 ai_agent_chat 20파일(0a66abea)·표면 수동 패치·스크립트 12종(429ae8f8)·문서+README 2계열 병합(6b9c83e1)·agent-backend-ci.yml(e931f7c0). **핸드머지 판단 2건 유지 필수**: ai_agent.py의 `validate_local_ollama_settings` 가드 유지(그들 제거분 기각 — 테스트로 미검출되는 보안 구멍), app_health_analysis.py의 commit 패턴 유지(그들 session.begin() 복귀는 라이브 500 회귀). 검증: 패키지 184·백엔드 2191(허용 2건 외 0)·모바일 360·merge smoke --llm none 4/4·라이브 스모크(화이트리스트/boundary/승인영속/대시보드200) 전부 그린
10. **OCR field-match 확정판 가이드라인**: `docs/ocr_baseline_reports/2026-06-12-ocr-field-match-design-and-team-guideline.md` (6bc52340) — 실측 스냅샷(§0)·실CLI·코드 기준 metric 명세·공식 문서 URL 검증·AGPL 리스크. 초안(`2026-06-12-ocr-yolo-gemma4-roadmap-guidelines.md`)은 사용자 WIP로 보존 중 — 대체/보존 결정 미정
11. **A100 트랙**: b32 후보 best ned **0.90132**(학습 val — holdout structured gate 미실행, 승격 판단 금지). lr1e4_b16 `after_lr5e5` run(PID 30364) 가동 중 + **train.log 기반 원본 워처 부착 완료**(patience 10, status: `early_stop.<suffix>.status.json`). 이 run은 체인 마지막 — 정지 후 자동 후속 없음

## 품질 게이트 현황
- 모바일: `flutter analyze` 0건 + 테스트 **360** 전통과
- 백엔드: `backend/.venv/bin/python -m pytest Nutrition-backend/tests -q -o addopts=""` → **2191 passed**, 허용 실패 2건만(supabase MCP config·OCR readiness — 사용자 WIP)
- ai_agent_chat 패키지: `PYTHONPATH=ai_agent_chat/src pytest ai_agent_chat/tests` → 184 passed, 1 skipped
- merge smoke: `backend/.venv/bin/python -X utf8 backend/scripts/run_agent_llm_merge_smoke.py --llm none` → 4/4

## 즉시 할 일 (우선순위)
1. **PR#4 사후 팀 공유 3건**: ① 팀원에게 app_health_analysis 트랜잭션 차이 역반영 요청(그들 브랜치는 라이브에서 챗 영속 500), ② strict SGLang smoke(`--require-answerable-llm`)는 SGLang 보유 환경에서 실행 필요, ③ `smoke_ai_agent_server.py`의 Supabase ref 하드코딩(`ajgvoxttzsjcwtphtsuz`) 우리 프로젝트 일치 확인. PR#4에 병합 완료 코멘트 회신 검토
2. **iOS 인터랙티브 워크스루**: 시뮬레이터 26.5에서 챗 면책 라인·추이 카드·실천 추가 실화면 확인(Android는 완료, 에뮬레이터가 불안정해지면 재부팅)
3. **가이드 06 잔여**: (b) 실천 체크/커스텀 항목 SharedPreferences 영속(coaching_check_store), (c) 날짜 칩 과거 조회, (d) 점수 링 등급색 헬퍼(_labelColor — 추이 포인트는 적용됨)
4. **가이드 10 P2**: ready-상태 재검(기록 1건 입력 후 홈/분석 재캡처) → kcal 진행 바·영양소 상세 CTA 확정, 영양제 확인 화면 보강(분류/직접추가/복용 컨트롤)
5. **OCR 트랙(확정판 가이드라인 §9.0 순서)**: PII 스크리닝 215건 해소(최우선 차단 해제) → b32 후보 holdout structured 재평가 → det thresh 3종 런타임 배선 티켓 → 검출기 재학습(mAP50 0.2349→0.70)
6. **(별도) A100**: lr1e4_b16 조기종료 시 best 회수(b16/b32 비교)→structured eval→승격 게이트(field_match≥0.85, ned≥0.90). 상태 확인: `ssh -i ~/.ssh/lemon_a100_ed25519 -p 8875 lemon-aid@155.230.153.222 'powershell -NoProfile -ExecutionPolicy Bypass -File G:\lemon-aid\paddleocr_rec_work\a100_compact_status_check.ps1'` (**Bypass 필수**, cmd 인용 문제 시 EncodedCommand 사용). 원격 실행은 사용자 승인 후
7. **P2 트랙**: Supabase Auth 착수(ADR 39 — 프로젝트 생성·소셜 키는 팀 액션), Health Connect 결정, 알림 센터
8. **문서 정리 결정**: OCR 초안 로드맵(사용자 WIP) 대체/보존, design_tokens_v3 삭제 PR

## 적용 중인 규칙 (위반 금지)
**협업/품질**: 수치·결과 추정 금지(확인값만) · framework 파라미터 변경 시 공식 문서 확인+URL 주석 · private image/raw OCR/provider payload/secret 결과물·커밋 금지 · 원격(155.230.153.222) 실행은 사용자 승인 후 · 원본 dataset(`rec_dataset\v2`) 불가침 · Conventional Commits+본문 "왜" · **사용자 요청 없이 commit/push 금지** · remote/branch 혼동 금지 · Google/NumPy docstring · 주석은 "왜" 중심
**프로젝트**: 의료법 금칙어(진단/처방/치료/효능) 금지+신규 문구 가드 테스트(표준 면책 문장은 정확 일치만 화이트리스트) · 신뢰도 % 미노출(등급 칩) · 면책 푸터 필수 · 디자인 토큰 **design_tokens_v2만**(v3는 import 0건 — 삭제 대기) · ApiClient 경로 `/api/v1` 접두사 제거 · 403 consent_required→1회 동의 재시도 · 시니어 최소치(본문 15px+/버튼 52px+) · 신규 PII 테이블 0041 FORCE RLS 패턴 · Integration-docs **신규 번호 40+**(02~12 이중 계열 — 링크는 파일명 전체로)
**PR#4 병합 후 보호 목록(덮어쓰기 금지)**: `src/llm/ollama.py` · `llm_wiki_retrieval.py`·`wiki_embedding_targets.py` · `requirements-dev.txt`(PyYAML) · alembic 전체(그들 체인은 우리 0030~0040과 동일 — 그들 신규 0018+는 0043+로 리베이스, RLS 체크) · ai_agent.py LLM 가드 · app_health_analysis.py commit 패턴
**구현 방식**: 화면 작업은 가이드(`mobile/uiux/implementation-guides/0X`) ④ 체크리스트 권위, "백엔드 공백" 임의 구현 금지 · 팀원 브랜치는 공통 조상 없음 — **git merge 금지, 경로 단위 임포트만**(임포트 시 자동 스테이징 주의 — 커밋 전 인덱스 확인)

## 참조 문서
- PR#4 병합 기록(권위): `outputs/todo-list/2026-06-12/2026-06-12-pr4-delta-analysis-and-merge-plan.md`
- UIUX 패리티: `mobile/uiux/implementation-guides/10-uiux-parity-audit-plan.md` · Figma 감사: `2026-06-12-figma-design-system-audit.md`
- OCR 확정판: `docs/ocr_baseline_reports/2026-06-12-ocr-field-match-design-and-team-guideline.md`
- 가이드 인덱스: `mobile/uiux/implementation-guides/00-overview-and-conventions.md` · frame id: `mobile/uiux/figma/_frames_index.md`
- 점수 결정: `outputs/todo-list/2026-06-11/2026-06-11-daily-health-score-decisions.md` (#7 채택 완료)
