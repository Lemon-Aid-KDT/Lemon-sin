# Lemon Aid — 데이터베이스 완전 가이드

> 비전공자도 처음부터 끝까지 이해할 수 있도록 작성한 DB 구조 설명서  
> 담당: D (백엔드) · 작성일: 2026-05-12 · v3.0

---

## 목차

1. [데이터베이스란 무엇인가?](#1-데이터베이스란-무엇인가)
2. [왜 PostgreSQL인가?](#2-왜-postgresql인가)
3. [왜 Docker로 실행하는가?](#3-왜-docker로-실행하는가)
4. [왜 Redis도 같이 쓰는가?](#4-왜-redis도-같이-쓰는가)
5. [외부 데이터 소스 3종 분석](#5-외부-데이터-소스-3종-분석)
6. [전체 데이터 구조 설계](#6-전체-데이터-구조-설계)
7. [병원 데이터 + 사용자 데이터 연결 구조](#7-병원-데이터--사용자-데이터-연결-구조)
8. [음식·영양제 섭취 기록 구조](#8-음식영양제-섭취-기록-구조)
9. [전체 테이블 구조 (현재 + 예정)](#9-전체-테이블-구조)
10. [테이블 간의 관계 (ERD)](#10-테이블-간의-관계)
11. [파일 구조와 역할](#11-파일-구조와-역할)
12. [요청부터 저장까지 — 전체 흐름](#12-요청부터-저장까지--전체-흐름)
13. [보안 처리 방식](#13-보안-처리-방식)
14. [SQLAlchemy — Python과 DB를 연결하는 다리](#14-sqlalchemy--python과-db를-연결하는-다리)
15. [Alembic — 테이블 변경 이력 관리](#15-alembic--테이블-변경-이력-관리)
16. [현재 구현된 API 전체 목록](#16-현재-구현된-api-전체-목록)
17. [로컬 실행 순서](#17-로컬-실행-순서)
18. [자주 하는 실수와 해결법](#18-자주-하는-실수와-해결법)
19. [다음 구현 예정 항목](#19-다음-구현-예정-항목)

---

## 1. 데이터베이스란 무엇인가?

### 1.1 일상 언어로 설명

앱을 쓸 때 입력하는 모든 정보는 어딘가에 저장되어야 합니다. 앱을 껐다 켜도 내 정보가 그대로 있는 이유가 바로 **데이터베이스(DB)** 가 정보를 보관하기 때문입니다.

가장 쉬운 비유는 **도서관**입니다.

```
도서관 = 데이터베이스 전체
서가(책장) = 테이블 (users, profiles, meals ...)
책 한 권 = 행(row) — 사용자 한 명의 정보
책의 목차 = 열(column) — 이름, 이메일, 나이 등 항목
사서 = 데이터베이스 관리 시스템 (PostgreSQL)
대출 규칙 = 제약 조건 (이메일 중복 불가, 비밀번호 필수 등)
```

### 1.2 Excel과 비교

많은 분들이 익숙한 Excel로 비교하면 이렇습니다.

| Excel | 데이터베이스 |
|-------|-------------|
| 파일(.xlsx) | 데이터베이스 |
| 시트(탭) | 테이블 |
| 행 | 레코드(record) |
| 열 | 컬럼(column) |
| 셀 서식 | 데이터 타입 (숫자, 문자, 날짜...) |
| 시트 간 참조(=Sheet1!A1) | 외래키(Foreign Key) |

**그렇다면 왜 Excel 대신 DB를 쓰나요?**

```
Excel의 한계:
  - 동시에 여러 명이 수정하면 파일이 망가짐
  - 수백만 행이 되면 엄청나게 느려짐
  - 비밀번호 같은 보안 처리가 어려움
  - 앱(Flutter)이 자동으로 읽고 쓸 수가 없음

데이터베이스:
  - 수만 명이 동시에 접속해도 안전하게 처리
  - 수억 건의 데이터도 0.001초 만에 검색
  - 암호화, 접근 권한 관리 내장
  - 앱과 자동으로 통신 가능
```

---

## 2. 왜 PostgreSQL인가?

### 2.1 데이터베이스 종류

세상에는 많은 종류의 데이터베이스가 있습니다. 크게 두 가지로 나뉩니다.

```
관계형 DB (테이블 구조)          비관계형 DB (자유 구조)
  Oracle                           MongoDB
  PostgreSQL  ← 우리가 선택       Redis  ← 캐시 용도로 같이 사용
  MySQL
  SQLite
```

### 2.2 왜 Oracle이 아닌가?

레몬헬스케어 실무에서는 Oracle을 사용합니다. 하지만 이 프로젝트에서 Oracle을 쓰지 않는 이유:

| 이유 | 설명 |
|------|------|
| 비용 | Oracle은 CPU 코어당 연간 수백만 원 |
| 설치 복잡도 | 설치와 설정만 수일 소요 |
| 학생 환경 | 라이선스 없이 합법적으로 쓸 수 없음 |

Oracle Free(Express) 버전이 있지만 **2GB RAM, 2 CPU 제한**이 있어 OCR + LLM + 시계열 DB를 동시에 돌리기 어렵습니다.

### 2.3 왜 MySQL이 아닌가?

MySQL도 무료이지만 이 프로젝트에서 부족한 부분이 있습니다.

| 필요한 기능 | MySQL | PostgreSQL |
|------------|-------|------------|
| JSON 데이터 유연 저장 | 제한적 | JSONB로 완벽 지원 |
| 시계열 확장(TimescaleDB) | 없음 | 있음 |
| 행 단위 보안(RLS) | 없음 | 있음 |
| 전문 검색(Full Text) | 약함 | 강함 |
| Oracle 문법 유사도 | 낮음 | 높음 |

### 2.4 PostgreSQL을 선택한 3가지 핵심 이유

**이유 ①: JSONB — 영양제 성분표를 자유롭게 저장**

영양제 제품마다 성분이 다릅니다. 비타민C만 있는 것도 있고, 30가지 성분이 있는 종합비타민도 있습니다. 이걸 고정된 열로 만들면:

```
❌ 일반 방식 (열 고정):
비타민C | 비타민D | 오메가3 | 마그네슘 | 아연 | CoQ10 | ...
500mg  |  NULL  |  NULL  |  NULL   | NULL | NULL | ...  ← 대부분 비어있음

✅ JSONB 방식:
nutrients: {
  "비타민C": {"amount": 500, "unit": "mg"},
  "비타민D": {"amount": 1000, "unit": "IU"}
}  ← 있는 것만 저장, 공간 낭비 없음
```

**이유 ②: TimescaleDB — 걸음수·심박수를 빠르게 처리**

사용자 한 명이 하루 1,440분 동안 매 분마다 걸음수를 기록하면 하루에 1,440건입니다. 사용자 1,000명이면 하루 144만 건입니다. 이 시계열 데이터를 일반 DB로 처리하면:

```
일반 PostgreSQL:    최근 30일 조회 → 약 0.8초
TimescaleDB 확장:  최근 30일 조회 → 약 0.02초 (40배 빠름)
```

TimescaleDB는 PostgreSQL 위에 얹는 **플러그인**이므로 추가 비용 없이 사용할 수 있습니다.

**이유 ③: RLS — 내 정보는 나만 볼 수 있다**

Row Level Security(행 단위 보안)는 PostgreSQL 내부에서 "본인 데이터만 볼 수 있게" 강제하는 기능입니다.

```sql
-- 이 설정 하나로, user_id가 다른 행은 절대 조회 불가
CREATE POLICY user_isolation ON profiles
  USING (user_id = current_setting('app.user_id')::int);
```

---

## 3. 왜 Docker로 실행하는가?

### 3.1 Docker가 없다면

각 팀원이 자기 컴퓨터에 PostgreSQL을 직접 설치해야 합니다. 문제는:

```
팀원 A (Mac): PostgreSQL 16 설치 → 잘 됨
팀원 B (Windows): 설치 중 오류 → 3시간 삽질
팀원 C (Windows): 버전 14 설치 → 버전 차이로 오류

"내 컴퓨터에서는 되는데요?" 현상 발생
```

### 3.2 Docker를 쓰면

```
docker-compose up -d  ← 명령어 하나로 끝

누구 컴퓨터에서 실행해도 동일한 환경
PostgreSQL 16 + TimescaleDB + Redis 동시에 실행
컴퓨터에 아무것도 직접 설치하지 않아도 됨
```

Docker는 **미리 만들어진 환경을 담은 상자(컨테이너)** 를 실행하는 도구입니다. 우리가 쓰는 상자 두 개:

| 컨테이너 이름 | 내용물 | 포트 |
|-------------|--------|------|
| lemon_aid_db | PostgreSQL 16 + TimescaleDB | 5432 |
| lemon_aid_redis | Redis 7 | 6379 |

---

## 4. 왜 Redis도 같이 쓰는가?

### 4.1 Redis란

Redis는 **초고속 임시 저장소**입니다. PostgreSQL이 도서관이라면 Redis는 **포스트잇** 입니다.

```
PostgreSQL (도서관): 영구 저장, 느리지만 안전
Redis (포스트잇):    임시 저장, 빠르지만 메모리 기반
```

### 4.2 이 프로젝트에서 Redis 용도

| 용도 | 설명 | 효과 |
|------|------|------|
| OCR 결과 캐시 | 같은 영양제 사진은 다시 분석 안 함 | 비용 50% 절감 |
| KDRIs 룩업 캐시 | 영양소 권장량 테이블 (자주 읽힘) | DB 부하 감소 |
| API Rate Limit | 사용자당 분당 5회 제한 | 과도한 비용 방지 |

---

## 5. 외부 데이터 소스 3종 분석

이 프로젝트에서 사용하는 외부 공공 데이터 3종의 구조와 우리 DB에 적재하는 방식을 설명합니다.

### 5.1 AI Hub — 한국 음식 이미지 데이터셋

**출처:** https://aihub.or.kr (데이터셋 번호 79)  
**용도:** 음식 사진 촬영 시 음식 이름 자동 인식 보조  
**규모:** 150종 음식 × 약 1,000장 = 총 150,000장

#### 제공 데이터 구조

```
AI Hub 음식 이미지 데이터
├─ 이미지 파일 (.jpg)
│    └─ 파일명 = 음식코드_일련번호.jpg
│
└─ 라벨 파일 (.json)
     ├─ food_id       : 음식 고유 코드 (예: F001)
     ├─ food_name_ko  : 음식명 한국어 (예: "된장찌개")
     ├─ food_name_en  : 음식명 영어 (예: "Doenjang Jjigae")
     ├─ category_main : 대분류 (밥류 / 면류 / 국류 / 구이류 ...)
     ├─ category_sub  : 소분류 (찌개 / 국 / 탕 ...)
     └─ bounding_box  : 이미지 안 음식 위치 좌표
```

#### 우리 DB 매핑

```
AI Hub 컬럼          우리 DB 테이블.컬럼
─────────────────────────────────────────
food_name_ko    →   foods.name_ko
food_name_en    →   foods.name_en
category_main   →   food_categories.name (대분류)
category_sub    →   food_categories.parent_id 참조
이미지 파일     →   Object Storage(S3/NCP) 업로드 후 URL만 저장
bounding_box 등 →   foods.ai_meta (JSONB)
```

> 이미지는 DB에 저장하지 않습니다. S3/NCP Object Storage에 올리고 URL(주소)만 저장합니다.
> 이미지를 DB에 넣으면 용량이 폭발적으로 커지기 때문입니다.

---

### 5.2 식약처 식품영양정보 표준DB

**출처:** https://data.mfds.go.kr  
**용도:** 음식별 정확한 영양소 수치 (100g당 칼로리, 단백질 등)  
**규모:** 가공식품·외식메뉴·건강기능식품 포함 수만 건

#### 제공 데이터 구조

```
식약처 표준DB 컬럼 구조
├─ 기본정보
│    ├─ 식품코드         고유 식별 코드 (예: D000001)
│    ├─ 대표식품명       음식 이름
│    ├─ 제조사명         제조·판매 회사
│    ├─ 식품유형         가공식품 / 건강기능식품 / 외식 / 원재료
│    └─ 1회 제공량(g)    1인분 기준 무게
│
└─ 영양성분 (100g 기준)
     에너지(kcal) / 탄수화물(g) / 단백질(g) / 지방(g)
     나트륨(mg) / 당류(g) / 식이섬유(g) / 콜레스테롤(mg)
```

#### 우리 DB 매핑

```
식약처 컬럼       우리 DB 테이블.컬럼
──────────────────────────────────────
식품코드    →   foods.source_code
대표식품명  →   foods.name_ko
제조사명    →   foods.manufacturer
식품유형    →   foods.food_type
영양성분    →   foods.nutrients_per_100g (JSONB)
```

---

### 5.3 식품안전나라 영양정보 DB

**출처:** https://various.foodsafetykorea.go.kr/nutrient  
**용도:** 비타민·미네랄·아미노산 등 50종 이상 세부 영양소  

#### 제공 데이터 카테고리

```
식품안전나라 영양 카테고리
├─ 일반성분 (7종)
│    에너지 / 탄수화물 / 단백질 / 지방 / 수분 / 회분 / 식이섬유
│
├─ 수용성 비타민 (8종)
│    비타민B1 / B2 / B3(나이아신) / B5 / B6 / B7 / B9(엽산) / B12
│
├─ 지용성 비타민 (4종)
│    비타민A / D / E / K
│
├─ 무기질 (9종)
│    칼슘 / 인 / 나트륨 / 칼륨 / 마그네슘 / 철 / 아연 / 구리 / 망간
│
├─ 아미노산 (18종)
│    필수 9종 + 비필수 9종
│
├─ 지방산
│    포화지방산 / 단불포화 / 다불포화 / 오메가3 / 오메가6
│
└─ 당류 (5종)
     포도당 / 과당 / 갈락토스 / 자당 / 유당
```

#### 우리 DB 매핑

```
모든 영양소 수치 → foods.nutrients_per_100g (JSONB)

JSONB 예시:
{
  "에너지_kcal": 157,    "탄수화물_g": 34.4,
  "단백질_g": 2.7,       "지방_g": 0.3,
  "비타민C_mg": 0,       "비타민D_mcg": 0,
  "칼슘_mg": 5,          "철_mg": 0.4,
  "오메가3_g": 0.02
}
```

---

## 6. 전체 데이터 구조 설계

### 6.1 데이터 흐름 개요

```
┌───────────────┬────────────────┬────────────────┬──────────────┐
│  공공 DB      │  병원 데이터   │  사용자 입력   │ 기기 데이터  │
│  (식약처 등)  │ (Kaggle/LDB)   │ (온보딩/기록)  │(HealthKit)   │
│               │                │                │              │
│ 음식 영양소   │ 진단명·검사값  │ 나이·키·체중   │ 걸음수       │
│ 영양제 성분   │ 처방약 정보    │ 식단 사진 기록 │ 심박수       │
│ AI 분류 체계  │ 병원 방문 이력 │ 영양제 복용기록│ 체중         │
└───────────────┴────────────────┴────────────────┴──────────────┘
                              │
                              ▼
                    PostgreSQL DB (통합 저장소)
                              │
                              ▼
                    AI 4개 Agent (분석·개인화)
```

### 6.2 음식 데이터 테이블

```
┌─────────────────────────────────────────────────────────────┐
│  테이블: food_categories (음식 분류 체계)                    │
│  출처: AI Hub 분류 기준                                      │
├──────────────────┬──────────────┬─────────────────────────┤
│ 컬럼             │ 타입         │ 설명                    │
├──────────────────┼──────────────┼─────────────────────────┤
│ id               │ SERIAL       │ 고유번호                │
│ name             │ VARCHAR(100) │ 분류명 (예: 밥류)       │
│ parent_id        │ INTEGER      │ 상위 분류 (NULL=최상위) │
│ level            │ INTEGER      │ 1=대분류, 2=소분류      │
└──────────────────┴──────────────┴─────────────────────────┘

예시:
  id=1, name="밥류",      parent_id=NULL, level=1
  id=2, name="볶음밥",    parent_id=1,    level=2
  id=4, name="국·찌개류", parent_id=NULL, level=1
  id=5, name="된장찌개",  parent_id=4,    level=2

┌─────────────────────────────────────────────────────────────┐
│  테이블: foods (음식 마스터)                                  │
│  출처: 식약처 표준DB + 식품안전나라 + AI Hub 통합            │
├──────────────────┬──────────────┬─────────────────────────┤
│ 컬럼             │ 타입         │ 설명                    │
├──────────────────┼──────────────┼─────────────────────────┤
│ id               │ SERIAL       │ 고유번호 (PK)           │
│ source_code      │ VARCHAR(50)  │ 식약처 원본 코드        │
│ name_ko          │ VARCHAR(200) │ 음식명 한국어           │
│ name_en          │ VARCHAR(200) │ 음식명 영어             │
│ category_id      │ INTEGER      │ food_categories 참조    │
│ food_type        │ VARCHAR(50)  │ 가공식품/외식/원재료    │
│ manufacturer     │ VARCHAR(200) │ 제조사 (없으면 NULL)    │
│ serving_size_g   │ NUMERIC(7,2) │ 1회 제공량(g)           │
│ nutrients_100g   │ JSONB        │ 100g당 50종 영양소      │
│ image_url        │ TEXT         │ 대표 이미지 URL         │
│ source           │ VARCHAR(50)  │ 식약처/농진청/AI Hub    │
└──────────────────┴──────────────┴─────────────────────────┘
```

### 6.3 영양제 데이터 테이블

```
┌─────────────────────────────────────────────────────────────┐
│  테이블: supplements (영양제 마스터)                         │
│  출처: 식약처 건강기능식품 원료 DB                           │
├──────────────────┬──────────────┬─────────────────────────┤
│ id               │ SERIAL       │ 고유번호 (PK)           │
│ source_code      │ VARCHAR(50)  │ 식약처 원료 코드        │
│ product_name_ko  │ VARCHAR(300) │ 제품명 한국어           │
│ product_name_en  │ VARCHAR(300) │ 제품명 영어             │
│ manufacturer     │ VARCHAR(200) │ 제조사                  │
│ supplement_type  │ VARCHAR(100) │ 비타민/미네랄/오메가3   │
│ serving_size     │ VARCHAR(100) │ 1회 섭취량 표기         │
│ functionality    │ TEXT         │ 식약처 인정 기능성      │
│ warnings         │ TEXT         │ 섭취 주의사항           │
└──────────────────┴──────────────┴─────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  테이블: supplement_ingredients (영양제 성분 상세)           │
├──────────────────┬──────────────┬─────────────────────────┤
│ supplement_id    │ INTEGER      │ supplements 참조 (FK)   │
│ name_ko          │ VARCHAR(200) │ 성분명 한국어           │
│ name_en          │ VARCHAR(200) │ 성분명 영어             │
│ amount           │ NUMERIC      │ 함량 수치               │
│ unit             │ VARCHAR(20)  │ mg / mcg / IU / g       │
│ daily_value_pct  │ NUMERIC(6,2) │ 1일 권장량 대비 %       │
│ upper_limit      │ NUMERIC      │ 상한섭취량 (UL)         │
└──────────────────┴──────────────┴─────────────────────────┘

예시: 종합비타민A 제품
  supplements: id=1, product_name_ko="종합비타민A"
  ingredients:
    supplement_id=1, name_ko="비타민C",  amount=500, unit="mg", daily_value_pct=556
    supplement_id=1, name_ko="비타민D",  amount=1000, unit="IU", daily_value_pct=250
```

---

## 7. 병원 데이터 + 사용자 데이터 연결 구조

### 7.1 왜 병원 데이터가 필요한가?

```
일반 영양제 앱:
  사용자 입력 → 일반인 기준 권장량 안내

Lemon Aid:
  사용자 입력 + 병원 검사값 + 복약 정보
  → "당뇨가 있으니 탄수화물 주의" 같은 개인화 권고
```

### 7.2 병원 데이터 테이블

```
┌─────────────────────────────────────────────────────────────┐
│  테이블: hospital_records (병원 방문 기록)                   │
│  MVP: Kaggle 만성질환 데이터 / 실서비스: LDB 연동           │
├──────────────────┬──────────────┬─────────────────────────┤
│ id               │ SERIAL       │ 고유번호 (PK)           │
│ user_id          │ INTEGER      │ users 참조 (FK)         │
│ visit_date       │ DATE         │ 진료 날짜               │
│ hospital_name    │ VARCHAR(200) │ 병원명                  │
│ department       │ VARCHAR(100) │ 진료과 (내과/순환기과)  │
│ diagnosis_codes  │ JSONB        │ 진단 코드 목록 (ICD-10) │
│ diagnosis_names  │ JSONB        │ 진단명 한국어 (암호화)  │
│ source           │ VARCHAR(50)  │ kaggle / ldb / manual   │
└──────────────────┴──────────────┴─────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  테이블: lab_results (검사 수치)                             │
│  혈당, 혈압, 콜레스테롤 등 정기 검사값                      │
├──────────────────┬──────────────┬─────────────────────────┤
│ id               │ SERIAL       │ 고유번호 (PK)           │
│ user_id          │ INTEGER      │ users 참조 (FK)         │
│ measured_at      │ TIMESTAMP    │ 검사 일시               │
│ test_type        │ VARCHAR(100) │ 검사 종류               │
│ value            │ NUMERIC      │ 수치 (암호화 예정)      │
│ unit             │ VARCHAR(50)  │ mg/dL, mmHg 등          │
│ reference_min    │ NUMERIC      │ 정상 최솟값             │
│ reference_max    │ NUMERIC      │ 정상 최댓값             │
│ is_abnormal      │ BOOLEAN      │ 정상 범위 초과 여부     │
└──────────────────┴──────────────┴─────────────────────────┘

검사 항목 예시:
  공복혈당    value=126  unit="mg/dL"  ref_min=70   ref_max=100
  수축기혈압  value=145  unit="mmHg"   ref_min=90   ref_max=120
  총콜레스테롤 value=220 unit="mg/dL"  ref_min=0    ref_max=200
  HbA1c      value=6.8  unit="%"      ref_min=0    ref_max=5.7
```

### 7.3 사용자 데이터 + 병원 데이터 연결 방식

```
① 회원가입 + 온보딩 (사용자가 직접 입력)
   users 테이블 → profiles 테이블
   이메일·비밀번호  나이·성별·키·체중·만성질환·복약

② 병원 데이터 연결 (시연: Kaggle / 실서비스: LDB)
   hospital_records (user_id로 연결)
     └ 진단명, 방문 병원, 진료과
   lab_results (user_id로 연결)
     └ 혈당, 혈압, 콜레스테롤 수치

③ AI Agent가 두 데이터를 합쳐서 해석
   profiles.chronic_diseases = ["고혈압", "당뇨전단계"]
   lab_results: 공복혈당 126mg/dL (정상 초과)
         ↓
   "이 사용자는 당뇨 위험군 + 고혈압 환자이므로
    탄수화물 섭취량을 일반인 기준보다 엄격하게 적용"
         ↓
   agent_memory 테이블에 요약 저장 → 다음 분석 재활용
```

### 7.4 Kaggle 데이터 → 우리 DB 매핑

```
Kaggle 컬럼              우리 DB 테이블.컬럼
─────────────────────────────────────────────
Age (나이)          →   profiles.age
Gender (성별)       →   profiles.gender
BMI                 →   키+체중으로 계산
Hypertension        →   profiles.chronic_diseases []
Diabetes            →   profiles.chronic_diseases []
Heart Disease       →   profiles.chronic_diseases []
Blood Glucose Level →   lab_results (test_type="공복혈당")
HbA1c Level         →   lab_results (test_type="HbA1c")
```

---

## 8. 음식·영양제 섭취 기록 구조

### 8.1 식단 기록 흐름

```
사진 촬영 → 분석 Agent (OCR+AI) → 사용자 확인 → 저장
                                              │
                                   ┌──────────┴──────────┐
                                   ▼                     ▼
                                meals              diagnoses
                               (원본기록)           (분석결과)
```

### 8.2 식단 기록 테이블

```
┌─────────────────────────────────────────────────────────────┐
│  테이블: meals (끼니 기록)  — 사진 1장 = 한 끼니 = 1행     │
├──────────────────┬──────────────┬─────────────────────────┤
│ id               │ SERIAL       │ 고유번호 (PK)           │
│ user_id          │ INTEGER      │ users 참조 (FK)         │
│ eaten_at         │ TIMESTAMP    │ 식사 일시               │
│ meal_type        │ VARCHAR(20)  │ breakfast/lunch/dinner  │
│ photo_url        │ TEXT         │ 사진 저장 URL           │
│ items            │ JSONB        │ 인식된 음식 목록        │
│ total_nutrients  │ JSONB        │ 이 끼니의 총 영양소     │
│ is_confirmed     │ BOOLEAN      │ 사용자가 확인했는지     │
└──────────────────┴──────────────┴─────────────────────────┘

items JSONB 구조:
[
  { "food_id": 1234, "food_name": "공깃밥",
    "amount_g": 200,
    "nutrients": {"에너지_kcal": 314, "탄수화물_g": 68.8} },
  { "food_id": 5678, "food_name": "된장찌개",
    "amount_g": 300,
    "nutrients": {"에너지_kcal": 87, "나트륨_mg": 1620} }
]
```

### 8.3 영양제 복용 기록 테이블

```
┌─────────────────────────────────────────────────────────────┐
│  테이블: user_supplements (복용 중인 영양제 등록)            │
├──────────────────┬──────────────┬─────────────────────────┤
│ user_id          │ INTEGER      │ users 참조 (FK)         │
│ supplement_id    │ INTEGER      │ supplements 참조 (FK)   │
│ dose_amount      │ NUMERIC      │ 1회 복용량              │
│ dose_unit        │ VARCHAR(20)  │ 정 / mg / ml            │
│ frequency        │ VARCHAR(50)  │ daily / weekly          │
│ times_per_day    │ INTEGER      │ 하루 몇 번              │
│ take_times       │ JSONB        │ 복용 시각 ["08:00"]     │
│ started_at       │ DATE         │ 복용 시작일             │
│ ended_at         │ DATE         │ 복용 종료일 (NULL=현재) │
└──────────────────┴──────────────┴─────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  테이블: supplement_intake_logs (실제 복용 기록)             │
│  "오늘 실제로 먹었다" 기록. 응모권 카운트에도 사용          │
├──────────────────┬──────────────┬─────────────────────────┤
│ user_id          │ INTEGER      │ users 참조 (FK)         │
│ supplement_id    │ INTEGER      │ supplements 참조 (FK)   │
│ taken_at         │ TIMESTAMP    │ 복용 일시               │
│ photo_url        │ TEXT         │ 라벨 사진 URL (선택)    │
└──────────────────┴──────────────┴─────────────────────────┘
```

### 8.4 분석 결과 저장

```
┌─────────────────────────────────────────────────────────────┐
│  테이블: diagnoses (끼니별 AI 분석 결과)                     │
├──────────────────┬──────────────┬─────────────────────────┤
│ user_id          │ INTEGER      │ users 참조 (FK)         │
│ meal_id          │ INTEGER      │ meals 참조 (FK)         │
│ analyzed_at      │ TIMESTAMP    │ 분석 수행 시각          │
│ deficiencies     │ JSONB        │ 부족 영양소 목록 (암호화)│
│ excesses         │ JSONB        │ 과다 영양소 목록        │
│ warnings         │ JSONB        │ 주의 성분 목록 (암호화) │
│ goal_analysis    │ JSONB        │ 목적별 분석 결과        │
│ score            │ INTEGER      │ 이 끼니 점수 (0-100)    │
└──────────────────┴──────────────┴─────────────────────────┘

deficiencies JSONB 예시:
[
  { "nutrient": "비타민D", "current_mcg": 2.1,
    "recommended_mcg": 15, "ratio": 0.14, "level": "DEFICIENT" },
  { "nutrient": "칼슘", "current_mg": 320,
    "recommended_mg": 800, "ratio": 0.40, "level": "LOW" }
]
```

---

## 9. 전체 테이블 구조

### 5.1 현재 구현된 테이블 (✅)

#### users — 회원 기본 정보

```
┌────────────────────────────────────────────────────────┐
│  테이블명: users                                        │
│  설명: 회원가입 시 생성. 앱의 모든 데이터의 기준점.    │
├───────────────┬──────────────┬────────────────────────┤
│ 컬럼명        │ 타입         │ 설명                   │
├───────────────┼──────────────┼────────────────────────┤
│ id            │ SERIAL(정수) │ 자동증가 고유번호 (PK) │
│ email         │ VARCHAR(255) │ 이메일, 중복 불가      │
│ password_hash │ TEXT         │ bcrypt 암호화된 비번   │
│ display_name  │ VARCHAR(100) │ 닉네임 (선택)          │
│ email_verified│ TIMESTAMP    │ 이메일 인증 완료 시각  │
│ created_at    │ TIMESTAMP    │ 가입일시 (자동기록)    │
│ last_login_at │ TIMESTAMP    │ 마지막 로그인 시각     │
│ deleted_at    │ TIMESTAMP    │ 탈퇴일시 (NULL=활성)   │
└───────────────┴──────────────┴────────────────────────┘

실제 데이터 예시:
  id=1, email="kim@test.com", display_name="김건강",
  created_at="2026-05-12 09:00:00", deleted_at=NULL
```

#### profiles — 건강 프로필

```
┌────────────────────────────────────────────────────────┐
│  테이블명: profiles                                     │
│  설명: 온보딩에서 입력하는 건강 정보. users와 1:1 관계 │
├───────────────┬──────────────┬────────────────────────┤
│ 컬럼명        │ 타입         │ 설명                   │
├───────────────┼──────────────┼────────────────────────┤
│ id            │ SERIAL       │ 고유번호 (PK)          │
│ user_id       │ INTEGER      │ users 테이블 참조 (FK) │
│ age           │ INTEGER      │ 나이                   │
│ gender        │ VARCHAR(1)   │ 'M' 또는 'F'           │
│ height_cm     │ NUMERIC(5,2) │ 키 (예: 178.50)        │
│ weight_kg     │ NUMERIC(5,2) │ 체중 (예: 84.00)       │
│ chronic_dis.. │ JSONB        │ 만성질환 목록 (암호화 예정) │
│ medications   │ JSONB        │ 복약 정보 (암호화 예정) │
│ goals         │ JSONB        │ 건강 목표 목록         │
│ created_at    │ TIMESTAMP    │ 최초 입력일            │
│ updated_at    │ TIMESTAMP    │ 마지막 수정일          │
└───────────────┴──────────────┴────────────────────────┘

실제 데이터 예시:
  user_id=1, age=52, gender="M", height_cm=178.0, weight_kg=84.0,
  chronic_diseases=["고혈압", "당뇨전단계"],
  medications=["혈압약 1종"],
  goals=["체중감량", "혈압관리"]
```

#### refresh_tokens — 로그인 토큰 관리

```
┌────────────────────────────────────────────────────────┐
│  테이블명: refresh_tokens                               │
│  설명: 로그인 상태 유지용 토큰. 로그아웃 시 무효화.    │
├───────────────┬──────────────┬────────────────────────┤
│ 컬럼명        │ 타입         │ 설명                   │
├───────────────┼──────────────┼────────────────────────┤
│ id            │ SERIAL       │ 고유번호 (PK)          │
│ user_id       │ INTEGER      │ 어느 사용자 토큰인지   │
│ token         │ TEXT         │ JWT 토큰 문자열        │
│ expires_at    │ TIMESTAMP    │ 만료 시각 (7일)        │
│ revoked       │ BOOLEAN      │ 로그아웃 여부          │
│ created_at    │ TIMESTAMP    │ 발급 시각              │
└───────────────┴──────────────┴────────────────────────┘
```

#### consents — 개인정보 동의 이력

```
┌────────────────────────────────────────────────────────┐
│  테이블명: consents                                     │
│  설명: 어떤 항목에 동의했는지 기록. 법적 의무사항.    │
├───────────────┬──────────────┬────────────────────────┤
│ 컬럼명        │ 타입         │ 설명                   │
├───────────────┼──────────────┼────────────────────────┤
│ id            │ SERIAL       │ 고유번호 (PK)          │
│ user_id       │ INTEGER      │ 어느 사용자인지        │
│ type          │ VARCHAR(50)  │ 동의 종류              │
│               │              │ 'privacy' 개인정보처리 │
│               │              │ 'ai_usage' AI 분석     │
│               │              │ 'health_data' 건강정보 │
│               │              │ 'notifications' 알림   │
│ accepted_at   │ TIMESTAMP    │ 동의 시각              │
│ revoked_at    │ TIMESTAMP    │ 동의 철회 시각         │
└───────────────┴──────────────┴────────────────────────┘
```

---

### 5.2 구현 예정 테이블

#### foods — 음식 영양소 DB

```
┌────────────────────────────────────────────────────────┐
│  테이블명: foods                                        │
│  설명: 식약처·농진청 데이터 약 3만 건 적재 예정        │
├───────────────┬──────────────┬────────────────────────┤
│ 컬럼명        │ 타입         │ 설명                   │
├───────────────┼──────────────┼────────────────────────┤
│ id            │ SERIAL       │ 고유번호               │
│ name_ko       │ VARCHAR      │ 음식명 (한국어)        │
│ name_en       │ VARCHAR      │ 음식명 (영어)          │
│ nutrients_100g│ JSONB        │ 100g당 영양소 (50종)   │
│ source        │ VARCHAR      │ '식약처' 또는 '농진청' │
└───────────────┴──────────────┴────────────────────────┘

JSONB 예시:
  nutrients_100g: {
    "칼로리": 157,    "탄수화물": 34.1,
    "단백질": 2.7,    "지방": 0.3,
    "나트륨": 1,      "식이섬유": 0.5
  }
```

#### supplements + supplement_ingredients — 영양제 DB

```
supplements (마스터)                supplement_ingredients (성분 상세)
┌──────────────────────┐           ┌──────────────────────────────┐
│ id                   │──1:N──→  │ supplement_id (FK)            │
│ product_name_ko      │           │ name_ko  (성분명 한국어)      │
│ product_name_en      │           │ name_en  (성분명 영어)        │
│ manufacturer (제조사)│           │ amount   (함량 숫자)          │
│ serving_size (1회량) │           │ unit     (mg / mcg / IU)      │
└──────────────────────┘           │ daily_value_pct (1일 권장%)   │
                                    └──────────────────────────────┘
예시:
  supplements:  id=1, product_name_ko="종합비타민A"
  ingredients:  supplement_id=1, name_ko="비타민C",
                amount=500, unit="mg", daily_value_pct=556
```

#### meals — 식단 기록

```
┌────────────────────────────────────────────────────────┐
│  테이블명: meals                                        │
│  설명: 사진 찍은 식사 기록. 1끼니 = 1행               │
├───────────────┬──────────────┬────────────────────────┤
│ user_id       │ INTEGER      │ 누구의 기록인지        │
│ date          │ DATE         │ 식사 날짜              │
│ meal_type     │ VARCHAR      │ breakfast/lunch/dinner │
│ foods         │ JSONB        │ 먹은 음식과 양 목록    │
│ photo_url     │ TEXT         │ 사진이 저장된 주소     │
└───────────────┴──────────────┴────────────────────────┘

foods JSONB 예시:
  [{"food_id": 123, "name": "공깃밥", "amount_g": 200},
   {"food_id": 456, "name": "된장찌개", "amount_g": 300}]
```

#### diagnoses — AI 분석 결과

```
┌────────────────────────────────────────────────────────┐
│  테이블명: diagnoses                                    │
│  설명: 4개 Agent가 분석한 결과. AES-256 암호화 적용    │
├───────────────┬──────────────┬────────────────────────┤
│ user_id       │ INTEGER      │ 누구의 분석인지        │
│ date          │ DATE         │ 분석 날짜              │
│ meal_type     │ VARCHAR      │ 어느 끼니 분석인지     │
│ deficiencies  │ JSONB (암호화)│ 부족 영양소 목록      │
│ excesses      │ JSONB        │ 과다 영양소 목록       │
│ warnings      │ JSONB (암호화)│ 주의 성분 목록        │
│ goal_analysis │ JSONB        │ 목적별 분석 결과       │
└───────────────┴──────────────┴────────────────────────┘
```

#### daily_scores — 하루 식단 점수

```
┌────────────────────────────────────────────────────────┐
│ user_id       │ 누구의 점수인지                        │
│ date          │ 어느 날의 점수인지                     │
│ score         │ 0~100 정수 점수                        │
│ breakdown     │ 항목별 점수 내역 (JSONB)               │
│ agent_comment │ AI가 작성한 오늘의 한마디              │
└───────────────────────────────────────────────────────┘
```

#### 건강 데이터 — TimescaleDB Hypertable

```
step_counts (걸음수)
┌───────────┬────────────────────┬──────┐
│ user_id   │ ts (타임스탬프)    │count │
├───────────┼────────────────────┼──────┤
│ 1         │ 2026-05-12 10:00   │ 2341 │
│ 1         │ 2026-05-12 11:00   │ 1823 │
│ 1         │ 2026-05-12 12:00   │  456 │
└───────────┴────────────────────┴──────┘
TimescaleDB가 날짜별로 자동 파티셔닝 → 조회 속도 40배 향상

동일한 구조: weight_logs (체중), heart_rate_samples (심박수)
```

---

## 10. 테이블 간의 관계

모든 데이터는 `users` 테이블을 중심으로 연결됩니다.
`user_id` 라는 번호가 **열쇠** 역할을 합니다.

```
                    ┌─────────────┐
                    │    users    │ ← 모든 것의 중심
                    │  (회원정보) │
                    └──────┬──────┘
                           │ user_id
          ┌────────────────┼────────────────────────┐
          │                │                        │
          ▼                ▼                        ▼
   ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐
   │   profiles   │ │   consents   │ │   refresh_tokens    │
   │  (건강정보)  │ │  (동의이력)  │ │   (로그인 토큰)     │
   └──────────────┘ └──────────────┘ └─────────────────────┘

          │ user_id
          ▼
   ┌──────────────┐      ┌──────────────────────┐
   │    meals     │      │   user_supplements   │
   │  (식단기록)  │      │   (영양제 복용기록)  │
   └──────┬───────┘      └──────────┬───────────┘
          │ food_id                  │ supplement_id
          ▼                          ▼
   ┌──────────────┐      ┌──────────────────────┐
   │    foods     │      │     supplements      │
   │ (음식 마스터)│      │   (영양제 마스터)    │
   └──────────────┘      └──────────┬───────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │ supplement_ingredients│
                          │  (영양제 성분 상세)  │
                          └──────────────────────┘

          │ user_id
          ▼
   ┌──────────────┐ ┌──────────────────┐ ┌──────────────┐
   │  diagnoses   │ │  daily_scores    │ │ agent_memory │
   │ (분석결과)   │ │   (식단점수)     │ │ (AI 기억)    │
   └──────────────┘ └──────────────────┘ └──────────────┘

          │ user_id (TimescaleDB)
          ▼
   ┌─────────────────────────────────────────┐
   │  step_counts / weight_logs / heart_rate │
   │       (시계열 건강 데이터)              │
   └─────────────────────────────────────────┘
```

### 관계 종류 설명

```
1:1 관계 (한 명에 하나)
  users ─── profiles
  사용자 한 명당 프로필 하나

1:N 관계 (한 명에 여러 개)
  users ─── meals          (식단 기록은 매일 여러 건)
  users ─── refresh_tokens (여러 기기에서 로그인 가능)
  supplements ─── supplement_ingredients

N:M 관계 (여러 개 대 여러 개)
  users ─── supplements    (user_supplements 중간 테이블로 연결)
  한 사람이 여러 영양제, 한 영양제를 여러 사람이 복용
```

---

## 11. 파일 구조와 역할

### 7.1 전체 파일 지도

```
backend/
│
├─ .env                    ← DB 비밀번호, JWT 키 등 민감 정보 (git에 올리지 않음)
├─ .env.example            ← .env 양식 (git에 공유)
├─ requirements.txt        ← 설치할 Python 패키지 목록
├─ alembic.ini             ← Alembic 설정
│
├─ alembic/
│   ├─ env.py              ← 마이그레이션 실행 설정
│   └─ versions/           ← 테이블 변경 이력 파일들
│
└─ src/
    ├─ main.py             ← [입구] FastAPI 앱 시작, 모든 요청의 첫 관문
    ├─ config.py           ← [설정] .env 파일 읽기
    │
    ├─ db/
    │   ├─ init.sql        ← [초기화] DB 첫 실행 시 테이블 생성 SQL
    │   ├─ base.py         ← [기반] 모든 테이블의 공통 설정 (Base, Mixin)
    │   └─ session.py      ← [연결] DB와 연결하는 통로, get_db() 함수
    │
    ├─ models/             ← [설계도] 테이블 구조를 Python으로 표현
    │   ├─ __init__.py     ← 모델 한 곳에서 불러오기
    │   ├─ user.py         ← users, refresh_tokens 테이블
    │   └─ profile.py      ← profiles, consents 테이블
    │
    ├─ schemas/            ← [검문소] 앱에서 오는 데이터 형식 검증
    │   ├─ auth.py         ← 회원가입·로그인 요청/응답 형식
    │   └─ profile.py      ← 프로필 저장/조회 형식
    │
    ├─ api/                ← [처리실] 실제 요청을 처리하는 함수들
    │   ├─ __init__.py     ← 라우터 등록
    │   ├─ auth.py         ← 회원가입·로그인·로그아웃 처리
    │   └─ profile.py      ← 프로필 조회·저장 처리
    │
    └─ utils/              ← [도구함] 여러 곳에서 공통으로 쓰는 기능
        ├─ security.py     ← 비밀번호 암호화, JWT 토큰 생성/검증
        └─ deps.py         ← 로그인 여부 확인 (get_current_user)
```

### 7.2 각 파일의 역할 상세

#### `config.py` — 설정 읽기

```python
# .env 파일에서 값을 읽어 다른 파일들이 쓸 수 있게 제공
settings.database_url  # PostgreSQL 접속 주소
settings.jwt_secret    # JWT 암호화 키
```

#### `db/base.py` — 모든 테이블의 공통 틀

```python
class Base(DeclarativeBase):
    pass  # 모든 테이블이 이걸 상속받음

class TimestampMixin:
    created_at  # 생성일시 자동 기록
    updated_at  # 수정일시 자동 기록
    # 모든 테이블에서 공통으로 쓰는 항목
```

#### `db/session.py` — DB 연결 통로

```python
# DB와 연결하는 문(세션)을 열고 닫는 역할
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session  # API 함수에 DB 연결 제공
        await session.commit()  # 성공하면 저장
        # 실패하면 rollback (되돌리기)
```

#### `models/user.py` — 테이블 설계도

```python
class User(Base, TimestampMixin):
    __tablename__ = "users"  # PostgreSQL의 users 테이블과 연결

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    # Python 코드로 테이블 구조 표현
```

#### `utils/security.py` — 보안 도구

```python
hash_password("1234")        # "1234" → "$2b$12$xyz..." (암호화)
verify_password("1234", hash) # 비밀번호 일치 확인
create_access_token(user_id)  # 로그인 증명서(JWT) 발급
decode_token(token)           # 증명서 해석
```

#### `utils/deps.py` — 로그인 확인

```python
# API 호출 시 "이 사람 로그인한 사람 맞아?" 자동 확인
async def get_current_user(credentials, db):
    # Authorization: Bearer eyJ... 헤더에서 토큰 추출
    # 토큰 해석 → user_id 추출 → DB에서 사용자 조회
    return user  # 맞으면 사용자 정보 반환, 아니면 401 에러
```

---

## 12. 요청부터 저장까지 — 전체 흐름

### 8.1 회원가입 흐름

```
[Flutter 앱]
    │
    │  POST /api/v1/auth/signup
    │  Body: {
    │    "email": "kim@test.com",
    │    "password": "mypass123",
    │    "display_name": "김건강"
    │  }
    ▼
[main.py]  → 요청 수신
    ▼
[api/__init__.py]  → /auth 경로는 auth.py로 보냄
    ▼
[api/auth.py - signup()]
    │
    ├─① [schemas/auth.py]
    │      SignupRequest 검증
    │      - 이메일 형식 맞아? (@, 도메인 있어?)
    │      - 비밀번호 8자 이상?
    │      - 형식 틀리면 → 422 에러 반환
    │
    ├─② [db/session.py - get_db()]
    │      PostgreSQL 연결
    │
    ├─③ [models/user.py - User]
    │      users 테이블에서 이메일 중복 조회
    │      SELECT * FROM users WHERE email = 'kim@test.com'
    │      - 이미 있으면 → 400 에러 반환
    │
    ├─④ [utils/security.py - hash_password()]
    │      "mypass123" → "$2b$12$randomsalt..." 암호화
    │
    └─⑤ [PostgreSQL - users 테이블]
           INSERT INTO users (email, password_hash, display_name)
           VALUES ('kim@test.com', '$2b$12$...', '김건강')
           ↓
           성공 → 201 Created 응답
```

### 8.2 로그인 흐름

```
[Flutter 앱]
    │
    │  POST /api/v1/auth/login
    │  Body: {"email": "kim@test.com", "password": "mypass123"}
    ▼
[api/auth.py - login()]
    │
    ├─① users 테이블에서 이메일로 사용자 조회
    │
    ├─② verify_password("mypass123", "$2b$12$...")
    │      - 불일치 → 401 에러
    │
    ├─③ create_access_token(user_id=1)
    │      → "eyJhbGciOiJIUzI1NiJ9..." (30분 유효)
    │
    ├─④ create_refresh_token(user_id=1)
    │      → "eyJhbGciOiJIUzI1NiJ9..." (7일 유효)
    │      refresh_tokens 테이블에 저장
    │
    └─⑤ 응답:
           {
             "access_token": "eyJ...",
             "refresh_token": "eyJ...",
             "token_type": "bearer"
           }
```

### 8.3 프로필 저장 흐름

```
[Flutter 앱]  ← 로그인 후 온보딩 화면에서
    │
    │  PUT /api/v1/profile
    │  Headers: { Authorization: "Bearer eyJ..." }
    │  Body: {
    │    "age": 52,
    │    "gender": "M",
    │    "height_cm": 178.0,
    │    "weight_kg": 84.0,
    │    "chronic_diseases": ["고혈압", "당뇨전단계"],
    │    "medications": ["암로디핀 5mg"],
    │    "goals": ["체중감량", "혈압관리"]
    │  }
    ▼
[api/profile.py - update_profile()]
    │
    ├─① [utils/deps.py - get_current_user()]
    │      "Bearer eyJ..." 토큰 추출
    │      → decode_token() → user_id=1 추출
    │      → users 테이블에서 id=1 조회
    │      → 삭제된 계정이면 401 에러
    │
    ├─② [schemas/profile.py - ProfileUpdate]
    │      나이가 음수? 키가 0? → 422 에러
    │
    ├─③ profiles 테이블 조회
    │      SELECT * FROM profiles WHERE user_id = 1
    │      - 없으면: 새로 생성
    │      - 있으면: 기존 것 수정
    │
    └─④ [PostgreSQL - profiles 테이블]
           INSERT 또는 UPDATE
           ↓
           저장된 프로필 반환 (200 OK)
```

---

## 13. 보안 처리 방식

### 9.1 비밀번호 — bcrypt 해싱

비밀번호는 **절대 원문으로 저장하지 않습니다.** bcrypt 알고리즘으로 복호화가 불가능한 해시값으로 변환합니다.

```
사용자 입력: "mypassword123"
DB 저장:    "$2b$12$K8RP5G2n7RxJMEqM3qPO.u..."

"$2b$" → bcrypt 알고리즘
"12"   → 연산 복잡도 (높을수록 안전, 느림)
"K8RP..." → 랜덤 소금값(salt) + 해시

특징:
  - DB가 털려도 원래 비밀번호를 알 수 없음
  - 같은 비밀번호도 매번 다른 해시값 생성 (소금 덕분)
  - 로그인 시 verify_password()로 일치 여부만 확인
```

### 9.2 JWT 토큰 — 신분증 시스템

로그인 후 매번 비밀번호를 보내는 것은 위험합니다. 대신 **임시 신분증(JWT 토큰)** 을 발급합니다.

```
JWT 토큰 구조:
eyJhbGciOiJIUzI1NiJ9  ←  Header (알고리즘 정보)
.
eyJzdWIiOiIxIiwiZXhwIjoxNjE2MjM5MDIyfQ  ←  Payload (user_id, 만료시간)
.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c  ←  Signature (위변조 방지)

3개 파트가 점(.)으로 연결된 문자열
```

| 토큰 | 유효시간 | 용도 |
|------|---------|------|
| access_token | 30분 | 모든 API 호출 시 첨부, 짧아서 유출돼도 피해 최소화 |
| refresh_token | 7일 | access_token 만료 시 재발급용, DB에 저장 |

```
토큰 사용 흐름:
  로그인 → access + refresh 발급
  API 호출 시 → Authorization: Bearer {access_token}
  30분 후 access 만료 → refresh로 새 access 발급
  7일 후 refresh 만료 → 재로그인 필요
  로그아웃 → DB의 refresh_token revoked=true로 변경
```

### 9.3 민감정보 — AES-256 암호화 (예정)

만성질환, 복약정보는 의료법상 민감정보입니다. 현재는 JSONB로 저장 중이며, 추후 AES-256-GCM으로 암호화 예정입니다.

```
AES-256이란?
  - 은행·군사 시스템에서 사용하는 암호화
  - 256bit 키로 암호화 → 현재 컴퓨터로 수십억 년이 걸려야 해독 가능
  - PostgreSQL DB가 털려도 암호화 키 없이는 해독 불가
```

---

## 14. SQLAlchemy — Python과 DB를 연결하는 다리

### 10.1 왜 SQLAlchemy를 쓰나?

SQL을 직접 쓰면 이렇게 됩니다:

```python
# SQL 직접 작성 (문자열 오류 위험, SQL Injection 위험)
query = f"SELECT * FROM users WHERE email = '{email}'"
```

SQLAlchemy(ORM)를 쓰면:

```python
# Python 문법으로 작성 (타입 체크, 보안 자동 처리)
user = await db.scalar(select(User).where(User.email == email))
```

### 10.2 ORM이란?

ORM(Object-Relational Mapping)은 **DB 테이블을 Python 클래스로 표현**하는 방식입니다.

```
PostgreSQL 테이블          Python 클래스
users 테이블       ←→    class User
한 행(row)         ←→    user = User(email="...", ...)
INSERT             ←→    db.add(user)
UPDATE             ←→    user.display_name = "새이름"
DELETE             ←→    await db.delete(user)
SELECT             ←→    select(User).where(...)
```

---

## 15. Alembic — 테이블 변경 이력 관리

### 11.1 왜 필요한가?

개발 중에 테이블 구조가 바뀔 때마다 "나는 컬럼 추가했는데 다른 팀원 DB에는 없어서 오류남" 상황이 생깁니다. Alembic은 이런 변경을 **버전으로 관리**합니다.

```
Git이 코드 변경을 관리하듯, Alembic은 테이블 변경을 관리
```

### 11.2 사용 방법

```bash
# 1. 모델(Python 코드) 변경 후 마이그레이션 파일 자동 생성
alembic revision --autogenerate -m "add profile table"
# → alembic/versions/xxxx_add_profile_table.py 생성

# 2. 변경 적용 (팀원 모두 이 명령어 한 번)
alembic upgrade head

# 3. 이전 버전으로 되돌리기 (문제 생겼을 때)
alembic downgrade -1
```

---

## 16. 현재 구현된 API 전체 목록

`http://localhost:8000/docs` 에서 Swagger UI로 테스트 가능합니다.

| 경로 | 메서드 | 기능 | 인증 필요 |
|------|--------|------|-----------|
| `/api/v1/auth/signup` | POST | 회원가입 | ❌ |
| `/api/v1/auth/login` | POST | 로그인 → JWT 발급 | ❌ |
| `/api/v1/auth/refresh` | POST | access 토큰 갱신 | ❌ |
| `/api/v1/auth/logout` | POST | 로그아웃 | ❌ |
| `/api/v1/profile` | GET | 내 프로필 조회 | ✅ Bearer |
| `/api/v1/profile` | PUT | 내 프로필 저장/수정 | ✅ Bearer |

### Swagger에서 테스트하는 방법

```
1. http://localhost:8000/docs 접속
2. POST /auth/signup → 계정 생성
3. POST /auth/login → access_token 복사
4. 화면 우상단 [Authorize] 클릭 → "Bearer {토큰}" 입력
5. GET /profile → 내 프로필 조회
6. PUT /profile → 나이, 키, 체중 등 저장
```

---

## 17. 로컬 실행 순서

### 13.1 처음 시작할 때 (최초 1회)

```bash
# 1. Docker 설치 (https://docs.docker.com/get-docker/)

# 2. DB + Redis 컨테이너 실행
docker-compose up -d

# 3. 컨테이너 정상 실행 확인
docker ps
# lemon_aid_db, lemon_aid_redis 두 개가 보여야 함

# 4. 환경변수 파일 생성
cp backend/.env.example backend/.env
# .env 파일 열어서 필요한 값 확인 (기본값으로도 실행 가능)

# 5. Python 패키지 설치
cd backend
pip install -r requirements.txt

# 6. 마이그레이션 실행 (테이블 생성)
alembic upgrade head

# 7. 서버 실행
uvicorn src.main:app --reload --app-dir src
```

### 13.2 이후 매번 개발할 때

```bash
docker-compose up -d          # DB 실행 (꺼져 있을 때)
uvicorn src.main:app --reload  # 서버 실행
```

---

## 18. 자주 하는 실수와 해결법

| 오류 메시지 | 원인 | 해결 |
|-------------|------|------|
| `Connection refused` | Docker DB가 안 켜져 있음 | `docker-compose up -d` |
| `relation does not exist` | 마이그레이션 안 함 | `alembic upgrade head` |
| `401 Unauthorized` | 토큰 없거나 만료됨 | 재로그인 → 새 토큰 발급 |
| `422 Unprocessable` | 요청 데이터 형식 오류 | 요청 Body 확인 |
| `duplicate key value` | 이미 가입된 이메일 | 다른 이메일로 시도 |
| `ModuleNotFoundError` | pip install 안 함 | `pip install -r requirements.txt` |

---

## 19. 다음 구현 예정 항목

| 순서 | 항목 | 필요한 테이블 | 데이터 출처 |
|------|------|-------------|------------|
| 1 | 음식 데이터 적재 | `foods` | 식약처 Open API (공공데이터포털) |
| 2 | 영양제 데이터 적재 | `supplements`, `supplement_ingredients` | 식약처 건강기능식품 DB |
| 3 | KDRIs 데이터 적재 | `data/kdris_2020.csv` | 한국영양학회 2020 |
| 4 | 식단 기록 저장 | `meals` | 사용자 입력 + OCR |
| 5 | 영양제 복용 기록 | `user_supplements` | 사용자 입력 |
| 6 | 분석 결과 저장 | `diagnoses`, `daily_scores` | AI Agent |
| 7 | 건강 데이터 수집 | `step_counts`, `weight_logs` | HealthKit / Health Connect |
| 8 | AES-256 암호화 | `profiles` (만성질환, 복약) | 내부 구현 |
| 9 | 이메일 인증 | `email_verifications` | SMTP / AWS SES |
