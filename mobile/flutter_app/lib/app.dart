import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'features/ai_coaching/presentation/daily_coaching_screen.dart';

final GoRouter appRouter = GoRouter(
  routes: <RouteBase>[
    GoRoute(
      path: '/',
      builder: (BuildContext context, GoRouterState state) => const DailyCoachingScreen(),
    ),
  ],
);

class LemonAidApp extends StatelessWidget {
  const LemonAidApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Lemon Aid',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2E7D32)),
        useMaterial3: true,
      ),
      routerConfig: appRouter,
    );
  }
}
