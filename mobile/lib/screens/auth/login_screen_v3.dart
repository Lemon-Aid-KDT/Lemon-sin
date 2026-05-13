// screens/auth/login_screen_v3.dart — Lemon Aid Login (Flat 2.0 + 카드 기반)
//
// 디자인 시스템 v2.0 (UX_DIARY §14.10) 적용.
// Toss / 여기어때 톤. 뉴모 효과 없음. 깔끔·실용·시중 앱 패턴.

import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../utils/router.dart';
import '../../utils/design_tokens_v2.dart';

class LoginScreenV3 extends StatelessWidget {
  const LoginScreenV3({super.key});

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        systemNavigationBarColor: AppColor.bg,
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
      child: Scaffold(
        backgroundColor: AppColor.bg,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpace.xl),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: AppSpace.xxxl + 13),

                // ─── 브랜드 워드마크 ───
                const _Brand(),
                const SizedBox(height: 12),
                const _Tagline(),

                const Spacer(),

                // ─── 캐릭터 ───
                Transform.translate(
                  offset: const Offset(0, 36),
                  child: Align(
                    alignment: Alignment.centerRight,
                    child: Image.asset(
                      'assets/illustrations/lemon_character.png',
                      width: 210,
                      height: 210,
                      fit: BoxFit.contain,
                    ),
                  ),
                ),

                const _RecentLoginTooltip(),
                const SizedBox(height: AppSpace.sm),

                // ─── OAuth 3종 (카카오 / 구글 / Apple) ───
                // 카카오·Apple → 뉴모 액센트 (감성 강조, 진입 첫 화면 인상)
                // 구글 → Flat (대비, 균형)
                AppPrimaryButton(
                  label: '카카오로 계속하기',
                  color: AppColor.kakao,
                  textColor: const Color(0xFF191600),
                  accent: true,
                  onPressed: () {},
                  leading: SvgPicture.asset(
                    'assets/icons/kakao_message.svg',
                    width: 20, height: 20,
                    colorFilter: const ColorFilter.mode(
                      Color(0xFF191600), BlendMode.srcIn,
                    ),
                  ),
                ),
                const SizedBox(height: AppSpace.md),
                AppSecondaryButton(
                  label: '구글로 계속하기',
                  onPressed: () {},
                  leading: SvgPicture.asset('assets/icons/google_g.svg', width: 20, height: 20),
                ),
                const SizedBox(height: AppSpace.md),
                AppPrimaryButton(
                  label: 'Apple로 계속하기',
                  color: AppColor.appleBlack,
                  accent: true,
                  onPressed: () {},
                  leading: SvgPicture.asset(
                    'assets/icons/apple_logo.svg',
                    width: 20, height: 20,
                    colorFilter: const ColorFilter.mode(Colors.white, BlendMode.srcIn),
                  ),
                ),

                const SizedBox(height: AppSpace.lg),

                // ─── 디바이더 + "이메일로 시작하기" ───
                Row(
                  children: [
                    const Expanded(child: Divider(height: 1, color: AppColor.border)),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: AppSpace.md),
                      child: Text(
                        '이메일로 시작하기',
                        style: AppText.caption.copyWith(color: AppColor.inkTertiary),
                      ),
                    ),
                    const Expanded(child: Divider(height: 1, color: AppColor.border)),
                  ],
                ),
                const SizedBox(height: AppSpace.md),

                // ─── 회원가입 / 로그인 1:2 ───
                Row(
                  children: [
                    Expanded(
                      flex: 1,
                      child: AppSecondaryButton(
                        label: '회원가입',
                        onPressed: () => context.push(AppRoute.signup),
                      ),
                    ),
                    const SizedBox(width: AppSpace.sm),
                    Expanded(
                      flex: 2,
                      child: AppPrimaryButton(
                        label: '로그인',
                        accent: true,
                        onPressed: () {},
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: AppSpace.xl),

                Center(
                  child: Text(
                    '© Lemon Aid · 이용약관 · 개인정보',
                    style: AppText.micro,
                  ),
                ),
                // ─── Dev Bypass (debug 빌드 전용) ───
                // 백엔드 합치기 전까지 메인 셸 진입용. release 빌드에선 완전히 사라짐.
                // 참조: mobile/CLAUDE.md §4.2 + integration_notes.md "AuthProvider 신설 시 제거"
                if (kDebugMode) ...<Widget>[
                  const SizedBox(height: AppSpace.xs),
                  Center(
                    child: TextButton(
                      onPressed: () => context.go(AppRoute.shellHome),
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpace.sm,
                          vertical: AppSpace.xs,
                        ),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      child: const Text(
                        '개발자 진입 (mock)',
                        style: TextStyle(
                          fontFamily: 'Pretendard',
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: AppColor.inkTertiary,
                          decoration: TextDecoration.underline,
                          decorationColor: AppColor.inkTertiary,
                        ),
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: AppSpace.md),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ─── 태그라인 (한 줄) ───
// "상"·"톡" 글자 위에 노란 점 강조.
// WidgetSpan(Stack) 으로 글자와 점을 같은 inline 박스에 묶어 줄바꿈·폰트 변경에도 위치 정확.
class _Tagline extends StatelessWidget {
  const _Tagline();

  // body 토큰 (15pt) — §14.10.5 타이포 사다리
  static const double _fontSize = 15;
  static const double _dotSize = 4;

  @override
  Widget build(BuildContext context) {
    const baseStyle = TextStyle(
      fontFamily: 'Pretendard',
      fontSize: _fontSize,
      fontWeight: FontWeight.w500,
      color: AppColor.inkSecondary,
      letterSpacing: -0.3,
      height: 1.55,
    );
    return Padding(
      padding: const EdgeInsets.only(top: 8),     // 점 공간 (8 그리드)
      child: RichText(
        text: TextSpan(
          style: baseStyle,
          children: [
            WidgetSpan(
              alignment: PlaceholderAlignment.baseline,
              baseline: TextBaseline.alphabetic,
              child: _AccentedChar(char: '상', style: baseStyle, dotSize: _dotSize),
            ),
            const TextSpan(text: '큼하게 찍고, '),
            WidgetSpan(
              alignment: PlaceholderAlignment.baseline,
              baseline: TextBaseline.alphabetic,
              child: _AccentedChar(char: '톡', style: baseStyle, dotSize: _dotSize),
            ),
            const TextSpan(text: ' 쏘게 채우는 스마트 헬스케어'),
          ],
        ),
      ),
    );
  }
}

// 단일 글자 + 위에 노란 점 (자체 가운데 정렬)
class _AccentedChar extends StatelessWidget {
  final String char;
  final TextStyle style;
  final double dotSize;
  const _AccentedChar({required this.char, required this.style, required this.dotSize});

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      alignment: Alignment.topCenter,
      children: [
        Text(char, style: style),
        Positioned(
          top: -dotSize - 2,    // 글자 위 2dp 띄움
          child: Container(
            width: dotSize,
            height: dotSize,
            decoration: const BoxDecoration(
              color: AppColor.yellow,
              shape: BoxShape.circle,
            ),
          ),
        ),
      ],
    );
  }
}

// ─── 워드마크 "레몬•Aid" — 생동감 로고 ───
// 한글 "레몬" 과 영문 "Aid" 가 같은 크기로 합쳐진 통일된 로고.
// 노란 점이 가운데서 살짝 떠 있는 듯한 인상 (작은 그림자).
class _Brand extends StatelessWidget {
  const _Brand();
  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        // 한글 "레몬" — Gmarket Sans Bold
        Text(
          '레몬',
          style: TextStyle(
            fontFamily: 'GmarketSans',
            fontSize: 44,
            fontWeight: FontWeight.w800,
            color: AppColor.ink,
            letterSpacing: -1.8,
            height: 1.0,
          ),
        ),
        // 가운데 노란 점 — 살짝 떠 있는 인상
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6),
          child: Container(
            width: 14, height: 14,
            decoration: BoxDecoration(
              color: AppColor.yellow,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: AppColor.yellow.withOpacity(0.55),
                  blurRadius: 10,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
          ),
        ),
        // 한글 "에이드"
        Text(
          '에이드',
          style: TextStyle(
            fontFamily: 'GmarketSans',
            fontSize: 44,
            fontWeight: FontWeight.w800,
            color: AppColor.ink,
            letterSpacing: -1.8,
            height: 1.0,
          ),
        ),
      ],
    );
  }
}

