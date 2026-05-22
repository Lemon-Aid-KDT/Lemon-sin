# 2026-05-17 Lemon Aid 주간 발표 요약

> 기준 기간: 2026-05-11 월요일 00:00 ~ 2026-05-17 일요일
> 작성 목적: Daily 기록을 발표/멘토링용 주간 브리핑으로 압축한다.

## 1. 이번 주 한 줄 결론

이번 주는 Lemon Aid MVP가 "아이디어/문서 정리"에서 "인증, OCR, 영양제 preview, Agent 검증 계약, 데이터/DB 안전 기준"을 실제 구현 단위로 쪼개는 단계로 이동한 주간이다. 다만 Daily 기준으로는 여러 작업이 브랜치별 초안, TODO, 로컬 요약, harness에 머물러 있어, 다음 주에는 하나의 시연 경로를 위해 API/DB/UI/Agent 계약을 먼저 고정해야 한다.

## 2. 주간 진행 요약

이번 주 Daily 근거는 2026-05-13부터 2026-05-17까지 존재한다. 2026-05-11, 2026-05-12 Daily는 없으므로 이틀의 진행은 이번 요약에서 근거 없음으로 둔다. 사용 가능한 기록 기준으로 보면, 초반에는 문서 운영 구조와 소셜 로그인, Python/CI, OCR/영양제 분석 기반이 병렬로 움직였고, 중반에는 인증 흐름과 KDRIs/근거 자료, OCR provider 정책이 더 구체화되었다.

구현 흐름의 핵심은 세 갈래다. 첫째, 모바일과 백엔드 인증이 이메일 인증, Google/Kakao OAuth, secure storage, Redis rate-limit, router guard 쪽으로 확장되었다. 둘째, 영양제 OCR/LLM 분석은 바로 저장하지 않고 preview와 `needs_review` 상태를 거치도록 모델과 검증 시나리오가 생겼다. 셋째, AI Agent는 실제 서비스 연결보다 먼저 harness, fixture, safety policy, tool preview 같은 검증 가능한 계약을 세우는 방향으로 정리되었다.

문서와 팀 운영도 이번 주의 중요한 진전이다. `changmin-plan` Daily 문서는 단순 커밋 목록이 아니라 PROJECT_GUIDE 기준 단계, 의존 관계, 병합 리스크, 팀 결정 필요 항목을 남기는 운영 문서로 자리 잡았다. `taedong-design`과 `yeong-tech` 쪽 TODO/HANDOFF는 데이터 수집, OCR provider, DUR 룰, 모바일 카메라 API 연결, DB 적재, 동의 audit 같은 다음 작업을 팀원별로 나누는 근거가 되었다.

아직 검증되지 않은 부분도 분명하다. 커밋 기준으로 실제 사용자가 앱에서 촬영하고, OCR preview를 보고, 안전 문구를 확인한 뒤, Agent 설명 또는 저장 전 상태까지 이어지는 end-to-end 동작은 확인되지 않았다. 특히 외부 OCR, DUR/복약 주의, 만성질환 정보, 동의 철회, raw OCR 저장 정책은 건강·개인정보 영역이므로 Safety Rules 기준 검토가 필요하다.

## 3. PROJECT_GUIDE 기준 현재 단계

커밋/문서 기준으로는 W3~W4 Phase 1 코어 구현이 중심이고, W5~W6 Phase 2 Agent 통합을 위한 선행 계약도 일부 준비되는 주간으로 보인다. 다만 Daily 근거 상당수가 TODO, handoff, harness, 로컬 작업 요약이므로 실제 통합 완료가 아니라 "진행 중"과 "검증 필요"로 표현한다.

