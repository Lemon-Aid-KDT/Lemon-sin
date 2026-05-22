# 2026-05-23 GitHub Branch Protection Audit

## Scope

팀 협업 문서의 `feature -> develop` squash, `develop -> main` merge commit,
force-push 금지, self-merge 금지 정책이 실제 GitHub repository setting으로
보완되는지 확인했다.

대상 repository:

- `Lemon-Aid-KDT/Lemon-sin`
- Branches: `develop`, `main`

## Added Operator Gate

추가 파일:

- `backend/scripts/check_github_branch_protection.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_github_branch_protection.py`

기능:

- GitHub public branch metadata endpoint로 `develop`/`main`의 `protected` flag,
  nested `protection.enabled`, public required status check enforcement를 확인한다.
- Repository rulesets endpoint는 ruleset raw content를 출력하지 않고 total count와
  active branch ruleset count만 요약한다.
- 출력은 branch name, stable finding code, boolean/count detail로 제한한다.
- GitHub raw JSON, commit metadata, public account email, token, request header,
  secret 값은 출력하지 않는다.

공식 문서 근거:

- GitHub protected branches REST API:
  https://docs.github.com/en/rest/branches/branch-protection
- GitHub repository rulesets REST API:
  https://docs.github.com/rest/repos/rules

## Live Result

실행:

```bash
PYTHONPATH=backend/Nutrition-backend \
  /usr/bin/python3 backend/scripts/check_github_branch_protection.py \
    --repo Lemon-Aid-KDT/Lemon-sin \
    --branch develop \
    --branch main
```

결과:

```text
develop: branch_unprotected protected=false
develop: branch_protection_disabled protection.enabled=false
develop: required_status_checks_not_enforced enforcement=off
main: branch_unprotected protected=false
main: branch_protection_disabled protection.enabled=false
main: required_status_checks_not_enforced enforcement=off
github_branch_protection_failed repo=Lemon-Aid-KDT/Lemon-sin branches=2 rulesets=total=0 active_branch=0
```

`gh auth status`도 확인했지만 현재 local GitHub CLI token은 invalid라 admin-only
protection detail은 조회하지 못했다.

## Security Interpretation

- `develop`과 `main` 모두 public branch metadata 기준 보호되지 않는다.
- Public repository rulesets도 `[]`로 반환되어 active branch ruleset 보완이 없다.
- 이 상태에서는 local hook과 CI gate가 있어도 direct push, force push, branch
  deletion 같은 repository-level 우회 위험을 GitHub setting에서 막는다고 주장할
  수 없다.
- 특히 `--no-verify`는 local hook을 우회할 수 있으므로, GitHub branch protection
  또는 repository ruleset이 최종 방어선이어야 한다.

## Required Admin Action

Repository admin 권한으로 다음을 설정해야 한다.

- `develop`, `main` branch protection 또는 ruleset 활성화
- direct push 제한
- force push 비활성화
- branch deletion 비활성화
- PR review requirement 및 required status checks 설정
- `develop -> main` merge commit 정책과 `feature -> develop` squash 정책 확인

admin 설정 후 다음 명령으로 재검증한다.

```bash
PYTHONPATH=backend/Nutrition-backend \
  /usr/bin/python3 backend/scripts/check_github_branch_protection.py \
    --repo Lemon-Aid-KDT/Lemon-sin \
    --branch develop \
    --branch main
```

## Validation

```text
4 passed - test_check_github_branch_protection.py
black passed
ruff passed
ruff-format passed
```
