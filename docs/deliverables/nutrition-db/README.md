# 음식 클래스별 영양소 데이터 (DB 적재용) — 전달 문서

> **대상**: DB(PostgreSQL) 작업 팀원 | **작성**: 2026-06-04
> 음식 탐지 모델(taxo59, 59클래스)이 인식한 음식을 **영양소와 연결**하기 위한 기준 데이터입니다.

---

## 1. 포함 파일
| 파일 | 내용 | 필요? |
|---|---|---|
| **`food_nutrition_taxo59.csv`** | **영양소 데이터 (59행)** — UTF-8 BOM, 한글명 포함 | ✅ **이것만 있으면 됨** |
| `README.md` | 컬럼 의미·단위·출처·매핑 가이드 | ✅ 참고용 |
| `food_nutrition_taxo59.sql` | CREATE TABLE + INSERT | ⛔ **스키마가 아직 없을 때만**. 이미 DB가 있으면 **불필요**(DROP/CREATE가 기존 테이블과 충돌 가능) |

## 2. 사용법 — **이미 DB가 있는 경우 (csv만 사용)**
이미 영양소 테이블이 있으면, **csv 데이터를 본인 스키마에 맞게 적재**하면 됩니다.
아래 §3 컬럼 표를 보고 본인 컬럼에 매핑하세요.
```sql
-- 예: 본인 테이블(컬럼명은 본인 것)에 csv를 임시 적재 후 INSERT/UPSERT
\copy your_nutrition_table (식별자, 한글명, 1인분g, 열량, ...) FROM 'food_nutrition_taxo59.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
```
> 컬럼 순서/이름이 본인 테이블과 다르면, 임시 staging 테이블에 csv를 넣고 `INSERT ... SELECT`로 매핑하는 걸 권장합니다.

<details><summary>참고: 스키마가 아직 없다면 (.sql 사용)</summary>

```bash
psql -d <DB이름> -f food_nutrition_taxo59.sql   # 테이블 생성 + 데이터 적재 한 번에
```
</details>

## 3. 테이블 스키마 `food_nutrition`
| 컬럼 | 타입 | 단위 | 설명 |
|---|---|---|---|
| **class_en** | VARCHAR(40) PK | — | **모델 클래스명(영문)** = 탐지 결과와 조인하는 키 |
| class_ko | VARCHAR(40) | — | 한글 표시명 (예: fried-chicken → 후라이드치킨) |
| n_source_codes | SMALLINT | 개 | 평균에 사용된 AIHub 원본 음식코드 수 |
| serving_g | NUMERIC(6,1) | g | **1인분 평균 중량** (1인분 환산용) |
| kcal_100g | NUMERIC(7,2) | kcal/100g | 열량 |
| carb_g | NUMERIC(6,2) | g/100g | 탄수화물 |
| sugar_g | NUMERIC(6,2) | g/100g | 당류 |
| fat_g | NUMERIC(6,2) | g/100g | 지방 |
| protein_g | NUMERIC(6,2) | g/100g | 단백질 |
| sodium_mg | NUMERIC(8,2) | mg/100g | 나트륨 |
| chol_mg | NUMERIC(7,2) | mg/100g | 콜레스테롤 |
| sat_fat_g | NUMERIC(6,2) | g/100g | 포화지방 |
| trans_fat_g | NUMERIC(6,2) | g/100g | 트랜스지방 |

> 💡 **영양소 값은 전부 "100g 기준"** 입니다. **1인분 기준**이 필요하면:
> `섭취량 영양소 = (해당 컬럼) × serving_g / 100`
> (예: 짜장면 1인분 열량 = `kcal_100g × serving_g/100`)

## 4. 출처 & 산출 방식
- **출처**: AIHub 음식 이미지 데이터셋의 라벨(JSON) `nutrition` 필드.
- **산출**: 각 음식의 영양소를 **100g 기준으로 정규화**(원본은 serving 기준) → 한 클래스에 묶인 여러 음식(AIHub 원본코드)의 **평균**.
- **연결 값**: 음식 클래스명(`class_en`의 값, 예 `'jjamppong'`)이 **모델 탐지 결과와 1:1**로 같습니다. 본인 DB에서 음식 클래스명을 저장하는 컬럼(이름은 자유)에 이 값을 넣으면 탐지 결과↔영양소가 연결됩니다. (제 테이블 구조와 무관 — `class_en`은 그저 "음식 식별 문자열")

## 5. ⚠️ 주의사항 (꼭 읽어주세요)
- **데모용 추정치**입니다. "한 클래스 = 여러 음식의 평균"이라 정밀 영양성분표가 아닙니다. (예: `fried-chicken`은 여러 치킨류 평균)
- 향후 정밀화 시 **클래스→대표 음식 단위로 세분**하거나 식약처 정밀 DB로 교체 예정 — 그때 스키마에 `source`·`updated_at` 컬럼 추가 권장.
- 일부 값이 원본에서 결측이면 `NULL`일 수 있으니 조회 시 `COALESCE` 고려.
- 클래스 수: **59** (음식 탐지 모델 taxo59와 동일). 모델이 클래스 추가/변경되면 이 표도 동기화 필요.

## 6. 활용 예시 (쿼리)
```sql
-- 탐지된 음식의 1인분 영양소 (앱 표시용)
SELECT class_ko,
       ROUND(kcal_100g * serving_g/100)        AS kcal_1인분,
       ROUND(protein_g * serving_g/100, 1)      AS 단백질_g,
       ROUND(sodium_mg * serving_g/100)         AS 나트륨_mg
FROM   food_nutrition
WHERE  class_en = 'jjamppong';

-- 나트륨 높은 음식 Top 10 (만성질환 경고용, 100g 기준)
SELECT class_ko, sodium_mg FROM food_nutrition ORDER BY sodium_mg DESC LIMIT 10;
```

---
문의/수정 필요하면 알려주세요. 모델 클래스가 바뀌면 같은 형식으로 갱신해 드리겠습니다.
