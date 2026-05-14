// app.dart — Lemon Aid 앱 셸 (테마 + 라우터)
//
// 담당: A 프론트 리드
// 참조: PROJECT_GUIDE.md §13 파일 구조, §4.2 UX 원칙

import 'package:flutter/material.dart';
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
      // 한국어 우선
      locale: const Locale('ko', 'KR'),
    );
  }
}
