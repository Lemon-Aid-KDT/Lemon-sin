# db/ — DB 세션·초기화 (D 담당)

- session.py : async SQLAlchemy 세션
- init.sql : `CREATE EXTENSION IF NOT EXISTS timescaledb;` (Docker init 시 자동 실행)
