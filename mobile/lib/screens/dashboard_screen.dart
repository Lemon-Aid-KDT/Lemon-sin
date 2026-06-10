// screens/dashboard_screen.dart — 홈 (메인 화면)
//
// 디자인: Pillyze 시안 기반 LADS 톤 변환 (비주얼 보존, 데이터는 실연동).
//   - 상단: brand 노랑 헤더 (로고 + 우측 아이콘 3개 + 캘린더 weekday strip)
//   - 본문: 흰 배경 카드들 — 모두 실데이터 (P0 배치 A)
//
// 데이터:
//   - 건강 점수: dashboard summary 의 health_score (ready/not_ready)
//   - kcal/매크로: 당일 meals nutrition_summary 합산
//   - 주간 스트립: 최근 7일 meals 기록 여부로 점 표시
//   - 상호작용: 영양제 영향도 preview 3상태
//   - 오늘의 분석: health_score.message
//   - 식단 관리: 당일 끼니별 / 영양제 관리: 등록 영양제 체크리스트
//
// 연산은 모두 백엔드. 모바일은 표시·합산만.

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../app_controller.dart';
import '../features/dashboard/home_models.dart';
import '../features/supplements/supplement_models.dart';
import '../shared/widgets/status_state_view.dart';
import '../utils/design_tokens_v2.dart';
import '../widgets/common/pressable.dart';
import '../widgets/common/staggered_entrance.dart';
import '../widgets/dashboard/health_hero_card.dart';

class DashboardScreen extends StatefulWidget {
  // recordDate 가 null 이면 메인(오늘 고정).
  // 값이 있으면 '과거 기록 조회' 모드 — 풀스크린 별도 페이지.
  final DateTime? recordDate;

  /// 홈 데이터(점수·식단·영양제·상호작용)를 제공하는 앱 컨트롤러.
  final AppController controller;

  const DashboardScreen({required this.controller, super.key, this.recordDate});

  bool get isRecordMode => recordDate != null;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  // 선택된 날짜 — 메인이면 항상 오늘, 기록 모드면 recordDate 부터.
  late DateTime _selectedDate;
  // 헤더 strip 이 보여주는 주 (그 주의 월요일)
  late DateTime _focusedMonday;
  // 영양제 체크 토글 — 세션 메모리. // TODO(persist): SharedPreferences 연동.
  final Set<String> _checkedSupplementIds = <String>{};

  bool get _isRecordMode => widget.isRecordMode;

  AppController get _controller => widget.controller;

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

  // 카메라 딥링크 — 끼니/영양제 촬영
  void _openCamera(String mode) {
    context.go('/shell/camera?mode=$mode');
  }

  void _toggleSupplement(String id) {
    setState(() {
      if (_checkedSupplementIds.contains(id)) {
        _checkedSupplementIds.remove(id);
      } else {
        _checkedSupplementIds.add(id);
      }
    });
  }

  // 당일 meals nutrition_summary 합산
  HomeMealNutrition _dayTotals(List<HomeMeal> meals) {
    HomeMealNutrition total = HomeMealNutrition.zero;
    for (final HomeMeal meal in meals) {
      total = total + meal.nutrition;
    }
    return total;
  }

  // 최근 7일(헤더 strip 표시 주) 기록 점
  Set<String> _recordDots() {
    final Set<String> dots = <String>{};
    for (final HomeMeal meal in _controller.recentMeals.results) {
      final DateTime? eatenAt = meal.eatenAt;
      if (eatenAt == null) continue;
      final DateTime local = eatenAt.toLocal();
      dots.add('${local.year}-${local.month}-${local.day}');
    }
    return dots;
  }

