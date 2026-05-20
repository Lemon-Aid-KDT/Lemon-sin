# Lemon Aid AI Agent 구현 공부 문서

이 문서는 `changmin-aiagent` 브랜치에서 지금까지 작업한 AI Agent 구현을 처음부터
끝까지 이해하기 위한 설명서입니다. 코드 파일 목록만 외우는 문서가 아니라, 왜
그런 구조를 잡았는지, 각 용어가 무엇을 뜻하는지, 데이터가 어떤 순서로 움직이는지
공부할 수 있게 정리했습니다.

## 1. 이번 작업의 큰 목표

이번 작업의 목표는 Lemon Aid 앱 안에서 사용할 수 있는 Health Agent의 MVP 기반을
만드는 것이었습니다.

여기서 Health Agent는 사용자의 음식 섭취, 영양제 섭취, 건강 흐름, 사용자 프로필을
바탕으로 "오늘 어떤 부분을 주의하면 좋을지"를 알려주는 서버 쪽 AI 기능입니다.

다만 건강 도메인은 조심해야 합니다. 앱이 사용자에게 "당뇨입니다", "이 약을
복용하세요", "이 제품을 사세요"처럼 말하면 위험합니다. 그래서 이번 구현의 가장
중요한 원칙은 다음입니다.

```text
건강 판단은 deterministic engine이 한다.
LLM은 이미 계산된 결과를 사람이 읽기 좋은 문장으로 설명만 한다.
```

쉽게 말하면, LLM에게 건강 판단을 맡기지 않았습니다. LLM은 말투를 정리하는
역할입니다. 실제 계산과 판단은 우리가 작성한 Python 코드가 합니다.

## 2. 핵심 용어 쉽게 풀기

### Agent

Agent는 어떤 목표를 수행하는 작은 실행 단위입니다. Lemon Aid에서는 Agent라는
말이 두 가지 의미로 쓰일 수 있습니다.

첫 번째는 앱 안에서 실제로 동작하는 제품 기능입니다. 예를 들어
`DailyHealthAgent`, `ChatAgent`, `IntakeAgent`가 여기에 해당합니다. 사용자의
섭취 데이터를 받아서 분석하고, 설명하고, 액션 후보를 만드는 코드입니다.

두 번째는 프로젝트를 자동으로 구현하기 위해 쓰는 개발용 서브에이전트입니다.
이것은 Codex나 자동화 도구 안에서 병렬 작업을 맡기는 개발 보조 역할입니다. 이번
코드에 들어간 `DailyHealthAgent` 같은 클래스와는 다릅니다.

이번 구현에서 실제 파일로 만들어진 것은 첫 번째 의미의 앱 실행용 Agent입니다.
개발 자동화를 위한 서브에이전트 파일을 따로 만든 것은 아닙니다.

### Deterministic

deterministic은 "같은 입력이면 항상 같은 결과가 나오는 방식"이라는 뜻입니다.

예를 들어 나트륨 섭취량이 2600mg이고 상한량이 2300mg이면, 코드는 항상
"상한량 초과"라고 계산합니다. LLM처럼 매번 표현이나 판단이 달라질 수 있는
방식이 아닙니다.

건강, 영양, 복약 주의처럼 안전이 중요한 부분은 deterministic하게 처리해야
테스트하기 쉽고, 리뷰하기 쉽고, 책임 범위가 명확합니다.

### Engine

Engine은 핵심 계산을 담당하는 코드입니다. Agent가 전체 흐름을 조율한다면,
Engine은 특정 계산을 정확히 수행합니다.

이번 구현에서는 `NutritionEngine`, `SupplementEngine`이 대표적입니다.

- `NutritionEngine`: 음식과 영양제의 영양소를 합산하고 기준 섭취량과 비교합니다.
- `SupplementEngine`: 영양제 성분별 하루 총량을 계산합니다.

### LLM

LLM은 Large Language Model, 즉 큰 언어 모델입니다. ChatGPT, Qwen, Llama 같은
모델을 떠올리면 됩니다.

이번 구현에서는 LLM을 "의사결정자"로 쓰지 않았습니다. LLM은 `DailyCoachingResult`
안에 이미 들어 있는 findings, recommendations, trace를 설명하는 역할만 합니다.

### Adapter

Adapter는 서로 모양이 다른 두 세계를 연결하는 얇은 변환 계층입니다.

이번 작업에는 두 종류의 adapter 개념이 들어갔습니다.

첫 번째는 LLM adapter입니다. `ChatAgent`가 Ollama인지, SGLang인지, 테스트용 fake인지
몰라도 같은 방식으로 호출할 수 있게 `LocalLLMClient`라는 공통 인터페이스를
만들었습니다.

두 번째는 앱 통합 adapter입니다. 내부 Health Agent는 dataclass를 쓰고, 실제
FastAPI 앱 계약은 Pydantic 모델을 쓸 가능성이 큽니다. 그래서
`DailyHealthAgentAppAdapter`가 `AgentInput`을 내부 입력으로 바꾸고,
`DailyCoachingResult`를 `AgentOutput`으로 바꿉니다.

### Protocol

Python의 `Protocol`은 "이런 메서드를 가진 객체라면 같은 타입처럼 취급하겠다"는
약속입니다.

`LocalLLMClient`는 다음 메서드를 가져야 합니다.

