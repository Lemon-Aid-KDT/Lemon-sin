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
| `.secrets.baseline` | 있음, 33 files / 87 historical candidates |
| `.markdownlint.json` | 있음, low-noise bootstrap rules |
| installed Git hooks | Git root `.git/hooks/pre-commit`, `commit-msg`, `pre-push` 없음 |
| `pre-commit validate-config` | 통과 |
| `pre-commit run detect-secrets --all-files` | 통과 |
| `pre-commit run markdownlint --all-files` | 통과 |

## Gap Table

| Rule | Expected by team docs | Current enforcement | Gap | Risk |
| --- | --- | --- | --- | --- |
| Branch name | `<type>/<scope>-<subject>` with no worker-name branches | Current `.pre-commit-config.yaml` has no branch-name hook. Root CI has no team-policy workflow for current branch. | Not enforced locally or by current Lemon root CI. | Medium: worker-name or unscoped branches can enter review. |
| Commit type list | `feat fix docs style refactor perf test chore ci build revert data ops` | Updated: `conventional-pre-commit` args now include all documented types. | Closed for type allow-list. Scope and subject rules still need the team-policy validator. | Lower: documented valid commits no longer create `--no-verify` pressure. |
| Commit subject | imperative, no period, <= 50 chars | Current third-party hook validates Conventional Commits type shape only. | Subject length/period/scope allow-list are not fully enforced. | Medium: squash titles can drift from documented format. |
| PR template | `PR_GUIDELINES.md` says `.github/PULL_REQUEST_TEMPLATE.md` should include branch/pre-commit/CI/secret checks. | Git root has a generic P1 template. Lemon-Aid folder has no standalone `.github`. `team/docs/team-collaboration-rules` has a closer template. | Current template does not fully match team checklist and may not export cleanly to standalone team repo. | Medium: review evidence and secret/no-raw checks are easy to omit. |
| CI workflow path | CI should run backend/mobile/docs gates for Lemon Aid. | Git root Lemon workflows point to `03_lemon_healthcare/yeong-Lemon-Aid/...`. Current work is under `03_lemon_healthcare/Lemon-Aid/...`. | CI path is stale for the current default Lemon-Aid location. | High: PR can appear green while current path is untested. |
| Secret scan | `CI_CD_GATES.md` requires security gate and `.env`/secret protection. | Local pre-commit now resolves the baseline in both the current monorepo path and a standalone team-root export path. `.secrets.baseline` contains hashes for existing historical candidates, not raw values. `audit_detect_secrets_baseline.py` classifies all 87 findings without printing values. Root CI still has no Lemon-specific secret scan job beyond dependency audit/docs. | Local hook bootstrap and bounded baseline audit are closed; CI enforcement remains. | Medium: local contributors can run the hook, but CI still needs the non-bypassable version. |
| Markdown lint | `.pre-commit-config.yaml` calls `markdownlint` with a repo config. | `.markdownlint.json` now exists and the hook resolves it in both current monorepo and standalone team-root paths. | Bootstrap closed with low-noise rules; stricter project-wide markdown cleanup remains separate. | Low-Medium: docs lint is reproducible, but intentionally not strict yet. |
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
- The secret baseline records existing historical candidates by detector type,
  filename, line number, and hashed secret only. It does not store cleartext
  candidate values.
- The generated baseline is not a proof that all historical candidates are safe;
  it is a bootstrap that makes new secret regressions locally detectable while
  the historical audit is handled separately.
- The bounded baseline audit currently reports 0 high-severity manual-review
  items. It classifies 72 findings as low severity and 15 documentation
  placeholders as medium severity without printing candidate values.
- Current docs and hooks still rely on local discipline for `--no-verify`; CI
  should own the non-bypassable version of this policy.
- Stale workflow paths are a security issue because a changed protected path can
  bypass intended lint/test/secret gates.

## Recommended Follow-up PR Split

| Priority | PR | Scope |
| --- | --- | --- |
| P0 | `ci/team-policy-gates` | Add team-policy workflow and scripts from `team/docs/team-collaboration-rules`, then adapt paths to the current Lemon-Aid location. |
| P1 | `docs(team): PR template을 동기화` | Replace or supplement the current generic PR template with the team checklist from `PR_GUIDELINES.md`. |
| P1 | `ci(infra): Lemon workflow 경로를 보정` | Move `yeong-Lemon-Aid` workflow paths to the current default Lemon-Aid path or make path detection explicit. |
| P2 | `style(docs): markdownlint 규칙을 단계적으로 강화` | Tighten markdownlint beyond the bootstrap rules after legacy docs cleanup. |
| Done | `chore(team): secret scan baseline을 추가` | Added `.secrets.baseline`; `pre-commit run detect-secrets --all-files` passes. |
| Done | `test(team): secret baseline 후보를 감사` | Added bounded audit helper; 87 candidates classify to 72 low / 15 medium / 0 high. |
| Done | `chore(team): markdownlint 설정을 추가` | Added `.markdownlint.json`; `pre-commit run markdownlint --all-files` passes. |
| Done | `chore(team): pre-commit type 목록을 문서와 맞춤` | Allowed `build`, `revert`, `data`, `ops`; scope and subject constraints still belong in the team-policy validator. |

## Current Decision

Keep CI/team-policy changes separate from the OCR quality-gate slices. The
local hook bootstrap is now repaired, but the next safe governance PR still
needs to import the team-policy validator and PR template, then fix stale
workflow paths.
