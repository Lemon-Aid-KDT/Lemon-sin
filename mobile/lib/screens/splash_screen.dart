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
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:lottie/lottie.dart';

import '../providers/auth_provider.dart';
import '../utils/router.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with TickerProviderStateMixin {
  late final AnimationController _floatController;
  late final AnimationController _lottieController;

  // 태그라인 — 한 글자씩 타이핑되며 노출되는 인덱스
  int _typedCount = 0;
  Timer? _typeTimer;
  static const Duration _typeStep = Duration(milliseconds: 120);
  static const Duration _typeStartDelay = Duration(milliseconds: 150);

  // 마지막 글자 안착 + 노란 점 애니까지 완료되는 여유 시간
  // (등장 320ms + 노란 점 720ms + 안전 마진 → 넉넉히)
  static const Duration _lastCharSettle = Duration(milliseconds: 1200);

  // 다 박힌 후 사용자가 읽고 음미할 머무름 시간
  static const Duration _readingHold = Duration(milliseconds: 1200);

  // 태그라인 원문 (한 자씩 노출)
  static const String _tagline = '상큼하게 찍고, 톡 쏘게 채우는 스마트 헬스케어';

  // 타이핑 전체 완료 시각 = 시작 지연 + (글자수 × 글자당 시간) + 마지막 글자 안착 + 머무름
  // 예) 150 + 23 × 120 + 800 + 700 = 4410ms
  Duration get _minSplashDuration {
    final typing = _typeStep * _tagline.length;
    return _typeStartDelay + typing + _lastCharSettle + _readingHold;
  }

  // 배포 빌드 (release) 의 최대 대기 시간 — 인증 / 네트워크 응답 한계
  // 로티는 repeat: true 로 그동안 무한 루프
  static const Duration _releaseMaxWait = Duration(seconds: 15);

  @override
  void initState() {
    super.initState();

    _floatController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2400),
    )..repeat(reverse: true);

    // Lottie 외부 컨트롤러 — 2x 속도 (원본 6초 → 3초 사이클).
    // 초기 duration 을 3초로 미리 세팅 (composition 로딩 전 첫 프레임 에러 방지).
    // onLoaded 에서 composition 실제 길이의 1/2 로 정확히 다시 설정.
    _lottieController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    );

    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
      ),
    );

    // 태그라인 타이핑 — 로티 시작 약 _typeStartDelay 후 (먼저 캐릭터 인식 후 글자 박힘)
    Future.delayed(_typeStartDelay, () {
      if (!mounted) return;
      _typeTimer = Timer.periodic(_typeStep, (t) {
        if (!mounted) {
          t.cancel();
          return;
        }
        if (_typedCount >= _tagline.length) {
          t.cancel();
          return;
        }
        setState(() => _typedCount++);
      });
    });

    // 인증 체크 + 라우팅 결정 (Splash가 로딩 책임)
    _initRoute();
  }

  Future<void> _initRoute() async {
    final stopwatch = Stopwatch()..start();

    String? route;
    String? errorMessage;

    // 실제 인증 / 네트워크 호출 future
    // AuthController.bootstrap() 이 토큰 읽고 상태 결정 — unknown → authenticated/unauthenticated.
    Future<String> authFuture() async {
      try {
        // AuthState 가 unknown 이 아닐 때까지 polling (보통 50ms 이내 끝남)
        // bootstrap 이 끝나면 isReady = true.
        for (var i = 0; i < 100; i++) {
          final state = ref.read(authControllerProvider);
          if (state.isReady) {
            return state.isAuthenticated ? '/shell/home' : AppRoute.login;
          }
          await Future<void>.delayed(const Duration(milliseconds: 50));
        }
        // 5초 동안 부트스트랩 안 끝나면 로그인 화면으로
        return AppRoute.login;
      } catch (_) {
        errorMessage = '잠시 후 다시 시도해주세요';
        return AppRoute.login;
      }
    }

    if (kReleaseMode) {
      // ─── 배포 빌드 ─────────────────────────────
      // 로티는 repeat: true 로 무한 루프 도는 중.
      // 인증 / 네트워크 응답이 도착하면 즉시 라우팅.
      // 최대 15 초까지만 기다리고, 그 후에는 timeout 처리.
      try {
        route = await authFuture().timeout(_releaseMaxWait);
      } on TimeoutException {
        route = AppRoute.login;
        errorMessage = '잠시 후 다시 시도해주세요';
      }
    } else {
      // ─── 개발 빌드 (debug / profile) ──────────
      // 로티 한 사이클 (6 초) 끝날 때까지 강제 대기 — 로딩 시뮬레이션.
      // 그 동안 인증 호출은 백그라운드에서 진행.
      final results = await Future.wait<dynamic>([
        authFuture(),
        Future<void>.delayed(_minSplashDuration),
      ]);
      route = results[0] as String;
    }

    if (!mounted) return;
    context.go(route);

    final err = errorMessage;
    if (err != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
      });
    }
    // stopwatch 는 디버그 로그 용도로만 — 라우팅 결정엔 사용 X
    stopwatch.stop();
  }

  @override
  void dispose() {
    _typeTimer?.cancel();
    _floatController.dispose();
    _lottieController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,    // 흰 배경 고정
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // ─── Lottie 캐릭터 로딩 ───
              // lemonaid_gold.json — 원본 6 초 / 30fps, 1.5x 속도로 4 초 사이클 (무한 반복).
              SizedBox(
                // 2026-05-18: 280 → 240 미세하게 줄임
                width: 240,
                height: 240,
                child: Lottie.asset(
                  'assets/animations/lemonaid_gold.json',
                  fit: BoxFit.contain,
                  controller: _lottieController,
                  frameRate: FrameRate.max,
                  onLoaded: (composition) {
                    if (!mounted) return;
                    // 1.5x 속도 — 원본 duration 의 2/3. 사이클 4 초 (잎 성장까지 다 포함).
                    _lottieController
                      ..duration = composition.duration * (2 / 3)
                      ..repeat();
                  },
                ),
              ),

              const SizedBox(height: 0),

              // ─── 타이핑 태그라인 (워드마크 제거됨) ───
              // 로티 캐릭터와 가깝게 붙임 (마이너스 마진 효과는 Transform 으로)
              Transform.translate(
                offset: const Offset(0, -8),
                child: _TypingTagline(typed: _typedCount, total: _tagline.length),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── 타이핑 태그라인 ──────────────────────────────────
//
// "상큼하게 찍고, 톡 쏘게 채우는 스마트 헬스케어"
// 한 글자씩 80ms 간격으로 노출, "상" / "톡" 위에는 노란 점 강조 (글자랑 같이
// 살짝 부풀었다 원래대로).
class _TypingTagline extends StatelessWidget {
  final int typed;       // 노출된 글자 수
  final int total;       // 전체 글자 수
  const _TypingTagline({required this.typed, required this.total});

  // 노란 점이 붙는 글자 인덱스 (텍스트 기준)
  // "상큼하게 찍고, 톡 쏘게 채우는 스마트 헬스케어"
  //  0:상  1:큼  2:하  3:게  4:_  5:찍  6:고  7:,  8:_  9:톡 ...
  static const Set<int> _dotIndices = {0, 9}; // "상", "톡"

  @override
  Widget build(BuildContext context) {
    const text = '상큼하게 찍고, 톡 쏘게 채우는 스마트 헬스케어';

    return RichText(
      textAlign: TextAlign.center,
      text: TextSpan(
        // AppText.bodyLg 기준 (17px) — 디자인 토큰 규칙
        style: const TextStyle(
          fontFamily: 'Pretendard',
          fontSize: 17,
          fontWeight: FontWeight.w500,
          color: Color(0xFF4E5968),
          height: 1.45,
          letterSpacing: -0.4,
        ),
        children: [
          for (int i = 0; i < typed && i < text.length; i++)
            WidgetSpan(
              alignment: PlaceholderAlignment.baseline,
              baseline: TextBaseline.alphabetic,
              child: _AnimatedChar(
                char: text[i],
                index: i,
                accent: _dotIndices.contains(i),
              ),
            ),
        ],
      ),
    );
  }
}

// 글자 한 개 — 회전 + 위에서 톡 떨어져 박힌 뒤 작은 바운스 (3단계).
// 짝수/홀수 index 별로 미세 다른 등장 변형 → 단조로움 해소.
// accent = true 면 위에 노란 점이 스프링으로 떨어져 박힘.
class _AnimatedChar extends StatefulWidget {
  final String char;
  final int index;
  final bool accent;
  const _AnimatedChar({required this.char, required this.index, required this.accent});

  @override
  State<_AnimatedChar> createState() => _AnimatedCharState();
}

class _AnimatedCharState extends State<_AnimatedChar>
    with TickerProviderStateMixin {
  late final AnimationController _c;   // 글자 등장 + 안착 바운스
  late final AnimationController _dc;  // 노란 점 (악센트 글자만)

  late final Animation<double> _opacity;     // 0 → 1
  late final Animation<double> _scale;       // 0.6 → 1.08 → 0.97 → 1.0 (톡톡)
  late final Animation<double> _offsetY;     // 위에서 -12 → 0 → -2 → 0 (작은 바운스)
  late final Animation<double> _rotation;    // ±0.14 rad → 0 (회전 안착)

  // 노란 점 (악센트만)
  late final Animation<double> _dotSize;     // 0 → 10 → 4 → 6 (스프링)
  late final Animation<double> _dotOffsetY;  // -14 → 0 (위에서 톡)
  late final Animation<double> _ringRadius;  // 0 → 22 (퍼지는 글로우 링)
  late final Animation<double> _ringOpacity; // 0.6 → 0 (페이드아웃)
  late final Animation<double> _charColorMix;// 0 → 1 → 0 (글자 색 노란 깜빡)

  @override
  void initState() {
    super.initState();

    // 글자 등장 컨트롤러 — 짝수 / 홀수 별 미세 변형
    final isEven = widget.index.isEven;
    _c = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 560),
    )..forward();

    _opacity = CurvedAnimation(
      parent: _c,
      curve: const Interval(0.0, 0.35, curve: Curves.easeOut),
    );

    // 톡톡 스케일 — 0.6 → 1.08 → 0.97 → 1.0
    _scale = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.6, end: 1.08), weight: 45),
      TweenSequenceItem(tween: Tween(begin: 1.08, end: 0.97), weight: 30),
      TweenSequenceItem(tween: Tween(begin: 0.97, end: 1.0), weight: 25),
    ]).animate(CurvedAnimation(parent: _c, curve: Curves.easeOutCubic));

    // y offset — 위에서 떨어져 살짝 더 들어갔다 (-2) 안착
    _offsetY = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: -12.0, end: 0.0), weight: 55),
      TweenSequenceItem(tween: Tween(begin: 0.0, end: -2.0), weight: 20),
      TweenSequenceItem(tween: Tween(begin: -2.0, end: 0.0), weight: 25),
    ]).animate(CurvedAnimation(parent: _c, curve: Curves.easeOutCubic));

    // 회전 — 짝수: 왼쪽으로 / 홀수: 오른쪽으로 살짝 비틀린 채 떨어져 안착
    final startAngle = isEven ? -0.14 : 0.14;
    _rotation = Tween(begin: startAngle, end: 0.0).animate(
      CurvedAnimation(parent: _c, curve: Curves.easeOutBack),
    );

    if (widget.accent) {
      _dc = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 720),
      );
      _dotSize = TweenSequence<double>([
        TweenSequenceItem(tween: Tween(begin: 0.0, end: 10.0), weight: 40),
        TweenSequenceItem(tween: Tween(begin: 10.0, end: 4.0), weight: 25),
        TweenSequenceItem(tween: Tween(begin: 4.0, end: 7.0), weight: 20),
        TweenSequenceItem(tween: Tween(begin: 7.0, end: 6.0), weight: 15),
      ]).animate(CurvedAnimation(parent: _dc, curve: Curves.easeOutCubic));

      _dotOffsetY = TweenSequence<double>([
        TweenSequenceItem(tween: Tween(begin: -14.0, end: 0.0), weight: 50),
        TweenSequenceItem(tween: Tween(begin: 0.0, end: 0.0), weight: 50),
      ]).animate(CurvedAnimation(parent: _dc, curve: Curves.easeOutCubic));

      // 점이 박힌 직후 퍼지는 노란 글로우 링 (radius 0 → 22, opacity 0.6 → 0)
      _ringRadius = TweenSequence<double>([
        TweenSequenceItem(tween: Tween(begin: 0.0, end: 0.0), weight: 35),
        TweenSequenceItem(tween: Tween(begin: 0.0, end: 22.0), weight: 65),
      ]).animate(CurvedAnimation(parent: _dc, curve: Curves.easeOut));

      _ringOpacity = TweenSequence<double>([
        TweenSequenceItem(tween: Tween(begin: 0.0, end: 0.0), weight: 35),
        TweenSequenceItem(tween: Tween(begin: 0.65, end: 0.0), weight: 65),
      ]).animate(CurvedAnimation(parent: _dc, curve: Curves.easeOut));

      // 글자 색이 점 박힐 때 노란(브랜드)으로 변하고 그대로 유지 (0 → 1)
      _charColorMix = TweenSequence<double>([
        TweenSequenceItem(tween: Tween(begin: 0.0, end: 0.0), weight: 25),
        TweenSequenceItem(tween: Tween(begin: 0.0, end: 1.0), weight: 35),
        TweenSequenceItem(tween: Tween(begin: 1.0, end: 1.0), weight: 40),
      ]).animate(CurvedAnimation(parent: _dc, curve: Curves.easeOutCubic));

      Future.delayed(const Duration(milliseconds: 140), () {
        if (mounted) _dc.forward();
      });
    } else {
      _dc = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 1),
      );
      _dotSize = const AlwaysStoppedAnimation(0);
      _dotOffsetY = const AlwaysStoppedAnimation(0);
      _ringRadius = const AlwaysStoppedAnimation(0);
      _ringOpacity = const AlwaysStoppedAnimation(0);
      _charColorMix = const AlwaysStoppedAnimation(0);
    }
  }

  @override
  void dispose() {
    _c.dispose();
    _dc.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([_c, _dc]),
      builder: (_, __) {
        // 일반 글자 색 ↔ 브랜드 노랑 (악센트 글자는 변하고 유지)
        final baseColor = const Color(0xFF4E5968);
        const accentColor = Color(0xFFE0A700);
        final mix = _charColorMix.value.clamp(0.0, 1.0);
        final textColor = widget.accent
            ? Color.lerp(baseColor, accentColor, mix)
            : baseColor;
        // 악센트 글자는 색 변하면서 두께도 같이 굵어짐 (w500 → w800)
        final FontWeight charWeight = widget.accent
            ? (mix > 0.6
                ? FontWeight.w800
                : mix > 0.25
                    ? FontWeight.w700
                    : FontWeight.w500)
            : FontWeight.w500;

        return Opacity(
          opacity: _opacity.value.clamp(0.0, 1.0),
          child: Transform.translate(
            offset: Offset(0, _offsetY.value),
            child: Transform.rotate(
              angle: _rotation.value,
              child: Transform.scale(
                scale: _scale.value,
                child: Stack(
                  clipBehavior: Clip.none,
                  alignment: Alignment.topCenter,
                  children: [
                    // 글자
                    Padding(
                      padding: EdgeInsets.only(top: widget.accent ? 9 : 0),
                      child: Text(
                        widget.char,
                        style: TextStyle(
                          fontFamily: 'Pretendard',
                          fontSize: 17,
                          fontWeight: charWeight,
                          color: textColor,
                          height: 1.45,
                          letterSpacing: -0.4,
                        ),
                      ),
                    ),
                    // 퍼지는 노란 글로우 링 (점 박힐 때)
                    if (widget.accent && _ringRadius.value > 0)
                      Positioned(
                        top: -(_ringRadius.value / 2) + 3,
                        child: Container(
                          width: _ringRadius.value,
                          height: _ringRadius.value,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: const Color(0xFFFFC700)
                                  .withOpacity(_ringOpacity.value),
                              width: 2,
                            ),
                          ),
                        ),
                      ),
                    // 노란 점
                    if (widget.accent)
                      Positioned(
                        top: _dotOffsetY.value,
                        child: Container(
                          width: _dotSize.value,
                          height: _dotSize.value,
                          decoration: BoxDecoration(
                            color: const Color(0xFFFFC700),
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFFFFC700).withOpacity(0.6),
                                blurRadius: 8,
                                offset: const Offset(0, 1),
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
