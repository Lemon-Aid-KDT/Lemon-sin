# Supplement Brand DB Import Gate

Schema: `supplement-brand-db-import-gate-v1`

## Status

- Status: `blocked_by_operator_review`
- Product import manifest allowed: `false`
- DB apply allowed now: `false`
- DB apply allowed after dry-run: `false`

## Counts

- Brand candidates: `388`
- Decision rows: `388`
- Valid decisions: `0`
- Approved decisions: `0`
- Blank decisions: `388`
- Invalid decisions: `0`
- Unmatched decisions: `0`
- Missing decisions: `0`
- Pending operator actions: `388`

## Next Steps

- `complete_operator_brand_review`
- `rerun_brand_decision_preflight_require_all_reviewed`
- `rerun_brand_db_import_gate`

## Rule

DB apply는 지금 바로 허용하지 않습니다. strict brand review preflight 통과 후 product import manifest를 만들고, taxonomy approved manifest dry-run이 먼저 통과해야 합니다.
