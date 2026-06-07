# v2 CLOVA teacher pass — section 커버리지 (Stage 2 결과)

작성: 2026-06-08. 입력 297 candidate(전부 resolve, sha 무결성 OK), CLOVA 297/297 labeled, 0 failed, section bbox 1,402개(avg 4.7/img). teacher 텍스트/박스는 gitignored `datasets/supplement-section-roi-v2/`.

## 섹션 커버리지 (candidate 297 기준)
| section | candidates | 비율 |
|---|---:|---:|
| ingredient_amounts | 268 | **90%** |
| supplement_facts | 53 | 18% |
| precautions | 41 | 14% |
| functional_claims | 40 | 13% |
| **intake_method** | **2** | **0.7%** |
| (섹션 없음/empty) | 26 | 9% |

## 해석
- **ingredient_amounts ROI는 강력(90%)** — 이것이 주 병목(ingredient_recall 0.466, ingredient_all_missed 33%)을 직접 때리는 라벨이므로, ROI 검출기/structured GT의 핵심 목적은 달성.
- **intake_method는 사실상 미확보(0.7%)** — 원인: candidate 선택 시 프록시의 intake 신호가 "1일"을 포함해 "1일 영양성분 기준치"(facts)에 오탐 → "fragmented(94)"가 실제 intake 분리가 아니었음. 실제 섭취방법/복용방법 패널은 선택되지 않은 다른 detail 이미지에 존재.
- empty 26개(9%)는 low_signal/분류 실패 → 사람 주석 또는 제외 대상.

## 권고 (다음)
1. **intake-targeted 보강 패스**(별도): 각 제품의 *비선택* detail 이미지를 **엄격 intake 키워드**(섭취방법/복용방법/섭취하/드십시오, 단 bare "1일" 제외)로 재스캔 → intake 패널 이미지 선택 → CLOVA → intake_method bbox 확보. (추가 CLOVA 비용 발생 → 승인 필요)
2. ingredient_amounts ROI는 그대로 Stage 3(사람 bbox 리뷰)로 진행 가능.
3. empty 26개는 리뷰 큐에서 별도 처리(주석 또는 제외).

> redaction: 본 문서는 카운트만. 원문/박스 좌표는 gitignored datasets/teacher에만.
