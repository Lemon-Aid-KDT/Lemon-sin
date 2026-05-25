import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'app_controller.dart';
import 'app_providers.dart';
import 'core/config/app_config.dart';
import 'features/auth/token_session.dart';
import 'features/consent/consent_gate_screen.dart';
import 'features/dashboard/dashboard_screen.dart';
import 'features/supplements/supplement_flow_screen.dart';
import 'features/supplements/supplement_repository.dart';
import 'shared/theme/lemon_design_tokens.dart';
import 'shared/widgets/error_panel.dart';

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
      if (!session.canEnterShell && !isLogin) {
        return '/login';
      }
      if (session.canEnterShell && (isLogin || isSplash)) {
        return '/shell/home';
      }
      return null;
    },
    routes: <RouteBase>[
      GoRoute(
        path: '/splash',
        builder: (BuildContext context, GoRouterState state) {
          return const _SplashScreen();
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
                  return const _DashboardBranch();
                },
              ),
            ],
          ),
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: '/shell/chat',
                builder: (BuildContext context, GoRouterState state) {
                  return const _NeutralBranch(
                    icon: Icons.chat_bubble_outline_rounded,
                    title: '챗',
                    message: '실시간 상담형 화면은 별도 API 계약 후 연결합니다.',
                  );
                },
              ),
            ],
          ),
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: '/shell/camera',
                builder: (BuildContext context, GoRouterState state) {
                  return const _SupplementCameraBranch();
                },
              ),
            ],
          ),
          StatefulShellBranch(
            routes: <RouteBase>[
              GoRoute(
                path: '/shell/score',
                builder: (BuildContext context, GoRouterState state) {
                  return const _NeutralBranch(
                    icon: Icons.workspace_premium_outlined,
                    title: '점수',
                    message: '등록된 보충제와 분석 결과 기반 점검 화면으로 확장합니다.',
                  );
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
    return MaterialApp.router(
      title: 'Lemon Aid',
      debugShowCheckedModeBanner: false,
      theme: buildLemonAidTheme(),
      routerConfig: ref.watch(_routerProvider),
    );
  }
}

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const ColoredBox(
      color: LemonColors.canvas,
      child: Center(child: CircularProgressIndicator(color: LemonColors.leaf)),
    );
  }
}

class _LemonAidShell extends ConsumerWidget {
  const _LemonAidShell({required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  static const int _cameraIndex = 2;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppController controller = ref.watch(appControllerProvider);
    final bool isCamera = navigationShell.currentIndex == _cameraIndex;

    return Scaffold(
      backgroundColor: isCamera ? Colors.black : LemonColors.canvas,
      extendBody: isCamera,
      body: Column(
        children: <Widget>[
          if (!isCamera && controller.busy) const LinearProgressIndicator(),
          if (!isCamera && controller.apiError != null)
            ErrorPanel(
              error: controller.apiError!,
              onDismissed: controller.clearMessages,
            ),
          if (!isCamera && controller.notice != null)
            _NoticePanel(
              message: controller.notice!,
              onDismissed: controller.clearMessages,
            ),
          Expanded(child: navigationShell),
        ],
      ),
      bottomNavigationBar: isCamera
          ? null
          : _BottomShellBar(
              currentIndex: navigationShell.currentIndex,
              onTap: _goBranch,
            ),
    );
  }

  void _goBranch(int index) {
    navigationShell.goBranch(
      index,
      initialLocation: index == navigationShell.currentIndex,
    );
  }
}

class _BottomShellBar extends StatelessWidget {
  const _BottomShellBar({required this.currentIndex, required this.onTap});

