# Lemon Aid AI Agent

음식과 영양제 OCR로 확보한 신뢰 가능한 섭취 데이터를 건강관리 코칭으로
바꾸기 위한 서버 기반 AI Agent 작업 공간입니다.

이 패키지는 현재 앱 코드와 의도적으로 분리되어 있습니다. 먼저 상용화를 염두에 둔
AI Agent 경계를 작게 세우고, 이후 기존 Flutter/FastAPI 앱에 통합할 수 있게
만드는 것이 목적입니다.

현재 정의한 1차 경계는 다음과 같습니다.

- OCR 결과 기반 섭취 데이터 정규화
- 음식과 영양제 영양소 합산
- 최근 건강 흐름 해석
- 사용자별 개인화 코칭
- 안전 표현 필터링
- 사용자 승인 기반 액션 제안

## 제품 방향

Lemon Aid는 일반 챗봇이 아닙니다. Agent 시스템은 구조화된 섭취 데이터, 공식
영양 기준, 사용자 맥락, 안전 정책을 함께 사용해야 합니다. LLM은 이 흐름 안에서
문장을 정리하고 설명을 돕는 보조 엔진이지, 건강 판단의 단독 근거가 아닙니다.

MVP에서는 혈당과 CGM 연동을 제외합니다. 다만 스키마에는 범용 `health_trends`
입력을 남겨 두어, 이후 혈당과 유사한 건강 지표 흐름을 Agent 인터페이스 변경
없이 추가할 수 있게 합니다.

## 실행 흐름

```text
OCR 음식/영양제 결과
-> Intake Agent
-> Nutrition Engine
-> Health Trend Engine
-> Personalization Agent
-> Coaching Agent
-> Safety Guard
-> Action Agent
-> 사용자 미리보기 및 승인
```

## 로컬 검증

```powershell
python -m unittest discover ai-agent/tests
```
