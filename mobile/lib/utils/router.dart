// utils/router.dart — go_router 7화면 라우팅
//
// 담당: A 프론트 리드 (라우팅 D2)
// 참조: PROJECT_GUIDE.md §3.4 인증·온보딩 흐름 / §3.5 주요 화면

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../screens/splash_screen.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/signup_screen.dart';
import '../screens/auth/verify_email_screen.dart';
import '../screens/auth/consent_screen.dart';
import '../screens/onboarding_screen.dart';
import '../screens/camera_screen.dart';
import '../screens/dashboard_screen.dart';
import '../screens/chat_screen.dart';
import '../screens/score_screen.dart';
import '../screens/raffle_screen.dart';
import '../screens/health_screen.dart';
import '../screens/settings_screen.dart';
import '../devtools/tokens_preview.dart';

/// 앱 라우트 경로
class AppRoute {
  static const String splash       = '/';
  static const String login        = '/login';
  static const String signup       = '/signup';
  static const String verifyEmail  = '/verify-email';
  static const String consent      = '/consent';
  static const String onboarding   = '/onboarding';
  static const String home         = '/home';
  static const String camera       = '/camera';
  static const String dashboard    = '/dashboard';
  static const String chat         = '/chat';
  static const String score        = '/score';
  static const String raffle       = '/raffle';
  static const String health       = '/health';
  static const String settings     = '/settings';

  // ─── Devtools (디버그 빌드 전용 — 다이어리 §4 토큰 검증) ───
  static const String tokensPreview = '/devtools/tokens';
}

/// 라우터 생성. 인증 가드는 D2에 auth_provider와 연결해서 추가.
final GoRouter appRouter = GoRouter(
  initialLocation: AppRoute.splash,
  debugLogDiagnostics: true,
  routes: [
    GoRoute(
      path: AppRoute.splash,
      name: 'splash',
      builder: (context, state) => const SplashScreen(),
    ),

    // 인증 흐름 (§3.4)
    GoRoute(
      path: AppRoute.login,
      name: 'login',
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: AppRoute.signup,
      name: 'signup',
      builder: (context, state) => const SignupScreen(),
    ),
    GoRoute(
      path: AppRoute.verifyEmail,
      name: 'verifyEmail',
      builder: (context, state) => const VerifyEmailScreen(),
    ),
    GoRoute(
      path: AppRoute.consent,
      name: 'consent',
      builder: (context, state) => const ConsentScreen(),
    ),
    GoRoute(
      path: AppRoute.onboarding,
      name: 'onboarding',
      builder: (context, state) => const OnboardingScreen(),
    ),

    // 메인 화면 (§3.5)
    GoRoute(
      path: AppRoute.home,
      name: 'home',
      builder: (context, state) => const DashboardScreen(),
    ),
    GoRoute(
      path: AppRoute.camera,
      name: 'camera',
      builder: (context, state) => const CameraScreen(),
    ),
    GoRoute(
      path: AppRoute.dashboard,
      name: 'dashboard',
      builder: (context, state) => const DashboardScreen(),
    ),
    GoRoute(
      path: AppRoute.chat,
      name: 'chat',
      builder: (context, state) => const ChatScreen(),
    ),
    GoRoute(
      path: AppRoute.score,
      name: 'score',
      builder: (context, state) => const ScoreScreen(),
    ),
    GoRoute(
      path: AppRoute.raffle,
      name: 'raffle',
      builder: (context, state) => const RaffleScreen(),
    ),
    GoRoute(
      path: AppRoute.health,
      name: 'health',
      builder: (context, state) => const HealthScreen(),
    ),
    GoRoute(
      path: AppRoute.settings,
      name: 'settings',
      builder: (context, state) => const SettingsScreen(),
    ),

    // Devtools — 디버그 빌드에서만 진입
    GoRoute(
      path: AppRoute.tokensPreview,
      name: 'tokensPreview',
      builder: (context, state) => const TokensPreview(),
    ),
  ],

  errorBuilder: (context, state) => Scaffold(
    appBar: AppBar(title: const Text('오류')),
    body: Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              '페이지를 찾을 수 없어요',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 12),
            Text(
              state.error?.toString() ?? '알 수 없는 경로',
              style: const TextStyle(fontSize: 14, color: Colors.grey),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => context.go(AppRoute.home),
              child: const Text('홈으로'),
            ),
          ],
        ),
      ),
    ),
  ),
);