  // 본문 — 날짜별로 다시 그려짐 (key 로 AnimatedSwitcher 전환)
  Widget _buildBody({Key? key}) {
    final List<HomeMeal> dayMeals = _controller.mealsForDay(_selectedDate);
    final HomeMealNutrition totals = _dayTotals(dayMeals);
    final DashboardHealthScore score = _controller.healthScore;

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
              date: _selectedDate,
              isToday: _isToday,
              scoreReady: score.isReady,
              healthScore: score.score ?? 0,
              scoreLabelText: score.labelText,
              consumedKcal: totals.kcal.round(),
              targetKcal: null,
              macrosTotalsOnly: true,
              carbG: totals.carbG.round(),
              proteinG: totals.proteinG.round(),
              fatG: totals.fatG.round(),
              onPrevDay: () =>
                  _selectDate(_selectedDate.subtract(const Duration(days: 1))),
              onNextDay: _isToday
                  ? null
                  : () =>
                        _selectDate(_selectedDate.add(const Duration(days: 1))),
              onTapDate: () => context.push('/shell/home/calendar'),
              onTapScore: score.isReady
                  ? () => context.go('/shell/score')
                  : () => _openCamera('meal'),
              onTapDetail: () =>
                  context.push('/shell/home/analysis-result?mode=meal'),
            ),
            _TodayAnalysisCard(score: score),
            _InteractionCard(
              preview: _controller.supplementImpactPreview,
              hasSupplements:
                  _controller.homeSupplements.results.isNotEmpty,
              failed: _controller.homeImpactFailed,
            ),
            _MealManagementCard(
              meals: dayMeals,
              failed: _controller.homeMealsFailed,
              onRecord: () => _openCamera('meal'),
            ),
            _SupplementChecklistCard(
              supplements: _controller.homeSupplements.results,
              checkedIds: _checkedSupplementIds,
              failed: _controller.homeSupplementsFailed,
              onToggle: _toggleSupplement,
              onAdd: () => _openCamera('supplement'),
            ),
            const _MedicalDisclaimer(),
          ],
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
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
                recordDots: _recordDots(),
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
                      child: RefreshIndicator(
                        onRefresh: _controller.refreshDashboard,
                        color: AppColor.brand,
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
              ),
            ],
          ),
        );
      },
    );
  }
}

// ═══════════════════════════════════════════
// 상단 brand 헤더 (Pillyze 톤)
//   - status bar 부터 색 채움
//   - 로고 + 우측 아이콘 3개
//   - weekday strip + 날짜 (오늘 = 흰 원 강조, 기록 점)
// ═══════════════════════════════════════════
class _BrandHeader extends StatelessWidget {
  final DateTime selectedDate;
  final DateTime focusedMonday;
  final bool isToday;
  final bool isRecordMode; // 과거 기록 페이지면 true
  final Set<String> recordDots; // 'y-m-d' 기록 있는 날짜 키
  final ValueChanged<DateTime> onSelectDate;
  final ValueChanged<int> onShiftWeek; // -1 이전 주 / +1 다음 주
  final VoidCallback onGoToday;

  const _BrandHeader({
    required this.selectedDate,
    required this.focusedMonday,
    required this.isToday,
    required this.isRecordMode,
    required this.recordDots,
    required this.onSelectDate,
    required this.onShiftWeek,
    required this.onGoToday,
  });

  static bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  static String _dotKey(DateTime d) => '${d.year}-${d.month}-${d.day}';

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
            AppSpace.page,
            AppSpace.lg,
            AppSpace.page,
            AppSpace.xl + AppSpace.xl,
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
                        letterSpacing: 0,
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
                      onTap: () => context.push('/shell/home/notifications'),
                    ),
                    const SizedBox(width: AppSpace.sm),
                    _HeaderIconButton(
                      icon: Icons.person_rounded,
                      onTap: () => context.go('/shell/settings'),
                    ),
                  ],
                ),

              // 메인 = 노란 헤더는 워드마크 + 아이콘만 (심플).
              // 날짜 네비는 히어로 카드 맨 위로 이동.

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
                          letterSpacing: 0,
                        ),
                        children: [
                          TextSpan(
                            text:
                                '${selectedDate.month}월 '
                                '${selectedDate.day}일',
                          ),
                          TextSpan(
                            text: isToday
                                ? '  ·  오늘'
                                : '  (${weekdayLabels[selectedDate.weekday - 1]})',
                            style: TextStyle(
                              color: isToday
                                  ? AppColor.brandDeep
                                  : AppColor.ink.withValues(alpha: 0.55),
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
                    if (!isToday) _TodayButton(onTap: onGoToday),
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
                              color: AppColor.ink.withValues(alpha: 0.75),
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
                          hasRecord: recordDots.contains(_dotKey(days[i])),
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
    today.year,
    today.month,
    today.day,
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
        width: 28,
        height: 28,
        child: Icon(
          icon,
          size: 22,
          color: AppColor.ink.withValues(alpha: enabled ? 0.85 : 0.25),
        ),
      ),
    );
  }
}

// '오늘로' 버튼
class _TodayButton extends StatelessWidget {
  final VoidCallback onTap;
  const _TodayButton({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpace.md,
          vertical: 6,
        ),
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
      letterSpacing: 0,
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
            width: 9,
            height: 9,
            decoration: BoxDecoration(
              color: AppColor.surface,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: AppColor.ink.withValues(alpha: 0.10),
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
        width: 32,
        height: 32,
        child: Icon(icon, color: AppColor.ink, size: 22),
      ),
    );
  }
}

