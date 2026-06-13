# 최종 40클래스 음식 영양 정보 (DB용 정리)

> 작성 2026-06-13. 최종 서비스 분류 모델(exp16b, 지원 40클래스)이 출력하는 음식 종류별
> 영양 정보를 DB 삽입용으로 정리한 산출물. 100g 기준 클래스 평균값.
> ⚠️ 참고용 정보이며 진단·처방이 아닙니다. 정밀 영양표가 아닌 데모용 추정치입니다.

---

## 1. 무엇인가 / 어디서 왔나

- 원천: 팀원이 구축한 `food_nutrition` 테이블(alembic `0027_create_food_nutrition_table.py`, taxo59 **59클래스** 시드, source=`aihub_taxo59_csv`).
- 이 문서는 그 59클래스 중 **최종 모델이 실제로 출력하는 40클래스만** 추려낸 부분집합이다.
- 값은 AIHub 라벨 JSON의 `nutrition` 필드를 100g로 정규화해 클래스 평균낸 것.

> **즉, 데이터는 이미 DB에 들어가 있다(59행).** 이 정리는 ①최종 서비스 범위(40)를 명확히 하고
> ②데이터 품질 이슈를 짚고 ③최종 분류 체계 기준의 깔끔한 레퍼런스를 제공하기 위함이다.

## 2. 왜 40클래스인가 (taxo59 → taxo50 → 서비스 40)

| 단계 | 처리 | 클래스 |
|---|---|---|
| taxo59 (DB 시드) | 원본 | 59 |
| − DROP 6 | 모호·저빈도 제거 (cold-ramen, nagasaki-champon, tteokbokki-jajang, tteokbokki-cream-rose, hot-pot, korean-clear-soup) | 53 |
| − MERGE 3 (원천 클래스) | 중복 통합 (korean-red-soup→jjigae-red, noodle-plain→kalguksu, pork-cutlet-sauced→pork-cutlet-dry) | 50 (=taxo50) |
| − 서비스 미지원 10 | wild 실사용 인식률 낮아 이번 버전 제외 (seafood-jjim/spicy-tang/clear-tang, squid-dish, shrimp-dish, grilled-beef, jjamppong, fried-rice, dumplings, rice-bowl) | **40 (서비스 지원)** |

→ DB의 59행 중 **19행(6 drop + 3 merge-source + 10 미지원)은 최종 모델이 출력하지 않음.**
MERGE 대상(jjigae-red, kalguksu, pork-cutlet-dry)은 40에 **포함**되며 자기 영양값을 그대로 쓴다.

## 3. 컬럼 / 단위

| 컬럼 | 의미 | 단위 |
|---|---|---|
| `class_en` / `class_ko` | 클래스명(영/한) — 모델 출력 `class_en`으로 조인 | — |
| `n_source_codes` | 평균에 쓰인 AIHub 음식코드 수 (많을수록 대표성↑) | 개 |
| `serving_g` | 1인분 추정 중량 | g |
| `kcal_100g` | 열량 | kcal/100g |
| `carb_g · sugar_g · fat_g · protein_g` | 탄수·당류·지방·단백질 | g/100g |
| `sodium_mg · chol_mg · sat_fat_g · trans_fat_g` | 나트륨·콜레스테롤·포화지방·트랜스지방 | mg 또는 g/100g |
| `carb_pct · protein_pct · fat_pct` | 탄·단·지 **칼로리** 비율 (파생) | % |
| `kcal_per_serving` | 1인분 열량 = kcal_100g × serving_g/100 (파생) | kcal |

**섭취량 환산 공식**: `섭취값 = per_100g × 섭취중량(g) / 100`. 앱에서 1인분/2인분/직접입력에 적용.

## 4. 웹서치 감사 보정 (v2, 2026-06-13)

