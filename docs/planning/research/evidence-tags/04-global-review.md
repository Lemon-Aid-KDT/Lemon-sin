# GLOBAL_REVIEW: 최신 동향/배경 근거

> 확인일: 2026-05-14  
> 성격: 국외 리뷰 논문, scoping review, systematic review, 의료 AI 안전성 연구  
> 사용 범위: 최신 동향 이해, 문제 정의 보강, 안전 설계 근거

## 핵심 판단

국외 리뷰는 Lemon Aid의 방향성과 기술 안전성을 설명하는 데 유용하지만, 한국 사용자의 권장량·건기식 표시·복약 경계에는 직접 적용하지 않습니다. 구현 기준은 국내 공식 기준을 우선하고, 국외 리뷰는 배경과 설계 품질을 높이는 보조 근거로 둡니다.

## 핵심 출처

| 출처 | URL | 자료 상태 | Lemon Aid 사용 |
|------|-----|-----------|----------------|
| Precision nutrition for cardiometabolic diseases | <https://pubmed.ncbi.nlm.nih.gov/40307513/> | 기존 research.md 수록 | 개인화 영양 필요성, 한계 설명 |
| Artificial Intelligence Applications to Measure Food and Nutrient Intakes: Scoping Review | <https://pubmed.ncbi.nlm.nih.gov/39608003/> | 이번 보강 조사 | AI 기반 식품·영양 섭취 측정의 장점과 한계 |
| Mobile Computer Vision-Based Applications for Food Recognition and Volume and Calorific Estimation: A Systematic Review | <https://www.mdpi.com/2029682> | 이번 보강 조사 | 모바일 음식 인식·분량 추정의 한계, 설명 가능성 |
| Navigating nutrients: real-time food nutrition classification and recommendation systems | <https://pubmed.ncbi.nlm.nih.gov/40328030/> | 이번 보강 조사 | 실시간 음식 영양 분류·추천 시스템 동향 |
| Large language models provide unsafe answers to patient-posed medical questions | <https://pmc.ncbi.nlm.nih.gov/articles/PMC13013898/> | 이번 보강 조사 | 환자 대상 LLM 의료 답변 안전성 위험 |

## 사용할 수 있는 방식

- 기획: 개인화 영양과 AI 기반 식단 관리가 왜 필요한지 설명
- 안전 설계: AI 답변을 사용자에게 직접 의료 조언처럼 제공하지 않아야 하는 근거
- OCR/이미지: 음식 사진만으로 분량과 영양소를 확정하기 어려운 이유 설명
- 검증: human-in-the-loop, 사용자 승인, 전문가 검토, confidence 표시의 필요성 설명
- 멘토 자료: Lemon Aid가 자동 처방형 서비스가 아니라 보조 서비스여야 하는 근거

## 사용하면 안 되는 방식

- 국외 연구의 권장량이나 질환별 기준을 한국 사용자 기준값으로 치환하지 않는다.
- 정밀영양 리뷰를 근거로 LLM이 사용자별 식단·영양제 권고를 새로 만들게 하지 않는다.
- 음식 인식 기술 논문을 근거로 사진만 보고 섭취량을 확정하지 않는다.
- LLM 의료 성능 논문을 근거로 챗봇이 의료 상담을 대신하게 하지 않는다.
- 국외 논문 표현을 앱 문구로 그대로 번역하지 않는다.

## 반영 위치

| 영역 | 반영 방식 |
|------|-----------|
| DB | 문헌 메타데이터만 저장 |
| 알고리즘 | 직접 기준값으로 사용 금지, confidence·검증 설계 참고 |
| Agent | LLM 안전장치, 불확실성, 상담 권장 설계 참고 |
| UI/UX | 사용자 확인, 수정, 설명 가능성, 출처 표시 |
| 안전/검증 | 의료 답변 위험성, red-team, 전문가 검토 필요성 |

## MVP 반영

- AI/OCR 결과는 후보로만 표시하고 사용자 승인 전 확정하지 않는다.
- 사용자에게 보이는 답변은 공식 기준 계산 결과의 설명으로 제한한다.
- LLM 출력은 정규식·스키마·금지 표현 필터를 통과시킨다.

## v2 이후 검토

- 음식 사진 기반 분량 추정 도입 여부는 별도 정확도 검증 후 결정
- 정밀영양 고도화는 의료자문위와 데이터 품질 검토 후 진행
- LLM 의료 안전성 평가셋을 Lemon Aid 금지 표현 테스트로 변환