// 날짜 칸 — 탭으로 선택. 선택 = 흰 원, 오늘 = 점 표시, 미래 = 흐림, 기록 = 아래 점.
class _DateBubble extends StatelessWidget {
  final DateTime date;
  final bool selected;
  final bool isToday;
  final bool isFuture;
  final bool hasRecord;
  final VoidCallback onTap;
  const _DateBubble({
    required this.date,
    required this.selected,
    required this.isToday,
    required this.isFuture,
    required this.hasRecord,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    // 기록 점: 선택 안 됐고, 오늘 표시 점과 겹치지 않을 때만 (오늘은 brandDeep 점 우선).
    final bool showRecordDot = hasRecord && !selected && !isToday;
    return GestureDetector(
      onTap: isFuture ? null : onTap,
      behavior: HitTestBehavior.opaque,
      child: Center(
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          width: 38,
          height: 38,
          decoration: BoxDecoration(
            color: selected ? AppColor.surface : Colors.transparent,
            shape: BoxShape.circle,
            boxShadow: selected
                ? [
                    BoxShadow(
                      color: AppColor.ink.withValues(alpha: 0.10),
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
                  color: AppColor.ink.withValues(alpha: isFuture ? 0.3 : 1.0),
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                  fontSize: 15,
                ),
              ),
              // 오늘 표시 — 선택 안 됐을 때만 작은 점
              if (isToday && !selected)
                Container(
                  width: 4,
                  height: 4,
                  margin: const EdgeInsets.only(top: 1),
                  decoration: const BoxDecoration(
                    color: AppColor.brandDeep,
                    shape: BoxShape.circle,
                  ),
                )
              // 기록 점 — 기록 있는 다른 날
              else if (showRecordDot)
                Container(
                  width: 4,
                  height: 4,
                  margin: const EdgeInsets.only(top: 1),
                  decoration: BoxDecoration(
                    color: AppColor.ink.withValues(alpha: 0.45),
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

// 카드 헤더 (제목)
class _CardHeader extends StatelessWidget {
  final String title;
  const _CardHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [Text(title, style: AppText.subtitle)],
    );
  }
}

// ═══════════════════════════════════════════
// '오늘의 분석' — AI 요약 카드 (health_score.message 재사용)
// 별도 daily-coaching 호출은 배치 C에서.
// ═══════════════════════════════════════════
class _TodayAnalysisCard extends StatelessWidget {
  final DashboardHealthScore score;
  const _TodayAnalysisCard({required this.score});

  @override
  Widget build(BuildContext context) {
    final String? message = score.message;
    final bool hasMessage = message != null && message.trim().isNotEmpty;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside + 2),
      decoration: _mainCardDeco(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: AppColor.brandSoft,
                  borderRadius: BorderRadius.circular(AppRadius.sm - 2),
                ),
                alignment: Alignment.center,
                child: Icon(
                  Icons.auto_awesome_rounded,
                  size: 18,
                  color: AppColor.brandDeep,
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Text('오늘의 분석', style: AppText.subtitle),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          Text(
            hasMessage
                ? message.trim()
                : '오늘 끼니와 영양제를 기록하면 맞춤 코멘트를 보여드려요.',
            style: AppText.body.copyWith(
              color: AppColor.inkSecondary,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 상호작용 카드 (3상태)
//   ① 위험 N건 → '주의 N건' + user_message 행들
//   ② 안심 → 영양제 있고 위험 없음
//   ③ 약 미등록 → 영양제 없음 (복약 라우트는 P1)
// 의사·약사 상담 각주 유지.
// ═══════════════════════════════════════════
class _InteractionCard extends StatelessWidget {
  final SupplementImpactPreviewResponse? preview;
  final bool hasSupplements;
  final bool failed;
  const _InteractionCard({
    required this.preview,
    required this.hasSupplements,
    required this.failed,
  });

  @override
  Widget build(BuildContext context) {
    final List<SupplementNutritionInsight> risks =
        preview?.excessOrDuplicateRisks ?? const <SupplementNutritionInsight>[];

    final Widget body;
    if (failed && preview == null) {
      body = _statusLine(
        icon: Icons.cloud_off_rounded,
        color: AppColor.inkTertiary,
        title: '상호작용 정보를 불러오지 못했어요',
        subtitle: '잠시 후 당겨서 새로고침 해주세요.',
      );
    } else if (!hasSupplements) {
      // ③ 약/영양제 미등록 — 복약 라우트는 P1 이라 안내만.
      body = _statusLine(
        icon: Icons.medication_outlined,
        color: AppColor.inkTertiary,
        title: '등록된 영양제가 없어요',
        subtitle: '영양제를 등록하면 중복·상한 확인을 도와드려요.',
      );
    } else if (risks.isNotEmpty) {
      // ① 위험 N건
      body = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _statusLine(
            icon: Icons.warning_amber_rounded,
            color: AppColor.warning,
            title: '확인이 필요해요 · ${risks.length}건',
            subtitle: preview?.safeUserMessage,
          ),
          const SizedBox(height: AppSpace.sm),
          for (final SupplementNutritionInsight risk in risks.take(3))
            Padding(
              padding: const EdgeInsets.only(top: AppSpace.xs),
              child: _RiskRow(risk: risk),
            ),
        ],
      );
    } else {
      // ② 안심
      body = _statusLine(
        icon: Icons.check_circle_outline_rounded,
        color: AppColor.success,
        title: '안심하고 드셔도 돼요',
        subtitle: preview?.safeUserMessage ?? '지금 등록된 영양제에서 중복·상한 신호는 없어요.',
      );
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside + 2),
      decoration: _mainCardDeco(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _CardHeader(title: '영양제 상호작용'),
          const SizedBox(height: AppSpace.md),
          body,
          const SizedBox(height: AppSpace.md),
          Text(
            '확인이 필요하면 의사·약사와 상담해주세요.',
            style: AppText.micro.copyWith(color: AppColor.inkTertiary),
          ),
        ],
      ),
    );
  }

  Widget _statusLine({
    required IconData icon,
    required Color color,
    required String title,
    String? subtitle,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(AppRadius.sm - 2),
          ),
          alignment: Alignment.center,
          child: Icon(icon, size: 18, color: color),
        ),
        const SizedBox(width: AppSpace.sm),
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
              if (subtitle != null && subtitle.trim().isNotEmpty) ...[
                const SizedBox(height: 2),
                Text(
                  subtitle.trim(),
                  style: AppText.caption.copyWith(color: AppColor.inkSecondary),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _RiskRow extends StatelessWidget {
  final SupplementNutritionInsight risk;
  const _RiskRow({required this.risk});

  @override
  Widget build(BuildContext context) {
    final String name = (risk.nutrientName?.trim().isNotEmpty ?? false)
        ? risk.nutrientName!.trim()
        : risk.nutrientCode.trim();
    return Container(
      padding: const EdgeInsets.all(AppSpace.sm + 2),
      decoration: BoxDecoration(
        color: AppColor.sunken,
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            margin: const EdgeInsets.only(top: 5),
            width: 6,
            height: 6,
            decoration: const BoxDecoration(
              color: AppColor.warning,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: AppSpace.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$name · ${risk.actionLabel}',
                  style: AppText.caption.copyWith(
                    color: AppColor.ink,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 1),
                Text(
                  risk.userMessage,
                  style: AppText.micro.copyWith(color: AppColor.inkSecondary),
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
// 식단 관리 — 당일 끼니별 (아침/점심/저녁/간식)
//   기록되면 메뉴명+kcal, 미기록이면 '아직 기록 전' + [기록하기].
// ═══════════════════════════════════════════
class _MealManagementCard extends StatelessWidget {
  final List<HomeMeal> meals;
  final bool failed;
  final VoidCallback onRecord;
  const _MealManagementCard({
    required this.meals,
    required this.failed,
    required this.onRecord,
  });

  static const List<MapEntry<String, String>> _slots = <MapEntry<String, String>>[
    MapEntry('breakfast', '아침'),
    MapEntry('lunch', '점심'),
    MapEntry('dinner', '저녁'),
    MapEntry('snack', '간식'),
  ];

  HomeMeal? _firstFor(String mealType) {
    for (final HomeMeal meal in meals) {
      if (meal.mealType == mealType) return meal;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside + 2),
      decoration: _mainCardDeco(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _CardHeader(title: '식단 관리'),
          const SizedBox(height: AppSpace.md),
          if (failed)
            StatusStateView(
              variant: StatusStateVariant.syncFailed,
              onPrimary: onRecord,
            )
          else
            for (int i = 0; i < _slots.length; i++) ...[
              _MealSlotRow(
                label: _slots[i].value,
                meal: _firstFor(_slots[i].key),
                onRecord: onRecord,
              ),
              if (i != _slots.length - 1)
                Divider(color: AppColor.border, height: AppSpace.lg),
            ],
        ],
      ),
    );
  }
}

class _MealSlotRow extends StatelessWidget {
  final String label;
  final HomeMeal? meal;
  final VoidCallback onRecord;
  const _MealSlotRow({
    required this.label,
    required this.meal,
    required this.onRecord,
  });

  @override
  Widget build(BuildContext context) {
    final HomeMeal? recorded = meal;
    return Row(
      children: [
        SizedBox(
          width: 44,
          child: Text(
            label,
            style: AppText.body.copyWith(
              color: AppColor.ink,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(width: AppSpace.sm),
        Expanded(
          child: recorded == null
              ? Text(
                  '아직 기록 전',
                  style: AppText.caption.copyWith(color: AppColor.inkTertiary),
                )
              : Text(
                  recorded.primaryName ?? '기록됨',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppText.body.copyWith(
                    color: AppColor.ink,
                    fontWeight: FontWeight.w600,
                  ),
                ),
        ),
        const SizedBox(width: AppSpace.sm),
        if (recorded == null)
          Pressable(
            onTap: onRecord,
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpace.md,
                vertical: 6,
              ),
              decoration: BoxDecoration(
                color: AppColor.brandSoft,
                borderRadius: BorderRadius.circular(AppRadius.full),
              ),
              child: Text(
                '기록하기',
                style: AppText.caption.copyWith(
                  color: AppColor.brandDeep,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          )
        else
          Text(
            '${recorded.nutrition.kcal.round()} kcal',
            style: AppText.caption.copyWith(
              color: AppColor.inkSecondary,
              fontWeight: FontWeight.w700,
            ),
          ),
      ],
    );
  }
}

// ═══════════════════════════════════════════
// 영양제 관리 — 등록 영양제 체크리스트
//   이름 + intake_schedule 요약 + 체크 토글 (세션 메모리).
// ═══════════════════════════════════════════
class _SupplementChecklistCard extends StatelessWidget {
  final List<HomeSupplement> supplements;
  final Set<String> checkedIds;
  final bool failed;
  final ValueChanged<String> onToggle;
  final VoidCallback onAdd;
  const _SupplementChecklistCard({
    required this.supplements,
    required this.checkedIds,
    required this.failed,
    required this.onToggle,
    required this.onAdd,
  });

  @override
  Widget build(BuildContext context) {
    final int total = supplements.length;
    final int done = supplements
        .where((HomeSupplement item) => checkedIds.contains(item.id))
        .length;

    Widget body;
    if (failed && supplements.isEmpty) {
      body = StatusStateView(
        variant: StatusStateVariant.syncFailed,
        onPrimary: onAdd,
      );
    } else if (supplements.isEmpty) {
      body = StatusStateView(
        variant: StatusStateVariant.emptyNew,
        onPrimary: onAdd,
      );
    } else {
      body = Column(
        children: [
          for (int i = 0; i < supplements.length; i++) ...[
            _SupplementRow(
              supplement: supplements[i],
              checked: checkedIds.contains(supplements[i].id),
              onToggle: () => onToggle(supplements[i].id),
            ),
            if (i != supplements.length - 1)
              Divider(color: AppColor.border, height: AppSpace.lg),
          ],
        ],
      );
    }

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
              Text('영양제 관리', style: AppText.subtitle),
              if (total > 0)
                Text(
                  '$done/$total 완료',
                  style: AppText.caption.copyWith(
                    color: AppColor.brandDeep,
                    fontWeight: FontWeight.w700,
                  ),
                ),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          body,
        ],
      ),
    );
  }
}

class _SupplementRow extends StatelessWidget {
  final HomeSupplement supplement;
  final bool checked;
  final VoidCallback onToggle;
  const _SupplementRow({
    required this.supplement,
    required this.checked,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final String? scheduleText = supplement.schedule?.summary;
    return Pressable(
      onTap: onToggle,
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  supplement.displayName.isNotEmpty
                      ? supplement.displayName
                      : '이름 미상 영양제',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppText.body.copyWith(
                    color: checked ? AppColor.inkTertiary : AppColor.ink,
                    fontWeight: FontWeight.w600,
                    decoration: checked ? TextDecoration.lineThrough : null,
                  ),
                ),
                if (scheduleText != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    scheduleText,
                    style: AppText.caption.copyWith(
                      color: AppColor.inkTertiary,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: AppSpace.sm),
          // 체크 박스
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: checked ? AppColor.brand : const Color(0xFFE5E8EB),
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Icon(Icons.check_rounded, color: Colors.white, size: 16),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 의료 면책 (LADS §14)
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
              style: AppText.caption.copyWith(color: AppColor.ink, height: 1.5),
            ),
          ),
        ],
      ),
    );
  }
}
