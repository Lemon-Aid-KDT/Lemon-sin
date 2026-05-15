# Implementation 문서 인덱스

이 폴더는 `PROJECT_GUIDE.md`를 바로 수정하기 전에, 실제 원격 브랜치와 팀 작업
상태를 기준으로 구현 순서와 통합 기준을 맞추기 위한 작업 문서 모음이다.

`PROJECT_GUIDE.md`는 제품 기획과 최종 방향의 단일 기준으로 유지한다. 이 폴더의
문서는 브랜치별 산출물, 구현 우선순위, Agent 연결점, 문서 파급 변경을 먼저
정리한 뒤 어떤 내용을 `PROJECT_GUIDE.md`에 반영할지 결정하는 중간 기준이다.

## 문서 목록

| 문서 | 목적 |
|------|------|
| [00-current-branch-map.md](./00-current-branch-map.md) | 원격 브랜치별 현재 산출물, 통합 가치, 위험도 정리 |
| [01-role-and-ownership-sync.md](./01-role-and-ownership-sync.md) | guide와 실제 브랜치 기준 업무 분담 차이 정렬 |
| [02-agent-integration-prerequisites.md](./02-agent-integration-prerequisites.md) | Agent 기능 구현 전 필요한 백엔드, 데이터, UI, 안전 조건 |
| [03-branch-absorption-plan.md](./03-branch-absorption-plan.md) | 브랜치 산출물을 어떤 순서와 방식으로 흡수할지 결정 |
| [04-step-by-step-implementation-roadmap.md](./04-step-by-step-implementation-roadmap.md) | 문서 정리 이후 구현을 작은 작업 카드로 분해 |

## 기준 결정

- 구현 기준은 `분석 알고리즘 + 3 Agent`다.
- 분석/OCR/영양소 산출은 Agent가 아니라 `algorithms/`, `ocr/`, `supplements/`,
  식단 인식 파이프라인 책임이다.
- Agent는 `personalization`, `evaluation`, `chat` 3개만 둔다.
- Agent 구현은 실제 LLM 호출보다 mock-first 계약, preview/approval, 안전 필터,
  `agent_runs`, `agent_memory`를 먼저 고정한다.
- 원격 브랜치의 코드는 바로 merge하지 않고, 문서 기준으로 흡수 단위를 판정한 뒤
  후속 구현 단계에서 별도 PR로 다룬다.

## 스냅샷 출처

- 기준일: 2026-05-14
- 원격 저장소: `https://github.com/Lemon-Aid-KDT/Lemon-sin`
- 브랜치 목록 확인: `git ls-remote --heads https://github.com/Lemon-Aid-KDT/Lemon-sin.git`
- 브랜치 차이 확인: GitHub compare API 기준 `main...<branch>`

