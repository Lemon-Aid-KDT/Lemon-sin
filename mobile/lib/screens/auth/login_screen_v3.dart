// screens/auth/login_screen_v3.dart — Lemon Aid Login (Flat 2.0 + 카드 기반)
//
// 디자인 시스템 v2.0 (UX_DIARY §14.10) 적용.
// Toss / 여기어때 톤. 뉴모 효과 없음. 깔끔·실용·시중 앱 패턴.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../providers/auth_provider.dart';
import '../../services/token_storage.dart';
import '../../utils/oauth_config.dart';
import '../../utils/router.dart';
import '../../utils/design_tokens_v2.dart';

// 카카오 로고 위 글자 색 — 카카오 가이드의 진한 갈색 (#191600)
const Color _kakaoInk = Color(0xFF191600);

class LoginScreenV3 extends ConsumerStatefulWidget {
  const LoginScreenV3({super.key});

  @override
  ConsumerState<LoginScreenV3> createState() => _LoginScreenV3State();
}

class _LoginScreenV3State extends ConsumerState<LoginScreenV3> {
  AuthProvider? _lastProvider;

  @override
  void initState() {
    super.initState();
    _loadLastProvider();
  }

  Future<void> _loadLastProvider() async {
    final p = await ref.read(authControllerProvider.notifier).readLastProvider();
    if (!mounted) return;
    setState(() => _lastProvider = p);
  }