  final int currentIndex;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: LemonColors.paper,
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Color(0x1A75829B),
            blurRadius: 18,
            offset: Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 74,
          child: Stack(
            clipBehavior: Clip.none,
            alignment: Alignment.topCenter,
            children: <Widget>[
              Row(
                children: <Widget>[
                  _ShellTab(
                    index: 0,
                    currentIndex: currentIndex,
                    icon: Icons.favorite_rounded,
                    label: '홈',
                    onTap: onTap,
                  ),
                  _ShellTab(
                    index: 1,
                    currentIndex: currentIndex,
                    icon: Icons.chat_bubble_rounded,
                    label: '챗',
                    onTap: onTap,
                  ),
                  const Expanded(child: SizedBox.shrink()),
                  _ShellTab(
                    index: 3,
                    currentIndex: currentIndex,
                    icon: Icons.workspace_premium_rounded,
                    label: '점수',
                    onTap: onTap,
                  ),
                  _ShellTab(
                    index: 4,
                    currentIndex: currentIndex,
                    icon: Icons.settings_rounded,
                    label: '설정',
                    onTap: onTap,
                  ),
                ],
              ),
              Positioned(
                top: -20,
                child: Semantics(
                  button: true,
                  label: '영양제 촬영',
                  child: SizedBox(
                    width: 66,
                    height: 66,
                    child: FilledButton(
                      onPressed: () => onTap(2),
                      style: FilledButton.styleFrom(
                        shape: const CircleBorder(),
                        backgroundColor: LemonColors.lemon,
                        foregroundColor: LemonColors.ink,
                        padding: EdgeInsets.zero,
                        elevation: 8,
                      ),
                      child: const Icon(Icons.add_a_photo_rounded, size: 30),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ShellTab extends StatelessWidget {
  const _ShellTab({
    required this.index,
    required this.currentIndex,
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final int index;
  final int currentIndex;
  final IconData icon;
  final String label;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    final bool active = currentIndex == index;
    final Color color = active ? LemonColors.lemonDeep : LemonColors.inkSoft;
    return Expanded(
      child: InkWell(
        onTap: () => onTap(index),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(icon, color: color, size: active ? 27 : 24),
              const SizedBox(height: 3),
              Text(
                label,
                style: TextStyle(
                  color: active ? LemonColors.ink : LemonColors.inkSoft,
                  fontSize: 11,
                  fontWeight: active ? FontWeight.w800 : FontWeight.w600,
                  letterSpacing: 0,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DashboardBranch extends ConsumerWidget {
  const _DashboardBranch();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return SafeArea(
      child: DashboardScreen(controller: ref.watch(appControllerProvider)),
    );
  }
}

class _SupplementCameraBranch extends ConsumerWidget {
  const _SupplementCameraBranch();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return SupplementFlowScreen(
      controller: ref.watch(appControllerProvider),
      onClose: () => context.go('/shell/home'),
    );
  }
}

class _SettingsBranch extends ConsumerWidget {
  const _SettingsBranch();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
        children: <Widget>[
          const _TokenAccessPanel(),
          const SizedBox(height: 16),
          ConsentGateScreen(controller: ref.watch(appControllerProvider)),
        ],
      ),
    );
  }
}

class _TokenAccessPanel extends ConsumerStatefulWidget {
  const _TokenAccessPanel();

  @override
  ConsumerState<_TokenAccessPanel> createState() => _TokenAccessPanelState();
}

class _TokenAccessPanelState extends ConsumerState<_TokenAccessPanel> {
  final TextEditingController _tokenController = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _tokenController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final TokenSessionController session = ref.watch(tokenSessionProvider);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LemonColors.paper,
        borderRadius: BorderRadius.circular(LemonRadius.lg),
        border: Border.all(color: LemonColors.border),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'API access',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: LemonColors.ink,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              session.bearerToken == null
                  ? (session.devBypassActive
                        ? 'Debug dev bypass is active for AUTH_MODE=disabled.'
                        : 'Enter an externally issued JWT bearer token.')
                  : 'External bearer token is stored locally.',
              style: const TextStyle(color: LemonColors.inkSoft, height: 1.35),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _tokenController,
              obscureText: true,
              decoration: InputDecoration(
                labelText: 'JWT bearer token',
                errorText: _error,
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                FilledButton.icon(
                  onPressed: _saveToken,
                  icon: const Icon(Icons.vpn_key_rounded),
                  label: const Text('저장'),
                ),
                OutlinedButton.icon(
                  onPressed: session.bearerToken == null
                      ? null
                      : () => ref.read(tokenSessionProvider).clearBearerToken(),
                  icon: const Icon(Icons.logout_rounded),
                  label: const Text('토큰 삭제'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _saveToken() async {
    setState(() {
      _error = null;
    });
    try {
      await ref
          .read(tokenSessionProvider)
          .saveBearerToken(_tokenController.text);
      _tokenController.clear();
      if (mounted) {
        FocusScope.of(context).unfocus();
      }
    } on ArgumentError {
      setState(() {
        _error = '토큰을 입력해주세요.';
      });
    }
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
  const _NoticePanel({required this.message, required this.onDismissed});

  final String message;
  final VoidCallback onDismissed;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Theme.of(context).colorScheme.secondaryContainer,
      child: ListTile(
        leading: const Icon(Icons.check_circle_outline),
        title: Text(message),
        trailing: IconButton(
          tooltip: 'Dismiss',
          onPressed: onDismissed,
          icon: const Icon(Icons.close),
        ),
      ),
    );
  }
}
