# 2026-05-22 Team Governance Enforcement Gap Report

## Scope

이 문서는 `2026-05-22-folder-implementation-plan.md`의 PR-3
`협업 규칙 enforcement 동기화` 항목에 대한 docs-only gap report다.

비교 대상:

- `docs/team-collaboration/BRANCH_STRATEGY.md`
- `docs/team-collaboration/COMMIT_CONVENTION.md`
- `docs/team-collaboration/PR_GUIDELINES.md`
- `docs/team-collaboration/CI_CD_GATES.md`
- 현재 checkout의 `.pre-commit-config.yaml`
- 현재 Git root의 `.github/PULL_REQUEST_TEMPLATE.md`
- 현재 Git root의 `.github/workflows/17-lemon-*.yml`
- `team/develop`
- `team/docs/team-collaboration-rules`

공식 문서 확인:

- pre-commit hook/stage 개념: https://pre-commit.com/
- GitHub pull request template 위치: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository
- GitHub protected branches/status check/force push 설정: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches

## Evidence

| Check | Result |
| --- | --- |
| `git remote -v` | `team` remote는 `Lemon-Aid-KDT/Lemon-sin.git` |
| `git ls-remote team refs/heads/develop refs/heads/main` | `develop`과 `main` 모두 `2f941020...` |
| `git ls-remote team refs/heads/feat/ocr-p1-5-followup` | `b5a9dec9...` |
| Lemon-Aid 내부 `.github` | 없음 |
| Git root `.github/PULL_REQUEST_TEMPLATE.md` | 있음, monorepo P1 template |
| Git root Lemon workflows | 있음, `yeong-Lemon-Aid` 경로 기준 |
| `.secrets.baseline` | 없음 |
| `.markdownlint.json` | 없음 |
| installed Git hooks | Git root `.git/hooks/pre-commit`, `commit-msg`, `pre-push` 없음 |
| `pre-commit validate-config` | 통과 |
| `pre-commit run detect-secrets --all-files` | 실패: `.secrets.baseline` missing |
| `pre-commit run markdownlint --all-files` | 실패: `.markdownlint.json` missing + broad markdown lint findings |

## Gap Table

| Rule | Expected by team docs | Current enforcement | Gap | Risk |
| --- | --- | --- | --- | --- |
| Branch name | `<type>/<scope>-<subject>` with no worker-name branches | Current `.pre-commit-config.yaml` has no branch-name hook. Root CI has no team-policy workflow for current branch. | Not enforced locally or by current Lemon root CI. | Medium: worker-name or unscoped branches can enter review. |
| Commit type list | `feat fix docs style refactor perf test chore ci build revert data ops` | `conventional-pre-commit` args only include `feat fix docs style refactor perf test chore ci`. | `build`, `revert`, `data`, `ops` are documented but rejected by local commit-msg hook. | High: documented valid commits fail locally, causing `--no-verify` pressure. |
| Commit subject | imperative, no period, <= 50 chars | Current third-party hook validates Conventional Commits type shape only. | Subject length/period/scope allow-list are not fully enforced. | Medium: squash titles can drift from documented format. |
| PR template | `PR_GUIDELINES.md` says `.github/PULL_REQUEST_TEMPLATE.md` should include branch/pre-commit/CI/secret checks. | Git root has a generic P1 template. Lemon-Aid folder has no standalone `.github`. `team/docs/team-collaboration-rules` has a closer template. | Current template does not fully match team checklist and may not export cleanly to standalone team repo. | Medium: review evidence and secret/no-raw checks are easy to omit. |
| CI workflow path | CI should run backend/mobile/docs gates for Lemon Aid. | Git root Lemon workflows point to `03_lemon_healthcare/yeong-Lemon-Aid/...`. Current work is under `03_lemon_healthcare/Lemon-Aid/...`. | CI path is stale for the current default Lemon-Aid location. | High: PR can appear green while current path is untested. |
| Secret scan | `CI_CD_GATES.md` requires security gate and `.env`/secret protection. | Local pre-commit has `detect-secrets --baseline .secrets.baseline`, but baseline file is missing. Root CI has no Lemon-specific secret scan job beyond dependency audit/docs. | Secret hook is configured but currently not runnable. | High: contributors can miss local secret scan, and CI may not compensate. |
| Markdown lint | `.pre-commit-config.yaml` calls `markdownlint --config .markdownlint.json`. | `.markdownlint.json` is missing. | Configured hook fails before meaningful team docs linting. | Medium: all-files pre-commit is not reproducible. |
| Large file limit | `CI_CD_GATES.md` shows 2MB example. | Current `.pre-commit-config.yaml` uses `--maxkb=5000`; team docs branch uses 2000. | Limit differs between docs/current/team docs branch. | Low-Medium: OCR artifacts or screenshots may exceed intended limit. |
| `--no-verify` ban | Docs ban usage. | Git cannot technically prevent user-supplied `--no-verify` locally. No CI team-policy equivalent exists in this branch. | Needs CI-side policy and review checklist, not only local hooks. | Medium: local-only gate can be bypassed. |
| Force push ban | Docs allow only safe force-with-lease and branch protection denies force pushes on protected branches. | Branch protection settings are not inspectable from this checkout. Root CI does not validate force-push settings. | External GitHub setting remains unverified. | Medium: requires admin/API verification. |
| Team integration base | PR target should be `develop`; feature to `develop` squash. | `team/develop` is skeleton and lacks current OCR backend tree; `team/feat/ocr-p1-5-followup` is code-bearing but tracks generated OCR eval artifacts. | Team PR export remains blocked until a clean code-bearing base exists or `develop` is synced. | High: wrong base can leak generated artifacts or create unreviewable PRs. |

