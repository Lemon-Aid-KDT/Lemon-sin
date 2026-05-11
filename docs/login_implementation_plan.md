# 로그인 구현 계획 (B안)

> branch: `sunghoon-database` · 담당: D (백엔드) · 작성일: 2026-05-11

---

## 파일 구조

```
Lemon-sin/
├─ docker-compose.yml                 ← PostgreSQL+TimescaleDB+Redis 컨테이너
│
└─ backend/
   ├─ requirements.txt                ← 패키지 목록
   ├─ .env.example                    ← 환경변수 템플릿
   │
   └─ src/
      ├─ main.py                      ← FastAPI 앱 생성 + 라우터 등록
      ├─ config.py                    ← 환경변수 로딩 (pydantic Settings)
      │
      ├─ db/
      │  ├─ init.sql                  ← TimescaleDB 확장 + users 테이블 DDL
      │  ├─ base.py                   ← DeclarativeBase + 공통 Mixin
      │  └─ session.py                ← async engine + get_db dependency
      │
      ├─ models/
      │  └─ user.py                   ← User ORM 모델 (users 테이블)
      │
      ├─ schemas/
      │  └─ auth.py                   ← 요청/응답 Pydantic 스키마
      │
      ├─ utils/
      │  └─ security.py               ← bcrypt 해싱 + JWT 생성/검증
      │
      └─ api/
         └─ auth.py                   ← 4개 엔드포인트
```

---

## 파일 간 의존 관계

```
config.py
  └─ DB_URL, JWT_SECRET, 환경변수 읽기
       ↓
db/session.py                         db/base.py
  └─ async engine 생성 (config.py 참조)  └─ Base, TimestampMixin
  └─ get_db() FastAPI dependency            ↓
       ↓                             models/user.py
       └──────────────────────────────── User 모델 정의
                                              ↓
                                      db/init.sql
                                        └─ users 테이블 DDL
                                              ↓
                                      alembic/env.py
                                        └─ 모델 import → autogenerate

utils/security.py
  └─ hash_password() / verify_password()   ← passlib[bcrypt]
  └─ create_access_token()                  ← python-jose
  └─ create_refresh_token()
  └─ decode_token()

schemas/auth.py
  └─ SignupRequest, LoginRequest
  └─ TokenResponse, RefreshRequest

api/auth.py
  ├─ POST /signup    → DB INSERT + 비밀번호 해싱
  ├─ POST /login     → DB 조회 + 비밀번호 검증 + JWT 발급
  ├─ POST /refresh   → refresh 토큰 검증 + 새 access 토큰
  └─ POST /logout    → refresh 토큰 DB 무효화

main.py
  └─ app.include_router(auth_router, prefix="/api/v1")
```

---

## 로그인 요청 흐름

```
Flutter 앱 (또는 Swagger UI)
  │
  │  POST /api/v1/auth/login
  │  Body: { "email": "...", "password": "..." }
  ▼
main.py → auth.py 라우터
  │
  ├─ schemas/auth.py 로 요청 파싱·검증
  ├─ get_db() 로 DB 세션 주입
  ├─ users 테이블에서 email 조회
  ├─ security.verify_password() 로 bcrypt 검증
  └─ security.create_access_token() + create_refresh_token()
  │
  ▼
Response: {
  "access_token":  "eyJ...",   ← 30분 유효
  "refresh_token": "eyJ...",   ← 7일 유효
  "token_type":    "bearer"
}
```

---

## users 테이블

```sql
CREATE TABLE users (
  id                SERIAL PRIMARY KEY,
  email             VARCHAR(255) UNIQUE NOT NULL,
  password_hash     TEXT NOT NULL,
  display_name      VARCHAR(100),
  email_verified_at TIMESTAMP,
  created_at        TIMESTAMP DEFAULT now(),
  last_login_at     TIMESTAMP,
  deleted_at        TIMESTAMP           -- 30일 grace
);
```

---

## 엔드포인트 목록

| 메서드 | 경로 | 기능 |
|--------|------|------|
| POST | `/api/v1/auth/signup` | 회원가입 (이메일+비밀번호) |
| POST | `/api/v1/auth/login` | 로그인 → access+refresh JWT |
| POST | `/api/v1/auth/refresh` | 토큰 갱신 |
| POST | `/api/v1/auth/logout` | 로그아웃 (refresh 무효화) |

---

## 로컬 검증 절차

```bash
# 1. DB 실행
docker-compose up -d

# 2. 환경변수 세팅
cp backend/.env.example backend/.env
# .env 파일에서 값 채우기

# 3. 마이그레이션 적용
cd backend
alembic upgrade head

# 4. 서버 실행
uvicorn src.main:app --reload

# 5. Swagger UI 에서 테스트
# http://localhost:8000/docs
#   → POST /api/v1/auth/signup 으로 계정 생성
#   → POST /api/v1/auth/login 으로 토큰 발급 확인
```

---

## 이번 PR 범위 외 (다음 PR)

- 이메일 인증 (`/verify-email`)
- 회원 탈퇴 (`DELETE /account`)
- 프로필 입력 (`/profile`)
- 나머지 테이블 모델 (supplements, meals, diagnoses 등)
