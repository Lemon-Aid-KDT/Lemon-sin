# Supplement Operator CSV Apply Check

## Summary

- `brand_product_review:001`의 batch-local CSV 적용 경로를 실제 산출물로 검증했다.
- CSV 적용 스크립트는 원본 `batches/brand_product_review-001.jsonl`을 수정하지 않고 `batches-applied/brand_product_review-001.jsonl` 복사본만 생성했다.
- 적용본 preflight는 CSV와 JSONL fixture order가 맞음을 `batch_review_csv_status=matched`로 확인했다.
- 같은 preflight는 현재 batch가 아직 수동 검수되지 않았음을 `blank_row_count=50`, `ready_for_reconcile=false`로 막고 있다.
- 따라서 brand/product DB import, review-image OCR ground truth, teacher OCR 비교, YOLO bbox dataset, PaddleOCR improvement loop는 계속 operator review 완료 이후 단계다.

## Artifacts

| Artifact | Status |
| --- | --- |
| `outputs/generated/supplement-learning/2026-06-05/operator-review/batches/brand_product_review-001.review.csv` | 50 rows, 50 blank decisions |
| `outputs/generated/supplement-learning/2026-06-05/operator-review/batches-applied/brand_product_review-001.jsonl` | generated, source batch not overwritten |
| `outputs/generated/supplement-learning/2026-06-05/operator-review/batches-applied/brand_product_review-001.jsonl.csv-apply.summary.json` | `changed_row_count=0`, `output_row_count=50` |
| `outputs/generated/supplement-learning/2026-06-05/operator-review/batches-applied/brand_product_review-001.jsonl.preflight.json` | `batch_review_csv_status=matched`, `batch_status=pending`, `ready_for_reconcile=false` |
| `outputs/generated/supplement-learning/2026-06-05/operator-review/operator-next-command-checklist.md` | starts with CSV apply, then CSV-validated applied-batch preflight, then reconcile with batch-file override |

## Current Gate Result

| Field | Value |
| --- | ---: |
| Expected rows | 50 |
| Applied output rows | 50 |
| CSV-applied changed rows | 0 |
| CSV fixture order match | true |
| Preflight valid rows | 0 |
| Preflight blank rows | 50 |
| Preflight invalid rows | 0 |
| Ready for reconcile | false |

## Interpretation

The command flow is now technically connected, but there is no reviewed brand/product data yet.
This is the correct fail-closed state: blank review rows cannot become DB import manifests, OCR ground-truth fixtures, YOLO section datasets, or PaddleOCR training candidates.

## Next Action

1. Fill the 50 rows in `brand_product_review-001.review.csv`.
2. Keep row order and row count unchanged.
3. Rerun `operator-next-command-checklist.md` command 1.
4. Rerun command 2 and confirm `ready_for_reconcile=true`.
5. Only then continue command 3 and downstream brand/product gates.

## Safety

- DB write performed: false.
- OCR provider call performed: false.
- LLM call performed: false.
- Source images read: false.
- Raw OCR text/provider payload/local absolute paths stored in this report: false.

## References

- Python argparse: https://docs.python.org/3/library/argparse.html
- Python csv: https://docs.python.org/3/library/csv.html
- Python json: https://docs.python.org/3/library/json.html
- PostgreSQL constraints: https://www.postgresql.org/docs/current/ddl-constraints.html
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
