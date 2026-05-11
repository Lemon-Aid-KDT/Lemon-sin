// main.dart — Lemon Aid 앱 진입점

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

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
