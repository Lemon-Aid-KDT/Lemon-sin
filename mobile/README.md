# Mobile

Lemon Aid 모바일 MVP 작업 공간입니다. 기본 구현 트랙은 Flutter이며,
현재 `flutter_app/`에는 dashboard shell, secure token store, AI Agent
daily-coaching API client, 영양제 촬영 권한/이미지 선택, 영양제 분석 preview
multipart API 연결이 들어 있습니다. `origin/taedong-design`의 루트 `mobile/`
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

## taedong-design에서 선별 반영한 연결점

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
