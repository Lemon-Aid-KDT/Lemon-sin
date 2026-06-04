# Supplement OCR Benchmark Gate

Schema: `supplement-ocr-benchmark-gate-v1`

## Status

- Status: `blocked_by_pii_screening`
- Ground-truth template allowed: `false`
- Teacher OCR benchmark allowed: `false`
- External teacher OCR eval allowed: `false`
- PaddleOCR training allowed now: `false`

## Counts

- Candidate rows: `215`
- Cleared no personal data: `0`
- Blank PII decisions: `215`
- Pending PII actions: `215`
- Ground-truth rows: `0`
- Ready benchmark rows: `0`
- Benchmark fixtures: `0`
- Scoreable fixtures: `0`

## Next Steps

- `complete_review_image_pii_screening`
- `rerun_pii_screening_decision_preflight_require_all_reviewed`
- `rerun_ocr_benchmark_gate`

## Rule

CLOVA/Google Vision teacher OCR 평가는 PII strict preflight, human-reviewed GT, benchmark fixture 생성이 모두 통과한 뒤에만 허용합니다. PaddleOCR 학습은 별도 baseline gate 전까지 계속 차단합니다.
