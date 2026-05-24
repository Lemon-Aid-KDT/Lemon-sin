// utils/router.dart — go_router 7화면 라우팅
//
// 담당: A 프론트 리드 (라우팅 D2)
// 참조: PROJECT_GUIDE.md §3.4 인증·온보딩 흐름 / §3.5 주요 화면

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../screens/splash_screen.dart';
import '../screens/auth/login_screen_v3.dart';
import '../screens/auth/signup_screen.dart';
import '../screens/auth/signup_flow_screen.dart';
import '../screens/auth/verify_email_screen.dart';
import '../screens/auth/consent_screen.dart';
import '../screens/onboarding_screen.dart';
import '../screens/camera_screen.dart';
import '../screens/analysis_result_screen.dart';
import '../screens/health_profile_screen.dart';
import '../screens/notifications_screen.dart';
import '../screens/calendar_screen.dart';
import '../screens/dashboard_screen.dart';
import '../screens/dashboard_screen_v3.dart';
import '../screens/chat_screen.dart';
import '../screens/score_screen.dart';
import '../screens/raffle_screen.dart';
import '../screens/health_screen.dart';
import '../screens/settings_screen.dart';
import '../widgets/common/main_shell.dart';
import 'page_transitions.dart';
import '../devtools/tokens_preview.dart';

/// 앱 라우트 경로
class AppRoute {
  static const String splash       = '/';
  static const String login        = '/login';      // 메인 (Login v3 - Hybrid Flat + 뉴모 액센트)
  static const String signup       = '/signup';
  static const String verifyEmail  = '/verify-email';
  static const String consent      = '/consent';
  static const String onboarding   = '/onboarding';
  static const String home         = '/home';
  static const String camera       = '/camera';
  static const String analysisResult = '/analysis-result';
  static const String dashboard    = '/dashboard';
  static const String dashboardV3  = '/dashboard-v3';   // PREVIEW — LADS §13 v3 토큰 검증
  static const String chat         = '/chat';
  static const String score        = '/score';
  static const String raffle       = '/raffle';
  static const String health       = '/health';
  static const String settings     = '/settings';

  // ─── 메인 5 탭 셸 (CLAUDE.md §4.2 — 가안, 사용자와 같이 결정 중) ───
  // shellHome = '/shell' 진입점. 실제 5 branch path 는 router 내부 literal.
  static const String shellHome = '/shell';

  // ─── Devtools (디버그 빌드 전용 — 다이어리 §4 토큰 검증) ───
  static const String tokensPreview = '/devtools/tokens';
}

/// Riverpod ChangeNotifier 어댑터 — AuthState 변경 시 go_router refresh.
class _AuthRouterListenable extends ChangeNotifier {
  _AuthRouterListenable(this._ref) {
    _ref.listen<AuthState>(authControllerProvider, (_, __) {
      notifyListeners();
    });
  }
  final Ref _ref;
}

