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
import '../widgets/common/pressable.dart';
import '../widgets/common/staggered_entrance.dart';
import '../widgets/dashboard/health_hero_card.dart';

class DashboardScreen extends StatefulWidget {
  // recordDate 가 null 이면 메인(오늘 고정).
  // 값이 있으면 '과거 기록 조회' 모드 — 풀스크린 별도 페이지.
  final DateTime? recordDate;
  const DashboardScreen({super.key, this.recordDate});

  bool get isRecordMode => recordDate != null;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  // 선택된 날짜 — 메인이면 항상 오늘, 기록 모드면 recordDate 부터.
  late DateTime _selectedDate;
  // 헤더 strip 이 보여주는 주 (그 주의 월요일)
  late DateTime _focusedMonday;

  bool get _isRecordMode => widget.isRecordMode;

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    final base = widget.recordDate ?? now;
    _selectedDate = DateTime(base.year, base.month, base.day);
    _focusedMonday = _mondayOf(_selectedDate);
  }

  static DateTime _mondayOf(DateTime d) =>
      DateTime(d.year, d.month, d.day).subtract(Duration(days: d.weekday - 1));

  static bool _sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  bool get _isToday => _sameDay(_selectedDate, DateTime.now());

  void _selectDate(DateTime d) {
    final picked = DateTime(d.year, d.month, d.day);
    // 미래 날짜는 선택 불가 (아직 기록 없음)
    if (picked.isAfter(DateTime.now())) return;
    // 페이지 이동 없이 그 자리에서 날짜 교체 — 본문이 페이드로 바뀜
    setState(() {
      _selectedDate = picked;
      _focusedMonday = _mondayOf(picked);
    });
  }

  void _shiftWeek(int delta) {
    setState(() {
      _focusedMonday = _focusedMonday.add(Duration(days: 7 * delta));
    });
  }

  void _goToday() {
    // 기록 모드면 → 메인(오늘)으로 돌아감 (페이지 pop)
    if (_isRecordMode) {
      if (context.canPop()) context.pop();
      return;
    }
    final now = DateTime.now();
    setState(() {
      _selectedDate = DateTime(now.year, now.month, now.day);
      _focusedMonday = _mondayOf(now);
    });
  }

  // 본문 좌우 스와이프 — 오→왼(velocity<0) = 다음날 / 왼→오 = 이전날
  void _onBodySwipe(DragEndDetails d) {
    final v = d.primaryVelocity ?? 0;
    if (v.abs() < 200) return; // 약한 스와이프 무시
    if (v < 0) {
      // 다음 날 (미래는 _selectDate 가 막음)
      _selectDate(_selectedDate.add(const Duration(days: 1)));
    } else {
      // 이전 날
      _selectDate(_selectedDate.subtract(const Duration(days: 1)));
    }
  }

  // 본문 — 날짜별로 다시 그려짐 (key 로 AnimatedSwitcher 전환)
  Widget _buildBody({Key? key}) {
    return ListView(
      key: key,
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page,
        AppSpace.xl,
        AppSpace.page,
        AppSpace.xl + 80,
      ),
      children: [
        StaggeredEntrance(
          gap: AppSpace.md,
          children: [
            HealthHeroCard(
              onTapScore: () => context.go('/shell/score'),
              onTapDetail: () =>
                  context.push('/shell/home/analysis-result?mode=meal'),
            ),
            const _FiveOutputsSection(),
            const _SupplementAlarmCard(),
            const _RecentAnalysisCard(),
            const _MedicalDisclaimer(),
          ],
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.bg,
      body: Column(
        children: [
          // ─── 상단 brand 헤더 (status bar 까지 포함) ───
          _BrandHeader(
            selectedDate: _selectedDate,
            focusedMonday: _focusedMonday,
            isToday: _isToday,
            isRecordMode: _isRecordMode,
            onSelectDate: _selectDate,
            onShiftWeek: _shiftWeek,
            onGoToday: _goToday,
          ),

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
                // 좌우 스와이프로 날짜 이동 (만보기 앱 표준 UX)
                child: GestureDetector(
                  onHorizontalDragEnd: _onBodySwipe,
                  // 날짜 바뀔 때 본문 페이드 전환 ("딱" 안 바뀜)
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 280),
                    switchInCurve: Curves.easeOutQuart,
                    transitionBuilder: (child, anim) =>
                        FadeTransition(opacity: anim, child: child),
                    child: _buildBody(
                      key: ValueKey<String>(
                        '${_selectedDate.year}'
                        '-${_selectedDate.month}'
                        '-${_selectedDate.day}',
                      ),
                    ),
                  ),
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
  final DateTime selectedDate;
  final DateTime focusedMonday;
  final bool isToday;
  final bool isRecordMode;   // 과거 기록 페이지면 true
  final ValueChanged<DateTime> onSelectDate;
  final ValueChanged<int> onShiftWeek;   // -1 이전 주 / +1 다음 주
  final VoidCallback onGoToday;

  const _BrandHeader({
    required this.selectedDate,
    required this.focusedMonday,
    required this.isToday,
    required this.isRecordMode,
    required this.onSelectDate,
    required this.onShiftWeek,
    required this.onGoToday,
  });

  static bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    final days = List.generate(7, (i) => focusedMonday.add(Duration(days: i)));
    const weekdayLabels = ['월', '화', '수', '목', '금', '토', '일'];

    return Container(
      color: AppColor.brand,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.page, AppSpace.lg, AppSpace.page, AppSpace.xl + AppSpace.xl,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ─── 상단 행 ───
              // 메인 = 워드마크 + 아이콘 3개 / 기록 모드 = 뒤로 + 제목
              if (isRecordMode)
                Row(
                  children: [
                    _HeaderIconButton(
                      icon: Icons.arrow_back_rounded,
                      onTap: () => context.canPop()
                          ? context.pop()
                          : context.go('/shell/home'),
                    ),
                    const SizedBox(width: AppSpace.xs),
                    const Text(
                      '지난 기록',
                      style: TextStyle(
                        color: AppColor.ink,
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.4,
                      ),
                    ),
                  ],
                )
              else
                Row(
                  children: [
                    const _Wordmark(),
                    const Spacer(),
                    _HeaderIconButton(
                      icon: Icons.calendar_today_rounded,
                      onTap: () => context.push('/shell/home/calendar'),
                    ),
                    const SizedBox(width: AppSpace.sm),
                    _HeaderIconButton(
                      icon: Icons.notifications_rounded,
                      onTap: () =>
                          context.push('/shell/home/notifications'),
                    ),
                    const SizedBox(width: AppSpace.sm),
                    _HeaderIconButton(
                      icon: Icons.person_rounded,
                      onTap: () => context.go('/shell/settings'),
                    ),
                  ],
                ),

              const SizedBox(height: AppSpace.lg),

              // ─── 메인 = 날짜 라벨 + 이번 주 strip ───
              if (!isRecordMode) ...[
                const SizedBox(height: AppSpace.md),
                // 선택 날짜 라벨 + (과거면) 오늘로 버튼
                Row(
                  children: [
                    Icon(
                      isToday
                          ? Icons.today_rounded
                          : Icons.event_note_rounded,
                      color: AppColor.ink.withOpacity(0.7), size: 16,
                    ),
                    const SizedBox(width: 5),
                    Text(
                      '${selectedDate.month}월 ${selectedDate.day}일'
                      ' ${weekdayLabels[selectedDate.weekday - 1]}요일',
                      style: const TextStyle(
                        color: AppColor.ink,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(width: 6),
                    // 오늘 = 검정 '오늘' 칩 / 과거 = 탭하면 오늘로 가는 칩
                    if (isToday)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 7, vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: AppColor.ink,
                          borderRadius:
                              BorderRadius.circular(AppRadius.full),
                        ),
                        child: const Text(
                          '오늘',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      )
                    else
                      _TodayButton(onTap: onGoToday),
                  ],
                ),
                const SizedBox(height: AppSpace.md),
                // 이번 주 strip — 날짜 탭하면 그 자리에서 본문 교체
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
                Row(
                  children: [
                    for (int i = 0; i < 7; i++)
                      Expanded(
                        child: _DateBubble(
                          date: days[i],
                          selected: _isSameDay(days[i], selectedDate),
                          isToday: _isSameDay(days[i], today),
                          isFuture: days[i].isAfter(today),
                          onTap: () => onSelectDate(days[i]),
                        ),
                      ),
                  ],
                ),
              ],

              // ─── 기록 모드 = 주 이동 + 날짜 strip ───
              if (isRecordMode) ...[
                const SizedBox(height: AppSpace.lg),
                Row(
                  children: [
                    _WeekArrow(
                      icon: Icons.chevron_left_rounded,
                      onTap: () => onShiftWeek(-1),
                    ),
                    const SizedBox(width: 2),
                    RichText(
                      text: TextSpan(
                        style: const TextStyle(
                          fontFamily: 'Pretendard',
                          color: AppColor.ink,
                          fontSize: 15,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.3,
                        ),
                        children: [
                          TextSpan(
                            text: '${selectedDate.month}월 '
                                '${selectedDate.day}일',
                          ),
                          TextSpan(
                            text: isToday
                                ? '  ·  오늘'
                                : '  (${weekdayLabels[selectedDate.weekday - 1]})',
                            style: TextStyle(
                              color: isToday
                                  ? AppColor.brandDeep
                                  : AppColor.ink.withOpacity(0.55),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 2),
                    _WeekArrow(
                      icon: Icons.chevron_right_rounded,
                      onTap: focusedMonday.isBefore(_mondayOfToday(today))
                          ? () => onShiftWeek(1)
                          : null,
                    ),
                    const Spacer(),
                    // 기록 모드에서 오늘이면 '오늘로'(메인 복귀) 버튼
                    if (!isToday)
                      _TodayButton(onTap: onGoToday),
                  ],
                ),
                const SizedBox(height: AppSpace.md),
                // 요일 strip
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
                // 날짜 strip
                Row(
                  children: [
                    for (int i = 0; i < 7; i++)
                      Expanded(
                        child: _DateBubble(
                          date: days[i],
                          selected: _isSameDay(days[i], selectedDate),
                          isToday: _isSameDay(days[i], today),
                          isFuture: days[i].isAfter(today),
                          onTap: () => onSelectDate(days[i]),
                        ),
                      ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  static DateTime _mondayOfToday(DateTime today) => DateTime(
        today.year, today.month, today.day,
      ).subtract(Duration(days: today.weekday - 1));
}

// 주 이동 화살표 — null onTap 이면 비활성(흐림)
class _WeekArrow extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;
  const _WeekArrow({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null;
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: 28, height: 28,
        child: Icon(
          icon,
          size: 22,
          color: AppColor.ink.withOpacity(enabled ? 0.85 : 0.25),
        ),
      ),
    );
  }
}

// '오늘로' 버튼
class _TodayButton extends StatelessWidget {
  final VoidCallback onTap;
  const _TodayButton({super.key, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: AppSpace.md, vertical: 6),
        decoration: BoxDecoration(
          color: AppColor.ink,
          borderRadius: BorderRadius.circular(AppRadius.full),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: const [
            Icon(Icons.today_rounded, color: Colors.white, size: 13),
            SizedBox(width: 4),
            Text(
              '오늘로',
              style: TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }
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

// 날짜 칸 — 탭으로 선택. 선택 = 흰 원, 오늘 = 점 표시, 미래 = 흐림.
class _DateBubble extends StatelessWidget {
  final DateTime date;
  final bool selected;
  final bool isToday;
  final bool isFuture;
  final VoidCallback onTap;
  const _DateBubble({
    required this.date,
    required this.selected,
    required this.isToday,
    required this.isFuture,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: isFuture ? null : onTap,
      behavior: HitTestBehavior.opaque,
      child: Center(
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          width: 38, height: 38,
          decoration: BoxDecoration(
            color: selected ? AppColor.surface : Colors.transparent,
            shape: BoxShape.circle,
            boxShadow: selected
                ? [
                    BoxShadow(
                      color: AppColor.ink.withOpacity(0.10),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          alignment: Alignment.center,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '${date.day}',
                style: AppText.bodyLg.copyWith(
                  color: AppColor.ink.withOpacity(isFuture ? 0.3 : 1.0),
                  fontWeight:
                      selected ? FontWeight.w800 : FontWeight.w600,
                  fontSize: 15,
                ),
              ),
              // 오늘 표시 — 선택 안 됐을 때만 작은 점
              if (isToday && !selected)
                Container(
                  width: 4, height: 4,
                  margin: const EdgeInsets.only(top: 1),
                  decoration: const BoxDecoration(
                    color: AppColor.brandDeep,
                    shape: BoxShape.circle,
                  ),
                ),
            ],
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
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('오늘의 분석', style: AppText.subtitle),
              Pressable(
                onTap: () => context.push('/shell/home/analysis-result?mode=supplement'),
                child: Text(
                  '전체 보기 ›',
                  style: AppText.caption.copyWith(
                    color: AppColor.inkTertiary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpace.sm),
        SizedBox(
          height: 110,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(width: AppSpace.sm),
            itemBuilder: (ctx, i) => Pressable(
              onTap: () => context.push('/shell/home/analysis-result?mode=supplement'),
              child: _OutputCard(spec: items[i]),
            ),
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
              Pressable(
                onTap: () => context.push('/shell/home/calendar'),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '2/4 완료',
                      style: AppText.caption.copyWith(
                        color: AppColor.brandDeep,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Icon(Icons.chevron_right_rounded,
                        color: AppColor.inkTertiary, size: 18),
                  ],
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
          _RecentRow(
            emoji: '💊', title: '오메가-3 1200mg',
            subtitle: '어제 · 부족 영양소 보완', mode: 'supplement',
          ),
          const SizedBox(height: AppSpace.md),
          _RecentRow(
            emoji: '🥗', title: '점심 식단',
            subtitle: '오늘 12:30 · 80점', mode: 'meal',
          ),
          const SizedBox(height: AppSpace.md),
          _RecentRow(
            emoji: '💊', title: '비타민 D 1000IU',
            subtitle: '3일 전 · 권장량 충족', mode: 'supplement',
          ),
        ],
      ),
    );
  }
}

class _RecentRow extends StatelessWidget {
  final String emoji;
  final String title;
  final String subtitle;
  final String mode;
  const _RecentRow({
    required this.emoji,
    required this.title,
    required this.subtitle,
    required this.mode,
  });

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: () => context.push('/shell/home/analysis-result?mode=$mode'),
      child: Row(
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
      ),
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
