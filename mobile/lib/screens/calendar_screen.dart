// screens/calendar_screen.dart — 월간 캘린더 (LADS v2)
//
// 디자인:
//   - 상단 흰 헤더 (뒤로 + 월 표시 + 좌우 화살표)
//   - 본문: 7열 그리드 (일~토)
//     · 분석 기록 있는 날 → 작은 brand 점
//     · 오늘 → brand 원 강조
//   - 하단: 선택한 날짜 요약 카드 (mock)

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../utils/design_tokens_v2.dart';

class CalendarScreen extends StatefulWidget {
  const CalendarScreen({super.key});

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  late DateTime _focusedMonth;
  late DateTime _selected;

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _focusedMonth = DateTime(now.year, now.month);
    _selected = now;
  }

  void _prevMonth() {
    setState(() {
      _focusedMonth = DateTime(_focusedMonth.year, _focusedMonth.month - 1);
    });
  }

  void _nextMonth() {
    setState(() {
      _focusedMonth = DateTime(_focusedMonth.year, _focusedMonth.month + 1);
    });
  }

  // mock — 분석 기록 있는 날 (이번 달 임의 날짜들)
  Set<int> get _recordedDays => {3, 7, 8, 12, 15, 16, 19, 20};

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.section,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _Header(),
            _MonthSwitcher(
              month: _focusedMonth,
              onPrev: _prevMonth,
              onNext: _nextMonth,
            ),
            const SizedBox(height: AppSpace.sm),
            _CalendarGrid(
              focusedMonth: _focusedMonth,
              selected: _selected,
              recordedDays: _recordedDays,
              onTap: (d) {
                setState(() => _selected = d);
                // 미래가 아니면 그 날 기록 페이지로 이동
                final now = DateTime.now();
                final today = DateTime(now.year, now.month, now.day);
                if (!d.isAfter(today)) {
                  context.push(
                    '/shell/home/record'
                    '?date=${d.toIso8601String().substring(0, 10)}',
                  );
                }
              },
            ),
            const SizedBox(height: AppSpace.lg),
            Expanded(child: _DaySummary(date: _selected)),
          ],
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColor.section,
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.sm, AppSpace.page, AppSpace.sm,
      ),
      child: Row(
        children: [
          GestureDetector(
            onTap: () => context.canPop()
                ? context.pop()
                : context.go('/shell/home'),
            child: Container(
              width: 40, height: 40,
              alignment: Alignment.center,
              child: const Icon(Icons.arrow_back_rounded,
                  color: AppColor.ink, size: 22),
            ),
          ),
          const Spacer(),
          const Text(
            '캘린더',
            style: TextStyle(
              color: AppColor.ink,
              fontSize: 16,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.3,
            ),
          ),
          const Spacer(),
          const SizedBox(width: 40, height: 40),
        ],
      ),
    );
  }
}

class _MonthSwitcher extends StatelessWidget {
  final DateTime month;
  final VoidCallback onPrev;
  final VoidCallback onNext;
  const _MonthSwitcher({
    required this.month,
    required this.onPrev,
    required this.onNext,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.page, vertical: AppSpace.sm,
      ),
      child: Row(
        children: [
          GestureDetector(
            onTap: onPrev,
            child: Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                color: AppColor.surface,
                shape: BoxShape.circle,
                border: Border.all(color: AppColor.border),
              ),
              alignment: Alignment.center,
              child: const Icon(Icons.chevron_left_rounded,
                  color: AppColor.ink, size: 22),
            ),
          ),
          const Spacer(),
          Text(
            '${month.year}년 ${month.month}월',
            style: const TextStyle(
              color: AppColor.ink,
              fontSize: 18,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.4,
            ),
          ),
          const Spacer(),
          GestureDetector(
            onTap: onNext,
            child: Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                color: AppColor.surface,
                shape: BoxShape.circle,
                border: Border.all(color: AppColor.border),
              ),
              alignment: Alignment.center,
              child: const Icon(Icons.chevron_right_rounded,
                  color: AppColor.ink, size: 22),
            ),
          ),
        ],
      ),
    );
  }
}

