# mobile/ — Flutter 앱

> 담당: **A 프론트 리드** + **B UI/UX**
> 참조: §4 기술 스택 - 프론트엔드, §13 파일 구조, §부록 A.7 pubspec.yaml

## D1 셋업

```bash
flutter create --org com.lemonaid --project-name lemon_aid .
flutter pub get
flutter run
```

`pubspec.yaml`에 §부록 A.7 의존성 추가.

## 폴더 책임

| 폴더 | 담당 |
|------|------|
| lib/screens/ | A — 7화면 라우팅 |
| lib/widgets/ | B — 재사용 위젯 |
| lib/services/ | A — API·헬스·알림·캘린더 |
| lib/providers/ | A — Riverpod 전역 상태 |
| lib/models/ | A — freezed 데이터 클래스 |
| lib/utils/ | A — 디자인 토큰·날짜·포매터 |
