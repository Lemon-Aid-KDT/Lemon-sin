# Mobile

Lemon Aid 모바일 MVP 작업 공간입니다. 기본 구현 트랙은 Flutter이며,
현재 `flutter_app/`에는 AI Agent daily-coaching API를 실제 백엔드 endpoint에
연결하는 초기 shell이 들어 있습니다.

```text
mobile/
├── CLAUDE.md
├── README.md
└── flutter_app/
    ├── lib/
    │   ├── core/
    │   ├── features/ai_coaching/
    │   └── shared/widgets/
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

Flutter CLI가 설치된 환경에서는 `mobile/flutter_app`에서 다음을 실행합니다.

```bash
flutter pub get
flutter analyze
flutter test
```
