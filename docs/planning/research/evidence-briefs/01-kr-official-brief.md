# KR_OFFICIAL Brief

> 확인일: 2026-05-14  
> 읽은 자료: 보건복지부 KDRIs 배포 페이지, 식약처 식품영양성분 DB Open API 안내, 농촌진흥청 OpenAPI 안내, 질병관리청 국가건강정보포털, 한국의약품안전관리원 DUR 이해 페이지

## 핵심 요약

보건복지부는 `2020 한국인 영양소 섭취기준`을 공식 발간자료로 배포한다. 페이지에서 에너지·다량영양소, 비타민, 무기질 PDF가 분리되어 있고, 2021~2022년 정오표 4차까지 제공되는 것을 확인했다. Lemon Aid에서 KDRIs를 쓰려면 PDF 수치만 가져오는 것이 아니라 정오표 반영 여부와 기준 버전을 함께 저장해야 한다.

식약처 식품영양성분 DB는 식품 검색, 영양성분 검색, DB 내려받기, Open API를 제공한다. 공공데이터포털 링크에는 가공식품, 음식, 원재료성 식품, 건강기능식품 영양성분 등이 나뉘어 있다. 따라서 음식 OCR 결과는 하나의 DB에 바로 확정 매칭하기보다 자료원과 식품 유형을 함께 기록해야 한다.

농촌진흥청 OpenAPI는 식단관리 음식정보, 음식별 영양성분, 메뉴젠 음식·재료·조리·이미지 정보, 국가표준식품성분정보를 제공한다. 한식은 음식명만으로 부족하므로 음식코드, 중량, 재료, 조리 정보가 중요하다.

DUR은 병용금기, 특정연령대금기, 임부금기, 효능군중복주의, 용량주의, 노인주의, 수유부주의 같은 범주를 제공한다. 이는 앱이 복약 안전을 판정하기 위한 자료가 아니라 상담 권장 조건을 설계하는 근거다.

## Lemon Aid 반영

- DB: `nutrient_reference`, `food_nutrients`, `evidence_sources`에 기준 버전, 정오표, 자료원, 식품 유형을 저장한다.
- 알고리즘: KDRIs 대비 섭취 비율, 상한섭취량 초과 가능성, 음식·영양제 합산 계산에만 사용한다.
- UI: “권장량 대비”, “입력된 정보 기준”, “전문가 상담 권장”으로 표현한다.

## 사용 금지선

공식 자료라도 질환 진단, 치료 목표 판정, 복약 가능 여부 확정, 특정 영양제 추천으로 확장하지 않는다. 식품 DB 값은 평균값이므로 사용자 확인 없이 실제 섭취량으로 확정하지 않는다.

## 출처

- https://www.mohw.go.kr/board.es?act=view&bid=0019&list_no=362385&mid=a10411000000&nPage=39&tag=
- https://various.foodsafetykorea.go.kr/nutrient/industry/openApi/info.do
- https://koreanfood.rda.go.kr/kfi/openapi/useNewGuidance
- https://health.kdca.go.kr/healthinfo
- https://www.drugsafe.or.kr/iwt/ds/ko/useinfo/EgovDurUds.do?pageCsf=KR
