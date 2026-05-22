# 2026-05-23 Artifact Privacy Gate Export Result

## Scope

PR split 계획에서 backend OCR quality gates를 더 작게 나누기 위해, generated OCR
artifact 유출 방지 gate만 clean code-bearing export base 위에서 독립 branch로
분리했다.

## Branches

- Base branch: `chore/ocr-clean-export-base`
- Export branch: `test/ocr-artifact-privacy-gate`
- Preserved remote: `origin/test/ocr-artifact-privacy-gate`
- Base commit: `67b9bc46 chore(ocr): export base artifact 추적을 제거`
- Patch commit: `98d51c7c test(ocr): artifact privacy gate를 추가`

## Changed Files

- `backend/scripts/check_ocr_artifact_privacy.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_ocr_artifact_privacy.py`

Change size:

```text
2 files changed, 585 insertions(+)
```

## Behavior Covered

- generated OCR artifact JSON/JSONL/Markdown scan
- forbidden raw keys:
  - `raw_ocr_text`
  - `ocr_text`
  - `raw_provider_payload`
  - `provider_payload`
  - `request_headers`
  - `image_bytes`
  - secret/header key variants
- developer-local path pattern detection
- populated secret assignment detection
- Git-tracked generated artifact detection for:
  - `outputs/generated/ocr-eval/`
  - `outputs/evaluations/supplement-ocr/live/`
- bounded diagnostics that print finding code and path but not matched sensitive
  values.

## Validation

```text
10 passed - test_check_ocr_artifact_privacy.py
black --check passed
ruff check passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
secret pattern scan on changed source files: no matches
git diff --check passed
git diff --cached --check passed
```

## Security / Leakage Review

- The branch adds scanner code and synthetic tests only.
- It does not add generated OCR observations, raw OCR text, provider raw payloads,
  request headers, image bytes, `.env`, or secrets.
- The test fixture that exercises secret assignment detection builds the
  credential-like string at runtime, so the repo source does not contain a
  contiguous credential assignment literal.
- The scanner itself intentionally reports only bounded finding codes and never
  prints matched sensitive text.

## Next Decision

This branch is a safe second PR candidate after `fix/ocr-field-extractor-shapes`.
It should still wait for the same team base decision:

1. use `chore/ocr-clean-export-base` as an approved code-bearing base, or
2. sync the real application tree into `team/develop`.

Repository-admin branch protection remains required before relying on the team
merge policy.
