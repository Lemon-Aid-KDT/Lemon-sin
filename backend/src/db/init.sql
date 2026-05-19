-- TimescaleDB 확장 (시계열 데이터용, 향후 건강 데이터에 사용)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- users 테이블
CREATE TABLE IF NOT EXISTS users (
    id                SERIAL PRIMARY KEY,
    email             VARCHAR(255) UNIQUE NOT NULL,
    password_hash     TEXT NOT NULL,
    display_name      VARCHAR(100),
    email_verified_at TIMESTAMP WITH TIME ZONE,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    last_login_at     TIMESTAMP WITH TIME ZONE,
    deleted_at        TIMESTAMP WITH TIME ZONE
);

-- refresh_tokens 테이블 (logout 시 무효화용)
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked    BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token   ON refresh_tokens(token);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);

-- profiles 테이블 (로그인 후 온보딩에서 입력하는 개인정보)
CREATE TABLE IF NOT EXISTS profiles (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    age                 INTEGER,
    gender              VARCHAR(1),                 -- 'M' or 'F'
    height_cm           NUMERIC(5,2),
    weight_kg           NUMERIC(5,2),
    chronic_diseases    JSONB DEFAULT '[]'::jsonb,  -- 추후 AES-256 암호화 예정
    medications         JSONB DEFAULT '[]'::jsonb,  -- 추후 AES-256 암호화 예정
    goals               JSONB DEFAULT '[]'::jsonb,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- consents 테이블 (개인정보 동의 이력)
CREATE TABLE IF NOT EXISTS consents (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type        VARCHAR(50) NOT NULL,   -- 'privacy' | 'ai_usage' | 'health_data' | 'notifications'
    accepted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    revoked_at  TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_consents_user_id ON consents(user_id);
