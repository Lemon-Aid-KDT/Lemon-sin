# 2026-06-02 작업 문서 인덱스

> 작성 기준: 2026-06-02 섹션 작업
> 범위: 모바일 분석 결과 그룹화, 서버 응답 점검, 네트워크 오류 처리 보완, OCR/YOLO 섹션 ROI 보완, 검증 및 GitHub 브랜치 푸시

---

## 문서 목록

- `2026-06-02-analysis-result-grouping-summary.md`
  - 여러 장의 영양제 이미지 분석 결과를 제품 단위로 묶는 모바일 결과 화면 변경 요약
  - 전면 라벨과 성분표 라벨이 분리 분석될 때 하나의 영양제로 보여주는 기준 정리

- `2026-06-02-server-runtime-response-check.md`
  - backend runtime이 실제로 살아 있는지 확인한 health/readiness/API 점검 기록
  - 모바일 base URL과 `/api/v1` prefix 혼동 가능성 정리

- `2026-06-02-server-network-hardening-summary.md`
  - Android emulator Host header 허용 기본값 보완
  - Flutter API client의 socket/client network failure 사용자 메시지 정규화
  - backend/mobile 단위 테스트 추가 사항 정리

- `2026-06-02-verification-and-git-publish.md`
  - 이번 커밋에 포함한 파일, 제외한 파일, 검증 명령, 커밋/푸시 기준 정리

- `2026-06-02-ocr-yolo-precaution-analysis.md`
  - 주의사항/알레르기 문구가 OCR 결과에 안정적으로 반영되지 않는 원인 조사 기록
  - YOLO ROI taxonomy, 다중 ROI OCR, OCR page merge, serving-size 오탐 후보를 분리해서 정리

- `2026-06-02-ocr-yolo-next-implementation-plan.md`
  - 코드 수정 전 설계 검토 결과와 다음 구현 순서
  - 테스트/검증 명령, 제외해야 하는 데이터, 공식 문서 기준 정리

- `2026-06-02-ocr-yolo-section-roi-implementation-summary.md`
  - 영양제 라벨 섹션 ROI taxonomy 확장, OCR page merge 보존, serving-size 오탐 제거 구현 요약
  - Ultralytics 공식 문서 기준과 custom section model 필요 조건 정리

- `2026-06-02-ocr-yolo-section-roi-verification.md`
  - backend unit/ruff/regression/parser 직접 재현 검증 결과
  - 실제 Ultralytics runtime smoke가 막힌 이유와 다음 작업 정리

- `2026-06-02-yolo26-gemma-supplement-vision-design.md`
  - YOLO26 custom 영양제 섹션 detector와 Ollama/Gemma 검증/설명 파이프라인 설계
  - OCR layout `precautions` fallback 구현, 자체 설계 점검, 남은 blocker 정리

- `2026-06-02-ollama-vision-verification-summary.md`
  - local Ollama/Gemma vision model이 OCR 텍스트를 이미지와 직접 대조하는 structured verification 계약 구현 요약
  - `match | partial | mismatch | uncertain`, 필수 섹션 누락, backend warning 연결 및 검증 결과 정리

- `2026-06-02-supplement-analysis-profile-context-summary.md`
  - 영양제 OCR 분석 미리보기 설명에 사용자 최신 건강 프로필 snapshot을 opt-in으로 연결한 작업 요약
  - `sensitive_health_analysis` 동의 gate, sanitized profile bucket, audit flag, 회귀 테스트 결과 정리

- `2026-06-02-supplement-analysis-medical-context-summary.md`
  - 영양제 OCR 분석 미리보기 설명에 사용자 질환/복약 DB 요약 bucket을 opt-in으로 연결한 작업 요약
  - 원문 질환명/약명/용량을 LLM에 전달하지 않는 safe medical context, consent gate, audit flag 정리

---

## 현재 핵심 상태

- `AnalysisResultScreen`은 다중 이미지 분석 결과를 단순 이미지 탭이 아니라 영양제 단위 탭으로 묶어 표시한다.
- 제품명/제조사만 있는 전면 이미지와 성분표만 있는 이미지가 같은 영양제로 이어지는 경우, 성분 후보와 누락 섹션을 병합해 보여준다.
- Android/iOS에서 이전 분석 결과를 새 분석 결과로 오해하지 않도록, 탭 개수와 표시 라벨이 제품 단위로 정리되는 테스트를 추가했다.
- backend는 `/health`, `/ready`, `/api/v1/dashboard/summary` 기준으로 응답을 다시 확인했다.
- Android emulator 기본 Host인 `10.0.2.2`를 backend 개발 기본 allowlist에 포함했다.
- Flutter API client는 `SocketException`과 `http.ClientException`을 `network_unavailable` 오류로 정규화해 사용자에게 backend 실행 상태/API 주소 확인 메시지를 보여준다.
- 이번 Git 작업은 팀 repo `Lemon-Aid-KDT/Lemon-sin.git`의 현재 브랜치 `docs/docs-2026-05-31-backend-ocr-security`에 커밋/푸시한다.
- OCR/YOLO 추가 조사에서는 코드 변경 전 원인 분석을 우선 진행했으며, 주의사항 누락과 `1회 제공량(26g)` 성분 후보 오탐은 서로 다른 문제로 분리했다.
- backend OCR/YOLO 구현은 섹션 ROI label(`supplement_facts`, `precautions`, `intake_method`, `ingredients`)을 인식하고 OCR merge에서 layout page를 보존하도록 갱신했다.
- `1회 제공량(26g)`, `Serving Size`, `Amount Per Serving` 계열은 성분 후보에서 제외하고, 실제 성분명과 함량이 있는 문장은 유지하도록 테스트를 추가했다.
- 실제 이미지 기반 YOLO runtime smoke는 custom supplement section `.pt` 모델과 backend vision runtime 설치가 필요해 다음 단계로 남겼다.
- OCR layout에 `precautions` 섹션이 보이면 LLM parser가 놓쳐도 structured `precautions` 배열로 승격하도록 보완했다.
- Gemma/Ollama 기반 멀티모달 검증은 기존 OCR 유사도 비교에서 OCR 텍스트와 이미지/ROI를 직접 대조하는 structured verification 계약으로 보완했다.
- 분석 미리보기 설명은 `include_profile_context=true`일 때 민감 건강 동의 확인 후 최신 body profile snapshot의 sanitized bucket을 설명 context에 포함한다.
- 분석 미리보기 설명은 `include_medical_context=true`일 때 민감 건강 동의 확인 후 사용자 의료정보 DB의 질환/복약 요약 bucket을 설명 context에 포함한다.
- 개인 맞춤 설명의 다음 단계는 모바일 요청 연결, comprehensive nutrition engine 결합, 실제 local Ollama/Gemma live smoke다.
