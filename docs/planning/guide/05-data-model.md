# Data Model Guide

> Source: PROJECT_GUIDE.md §6, §11
> 원본 대형 기획서는 PROJECT_GUIDE.md에 보존되어 있습니다.

## 6. 기술 스택 — 데이터베이스

### 6.1 데이터베이스 구성

| 분류 | 기술 | 선정 이유 | 앱에서의 역할 |
|------|------|-----------|---------------|
| 메인 DB | PostgreSQL 16 | JSON/JSONB(영양제 동적 스키마), GIN 인덱스(식품 풀텍스트 검색), 컬럼 단위 AES-256 암호화로 의료 데이터 보안 | 사용자·영양제·음식·진단·식단 기록 영속 |
| 시계열 확장 | TimescaleDB 2.x (`timescale/timescaledb:latest-pg16` 이미지) | Hypertable로 걸음수·체중·심박 효율 처리, 자동 다운샘플링·압축. 첫 부팅 시 init.sql에서 `CREATE EXTENSION IF NOT EXISTS timescaledb;` 자동 실행 | HealthKit/Health Connect에서 들어오는 시계열 데이터 |
| 캐시 / 큐 | Redis 7 | OCR 결과 캐싱(SHA-256 해시 키, 동일 영양제는 동일 결과), KDRIs 룩업 캐싱, Cloud Vision API rate limiting, 세션 | 영양제 분석 캐시(TTL 30일), 챗봇 컨텍스트 캐시 |
| 파일 스토리지 | S3 호환 (MVP는 NCP Object Storage 또는 로컬 디스크) | 영양제·음식 원본 사진 저장. DB에는 URL만 | photo_url 필드의 실체 |
| 마이그레이션 | Alembic (async) | SQLAlchemy 기반, 버전 관리 | 스키마 변경 추적 |
| 컨테이너 | Docker Compose | 로컬 개발 환경 통일 | timescale + redis 한 번에 부팅 |

### 6.2 핵심 테이블

```
users                    # 사용자 (uid, email, email_verified_at, name, created_at, deleted_at)
profiles                 # 프로필 (user_id, age, gender, height, weight,
                         #         chronic_diseases[] AES-256, medications[] AES-256, goals[])
consents                 # 동의 이력 (user_id, type, accepted_at, revoked_at)
supplements              # 영양제 마스터 (id, product_name_ko/en, manufacturer)
supplement_ingredients   # 영양제 성분 (supplement_id, name_ko/en, amount, unit)
user_supplements         # 사용자 복용 (user_id, supplement_id, dose, frequency)
foods                    # 식품 마스터 (식약처 + 농진청 데이터 임포트)
meals                    # 끼니 기록 (user_id, date, meal_type, foods[], photo_url)
diagnoses                # 분석 결과 (user_id, date, meal_type, deficiencies[] AES-256,
                         #            excesses[], warnings[] AES-256, goal_analysis)
                         # ※ 끼니별 단위. 점수는 daily_scores에 단일 저장.
daily_scores             # 하루 점수 (user_id, date, score, breakdown, agent_comment)
reminders                # 복약·식단 알림 (user_id, type, time, recurrence, weekdays[], active)
calendar_events          # 진료 일정 (user_id, date, time, title, hospital, note)
raffle_tickets           # 응모권 누적 (user_id, earned_at, count, reason, idempotency_key)
agent_memory             # Agent 요약 기억 (user_id, summary_json, updated_at)
agent_runs               # Agent 호출 로그 (request_id, agent_name, latency_ms, cost_usd, status)
audit_logs               # PHI 접근·수정 감사 로그 (user_id, actor, action, target, created_at)
email_verifications      # 이메일 인증 토큰 (user_id, token, expires_at, verified_at)

# 시계열 (TimescaleDB Hypertable)
step_counts              # 걸음수 (user_id, ts, count)
weight_logs              # 체중 (user_id, ts, kg)
heart_rate_samples       # 심박 (user_id, ts, bpm)
```

### 6.3 보안 · 컴플라이언스

| 항목 | 적용 |
|------|------|
| 민감정보 컬럼 암호화 | `chronic_diseases`, `medications`, `diagnoses.deficiencies`, `diagnoses.warnings` AES-256 |
| 전송 구간 | TLS 1.3 강제 |
| Row Level Security | PostgreSQL RLS로 본인 user_id 데이터만 접근 |
| 감사 로그 | 의료 정보(PHI) 조회·수정 모두 audit_logs 테이블 기록 |
| 백업 암호화 | pg_dump 결과 GPG 암호화 후 보관 |
| 삭제 / 동의 철회 | 사용자 탈퇴 시 30일 grace period 후 완전 삭제, 백업 90일 내 폐기 |

> 보안 셋업 책임자: D(백엔드) — JWT, RLS, AES-256 컬럼 암호화 모두 D 담당. 컴플라이언스 검토는 E(데이터·도메인) 협업.

### 6.4 캐싱 전략 (3단계)

1. **Redis L1**: OCR 결과(영양제 사진 SHA-256 → 분석 JSON), TTL 30일
2. **Redis L2**: KDRIs 룩업·식약처 기능성 인정 원료, TTL 영구 (수동 무효화)
3. **PostgreSQL**: 사용자별 분석 결과 영속, Agent 요약 기억