| Guide 기준 단계 | 이번 주 근거 | 아직 부족한 부분 | 다음 우선순위 |
|---|---|---|---|
| W3~W4 / Phase 1 코어 구현 | 인증 API/모바일 OAuth, 이메일 인증, Redis rate-limit, 영양제 preview 모델, Google Vision/PaddleOCR 비교, `/api/v1/supplements/analyze` 후보가 Daily에 반복 등장 | 로그인 이후 온보딩, OCR preview API, DB 저장 정책, Flutter 결과 화면 연결은 end-to-end 검증 필요 | `preview -> user_confirmed -> saved` 상태와 multipart analyze 응답 shape 고정 |
| W5~W6 / Phase 2 Agent 준비 | Agent harness, fixture, safety policy, consent revoked scenario, tool preview, governance/correction rule 설계가 문서 기준으로 준비 | 실제 orchestrator, AgentInput/AgentOutput, safety filter, Mobile 승인 UI와 연결된 근거 부족 | Agent schema와 tool preview 계약을 백엔드 DTO와 맞추기 |
| Safety / Privacy 기반 | 외부 OCR fail-closed, raw OCR text 저장 금지, 동의 audit, OAuth key 안전 주입, 민감정보 저장 최소화가 여러 Daily에서 강조 | Google Vision raw payload, ngrok 공개 테스트, DUR 주의 문구, 만성질환/복약 데이터 처리 정책 검증 필요 | 외부 OCR 동의 문구, 저장/로그 정책, DUR 표현 기준 확정 |
| QA / 통합 준비 | Python 3.13/CI, DB smoke, pytest 기록, readiness/ngrok 확인 기록이 문서에 남음 | 브랜치별 구조가 달라 같은 명령이 main 통합 후 재현되는지 확인 필요 | 표준 경로와 CI 경로를 먼저 정리 |

## 4. 이번 주 진전된 구현 흐름

### OCR / 분석

- 영양제 라벨 OCR은 Google Vision, PaddleOCR, ROI/촬영 품질, 다중 이미지 업로드, parser/domain correction, action contract까지 논의가 확장되었다.
- 커밋 기준으로는 영양제 분석 preview 모델이 추가되어 성분명, 함량, 단위, 근거 텍스트, confidence, 공식 출처 매칭 여부를 사용자 확인 전 상태로 묶는 방향이 확인된다.
- 문서 기준으로는 외부 OCR 기본값을 꺼 두고, 이미지 외부 전송은 별도 동의가 필요하다는 fail-closed 원칙이 반복된다.

### Backend / API

- 인증 API는 이메일 인증, Google/Kakao OAuth, token refresh/logout, Redis rate-limit까지 확장되었다.
- OCR 쪽은 `/api/v1/supplements/analyze`, readiness `/ready`, DUR 기반 `/api/v1/safety/check`가 다음 계약 후보로 정리되었다.
- 실제 API shape는 아직 팀 결정 전이다. Mobile, OCR parser, DB, Agent가 같은 DTO를 보도록 Pydantic/OpenAPI 계약을 먼저 고정해야 한다.

### DB / 데이터

- `users`의 social login 컬럼, 이메일/password nullable 정책, 이메일 인증 저장소, Redis rate-limit key, KDRIs 2025 source manifest, chronic priority reference가 Daily 근거로 등장한다.
- DUR CSV/parquet와 rule JSON은 복약/영양제 주의 흐름의 다음 데이터 기반으로 제안되었다.
- KDRIs 2025 사용 여부는 `PROJECT_GUIDE.md`의 기존 KDRIs 기준과 차이가 있어 팀 결정이 필요하다.

### Mobile / UI

- 모바일 인증은 Dio, Riverpod, secure storage, router redirect, OAuth service, 최근 로그인 표시, 설정 로그아웃까지 실제 앱 흐름에 가까워졌다.
- 다음 UI 핵심은 camera screen에서 `/api/v1/supplements/analyze`로 multipart 업로드하고, success/partial/retry/error 또는 `needs_review` 상태를 결과 화면으로 분기하는 것이다.
- OCR 테스트 UI와 Flutter 실제 화면의 계약이 다를 수 있어, 테스트 UI에서 검증한 action contract를 Flutter 상태 enum으로 옮기는 작업이 필요하다.

