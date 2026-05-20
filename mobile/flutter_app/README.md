# Lemon Aid Flutter App

초기 모바일 MVP shell입니다. 현재 연결된 첫 실제 API flow는
`/api/v1/me/privacy/consents/sensitive_health_analysis` 동의 생성 후
`/api/v1/ai-agent/daily-coaching`을 호출하는 AI Agent daily coaching입니다.

## Local API 연결

백엔드 smoke 서버가 `http://127.0.0.1:18080`에서 실행 중이면 기본값으로 바로 붙습니다.

```bash
flutter pub get
flutter run --dart-define=LEMON_API_BASE_URL=http://127.0.0.1:18080
```

JWT 인증 모드에서는 토큰을 앱 storage adapter로 넣기 전까지 개발용 dart define으로만 주입합니다.

```bash
flutter run \
  --dart-define=LEMON_API_BASE_URL=https://staging-api.example.com \
  --dart-define=LEMON_AUTH_TOKEN=<access-token>
```

토큰과 민감 건강 데이터는 로그에 남기지 않습니다. 화면은 백엔드 결과를 표시만 하며,
영양/의료 판단은 백엔드 API와 Agent contract를 단일 진실로 둡니다.
