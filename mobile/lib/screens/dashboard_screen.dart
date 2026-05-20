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
import 'package:go_router/go_router.dart';

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
                    // 1. 메인 박스 (캐릭터 + 동적 인사 메시지)
                    _GreetingCard(),
                    SizedBox(height: AppSpace.md),
                    // 2. 오늘의 영양 진행률 (칼로리·탄단지)
                    _NutritionProgressCard(),
                    SizedBox(height: AppSpace.md),
                    // 3. 5종 분석 결과 grid
                    _FiveOutputsSection(),
                    SizedBox(height: AppSpace.md),
                    // 4. 복약 알람 (오늘 먹을 영양제·약)
                    _SupplementAlarmCard(),
                    SizedBox(height: AppSpace.md),
                    // 5. 최근 분석
                    _RecentAnalysisCard(),
                    SizedBox(height: AppSpace.lg),
                    // 6. 의료 면책 문구
                    _MedicalDisclaimer(),
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
                    onTap: () => context.push('/calendar'),
                  ),
                  const SizedBox(width: AppSpace.sm),
                  _HeaderIconButton(
                    icon: Icons.notifications_rounded,
                    onTap: () => context.push('/notifications'),
                  ),
                  const SizedBox(width: AppSpace.sm),
                  _HeaderIconButton(
                    icon: Icons.person_rounded,
                    onTap: () => context.go('/shell/settings'),
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
/// 로그인 화면 _Brand 동일 패턴 (GmarketSans w800 + 가운데 점) 을 헤더 사이즈로 축소.
/// 노란 헤더 위라 점은 흰색 + 미세 그림자 (가독성).
class _Wordmark extends StatelessWidget {
  const _Wordmark();

  @override
  Widget build(BuildContext context) {
    const baseStyle = TextStyle(
      fontFamily: 'GmarketSans',
      fontSize: 26,
      fontWeight: FontWeight.w800,
      color: AppColor.ink,
      letterSpacing: -1.1,
      height: 1.0,
    );
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        const Text('레몬', style: baseStyle),
        // 가운데 흰색 점 + 미세 그림자 (노란 헤더 위 가독성)
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Container(
            width: 9, height: 9,
            decoration: BoxDecoration(
              color: AppColor.surface,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: AppColor.ink.withOpacity(0.10),
                  blurRadius: 6,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
          ),
        ),
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
// 공통 카드 데코 — LADS Flat 2.0 + Soft UI
// 모든 메인 카드는 이 톤 통일 (§17)
// ═══════════════════════════════════════════
BoxDecoration _mainCardDeco() => BoxDecoration(
      color: AppColor.surface,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      boxShadow: const [
        BoxShadow(
          color: Color.fromRGBO(140, 155, 175, 0.20),
          blurRadius: 16,
          offset: Offset(0, 5),
        ),
      ],
    );

// ═══════════════════════════════════════════
// 1. 인사 카드 — 캐릭터 + 동적 메시지
// ═══════════════════════════════════════════
class _GreetingCard extends StatelessWidget {
  const _GreetingCard();

  @override
  Widget build(BuildContext context) {
    final hour = DateTime.now().hour;
    final timeGreeting = hour < 11
        ? '좋은 아침이에요'
        : hour < 17
            ? '오늘도 화이팅이에요'
            : '오늘 하루 어떠셨어요';

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(
        AppSpace.cardInside + 2, AppSpace.xl,
        AppSpace.cardInside + 2, AppSpace.xl,
      ),
      decoration: _mainCardDeco(),
      child: Row(
        children: [
          // 캐릭터
          Image.asset(
            'assets/mascot/hello-mascot.png',
            width: 80, height: 80,
            fit: BoxFit.contain,
            errorBuilder: (_, __, ___) => Container(
              width: 80, height: 80,
              decoration: BoxDecoration(
                color: AppColor.brandSoft,
                shape: BoxShape.circle,
              ),
              alignment: Alignment.center,
              child: Icon(Icons.emoji_food_beverage,
                  color: AppColor.brand, size: 40),
            ),
          ),
          const SizedBox(width: AppSpace.md),
          // 인사 + 부족 영양소 한 줄
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  timeGreeting,
                  style: AppText.caption.copyWith(
                    color: AppColor.inkTertiary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '태동님',
                  style: AppText.title.copyWith(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    color: AppColor.ink,
                    letterSpacing: -0.4,
                  ),
                ),
                const SizedBox(height: AppSpace.sm),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpace.md, vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: AppColor.brandSoft,
                    borderRadius: BorderRadius.circular(AppRadius.full),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.bolt_rounded,
                          color: AppColor.brandDeep, size: 14),
                      const SizedBox(width: 4),
                      Text(
                        '비타민 D 부족',
                        style: AppText.caption.copyWith(
                          color: AppColor.brandDeep,
                          fontWeight: FontWeight.w700,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 2. 오늘의 영양 진행률 (칼로리·탄단지·진행 바)
// ═══════════════════════════════════════════
class _NutritionProgressCard extends StatelessWidget {
  const _NutritionProgressCard();

  @override
  Widget build(BuildContext context) {
    // TODO: 실제 데이터 연결 — 지금은 mock
    const consumed = 1240;
    const target = 1840;
    const ratio = consumed / target;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside + 2),
      decoration: _mainCardDeco(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('오늘의 영양', style: AppText.subtitle),
              Text(
                '${(ratio * 100).toInt()}%',
                style: AppText.subtitle.copyWith(
                  color: AppColor.brandDeep,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          // 칼로리 큰 숫자
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                '$consumed',
                style: const TextStyle(
                  fontFamily: 'Pretendard',
                  fontSize: 32,
                  fontWeight: FontWeight.w800,
                  color: AppColor.ink,
                  letterSpacing: -0.8,
                  height: 1.0,
                ),
              ),
              Text(
                ' / $target kcal',
                style: AppText.body.copyWith(
                  color: AppColor.inkSecondary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          // 진행 바
          ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.full),
            child: LinearProgressIndicator(
              value: ratio.clamp(0.0, 1.0),
              minHeight: 8,
              backgroundColor: const Color(0xFFF1F3F6),
              valueColor: AlwaysStoppedAnimation(AppColor.brand),
            ),
          ),
          const SizedBox(height: AppSpace.lg),
          // 탄단지 3개
          Row(
            children: const [
              Expanded(child: _MacroBar(label: '탄수화물', value: 142, target: 230, color: Color(0xFFFFB200))),
              SizedBox(width: AppSpace.sm),
              Expanded(child: _MacroBar(label: '단백질', value: 42, target: 72, color: Color(0xFF22B07D))),
              SizedBox(width: AppSpace.sm),
              Expanded(child: _MacroBar(label: '지방', value: 38, target: 60, color: Color(0xFFFF6B6B))),
            ],
          ),
        ],
      ),
    );
  }
}

class _MacroBar extends StatelessWidget {
  final String label;
  final int value;
  final int target;
  final Color color;
  const _MacroBar({
    required this.label,
    required this.value,
    required this.target,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final ratio = (value / target).clamp(0.0, 1.0);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: AppText.caption.copyWith(color: AppColor.inkSecondary, fontWeight: FontWeight.w600)),
        const SizedBox(height: 4),
        Row(
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          children: [
            Text('$value',
                style: AppText.body.copyWith(color: AppColor.ink, fontWeight: FontWeight.w800)),
            Text(' / $target g',
                style: AppText.caption.copyWith(color: AppColor.inkTertiary)),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.full),
          child: LinearProgressIndicator(
            value: ratio,
            minHeight: 4,
            backgroundColor: const Color(0xFFF1F3F6),
            valueColor: AlwaysStoppedAnimation(color),
          ),
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════
// 3. 5종 분석 결과 grid (부족/과다/주의/점수/목적)
// ═══════════════════════════════════════════
class _FiveOutputsSection extends StatelessWidget {
  const _FiveOutputsSection();

  @override
  Widget build(BuildContext context) {
    const items = [
      _OutputSpec(icon: Icons.eco_rounded, color: Color(0xFF22B07D),
          label: '부족 영양소', value: '비타민D'),
      _OutputSpec(icon: Icons.warning_amber_rounded, color: Color(0xFFFF9500),
          label: '과다 섭취', value: '나트륨'),
      _OutputSpec(icon: Icons.shield_outlined, color: Color(0xFFFF6B6B),
          label: '주의 성분', value: '비타민K'),
      _OutputSpec(icon: Icons.workspace_premium_rounded, color: Color(0xFFFFB200),
          label: '식단 점수', value: '78점'),
      _OutputSpec(icon: Icons.flag_rounded, color: Color(0xFF4D7BFF),
          label: '목적별', value: '당뇨'),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Text('오늘의 분석', style: AppText.subtitle),
        ),
        const SizedBox(height: AppSpace.sm),
        SizedBox(
          height: 110,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(width: AppSpace.sm),
            itemBuilder: (ctx, i) => _OutputCard(spec: items[i]),
          ),
        ),
      ],
    );
  }
}

class _OutputSpec {
  final IconData icon;
  final Color color;
  final String label;
  final String value;
  const _OutputSpec({
    required this.icon,
    required this.color,
    required this.label,
    required this.value,
  });
}

class _OutputCard extends StatelessWidget {
  final _OutputSpec spec;
  const _OutputCard({required this.spec});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 110,
      padding: const EdgeInsets.all(AppSpace.md + 2),
      decoration: _mainCardDeco(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Container(
            width: 32, height: 32,
            decoration: BoxDecoration(
              color: spec.color.withOpacity(0.12),
              borderRadius: BorderRadius.circular(AppRadius.sm - 2),
            ),
            alignment: Alignment.center,
            child: Icon(spec.icon, size: 18, color: spec.color),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                spec.label,
                style: AppText.caption.copyWith(
                  color: AppColor.inkTertiary,
                  fontWeight: FontWeight.w600,
                  fontSize: 11,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                spec.value,
                style: AppText.body.copyWith(
                  color: AppColor.ink,
                  fontWeight: FontWeight.w800,
                  fontSize: 14,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 4. 복약 알람 카드 (오늘 먹을 영양제·약)
// ═══════════════════════════════════════════
class _SupplementAlarmCard extends StatelessWidget {
  const _SupplementAlarmCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside + 2),
      decoration: _mainCardDeco(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('오늘 복용', style: AppText.subtitle),
              Text(
                '2/4 완료',
                style: AppText.caption.copyWith(
                  color: AppColor.brandDeep,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          const _AlarmRow(
            time: '09:00',
            name: '비타민 D',
            dose: '1정',
            taken: true,
          ),
          Divider(color: AppColor.border, height: AppSpace.lg),
          const _AlarmRow(
            time: '13:00',
            name: '오메가-3',
            dose: '1정',
            taken: true,
          ),
          Divider(color: AppColor.border, height: AppSpace.lg),
          const _AlarmRow(
            time: '19:00',
            name: '프로바이오틱스',
            dose: '1정',
            taken: false,
          ),
          Divider(color: AppColor.border, height: AppSpace.lg),
          const _AlarmRow(
            time: '21:00',
            name: '마그네슘',
            dose: '1정',
            taken: false,
          ),
        ],
      ),
    );
  }
}

class _AlarmRow extends StatelessWidget {
  final String time;
  final String name;
  final String dose;
  final bool taken;
  const _AlarmRow({
    required this.time,
    required this.name,
    required this.dose,
    required this.taken,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        // 시간
        SizedBox(
          width: 56,
          child: Text(
            time,
            style: AppText.body.copyWith(
              color: taken ? AppColor.inkTertiary : AppColor.ink,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        // 이름 + 용량
        Expanded(
          child: Row(
            children: [
              Text(
                name,
                style: AppText.body.copyWith(
                  color: taken ? AppColor.inkTertiary : AppColor.ink,
                  fontWeight: FontWeight.w600,
                  decoration: taken ? TextDecoration.lineThrough : null,
                ),
              ),
              const SizedBox(width: AppSpace.xs),
              Text(
                dose,
                style: AppText.caption.copyWith(
                  color: AppColor.inkTertiary,
                ),
              ),
            ],
          ),
        ),
        // 체크 박스
        Container(
          width: 24, height: 24,
          decoration: BoxDecoration(
            color: taken ? AppColor.brand : const Color(0xFFE5E8EB),
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: Icon(
            Icons.check_rounded,
            color: Colors.white,
            size: 16,
          ),
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════
// 5. 최근 분석 (사진 + 결과)
// ═══════════════════════════════════════════
class _RecentAnalysisCard extends StatelessWidget {
  const _RecentAnalysisCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside + 2),
      decoration: _mainCardDeco(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('최근 분석', style: AppText.subtitle),
              Text(
                '전체 보기 ›',
                style: AppText.caption.copyWith(
                  color: AppColor.inkTertiary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          const _RecentRow(emoji: '💊', title: '오메가-3 1200mg', subtitle: '어제 · 부족 영양소 보완'),
          const SizedBox(height: AppSpace.md),
          const _RecentRow(emoji: '🥗', title: '점심 식단', subtitle: '오늘 12:30 · 80점'),
          const SizedBox(height: AppSpace.md),
          const _RecentRow(emoji: '💊', title: '비타민 D 1000IU', subtitle: '3일 전 · 권장량 충족'),
        ],
      ),
    );
  }
}

class _RecentRow extends StatelessWidget {
  final String emoji;
  final String title;
  final String subtitle;
  const _RecentRow({
    required this.emoji,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 44, height: 44,
          decoration: BoxDecoration(
            color: const Color(0xFFF1F3F6),
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          alignment: Alignment.center,
          child: Text(emoji, style: const TextStyle(fontSize: 22)),
        ),
        const SizedBox(width: AppSpace.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: AppText.body.copyWith(
                  color: AppColor.ink,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                style: AppText.caption.copyWith(
                  color: AppColor.inkTertiary,
                ),
              ),
            ],
          ),
        ),
        Icon(Icons.chevron_right_rounded,
            color: AppColor.inkTertiary, size: 20),
      ],
    );
  }
}

// ═══════════════════════════════════════════
// 6. 의료 면책 (LADS §14)
// ═══════════════════════════════════════════
class _MedicalDisclaimer extends StatelessWidget {
  const _MedicalDisclaimer();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.brandSoft,
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, color: AppColor.brandDeep, size: 18),
          const SizedBox(width: AppSpace.sm),
          Expanded(
            child: Text(
              '레몬에이드는 건강 관리를 도와드리는 서비스로\n의사·약사·영양사의 진단을 대신하진 않아요.',
              style: AppText.caption.copyWith(
                color: AppColor.ink,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
