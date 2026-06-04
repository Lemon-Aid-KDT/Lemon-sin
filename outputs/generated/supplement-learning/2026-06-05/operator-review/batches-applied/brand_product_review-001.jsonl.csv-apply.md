# Supplement Brand Batch Review CSV Apply

Schema: `supplement-brand-batch-review-csv-apply-markdown-v1`

이 문서는 CSV decision을 batch JSONL schema로 변환한 aggregate 결과만 표시합니다.

- Batch file: `brand_product_review-001.jsonl`
- Batch review CSV: `brand_product_review-001.review.csv`
- Output rows: `50`
- Changed rows: `0`
- Unchanged rows: `50`

## Decision Counts

- `blank`: `50`

## Next Gate

1. Output batch JSONL에 대해 single-batch preflight를 다시 실행합니다.
2. complete 상태가 된 batch만 reconcile로 넘깁니다.
3. queue-level preflight 통과 전에는 DB import manifest를 만들지 않습니다.
