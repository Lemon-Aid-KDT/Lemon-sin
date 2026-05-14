# GLOBAL_TECH Brief

> 확인일: 2026-05-14  
> 읽은 자료: Hugging Face Papers 원문 메타데이터, arXiv 초록 페이지, 공개 논문 요약

## 핵심 요약

NutriBench는 자연어 식사 설명에서 영양 추정을 평가하는 벤치마크다. 11,857개 식사 설명과 탄수화물, 단백질, 지방, 열량 라벨을 포함하고, 여러 LLM과 Chain-of-Thought, RAG 전략을 비교한다. 이는 Lemon Aid 챗봇이 식사 설명을 구조화할 수 있다는 가능성을 보여주지만, 실제 서비스에서는 공식 DB 매칭과 사용자 확인이 필요하다.

MedHalu는 의료 질의에 대한 LLM hallucination을 다룬다. 의료 전문가, LLM, 일반 사용자를 비교하며 LLM이 의료 hallucination 탐지에서 전문가보다 약하고, expert-in-the-loop 접근이 성능을 높일 수 있다고 설명한다.

의료 LLM 인간 평가 프레임워크 논문은 자동 평가만으로는 의료 LLM 안전성을 보장하기 어렵다고 본다. QUEST 프레임워크는 정보 품질, 이해와 추론, 표현, 안전과 해로움, 신뢰와 확신을 평가 차원으로 제안한다.

Guided deferral 논문은 의료 환경에서 LLM hallucination, 개인정보, 신뢰 문제가 있으므로 불확실한 예측을 사람에게 넘기는 구조가 필요하다고 설명한다. 의료 LLM primer는 task 정의, 모델 선택, prompt/fine-tuning, 배포, 규제·윤리·모니터링을 단계적으로 고려해야 한다고 본다.

## Lemon Aid 반영

- OCR/LLM 결과는 `raw_text`, `candidate`, `matched_source`, `confidence`, `user_approved`로 분리한다.
- Agent 응답은 스키마 검증, 금지어 필터, fallback, deferral을 통과해야 한다.
- 평가에는 자동 테스트와 사람 검토 체크리스트를 함께 둔다.

## 사용 금지선

벤치마크 성능을 Lemon Aid 정확도 보장으로 쓰지 않는다. LLM이 영양 기준값, 질환별 판단, 복약 주의를 생성하게 하지 않는다.

## 출처

- https://huggingface.co/papers/2407.12843
- https://huggingface.co/papers/2409.19492
- https://arxiv.org/abs/2405.02559
- https://arxiv.org/abs/2406.07212
- https://huggingface.co/papers/2410.18856
