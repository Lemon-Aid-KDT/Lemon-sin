# Lemon Aid — 데이터베이스 완전 가이드

> 비전공자도 처음부터 끝까지 이해할 수 있도록 작성한 DB 구조 설명서
> 담당: D (백엔드) · 작성일: 2026-05-12 · v4.0

---

## 목차

1. [데이터베이스란 무엇인가?](#1-데이터베이스란-무엇인가)
2. [왜 PostgreSQL인가?](#2-왜-postgresql인가)
3. [왜 Docker로 실행하는가?](#3-왜-docker로-실행하는가)
4. [왜 Redis도 같이 쓰는가?](#4-왜-redis도-같이-쓰는가)
5. [외부 데이터 소스 3종](#5-외부-데이터-소스-3종)
6. [전체 데이터 구조 설계](#6-전체-데이터-구조-설계)
7. [병원 데이터 + 사용자 데이터 연결](#7-병원-데이터--사용자-데이터-연결)
8. [음식·영양제 섭취 기록 구조](#8-음식영양제-섭취-기록-구조)
9. [전체 테이블 구조](#9-전체-테이블-구조)
10. [테이블 간의 관계](#10-테이블-간의-관계)
11. [파일 구조와 역할](#11-파일-구조와-역할)
12. [요청부터 저장까지 전체 흐름](#12-요청부터-저장까지-전체-흐름)
13. [보안 처리 방식](#13-보안-처리-방식)
14. [SQLAlchemy란?](#14-sqlalchemy란)
15. [Alembic이란?](#15-alembic이란)
16. [현재 구현된 API 목록](#16-현재-구현된-api-목록)
17. [로컬 실행 순서](#17-로컬-실행-순서)
18. [자주 하는 실수와 해결법](#18-자주-하는-실수와-해결법)
19. [다음 구현 예정 항목](#19-다음-구현-예정-항목)

---

## 1. 데이터베이스란 무엇인가?

앱을 껐다 켜도 내 정보가 그대로 있는 이유는 **데이터베이스(DB)** 가 정보를 보관하기 때문입니다.

가장 쉬운 비유는 **도서관**입니다.

| 도서관 | 데이터베이스 |
|--------|-------------|
| 도서관 건물 전체 | 데이터베이스 |
| 서가(책장) | 테이블 (users, meals, supplements ...) |
| 책 한 권 | 행(row) — 사용자 한 명의 정보 |
| 책의 항목(제목·저자·출판일) | 열(column) — 이름, 이메일, 나이 |
| 사서 | PostgreSQL (DB 관리 시스템) |
| 대출 규칙 | 제약 조건 (이메일 중복 불가 등) |

**Excel과 비교하면:**

| Excel | 데이터베이스 |
|-------|-------------|
| 파일(.xlsx) | 데이터베이스 |
| 시트(탭) | 테이블 |
| 행 | 레코드(record) |
| 열 | 컬럼(column) |
| 셀 서식 | 데이터 타입 (숫자, 문자, 날짜) |
| 시트 간 참조(=Sheet1!A1) | 외래키(Foreign Key) |

Excel은 동시 접속이 안 되고 수백만 행이 되면 느려집니다. DB는 수만 명이 동시에 접속해도 안전하고, 수억 건도 빠르게 처리합니다.

---

## 2. 왜 PostgreSQL인가?

### Oracle 대신 쓰는 이유

레몬헬스케어 실무에서는 Oracle을 사용하지만, 이 프로젝트에서 Oracle을 쓰지 않는 이유는 비용입니다.

| 항목 | Oracle | Oracle Free | PostgreSQL |
|------|--------|-------------|------------|
| 비용 | CPU당 수백만 원/년 | 무료 | 무료 |
| RAM 제한 | 없음 | 2GB | 없음 |
| CPU 제한 | 없음 | 2코어 | 없음 |
| Oracle 문법과 유사도 | 기준 | 동일 | 높음 |

Oracle Free는 2GB RAM 제한이 있어 OCR + LLM + 시계열 DB를 동시에 돌리기 어렵습니다.

### MySQL 대신 쓰는 이유

| 필요한 기능 | MySQL | PostgreSQL |
|------------|-------|------------|
| JSON 유연 저장 (JSONB) | 제한적 | 완벽 지원 |
| 시계열 확장 (TimescaleDB) | 없음 | 지원 |
| 행 단위 보안 (RLS) | 없음 | 지원 |
| 전문 검색 | 약함 | 강함 |
| Oracle 문법 유사도 | 낮음 | 높음 |

### PostgreSQL을 선택한 핵심 이유 3가지

**① JSONB — 영양제 성분표를 유연하게 저장**

영양제 제품마다 성분 개수가 다릅니다. 비타민C 하나짜리도 있고 30가지짜리도 있습니다. 고정 열로 만들면 대부분이 빈칸이 되지만, JSONB는 있는 것만 저장합니다.

```json
{
  "비타민C": {"amount": 500, "unit": "mg"},
  "비타민D": {"amount": 1000, "unit": "IU"},
  "오메가3": {"amount": 1, "unit": "g"}
}
```

**② TimescaleDB — 걸음수·심박수 시계열 처리**

사용자 1,000명이 매 분 걸음수를 기록하면 하루 144만 건입니다. TimescaleDB 확장을 추가하면 최근 30일 조회가 일반 DB 대비 40배 빨라집니다. PostgreSQL 위에 얹는 무료 플러그인입니다.

**③ RLS — 내 데이터는 나만 볼 수 있다**

PostgreSQL의 Row Level Security는 DB 차원에서 "본인 데이터만 조회 가능"을 강제합니다. 코드에서 실수해도 DB가 막아줍니다.

---

## 3. 왜 Docker로 실행하는가?

직접 설치하면 팀원마다 OS가 다르고 버전이 달라서 "내 컴에서는 되는데요" 문제가 생깁니다. Docker는 **미리 만들어진 환경 상자(컨테이너)** 를 실행하므로 누구 컴퓨터에서든 동일합니다.

```bash
docker-compose up -d   # 이 명령어 하나로 DB + Redis 동시 실행
```

우리가 실행하는 컨테이너:

| 컨테이너 | 내용 | 포트 |
|---------|------|------|
| lemon_aid_db | PostgreSQL 16 + TimescaleDB | 5432 |
| lemon_aid_redis | Redis 7 | 6379 |

---

## 4. 왜 Redis도 같이 쓰는가?

PostgreSQL이 **도서관(영구 저장)** 이라면, Redis는 **포스트잇(빠른 임시 저장)** 입니다.

| 용도 | 설명 | 효과 |
|------|------|------|
| OCR 결과 캐시 | 같은 영양제 사진은 재분석 안 함 (SHA-256 키, TTL 30일) | API 비용 50% 절감 |
| KDRIs 룩업 캐시 | 영양소 권장량은 자주 읽히지만 거의 안 바뀜 | DB 부하 감소 |
| API Rate Limit | 사용자당 분당 5회, 일당 50회 제한 | LLM 비용 과다 방지 |

---

## 5. 외부 데이터 소스 3종

### 5.1 AI Hub — 한국 음식 이미지 데이터셋

- **출처:** https://aihub.or.kr (데이터셋 번호 79)
- **용도:** 음식 사진 촬영 시 음식 이름 자동 인식 보조
- **규모:** 150종 × 약 1,000장 = 총 150,000장

**제공 데이터 항목:**

| 항목 | 설명 |
|------|------|
| food_id | 음식 고유 코드 (예: F001) |
| food_name_ko | 음식명 한국어 (예: 된장찌개) |
| food_name_en | 음식명 영어 (예: Doenjang Jjigae) |
| category_main | 대분류 (밥류 / 면류 / 국류 / 구이류) |
| category_sub | 소분류 (찌개 / 국 / 탕) |
| 이미지 파일 | .jpg 형식, 음식코드_번호.jpg |

**우리 DB로 가져오는 방식:**

| AI Hub 항목 | 저장 위치 |
|------------|---------|
| food_name_ko | foods.name_ko |
| food_name_en | foods.name_en |
| category_main | food_categories.name (대분류) |
| category_sub | food_categories (소분류, parent_id 참조) |
| 이미지 파일 | S3/NCP Object Storage → URL만 foods.image_url에 저장 |

> 이미지 자체는 DB에 넣지 않습니다. DB에 이미지를 넣으면 용량이 폭발적으로 커지기 때문에 파일 저장소(Object Storage)에 올리고 주소(URL)만 DB에 기록합니다.

---

### 5.2 식약처 식품영양정보 표준DB

- **출처:** https://data.mfds.go.kr
- **용도:** 음식별 정확한 영양소 수치 (100g당 칼로리, 단백질 등)
- **규모:** 가공식품·외식메뉴·건강기능식품 포함 수만 건

**제공 데이터 항목:**

| 항목 | 설명 |
|------|------|
| 식품코드 | 고유 식별 코드 (예: D000001) |
| 대표식품명 | 음식 이름 |
| 제조사명 | 제조·판매 회사 |
| 식품유형 | 가공식품 / 건강기능식품 / 외식 / 원재료 |
| 1회 제공량(g) | 1인분 기준 무게 |
| 에너지(kcal) | 칼로리 |
| 탄수화물(g) | — |
| 단백질(g) | — |
| 지방(g) | — |
| 나트륨(mg) | — |
| 당류(g) | — |
| 식이섬유(g) | — |
| 콜레스테롤(mg) | — |

**우리 DB로 가져오는 방식:**

| 식약처 항목 | 저장 위치 |
|-----------|---------|
| 식품코드 | foods.source_code |
| 대표식품명 | foods.name_ko |
| 제조사명 | foods.manufacturer |
| 식품유형 | foods.food_type |
| 영양성분 전체 | foods.nutrients_per_100g (JSONB, 한 컬럼에 모두 저장) |

---

### 5.3 식품안전나라 영양정보 DB

- **출처:** https://various.foodsafetykorea.go.kr/nutrient
- **용도:** 비타민·미네랄·아미노산 등 50종 이상 세부 영양소

**제공 영양소 카테고리:**

| 카테고리 | 항목 수 | 예시 |
|---------|---------|------|
| 일반성분 | 7종 | 에너지, 탄수화물, 단백질, 지방, 수분 |
| 수용성 비타민 | 8종 | B1, B2, B3(나이아신), B6, B9(엽산), B12 |
| 지용성 비타민 | 4종 | A, D, E, K |
| 무기질 | 9종 | 칼슘, 인, 나트륨, 칼륨, 마그네슘, 철, 아연 |
| 아미노산 | 18종 | 필수 9종 + 비필수 9종 |
| 지방산 | 여러 종 | 포화, 단불포화, 다불포화, 오메가3, 오메가6 |
| 당류 | 5종 | 포도당, 과당, 갈락토스, 자당, 유당 |

이 모든 수치는 `foods.nutrients_per_100g` JSONB 컬럼 하나에 통합 저장됩니다.

---

## 6. 전체 데이터 구조 설계

이 프로젝트의 데이터는 4가지 출처에서 들어옵니다.

| 출처 | 종류 | 저장 테이블 |
|------|------|-----------|
| 공공 DB (식약처 등) | 음식 영양소, 영양제 성분, AI 분류 | foods, supplements |
| 병원 데이터 (Kaggle/LDB) | 진단명, 검사값, 처방약, 방문 이력 | hospital_records, lab_results |
| 사용자 직접 입력 | 나이·키·체중·만성질환·식단·영양제 기록 | profiles, meals, user_supplements |
| 기기 데이터 (HealthKit) | 걸음수, 심박수, 체중 | step_counts, heart_rate_samples, weight_logs |

---

### 6.1 음식 분류 테이블

**food_categories** — AI Hub 분류 기준으로 대·소분류 체계 구성

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | 정수 (자동증가) | 고유번호 |
| name | 문자(100) | 분류명 (예: 밥류, 된장찌개) |
| parent_id | 정수 | 상위 분류 번호 (최상위면 비어 있음) |
| level | 정수 | 1 = 대분류, 2 = 소분류 |

예시 데이터:

| id | name | parent_id | level |
|----|------|-----------|-------|
| 1 | 밥류 | (없음) | 1 |
| 2 | 볶음밥 | 1 | 2 |
| 3 | 비빔밥 | 1 | 2 |
| 4 | 국·찌개류 | (없음) | 1 |
| 5 | 된장찌개 | 4 | 2 |

---

### 6.2 음식 마스터 테이블

**foods** — 식약처 + 식품안전나라 + AI Hub 통합

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | 정수 | 고유번호 |
| source_code | 문자(50) | 식약처 원본 코드 |
| name_ko | 문자(200) | 음식명 한국어 |
| name_en | 문자(200) | 음식명 영어 |
| category_id | 정수 | food_categories 참조 |
| food_type | 문자(50) | 가공식품 / 외식 / 원재료 |
| manufacturer | 문자(200) | 제조사 (없으면 빈칸) |
| serving_size_g | 소수 | 1회 제공량(g) |
| nutrients_per_100g | JSONB | 100g당 영양소 50종 전체 |
| image_url | 텍스트 | 대표 이미지 URL |
| source | 문자(50) | 식약처 / 농진청 / AI Hub |

---

### 6.3 영양제 마스터 테이블

**supplements** — 식약처 건강기능식품 원료 DB

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | 정수 | 고유번호 |
| source_code | 문자(50) | 식약처 원료 코드 |
| product_name_ko | 문자(300) | 제품명 한국어 |
| product_name_en | 문자(300) | 제품명 영어 |
| manufacturer | 문자(200) | 제조사 |
| supplement_type | 문자(100) | 비타민 / 미네랄 / 오메가3 등 |
| serving_size | 문자(100) | 1회 섭취량 표기 |
| functionality | 텍스트 | 식약처 인정 기능성 내용 |
| warnings | 텍스트 | 섭취 주의사항 |

**supplement_ingredients** — 영양제 성분 상세 (한 제품에 여러 성분)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | 정수 | 고유번호 |
| supplement_id | 정수 | supplements 참조 |
| name_ko | 문자(200) | 성분명 한국어 |
| name_en | 문자(200) | 성분명 영어 |
| amount | 소수 | 함량 수치 |
| unit | 문자(20) | mg / mcg / IU / g |
| daily_value_pct | 소수 | 1일 권장량 대비 % |
| upper_limit | 소수 | 상한섭취량 (UL) |

예시 — 종합비타민A 제품:

| 성분명 | 함량 | 단위 | 1일 권장% |
|--------|------|------|---------|
| 비타민C | 500 | mg | 556% |
| 비타민D | 1000 | IU | 250% |
| 비타민B12 | 2.4 | mcg | 100% |

---

## 7. 병원 데이터 + 사용자 데이터 연결

### 7.1 왜 병원 데이터가 필요한가?

일반 영양제 앱은 사용자 입력만으로 일반인 기준 권장량을 안내합니다. Lemon Aid는 병원 검사값과 복약 정보까지 합쳐서 개인화된 권고를 합니다.

> 예: "당뇨가 있으니 탄수화물 주의", "혈압약과 오메가3 동시 복용 시 주의"

### 7.2 병원 방문 기록 테이블

**hospital_records** — MVP는 Kaggle 데이터, 실서비스는 LDB 연동

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | 정수 | 고유번호 |
| user_id | 정수 | users 참조 |
| visit_date | 날짜 | 진료 날짜 |
| hospital_name | 문자(200) | 병원명 |
| department | 문자(100) | 진료과 (내과, 순환기과 등) |
| diagnosis_codes | JSONB | 진단 코드 목록 (ICD-10 코드) |
| diagnosis_names | JSONB | 진단명 한국어 (암호화 예정) |
| source | 문자(50) | kaggle / ldb / manual |

### 7.3 검사 수치 테이블

**lab_results** — 혈당, 혈압, 콜레스테롤 등

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | 정수 | 고유번호 |
| user_id | 정수 | users 참조 |
| measured_at | 일시 | 검사 일시 |
| test_type | 문자(100) | 검사 종류 |
| value | 소수 | 수치 (암호화 예정) |
| unit | 문자(50) | mg/dL, mmHg 등 |
| reference_min | 소수 | 정상 최솟값 |
| reference_max | 소수 | 정상 최댓값 |
| is_abnormal | 참/거짓 | 정상 범위 초과 여부 |

검사 항목 예시:

| 검사 종류 | 수치 | 단위 | 정상 범위 | 정상 여부 |
|---------|------|------|---------|---------|
| 공복혈당 | 126 | mg/dL | 70~100 | 초과 |
| 수축기혈압 | 145 | mmHg | 90~120 | 초과 |
| 총콜레스테롤 | 220 | mg/dL | 0~200 | 초과 |
| HbA1c | 6.8 | % | 0~5.7 | 초과 |

### 7.4 Kaggle 데이터를 우리 DB로 가져오는 방법

| Kaggle 컬럼 | 우리 DB 저장 위치 |
|-----------|---------------|
| Age (나이) | profiles.age |
| Gender (성별) | profiles.gender |
| BMI | 키+체중으로 계산 |
| Hypertension (고혈압) | profiles.chronic_diseases 배열 |
| Diabetes (당뇨) | profiles.chronic_diseases 배열 |
| Heart Disease (심질환) | profiles.chronic_diseases 배열 |
| Blood Glucose Level | lab_results (test_type = 공복혈당) |
| HbA1c Level | lab_results (test_type = HbA1c) |

### 7.5 데이터 연결 흐름

1. **회원가입 + 온보딩** → users + profiles 테이블 생성 (이메일, 나이, 키, 체중, 만성질환, 복약)
2. **병원 데이터 연결** → hospital_records + lab_results 테이블 (user_id로 연결)
3. **AI Agent 해석** → profiles + lab_results를 합쳐서 개인화 기준 생성
4. **결과 저장** → agent_memory 테이블에 요약 저장 → 다음 분석 때 재활용

---

## 8. 음식·영양제 섭취 기록 구조

### 8.1 식단 기록 흐름

사진 촬영 → AI 분석 → 사용자 확인 → 저장의 순서로 진행됩니다. 저장 시 끼니 원본(meals)과 AI 분석 결과(diagnoses) 두 곳에 나눠서 저장합니다.

### 8.2 끼니 기록 테이블

**meals** — 사진 1장 = 한 끼니 = 1행

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | 정수 | 고유번호 |
| user_id | 정수 | users 참조 |
| eaten_at | 일시 | 식사 일시 |
| meal_type | 문자(20) | breakfast / lunch / dinner / snack |
| photo_url | 텍스트 | 사진 저장 URL |
| items | JSONB | 인식된 음식 목록 (음식명, 양, 영양소) |
| total_nutrients | JSONB | 이 끼니 총 영양소 합계 |
| is_confirmed | 참/거짓 | 사용자가 확인·수정했는지 여부 |

items JSONB 예시:

```json
[
  { "food_id": 1234, "food_name": "공깃밥", "amount_g": 200,
    "nutrients": { "에너지_kcal": 314, "탄수화물_g": 68.8 } },
  { "food_id": 5678, "food_name": "된장찌개", "amount_g": 300,
    "nutrients": { "에너지_kcal": 87, "나트륨_mg": 1620 } }
]
```

### 8.3 영양제 복용 기록 테이블

**user_supplements** — 복용 중인 영양제 등록

| 컬럼 | 타입 | 설명 |
|------|------|------|
| user_id | 정수 | users 참조 |
| supplement_id | 정수 | supplements 참조 |
| dose_amount | 소수 | 1회 복용량 |
| dose_unit | 문자(20) | 정 / mg / ml |
| frequency | 문자(50) | daily / weekly / as_needed |
| times_per_day | 정수 | 하루 몇 번 |
| take_times | JSONB | 복용 시각 예: ["08:00", "20:00"] |
| started_at | 날짜 | 복용 시작일 |
| ended_at | 날짜 | 복용 종료일 (없으면 현재 복용 중) |

**supplement_intake_logs** — 실제 복용 기록 (응모권 카운트용)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| user_id | 정수 | users 참조 |
| supplement_id | 정수 | supplements 참조 |
| taken_at | 일시 | 복용 일시 |
| photo_url | 텍스트 | 라벨 사진 URL (선택) |

### 8.4 AI 분석 결과 저장 테이블

**diagnoses** — 끼니별 AI 분석 결과

| 컬럼 | 타입 | 설명 |
|------|------|------|
| user_id | 정수 | users 참조 |
| meal_id | 정수 | meals 참조 |
| analyzed_at | 일시 | 분석 수행 시각 |
| deficiencies | JSONB | 부족 영양소 목록 (암호화 예정) |
| excesses | JSONB | 과다 영양소 목록 |
| warnings | JSONB | 주의 성분 목록 (암호화 예정) |
| goal_analysis | JSONB | 목적별 분석 결과 (눈/간/피로) |
| score | 정수 | 이 끼니 점수 (0~100) |

deficiencies 예시:

```json
[
  { "nutrient": "비타민D", "current": 2.1, "recommended": 15,
    "ratio": 0.14, "level": "결핍" },
  { "nutrient": "칼슘", "current": 320, "recommended": 800,
    "ratio": 0.40, "level": "낮음" }
]
```

---

## 9. 전체 테이블 구조

### 현재 구현된 테이블

**users** — 회원 기본 정보

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | 정수 (자동증가) | 고유번호 (PK) |
| email | 문자(255) | 이메일, 중복 불가 |
| password_hash | 텍스트 | bcrypt 암호화된 비밀번호 |
| display_name | 문자(100) | 닉네임 |
| email_verified_at | 일시 | 이메일 인증 완료 시각 |
| created_at | 일시 | 가입일시 (자동기록) |
| last_login_at | 일시 | 마지막 로그인 시각 |
| deleted_at | 일시 | 탈퇴일시 (없으면 활성 계정) |

**profiles** — 건강 프로필

| 컬럼 | 타입 | 설명 |
|------|------|------|
| user_id | 정수 | users 참조, 사용자당 1개 |
| age | 정수 | 나이 |
| gender | 문자(1) | M 또는 F |
| height_cm | 소수 | 키 (예: 178.5) |
| weight_kg | 소수 | 체중 (예: 84.0) |
| chronic_diseases | JSONB | 만성질환 목록 (암호화 예정) |
| medications | JSONB | 복약 정보 (암호화 예정) |
| goals | JSONB | 건강 목표 목록 |

**refresh_tokens** — 로그인 토큰 관리

| 컬럼 | 타입 | 설명 |
|------|------|------|
| user_id | 정수 | users 참조 |
| token | 텍스트 | JWT 토큰 문자열 |
| expires_at | 일시 | 만료 시각 (7일) |
| revoked | 참/거짓 | 로그아웃 여부 |

**consents** — 개인정보 동의 이력

| 컬럼 | 타입 | 설명 |
|------|------|------|
| user_id | 정수 | users 참조 |
| type | 문자(50) | privacy / ai_usage / health_data / notifications |
| accepted_at | 일시 | 동의 시각 |
| revoked_at | 일시 | 동의 철회 시각 |

### 구현 예정 테이블

| 테이블 | 설명 |
|--------|------|
| food_categories | 음식 대·소분류 체계 |
| foods | 음식 마스터 (식약처 + AI Hub) |
| supplements | 영양제 마스터 (식약처) |
| supplement_ingredients | 영양제 성분 상세 |
| hospital_records | 병원 방문 기록 |
| lab_results | 혈당·혈압 등 검사 수치 |
| meals | 끼니 기록 |
| user_supplements | 복용 중인 영양제 등록 |
| supplement_intake_logs | 실제 복용 기록 |
| diagnoses | AI 분석 결과 |
| daily_scores | 하루 식단 점수 |
| reminders | 복약·식단 알림 |
| calendar_events | 진료 일정 |
| raffle_tickets | 응모권 누적 |
| agent_memory | AI 요약 기억 |
| agent_runs | AI 호출 로그 |
| step_counts | 걸음수 (TimescaleDB) |
| weight_logs | 체중 기록 (TimescaleDB) |
| heart_rate_samples | 심박수 (TimescaleDB) |

---

## 10. 테이블 간의 관계

모든 데이터는 users 테이블을 중심으로 user_id로 연결됩니다.

**1:1 관계** (한 사용자 = 하나의 레코드)
- users → profiles (프로필은 사용자당 하나)

**1:N 관계** (한 사용자 = 여러 레코드)
- users → meals (식단 기록은 매일 여러 건)
- users → refresh_tokens (여러 기기 로그인 가능)
- users → hospital_records (병원 방문은 여러 번)
- users → lab_results (검사는 여러 번)
- users → step_counts, weight_logs, heart_rate_samples

**N:M 관계** (중간 테이블로 연결)
- users ↔ supplements → user_supplements (한 사람이 여러 영양제, 한 영양제를 여러 사람이 복용)

---

## 11. 파일 구조와 역할

```
backend/
├── .env                    환경변수 (DB 비밀번호, JWT 키 등. git에 올리지 않음)
├── .env.example            .env 양식 (git에 공유)
├── requirements.txt        설치할 Python 패키지 목록
├── alembic.ini             Alembic 설정
├── alembic/
│   ├── env.py              마이그레이션 실행 설정
│   └── versions/           테이블 변경 이력 파일들
└── src/
    ├── main.py             FastAPI 앱 시작점, 모든 요청의 첫 관문
    ├── config.py           .env 파일 읽기
    ├── db/
    │   ├── init.sql        DB 첫 실행 시 테이블 생성 SQL
    │   ├── base.py         모든 테이블의 공통 설정 (Base, Mixin)
    │   └── session.py      DB와 연결하는 통로, get_db() 함수
    ├── models/             테이블 구조를 Python으로 표현
    │   ├── user.py         users, refresh_tokens
    │   └── profile.py      profiles, consents
    ├── schemas/            앱에서 오는 데이터 형식 검증
    │   ├── auth.py         회원가입·로그인 요청/응답
    │   └── profile.py      프로필 저장/조회 형식
    ├── api/                실제 요청을 처리하는 함수들
    │   ├── auth.py         회원가입·로그인·로그아웃
    │   └── profile.py      프로필 조회·저장
    └── utils/
        ├── security.py     비밀번호 암호화, JWT 토큰 생성/검증
        └── deps.py         로그인 여부 확인 (get_current_user)
```

---

## 12. 요청부터 저장까지 전체 흐름

### 로그인 흐름

1. Flutter 앱이 이메일 + 비밀번호를 `POST /api/v1/auth/login`으로 전송
2. `main.py` → `api/__init__.py` → `api/auth.py`로 전달
3. `schemas/auth.py`가 이메일 형식, 필수값 검증
4. `db/session.py`로 DB 연결
5. `models/user.py`로 users 테이블에서 이메일 검색
6. `utils/security.py`로 비밀번호 일치 확인
7. JWT 토큰 2개 생성 (access 30분, refresh 7일)
8. refresh_tokens 테이블에 저장
9. 앱에 토큰 반환

### 프로필 저장 흐름

1. Flutter 앱이 나이·키·체중·만성질환을 `PUT /api/v1/profile`로 전송 (헤더에 Bearer 토큰 포함)
2. `utils/deps.py`의 get_current_user가 토큰을 해석해 사용자 신원 확인
3. `schemas/profile.py`가 데이터 형식 검증
4. `models/profile.py`로 profiles 테이블 조회 (없으면 새로 생성, 있으면 수정)
5. DB 저장 후 프로필 반환

---

## 13. 보안 처리 방식

### 비밀번호 — bcrypt 해싱

비밀번호는 원문 그대로 저장하지 않습니다. bcrypt 알고리즘으로 복호화가 불가능한 해시값으로 변환합니다.

- 입력: `mypassword123`
- 저장: `$2b$12$K8RP5G2n7Rx...` (원래 비밀번호로 되돌릴 수 없음)
- 로그인 시 입력값을 같은 방식으로 변환해 저장값과 비교

### JWT 토큰 — 신분증 시스템

| 토큰 종류 | 유효시간 | 용도 |
|---------|---------|------|
| access_token | 30분 | 모든 API 호출 시 첨부 |
| refresh_token | 7일 | access_token 만료 시 재발급용 |

로그아웃하면 DB의 refresh_token이 revoked=true로 변경됩니다.

### 민감정보 — AES-256 암호화 예정

만성질환, 복약정보, 진단명, 검사값은 의료법상 민감정보입니다. 현재는 JSONB로 저장하며, 추후 AES-256-GCM 암호화를 적용할 예정입니다 (은행·군사 시스템 수준).

---

## 14. SQLAlchemy란?

SQL을 직접 문자열로 쓰면 오타 위험과 SQL Injection 보안 위험이 있습니다. SQLAlchemy(ORM)는 Python 문법으로 DB를 다루게 해줍니다.

| SQL 직접 작성 | SQLAlchemy (ORM) |
|-------------|----------------|
| `SELECT * FROM users WHERE email = '...'` | `select(User).where(User.email == email)` |
| `INSERT INTO users VALUES (...)` | `db.add(User(email=..., ...))` |
| `UPDATE users SET name = '...'` | `user.display_name = "새이름"` |
| `DELETE FROM users WHERE id = 1` | `await db.delete(user)` |

ORM은 테이블을 Python 클래스로 표현합니다. `class User` = `users 테이블`, `user 객체` = 테이블의 한 행(row).

---

## 15. Alembic이란?

Git이 코드 변경을 관리하듯, Alembic은 테이블 구조 변경을 버전으로 관리합니다. 팀원 모두가 같은 DB 구조를 유지할 수 있습니다.

```bash
# 모델(Python 코드) 변경 후 마이그레이션 파일 자동 생성
alembic revision --autogenerate -m "add profile table"

# 변경 적용 (팀원 모두 이 명령어 한 번)
alembic upgrade head

# 이전 버전으로 되돌리기
alembic downgrade -1
```

---

## 16. 현재 구현된 API 목록

`http://localhost:8000/docs` 에서 Swagger UI로 테스트 가능합니다.

| 경로 | 방식 | 기능 | 인증 |
|------|------|------|------|
| /api/v1/auth/signup | POST | 회원가입 | 불필요 |
| /api/v1/auth/login | POST | 로그인 → JWT 발급 | 불필요 |
| /api/v1/auth/refresh | POST | access 토큰 갱신 | 불필요 |
| /api/v1/auth/logout | POST | 로그아웃 | 불필요 |
| /api/v1/profile | GET | 내 프로필 조회 | Bearer 토큰 필요 |
| /api/v1/profile | PUT | 내 프로필 저장·수정 | Bearer 토큰 필요 |

---

## 17. 로컬 실행 순서

```bash
# 1. DB + Redis 컨테이너 실행
docker-compose up -d

# 2. 환경변수 파일 생성
cp backend/.env.example backend/.env

# 3. Python 패키지 설치
pip install -r backend/requirements.txt

# 4. 마이그레이션 실행 (테이블 생성)
cd backend
alembic upgrade head

# 5. 서버 실행
uvicorn src.main:app --reload

# 6. 브라우저에서 API 테스트
# http://localhost:8000/docs
```

---

## 18. 자주 하는 실수와 해결법

| 오류 메시지 | 원인 | 해결 |
|------------|------|------|
| Connection refused | Docker DB가 안 켜져 있음 | `docker-compose up -d` |
| relation does not exist | 마이그레이션 안 함 | `alembic upgrade head` |
| 401 Unauthorized | 토큰 없거나 만료됨 | 재로그인 후 새 토큰 발급 |
| 422 Unprocessable | 요청 데이터 형식 오류 | 요청 Body 항목 확인 |
| duplicate key value | 이미 가입된 이메일 | 다른 이메일로 시도 |
| ModuleNotFoundError | pip install 안 함 | `pip install -r requirements.txt` |

---

## 19. 다음 구현 예정 항목

| 순서 | 항목 | 관련 테이블 | 데이터 출처 |
|------|------|-----------|-----------|
| 1 | 음식 데이터 적재 | foods, food_categories | 식약처 Open API |
| 2 | 영양제 데이터 적재 | supplements, supplement_ingredients | 식약처 건강기능식품 DB |
| 3 | KDRIs 권장량 데이터 | data/kdris_2020.csv | 한국영양학회 2020 |
| 4 | 식단 기록 저장 | meals | 사용자 입력 + OCR |
| 5 | 영양제 복용 기록 | user_supplements, supplement_intake_logs | 사용자 입력 |
| 6 | 병원 데이터 적재 | hospital_records, lab_results | Kaggle 데이터셋 |
| 7 | AI 분석 결과 저장 | diagnoses, daily_scores | AI Agent |
| 8 | 건강 데이터 수집 | step_counts, weight_logs | HealthKit / Health Connect |
| 9 | 민감정보 암호화 | profiles, diagnoses | AES-256-GCM 구현 |
| 10 | 이메일 인증 | email_verifications | SMTP / AWS SES |
