# TimescaleDB 활성화 운영 가이드

> 작성일: 2026-05-19 | 대상: 운영팀 + 백엔드 인계 담당자
> 관련 PR: PR-O (composite PK prep, alembic 0007) + PR-P (opt-in hypertable, alembic 0008)
> 관련 보고서: [Brand-New-update/2026-05-18-comprehensive-critical-audit-and-app-launch-readiness.md §1.1·§5.3·§P1](../../../Brand-New-update/2026-05-18-comprehensive-critical-audit-and-app-launch-readiness.md)

---

## 한 줄 요약

`alembic upgrade head`는 **TimescaleDB 확장이 가용한 PostgreSQL 인스턴스에서만** `health_daily_summaries`를 hypertable로 변환한다. 표준 PostgreSQL 인스턴스(`postgres:16` 등)에서는 NOTICE만 남기고 no-op로 통과한다. 운영 활성화는 *DB 인스턴스 교체* 또는 *기존 인스턴스에 extension 설치*로 시작한다.

---

## 1. 배경

### 1.1 왜 hypertable인가
`health_daily_summaries`는 사용자별 일별 건강 지표 집계(걸음수, 체중, 심박)를 적재한다. 사용자 N명·운영 기간 M개월 → 행 수가 빠르게 N×M×30 단위로 증가. 일반 PostgreSQL 인덱스만으로도 동작하지만 운영 6개월~3년 시점에 다음이 발생한다:
- B-tree 인덱스 깊이 증가 → INSERT/UPDATE 비용 ↑
- `measured_date` 기반 범위 쿼리 시 인덱스 leaf 스캔 폭증
- 오래된 데이터 보존 정책(retention)·압축(compression) 수동 관리

TimescaleDB hypertable은 위 셋을 자동화하고 *measured_date 기반 chunk 파티셔닝*으로 범위 쿼리를 chunk-prune한다. 라이선스는 Apache 2 (코어) + TSL (compress/continuous aggregate). 현 PR-P는 **Apache 코어 기능만 사용**.

### 1.2 PR-O / PR-P 책임 분담
- **PR-O** ([alembic/versions/0007_health_daily_summaries_composite_pk.py](../../../backend/alembic/versions/0007_health_daily_summaries_composite_pk.py)): PK를 `id` 단독에서 `(id, measured_date)` 복합으로 확장. TimescaleDB의 *UNIQUE/PK는 partition column 포함 필수* 규칙을 충족시키는 메타데이터 변경. 표준 Postgres에서도 안전 머지 가능.
- **PR-P** ([alembic/versions/0008_health_daily_summaries_hypertable.py](../../../backend/alembic/versions/0008_health_daily_summaries_hypertable.py)): 위 PK 위에서 *조건부* `create_hypertable` 호출. 확장 가용성 검사로 표준 Postgres·TimescaleDB Postgres 모두에서 깨지지 않는다.

---

## 2. 시나리오 결정 매트릭스

| 환경 | DB 이미지 / 인스턴스 | `alembic upgrade head` 결과 |
|------|---------------------|----------------------------|
| 로컬 dev | `postgres:16` (또는 무엇이든) | 0008이 NOTICE 남기고 no-op. 일반 테이블 그대로 사용 가능. |
| CI | `postgres:16` (현재 기본) | 0008이 NOTICE 남기고 no-op. CI 전체 통과 유지. |
| Staging | `timescale/timescaledb:latest-pg17` 권장 | 0008이 `CREATE EXTENSION timescaledb` + `create_hypertable` 실행. 운영 부하 패턴 검증. |
| Production | `timescale/timescaledb:latest-pg17` 또는 동등 매니지드 (Timescale Cloud / AWS RDS for TimescaleDB) | Staging 14일 검증 후 동일 절차로 활성화. |

표준 Postgres에서 hypertable로 마이그레이션하려면 *DB 인스턴스 자체*를 TimescaleDB 이미지로 교체해야 한다 (확장 동적 설치 불가). 운영 시작 시점에 결정한다.

---

## 3. 사전 점검 (활성화 직전 1회)