// ─── 최근 로그인 툴팁 — 검정 배경 + 노란 텍스트 + 바운스 ───
class _RecentLoginTooltip extends StatefulWidget {
  const _RecentLoginTooltip();
  @override
  State<_RecentLoginTooltip> createState() => _RecentLoginTooltipState();
}

class _RecentLoginTooltipState extends State<_RecentLoginTooltip>
    with SingleTickerProviderStateMixin {
  late final AnimationController _bounce;
  late final Animation<double> _dy;

  @override
  void initState() {
    super.initState();
    _bounce = AnimationController(vsync: this, duration: const Duration(milliseconds: 1400))
      ..repeat(reverse: true);
    _dy = Tween<double>(begin: -3, end: 3).animate(
      CurvedAnimation(parent: _bounce, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() { _bounce.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: AnimatedBuilder(
        animation: _dy,
        builder: (_, child) => Transform.translate(offset: Offset(0, _dy.value), child: child),
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: AppColor.ink,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Text(
                '최근 로그인했어요',
                style: TextStyle(
                  fontFamily: 'Pretendard',
                  fontSize: 13, fontWeight: FontWeight.w700,
                  color: AppColor.yellow, height: 1.0,
                  letterSpacing: -0.2,
                ),
              ),
            ),
            Positioned(
              left: 24, bottom: -6,
              child: CustomPaint(
                size: const Size(12, 7),
                painter: _ArrowPainter(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ArrowPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = AppColor.ink;
    final path = Path()
      ..moveTo(0, 0)
      ..lineTo(size.width / 2, size.height)
      ..lineTo(size.width, 0)
      ..close();
    canvas.drawPath(path, paint);
  }
  @override
  bool shouldRepaint(_) => false;
}
