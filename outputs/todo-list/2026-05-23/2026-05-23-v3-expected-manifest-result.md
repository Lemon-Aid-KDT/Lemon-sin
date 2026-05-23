# 2026-05-23 V3 Expected Manifest Result

Scope: 16개 chronic PaddleOCR post-alpha observations에 repo-local V3 expected snapshot을 deterministic하게 붙이는 도구를 추가했다. 새 OCR 호출, CLOVA 재전송, raw OCR text 저장은 없다.

Official references: Python JSON https://docs.python.org/3/library/json.html, argparse https://docs.python.org/3/library/argparse.html.

Implementation:

- `backend/scripts/build_three_tier_manifest_with_v3_expected.py`
  - `naver-live-0001` -> `naver-chronic-0001.snapshot_v3.json` 매핑
  - V3 expected projection에 필요한 필드만 구조 검증
  - raw OCR text, provider payload, request headers, image bytes, secret key 차단
- `backend/Nutrition-backend/tests/unit/scripts/test_build_three_tier_manifest_with_v3_expected.py`
  - live-to-chronic 매핑, raw field rejection, missing snapshot fail-closed 검증

Result:

```text
rows=16
v3_expected_attached=16
ingredient_count=18
provisional_expected=16
scoreable_fixture_count=7
provisional_fixture_count=16
expected_quality_warning_count=16
ingredient_name_exact_rate=0.1111
scoreable_ingredient_name_exact_rate=0.1111
raw_artifacts_stored=False
raw_ocr_text_stored=False
```

Interpretation: V3 expected 정렬은 성공했지만, 현재 V3 ingredients가 human-reviewed ground truth가 아니라 provisional seed라 PaddleOCR exact rate가 낮게 나온다. 따라서 이 결과는 “OCR 회귀”가 아니라 “V3 expected seed 품질 미확정” 증거로 취급한다. 공식 KPI를 만들려면 16개 V3 snapshot의 ingredient list를 사람 검수로 확정해야 한다.

Security checks: generated V3 expected evaluation artifacts privacy scan passed (`ocr_artifact_privacy_ok files=3`), generated artifacts are ignored local outputs.

Verification: 31 focused tests passed, black passed, ruff passed, `git diff --check` passed.
