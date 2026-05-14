# GLOBAL_TECH: AI, OCR, 추천 시스템 구현 참고

> 확인일: 2026-05-14  
> 성격: 음식 인식, 영양 추정, LLM 평가, hallucination, human-in-the-loop 기술 자료  
> 사용 범위: 모델 학습 데이터가 아니라 시스템 설계와 검증 방식 참고

## 핵심 판단

`GLOBAL_TECH` 자료는 Lemon Aid의 AI/OCR 파이프라인, Agent 평가, 사용자 확인 흐름을 설계하는 데 참고합니다. 이 자료를 사용자 건강 판단 기준이나 의료 지식 생성 근거로 사용하지 않습니다.

## 핵심 출처

| 출처 | URL | 자료 상태 | Lemon Aid 사용 |
|------|-----|-----------|----------------|
| NutriBench: nutrition estimation from meal descriptions | <https://huggingface.co/papers/2407.12843> | 이번 보강 조사 | 자연어 식사 설명에서 영양 추정 벤치마크 참고 |
| Demystifying Large Language Models for Medicine: A Primer | <https://huggingface.co/papers/2410.18856> | 이번 보강 조사 | 의료 LLM 사용 범위와 안전 평가 관점 참고 |
| MedHalu: Hallucinations in Responses to Healthcare Queries | <https://huggingface.co/papers/2409.19492> | 이번 보강 조사 | 의료 질의 hallucination 위험과 expert-in-the-loop 필요성 |
| A Framework for Human Evaluation of LLMs in Healthcare | <https://arxiv.org/abs/2405.02559> | 이번 보강 조사 | 의료 LLM 인간 평가 프레임 참고 |
| Towards Human-AI Collaboration in Healthcare: Guided Deferral Systems | <https://arxiv.org/abs/2406.07212> | 이번 보강 조사 | AI가 사람에게 판단을 넘기는 deferral 설계 참고 |
| Can large language models reason about medical questions? | <https://www.sciencedirect.com/science/article/pii/S2666389924000424> | 이번 보강 조사 | 의료 질문 평가의 한계와 benchmark 해석 참고 |

## 사용할 수 있는 방식

- OCR 파이프라인: raw text, 후보 구조화, DB 매칭, 사용자 수정, 승인 상태 분리
- LLM Tool Use: Pydantic schema 강제, confidence 관리, 재시도·fallback 설계
- 평가: 의료 답변 품질을 자동 점수만으로 판단하지 않고 사람 검토 항목을 둠
- Agent: 불확실하거나 의료적 판단이 필요한 경우 상담 권장 또는 입력 보완 요청
- 로그: Agent run, 사용한 도구, latency, cost, 실패 사유, filter 결과 저장

## 사용하면 안 되는 방식

- 국외 benchmark 결과를 Lemon Aid 정확도 보장 근거로 쓰지 않는다.
- LLM이 영양소 기준값, 질환별 판단, 복약 주의를 새로 생성하게 하지 않는다.
- hallucination 탐지 논문을 읽었다는 이유로 hallucination이 해결됐다고 가정하지 않는다.
- meal description 영양 추정 결과를 공식 식품 DB 매칭 없이 확정하지 않는다.
- 의료 질문 benchmark 통과를 사용자 대상 의료 상담 가능성으로 해석하지 않는다.

## 반영 위치

| 영역 | 반영 방식 |
|------|-----------|
| DB | OCR 원문, 정규화 후보, 사용자 승인 상태 분리 |
| 알고리즘 | confidence, fallback, 사용자 확인 조건 |
| Agent | 스키마 검증, tool call 제한, deferral |
| UI/UX | 낮은 confidence 표시, 수정 가능한 미리보기 |
| 안전/검증 | hallucination 테스트, human review 체크리스트 |

## MVP 반영

- 음식 사진과 영양제 라벨은 “후보 분석”으로 처리한다.
- OCR/LLM 구조화 결과는 사용자 승인 전 건강 기록으로 저장하지 않는다.
- 금지 표현 필터와 재생성 실패 시 수동 입력 안내를 둔다.

## v2 이후 검토

- Lemon Aid 전용 음식/영양제 OCR 테스트셋 구축
- LLM 출력 안전성 red-team 케이스 축적
- 의료자문위 리뷰가 필요한 deferral 조건을 코드 정책으로 정리
