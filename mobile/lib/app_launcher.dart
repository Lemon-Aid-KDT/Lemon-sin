import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

import 'app.dart';
import 'utils/device_env.dart';
import 'utils/oauth_config.dart';
import 'utils/tokens.dart';

Future<void> runLemonAidApp() async {
  // ─── .env 로드 (개발 편의용 — flutter_dotenv) ─
  // .env 파일이 없거나 못 읽어도 에러 X — dart-define 폴백 동작
  try {
    await dotenv.load(fileName: '.env');
  } catch (e) {
    debugPrint('[env] .env 파일 미발견 — dart-define 으로 fallback ($e)');
  }

  // ─── 에뮬/실기기 감지 (캐시) ─────────────────
  // 카메라 화면에서 분기용. 한 번 호출 후 동기 접근 가능.
  await DeviceEnv.warmUp();
  debugPrint('[env] isEmulator = ${DeviceEnv.isEmulatorSync}');

  // ─── 카카오 SDK 초기화 ──────────────────────
  if (OAuthConfig.hasKakaoKey) {
    KakaoSdk.init(nativeAppKey: OAuthConfig.kakaoNativeAppKey);
  } else {
    debugPrint(
      '[OAuth] KAKAO_NATIVE_APP_KEY not provided — Kakao login disabled. '
      'mobile/.env 또는 --dart-define 으로 주입하세요.',
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
