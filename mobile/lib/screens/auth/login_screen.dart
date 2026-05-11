// screens/auth/login_screen.dart — Lemon Aid Login
//
// 진짜 Figma Export ZIP (LoginButtons.tsx + LemonMascot.tsx) 1:1 변환.
//   - SVG asset 그대로 사용 (마스코트·구글 G·카카오 말풍선)
//   - 토큰 정확히 일치
//   - 12 variant 모두 명세 그대로
//
// 참조:
//   - 다이어리 §14.7 S-02 Login
//   - 다이어리 §12.5.1 건강의신 정밀 분석
//   - Figma export: src/app/components/{LoginButtons,LemonMascot}.tsx

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../utils/router.dart';
import '../../utils/tokens.dart';
import '../../widgets/common/lemon_button.dart';
import '../../widgets/common/lemon_text_field.dart';

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: LemonColors.bg,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ─── 상단 : 워드마크 + 태그라인 ───
              const SizedBox(height: 48),
              const _Wordmark(),
              const SizedBox(height: 12),
              Text(
                '사진 한 번, 영양 분석 끝',
                style: LemonText.body.copyWith(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: LemonColors.inkSoft,
                ),
              ),

              // ─── 중앙 : 호흡 공간 (마스코트 임시 제거) ───
              // Spacer로 CTA를 아래로 밀어내기 (워드마크와 CTA 사이 빈 공간)
              const Spacer(),

              // ─── 하단 : CTA ───
              // 툴팁 (재방문 시만 표시 — 디자인 검증용 항상 노출)
              const _RecentLoginTooltip(),
              const SizedBox(height: 10),

              // 카카오 풀폭
              LemonButton.kakao(
                label: '카카오로 계속하기',
                onPressed: null,
                leading: SvgPicture.asset(
                  'assets/icons/kakao_message.svg',
                  width: 20,
                  height: 20,
                  colorFilter: const ColorFilter.mode(
                    Color(0xFF191919),
                    BlendMode.srcIn,
                  ),
                ),
              ),
              const SizedBox(height: 12),

              // 구글 풀폭
              LemonButton.google(
                label: '구글로 계속하기',
                onPressed: null,
                leading: SvgPicture.asset(
                  'assets/icons/google_g.svg',
                  width: 20,
                  height: 20,
                ),
              ),
              const SizedBox(height: 12),

              // Apple 풀폭 (iOS 호환성 + 검정 배경)
              LemonButton.apple(
                label: 'Apple로 계속하기',
                onPressed: null,
                leading: SvgPicture.asset(
                  'assets/icons/apple_logo.svg',
                  width: 20,
                  height: 20,
                  colorFilter: const ColorFilter.mode(
                    Colors.white,
                    BlendMode.srcIn,
                  ),
                ),
              ),
              const SizedBox(height: 18),

              // 디바이더 + "이메일로 시작하기" 인라인 라벨
              Row(
                children: [
                  const Expanded(
                    child: Divider(
                      height: 1,
                      thickness: 1,
                      color: LemonColors.line,
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Text(
                      '이메일로 시작하기',
                      style: TextStyle(
                        fontFamily: LemonFont.body,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                        color: LemonColors.inkMute,
                      ),
                    ),
                  ),
                  const Expanded(
                    child: Divider(
                      height: 1,
                      thickness: 1,
                      color: LemonColors.line,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // 회원가입(좌·Outline) + 로그인(우·Primary) 분할 — 1:2 비율
              Row(
                children: [
                  Expanded(
                    flex: 1,
                    child: LemonButton.secondary(
                      label: '회원가입',
                      onPressed: () => context.push(AppRoute.signup),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    flex: 2,
                    child: LemonButton.primary(
                      label: '로그인',
                      onPressed: () => _openEmailSheet(context),
                    ),
                  ),
                ],
              ),

              // CTA와 약관 사이 — 60dp (버튼 위로 20dp 더 올림)
              const SizedBox(height: 60),

              // 약관 caption — 화면 아래
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Center(
                  child: Text(
                    '© Lemon Aid · 이용약관 · 개인정보',
                    style: LemonText.caption.copyWith(
                      fontSize: 12,
                      color: LemonColors.inkMute,
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

  void _openEmailSheet(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: LemonColors.bgElev,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(LemonRadius.xl)),
      ),
      builder: (_) => const _EmailLoginSheet(),
    );
  }
}

// ─── 워드마크 "Lemon Aid" + 작은 노란 레몬 점 ───
class _Wordmark extends StatelessWidget {
  const _Wordmark();

  @override
  Widget build(BuildContext context) {
    return Row(
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

// ─── 레몬 마스코트 — Figma SVG 그대로 ───
class _LemonMascot extends StatelessWidget {
  const _LemonMascot();

  @override
  Widget build(BuildContext context) {
    return SvgPicture.asset(
      'assets/illustrations/lemon_mascot.svg',
      width: 160,
      height: 180,
    );
  }
}

// ─── "최근 로그인했어요" 툴팁 — 스크린샷 정밀 매칭 ───
// 디자인:
//   - 검정 배경 + 흰 텍스트
//   - radius 10 (pill 보다 살짝 각진 둥근 사각)
//   - padding 14 H · 7 V
//   - 부드러운 그림자 (노란 카카오 위에 떠있는 느낌)
//   - 좌측 약 1/4 지점 아래 삼각 화살표 (카카오 말풍선 아이콘 위)
class _RecentLoginTooltip extends StatelessWidget {
  const _RecentLoginTooltip();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
            decoration: BoxDecoration(
              color: LemonColors.ink,
              borderRadius: BorderRadius.circular(10),
              boxShadow: [
                BoxShadow(
                  color: LemonColors.ink.withOpacity(0.16),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
                BoxShadow(
                  color: LemonColors.ink.withOpacity(0.10),
                  blurRadius: 4,
                  offset: const Offset(0, 1),
                ),
              ],
            ),
            child: const Text(
              '최근 로그인했어요',
              style: TextStyle(
                fontFamily: LemonFont.body,
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: Colors.white,
                height: 1.0,
                letterSpacing: -0.2,
              ),
            ),
          ),
          // 화살표 — 좌측 약 1/4 지점에 (카카오 말풍선 아이콘 위쪽)
          Positioned(
            left: 24,
            bottom: -6,
            child: CustomPaint(
              size: const Size(12, 7),
              painter: _TooltipArrowPainter(),
            ),
          ),
        ],
      ),
    );
  }
}

class _TooltipArrowPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = LemonColors.ink;
    final path = Path()
      ..moveTo(0, 0)
      ..lineTo(size.width / 2, size.height)
      ..lineTo(size.width, 0)
      ..close();
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// ─── 이메일 로그인 BottomSheet ───
class _EmailLoginSheet extends StatelessWidget {
  const _EmailLoginSheet();

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Padding(
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        top: 16,
        bottom: 24 + bottomInset,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 드래그 핸들
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: LemonColors.lineStrong,
                borderRadius: BorderRadius.circular(999),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text(
            '이메일로 로그인',
            style: LemonText.title.copyWith(fontSize: 22),
          ),
          const SizedBox(height: 20),
          const LemonTextField(
            label: '이메일',
            hint: 'name@email.com',
            keyboardType: TextInputType.emailAddress,
            autofillHints: [AutofillHints.email],
          ),
          const SizedBox(height: 16),
          const LemonTextField(
            label: '비밀번호',
            hint: '8자 이상, 영문+숫자',
            obscure: true,
            obscureToggle: true,
            textInputAction: TextInputAction.done,
            autofillHints: [AutofillHints.password],
          ),
          const SizedBox(height: 24),
          LemonButton.primary(
            label: '로그인',
            onPressed: null,
          ),
          const SizedBox(height: 12),
          Center(
            child: TextButton(
              onPressed: () {
                Navigator.pop(context);
                context.push(AppRoute.signup);
              },
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '처음이신가요? 회원가입',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: LemonColors.brand,
                    ),
                  ),
                  SizedBox(width: 4),
                  Icon(Icons.arrow_forward, size: 16, color: LemonColors.brand),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
