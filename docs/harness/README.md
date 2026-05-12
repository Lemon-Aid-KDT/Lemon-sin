# 문서 하네스

새 문서를 만들 때 Codex가 문서 성격을 판별하고 적절한 폴더에 생성하기 위한 규칙과 템플릿입니다.

> 상태: 문서 라우팅 전용 하네스입니다. 프로젝트 전체 Codex 실행 하네스는 repo 루트의
> `AGENTS.md`, `.codex/`, `.agents/skills/`를 기준으로 합니다.

## 구성

| 경로 | 목적 |
|------|------|
| [document-routing.md](./document-routing.md) | 문서 성격별 라우팅 규칙 |
| [templates/](./templates/) | 문서 유형별 기본 템플릿 |

## 사용 원칙

- 새 문서 작성 요청을 받으면 `document-routing.md`의 라우팅 표를 먼저 적용합니다.
- 맞는 성격이 없으면 새 폴더를 바로 만들지 않고, 이름과 이유를 제안한 뒤 승인 후 생성합니다.
- 문서가 생성되면 `docs/README.md`와 해당 폴더의 `README.md`를 함께 갱신합니다.
- 같은 규칙은 `.agents/skills/lemon-doc-create/SKILL.md`에도 실행형 워크플로로 유지합니다.
