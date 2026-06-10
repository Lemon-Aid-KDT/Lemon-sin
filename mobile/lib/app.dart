import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'app_controller.dart';
import 'app_providers.dart';
import 'core/config/app_config.dart';
import 'features/auth/token_session.dart';
import 'features/consent/consent_gate_screen.dart';
import 'features/supplements/supplement_models.dart';
import 'features/supplements/supplement_repository.dart';
import 'screens/analysis_result_screen.dart' as source_analysis;
import 'screens/camera_screen.dart' as source_camera;
import 'screens/chat_screen.dart' as source_chat;
import 'screens/dashboard_screen.dart' as source_dashboard;
import 'screens/score_screen.dart' as source_score;
import 'screens/settings_screen.dart' as source_settings;
import 'screens/splash_screen.dart' as source_splash;
import 'shared/theme/brand_theme_controller.dart';
import 'shared/theme/lemon_design_tokens.dart';
import 'utils/brand_palette.dart';
import 'shared/widgets/error_panel.dart';
import 'widgets/common/main_shell.dart';

/// Lemon Aid mobile application with the 17 Pro-style shell.
class LemonAidApp extends StatelessWidget {
  /// Creates the app.
  ///
  /// Args:
  ///   repository: Optional repository override for widget tests.
  ///   config: Optional runtime config override for tests.
  ///   tokenStore: Optional external JWT store override for tests.
  const LemonAidApp({this.repository, this.config, this.tokenStore, super.key});

  /// Optional repository override.
  final LemonAidRepository? repository;

  /// Optional config override.
  final AppConfig? config;

  /// Optional bearer-token store override.
  final BearerTokenStore? tokenStore;

  @override
  Widget build(BuildContext context) {
    final List<Override> overrides = <Override>[
      if (config != null) appConfigProvider.overrideWithValue(config!),
      if (repository != null)
        lemonAidRepositoryProvider.overrideWithValue(repository!),
      if (tokenStore != null)
        bearerTokenStoreProvider.overrideWithValue(tokenStore!)
      else if (repository != null)
        bearerTokenStoreProvider.overrideWithValue(MemoryBearerTokenStore()),
    ];

    return ProviderScope(
      overrides: overrides,
      child: const _LemonAidRouterApp(),
    );
  }
}

final Provider<GoRouter> _routerProvider = Provider<GoRouter>((Ref ref) {
  final TokenSessionController session = ref.watch(tokenSessionProvider);
  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: session,
    redirect: (BuildContext context, GoRouterState state) {
      final String path = state.uri.path;
      final bool isLogin = path == '/login';
      final bool isSplash = path == '/splash';
      if (!session.bootstrapped) {
        return isSplash ? null : '/splash';
      }
      if (isSplash) {
        return null;
      }
      if (!session.canEnterShell && !isLogin) {
        return '/login';
      }
      if (session.canEnterShell && isLogin) {
        return '/shell/home';
      }
      return null;
    },
    routes: <RouteBase>[
      GoRoute(
        path: '/splash',
        builder: (BuildContext context, GoRouterState state) {
          return const source_splash.SplashScreen();
        },
      ),
      GoRoute(
        path: '/login',
        builder: (BuildContext context, GoRouterState state) {
          return const _BearerTokenLoginScreen();
        },
      ),
      StatefulShellRoute.indexedStack(
        builder:
            (
              BuildContext context,
              GoRouterState state,
              StatefulNavigationShell navigationShell,
            ) {
              return _LemonAidShell(navigationShell: navigationShell);
            },
        branches: <StatefulShellBranch>[
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: '/shell/home',
                builder: (BuildContext context, GoRouterState state) {
                  return Consumer(
                    builder:
                        (BuildContext context, WidgetRef ref, Widget? child) {
                          return source_dashboard.DashboardScreen(
                            controller: ref.watch(appControllerProvider),
                          );
                        },
                  );
                },
                routes: <RouteBase>[
                  GoRoute(
                    path: 'calendar',
                    builder: (BuildContext context, GoRouterState state) {
                      return const _NeutralBranch(
                        icon: Icons.calendar_month_rounded,
                        title: '캘린더',
                        message: '식단·복약 기록 캘린더는 다음 단계에서 API와 연결합니다.',
                      );
                    },
                  ),
                  GoRoute(
                    path: 'notifications',
                    builder: (BuildContext context, GoRouterState state) {
                      return const _NeutralBranch(
                        icon: Icons.notifications_rounded,
                        title: '알림',
                        message: '복약 알림과 분석 리포트 알림 설정을 연결할 예정입니다.',
                      );
                    },
                  ),
                  GoRoute(
                    path: 'analysis-result',
                    builder: (BuildContext context, GoRouterState state) {
                      final String mode =
                          state.uri.queryParameters['mode'] ?? 'supplement';
                      return Consumer(
                        builder:
                            (
                              BuildContext context,
                              WidgetRef ref,
                              Widget? child,
                            ) {
                              return source_analysis.AnalysisResultScreen(
                                mode: mode,
                                controller: ref.watch(appControllerProvider),
                              );
                            },
                      );
                    },
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: '/shell/camera',
                builder: (BuildContext context, GoRouterState state) {
                  return _SupplementCameraBranch(
                    initialMode:
                        state.uri.queryParameters['mode'] ?? 'supplement',
                    initialImageRole:
                        state.uri.queryParameters['role'] ?? 'unknown',
                  );
                },
              ),
            ],
          ),
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: '/shell/chat',
                builder: (BuildContext context, GoRouterState state) {
                  return Consumer(
                    builder:
                        (BuildContext context, WidgetRef ref, Widget? child) {
                          return source_chat.ChatScreen(
                            controller: ref.watch(appControllerProvider),
                          );
                        },
                  );
                },
              ),
            ],
          ),
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: '/shell/score',
                builder: (BuildContext context, GoRouterState state) {
                  return const source_score.ScoreScreen();
                },
              ),
            ],
          ),
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: '/shell/settings',
                builder: (BuildContext context, GoRouterState state) {
                  return const _SettingsBranch();
                },
              ),
            ],
          ),
        ],
      ),
    ],
  );
});