/// 라우터 Provider — Riverpod 안에서 만들어 인증 상태와 자동 연결.
final Provider<GoRouter> goRouterProvider = Provider<GoRouter>((ref) {
  final listenable = _AuthRouterListenable(ref);
  return GoRouter(
    initialLocation: AppRoute.splash,
    debugLogDiagnostics: true,
    refreshListenable: listenable,
    redirect: (context, state) {
      final auth = ref.read(authControllerProvider);
      // 부트스트랩 전엔 splash 유지 — splash 화면이 자체 분기
      if (!auth.isReady) return null;
      final path = state.matchedLocation;
      final isAuthRoute = path == AppRoute.login ||
                          path == AppRoute.signup ||
                          path == AppRoute.verifyEmail ||
                          path == AppRoute.consent ||
                          path == AppRoute.splash;
      // 로그인 안 됐는데 보호 라우트로 가려는 경우
      if (!auth.isAuthenticated && !isAuthRoute) {
        return AppRoute.login;
      }
      // 로그인 됐는데 login 화면이면 셸로
      // (OAuth 신규 사용자 → signup_flow 분기는 listener 측에서 화면 진입 후 한 번 처리)
      if (auth.isAuthenticated && path == AppRoute.login) {
        return '/shell/home';
      }
      return null;
    },
    routes: [
    // Splash 라우트는 라우터에 등록되어 있지만 initialLocation에서 빠짐
    // 필요시 (백엔드 인증 체크) /splash 로 명시 진입 가능
    GoRoute(
      path: AppRoute.splash,
      name: 'splash',
      pageBuilder: (context, state) => fadePage(state, const SplashScreen()),
    ),

    // 인증 흐름 (§3.4)
    // 메인 로그인 — 최종 확정 (2026-05-12 / UX_DIARY §14.10 Hybrid 시스템)
    GoRoute(
      path: AppRoute.login,
      name: 'login',
      pageBuilder: (context, state) => fadePage(state, const LoginScreenV3()),
    ),
    GoRoute(
      path: AppRoute.signup,
      name: 'signup',
      // 2026-05-18: 10-step flow 로 교체 (Claude Design v1 구성 차용)
      // /signup?oauth=1&consented=1&mk=1&name=xxx&email=xxx
      //   - oauth=1   : 이메일/비번/인증 단계 스킵
      //   - consented=1 : 약관 사전 동의 (step 10 약관 화면 스킵)
      //   - mk=1      : 마케팅 동의 여부
      //   - name/email: 프리필
      pageBuilder: (context, state) {
        final qp = state.uri.queryParameters;
        return slidePage(
          state,
          SignupFlowScreen(
            oauthMode: qp['oauth'] == '1',
            preConsented: qp['consented'] == '1',
            marketingAgreed: qp['mk'] == '1',
            prefillName: qp['name'],
            prefillEmail: qp['email'],
          ),
        );
      },
    ),
    // 기존 단순 signup (이메일/비번만) 은 별도 경로로 백업
    GoRoute(
      path: '/signup-legacy',
      name: 'signup-legacy',
      pageBuilder: (context, state) => slidePage(state, const SignupScreen()),
    ),
    GoRoute(
      path: AppRoute.verifyEmail,
      name: 'verifyEmail',
      pageBuilder: (context, state) => slidePage(
        state,
        VerifyEmailScreen(email: state.uri.queryParameters['email']),
      ),
    ),
    GoRoute(
      path: AppRoute.consent,
      name: 'consent',
      pageBuilder: (context, state) => modalPage(state, const ConsentScreen()),
    ),
    GoRoute(
      path: AppRoute.onboarding,
      name: 'onboarding',
      pageBuilder: (context, state) =>
          slidePage(state, const OnboardingScreen()),
    ),

    // 메인 화면 (§3.5)
    GoRoute(
      path: AppRoute.home,
      name: 'home',
      pageBuilder: (context, state) => fadePage(state, const DashboardScreen()),
    ),
    GoRoute(
      path: AppRoute.camera,
      name: 'camera',
      pageBuilder: (context, state) => modalPage(state, const CameraScreen()),
    ),
    // analysis-result / health-profile / notifications / calendar 는
    // StatefulShellRoute 의 sub-route 로 이동 (하단 탭바 유지).
    // → 아래 5탭 셸 branch 안에 정의됨.
    GoRoute(
      path: AppRoute.dashboard,
      name: 'dashboard',
      pageBuilder: (context, state) =>
          fadePage(state, const DashboardScreen()),
    ),
    // PREVIEW — Dashboard v3 (LADS §13). Claude Design Export ZIP 도착 시 본 화면 교체.
    GoRoute(
      path: AppRoute.dashboardV3,
      name: 'dashboardV3',
      pageBuilder: (context, state) =>
          fadePage(state, const DashboardScreenV3()),
    ),
    GoRoute(
      path: AppRoute.chat,
      name: 'chat',
      pageBuilder: (context, state) => slidePage(state, const ChatScreen()),
    ),
    GoRoute(
      path: AppRoute.score,
      name: 'score',
      pageBuilder: (context, state) => slidePage(state, const ScoreScreen()),
    ),
    GoRoute(
      path: AppRoute.raffle,
      name: 'raffle',
      pageBuilder: (context, state) => slidePage(state, const RaffleScreen()),
    ),
    GoRoute(
      path: AppRoute.health,
      name: 'health',
      pageBuilder: (context, state) => slidePage(state, const HealthScreen()),
    ),
    GoRoute(
      path: AppRoute.settings,
      name: 'settings',
      pageBuilder: (context, state) =>
          slidePage(state, const SettingsScreen()),
    ),

    // ─── 메인 5 탭 셸 (CLAUDE.md §4.2 — 가안) ───
    // /shell 단독 진입 시 홈 branch 로 redirect.
    GoRoute(
      path: AppRoute.shellHome,
      redirect: (context, state) =>
          state.uri.path == AppRoute.shellHome ? '/shell/home' : null,
    ),
    // StatefulShellRoute.indexedStack — 5 branch 각자 navigation stack 보존.
    // navigationShell 이 IndexedStack 으로 5 페이지 상태 보존을 자동 처리.
    StatefulShellRoute.indexedStack(
      builder: (context, state, navigationShell) =>
          MainShell(navigationShell: navigationShell),
      branches: <StatefulShellBranch>[
        StatefulShellBranch(
          routes: <RouteBase>[
            GoRoute(
              path: '/shell/home',
              name: 'shellHome',
              builder: (context, state) => const DashboardScreen(),
              // 홈에서 들어가는 상세 화면 — 셸 안이라 하단 탭바 유지
              routes: <RouteBase>[
                // 과거 기록 조회 — 메인과 같은 구성, 풀스크린
                GoRoute(
                  path: 'record',
                  name: 'dayRecord',
                  pageBuilder: (context, state) {
                    final dateStr = state.uri.queryParameters['date'];
                    final date = dateStr != null
                        ? DateTime.tryParse(dateStr)
                        : null;
                    return slidePage(
                      state,
                      DashboardScreen(recordDate: date),
                    );
                  },
                ),
                GoRoute(
                  path: 'analysis-result',
                  name: 'shellAnalysisResult',
                  pageBuilder: (context, state) {
                    final mode =
                        state.uri.queryParameters['mode'] ?? 'supplement';
                    return modalPage(state, AnalysisResultScreen(mode: mode));
                  },
                ),
                GoRoute(
                  path: 'notifications',
                  name: 'shellNotifications',
                  pageBuilder: (context, state) =>
                      slidePage(state, const NotificationsScreen()),
                ),
                GoRoute(
                  path: 'calendar',
                  name: 'shellCalendar',
                  pageBuilder: (context, state) =>
                      slidePage(state, const CalendarScreen()),
                ),
              ],
            ),
          ],
        ),
        StatefulShellBranch(
          routes: <RouteBase>[
            GoRoute(
              path: '/shell/camera',
              name: 'shellCamera',
              builder: (context, state) => const CameraScreen(),
            ),
          ],
        ),
        StatefulShellBranch(
          routes: <RouteBase>[
            GoRoute(
              path: '/shell/chat',
              name: 'shellChat',
              builder: (context, state) => const ChatScreen(),
            ),
          ],
        ),
        StatefulShellBranch(
          routes: <RouteBase>[
            GoRoute(
              path: '/shell/score',
              name: 'shellScore',
              builder: (context, state) => const ScoreScreen(),
            ),
          ],
        ),
        StatefulShellBranch(
          routes: <RouteBase>[
            GoRoute(
              path: '/shell/settings',
              name: 'shellSettings',
              builder: (context, state) => const SettingsScreen(),
              // 설정에서 들어가는 상세 화면 — 셸 안이라 하단 탭바 유지
              routes: <RouteBase>[
                GoRoute(
                  path: 'health-profile',
                  name: 'shellHealthProfile',
                  pageBuilder: (context, state) {
                    final tab = state.uri.queryParameters['tab'] ?? 'disease';
                    return slidePage(
                        state, HealthProfileScreen(initialTab: tab));
                  },
                ),
              ],
            ),
          ],
        ),
      ],
    ),

    // Devtools — 디버그 빌드에서만 진입
    GoRoute(
      path: AppRoute.tokensPreview,
      name: 'tokensPreview',
      pageBuilder: (context, state) => fadePage(state, const TokensPreview()),
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
});
