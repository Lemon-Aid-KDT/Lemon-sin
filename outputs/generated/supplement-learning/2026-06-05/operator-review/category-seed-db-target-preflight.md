# Supplement Category Seed DB Target Preflight

Schema: `supplement-category-seed-db-target-preflight-v1`

이 문서는 category seed DB apply 전 연결 대상이 로컬 개발 DB인지 확인합니다. DB URL 원문, 사용자명, 비밀번호, DB 이름은 출력하지 않습니다.

- Status: `ready_for_local_category_seed_apply`
- Target apply allowed: `true`
- Runtime environment: `development`
- Database driver: `postgresql+asyncpg`
- Database host class: `local`
- Database target kind: `local_postgres`

## Conditions

- `apply_gate_performed_no_db_write`: `true`
- `category_seed_apply_gate_ready`: `true`
- `category_seed_apply_gate_status_ready`: `true`
- `database_host_is_local`: `true`
- `driver_is_postgresql_asyncpg`: `true`
- `environment_is_development`: `true`
- `product_apply_blocked`: `true`
- `product_category_apply_blocked`: `true`

## Failed Conditions

- none

## Next Steps

- `run_category_seed_apply_against_local_database`
- `run_category_seed_db_verifier`
- `record_category_seed_apply_result`

## Rule

이 preflight가 통과해도 제품/브랜드 DB write는 허용하지 않습니다. category seed apply는 로컬 개발 DB에서만 진행합니다.