class _LemonAidRouterApp extends ConsumerWidget {
  const _LemonAidRouterApp();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final BrandTheme brandTheme = ref.watch(brandThemeProvider);
    return MaterialApp.router(
      title: 'Lemon Aid',
      debugShowCheckedModeBanner: false,
      theme: buildLemonAidTheme(brandTheme.color),
      routerConfig: ref.watch(_routerProvider),
    );
  }
}

class _LemonAidShell extends ConsumerWidget {
  const _LemonAidShell({required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  static const int _cameraIndex = 1;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppController controller = ref.watch(appControllerProvider);
    final bool isCamera = navigationShell.currentIndex == _cameraIndex;
    final String? completedAnalysisRoute = controller.completedAnalysisRoute;

    return Stack(
      children: <Widget>[
        MainShell(navigationShell: navigationShell),
        if (!isCamera && controller.busy)
          const Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: SafeArea(bottom: false, child: LinearProgressIndicator()),
          ),
        if (!isCamera && controller.apiError != null)
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              bottom: false,
              child: ErrorPanel(
                error: controller.apiError!,
                onDismissed: controller.clearMessages,
              ),
            ),
          ),
        if (!isCamera && controller.notice != null)
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              bottom: false,
              child: _NoticePanel(
                message: controller.notice!,
                actionLabel: completedAnalysisRoute == null ? null : '결과 보기',
                onAction: completedAnalysisRoute == null
                    ? null
                    : () {
                        final String route = completedAnalysisRoute;
                        controller.markAnalysisCompletionRead();
                        controller.clearMessages();
                        context.go(route);
                      },
                onDismissed: () {
                  controller.markAnalysisCompletionRead();
                  controller.clearMessages();
                },
              ),
            ),
          ),
      ],
    );
  }
}

class _SupplementCameraBranch extends ConsumerWidget {
  const _SupplementCameraBranch({
    required this.initialMode,
    required this.initialImageRole,
  });

