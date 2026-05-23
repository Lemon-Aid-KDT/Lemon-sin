# 2026-05-23 Analyze API Security Gate Export Result

## Scope

`PR 3 - Analyze API Security Gate` 범위를 clean code-bearing base 위의 독립
branch로 분리했다. 목표는 고비용 OCR 이미지 업로드 경로에 local abuse guard를
추가하고, 운영 환경에서는 process-local limiter만으로 배포되지 않게 막는 것이다.

## Branches

- Base branch: `chore/ocr-clean-export-base`
- Export branch: `feat/backend-analyze-rate-limit-gate`
- Preserved remote: `origin/feat/backend-analyze-rate-limit-gate`
- Base commit: `67b9bc46 chore(ocr): export base artifact 추적을 제거`
- Patch commit: `db3b5391 feat(backend): 분석 업로드 제한을 추가`

## Changed Files

- `backend/.env.example`
- `backend/Nutrition-backend/src/config.py`
- `backend/Nutrition-backend/src/main.py`
- `backend/Nutrition-backend/src/middleware/rate_limit.py`
- `backend/Nutrition-backend/tests/integration/api/test_supplement_intake_api.py`
- `backend/Nutrition-backend/tests/unit/test_config.py`

Change size:

```text
6 files changed, 499 insertions(+), 18 deletions(-)
```

## Behavior Covered

- Adds process-local fixed-window middleware for `POST /api/v1/supplements/analyze`.
- Returns HTTP `429` with `Retry-After` for exhausted upload buckets.
- Builds limiter subject keys from hashed client metadata, not raw client values.
- Does not use arbitrary `Authorization` header content as a bypass key.
- Rejects staging/production boot when `RATE_LIMIT_ENABLED=false`.
- Rejects production boot unless external ingress/API gateway/Redis rate-limit
  enforcement is attested with provider and non-secret policy reference.
- Updates `.env.example` to default local rate limiting on and Google API-key
  auth off.

## Validation

```text
70 passed - test_supplement_intake_api.py and test_config.py
black --check passed on changed Python files
ruff check --ignore RUF001 passed on changed Python files
git diff --cached --check passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
added-line secret pattern scan: no real secret assignments found
```

`detect-secrets-hook --baseline .secrets.baseline` cannot run directly on this
clean export base because that base does not yet include `.secrets.baseline`.
The missing baseline is the separate team-governance gap already tracked in the
quality-gates docs. For this branch, the changed lines were separately scanned
for credential-looking assignments and bearer tokens.

## Security / Leakage Review

- No generated OCR artifacts, raw OCR text, provider payloads, request headers,
  image bytes, `.env`, or secret values were added.
- Test fixture credential-looking strings were normalized to
  `noncredential-fixture-value`.
- The rate limiter stores only SHA-256 digests derived from client metadata.
- Production requires an external distributed limiter attestation because
  process-local memory is insufficient for multi-instance deployments.

## Next Decision

This branch is the next safe backend-security PR candidate after the OCR parser
and export/privacy gate branches. Team still needs to decide whether PRs target
the clean code-bearing base or wait until `team/develop` is synchronized with
the real Lemon Aid application tree.