40클래스를 멀티에이전트 웹서치(52 에이전트, USDA·식약처·농진청 등 교차)로 감사하고,
**통용 정보와 확실히 다른 항목만 적대적 재검증 후 high-신뢰일 때만** 보정했다(AIHub 1차·웹 보조 원칙).
**40클래스 중 8클래스 10개 값 보정, 나머지 32클래스는 AIHub 값 유지.** 전체 근거(출처 URL 포함)는
`nutrition_web_audit_evidence.txt`.

| 클래스 | 항목 | 기존(AIHub) | 보정 | 사유 |
|---|---|---|---|---|
| pizza 피자 | sodium_mg | 2609.22 | **550** | 통용 400~700의 ~5배, 평균 오염 |
| fried-chicken 후라이드치킨 | chol_mg | 14.93 | **88** | 닭+껍질 튀김 통용 ~85~90 |
| fried-chicken 후라이드치킨 | sat_fat_g | 0.4 | **3** | 총지방 11.7인데 포화 0.4 = 물리적 불가 |
| korean-ramyeon-red 라면 | chol_mg | 55.07 | **0** | 유탕면은 식물성 → 콜레스테롤 ~0 |
| rice-noodle-soup 쌀국수 | chol_mg | 71.22 | **13** | 통용 0~13, 71은 과다 |
| braised-chicken 찜닭 | chol_mg | 3.77 | **30** | 닭고기 함유인데 3.77 과소 |
| braised-chicken 찜닭 | sat_fat_g | 0.02 | **1.3** | 물리적 불가(총지방 6.6) |
| fried-food-platter 튀김(모둠) | sat_fat_g | 0.37 | **2** | 물리적 불가(총지방 11.9) |
| hamburger 햄버거 | sat_fat_g | 1.34 | **4** | 패티+치즈 통용 3.5~5 |
| pork-cutlet-dry 돈가스 | sat_fat_g | 1.93 | **4.5** | 튀김 통용 ~4.5~5 |

> 보정값 출처/근거는 근거파일에 클래스별로 기록. 감사 manifest 버전 = `food-nutrition-40class-v2`.
> ⚠️ `questionable`(의심되나 레시피 편차로 단정 불가) 항목 다수는 **변경하지 않고** 근거파일에만 기록
> (예: 죽 열량, 삼겹살 지방, 초밥 콜레스테롤 등 — AIHub 우선 원칙).

## 4-1. 남은 데이터 품질 메모

1. **당류(sugar_g) 결측 6개**: grilled-fish, grilled-pork-belly, korean-ramyeon-red, rice-soup,
   savory-pancake, udon — 원천에 값 없음(AIHub −99). DB에선 NULL. UI는 "정보 없음" 처리 권장.
2. 단일 코드(`n_source_codes`=1) 클래스(takoyaki·grilled-pork-belly)는 표본 1개 평균이라 신뢰도 낮음 — 참고.

## 5. 파일 / 사용법

| 파일 | 용도 |
|---|---|
| `food_nutrition_40class.csv` | 리뷰·시드용 (40행, UTF-8 BOM). 파생 비율·1인분 kcal 포함 |
| `food_nutrition_40class_upsert.sql` | DB 삽입용. `food_nutrition` 테이블에 `ON CONFLICT(class_en) DO UPDATE` (멱등) |

- **이미 0027 마이그레이션으로 59행이 들어가 있다면** 별도 삽입 불필요 — 이 SQL은 ①최종 40만 별도
  관리하거나 ②다른 DB에 40만 넣을 때 사용. 기존 테이블에 돌려도 40행만 갱신(나머지 19행 유지)된다.
- 미지원 19행을 쿼리에서 빼려면 모델이 그 `class_en`을 출력하지 않으므로 자연히 조인 안 됨
  (별도 `is_active=false` 처리는 선택).

## 6. 컴플라이언스

- 본 데이터는 **정보 제공·참고용**이며 의학적 진단·처방이 아니다.
- 만성질환(혈압·혈당 등) 관점 안내는 "참고하세요" 수준의 정보 제공으로 한정하고,
  최종 식단 판단은 전문가 상담을 안내한다. (`docs/10-compliance-checklist.md` §10 준수)
