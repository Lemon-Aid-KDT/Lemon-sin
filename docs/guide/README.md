# Lemon Aid Guide Index

`PROJECT_GUIDE.md`를 보존한 상태에서, 팀원과 Codex가 필요한 맥락만 빠르게 읽을 수 있도록 나눈 문서 모음입니다.

원본 대형 기획서는 [PROJECT_GUIDE.md](../../PROJECT_GUIDE.md)에 그대로 남겨둡니다. `guide.html` 자동 동기화 구조도 기존대로 유지합니다.

## 처음 읽는 순서

1. [01 Product Overview](./01-product-overview.md)
2. [Domain Onboarding](../domain/domain-onboarding.md)
3. [02 Product Spec](./02-product-spec.md)
4. [09 Team Workflow](./09-team-workflow.md)
5. 본인 담당 영역 문서
6. [08 Compliance & Safety](./08-compliance-safety.md)

## 담당 영역별 문서

| 담당 | 먼저 읽을 문서 |
|------|----------------|
| 프론트 리드 | [03 Frontend](./03-frontend.md), [02 Product Spec](./02-product-spec.md) |
| UI/UX | [02 Product Spec](./02-product-spec.md), [03 Frontend](./03-frontend.md), [08 Compliance & Safety](./08-compliance-safety.md) |
| AI 엔지니어 | [06 AI Agents](./06-ai-agents.md), [07 Algorithms](./07-algorithms.md), [08 Compliance & Safety](./08-compliance-safety.md) |
| 백엔드 | [04 Backend API](./04-backend-api.md), [05 Data Model](./05-data-model.md), [07 Algorithms](./07-algorithms.md) |
| 데이터·도메인 | [Domain Onboarding](../domain/domain-onboarding.md), [07 Algorithms](./07-algorithms.md), [08 Compliance & Safety](./08-compliance-safety.md) |

## 문서 목록

| 파일 | 내용 |
|------|------|
| [01-product-overview.md](./01-product-overview.md) | 프로젝트 요약, 개요, 배경, 페르소나, 차별화, 일정 |
| [02-product-spec.md](./02-product-spec.md) | 핵심 기능, 주요 화면, MVP 흐름, 예외·오프라인·동기화 정책 |
| [03-frontend.md](./03-frontend.md) | Flutter 스택, UX 원칙, 화면 동작 흐름 |
| [04-backend-api.md](./04-backend-api.md) | FastAPI 스택, 모듈 책임, API 엔드포인트, 외부 API |
| [05-data-model.md](./05-data-model.md) | DB 구성, 핵심 테이블, 시계열, 보안·권한 |
| [06-ai-agents.md](./06-ai-agents.md) | Agent 구조, 데이터 포맷, Tool Use, AI 스택, 호출 흐름 |
| [07-algorithms.md](./07-algorithms.md) | BMI, 활동점수, 체중 예측, OCR 매칭, 결핍 진단, 검증 |
| [08-compliance-safety.md](./08-compliance-safety.md) | 의료법·약사법 표현, 면책 문구, 개인정보, DTx, 출처 명시 |
| [09-team-workflow.md](./09-team-workflow.md) | 작업 파이프라인, 툴, 파일 구조, 팀 분담, GitHub 규칙, 동기화 |
| [10-demo-release.md](./10-demo-release.md) | 리스크, 시연 시나리오, 배포, 참고 자료, 최종 메시지 |

관련 보조 문서는 [docs/ 인덱스](../README.md)에서 목적별 폴더를 확인합니다.

## 작업 규칙

- `PROJECT_GUIDE.md`와 `guide.html`은 이번 분리 문서의 원본 보존본으로 둡니다.
- 새 기획 검토는 먼저 이 분리 문서에서 하고, 나중에 필요할 때 원본 반영 여부를 결정합니다.
- 건강 로직, 복약/영양제, 개인정보, 면책 문구를 바꾸는 작업은 [08 Compliance & Safety](./08-compliance-safety.md)를 함께 확인합니다.