class _CalendarGrid extends StatelessWidget {
  final DateTime focusedMonth;
  final DateTime selected;
  final Set<int> recordedDays;
  final ValueChanged<DateTime> onTap;
  const _CalendarGrid({
    required this.focusedMonth,
    required this.selected,
    required this.recordedDays,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final firstDay = DateTime(focusedMonth.year, focusedMonth.month, 1);
    final daysInMonth = DateTime(
      focusedMonth.year, focusedMonth.month + 1, 0,
    ).day;
    // 일요일을 0으로 (Sun=7 in DateTime, % 7 처리)
    final leadingBlanks = firstDay.weekday % 7;
    const headers = ['일', '월', '화', '수', '목', '금', '토'];
    final today = DateTime.now();

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: AppSpace.page),
      padding: const EdgeInsets.fromLTRB(
        AppSpace.sm, AppSpace.md, AppSpace.sm, AppSpace.md,
      ),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.14),
            blurRadius: 12,
            offset: Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            children: [
              for (int i = 0; i < 7; i++)
                Expanded(
                  child: Center(
                    child: Text(
                      headers[i],
                      style: TextStyle(
                        color: i == 0
                            ? const Color(0xFFFF6B6B)
                            : AppColor.inkTertiary,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: AppSpace.sm),
          // 6주 (최대) — 빈 칸 + 실제 날짜
          ..._buildWeeks(
            leadingBlanks: leadingBlanks,
            daysInMonth: daysInMonth,
            month: focusedMonth,
            today: today,
            selected: selected,
            onTap: onTap,
          ),
        ],
      ),
    );
  }

  List<Widget> _buildWeeks({
    required int leadingBlanks,
    required int daysInMonth,
    required DateTime month,
    required DateTime today,
    required DateTime selected,
    required ValueChanged<DateTime> onTap,
  }) {
    final cells = <Widget>[];
    for (int i = 0; i < leadingBlanks; i++) {
      cells.add(const Expanded(child: SizedBox(height: 44)));
    }
    for (int d = 1; d <= daysInMonth; d++) {
      final date = DateTime(month.year, month.month, d);
      final isToday = _isSame(date, today);
      final isSelected = _isSame(date, selected);
      final hasRecord = recordedDays.contains(d);
      cells.add(Expanded(
        child: GestureDetector(
          onTap: () => onTap(date),
          behavior: HitTestBehavior.opaque,
          child: SizedBox(
            height: 44,
            child: Center(
              child: Container(
                width: 36, height: 36,
                decoration: BoxDecoration(
                  color: isSelected
                      ? AppColor.brand
                      : (isToday
                          ? AppColor.brandSoft
                          : Colors.transparent),
                  shape: BoxShape.circle,
                ),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    Center(
                      child: Text(
                        '$d',
                        style: TextStyle(
                          color: AppColor.ink,
                          fontSize: 13.5,
                          fontWeight: (isSelected || isToday)
                              ? FontWeight.w800
                              : FontWeight.w600,
                        ),
                      ),
                    ),
                    if (hasRecord && !isSelected)
                      Positioned(
                        bottom: 4,
                        child: Container(
                          width: 4, height: 4,
                          decoration: const BoxDecoration(
                            color: AppColor.brand,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ));
    }
    // 7개씩 묶기
    final rows = <Widget>[];
    for (int i = 0; i < cells.length; i += 7) {
      final chunk = cells.sublist(
        i, (i + 7 <= cells.length) ? i + 7 : cells.length,
      );
      while (chunk.length < 7) {
        chunk.add(const Expanded(child: SizedBox(height: 44)));
      }
      rows.add(Row(children: chunk));
    }
    return rows;
  }

  static bool _isSame(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;
}

class _DaySummary extends StatelessWidget {
  final DateTime date;
  const _DaySummary({required this.date});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: AppSpace.page),
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.14),
            blurRadius: 12,
            offset: Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${date.month}월 ${date.day}일',
            style: const TextStyle(
              color: AppColor.ink,
              fontSize: 16,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: AppSpace.md),
          _Row(
            icon: Icons.workspace_premium_rounded,
            color: AppColor.brand,
            label: '식단 점수',
            value: '80점',
          ),
          const SizedBox(height: AppSpace.sm),
          _Row(
            icon: Icons.medication_rounded,
            color: const Color(0xFF22B07D),
            label: '복약',
            value: '4/4 완료',
          ),
          const SizedBox(height: AppSpace.sm),
          _Row(
            icon: Icons.restaurant_rounded,
            color: const Color(0xFFFF9500),
            label: '식단 분석',
            value: '3건',
          ),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String label;
  final String value;
  const _Row({
    required this.icon,
    required this.color,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 32, height: 32,
          decoration: BoxDecoration(
            color: color.withOpacity(0.14),
            borderRadius: BorderRadius.circular(AppRadius.sm - 2),
          ),
          alignment: Alignment.center,
          child: Icon(icon, color: color, size: 16),
        ),
        const SizedBox(width: AppSpace.md),
        Expanded(
          child: Text(
            label,
            style: const TextStyle(
              color: AppColor.inkSecondary,
              fontSize: 13.5,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            color: AppColor.ink,
            fontSize: 14,
            fontWeight: FontWeight.w800,
          ),
        ),
      ],
    );
  }
}
