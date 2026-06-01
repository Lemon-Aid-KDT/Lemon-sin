# exp07 chicken-galbi 라벨노이즈 감사 (taxonomy v3)

> off-by-one 보정 후 실제 약점 점검. 결론: **chicken-galbi는 데이터 빈약이 아니라 라벨노이즈** — 증강 무의미, 재매핑/재분할 필요.

## 근거 (zoom 감사 + 소스코드 분포)

- 산출물: `zoom_label_chicken-galbi.png`, `zoom_label_fried-chicken.png` (bal500 학습셋, GT 박스 오버레이)
- chicken-galbi(n=500)는 **단 3개 AI Hub 코드**의 병합:

| 소스코드 | bal500 표본 | 원본 tr/va | 시각 판정 (montage) | 충돌 대상 |
|---|---|---|---|---|
| **B11004** | 180 | 350/80 | **황금빛 후라이드 치킨** — `B11*` = fried-chicken 패밀리 코드인데 chicken-galbi로 매핑됨 | **fried-chicken과 직접 충돌** |
| **B12003** | 122 | 350/80 | 붉은 양념 닭(양념치킨류 소량) | fried-chicken의 양념치킨 타일과 중첩 |
| **B12144** | 198 | 230/30 | **치즈 베이크드 붉은 요리(치즈닭갈비)** — 그라탕/피자/로제 외형 | pizza·rose-tteokbokki 영역 오염 |

→ 하나의 "chicken-galbi" 클래스가 **후라이드 / 양념 / 치즈베이크** 세 가지 이질 외형을 섞고 있어 일관 표현 학습 불가 → AP 0.53. 38% fried-chicken 오예측의 직접 원인은 **B11004(후라이드)** 혼입.

## B12003 추가 확인 (zoom_code_compare.png)

- B12003: 접시에 담긴 **작은 붉은 닭 조각**(양념치킨/닭강정류). **채소·떡·팬 없음** → 전형적 닭갈비(고추장 볶음 + 양배추/떡) 아님.
- B11003(fried-chicken 비교군): 큰 후라이드/양념 조각 — 전형적 치킨.
- **결정타**: 인벤토리상 **B12003과 B11004의 한글명이 동일**("…치킨"). 같은 음식이 fried-chicken / chicken-galbi 두 클래스로 갈린 것 → B12003도 치킨 패밀리.

→ **`chicken-galbi` 클래스에 진짜 닭갈비가 0장.** 명칭이 오칭이며, 실제 내용은 [치킨 2코드 + 치즈닭갈비 1코드].

## 최종 매핑 (taxonomy v3 확정)

| 소스코드 | 표본 | → 이동 | 사유 |
|---|---|---|---|
| B11004 | 180 | **fried-chicken** | 후라이드 치킨 (명칭·외형 일치) |
| B12003 | 122 | **fried-chicken** | 양념치킨/닭강정 (B11004와 동명, 치킨류) |
| B12144 | 198 | **drop** (확정) | 치즈베이크 외형, pizza/rose 오염 — v3에서 제외 |

→ **`chicken-galbi` 클래스 삭제.** 효과: ①0.53 드래그 제거, ②fried-chicken 38% 혼동의 원본 이미지가 이제 정상적으로 fried-chicken 내부로 귀속, ③치즈베이크 오염 격리(drop). **클래스 수 63 → 62.**

## 부수 발견 (데이터 위생)

- `exp06_taxonomy_424_inventory.csv`의 `korean_name`이 **BOM(EF BB BF) + 이중 인코딩 손상**으로 mojibake(복구 불가, `�` 포함). 한글명 신뢰 불가 → 분류 판단은 **이미지·코드 기준**으로만. 인벤토리 재생성 시 UTF-8 정상 저장 필요.