  /// tooltip 영역 — 매칭되면 실 위젯, 안 되면 SizedBox.shrink().
  /// 캐릭터 위치 고정은 OAuth 영역 위 SizedBox 로 보장 (각 슬롯 동적 높이는 OK).
  Widget _tooltipFor(AuthProvider provider) {
    if (_lastProvider != provider) return const SizedBox.shrink();
    final (bg, fg, border) = _tooltipColors(provider);
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpace.sm),
      child: _RecentLoginTooltip(
        background: bg,
        foreground: fg,
        borderColor: border,
      ),
    );
  }

  /// provider 별 색 매핑 — 버튼 톤에 맞춤. (bg, fg, border?)
  (Color, Color, Color?) _tooltipColors(AuthProvider provider) {
    switch (provider) {
      case AuthProvider.kakao:
        // 카카오 — 검정 배경 + 노란 글자 (현재 톤 유지)
        return (AppColor.ink, AppColor.yellow, null);
      case AuthProvider.google:
        // 구글 — 흰 배경 + 검정 글자 + 얇은 회색 보더 (Google 버튼과 일관)
        return (AppColor.surface, AppColor.ink, AppColor.border);
      case AuthProvider.apple:
        // Apple — 검정 배경 + 흰 글자
        return (AppColor.appleBlack, Colors.white, null);
      case AuthProvider.email:
        // 자체 가입/로그인 — 브랜드 블루 배경 + 흰 글자
        return (AppColor.brand, Colors.white, null);
    }
  }

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
                const SizedBox(height: 9),  // 워드마크 ↔ 태그라인 간격 12 → 9 (태그라인 위로 3dp)
                const _Tagline(),

                // 태그라인 ↔ 캐릭터 사이 — Spacer 가 남은 세로 공간 흡수.
                // 기존 Spacer 1 → 캐릭터·버튼 묶음 살짝 위로: Spacer flex 비율을 잘라
                //   위쪽 (Spacer 3) : 아래쪽 (SizedBox 으로 추가 여백) 으로 분배해
                //   결과적으로 묶음이 약 12 ~ 16dp 위로 올라옴.
                const Spacer(flex: 3),

                // ─── 캐릭터 ───
                Transform.translate(
                  offset: const Offset(0, 8),
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

                // 캐릭터 ↔ OAuth 영역 사이 고정 여백 (12dp).
                // tooltip 이 카카오 위에 뜰 때는 자동으로 + tooltip 높이만큼 떨어져 보임.
                // tooltip 없을 때도 캐릭터가 버튼에 바짝 붙지 않도록 최소 간격 보장.
                const SizedBox(height: AppSpace.sm + 4),

                // ─── OAuth 3종 (카카오 / 구글 / Apple) ───
                // 각 버튼 위에 — 마지막 로그인 방식이 그 버튼이면 "최근 로그인" 말풍선 표시.
                // 카카오·Apple → 뉴모 액센트 (감성 강조, 진입 첫 화면 인상)
                // 구글 → Flat (대비, 균형)
                _tooltipFor(AuthProvider.kakao),
                AppPrimaryButton(
                  label: '카카오로 계속하기',
                  color: AppColor.kakao,
                  textColor: _kakaoInk,
                  accent: true,
                  onPressed: () => _handleKakaoLogin(context, ref),
                  leading: SvgPicture.asset(
                    'assets/icons/kakao_message.svg',
                    width: 20, height: 20,
                    colorFilter: const ColorFilter.mode(_kakaoInk, BlendMode.srcIn),
                  ),
                ),
                const SizedBox(height: AppSpace.md),
                _tooltipFor(AuthProvider.google),
                AppSecondaryButton(
                  label: '구글로 계속하기',
                  onPressed: () => _handleGoogleLogin(context, ref),
                  leading: SvgPicture.asset('assets/icons/google_g.svg', width: 20, height: 20),
                ),
                const SizedBox(height: AppSpace.md),
                _tooltipFor(AuthProvider.apple),
                AppPrimaryButton(
                  label: 'Apple로 계속하기',
                  color: AppColor.appleBlack,
                  accent: true,
                  // Apple 로그인은 iOS 합류 후 구현 — sign_in_with_apple 추가 필요.
                  onPressed: () => _showNotReady(context, 'Apple'),
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

                // 이메일 로그인 영역에도 마지막 로그인 표시 — 로그인 버튼 위쪽으로
                _tooltipFor(AuthProvider.email),

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
                        onPressed: () => _showEmailLoginSheet(context, ref),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: AppSpace.xl),

                // 캐릭터·버튼 묶음을 위로 끌어올리기 위한 하단 흡수 Spacer
                const Spacer(flex: 1),

                Center(
                  child: Text(
                    '© Lemon Aid · 이용약관 · 개인정보',
                    style: AppText.micro,
                  ),
                ),
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

// ─── 최근 로그인 툴팁 — provider 별 색상 매칭 + 바운스 ───
// provider 마다 톤 다르게:
//   카카오 → 검정 배경 + 노란 글자 (현재 톤)
//   구글  → 흰 배경 + 검정 글자 + 회색 보더
//   Apple → 검정 배경 + 흰 글자
//   이메일(자체) → 브랜드 블루 배경 + 흰 글자
class _RecentLoginTooltip extends StatefulWidget {
  const _RecentLoginTooltip({
    required this.background,
    required this.foreground,
    this.borderColor,
  });
  final Color background;
  final Color foreground;
  final Color? borderColor;
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
                color: widget.background,
                borderRadius: BorderRadius.circular(10),
                border: widget.borderColor != null
                    ? Border.all(color: widget.borderColor!, width: 1)
                    : null,
              ),
              child: Text(
                '최근 로그인했어요',
                style: TextStyle(
                  fontFamily: 'Pretendard',
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: widget.foreground,
                  height: 1.0,
                  letterSpacing: -0.2,
                ),
              ),
            ),
            Positioned(
              left: 24, bottom: -6,
              child: CustomPaint(
                size: const Size(12, 7),
                painter: _ArrowPainter(
                  fill: widget.background,
                  border: widget.borderColor,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ArrowPainter extends CustomPainter {
  _ArrowPainter({required this.fill, this.border});
  final Color fill;
  final Color? border;

  @override
  void paint(Canvas canvas, Size size) {
    final path = Path()
      ..moveTo(0, 0)
      ..lineTo(size.width / 2, size.height)
      ..lineTo(size.width, 0)
      ..close();
    canvas.drawPath(path, Paint()..color = fill);
    // 보더 있으면 두 사선만 그림 (윗변은 버튼과 맞닿아 가려져도 OK)
    if (border != null) {
      final stroke = Paint()
        ..color = border!
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1;
      final left = Path()..moveTo(0, 0)..lineTo(size.width / 2, size.height);
      final right = Path()..moveTo(size.width, 0)..lineTo(size.width / 2, size.height);
      canvas.drawPath(left, stroke);
      canvas.drawPath(right, stroke);
    }
  }
  @override
  bool shouldRepaint(covariant _ArrowPainter old) =>
      old.fill != fill || old.border != border;
}

// ─── OAuth 버튼 핸들러 ───
// 키 미주입 상태에서 누르면 안내 SnackBar 만 띄움.
// 키 있으면 SDK 호출 → 백엔드 검증 → 인증 상태 변경 (router 가 자동 /shell 이동)
Future<void> _handleKakaoLogin(BuildContext context, WidgetRef ref) async {
  if (!OAuthConfig.hasKakaoKey) {
    _showNotReady(context, '카카오');
    return;
  }
  final ok = await ref.read(authControllerProvider.notifier).signInWithKakao();
  if (!ok && context.mounted) {
    final msg = ref.read(authControllerProvider).errorMessage;
    if (msg != null && msg.isNotEmpty) {
      _showSnack(context, msg);
    }
  }
}

Future<void> _handleGoogleLogin(BuildContext context, WidgetRef ref) async {
  if (!OAuthConfig.hasGoogleKey) {
    _showNotReady(context, '구글');
    return;
  }
  final ok = await ref.read(authControllerProvider.notifier).signInWithGoogle();
  if (!ok && context.mounted) {
    final msg = ref.read(authControllerProvider).errorMessage;
    if (msg != null && msg.isNotEmpty) {
      _showSnack(context, msg);
    }
  }
}

void _showNotReady(BuildContext context, String provider) {
  _showSnack(
    context,
    '$provider 로그인은 키 설정 후 사용할 수 있어요',
  );
}

void _showSnack(BuildContext context, String message) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(
      content: Text(message),
      behavior: SnackBarBehavior.floating,
      duration: const Duration(seconds: 4),
    ));
}

// ─── 이메일 로그인 바텀시트 ───
// "로그인" 버튼 누르면 뜸. 회원가입은 별도 화면 (/signup).
Future<void> _showEmailLoginSheet(BuildContext context, WidgetRef ref) async {
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: AppColor.bg,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (sheetContext) {
      return Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(sheetContext).viewInsets.bottom,
        ),
        child: const _EmailLoginSheet(),
      );
    },
  );
}

