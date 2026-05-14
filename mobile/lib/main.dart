// main.dart — Lemon Aid 앱 진입점

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

import 'app.dart';
import 'utils/oauth_config.dart';
import 'utils/tokens.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // ─── 카카오 SDK 초기화 ──────────────────────
  // 보안: Native App Key 는 dart-define 으로만 주입. 소스에 박지 않음.
  //   flutter run --dart-define=KAKAO_NATIVE_APP_KEY=xxxx
  // 키 없으면 init 자체를 건너뛰고, 로그인 버튼 누를 때 안내.
  if (OAuthConfig.hasKakaoKey) {
    KakaoSdk.init(nativeAppKey: OAuthConfig.kakaoNativeAppKey);
  } else {
    debugPrint(
      '[OAuth] KAKAO_NATIVE_APP_KEY not provided — Kakao login disabled. '
      'Build with --dart-define=KAKAO_NATIVE_APP_KEY=xxxx to enable.',
    );
  }

  // 시스템 바 — 앱 시작부터 크림 배경으로 강제
  // (Login·기타 화면에서 AnnotatedRegion 으로 덮어쓰기 가능)
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
      statusBarBrightness: Brightness.light,
      systemNavigationBarColor: LemonColors.bg,
      systemNavigationBarIconBrightness: Brightness.dark,
      systemNavigationBarDividerColor: LemonColors.bg,
      systemNavigationBarContrastEnforced: false,
    ),
  );

  // TODO(A): D2에 추가
  // - Isar 초기화 (오프라인 큐)
  // - flutter_local_notifications 초기화
  // - 환경 변수 로드 (API_BASE_URL)

  runApp(
    const ProviderScope(
      child: LemonAidApp(),
    ),
  );
}
