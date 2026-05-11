// screens/splash_screen.dart — S-01 Splash / Loading 통합
//
// 다이어리 §14.7 S-01 명세 그대로 + 인증 라우팅 로직:
//   - 네이티브 splash 끝나면 이 화면이 자연스럽게 이어짐 (같은 배경 + 같은 로고)
//   - 1.0~2.0초 동안 인증 상태 체크 + 라우팅 결정
//   - 인증 OK -> /home, 없음 -> /login, 에러 -> /login + Snackbar
//   - 떠다니는 로고 모션 (지금은 Flutter 내장 AnimationController)
//   - 미래에 Lottie .json 으로 교체 가능 (assets/animations/lemon_bounce.json)
//
// 참조: 다이어리 §14.7 S-01 (12 영역 + 친화도 7대 원칙)

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../utils/router.dart';
import '../utils/tokens.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _floatController;

  // 최대 표시 시간 — 백엔드 API 응답 대기 한계
  // 실제 배포 시: 무한 loop (Lottie repeat true) — 인증/네트워크 응답까지 무한 대기 가능
  // 개발 단계: 3.5초 timeout 후 강제 /login
  static const Duration _maxDuration = Duration(milliseconds: 3500);

  // 최소 표시 시간 — 너무 짧으면 50대가 로고 인식 못 함
  // 사용자 결정 (2026-05-11): 2초 (다이어리 §14.7 S-01 결정)
  static const Duration _minDuration = Duration(milliseconds: 2000);

  @override
  void initState() {
    super.initState();

    _floatController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2400),
    )..repeat(reverse: true);

    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
      ),
    );

    // 인증 체크 + 라우팅 결정 (Splash가 로딩 책임)
    _initRoute();
  }

  Future<void> _initRoute() async {
    final stopwatch = Stopwatch()..start();

    String? route;
    String? errorMessage;

    try {
      // TODO: 실제 인증 체크 (실제 배포 시점)
      //   - SharedPreferences에서 auth_token 읽기
      //   - 토큰 있으면 /auth/me 호출해서 유효성 검증
      //   - 응답에 따라 /home 또는 /login
      //   - Lottie 애니메이션은 repeat: true (무한 loop) — 응답 늦어도 자연스러움
      //
      // 지금은 mock: 1.5초 후 인증 없음 -> /login (최소 2초 보장과 함께)
      await Future<void>.delayed(const Duration(milliseconds: 1500));
      route = AppRoute.login;

      // 예시: 인증 있으면
      // final token = await prefs.getString('auth_token');
      // if (token != null && await authService.verify(token)) {
      //   route = AppRoute.home;
      // } else {
      //   route = AppRoute.login;
      // }
    } catch (e) {
      route = AppRoute.login;
      errorMessage = '잠시 후 다시 시도해주세요';
    }

    // 최소 노출 시간 보장 (너무 빨리 사라지지 않게)
    final elapsed = stopwatch.elapsed;
    if (elapsed < _minDuration) {
      await Future<void>.delayed(_minDuration - elapsed);
    }

    if (!mounted) return;

    // 최대 시간 초과 — Splash 자체 timeout (위에 1초 정도라 거의 도달 X)
    if (elapsed > _maxDuration) {
      errorMessage ??= '잠시 후 다시 시도해주세요';
    }

    context.go(route);

    if (errorMessage != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(errorMessage!)),
        );
      });
    }
  }

  @override
  void dispose() {
    _floatController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: LemonColors.bg,
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // ─── 로고 (네이티브 splash와 같은 위치·크기) ───
              // 미래에 Lottie로 교체:
              //   Lottie.asset('assets/animations/lemon_bounce.json',
              //     width: 120, height: 120, repeat: true)
              AnimatedBuilder(
                animation: _floatController,
                builder: (context, child) {
                  final t = Curves.easeInOut.transform(_floatController.value);
                  final dy = -4.0 + t * 8.0;
                  return Transform.translate(
                    offset: Offset(0, dy),
                    child: child,
                  );
                },
                child: const _LemonLogo(size: 120),
              ),

              const SizedBox(height: 24),

              const _Wordmark(),

              const SizedBox(height: 8),

              Text(
                '내 손안의 영양 상담사',
                style: LemonText.body.copyWith(
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                  color: LemonColors.inkSoft,
                ),
              ),

              const SizedBox(height: 48),

              // 인디케이터 — 로딩 중임을 명시
              SizedBox(
                width: 56,
                height: 3,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: const LinearProgressIndicator(
                    backgroundColor: LemonColors.line,
                    valueColor: AlwaysStoppedAnimation(LemonColors.brand),
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

// ─── 레몬 도형 로고 (네이티브 splash와 동일 디자인) ───
class _LemonLogo extends StatelessWidget {
  final double size;
  const _LemonLogo({required this.size});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Positioned(
            bottom: 6,
            child: Container(
              width: size * 0.7,
              height: 10,
              decoration: BoxDecoration(
                color: LemonColors.ink.withOpacity(0.08),
                borderRadius: BorderRadius.circular(999),
              ),
            ),
          ),
          Container(
            width: size * 0.85,
            height: size * 0.85,
            decoration: BoxDecoration(
              gradient: const RadialGradient(
                center: Alignment(-0.3, -0.3),
                radius: 0.95,
                colors: [
                  Color(0xFFFFE066),
                  LemonColors.citrus,
                  Color(0xFFE8B800),
                ],
                stops: [0.0, 0.6, 1.0],
              ),
              shape: BoxShape.circle,
              boxShadow: LemonShadow.md,
            ),
          ),
          Positioned(
            top: size * 0.05,
            right: size * 0.20,
            child: Transform.rotate(
              angle: -0.5,
              child: Container(
                width: size * 0.18,
                height: size * 0.12,
                decoration: BoxDecoration(
                  color: LemonColors.green,
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Wordmark extends StatelessWidget {
  const _Wordmark();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        const Text(
          'Lemon',
          style: TextStyle(
            fontFamily: LemonFont.display,
            fontSize: 36,
            fontWeight: FontWeight.w800,
            color: LemonColors.ink,
            letterSpacing: -1.2,
            height: 1.0,
          ),
        ),
        Padding(
          padding: const EdgeInsets.only(left: 2, right: 2, bottom: 6),
          child: Container(
            width: 14,
            height: 14,
            decoration: BoxDecoration(
              color: LemonColors.citrus,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: LemonColors.citrus.withOpacity(0.4),
                  blurRadius: 4,
                  offset: const Offset(0, 1),
                ),
              ],
            ),
          ),
        ),
        const Text(
          'Aid',
          style: TextStyle(
            fontFamily: LemonFont.display,
            fontSize: 36,
            fontWeight: FontWeight.w800,
            color: LemonColors.ink,
            letterSpacing: -1.2,
            height: 1.0,
          ),
        ),
      ],
    );
  }
}