## Existing Candidate From Team Branch

`team/docs/team-collaboration-rules` already contains useful enforcement pieces:

- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/team-policy.yml`
- `scripts/git-hooks/guard_protected_branch.py`
- `scripts/git-hooks/validate_commit_msg.py`
- `scripts/git-hooks/validate_team_policy.py`

However, it is based on the skeleton team tree rather than the current
code-bearing Lemon Aid application tree. Importing it into this work should be
done as a separate small PR after choosing the correct base.

## Security / Leakage Review

- No secret values were read from `.env`.
- This report only records filenames, branch names, command outcomes, and
  bounded error classes.
- The missing `.secrets.baseline` makes the configured secret hook fail before
  scanning actual files.
- Current docs and hooks still rely on local discipline for `--no-verify`; CI
  should own the non-bypassable version of this policy.
- Stale workflow paths are a security issue because a changed protected path can
  bypass intended lint/test/secret gates.

## Recommended Follow-up PR Split

| Priority | PR | Scope |
| --- | --- | --- |
| P0 | `ci/team-policy-gates` | Add team-policy workflow and scripts from `team/docs/team-collaboration-rules`, then adapt paths to the current Lemon-Aid location. |
| P0 | `chore(team): secret scan baseline을 추가` | Add or regenerate `.secrets.baseline` after a full review; do not include real secret values. |
| P1 | `docs(team): PR template을 동기화` | Replace or supplement the current generic PR template with the team checklist from `PR_GUIDELINES.md`. |
| P1 | `ci(infra): Lemon workflow 경로를 보정` | Move `yeong-Lemon-Aid` workflow paths to the current default Lemon-Aid path or make path detection explicit. |
| P1 | `chore(team): markdownlint 설정을 추가` | Add `.markdownlint.json` or remove the configured hook until a project-wide rule set exists. |
| P2 | `chore(team): pre-commit type 목록을 문서와 맞춤` | Allow `build`, `revert`, `data`, `ops`; enforce scope and subject constraints with the local script. |

## Current Decision

Do not change CI or hooks in the same PR as OCR quality gates. The next safe
step is a dedicated governance PR that first imports the team-policy validator
and PR template, then separately fixes stale workflow paths and secret scanning.