```python
def generate(self, request: LLMRequest) -> LLMResponse:
    ...
```

그러면 `FakeLLMClient`, `OllamaClient`, `OpenAICompatibleClient`는 내부 구현이
달라도 모두 `ChatAgent`에 끼워 넣을 수 있습니다.

### Pydantic

Pydantic은 Python에서 입력과 출력 데이터를 검증하고 문서화하기 좋게 만들어 주는
라이브러리입니다. FastAPI와 함께 자주 씁니다.

예를 들어 `AgentInput`에 `request_id`, `user_id`, `payload`가 있어야 한다고
정의하면, 앱 API로 들어오는 데이터가 그 형태를 만족하는지 검증하기 쉬워집니다.

공식 문서:

- [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic Fields](https://docs.pydantic.dev/latest/concepts/fields/)

### Trace

trace는 Agent가 왜 그런 결과를 냈는지 남기는 실행 흔적입니다.

예를 들어 다음과 같은 정보가 trace에 들어갑니다.

```text
intake normalized: foods=1, supplements=0, confirmed source records: 1
nutrition findings: sodium=risky
policy guard warnings: 0
```

이 trace는 디버깅과 설명에 매우 유용하지만, 사용자 입력이나 OCR 원문에서 위험한
문구가 섞일 수 있습니다. 그래서 trace도 사용자에게 보여주기 전에 `SafetyGuard`를
거칩니다.

### Preview

preview는 "아직 확정하지 않고 사용자에게 확인받는 상태"입니다.

OCR은 틀릴 수 있습니다. 사진에서 추출한 영양 성분이나 음식 이름이 잘못될 수 있기
때문입니다. 그래서 OCR source가 아직 사용자의 확인을 받지 않았다면, Agent는 바로
분석 결과와 액션을 만들지 않고 `requires_confirmation` 상태로 멈춥니다.

## 3. 현재 브랜치와 커밋 상태

현재 핵심 작업은 `changmin-aiagent` 브랜치에 유지되어 있습니다.

최근 커밋 흐름은 다음과 같습니다.

```text
c0f4e92 docs(ai): add pull request description draft
dd1e598 docs(ai): mark pushed integration progress
a9d612f feat(ai): add app integration adapter
d69d1a3 docs(ai): update agent todo progress
5433179 feat(ai): add local llm adapter for traced coaching
```

현재 이 브랜치는 `origin/changmin-aiagent`와 동기화된 상태로 확인되었습니다.

이전에 `feat/ai-agent-local-llm` 브랜치로 `changmin-plan` 대상 PR을 하나 만들었지만,
사용자가 직접 닫았습니다. 그 PR은 merge되지 않았습니다. 따라서 `changmin-plan`에는
이 작업이 들어가지 않았습니다.

정리하면 현재 전략은 다음입니다.

```text
AI Agent 구현은 changmin-aiagent에 유지한다.
다른 팀 브랜치나 changmin-plan에는 아직 합치지 않는다.
나중에 사용자가 통합 타이밍을 다시 알려주면 그때 대상 브랜치를 정한다.
```

## 4. 전체 폴더 구조

이번 구현의 중심은 다음 경로입니다.

```text
ai-agent/
  README.md
  docs/
    architecture.md
    decision-log.md
    todo.md
    app-integration-todo.md
    pr-description.md
    implementation-study-guide.md
  src/
    lemon_ai_agent/
      schemas.py
      orchestrator.py
      agents/
      engines/
      guards/
      llm/
      adapters/
  tests/
    test_daily_health_agent.py
    test_llm_and_chat_agent.py
    test_app_adapter.py
```

중요한 점은 `ai-agent`가 현재 앱 코드와 의도적으로 분리되어 있다는 것입니다.

왜 분리했냐면, 실제 앱 backend에 바로 끼워 넣으면 브랜치 충돌, API 계약 충돌,
DB 구현 미완성, 승인 흐름 미정 같은 문제가 섞일 수 있기 때문입니다. 그래서 먼저
독립 패키지처럼 검증 가능한 Health Agent를 만들고, 그다음 앱 통합 adapter를 통해
붙이는 방향으로 설계했습니다.

## 5. 데이터 모델: `schemas.py`

`schemas.py`는 내부 Health Agent가 사용하는 기본 데이터 구조를 정의합니다.

여기서는 Pydantic이 아니라 Python `dataclass`를 사용했습니다.

이유는 간단합니다. `ai-agent` 내부의 계산 엔진은 API 요청 검증보다 순수한 계산
모델이 중요합니다. dataclass는 가볍고 테스트하기 쉽습니다.

주요 모델은 다음과 같습니다.

### `NutrientAmount`

영양소 하나의 이름, 양, 단위를 나타냅니다.

```text
name: sodium
amount: 2600
unit: mg
```

### `FoodIntake`

하루에 먹은 음식 하나를 나타냅니다.

```text
name: instant noodles
meal_type: lunch
serving_label: 1 bowl
nutrients: sodium 2600mg, protein 25g ...
```

### `SupplementIntake`

하루에 먹은 영양제 하나를 나타냅니다.

```text
product_name: multivitamin
ingredients: magnesium 100mg ...
times_per_day: 1
```

### `IntakeSource`

이 섭취 데이터가 어디서 왔는지 나타냅니다.

```text
source_type: food_ocr | supplement_ocr | manual
image_id: 이미지 ID
raw_ocr_text: OCR 원문
user_confirmed: 사용자가 확인했는지 여부
```

여기서 `user_confirmed`가 중요합니다. OCR이 아직 사용자 확인을 받지 않았다면
Agent는 preview 상태로 멈춥니다.

### `UserProfile`

사용자 프로필입니다.

```text
user_id
age
gender
goals
chronic_conditions
medications
```

현재는 DB에서 직접 가져오지 않고 mock 객체로 사용합니다.

### `ReferenceRange`

영양소 기준 섭취량입니다.

```text
nutrient: sodium
target: 2000
unit: mg
upper_limit: 2300
```

현재는 실제 기준 섭취량 DB가 아니라 테스트용 리스트로 넣습니다.

### `DailyCoachingResult`

최종 결과입니다.

```text
user_id
date
findings
recommendations
actions
safety_warnings
sources
supplement_totals
trace
approval_status
```

여기서 `approval_status`는 `confirmed` 또는 `requires_confirmation`입니다.

## 6. 실행 흐름: `DailyHealthAgent`

전체 건강 분석 흐름은 `orchestrator.py`의 `DailyHealthAgent`가 조율합니다.

흐름을 쉽게 쓰면 다음과 같습니다.

```text
1. IntakeAgent가 입력을 정규화한다.
2. OCR source가 미승인인지 확인한다.
3. 미승인이면 preview-only 결과로 멈춘다.
4. 승인된 입력이면 SupplementEngine이 영양제 총량을 계산한다.
5. NutritionEngine이 영양소 합산과 기준 비교를 한다.
6. PersonalizationAgent가 사용자 맥락을 만든다.
7. CoachingAgent가 코칭 추천을 만든다.
8. SafetyGuard가 추천 문구를 검사한다.
9. ActionAgent가 사용자 승인 필요한 액션 후보를 만든다.
10. trace를 만들고 trace도 SafetyGuard로 검사한다.
11. DailyCoachingResult를 반환한다.
```

가장 중요한 방어선은 2번과 3번입니다.

OCR 결과가 미승인이라면 다음 결과만 반환합니다.

```text
findings: []
recommendations: []
actions: []
approval_status: requires_confirmation
```

이렇게 한 이유는 OCR이 틀린 상태에서 건강 추천을 바로 만들면 위험하기 때문입니다.

## 7. Nutrition Engine: 영양소 합산과 기준 비교

`NutritionEngine`은 음식과 영양제의 영양소를 합산하고, 기준 섭취량과 비교합니다.

예를 들어 사용자가 점심으로 나트륨 2600mg이 들어 있는 음식을 먹었고 기준이
다음과 같다고 가정합니다.

```text
target: 2000mg
upper_limit: 2300mg
```

그러면 2600mg은 상한량을 넘기 때문에 `risky`로 분류합니다.

### 왜 단위 정규화가 필요한가

OCR이나 외부 데이터는 같은 영양소를 여러 방식으로 표현할 수 있습니다.

```text
Vitamin D
vitamin d
비타민D
비타민 D
```

단위도 섞일 수 있습니다.

```text
g
mg
mcg
ug
IU
```

이걸 그대로 합산하면 같은 영양소가 서로 다른 영양소처럼 처리될 수 있습니다.

그래서 이번 구현에서는 최소한 다음을 정규화했습니다.

```text
Vitamin D / vitamin D / 비타민D / 비타민 D -> vitamin d
g -> mcg 변환 가능
mg -> mcg 변환 가능
ug / μg / µg -> mcg
vitamin d IU -> mcg
```

비타민 D는 일반적으로 다음 변환을 사용했습니다.

```text
40 IU = 1 mcg
```

이 정규화는 아직 MVP 수준입니다. 실제 서비스에서는 식품 DB, 영양성분 DB,
성분 alias, OCR confidence, 사용자가 수정한 값까지 반영해야 합니다.

## 8. Supplement Engine: 영양제 총량 계산

`SupplementEngine`은 영양제 성분을 하루 총량으로 합산합니다.

예를 들어 마그네슘 100mg 영양제를 하루 2번 먹는다면:

```text
100mg * 2 = 200mg/day
```

여기서 제품명은 추적용으로 보존하지만, 코칭은 특정 제품을 사라고 유도하지 않도록
성분 중심으로 제한합니다.

이유는 특정 제품 구매 유도는 건강 앱에서 위험하고, 광고성 추천처럼 보일 수 있기
때문입니다.

## 9. SafetyGuard: 문구 안전 검사

`SafetyGuard`는 사용자에게 보일 수 있는 문장을 검사합니다.

현재 차단하는 방향은 다음입니다.

```text
진단 표현
치료/처방 표현
약 복용 단정
특정 제품 구매 유도
효과 보장에 가까운 표현
```

예를 들어 다음 문구는 차단됩니다.

```text
당뇨입니다. 이 제품을 구매하세요.
```

차단되면 원문을 그대로 보여주지 않고 fallback 또는 대체 문구를 사용합니다.

trace도 검사합니다. 이전 검토에서 중요한 문제가 하나 있었습니다. 추천 문구만
검사하고 trace를 그대로 보여주면, 사용자 입력이나 외부 입력에 위험 문구가 섞였을
때 그대로 노출될 수 있었습니다.

그래서 지금은 trace line도 검사하고, 위험하면 다음으로 대체합니다.

```text
trace item withheld by policy guard
```

현재 `SafetyGuard`는 단순 문자열 검사 기반입니다. 즉 아주 강력한 의료 안전
엔진은 아닙니다. 하지만 MVP 방어선으로는 테스트 가능한 최소 구조를 세웠고, 앞으로
golden test와 정책 규칙을 늘릴 수 있게 만들었습니다.

## 10. ChatAgent: 설명 담당

`ChatAgent`는 사용자가 "왜 이렇게 추천했어?"라고 물었을 때 답하는 역할입니다.

중요한 점은 `ChatAgent`가 새로운 건강 판단을 만들지 않는다는 것입니다.

`ChatAgent`가 볼 수 있는 정보는 다음으로 제한했습니다.

```text
date
top findings
top recommendations
sanitized trace summary
```

반대로 다음은 prompt에 넣지 않습니다.

```text
원본 이미지
전체 OCR 원문
실제 개인 식별 정보
시크릿
```

### LLM이 없을 때

`llm_client`가 없으면 deterministic fallback 답변을 반환합니다.

즉, LLM 서버가 없어도 앱의 핵심 Health Agent 기능은 동작합니다.

### LLM이 있을 때

`llm_client`가 있으면 LLM에게 설명 문장을 요청합니다.

하지만 LLM 응답을 바로 사용자에게 보여주지 않습니다.

```text
LLM 응답
-> SafetyGuard.check_text()
-> 안전하면 사용자에게 반환
-> 위험하면 deterministic fallback 반환
```

LLM 호출 자체가 실패해도 전체 Agent는 실패하지 않습니다. 예를 들어 Ollama 서버가
꺼져 있거나 timeout이 나면 fallback으로 돌아갑니다.

이 구조 덕분에 건강 판단 결과는 LLM의 상태에 영향을 받지 않습니다.

## 11. LLM Adapter 계층

새로 추가된 LLM 패키지는 다음 경로입니다.

```text
ai-agent/src/lemon_ai_agent/llm/
  base.py
  fake.py
  ollama.py
  openai_compatible.py
  __init__.py
```

### `base.py`

공통 타입을 정의합니다.

```python
LLMMessage
LLMRequest
LLMResponse
LocalLLMClient
```

`ChatAgent`는 provider별 구현을 직접 알 필요가 없습니다. `LocalLLMClient`의
`generate()`만 호출하면 됩니다.

### `FakeLLMClient`

테스트용 LLM입니다.

특징은 다음과 같습니다.

```text
네트워크 호출 없음
항상 고정 응답 반환
provider = "fake"
model = "fake-local-llm"
```

테스트에서 실제 LLM 서버를 띄우면 불안정해집니다. 서버가 꺼져 있거나 모델 다운로드
상태가 다르면 테스트가 실패할 수 있습니다. 그래서 기본 테스트는 fake를 사용합니다.

### `OllamaClient`

로컬 개발용 LLM client입니다.

기본 endpoint:

```text
http://127.0.0.1:11434
```

호출 endpoint:

```text
/api/chat
```

공식 문서:

- [Ollama Chat API](https://docs.ollama.com/api/chat)

Ollama는 개발자가 로컬 PC에서 모델을 쉽게 실행하기 좋기 때문에 개발 기본 후보로
두었습니다.

### `OpenAICompatibleClient`

SGLang, vLLM 같은 OpenAI-compatible 서버를 호출하기 위한 공통 client입니다.

기본 endpoint:

```text
http://127.0.0.1:8000/v1
```

호출 endpoint:

```text
/chat/completions
```

API key가 없으면 `"EMPTY"`를 사용합니다. SGLang, vLLM 같은 로컬 또는 내부망 서버에서는
테스트용으로 빈 key를 허용하는 경우가 있기 때문입니다.

공식 문서:

- [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/)
- [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)

현재 운영 후보는 SGLang입니다. vLLM은 처리량 비교나 별도 serving 구성이 필요할 때
검토할 수 있는 대체 OpenAI-compatible backend로만 남깁니다.

### 왜 `urllib.request`를 썼나

이번 단계에서는 새 dependency를 추가하지 않기로 했습니다. 그래서 Python 표준
라이브러리인 `urllib.request`로 HTTP 요청을 구현했습니다.

공식 문서:

- [Python urllib.request](https://docs.python.org/3/library/urllib.request.html)

나중에 실제 backend에 붙일 때는 `httpx`나 기존 프로젝트의 HTTP client 정책에 맞춰
바꿀 수 있습니다. 지금은 MVP 범위를 작게 유지하는 것이 우선이었습니다.

## 12. 앱 통합 Adapter

검토 과정에서 중요한 우려가 있었습니다.

기존 기획 문서 쪽은 `AgentInput`, `AgentOutput`, `request_id`, `used_tools`,
`latency_ms`, `cost_usd`, `agent_runs`, `agent_memory` 같은 앱 통합 계약을
전제로 하고 있었습니다.

반면 내부 Health Agent는 dataclass 중심의 `DailyCoachingResult`를 반환합니다.

이 둘을 억지로 하나로 합치면 내부 계산 모델이 API/DB 요구사항에 끌려가고,
코드가 복잡해질 수 있습니다.

그래서 `DailyHealthAgentAppAdapter`를 추가했습니다.

경로:

```text
ai-agent/src/lemon_ai_agent/adapters/app.py
```

이 adapter가 하는 일은 다음입니다.

```text
AgentInput
-> UserProfile / DailyIntake / HealthTrend / ReferenceRange
-> DailyHealthAgent.run()
-> ChatAgent.answer()
-> AgentOutput
```

### `AgentInput`

앱에서 Agent에게 요청할 때 들어오는 형태입니다.

```text
request_id
user_id
payload
context
```

### `AgentOutput`

앱이 받을 응답 형태입니다.

```text
request_id
user_id
agent_name
status
approval_status
requires_user_approval
message
findings
recommendations
actions
safety_warnings
used_tools
latency_ms
cost_usd
provider
debug_trace
```

### 왜 adapter가 중요한가

adapter가 있으면 내부 엔진은 건강 판단에만 집중할 수 있습니다.

반대로 FastAPI, DB logging, memory 저장, request_id 추적 같은 앱 요구사항은
adapter에서 처리할 수 있습니다.

즉 역할이 분리됩니다.

```text
DailyHealthAgent: 건강 판단과 결과 생성
DailyHealthAgentAppAdapter: 앱 계약에 맞게 입력/출력 변환
FastAPI route: HTTP 요청/응답, 인증, 동의 체크, 감사 로그
DB layer: agent_runs, agent_memory 저장
```

현재 `changmin-aiagent`에는 DB 없이 테스트 가능한 adapter까지만 들어 있습니다.
실제 FastAPI route와 DB 저장은 통합 시점에 이어서 붙이면 됩니다.

## 13. 사용자 승인 흐름

건강 데이터와 OCR은 바로 저장하거나 실행하면 안 됩니다.

이번 구현의 승인 흐름은 다음 원칙입니다.

```text
미승인 OCR source가 있으면 preview로 멈춘다.
사용자가 확인한 뒤 confirmed payload로 다시 실행한다.
confirmed일 때만 action 후보와 memory update로 넘어간다.
```

예를 들어 OCR로 라면의 나트륨 2600mg을 읽었다고 해도, 사용자가 확인하지 않았다면
다음 상태가 됩니다.

```text
status = "preview"
approval_status = "requires_confirmation"
requires_user_approval = True
findings = []
recommendations = []
actions = []
```

사용자가 확인하면 deterministic engine이 실행되고, 그때 findings와 recommendations가
생깁니다.

이 구조는 "AI가 결과를 바로 저장하거나 액션을 실행하지 않는다"는 앱 안전 원칙과
맞습니다.

## 14. 로깅과 메모리 연결점

이번 구현은 실제 DB를 만들지 않았습니다. 대신 나중에 DB에 붙일 수 있도록 Protocol
연결점을 만들었습니다.

### `AgentRunLogger`

Agent 실행 기록을 남기기 위한 인터페이스입니다.

기록할 수 있는 정보:

```text
request_id
user_id
agent_name
status
latency_ms
cost_usd
provider
approval_status
used_tools
error
```

현재 테스트에서는 `InMemoryAgentRunLogger`를 사용합니다. 실제 backend에서는
이 인터페이스 뒤에 `agent_runs` 테이블 저장 로직을 붙이면 됩니다.

### `AgentMemoryWriter`

Agent 결과를 사용자 장기 메모리에 반영하기 위한 인터페이스입니다.

중요한 제한은 confirmed 결과일 때만 호출한다는 점입니다.

미승인 preview 상태에서는 memory에 쓰지 않습니다.

## 15. 테스트 전략

현재 테스트는 크게 세 묶음입니다.

```text
test_daily_health_agent.py
test_llm_and_chat_agent.py
test_app_adapter.py
```

### Health Agent 테스트

기존 Health Agent 흐름을 검증합니다.

검증한 내용:

```text
고나트륨/고혈압 맥락
단백질 부족
비타민 D 부족
식이섬유 부족
마그네슘/철분/칼슘 상한량 초과
복약 주의 문구
제품 구매 유도 차단
혈당 trend 진단 회피
미승인 OCR preview-only
비타민 D alias와 IU -> mcg 변환
```

### LLM과 ChatAgent 테스트

LLM 계층이 안전하게 동작하는지 검증합니다.

검증한 내용:

```text
FakeLLMClient가 고정 응답을 반환하는지
llm_client가 없으면 deterministic fallback을 쓰는지
안전한 fake LLM 응답은 그대로 반환하는지
위험한 LLM 응답은 차단하고 fallback하는지
LLM 실패 시 예외를 밖으로 던지지 않는지
trace 위험 문구가 prompt와 fallback 답변에 노출되지 않는지
OllamaClient가 /api/chat payload를 올바르게 만드는지
OpenAICompatibleClient가 /chat/completions payload와 Authorization header를 만드는지
```

중요한 점은 실제 Ollama, SGLang, vLLM 서버를 호출하지 않았다는 것입니다. HTTP 호출은
`unittest.mock`으로 가짜 처리했습니다.

공식 문서:

- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

### App Adapter 테스트

앱 통합 경계가 맞는지 검증합니다.

검증한 내용:

```text
AgentInput이 내부 Health Agent 입력으로 잘 변환되는지
confirmed 결과가 completed로 반환되는지
미승인 OCR이 preview로 멈추는지
confirmed일 때 memory writer가 호출되는지
unsafe trend가 trace/debug/message에 원문 노출되지 않는지
FakeLLMClient provider와 cost_usd=0이 기록되는지
```

## 16. 실행한 검증

현재 구현 후 실행한 핵심 검증은 다음입니다.

```powershell
python -m unittest discover ai-agent\tests
python -m compileall ai-agent\src
```

결과는 다음과 같이 확인했습니다.

```text
24 tests OK
compile OK
```

즉 `ai-agent` 독립 패키지 기준으로는 테스트와 Python compile이 통과했습니다.

별도로 backend 통합 실험 브랜치에서는 FastAPI route 연결까지 테스트했지만,
그 작업은 아직 `changmin-aiagent`에 합치지 않고 별도 브랜치에 둔 상태입니다.

## 17. 문서화한 내용

이번 작업에서는 코드뿐 아니라 문서도 함께 정리했습니다.

### `README.md`

사용자가 가장 먼저 보는 요약 문서입니다.

추가한 내용:

```text
Local LLM 전략
Ollama 개발 후보
SGLang/OpenAI-compatible 운영 후보
FakeLLMClient 테스트 기본값
LLM은 판단이 아니라 설명 레이어라는 원칙
앱 통합 adapter 개요
```

### `docs/architecture.md`

구조를 설명하는 문서입니다.

추가한 내용:

```text
ChatAgent -> LocalLLMClient -> Fake/Ollama/OpenAI-compatible 구조
SafetyGuard 통과 후 사용자 노출
trace sanitization
DailyHealthAgentAppAdapter 구조
검증 기준
```

### `docs/decision-log.md`

왜 그렇게 결정했는지 남기는 문서입니다.

추가한 내용:

```text
Ollama를 개발용 후보로 둔 이유
SGLang을 운영 후보로 둔 이유
vLLM을 대체 compatible backend로만 남긴 이유
provider를 생성자 주입으로 분리한 이유
외부 LLM API로 실제 건강 데이터를 보내지 않는 원칙
```

### `docs/todo.md`

처음 계획한 Local LLM 구현 TODO입니다. 완료된 항목은 체크했습니다.

### `docs/app-integration-todo.md`

실제 앱 통합을 할 때 보는 TODO입니다. 내부 Agent 구현과 앱 backend 통합을
구분하기 위해 만들었습니다.

## 18. `todo.md`와 `app-integration-todo.md`의 차이

두 문서는 목적이 다릅니다.

### `todo.md`

`todo.md`는 `ai-agent` 독립 구현 자체를 완성하기 위한 체크리스트입니다.

언제 보냐면:

```text
Local LLM adapter를 만들 때
ChatAgent에 LLM을 연결할 때
SafetyGuard fallback을 확인할 때
ai-agent 단위 테스트를 돌릴 때
문서/테스트/compile 완료 여부를 확인할 때
```

즉 "AI Agent 자체가 제대로 만들어졌나?"를 확인하는 문서입니다.

### `app-integration-todo.md`

`app-integration-todo.md`는 만들어진 AI Agent를 실제 Lemon Aid 앱 backend에 붙일
때 보는 문서입니다.

언제 보냐면:

```text
FastAPI route를 만들 때
AgentInput/AgentOutput을 backend 계약에 맞출 때
agent_runs 테이블 저장을 붙일 때
agent_memory 저장을 붙일 때
사용자 동의/승인 흐름과 연결할 때
인증된 user_id로 client payload를 덮어쓸 때
```

즉 "만들어진 AI Agent를 앱에 어떻게 안전하게 붙이나?"를 확인하는 문서입니다.

현재는 `todo.md` 쪽 작업은 대부분 완료되었고, `app-integration-todo.md`는
adapter 수준까지 완료되어 있습니다. 실제 FastAPI route와 DB 저장은 팀 브랜치
상황을 보고 나중에 이어서 진행하면 됩니다.

## 19. 왜 `changmin-aiagent`에만 유지하기로 했나

중간에 PR을 만들 때 `changmin-plan`과 `yeong-tech` 브랜치 이야기가 있었습니다.

하지만 현재 팀 작업이 진행 중인 브랜치에 바로 넣으면 충돌이 생길 수 있습니다.
특히 backend 쪽은 `yeong-tech`에서 다른 작업자가 작업 중일 수 있으므로, 임의로
PR을 올리거나 merge하면 서로의 작업을 꼬이게 만들 수 있습니다.

그래서 현재 결정은 다음입니다.

```text
AI Agent 구현은 changmin-aiagent에 안전하게 보관한다.
필요한 원격 feature 브랜치도 백업처럼 남겨 둔다.
실제 통합 대상 브랜치는 나중에 사용자와 다시 확인한다.
```

이 방식은 작업물을 잃지 않으면서도 팀 브랜치를 건드리지 않는 방법입니다.

## 20. 아직 하지 않은 것

이번 작업에서 일부러 하지 않은 것도 중요합니다.

하지 않은 것:

```text
실제 OCR 모델 연결
실제 음식/영양제 DB 조회
실제 사용자 DB 조회
실제 CGM/혈당 API 연동
실제 Ollama/SGLang/vLLM 서버 실행
모델 다운로드 자동화
.env 로딩 라이브러리 추가
실제 agent_runs DB 테이블 저장
실제 agent_memory DB 테이블 저장
팀 브랜치 merge
PR merge
```

이것들을 하지 않은 이유는 MVP 범위를 작게 유지하고, 안전 검증 가능한 코어를 먼저
만드는 것이 우선이었기 때문입니다.

## 21. 앞으로 통합할 때의 순서

나중에 실제 앱에 붙일 때는 다음 순서가 좋습니다.

```text
1. 통합 대상 브랜치를 먼저 정한다.
2. 그 브랜치의 최신 backend 구조를 확인한다.
3. 기존 인증/동의/감사 로그 흐름을 확인한다.
4. ai-agent 코어를 backend 패키지로 가져갈 방법을 정한다.
5. FastAPI route를 만든다.
6. route에서 인증된 user_id를 사용하도록 한다.
7. 민감 건강정보 동의가 없으면 실행을 막는다.
8. AgentInput을 DailyHealthAgentAppAdapter에 넘긴다.
9. AgentOutput을 API 응답으로 반환한다.
10. agent_runs 저장을 붙인다.
11. confirmed 결과에만 agent_memory 저장을 붙인다.
12. 테스트와 compile을 돌린다.
13. PR을 작게 올린다.
```

이때도 원칙은 같습니다.

```text
LLM은 설명만 한다.
건강 판단은 deterministic engine이 한다.
사용자 승인 전에는 저장/액션 실행을 하지 않는다.
민감 정보는 최소한만 prompt와 로그에 남긴다.
```

## 22. 전체 흐름을 한 번에 보기

최종적으로 의도한 흐름은 다음입니다.

```text
사용자 음식/영양제 입력
  |
  v
OCR 또는 수동 입력
  |
  v
IntakeSource로 출처와 user_confirmed 상태 보존
  |
  v
미승인 OCR인가?
  |
  +-- 예 --> preview-only AgentOutput
  |          findings/recommendations/actions 없음
  |
  +-- 아니오 --> NutritionEngine / SupplementEngine 실행
                  |
                  v
                PersonalizationAgent가 사용자 맥락 반영
                  |
                  v
                CoachingAgent가 추천 생성
                  |
                  v
                SafetyGuard가 추천과 trace 검사
                  |
                  v
                ActionAgent가 승인 필요한 액션 후보 생성
                  |
                  v
                ChatAgent가 설명 문장 생성
                  |
                  v
                LLM 사용 시에도 SafetyGuard 검사
                  |
                  v
                AgentOutput 반환
```

## 23. 2026-05-19 memory loop and SGLang update

이번 동기화로 `changmin-aiagent/ai-agent` 독립 패키지는 backend integration에서
필요한 소비 경계까지 따라왔습니다.

### `SGLangClient`

`SGLangClient`는 `OpenAICompatibleClient`를 상속합니다. 기본 endpoint는
`http://127.0.0.1:30000/v1`이고, 호출 경로는 `/chat/completions`입니다.

```python
from lemon_ai_agent.llm import SGLangClient

client = SGLangClient(model="qwen-local")
```

`LLMRequest`에는 `response_format`가 추가되었습니다. 그래서 structured output이
필요한 호출은 JSON Schema payload를 그대로 전달할 수 있습니다.

```python
LLMRequest(
    messages=[LLMMessage(role="user", content="summarize")],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "coaching_summary",
            "schema": {"type": "object"},
        },
    },
)
```

SGLang은 건강 판단자가 아닙니다. Lemon Aid에서 건강 판단은 계속
`NutritionEngine`, `SupplementEngine`, `SafetyGuard`가 맡고, SGLang은 설명과
구조화 보조 역할만 합니다.

### Agent memory context

`PersonalizationContext`에 `agent_memory`가 추가되었습니다. backend route가
`agent_memory` table에서 요약 기억을 읽어 `context["agent_memory"]`로 넣으면,
standalone adapter가 이 값을 `DailyHealthAgent.run(..., agent_memory=...)`으로
전달합니다.

현재 `CoachingAgent`가 읽는 대표 형태는 다음입니다.

```python
{
    "summaries": [
        {
            "memory_type": "nutrition_patterns",
            "summary_json": {
                "repeated_nutrient_patterns": {
                    "protein": 3,
                    "sodium": 2,
                }
            },
        }
    ]
}
```

반복 횟수가 기준 이상이면 recommendation rationale에 최근 confirmed records에서
반복되었다는 설명이 붙고 priority가 소폭 올라갑니다. 이 값은 확정된 기록의 요약만
써야 합니다.

### Preview and logging rule

미확정 OCR source가 있으면 결과는 preview입니다. 이 상태에서는 findings,
recommendations, actions를 만들지 않고, standalone adapter도 run log를 남기지
않습니다. backend integration에서도 같은 원칙으로 `agent_memory`와 `agent_runs`를
쓰지 않습니다.

### What this package still does not do

이 패키지는 DB migration, ORM model, 실제 memory persistence를 소유하지 않습니다.
그 부분은 `ai-agent-backend-integration` backend checkout의 책임입니다. 여기서는
Agent가 memory를 안전하게 소비하고, adapter protocol 경계로 연결될 수 있게 합니다.

### Backend live verification status

backend integration checkout에서는 `agent_memory`와 `agent_runs`를 실제 DB migration
대상으로 추가했습니다. 이때 기존 Alembic revision id
`0005_create_learning_vector_tables`가 Alembic 기본 version table 길이 32를 넘어
fresh PostgreSQL migration이 실패할 수 있었습니다.

해결 방식은 migration id를 바꾸지 않고 `backend/alembic/env.py`에서
`alembic_version.version_num` 길이를 80으로 확장하는 것입니다. revision id를
바꾸면 이미 적용된 DB와 migration history가 어긋날 수 있기 때문입니다.

검증은 conda `lemon-sglang` 환경의 PostgreSQL 16.10과 pgvector 0.8.1 test DB에서
수행했습니다.

```powershell
$env:RUN_POSTGRES_MIGRATION_SMOKE='1'
$env:TEST_DATABASE_URL='postgresql+asyncpg://postgres@127.0.0.1:55432/lemon_agent_smoke'
python -m pytest -o addopts='' backend\Nutrition-backend\tests\integration\db\test_alembic_migration_smoke.py -q
```

결과는 `1 passed`입니다. 이후 SGLang live smoke도 WSL2/Docker/GPU runtime으로
검증했습니다. Windows 직접 설치와 conda Python 환경은 `flashinfer_python` symlink
권한(`WinError 1314`)에 막혔기 때문에, 실제 로컬 runtime은
`lmsysorg/sglang:latest-cu129-runtime` Docker image를 사용했습니다.

검증된 SGLang 설정은 다음입니다.

```powershell
.\ai-agent\scripts\check-local-sglang.ps1 -RunLiveSmoke
```

내부적으로는 `RUN_SGLANG_SMOKE=1`, `SGLANG_BASE_URL=http://localhost:30000/v1`,
`SGLANG_MODEL=Qwen/Qwen2.5-0.5B-Instruct`, `SGLANG_API_KEY=EMPTY`를 사용하며,
ai-agent의 `SGLangClient`가 실제 `/v1/chat/completions` endpoint를 호출합니다.
검증 결과는 `1 test OK`입니다.

## 24. 공식 참고 문서

이 프로젝트에서 공식 문서를 기준으로 봐야 하는 기술은 다음입니다.

### Ollama

로컬 개발용 LLM 실행 후보입니다.

- [Ollama API](https://docs.ollama.com/api)
- [Ollama Chat API](https://docs.ollama.com/api/chat)

### SGLang

운영 후보 self-hosted LLM serving입니다. OpenAI-compatible API와 structured output
검증 흐름을 확인할 때 기준으로 봅니다.

- [SGLang GitHub](https://github.com/sgl-project/sglang)
- [SGLang Structured Outputs](https://docs.sglang.io/docs/advanced_features/structured_outputs)
- [SGLang Model Gateway](https://docs.sglang.io/docs/advanced_features/sgl_model_gateway)

### vLLM

SGLang과 같은 API 형태로 대체 가능성을 검토할 수 있는 OpenAI-compatible backend입니다.

- [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/)

### OpenAI-compatible Chat Completions

SGLang, vLLM 같은 서버가 맞추는 API 형태입니다.

- [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)

### Pydantic

앱 통합용 `AgentInput`/`AgentOutput` 같은 API 계약 모델에 사용합니다.

- [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic Fields](https://docs.pydantic.dev/latest/concepts/fields/)

### FastAPI

나중에 backend route로 붙일 때 기준이 되는 웹 프레임워크입니다.

- [FastAPI Request Body](https://fastapi.tiangolo.com/tutorial/body/)

### Python 표준 라이브러리

HTTP mock과 client 구현에 사용했습니다.

- [urllib.request](https://docs.python.org/3/library/urllib.request.html)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

## 25. 공부할 때 추천 순서

코드를 처음 읽는다면 다음 순서가 가장 이해하기 쉽습니다.

```text
1. ai-agent/README.md
2. ai-agent/docs/architecture.md
3. ai-agent/src/lemon_ai_agent/schemas.py
4. ai-agent/src/lemon_ai_agent/orchestrator.py
5. ai-agent/src/lemon_ai_agent/engines/nutrition.py
6. ai-agent/src/lemon_ai_agent/guards/safety.py
7. ai-agent/src/lemon_ai_agent/agents/chat.py
8. ai-agent/src/lemon_ai_agent/llm/base.py
9. ai-agent/src/lemon_ai_agent/llm/fake.py
10. ai-agent/src/lemon_ai_agent/llm/ollama.py
11. ai-agent/src/lemon_ai_agent/llm/openai_compatible.py
12. ai-agent/src/lemon_ai_agent/llm/sglang.py
13. ai-agent/src/lemon_ai_agent/adapters/app.py
14. ai-agent/tests/test_daily_health_agent.py
15. ai-agent/tests/test_llm_and_chat_agent.py
16. ai-agent/tests/test_app_adapter.py
```

처음에는 테스트부터 보는 것도 좋습니다. 테스트는 "이 코드가 어떤 동작을 보장하려고
하는지"를 가장 직접적으로 보여줍니다.

## 26. 한 문장으로 요약

이번 작업은 Lemon Aid의 건강관리 AI Agent를 "판단은 검증 가능한 코드가 하고,
LLM은 안전 검사를 거친 설명만 담당하는 구조"로 만들고, 나중에 실제 앱 backend에
붙일 수 있도록 adapter와 테스트, 문서까지 준비한 작업입니다.