  final String initialMode;
  final String initialImageRole;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppController controller = ref.watch(appControllerProvider);
    if (!controller.hasMinimumConsents) {
      return ConsentGateScreen(controller: controller);
    }
    return source_camera.CameraScreen(
      key: ValueKey<String>('camera-$initialMode-$initialImageRole'),
      initialMode: initialMode,
      initialImageRole: initialImageRole,
      onClose: () => context.go('/shell/home'),
      onAnalyzeSupplementImage:
          (String imagePath, {required String ocrProvider}) async {
            await controller.startSupplementImageAnalysis(imagePath);
            if (!context.mounted) return;
            context.go('/shell/home/analysis-result?mode=supplement');
          },
      onAnalyzeSupplementImages:
          (
            List<SupplementImageUpload> images, {
            required String ocrProvider,
          }) async {
            await controller.startSupplementImageBatchAnalysis(images);
            if (!context.mounted) return;
            context.go('/shell/home/analysis-result?mode=supplement');
          },
      onAnalyzeMealImage: (String imagePath) async {
        await controller.startMealImageAnalysis(imagePath);
        if (!context.mounted) return;
        context.go('/shell/home/analysis-result?mode=meal');
      },
    );
  }
}

class _SettingsBranch extends ConsumerWidget {
  const _SettingsBranch();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return source_settings.SettingsScreen(
      controller: ref.watch(appControllerProvider),
      session: ref.watch(tokenSessionProvider),
    );
  }
}

class _BearerTokenLoginScreen extends ConsumerStatefulWidget {
  const _BearerTokenLoginScreen();

  @override
  ConsumerState<_BearerTokenLoginScreen> createState() =>
      _BearerTokenLoginScreenState();
}

class _BearerTokenLoginScreenState
    extends ConsumerState<_BearerTokenLoginScreen> {
  final TextEditingController _tokenController = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _tokenController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: LemonColors.canvas,
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: LemonColors.paper,
                  borderRadius: BorderRadius.circular(LemonRadius.lg),
                  border: Border.all(color: LemonColors.border),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      Text(
                        'Lemon Aid',
                        style: Theme.of(context).textTheme.headlineSmall
                            ?.copyWith(
                              color: LemonColors.ink,
                              fontFamily: 'AtoZ',
                              fontWeight: FontWeight.w900,
                            ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        '외부 OIDC/JWT 발급 토큰으로 staging API를 테스트합니다.',
                        style: TextStyle(
                          color: LemonColors.inkSoft,
                          height: 1.35,
                        ),
                      ),
                      const SizedBox(height: 18),
                      TextField(
                        controller: _tokenController,
                        obscureText: true,
                        decoration: InputDecoration(
                          labelText: 'JWT bearer token',
                          errorText: _error,
                          border: const OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 14),
                      FilledButton.icon(
                        onPressed: _saveAndEnter,
                        icon: const Icon(Icons.login_rounded),
                        label: const Text('토큰으로 시작'),
                      ),
                      if (!kReleaseMode) ...<Widget>[
                        const SizedBox(height: 8),
                        TextButton(
                          onPressed: () => context.go('/shell/home'),
                          child: const Text('로컬 dev bypass로 계속'),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _saveAndEnter() async {
    setState(() {
      _error = null;
    });
    try {
      await ref
          .read(tokenSessionProvider)
          .saveBearerToken(_tokenController.text);
      if (mounted) {
        context.go('/shell/home');
      }
    } on ArgumentError {
      setState(() {
        _error = '토큰을 입력해주세요.';
      });
    }
  }
}

class _NeutralBranch extends StatelessWidget {
  const _NeutralBranch({
    required this.icon,
    required this.title,
    required this.message,
  });

  final IconData icon;
  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(icon, color: LemonColors.leaf, size: 56),
              const SizedBox(height: 14),
              Text(
                title,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: LemonColors.ink,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                message,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: LemonColors.inkSoft,
                  height: 1.35,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NoticePanel extends StatelessWidget {
  const _NoticePanel({
    required this.message,
    required this.onDismissed,
    this.actionLabel,
    this.onAction,
  });

  final String message;
  final VoidCallback onDismissed;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Theme.of(context).colorScheme.secondaryContainer,
      child: ListTile(
        leading: const Icon(Icons.check_circle_outline),
        title: Text(message),
        subtitle: actionLabel == null
            ? null
            : Align(
                alignment: Alignment.centerLeft,
                child: TextButton(
                  onPressed: onAction,
                  child: Text(actionLabel!),
                ),
              ),
        trailing: IconButton(
          tooltip: 'Dismiss',
          onPressed: onDismissed,
          icon: const Icon(Icons.close),
        ),
      ),
    );
  }
}
