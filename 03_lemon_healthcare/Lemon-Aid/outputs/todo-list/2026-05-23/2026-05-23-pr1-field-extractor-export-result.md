# 2026-05-23 PR 1 Field Extractor Export Result

## Scope

PR split 계획의 첫 번째 slice인 field extractor regression patch를 clean
code-bearing export base 위에서 실제 branch로 분리했다.

## Branches

- Base branch: `chore/ocr-clean-export-base`
- Export branch: `fix/ocr-field-extractor-shapes`
- Preserved remote: `origin/fix/ocr-field-extractor-shapes`
- Base commit: `67b9bc46 chore(ocr): export base artifact 추적을 제거`
- Patch commit: `9fac120b fix(ocr): 성분 표 셀 파싱을 보정`

## Changed Files

- `backend/Nutrition-backend/src/ocr/field_extractor.py`
- `backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py`

Change size:

```text
2 files changed, 115 insertions(+), 56 deletions(-)
```

## Behavior Covered

- colon-less table rows such as `비타민 C  1000mg`
- pipe-separated table rows such as `비타민 C | 1000mg`
- false-positive guard for single-space product-like rows such as `비타민 C 1000mg`
- thousand comma dosage normalization such as `1,000mg` -> `1000mg`
- `mcg`/`ug`/`µg` normalization to `μg`
- compound unit case normalization such as `μg rae` -> `μg RAE`

## Validation

```text
27 passed - backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py
black --check passed on field_extractor.py and test_field_extractor.py
ruff check --ignore RUF001 passed on field_extractor.py and test_field_extractor.py
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
secret pattern scan on changed files: no matches
git diff --check passed
git diff --cached --check passed
clean_base_is_ancestor=0
```

## Security / Leakage Review

- 변경은 deterministic parser와 unit tests에만 한정된다.
- network call, external OCR/LLM call, file write, subprocess, credential read를
  추가하지 않는다.
- raw OCR text, provider payload, request headers, image bytes, secret values를
  commit에 추가하지 않는다.
- branch는 clean export base를 parent로 하므로 generated OCR/live artifacts는
  Git-tracked 상태가 아니다.

## Next Decision

이 branch는 PR 1 후보로 준비되어 있지만 아직 팀 remote나 GitHub PR로 열지 않았다.
`team/develop`은 여전히 skeleton base이고, public GitHub metadata 기준
`develop`/`main` branch protection도 꺼져 있기 때문이다.

팀이 clean base 전략을 승인하면 다음 순서가 안전하다.

1. `chore/ocr-clean-export-base`를 team remote 또는 `team/develop` 동기화 경로로
   확정한다.
2. `fix/ocr-field-extractor-shapes`를 그 base 위의 작은 PR로 연다.
3. PR body에는 generated OCR artifacts 대신 이 문서와 PaddleOCR post-alpha
   summary만 링크한다.