### Auth / Security / Privacy

- OAuth key는 코드에 박지 않고 환경 주입으로 관리하는 방향이 정리되었다.
- refresh token 저장, revoke, Redis rate-limit, 이메일 인증은 실제 보안 흐름으로 커지고 있다.
- ngrok과 `AUTH_MODE=disabled`는 임시 테스트 경로로만 보아야 하며, 테스트 종료 후 공개 URL과 인증 비활성화 상태를 닫았는지 확인해야 한다.

### AI / Agent

- Agent는 바로 서비스에 붙이기보다 harness, fixture, scenario, safety policy로 먼저 검증하는 구조가 생겼다.
- `분석 알고리즘 + 3 Agent` 용어 정렬이 반복되며, 분석 알고리즘을 Agent로 오해하지 않게 분리하려는 방향이 확인된다.
- supplement preview, meal evaluation, chat reminder, consent revoked 시나리오가 준비되었으나 실제 orchestrator와 API 연결은 검증 필요다.

### Docs / Team Workflow

- Daily 문서는 팀 브랜치 활동을 PROJECT_GUIDE 기준으로 해석하는 운영 도구가 되었다.
- 이번 주 문서들은 매일 반복되는 리스크를 누적해 보여준다: 표준 경로 결정, API/DB 계약 충돌, safety wording, 데이터 라이선스, 외부 OCR 동의, CI 복원.
- 주간 요약 기준으로는 5월 13~17일 Daily만 근거로 사용했고, `reports/`, `team-progress.md` 같은 helper 문서는 제외했다.

## 5. 시연 가능성

| 구분 | 현재 보여줄 수 있는 흐름 | 아직 mock/문서/TODO인 흐름 | 다음 주까지 고정할 것 |
|---|---|---|---|
| 사용자 시연 | 모바일 인증 흐름 일부, OAuth/이메일 인증 방향, OCR 테스트 UI/ngrok 기반 확인 흐름 | Flutter 카메라 화면에서 실제 analyze API로 이어지는 완성 경로 | iPhone 촬영 -> preview 응답 -> 사용자 확인 화면 |
| 백엔드/API 시연 | 인증 API, `/ready`, analyze API 후보, supplement preview 모델 단위 | `/api/v1/supplements/analyze` 최종 response, confirm API, safety check API | OpenAPI/Pydantic DTO와 예시 응답 |
| AI/OCR/Agent 시연 | Google Vision/PaddleOCR 비교 방향, Agent harness/scenario, safety policy | 실제 OCR 결과를 AgentInput으로 넘기는 흐름 | OCRResult, PreviewResult, AgentInput 매핑 |
| 안전/개인정보 설명 | fail-closed OCR, raw OCR 저장 금지, consent gate, OAuth key 환경 주입 원칙 | 외부 OCR 동의 화면, raw provider payload 저장/삭제 정책, DUR 표현 검수 | 안전 문구 표준과 동의/audit schema |

## 6. 팀 공유·결정 필요