```sql
-- 1. 확장 가용성 확인
SELECT * FROM pg_available_extensions WHERE name = 'timescaledb';
-- 결과 0건 → 본 인스턴스는 TimescaleDB 미지원. DB 교체 필요.

-- 2. 이미 설치돼 있는지 확인 (있다면 alembic 0008은 idempotent)
SELECT * FROM pg_extension WHERE extname = 'timescaledb';

-- 3. 현 알렘빅 head 확인 (PR-O가 머지된 상태여야 한다)
SELECT version_num FROM alembic_version;
-- 기대값: 0008_health_daily_summaries_hypertable
-- (PR-O만 머지된 상태면 0007_health_daily_summaries_composite_pk)
```

---

## 4. 활성화 절차

```bash
# 1) DB가 TimescaleDB 이미지로 부팅됐는지 확인
psql "$DATABASE_URL" -c "SELECT * FROM pg_available_extensions WHERE name = 'timescaledb';"

# 2) 알렘빅 head 적용
cd backend
alembic upgrade head

# 3) hypertable 등록 확인
psql "$DATABASE_URL" -c \
    "SELECT hypertable_name FROM timescaledb_information.hypertables \
     WHERE hypertable_name = 'health_daily_summaries';"
# 기대 결과: 1 row, hypertable_name = 'health_daily_summaries'
```

`alembic upgrade head` 실행 로그에 `NOTICE: timescaledb extension not available` 이 보이면 *DB 인스턴스가 표준 Postgres*다. 활성화하려면 DB 인스턴스를 교체한 뒤 다시 `alembic upgrade head`를 호출한다 (마이그레이션은 idempotent).

---

## 5. 통합 테스트 실행

PR-P의 통합 테스트는 기본 `pytest` 실행에서 *제외*된다 (`pyproject.toml`의 `-m "not timescaledb"`). 활성화 후 검증할 때만 마커를 명시적으로 켠다:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://lemon:secret@db:5432/lemon \
    pytest -m timescaledb \
    Nutrition-backend/tests/integration/db/test_timescaledb_hypertable.py
```

두 테스트가 통과해야 한다:
- `test_health_daily_summaries_is_registered_as_hypertable`
- `test_timescaledb_extension_is_installed`

---

## 6. 운영 튜닝 — chunk_time_interval

기본값은 7일 청크. `health_daily_summaries`는 사용자당 일별 4 metric 기록이라 (1 user × 1 day = 1 row, 평균 1000 users × 7일 = 7,000 rows/청크) 충분히 안전. 변경이 필요하면:

```sql
-- 예: 14일 청크로 변경 (대량 운영 환경에서 청크 수 감소)
SELECT set_chunk_time_interval('health_daily_summaries', INTERVAL '14 days');
```

운영 출시 *전*에만 변경한다. 데이터가 쌓인 뒤 변경은 기존 청크의 경계에 영향을 주지 않는다(향후 청크에만 적용).

---

## 7. 롤백 시나리오

**downgrade 0008 → 0007은 의도적으로 no-op**. 이유:
1. Hypertable 해제는 데이터를 청크에서 일반 테이블로 *복사*해야 한다 — 트랜잭션 안전성 보장이 어렵다.
2. `alembic downgrade`는 자동 실행될 가능성이 있어 사고 위험이 크다.

비상 롤백이 필요한 경우:
- **선호**: 데이터베이스 스냅샷 / PITR (Point-in-Time Recovery) 복원.
- **차선**: 새 일반 테이블 생성 → `INSERT INTO new_table SELECT * FROM health_daily_summaries` → DROP hypertable → RENAME. **운영팀이 maintenance window를 잡고 수행**.

---

## 8. 라이선스 명시

- TimescaleDB 코어 (Apache 2): `create_hypertable`, chunk auto-creation, 기본 인덱싱. **본 PR이 사용하는 전부**.
- TimescaleDB TSL (Timescale License): compress, continuous aggregate, data tiering. **본 PR에서 미사용**. 향후 도입 시 라이선스 영향 별도 검토.

---

## 9. 다음 단계 (P2 트래킹)

- Retention policy (예: 3년 이상 데이터 자동 삭제) 추가 — `add_retention_policy`.
- Compression (TSL) 검토 — TSL 라이선스 영향 사전 검토 필요.
- Continuous aggregate (예: 주간/월간 사전 집계) — 대시보드 응답속도 개선용.

위 셋은 *현재 PR-P 범위 밖*. 운영 출시 후 사용량 패턴 데이터로 결정.
