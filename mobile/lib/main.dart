// main.dart — Lemon Aid 앱 진입점

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'utils/tokens.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

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
