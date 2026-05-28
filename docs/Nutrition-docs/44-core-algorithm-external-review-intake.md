# 44. core-algorithm 외부 검토 자료 흡수 기록

## 목적

팀원이 수집한 core-algorithm 자료는 LLM 프롬프트에 바로 주입하지 않는다. 먼저
`data/nutrition_reference/core_algorithm_evidence.json`에 검수 대기 evidence로
등록하고, 공식 출처 또는 논문 원문 확인을 거친 항목만 사용자 답변 지식층으로
승격한다.

## 현재 처리 원칙

- 모든 신규 claim의 기본 상태는 `draft`다.
- `draft`와 `paper_candidate` 항목은 사용자-facing 출처나 LLM prompt의 근거
  항목으로 노출하지 않는다.
- P0 항목은 정답 판정이 아니라 deterministic boundary로만 반영한다.
- 공개 API 응답 필드는 유지하고, 필요한 경우 기존 `warning` 또는 `note` 안에
  낮은 신뢰도 안내를 붙인다.

## 초기 분류

| 우선순위 | 영역 | 항목 | 현재 처리 |
|---|---|---|---|
| P0 | supplement interaction | 와파린-비타민 K, 갑상선약-칼슘/철, 메트포민-B12, 항응고제-오메가3/은행잎/Vit E, MAOI-티라민 | `drug_or_interaction` boundary |
| P0 | supplement interaction | 흡연자 베타카로틴/Vit A, 음주자 Vit A/아세트아미노펜 | `drug_or_interaction` boundary |
| P0 | weight prediction | 갑상선 질환, CKD, 간질환, 스테로이드, 당뇨 약물 맥락 | 장기 Hall-lite 자동 선택 비활성 + warning |
| P1 | BMI/activity/KDRIs | KSSO 35+, WHtR, Tanaka HRmax, 임산부/노인/만성질환 KDRIs 라우팅 | backlog |
| P2 | 고도화 | Hall 모델 정밀화, METs/cadence, 흡연/음주 modifier, 장기 개인화 보정 | 별도 PR 후보 |

## 출처 역할

- KDCA: 질환 설명, 사용자 문구 경계, 안전 boundary 보조
- MFDS/FoodSafetyKorea: 국내 건강기능식품 기능성, 성분, 제품·의약품 확인 경로
- KDRIs: 영양 섭취 기준과 부족·과잉 비교 기준
- NIH ODS/openFDA: 해외 보충제·drug label 보조 근거 후보
- NCBI/Semantic Scholar: 논문 후보 수집용이며, 검수 전 사용자 출처로 쓰지 않음

논문 API key가 있더라도 자동으로 안전한 지식이 되는 것은 아니다. API는 후보
수집을 돕는 도구이고, 사용자 답변 근거가 되려면 source review와 표현 검수를
통과해야 한다.

## 검증

- inventory 파일은 모든 항목에 `topic`, `algorithm_area`, `claim_summary`,
  `recommended_action`, `source_type`, `review_status`, `source_doc`, `priority`,
  `implementation_target`을 요구한다.
- P0 상호작용 예시는 LLM 호출 없이 boundary 응답으로 이동한다.
- 장기 체중예측 위험 맥락은 Hall-lite 자동 선택을 쓰지 않고 기존 7-step 결과에
  낮은 신뢰도 warning을 붙인다.
