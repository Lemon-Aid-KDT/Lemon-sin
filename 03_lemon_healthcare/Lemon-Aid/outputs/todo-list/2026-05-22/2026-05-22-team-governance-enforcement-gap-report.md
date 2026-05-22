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
- Git pre-push hook stdin/exit behavior: https://git-scm.com/docs/githooks#_pre_push
- GitHub pull request template 위치: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository
- GitHub protected branches/status check/force push 설정: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- GitHub protected branches REST API: https://docs.github.com/en/rest/branches/branch-protection
- GitHub repository rulesets REST API: https://docs.github.com/rest/repos/rules

## Evidence

| Check | Result |
| --- | --- |
| `git remote -v` | `team` remote는 `Lemon-Aid-KDT/Lemon-sin.git` |
| `git ls-remote team refs/heads/develop refs/heads/main` | `develop`과 `main` 모두 `2f941020...` |
| `git ls-remote team refs/heads/feat/ocr-p1-5-followup` | `b5a9dec9...` |
| Lemon-Aid 내부 `.github` | 있음, standalone export용 PR template/workflow |
| Git root `.github/PULL_REQUEST_TEMPLATE.md` | 있음, monorepo P1 template |
| Git root Lemon workflows | 있음, 현재 `Lemon-Aid` 경로 기준으로 보정 |
| `.secrets.baseline` | 있음, 18 files / 72 historical candidates |
| `.markdownlint.json` | 있음, low-noise bootstrap rules |
| installed Git hooks | Git root `.git/hooks/pre-commit`, `commit-msg`, `pre-push` 없음 |
| GitHub public branch protection | `develop`/`main` 모두 `protected=false`, `protection.enabled=false`, required status checks off |
| GitHub public repository rulesets | `total=0`, `active_branch=0` |
| `pre-commit validate-config` | 통과 |
| `pre-commit run detect-secrets --all-files` | 통과 |
| `pre-commit run markdownlint --all-files` | 통과 |
| `backend/scripts/check_lemon_ci_paths.py --project-root .` | 통과, Git root Lemon CI/policy path 6 files 검사 |

## Gap Table

| Rule | Expected by team docs | Current enforcement | Gap | Risk |
| --- | --- | --- | --- | --- |
| Branch name | `<type>/<scope>-<subject>` with no worker-name branches | Lemon-Aid standalone export assets include `.github/workflows/team-policy.yml` and `scripts/git-hooks/validate_team_policy.py`. Git root backend CI now invokes the validator for PR events. | Closed for PRs that run the current root backend CI. | Lower: direct push protection still depends on repository settings. |
| Commit type list | `feat fix docs style refactor perf test chore ci build revert data ops` | Updated: `conventional-pre-commit` args now include all documented types. | Closed for type allow-list. Scope and subject rules still need the team-policy validator. | Lower: documented valid commits no longer create `--no-verify` pressure. |
| Commit subject | imperative, no period, <= 50 chars | Lemon-Aid standalone export assets include `scripts/git-hooks/validate_commit_msg.py`, and Git root backend CI now validates PR titles through `validate_team_policy.py`. Current third-party local hook remains broader. | Closed for PR title gate; local hook parity is optional follow-up. | Low: local commits still rely on existing hook plus review, but PR title is CI-gated. |
| PR template | `PR_GUIDELINES.md` says `.github/PULL_REQUEST_TEMPLATE.md` should include branch/pre-commit/CI/secret checks. | Lemon-Aid now has `.github/PULL_REQUEST_TEMPLATE.md` with branch, title, pre-commit, secret, raw OCR, provider payload, and generated artifact checks. | Closed for team-root export; Git root template remains generic for nested monorepo PRs. | Low-Medium: export path is covered, root monorepo still needs template sync if used directly. |
| CI workflow path | CI should run backend/mobile/docs gates for Lemon Aid. | Git root Lemon workflows, dependabot, PR template, and CODEOWNERS now point to `03_lemon_healthcare/Lemon-Aid/...`. `check_lemon_ci_paths.py` also scans CODEOWNERS. | Closed for current monorepo root. | Lower: path drift is now covered by an explicit bounded audit. |
| Secret scan | `CI_CD_GATES.md` requires security gate and `.env`/secret protection. | Local pre-commit resolves the baseline in both the current monorepo path and a standalone team-root export path. Git root backend CI now runs `detect-secrets-hook`, baseline audit, OCR artifact tracking audit, CI path audit, and team-policy asset audit. | Closed for current root backend CI. | Lower: keep baseline audit in future doc/code changes. |
| Markdown lint | `.pre-commit-config.yaml` calls `markdownlint` with a repo config. | `.markdownlint.json` now exists and the hook resolves it in both current monorepo and standalone team-root paths. | Bootstrap closed with low-noise rules; stricter project-wide markdown cleanup remains separate. | Low-Medium: docs lint is reproducible, but intentionally not strict yet. |
| Large file limit | `CI_CD_GATES.md` shows 2MB example. | Current `.pre-commit-config.yaml` uses `--maxkb=5000`; team docs branch uses 2000. | Limit differs between docs/current/team docs branch. | Low-Medium: OCR artifacts or screenshots may exceed intended limit. |
| `--no-verify` ban | Docs ban usage. | Git cannot technically prevent user-supplied `--no-verify` locally. Root backend CI now reruns the important secret, OCR artifact, path, and PR policy gates without relying on local hooks. | Closed for covered CI gates; literal local `--no-verify` usage remains a review/process rule. | Low-Medium: direct pushes still require branch protection. |
| Force push ban | Docs allow only safe force-with-lease and branch protection denies force pushes on protected branches. | Public GitHub branch metadata currently reports `develop` and `main` as unprotected, with no active branch rulesets. Root CI does not validate force-push settings. | Open: repository admin must enable branch protection or rulesets. | High: repository settings do not currently provide the final non-bypassable layer. |
| Team integration base | PR target should be `develop`; feature to `develop` squash. | `team/develop` is skeleton and lacks current OCR backend tree; `team/feat/ocr-p1-5-followup` is code-bearing but tracks generated OCR eval artifacts. | Team PR export remains blocked until a clean code-bearing base exists or `develop` is synced. | High: wrong base can leak generated artifacts or create unreviewable PRs. |

