# 로컬 SGLang 런타임 체크리스트

작성일: 2026-05-20

이 문서는 Windows + WSL2 + Docker Desktop 환경에서 로컬 GPU LLM 서버를
실행하고 검증한 내용을 기록합니다. 다음 ai-agent 연동 작업을 이어갈 때 이
흐름을 그대로 따라가기 위한 작업 노트입니다.

## 현재 완료 상태

- WSL2가 설치되어 있고 정상 동작합니다.
- WSL2 배포판이 등록되어 있습니다.
  - `Ubuntu`
  - `Ubuntu-Dev`
- `Ubuntu-Dev` 안에서 NVIDIA GPU가 보입니다.
- Windows NVIDIA 드라이버가 정상 동작합니다.
  - 확인된 드라이버 버전: `577.03`
  - `nvidia-smi`에서 확인된 CUDA 지원 버전: `12.9`
  - 확인된 GPU: `NVIDIA GeForce RTX 5060 Laptop GPU`
- Docker Desktop이 설치되어 있고 Linux 엔진에 연결되어 있습니다.
- 일반 Docker 컨테이너 실행이 성공했습니다.
  - `docker run hello-world`로 확인
- Docker GPU 컨테이너 실행이 성공했습니다.
  - NVIDIA CUDA `nbody` 샘플로 확인
- SGLang 서버가 아래 주소로 정상 실행되었습니다.
  - Base URL: `http://localhost:30000/v1`
  - Model: `Qwen/Qwen2.5-0.5B-Instruct`
- OpenAI 호환 API 확인이 끝났습니다.
  - `GET /v1/models`에서 Qwen 모델이 반환됨
  - `POST /v1/chat/completions`에서 모델 응답이 반환됨
- ai-agent의 `SGLangClient` live smoke test가 통과했습니다.
  - `RUN_SGLANG_SMOKE=1`로 opt-in 실행
  - `python -m unittest ai-agent.tests.test_sglang_live_smoke`
  - 결과: `Ran 1 test ... OK`

## API Key 판단

현재 로컬 SGLang 테스트 서버에는 실제 API key가 필요하지 않습니다.

- 로컬 SGLang endpoint:
  - Base URL: `http://localhost:30000/v1`
  - API key: 서버를 별도 인증 옵션으로 띄우지 않는 한 필요 없음
- 일부 OpenAI-compatible client는 API key 필드 자체를 요구할 수 있습니다.
  - 이 경우 `EMPTY`, `dummy`, `local-dev` 같은 placeholder 값을 사용합니다.
- 현재 테스트한 공개 Qwen 모델에는 Hugging Face token이 필수는 아닙니다.
  - 다운로드 제한 완화나 gated/private 모델 사용 시에는 필요할 수 있습니다.
  - `HF_TOKEN`이나 실제 토큰은 repo에 커밋하지 않습니다.

## 수동 서버 실행 순서

반복 실행할 때는 아래 스크립트를 우선 사용합니다.

```powershell
.\ai-agent\scripts\start-local-sglang.ps1
```

이 스크립트는 기본적으로 다음 설정을 사용합니다.

- WSL 배포판: `Ubuntu-Dev`
- Docker image: `lmsysorg/sglang:latest-cu129-runtime`
- Model: `Qwen/Qwen2.5-0.5B-Instruct`
- Port: `30000`
- API base URL: `http://localhost:30000/v1`

서버가 실행되는 동안 이 PowerShell 터미널은 닫지 않습니다. 직접 명령을 확인하거나
문제가 생겼을 때는 아래 수동 절차를 사용합니다.

PowerShell에서 `Ubuntu-Dev`로 들어갑니다.

```powershell
wsl -d Ubuntu-Dev
```

CUDA 12.9용 SGLang 컨테이너를 실행합니다.

```bash
docker run --rm -it --gpus=all --shm-size 8g \
  -p 30000:30000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  lmsysorg/sglang:latest-cu129-runtime \
  bash
```

컨테이너 안에서 누락된 Python 패키지를 설치합니다.

```bash
python3 -m pip install --no-cache-dir distro
```

그다음 SGLang 서버를 실행합니다.

```bash
python3 -m sglang.launch_server --model-path Qwen/Qwen2.5-0.5B-Instruct --host 0.0.0.0 --port 30000
```

아래 문구가 나오면 서버가 준비된 상태입니다.

```text
The server is fired up and ready to roll!
```

로컬 LLM API를 사용하는 동안 이 터미널은 닫지 않습니다.

## PowerShell에서 검증하기

반복 확인할 때는 아래 스크립트를 우선 사용합니다.

```powershell
.\ai-agent\scripts\check-local-sglang.ps1
```

SGLang 서버 상태 확인과 ai-agent live smoke를 함께 실행하려면 다음을 사용합니다.

```powershell
.\ai-agent\scripts\check-local-sglang.ps1 -RunLiveSmoke
```

직접 확인하려면 아래 명령을 사용합니다.

