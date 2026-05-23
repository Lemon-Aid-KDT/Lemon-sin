# 2026-05-23 PR Export Base Gate Result

## Scope

PR split/export 과정에서 잘못된 base를 선택해 skeleton branch에 patch를 적용하거나
generated OCR artifact가 포함된 branch 위에 PR을 여는 일을 막는 gate를 독립
branch로 분리했다.

## Branches

- Base branch: `chore/ocr-clean-export-base`
- Export branch: `test/ocr-pr-export-base-gate`
- Preserved remote: `origin/test/ocr-pr-export-base-gate`
- Base commit: `67b9bc46 chore(ocr): export base artifact 추적을 제거`
- Patch commit: `ea7a9006 test(ocr): PR export base gate를 추가`

## Changed Files

- `backend/scripts/check_pr_export_base.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_pr_export_base.py`

Change size:

```text
2 files changed, 516 insertions(+)
```

## Behavior Covered

- Required OCR backend paths must exist in the base ref.
- Base ref must not track `.env`.
- Base ref must not track `outputs/generated/ocr-eval/`.
- Both team-root and monorepo-prefixed path layouts are checked.
- CLI diagnostics are bounded to finding code, ref, and project-relative path.

## Live Ref Smoke

```text
chore/ocr-clean-export-base: pr_export_base_ok
team/develop: missing backend/Nutrition-backend OCR source/test paths
team/feat/ocr-p1-5-followup: forbidden tracked outputs/generated/ocr-eval paths
```

## Validation

```text
6 passed - test_check_pr_export_base.py
black --check passed
ruff check passed
secret pattern scan on changed source files: no matches
git diff --check passed
git diff --cached --check passed
```

## Security / Leakage Review

- The branch adds a Git tree/ref inspection script and tests only.
- It does not add generated OCR artifacts, raw OCR text, provider payloads,
  request headers, image bytes, `.env`, or secrets.
- The script checks for forbidden tracked paths without reading `.env` values or
  generated artifact contents.
- Output is intentionally bounded and does not print raw OCR content or secret
  candidate values.

## Next Decision

This branch is a safe companion to `test/ocr-artifact-privacy-gate`. Together
they form the minimum export-readiness controls before larger OCR tooling slices.

Team decision is still needed for the actual PR base:

1. approve `chore/ocr-clean-export-base` as the code-bearing clean base, or
2. sync the real Lemon Aid application tree into `team/develop`.

Repository-admin branch protection remains required before relying on the team
merge policy.
