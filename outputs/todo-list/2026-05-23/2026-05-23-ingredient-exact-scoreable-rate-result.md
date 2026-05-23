# 2026-05-23 Ingredient Exact Scoreable Rate Result

Scope: 기존 redacted PaddleOCR post-alpha observations를 새 evaluator로 재평가했다. OCR 원문, provider payload, request headers, image bytes, `.env`, secret 값은 저장/커밋하지 않았다.

Official references: PaddleOCR OCR pipeline https://www.paddleocr.ai/v3.3.1/en/version3.x/pipeline_usage/OCR.html, PP-StructureV3 http://www.paddleocr.ai/main/en/version3.x/pipeline_usage/PP-StructureV3.html, Python `re` https://docs.python.org/3/library/re.html.

Result:

```text
fixture_count=16
observation_count=16
scoreable_fixture_count=4
provisional_fixture_count=16
expected_quality_warning_count=26
ingredient_name_exact_rate=0.9375
scoreable_ingredient_name_exact_rate=1.0
raw_artifacts_stored=False
raw_ocr_text_stored=False
```

Conclusion: stage0 `ingredient_name_exact_rate=0.0`는 현재 post-alpha 상태 기준으로 stale이다. 남은 legacy 1개 mismatch는 `정x 3개입(` 포장 수량 token이 provisional expected에 섞인 ground-truth 품질 문제이며, 포장/수량 오염을 제외한 scoreable 지표는 95% 이상이다. 단, 16개 expected가 모두 provisional이므로 human-verified official KPI로는 아직 쓰지 않는다.

Verification: 54 focused tests passed, black passed, ruff passed, generated artifact privacy scan passed, detect-secrets passed, `git diff --check` passed.