모델 목록을 확인합니다.

```powershell
curl.exe http://localhost:30000/v1/models
```

채팅 요청 본문을 준비합니다.

```powershell
$body = '{"model":"Qwen/Qwen2.5-0.5B-Instruct","messages":[{"role":"user","content":"안녕"}],"max_tokens":64}'
```

채팅 completion API를 호출합니다.

```powershell
Invoke-RestMethod -Uri http://localhost:30000/v1/chat/completions -Method Post -ContentType "application/json" -Body $body
```

모델 답변 문장만 보고 싶으면 아래처럼 실행합니다.

```powershell
$response = Invoke-RestMethod -Uri http://localhost:30000/v1/chat/completions -Method Post -ContentType "application/json" -Body $body
$response.choices[0].message.content
```

검증된 예시 응답:

```text
Hello! How can I assist you today?
```

## ai-agent SGLang live smoke

SGLang 서버가 켜져 있을 때만 opt-in 테스트를 실행합니다.

반복 실행용 스크립트:

```powershell
.\ai-agent\scripts\check-local-sglang.ps1 -RunLiveSmoke
```

직접 실행 명령:

```powershell
$env:RUN_SGLANG_SMOKE='1'
$env:SGLANG_BASE_URL='http://localhost:30000/v1'
$env:SGLANG_MODEL='Qwen/Qwen2.5-0.5B-Instruct'
$env:SGLANG_API_KEY='EMPTY'
python -m unittest ai-agent.tests.test_sglang_live_smoke
```

검증된 결과:

```text
.
----------------------------------------------------------------------
Ran 1 test in 3.214s

OK
```

서버가 꺼져 있거나 `RUN_SGLANG_SMOKE=1`을 설정하지 않으면 이 테스트는 기본
테스트를 깨지 않도록 skip됩니다.

## 주의사항

- SGLang 서버는 서버 컨테이너가 실행 중일 때만 동작합니다.
- 서버 터미널을 닫거나, `Ctrl+C`를 누르거나, Docker Desktop을 종료하면
  로컬 LLM API도 중지됩니다.
- `lmsysorg/sglang:latest` 이미지는 CUDA `>=13.0`을 요구해서 실패했습니다.
- 현재 PC의 CUDA 12.9 드라이버 스택에는
  `lmsysorg/sglang:latest-cu129-runtime` 이미지가 맞았습니다.
- 현재 이미지에서는 `distro` Python 패키지를 컨테이너 안에서 임시로 설치해야
  했습니다.
- 이 문서는 런타임 검증 기록입니다. 아직 Lemon Aid backend나 ai-agent 설정에
  SGLang을 연결한 것은 아닙니다.

## 다음 TODO

- [x] 현재 단계에서는 foreground 터미널 실행 방식을 유지하기로 결정합니다.
  - 서버 로그를 바로 볼 수 있고, `Ctrl+C`로 명확히 종료할 수 있습니다.
  - 백그라운드 Docker 컨테이너나 Docker Compose 서비스는 backend route smoke 이후
    별도 운영 편의 작업으로 둡니다.
- [x] 긴 Docker 명령을 매번 직접 치지 않도록 재사용 가능한 시작/확인 스크립트를
  추가합니다.
  - `scripts/start-local-sglang.ps1`
  - `scripts/check-local-sglang.ps1`
- [x] 현재 smoke/default 로컬 모델은 `Qwen/Qwen2.5-0.5B-Instruct`로 결정합니다.
  - VRAM이 허용하는 더 큰 Qwen 모델과 한국어 응답 품질 비교는 후속 모델 평가
    작업으로 둡니다.
- [x] Lemon Aid ai-agent live smoke가 아래 설정을 사용하도록 연결했습니다.
  - `SGLANG_BASE_URL=http://localhost:30000/v1`
  - `SGLANG_MODEL=Qwen/Qwen2.5-0.5B-Instruct`
  - client가 key 값을 요구하면 `SGLANG_API_KEY=EMPTY`
- [x] 이 서버를 대상으로 ai-agent local LLM smoke test를 실행합니다.
- [x] 안전 동작을 확인합니다.
  - LLM 출력은 설명/문장화 역할만 맡습니다.
  - 영양, 보충제, 정책 판단은 deterministic engine이 계속 담당합니다.
  - 모델 출력이 위험하거나 서버가 unavailable이면 deterministic fallback을
    사용합니다.
- [x] 선택한 런타임 실행 방식을 메인 ai-agent
  setup 문서에 반영합니다.

## 참고 공식 문서

- SGLang docs: https://docs.sglang.io/
- SGLang install guide: https://sgl-project.github.io/get_started/install.html
- Docker Desktop Windows install: https://docs.docker.com/desktop/setup/install/windows-install/
- Docker Desktop GPU support: https://docs.docker.com/desktop/features/gpu/
- NVIDIA CUDA on WSL: https://docs.nvidia.com/cuda/wsl-user-guide/