## Existing Candidate From Team Branch

`team/docs/team-collaboration-rules` already contains useful enforcement pieces:

- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/team-policy.yml`
- `scripts/git-hooks/guard_protected_branch.py`
- `scripts/git-hooks/validate_commit_msg.py`
- `scripts/git-hooks/validate_team_policy.py`

However, it is based on the skeleton team tree rather than the current
code-bearing Lemon Aid application tree. The PR template, team-policy workflow,
and branch/title validators have now been adapted inside the current Lemon-Aid
folder for standalone team-root export. `guard_protected_branch.py` has also
been adapted as a local `pre-push` guard. It remains a bypassable local helper,
so CI-side gates and GitHub branch protection remain the non-bypassable layers.

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
  items. It classifies all 72 remaining findings as low severity after
  documentation placeholders were rewritten to explicit non-credential examples.
- Current docs and hooks still ban `--no-verify`; root backend CI now owns the
  non-bypassable version for secret scan, baseline audit, OCR artifact
  tracking, CI path audit, and PR branch/title policy.
- The local protected-branch guard blocks direct `main`/`develop` push lines in
  Git `pre-push` stdin and prints only bounded branch/reason messages. It does
  not print remote URLs, local absolute paths, request headers, provider
  payloads, raw OCR text, or secret values.
- `backend/scripts/check_github_branch_protection.py` now confirms via public
  GitHub branch metadata that `develop` and `main` are not protected, required
  status checks are off, and public repository rulesets are absent. The command
  prints bounded findings only and does not print raw API JSON or account
  metadata.
- Stale workflow and CODEOWNERS paths are security issues because a changed
  protected path can bypass intended lint/test/secret gates and reviewer
  ownership.
- `check_lemon_ci_paths.py` now detects stale root `.github` CI/policy paths
  without printing workflow contents, local absolute roots, or secret values.

## Recommended Follow-up PR Split

| Priority | PR | Scope |
| --- | --- | --- |
| P2 | `style(docs): markdownlint 규칙을 단계적으로 강화` | Tighten markdownlint beyond the bootstrap rules after legacy docs cleanup. |
| P1 | `ops(team): GitHub 보호 브랜치를 활성화` | Repository admin must enable branch protection or rulesets for `develop` and `main`, then rerun `check_github_branch_protection.py`. |
| Done | `chore(team): 보호 브랜치 push guard를 추가` | Added `guard_protected_branch.py`, pre-commit `pre-push` wiring, asset checks, and LOCAL_SETUP guidance. |
| Done | `ci(infra): CI 보안 gate를 추가` | Root backend CI now reruns team policy, secret baseline, OCR artifact, and CI path gates. |
| Done | `ci(infra): Lemon workflow 경로를 보정` | Root workflows, dependabot, PR template, and CODEOWNERS now point to the current default Lemon-Aid path, and `check_lemon_ci_paths.py --project-root .` passes. |
| Done | `test(infra): Lemon CI 경로 감사를 추가` | Added bounded audit for stale root workflow/dependabot/PR-template paths. |
| Done | `ci(team): team policy gate를 추가` | Added standalone export PR template, team-policy workflow, branch/title validators, and asset checker. |
| Done | `chore(team): secret scan baseline을 추가` | Added `.secrets.baseline`; `pre-commit run detect-secrets --all-files` passes. |
| Done | `test(team): secret baseline 후보를 감사` | Added bounded audit helper; current baseline classifies to 72 low / 0 medium / 0 high. |
| Done | `docs(team): credential 예시 placeholder를 보정` | Rewrote 15 documentation placeholders that looked like credentials and regenerated the baseline from tracked Lemon-Aid files. |
| Done | `chore(team): markdownlint 설정을 추가` | Added `.markdownlint.json`; `pre-commit run markdownlint --all-files` passes. |
| Done | `chore(team): pre-commit type 목록을 문서와 맞춤` | Allowed `build`, `revert`, `data`, `ops`; scope and subject constraints still belong in the team-policy validator. |

## Current Decision

Keep CI/team-policy changes separate from the OCR quality-gate slices. The
local hook bootstrap, standalone team-policy assets, and current monorepo root
`.github` paths, local protected-branch hook parity, and CI-owned security gates
are repaired. Public GitHub metadata now shows that repository-admin branch
protection or active branch rulesets are still missing for `develop` and `main`;
that is the remaining non-bypassable governance control before team merge flow
can be considered protected.