| 결정 주제 | 왜 필요한가 | 영향 받는 파트 | 제안 상태 |
|---|---|---|---|
| OCR preview/action contract | 화면이 단순 오류가 아니라 재촬영, 영역 선택, 추가 사진 요청으로 분기해야 함 | Mobile, Backend, OCR, Agent | 팀 결정 필요 |
| `preview -> user_confirmed -> saved` 상태 | OCR/LLM 결과를 사용자 확인 없이 건강 기록으로 확정하면 위험함 | Backend, DB, Mobile, Safety | 팀 결정 필요 |
| `/api/v1/supplements/analyze` 응답 shape | Mobile camera, OCR parser, Agent 입력이 같은 구조를 봐야 함 | Backend, Mobile, AI | 사전 조율 필요 |
| KDRIs 기준 연도 | Daily에는 2025 데이터 승격이 나오지만 Guide 일부는 2020 기준을 언급함 | Data, AI, Docs, Safety | 검토 필요 |
| DUR 주의 레벨 표현 | 복약/영양제 주의가 진단·처방처럼 보일 수 있음 | Backend, Mobile, Agent, Safety | 안전 검토 필요 |
| 표준 backend/data 경로 | `backend/src`, `backend/Nutrition-backend`, `data/rda`, `data/nutrition_reference` 기준이 갈림 | 전체 | 팀 결정 필요 |
| 외부 OCR provider 정책 | Google Vision은 이미지 외부 전송, PaddleOCR은 local runtime/모델 관리 이슈가 있음 | OCR, Privacy, Infra | 안전 검토 필요 |
| 데이터 수집 자산 사용 범위 | Shop API, NIH DSLD, Open Food Facts, 자체 사진은 라이선스와 용도가 다름 | Data, OCR, Docs, Legal | 검토 필요 |

## 7. 다음 주 우선순위

1. Backend/Mobile/AI 공통으로 `SupplementAnalysisPreview` 또는 동등 DTO를 고정하고, `preview`, `needs_review`, `user_confirmed`, `saved`, `failed` 상태를 합의한다.
2. DB/Auth는 user/profile/consent/audit, DUR 적재 후보 테이블, refresh token 흐름을 먼저 정리해 OCR/Agent가 의존할 수 있는 기반을 만든다.
3. OCR은 Google Vision 실제 라벨 E2E와 PaddleOCR runtime 활성화 여부를 구분하고, 외부 OCR 동의와 raw data 저장 정책을 문서화한다.
4. Mobile은 camera screen multipart upload와 결과 상태 UI를 mock 응답으로 먼저 붙이고, OAuth 실기기 QA를 별도 확인한다.
5. Agent는 harness fixture와 실제 API DTO를 맞추고, tool preview가 사용자 승인 전 side effect를 만들지 않는지 검증한다.
6. Docs는 데이터 수집/라이선스/안전 정책을 PROJECT_GUIDE 반영 후보로 정리하되, 기획 변경인지 구현 기준인지 구분한다.

## 8. 이번 주 지속 리스크

- 실제 end-to-end 시연 가능성은 아직 검증 필요다. 인증, OCR, preview, Agent, DB가 각각 전진했지만 한 화면 흐름으로 묶였다는 근거는 부족하다.
- 건강·영양·복약 문구 리스크가 커졌다. DUR, 만성질환, 복약 주의는 "현재 입력 정보 기준", "주의가 필요할 수 있음", "전문가 상담 권장" 수준으로 제한해야 한다.
- 개인정보/동의 리스크가 반복된다. raw image, raw OCR text, provider raw payload, 건강 데이터, 동의 철회 상태의 저장·전송·로그 정책을 명확히 해야 한다.
- 브랜치 구조 충돌 위험이 높다. 일부 브랜치는 대규모 폴더 재구성을 포함하므로 그대로 merge하기보다 표준 경로와 선별 반영 범위를 먼저 정해야 한다.
- 데이터 기준이 흔들릴 수 있다. KDRIs 2025, DUR, NIH DSLD, Shop API, 자체 수집 이미지의 출처, checksum, license, 사용 범위를 분리해야 한다.
- CI/검증 재현성이 불확실하다. 특정 브랜치 README의 test pass 기록은 해당 checkout 기준이므로 main 통합 후 같은 결과를 재검증해야 한다.

## 9. 근거 Daily

사용한 Daily 파일:

- [2026-05-13](../../daily/2026-05-13.md)
- [2026-05-14](../../daily/2026-05-14.md)
- [2026-05-15](../../daily/2026-05-15.md)
- [2026-05-16](../../daily/2026-05-16.md)
- [2026-05-17](../../daily/2026-05-17.md)

누락된 Daily:

- 2026-05-11 Daily 없음
- 2026-05-12 Daily 없음