캐싱으로 LLM·OCR 호출 비용을 50% 이상 절감.


---

## 11. 데이터 모델

모든 사용자 데이터는 user_id로 격리되어 PostgreSQL에 저장. 시계열은 TimescaleDB Hypertable, 캐시는 Redis.

### 11.1 사용자 (User · Profile)

```
type User = {
  id: int (PK);
  email: string (unique);
  password_hash: string;
  display_name: string;
  email_verified_at: timestamp?;
  created_at: timestamp;
  last_login_at: timestamp;
  deleted_at: timestamp?;     # 30일 grace
}

type Profile = {
  id: int (PK);
  user_id: int (FK);
  age: int;
  gender: 'M' | 'F';
  height_cm: float;
  weight_kg: float;
  chronic_diseases: string[];   # AES-256
  medications: string[];        # AES-256
  goals: string[];
}

type Consent = {
  id: int (PK);
  user_id: int (FK);
  type: 'privacy' | 'ai_usage' | 'health_data' | 'notifications';
  accepted_at: timestamp;
  revoked_at: timestamp?;
}

type EmailVerification = {
  id: int (PK);
  user_id: int (FK);
  token: string;
  expires_at: timestamp;
  verified_at: timestamp?;
}
```

### 11.2 영양제 · 식단

```
type Supplement = {
  id: int (PK);
  product_name_ko: string;
  product_name_en: string;
  manufacturer: string;
  serving_size: string;
}

type SupplementIngredient = {
  id: int (PK);
  supplement_id: int (FK);
  name_ko: string;
  name_en: string;
  amount: float;
  unit: 'mg' | 'mcg' | 'IU';
  daily_value_pct: float?;
}

type UserSupplement = {
  id: int (PK);
  user_id: int (FK);
  supplement_id: int (FK);
  dose: float;
  frequency_per_day: int;
  taken_times: string[];
  started_at: date;
}

type Food = {
  id: int (PK);
  name_ko: string;
  name_en: string;
  nutrients_per_100g: jsonb;
  source: '식약처' | '농진청';
}

type Meal = {
  id: int (PK);
  user_id: int (FK);
  date: date;
  meal_type: 'breakfast' | 'lunch' | 'dinner' | 'snack';
  foods: jsonb;
  photo_url: string?;
}
```

### 11.3 분석 · 점수 · 알림

```
type Diagnosis = {
  id: int (PK);
  user_id: int (FK);
  date: date;
  meal_type: 'breakfast' | 'lunch' | 'dinner' | 'snack';
  deficiencies: jsonb;          # AES-256
  excesses: jsonb;
  warnings: jsonb;              # AES-256
  goal_analysis: jsonb;
}

type DailyScore = {
  id: int (PK);
  user_id: int (FK);
  date: date;
  score: int;                   # 0~100
  breakdown: jsonb;
  agent_comment: string;
}

type Reminder = {
  id: int (PK);
  user_id: int (FK);
  type: 'medication' | 'meal' | 'supplement';
  name: string;
  time: string;
  recurrence: 'daily' | 'weekly' | 'once';
  weekdays: int[]?;
  active: boolean;
}

type CalendarEvent = {
  id: int (PK);
  user_id: int (FK);
  date: date;
  time: string;
  title: string;
  hospital: string?;
  note: string?;
  added_to_system_calendar: boolean;
}

type RaffleTicket = {
  id: int (PK);
  user_id: int (FK);
  earned_at: timestamp;
  count: int;
  reason: 'daily' | 'weekly_streak' | 'monthly_complete';
  idempotency_key: string;
}

type AgentMemory = {
  id: int (PK);
  user_id: int (FK);
  summary: jsonb;
  updated_at: timestamp;
}

type AgentRun = {
  id: int (PK);
  request_id: string;
  user_id: int (FK);
  agent_name: 'analysis' | 'personalization' | 'chat' | 'evaluation';
  status: 'success' | 'fail' | 'fallback';
  latency_ms: int;
  cost_usd: float;
  created_at: timestamp;
}

type AuditLog = {
  id: int (PK);
  user_id: int (FK);
  actor: 'user' | 'admin' | 'system';
  action: string;
  target: string;
  created_at: timestamp;
}
```

### 11.4 시계열 (TimescaleDB Hypertable)

```
type StepCount = {
  user_id: int (FK);
  ts: timestamp;
  count: int;
}

type WeightLog = {
  user_id: int (FK);
  ts: timestamp;
  kg: float;
}

type HeartRateSample = {
  user_id: int (FK);
  ts: timestamp;
  bpm: int;
}
```

### 11.5 보안 · 권한

```
PostgreSQL Row Level Security (RLS) 적용

CREATE POLICY user_isolation ON profiles
  FOR ALL
  USING (user_id = current_setting('app.user_id')::int);

# 모든 테이블 동일 패턴 적용
# 컬럼 단위 AES-256: chronic_diseases, medications, deficiencies, warnings
# TLS 1.3 강제, 백업 GPG 암호화
```



