# Document Routing Harness

이 문서는 `changmin-plan/docs/` 안에서 새 문서를 어디에 만들지 결정하는 기준입니다.
문서 분류 기준은 담당자나 프로젝트 단계가 아니라 **문서의 목적과 쓰임새**입니다.

## 기본 라우팅

| 문서 성격 | 생성 위치 | 템플릿 | 판단 기준 |
|----------|-----------|--------|-----------|
| 제품·개발 기준 가이드 | `docs/guide/` | `templates/guide.md` | 구현자가 계속 참조할 기준 문서 |
| 도메인 학습 자료 | `docs/domain/` | `templates/domain.md` | 만성질환, 영양, 식단 등 팀 내부 학습 문서 |
| 근거·리서치 정리 | `docs/research/` | `templates/research.md` | 논문, API, 외부 자료, 기술 판단 근거 |
| 검토 보고서 | `docs/reports/` | `templates/report.md` | 특정 시점의 리뷰, 결정, 질문 정리 |
| 실행 부록 | `docs/appendices/` | `templates/appendix.md` | 본문 가이드에서 분리한 실행 보조 자료 |
| 발표·공유 산출물 | `docs/presentations/<topic>/` | `templates/presentation.md` | 멘토 미팅, 발표, PDF/HTML 산출물 |

## 생성 절차

1. 요청에서 문서의 목적, 독자, 사용 시점을 파악한다.
2. 위 라우팅 표에서 가장 가까운 성격을 고른다.
3. 파일명은 소문자 kebab-case로 만든다.
4. 해당 성격의 템플릿을 사용해 문서를 만든다.
5. `docs/README.md`와 해당 폴더의 `README.md`에 링크를 추가한다.
6. 이동 또는 생성으로 기존 링크가 깨질 수 있으면 `rg`로 참조를 찾아 갱신한다.

## 애매한 경우

- 리서치와 보고서가 겹치면, 외부 근거 축적이 목적이면 `research/`, 팀 의사결정 기록이 목적이면 `reports/`로 둔다.
- 도메인과 가이드가 겹치면, 팀 학습이 목적이면 `domain/`, 구현 기준이면 `guide/`로 둔다.
- 발표와 보고서가 겹치면, 공유용 산출물이 중심이면 `presentations/`, 검토 기록이 중심이면 `reports/`로 둔다.

## 맞는 성격이 없을 때

기존 성격에 억지로 넣지 않는다. Codex는 다음 형식으로 사용자에게 먼저 제안한다.

```text
새 문서 성격이 기존 폴더와 맞지 않습니다.
제안 폴더: docs/<new-category>/
이유: <왜 기존 카테고리보다 새 카테고리가 맞는지>
생성 예정 파일: docs/<new-category>/<document-name>.md
```

사용자가 승인하면 `docs/<new-category>/README.md`를 만들고 `docs/README.md`에도 새 카테고리를 추가한다.
