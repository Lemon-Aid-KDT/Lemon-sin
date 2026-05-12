# Lemon Aid Codex 하네스

이 디렉터리는 Lemon Aid 프로젝트 단위 Codex 하네스입니다. 앱 런타임 Agent와는
의도적으로 분리합니다.

## 구성

| 경로 | 목적 |
|------|------|
| `config.toml` | 샌드박스, 승인, 웹 검색, subagent 제한의 프로젝트 기본값 |
| `rules/default.rules` | 로컬 명령 실행 승인 규칙 |
| `agents/` | 탐색과 리뷰를 위한 Codex 전용 custom subagent |

## 설계

- `AGENTS.md`는 항상 적용되는 프로젝트 규칙을 담습니다.
- `.codex/config.toml`은 이 프로젝트 계층이 신뢰된 뒤 Codex 동작을 제어합니다.
- `.codex/rules/default.rules`는 sandbox 밖에서 새 승인 없이 실행할 수 있는 명령을
  제어합니다.
- `.codex/agents/*.toml`은 좁은 책임의 Codex 보조 에이전트를 정의합니다. 제품
  런타임 Agent가 아니며 백엔드 아키텍처로 문서화하지 않습니다.
- `.agents/skills/*/SKILL.md`는 필요할 때 불러오는 Lemon Aid 반복 워크플로를
  담습니다.

## 운영 기본값

- sandbox는 `workspace-write`를 유지합니다.
- 네트워크, 의존성 설치, migration, 배포, commit, push 전에는 사용자 확인을
  거칩니다.
- 사용자가 별도 승인 경로로 명시하지 않는 한 강제 Git 작업과 광범위한 삭제 명령은
  금지합니다.
- subagent 중첩은 얕게 유지합니다. Lemon Aid 작업에는 재귀적 확장보다 병렬 리뷰가
  더 적합합니다.
