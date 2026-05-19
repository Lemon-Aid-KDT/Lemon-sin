// screens/dashboard_screen.dart — 홈 (메인 화면)
//
// 디자인: Pillyze 시안 기반 LADS 톤 변환
//   - 상단: brand 노랑 헤더 (로고 + 우측 아이콘 3개 + 캘린더 weekday strip)
//   - 본문: 흰 배경 카드들 (P0 작업 — 추후 단계별)
//
// 작업 순서:
//   ✅ 1. 상단 헤더 + weekday 캘린더 (지금 단계)
//   ⏳ 2. 식단 카드
//   ⏳ 3. 5종 분석 결과
//   ⏳ 4. 최근 분석
//   ⏳ 5. 의료 면책

import 'package:flutter/material.dart';

import '../utils/design_tokens_v2.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.bg,
      body: Column(
        children: [
          // ─── 상단 brand 헤더 (status bar 까지 포함) ───
          const _BrandHeader(),

          // ─── 본문 ───
          // 헤더(노랑)와 만나는 지점에서 본문(흰)이 위쪽으로 둥글게 올라옴 (Pillyze 톤)
          Expanded(
            child: Transform.translate(
              offset: const Offset(0, -24),
              child: Container(
                decoration: const BoxDecoration(
                  color: AppColor.bg,
                  borderRadius: BorderRadius.only(
                    topLeft: Radius.circular(28),
                    topRight: Radius.circular(28),
                  ),
                ),
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(
                    AppSpace.page,
                    AppSpace.xl,
                    AppSpace.page,
                    AppSpace.xl + 80,
                  ),
                  children: const [
                    _MainCard(),
                    SizedBox(height: AppSpace.md),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 상단 brand 헤더 (Pillyze 톤)
//   - status bar 부터 색 채움
//   - 로고 + 우측 아이콘 3개
//   - weekday strip + 날짜 (오늘 = 흰 원 강조)
// ═══════════════════════════════════════════
class _BrandHeader extends StatelessWidget {
  const _BrandHeader();

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    // 이번 주 월요일 기준 7일
    final monday = today.subtract(Duration(days: today.weekday - 1));
    final days = List.generate(7, (i) => monday.add(Duration(days: i)));
    const weekdayLabels = ['월', '화', '수', '목', '금', '토', '일'];

    return Container(
      color: AppColor.brand,
      child: SafeArea(
        bottom: false,
        child: Padding(
          // 노란 헤더 영역 더 넓고 길게 — 위 lg(16), 아래 xl+xl(48) + 좌우 page(24)
          padding: const EdgeInsets.fromLTRB(
            AppSpace.page, AppSpace.lg, AppSpace.page, AppSpace.xl + AppSpace.xl,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ─── 상단 행: 한국어 워드마크 + 우측 아이콘들 ───
              Row(
                children: [
                  // 워드마크: "레몬·에이드" — 가운데 점 강조 (브랜드 시그니처)
                  const _Wordmark(),
                  const Spacer(),
                  _HeaderIconButton(
                    icon: Icons.calendar_today_rounded,
                    onTap: () {
                      // TODO: 캘린더 화면
                    },
                  ),
                  const SizedBox(width: AppSpace.sm),
                  _HeaderIconButton(
                    icon: Icons.notifications_rounded,
                    onTap: () {
                      // TODO: 알림 화면
                    },
                  ),
                  const SizedBox(width: AppSpace.sm),
                  _HeaderIconButton(
                    icon: Icons.person_rounded,
                    onTap: () {
                      // TODO: 프로필 화면
                    },
                  ),
                ],
              ),

              const SizedBox(height: AppSpace.xl),

              // ─── 요일 strip ───
              Row(
                children: [
                  for (int i = 0; i < 7; i++)
                    Expanded(
                      child: Center(
                        child: Text(
                          weekdayLabels[i],
                          style: AppText.caption.copyWith(
                            color: AppColor.ink.withOpacity(0.75),
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ),
                ],
              ),

              const SizedBox(height: AppSpace.sm),

              // ─── 날짜 strip (오늘 = 흰 원 강조) ───
              Row(
                children: [
                  for (int i = 0; i < 7; i++)
                    Expanded(
                      child: _DateBubble(
                        day: days[i].day,
                        isToday: _isSameDay(days[i], today),
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  static bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;
}

/// 한국어 워드마크 — "레몬·에이드"
/// 가운데 점은 작은 원 (브랜드 시그니처 — 로그인 화면 "Lemon·Aid" 와 동일 톤)
class _Wordmark extends StatelessWidget {
  const _Wordmark();

  @override
  Widget build(BuildContext context) {
    const baseStyle = TextStyle(
      fontFamily: 'Pretendard',
      fontSize: 22,
      fontWeight: FontWeight.w800,
      color: AppColor.ink,
      letterSpacing: -0.6,
      height: 1.0,
    );
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        const Text('레몬', style: baseStyle),
        const SizedBox(width: 5),
        // 가운데 점 — 흰색 원 (노란 헤더 위에서 또렷)
        Container(
          width: 6, height: 6,
          decoration: const BoxDecoration(
            color: AppColor.surface,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 5),
        const Text('에이드', style: baseStyle),
      ],
    );
  }
}

class _HeaderIconButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  const _HeaderIconButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: 32, height: 32,
        child: Icon(icon, color: AppColor.ink, size: 22),
      ),
    );
  }
}

class _DateBubble extends StatelessWidget {
  final int day;
  final bool isToday;
  const _DateBubble({required this.day, required this.isToday});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        width: 36, height: 36,
        decoration: BoxDecoration(
          color: isToday ? AppColor.surface : Colors.transparent,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Text(
          '$day',
          style: AppText.bodyLg.copyWith(
            color: AppColor.ink,
            fontWeight: isToday ? FontWeight.w800 : FontWeight.w600,
            fontSize: 16,
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 메인 박스 — 캘린더 아래 첫 번째 카드
// 캐릭터 + 분석 미리보기 등 들어갈 자리 (지금은 셸)
//
// 디자인: Flat 2.0 + Soft UI (LADS §17 일관성)
//   - 흰 배경
//   - 라운드: Pillyze 톤 따라 살짝 더 둥글게 (AppRadius.lg = 20)
//   - 그림자: 회원가입 박스/메인 흰 버튼과 동일한 soft 톤
//   - 테두리 없음
// ═══════════════════════════════════════════
class _MainCard extends StatelessWidget {
  const _MainCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.cardInside + 2,
        vertical: AppSpace.xl,
      ),
      decoration: BoxDecoration(
        color: AppColor.surface,
        // Pillyze 톤 — Flat 2.0 라운드(sm=12)보다 살짝 더 둥글게.
        // 회원가입 박스/버튼은 sm 그대로 유지, 메인 박스만 lg(20) 로 차별.
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: const [
          // LADS 표준 soft UI 그림자 (회원가입 박스·메인 흰 버튼 동일)
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.20),
            blurRadius: 16,
            offset: Offset(0, 5),
          ),
        ],
      ),
      // 내용은 다음 단계에서 — 지금은 높이 확보용 SizedBox
      child: const SizedBox(
        height: 220,
      ),
    );
  }
}
