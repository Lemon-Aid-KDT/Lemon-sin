# Mobile

Lemon Aid 모바일 MVP 작업 공간입니다. 기본 구현 트랙은 Flutter이며,
현재 `flutter_app/`에는 dashboard shell, taedong-inspired bottom shell,
secure token store, AI Agent daily-coaching API client, 영양제 촬영 권한/이미지 선택, 영양제 분석 preview와
확정 저장 flow, 음식 사진+수동 입력 확인 flow, confirmed food/supplement 기반
coaching payload 조립이 들어 있습니다. `origin/taedong-design`의 루트 `mobile/`
Flutter 앱은 UI/UX와 인증 흐름의 후보 원천으로 확인했지만, 현재 백엔드에는
`/api/v1/auth/*` 라우트가 아직 없으므로 직접 병합하지 않고 호환 가능한 모델과
API 연결층부터 선별 반영합니다.

```text
mobile/
├── CLAUDE.md
├── README.md
└── flutter_app/
    ├── lib/
    │   ├── core/
    │   ├── features/ai_coaching/
    │   ├── features/food/
    │   ├── features/supplement/
    │   └── shared/
    ├── test/
    ├── pubspec.yaml
    └── analysis_options.yaml
```

## 현재 연결된 flow

1. 민감 건강 분석 동의 생성:
   `POST /api/v1/me/privacy/consents/sensitive_health_analysis`
2. 확인된 식단 payload로 AI Agent 코칭 요청:
   `POST /api/v1/ai-agent/daily-coaching`
3. 응답의 `provider`, `used_tools`, `agent_memory` 사용 여부를 화면에 표시
4. 영양제 촬영 화면에서 카메라 권한 요청 또는 갤러리 이미지 선택
5. OCR 이미지 처리 동의 생성 후 `POST /api/v1/supplements/analyze` multipart 호출
6. 분석 preview를 사용자가 확인/수정한 뒤 `user_confirmed=true` payload로
   `POST /api/v1/supplements` 저장
7. 음식 입력 화면에서 사진 선택과 수동 음식명/끼니/섭취량 확인 payload 생성
8. 음식 flow는 음식 인식 모델이나 영양성분 DB lookup을 구현하지 않고,
   확인된 입력만 AI Agent 연결 후보로 유지
9. Daily coaching payload는 하드코딩된 OCR/영양성분 샘플 대신 confirmed
   food/supplement entry 목록에서 조립
10. `shared/state/confirmed_entry_store.dart`는 앱 세션 안에서 확인된 음식·영양제
    entry를 보관하고 daily coaching 화면에 전달
11. `shared/widgets/lemon_main_shell.dart`는 home/coaching 하단 셸과 중앙 기록 버튼을
    제공하고, 음식·영양제 capture flow는 full-screen route로 유지
12. `shared/widgets/capture_frame_card.dart`는 음식/영양제 공통 촬영 프레임과
    camera/gallery 선택 UX를 제공합니다.
13. `features/capture_result/`는 confirmed 저장 후 결과 화면을 보여주며,
    이후 taedong analysis-result 상세 UX를 확장할 위치입니다.
14. debug build에서는 Daily coaching 화면의 `개발용 샘플로 LLM 코칭 실행`
    버튼으로 사진 없이 confirmed sample을 넣고 실제 coaching API 호출을 확인할 수 있습니다.

## taedong-design에서 선별 반영한 연결점

- `origin/taedong-design`의 5-tab shell 아이디어를 현재 라우트에 맞춰
  `LemonMainShell`로 축소 이식했습니다.
- `origin/taedong-design`의 camera/analysis-result UX는 full app merge 없이
  `CaptureFrameCard`와 `CaptureResultScreen`으로 축소 이식했습니다.
- 사진 인식 모델이 준비되기 전 LLM 흐름 확인을 위해 debug-only dev sample seeding을
  추가했습니다. 이 샘플은 production 기록이 아니며 food nutrient를 임의 생성하지 않습니다.
- taedong root `mobile/` app/router/auth tree는 아직 직접 병합하지 않습니다.
- Android 에뮬레이터에서 로컬 백엔드 호출이 되도록 기본 API 주소를
  `http://10.0.2.2:18080`로 분기합니다.
- 데스크톱/WSL/PowerShell 확인은 `http://127.0.0.1:18080`, 웹은
  `http://localhost:18080` 기본값을 사용합니다.
- 실제 환경에서는 `--dart-define=LEMON_API_BASE_URL=<url>`로 명시 주소를
  넘기는 방식을 우선합니다.
- `shared/models/`에는 `AgentMemory`, `AnalysisResult`, `Supplement` loose model을
  두어 taedong UI를 이식할 때 원본 backend payload를 `raw`로 보존합니다.

Flutter CLI가 설치된 환경에서는 `mobile/flutter_app`에서 다음을 실행합니다.

```bash
flutter pub get
flutter analyze
flutter test
```

## 로컬 LLM coaching 실행 순서

Flutter web에서 개발용 샘플 코칭 버튼을 쓰려면 SGLang뿐 아니라 FastAPI도 켜져 있어야 합니다.

1. Docker Desktop에서 `lemon-sglang` 컨테이너가 실행 중인지 확인합니다.
2. 새 PowerShell에서 backend dev stack을 전면 실행합니다.

   ```powershell
   cd C:\MyWorkspace\lemon_aid\ai-agent-backend-integration
   powershell -ExecutionPolicy Bypass -File scripts\start_ai_agent_dev_stack.ps1 -Foreground
   ```

   이 스크립트는 Flutter web origin `http://localhost:52100`을 CORS 허용 목록에 넣고
   FastAPI를 `http://127.0.0.1:18080`에서 실행합니다.

3. 다른 PowerShell에서 Flutter web을 실행합니다.

   ```powershell
   cd C:\MyWorkspace\lemon_aid\ai-agent-backend-integration\mobile\flutter_app
   flutter run -d chrome --web-port 52100
   ```

4. 앱의 Daily coaching 화면에서 `개발용 샘플로 LLM 코칭 실행`을 누릅니다.
