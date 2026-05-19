// app.dart — Lemon Aid 앱 셸 (테마 + 라우터)
//
// 담당: A 프론트 리드
// 참조: PROJECT_GUIDE.md §13 파일 구조, §4.2 UX 원칙

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'utils/router.dart';
import 'utils/tokens.dart';

class LemonAidApp extends ConsumerWidget {
  const LemonAidApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(goRouterProvider);
    return MaterialApp.router(
      title: 'Lemon Aid',
      debugShowCheckedModeBanner: false,
      theme: buildLemonTheme(),
      routerConfig: router,
      // 2026-05-18: 한국어 로케일 + Material/Widgets/Cupertino delegate 등록
      // showDatePicker 등 Material 위젯이 한국어 + 한국 형식으로 표시됨
      locale: const Locale('ko', 'KR'),
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('ko', 'KR'),
        Locale('en', 'US'),
      ],
    );
  }
}