class _EmailLoginSheet extends ConsumerStatefulWidget {
  const _EmailLoginSheet();

  @override
  ConsumerState<_EmailLoginSheet> createState() => _EmailLoginSheetState();
}

class _EmailLoginSheetState extends ConsumerState<_EmailLoginSheet> {
  final _email = TextEditingController();
  final _pw = TextEditingController();
  final _pwFocus = FocusNode();
  bool _showPw = false;
  bool _submitting = false;
  String? _emailErr;
  String? _pwErr;

  @override
  void dispose() {
    _email.dispose();
    _pw.dispose();
    _pwFocus.dispose();
    super.dispose();
  }

  bool _validate() {
    final email = _email.text.trim();
    final pw = _pw.text;
    setState(() {
      _emailErr = email.isEmpty
          ? '이메일을 입력해주세요'
          : !RegExp(r'^[\w\.-]+@[\w\.-]+\.\w+$').hasMatch(email)
              ? '이메일 형식이 아니에요'
              : null;
      _pwErr = pw.isEmpty ? '비밀번호를 입력해주세요' : null;
    });
    return _emailErr == null && _pwErr == null;
  }

  Future<void> _submit() async {
    if (_submitting) return;
    if (!_validate()) return;
    setState(() => _submitting = true);

    final controller = ref.read(authControllerProvider.notifier);
    final ok = await controller.loginWithEmail(
      email: _email.text.trim(),
      password: _pw.text,
    );

    if (!mounted) return;
    setState(() => _submitting = false);

    if (ok) {
      Navigator.of(context).pop();
      // 라우터 refreshListenable 가 인증 상태 변경 감지 → /shell 자동 이동.
      // 보강: 직접 push 로 즉시 반응.
      context.go(AppRoute.shellHome);
    } else {
      final msg = ref.read(authControllerProvider).errorMessage ??
          '로그인에 실패했어요';
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(
          content: Text(msg),
          behavior: SnackBarBehavior.floating,
        ));
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
            AppSpace.xl, AppSpace.lg, AppSpace.xl, AppSpace.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Drag handle
            Center(
              child: Container(
                width: 36,
                height: 4,
                margin: const EdgeInsets.only(bottom: AppSpace.lg),
                decoration: BoxDecoration(
                  color: AppColor.border,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            Text(
              '이메일로 로그인',
              style: AppText.title.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: AppSpace.lg),

            AppTextField(
              controller: _email,
              label: '이메일',
              hint: 'example@email.com',
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              onSubmitted: (_) => _pwFocus.requestFocus(),
              error: _emailErr,
            ),
            const SizedBox(height: AppSpace.lg),

            AppTextField(
              controller: _pw,
              focusNode: _pwFocus,
              label: '비밀번호',
              obscure: !_showPw,
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _submit(),
              error: _pwErr,
              suffix: IconButton(
                icon: Icon(
                  _showPw
                      ? Icons.visibility_off_outlined
                      : Icons.visibility_outlined,
                  color: AppColor.inkTertiary,
                  size: 22,
                ),
                onPressed: () => setState(() => _showPw = !_showPw),
              ),
            ),
            const SizedBox(height: AppSpace.xl),

            AppPrimaryButton(
              label: _submitting ? '로그인 중...' : '로그인',
              accent: true,
              loading: _submitting,
              enabled: !_submitting,
              onPressed: _submit,
            ),
            const SizedBox(height: AppSpace.md),
            Center(
              child: TextButton(
                onPressed: _submitting
                    ? null
                    : () {
                        Navigator.of(context).pop();
                        context.push(AppRoute.signup);
                      },
                child: Text(
                  '계정이 없어요 — 회원가입',
                  style: AppText.body.copyWith(
                    color: AppColor.inkSecondary,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
