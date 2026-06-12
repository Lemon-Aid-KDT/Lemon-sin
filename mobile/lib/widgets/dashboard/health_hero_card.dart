// widgets/dashboard/health_hero_card.dart — 메인 대시보드 히어로 카드
//
// 디자인: Figma node 48-2 구조를 LADS(Flat 2.0 + Soft UI) 로 변환.
//   - 흰 배경 카드 + soft shadow (LADS 기본)
//   - 포인트 색만 사용 — 게이지·탄단지·칼로리 강조에만 컬러, 나머지는 ink
//   - 상단: 시간대별 인사 + 테마 칩
//   - 건강 점수 + 칼로리
//   - 반원 게이지 위에 시간대별 레몬 마스코트
//   - 하단: 소모/잔여 칼로리 + 순탄수·단백질·지방
//
// 시간대별 캐릭터: MascotFor.timedRandom(DateTime.now()) — 시간 버킷마다 자동 변경

import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../features/dashboard/dashboard_models.dart';
import '../../shared/score_label_colors.dart';
import '../../utils/design_tokens_v2.dart';
import '../../utils/mascot_poses.dart';
import '../common/pressable.dart';

// 매크로 3색 — 포인트 컬러
const _kCarb = Color(0xFFFFB200); // 탄수화물 — 옐로
const _kProtein = Color(0xFF22B07D); // 단백질 — 그린
const _kFat = Color(0xFFFF6B6B); // 지방 — 레드

class HealthHeroCard extends StatefulWidget {
  /// Optional live backend summary kept for the existing dashboard contract.
  final DashboardSummary? summary;
  final int healthScore;
  // not_ready (점수 없음) 일 때 점수 카운트업/숫자 숨김.
  final bool scoreReady;
  // 점수 라벨(예: '좋아요') — 칩 표시. null 이면 미표시.
  final String? scoreLabelText;
  // 점수 등급 코드 — 라벨 색 매핑 전용 (오늘의 분석 링과 동일 매핑, 가이드 06 §2.4).
  final String? scoreLabel;
  final int consumedKcal;
  // 목표 kcal — 백엔드 미제공 시 null. null 이면 '/ 목표' 숨기고 '기록 합계' 표시.
  final int? targetKcal;
  final int burnedKcal;
  final int carbPct;
  final int proteinPct;
  final int fatPct;
  final int carbG, carbTargetG;
  final int proteinG, proteinTargetG;
  final int fatG, fatTargetG;
  // 매크로 막대를 '기록 합계' 모드로 표시 (목표 대비 X). 목표 하드코딩 금지.
  final bool macrosTotalsOnly;
  final VoidCallback? onTapScore;
  final VoidCallback? onTapDetail;
  // 날짜 네비게이션 — 카드 맨 위 캡슐
  final DateTime date;
  final bool isToday;
  final VoidCallback? onPrevDay;
  final VoidCallback? onNextDay; // null 이면 비활성 (미래)
  final VoidCallback? onTapDate; // 날짜 텍스트 탭 → 캘린더

  HealthHeroCard({
    super.key,
    this.summary,
    DateTime? date,
    this.isToday = true,
    this.onPrevDay,
    this.onNextDay,
    this.onTapDate,
    this.healthScore = 78,
    this.scoreReady = true,
    this.scoreLabelText,
    this.scoreLabel,
    this.consumedKcal = 600,
    this.targetKcal = 1500,
    this.burnedKcal = 200,
    this.carbPct = 46,
    this.proteinPct = 24,
    this.fatPct = 30,
    this.carbG = 78,
    this.carbTargetG = 170,
    this.proteinG = 44,
    this.proteinTargetG = 86,
    this.fatG = 17,
    this.fatTargetG = 40,
    this.macrosTotalsOnly = false,
    this.onTapScore,
    this.onTapDetail,
  }) : date = date ?? DateTime.now();

  @override
  State<HealthHeroCard> createState() => _HealthHeroCardState();
}

class _HealthHeroCardState extends State<HealthHeroCard>
    with SingleTickerProviderStateMixin {
  // 게이지 차오름 애니메이션
  late final AnimationController _gaugeCtl;
  late final Animation<double> _gauge;
  static const Duration _poseRefreshInterval = Duration(minutes: 5);
  // 테마 칩으로 캐릭터 포즈 순환 (확인용) — null 이면 시간대 자동
  int? _poseOverride;
  late DateTime _poseClock;
  Timer? _poseTimer;

  bool get _hasTarget => widget.targetKcal != null && widget.targetKcal! > 0;

  int get _remainKcal {
    final int? target = widget.targetKcal;
    if (target == null || target <= 0) return 0;
    return (target - widget.consumedKcal).clamp(0, target);
  }

  double get _kcalRatio {
    final int? target = widget.targetKcal;
    if (target == null || target <= 0) {
      // 목표 미제공 — 게이지는 은은하게 채워 시각만 유지 (수치 의미 없음).
      return 0.35;
    }
    return (widget.consumedKcal / target).clamp(0.0, 1.0);
  }

  @override
  void initState() {
    super.initState();
    _gaugeCtl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    );
    _gauge = CurvedAnimation(parent: _gaugeCtl, curve: Curves.easeOutQuart);
    _poseClock = DateTime.now();
    _poseTimer = Timer.periodic(_poseRefreshInterval, (_) {
      if (!mounted || _poseOverride != null) return;
      setState(() => _poseClock = DateTime.now());
    });
    // 진입 직후 살짝 지연 후 차오름
    Future.delayed(const Duration(milliseconds: 220), () {
      if (mounted) _gaugeCtl.forward();
    });
  }

  @override
  void dispose() {
    _poseTimer?.cancel();
    _gaugeCtl.dispose();
    super.dispose();
  }

  // 테마 칩 — 캐릭터 포즈 순환 (확인용)
  void _cyclePose() {
    setState(() {
      final next = ((_poseOverride ?? -1) + 1) % MascotPose.values.length;
      _poseOverride = next;
    });
  }

  @override
  Widget build(BuildContext context) {
    final hour = DateTime.now().hour;
    final greeting = hour < 11
        ? '좋은 아침이에요'
        : hour < 17
        ? '오늘도 화이팅이에요'
        : '오늘 하루 어떠셨어요';
    // 포즈 — 테마칩으로 오버라이드했으면 그거, 아니면 시간 버킷 기반 자동 랜덤
    final pose = _poseOverride != null
        ? MascotPose.values[_poseOverride!]
        : MascotFor.timedRandom(_poseClock, interval: _poseRefreshInterval);

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        // 흰 배경 — LADS Flat 2.0 기본
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.xl),
        // Soft UI — 부드러운 단일 그림자
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.20),
            blurRadius: 18,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: Padding(
        // 상단·좌우 여유 — 위는 더 넉넉히 (날짜 네비 숨쉬게)
        padding: const EdgeInsets.fromLTRB(
          AppSpace.cardInside + 2,
          AppSpace.lg + 4,
          AppSpace.cardInside + 2,
          AppSpace.cardInside + 4,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ─── 날짜 네비게이션 — ‹ 5월 24일 일 ▾ › ───
            _DateNav(
              date: widget.date,
              isToday: widget.isToday,
              onPrev: widget.onPrevDay,
              onNext: widget.onNextDay,
              onTapDate: widget.onTapDate,
            ),
            const SizedBox(height: AppSpace.xl),

            // ─── 상단: 인사 + 테마 칩 ───
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  greeting,
                  style: AppText.caption.copyWith(
                    color: AppColor.inkTertiary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                _ThemeChip(onTap: _cyclePose),
              ],
            ),
            const SizedBox(height: AppSpace.sm),

            // ─── 건강 점수 (포인트 — brand) ───
            Pressable(
              onTap: widget.onTapScore,
              child: widget.scoreReady
                  ? Row(
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        // 점수 카운트업 — 0 → healthScore (게이지와 동기)
                        AnimatedBuilder(
                          animation: _gauge,
                          builder: (context, child) => Text(
                            '${(_gauge.value * widget.healthScore).round()}',
                            style: const TextStyle(
                              fontFamily: 'Pretendard',
                              color: AppColor.brandDeep,
                              fontSize: 44,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0,
                              height: 1.0,
                            ),
                          ),
                        ),
                        Text(
                          '점',
                          style: TextStyle(
                            color: AppColor.brandDeep,
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(width: AppSpace.sm),
                        Padding(
                          padding: const EdgeInsets.only(bottom: 5),
                          child: Text(
                            widget.scoreLabelText ?? '오늘의 건강 점수',
                            style: AppText.caption.copyWith(
                              // 등급 코드가 오면 오늘의 분석 링/칩과 같은
                              // 시맨틱 색을 쓴다 — 두 화면 등급 색 정합.
                              color: widget.scoreLabel != null
                                  ? scoreLabelColor(widget.scoreLabel)
                                  : AppColor.inkSecondary,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        const Spacer(),
                        Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Icon(
                            Icons.chevron_right_rounded,
                            color: AppColor.inkTertiary,
                            size: 20,
                          ),
                        ),
                      ],
                    )
                  : Row(
                      children: [
                        Expanded(
                          child: Text(
                            '기록을 추가하면 점수를 보여드려요',
                            style: AppText.body.copyWith(
                              color: AppColor.inkSecondary,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        Icon(
                          Icons.chevron_right_rounded,
                          color: AppColor.inkTertiary,
                          size: 20,
                        ),
                      ],
                    ),
            ),
            const SizedBox(height: 2),
            // 칼로리 — 목표 있으면 '소비/목표', 없으면 '기록 합계'
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Text(
                  '${widget.consumedKcal}',
                  style: const TextStyle(
                    fontFamily: 'Pretendard',
                    color: AppColor.ink,
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                Text(
                  _hasTarget
                      ? ' / ${widget.targetKcal} kcal'
                      : ' kcal · 오늘 기록 합계',
                  style: AppText.caption.copyWith(
                    color: AppColor.inkTertiary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpace.md),

            // ─── 탄단지 알약 칩 (포인트 — 매크로 3색) ───
            Row(
              children: [
                _MacroPill(label: '탄', pct: widget.carbPct, color: _kCarb),
                const SizedBox(width: AppSpace.sm),
                _MacroPill(
                  label: '단',
                  pct: widget.proteinPct,
                  color: _kProtein,
                ),
                const SizedBox(width: AppSpace.sm),
                _MacroPill(label: '지', pct: widget.fatPct, color: _kFat),
              ],
            ),
            const SizedBox(height: AppSpace.md),

            // ─── 반원 게이지 + 캐릭터 (게이지 차오름 애니메이션) ───
            AnimatedBuilder(
              animation: _gauge,
              builder: (context, child) => _GaugeWithMascot(
                ratio: _kcalRatio * _gauge.value,
                pose: pose,
              ),
            ),
            const SizedBox(height: AppSpace.sm),

            // ─── 소모/잔여 칼로리 한 줄 (목표 있을 때만 잔여 표시) ───
            // 미연동(목표 없음)이면 추정치 대신 워치 연동 잠금 안내 (figma 951:58).
            Center(
              child: _hasTarget
                  ? RichText(
                      text: TextSpan(
                        style: AppText.caption.copyWith(
                          fontWeight: FontWeight.w700,
                          color: AppColor.inkSecondary,
                        ),
                        children: [
                          const TextSpan(text: '🔥 '),
                          TextSpan(text: '${widget.burnedKcal} kcal 소모'),
                          TextSpan(
                            text: '  ·  ',
                            style: TextStyle(color: AppColor.border),
                          ),
                          TextSpan(
                            text: '$_remainKcal kcal',
                            style: const TextStyle(
                              color: AppColor.brandDeep,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const TextSpan(text: ' 더 먹을 수 있어요'),
                        ],
                      ),
                    )
                  : const _BurnedKcalLock(),
            ),
            const SizedBox(height: AppSpace.lg),

            // ─── 순탄수 · 단백질 · 지방 (sunken 박스) ───
            Container(
              padding: const EdgeInsets.all(AppSpace.md),
              decoration: BoxDecoration(
                color: AppColor.sunken, // 옅은 회색 — LADS sunken
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: _MacroBar(
                      label: '순탄수',
                      value: widget.carbG,
                      target: widget.carbTargetG,
                      color: _kCarb,
                      progress: _gauge,
                      totalsOnly: widget.macrosTotalsOnly,
                    ),
                  ),
                  const SizedBox(width: AppSpace.md),
                  Expanded(
                    child: _MacroBar(
                      label: '단백질',
                      value: widget.proteinG,
                      target: widget.proteinTargetG,
                      color: _kProtein,
                      progress: _gauge,
                      totalsOnly: widget.macrosTotalsOnly,
                    ),
                  ),
                  const SizedBox(width: AppSpace.md),
                  Expanded(
                    child: _MacroBar(
                      label: '지방',
                      value: widget.fatG,
                      target: widget.fatTargetG,
                      color: _kFat,
                      progress: _gauge,
                      totalsOnly: widget.macrosTotalsOnly,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpace.sm),

            // ─── 영양소 상세 ───
            Pressable(
              onTap: widget.onTapDetail,
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
                alignment: Alignment.center,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      '영양소 상세 보기',
                      style: AppText.caption.copyWith(
                        color: AppColor.inkSecondary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Icon(
                      Icons.chevron_right_rounded,
                      color: AppColor.inkTertiary,
                      size: 18,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 테마 칩 — 누르면 캐릭터 포즈 순환 (확인용)
// ═══════════════════════════════════════════
// ═══════════════════════════════════════════
// 날짜 네비게이션 — ‹  5월 24일 일 [오늘] ▾  ›
//   카드 맨 위. 화살표로 하루 이동, 가운데 탭 → 캘린더.
// ═══════════════════════════════════════════
class _DateNav extends StatelessWidget {
  final DateTime date;
  final bool isToday;
  final VoidCallback? onPrev;
  final VoidCallback? onNext;
  final VoidCallback? onTapDate;
  const _DateNav({
    required this.date,
    required this.isToday,
    this.onPrev,
    this.onNext,
    this.onTapDate,
  });

  static const _wd = ['월', '화', '수', '목', '금', '토', '일'];

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _NavArrow(icon: Icons.chevron_left_rounded, onTap: onPrev),
        const SizedBox(width: AppSpace.sm),
        // 가운데 날짜 캡슐 — 탭하면 캘린더
        Pressable(
          onTap: onTapDate,
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpace.lg,
              vertical: 9,
            ),
            decoration: BoxDecoration(
              color: AppColor.sunken,
              borderRadius: BorderRadius.circular(AppRadius.full),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.event_note_rounded,
                  color: AppColor.inkSecondary,
                  size: 15,
                ),
                const SizedBox(width: 5),
                Text(
                  '${date.month}월 ${date.day}일 ${_wd[date.weekday - 1]}',
                  style: const TextStyle(
                    color: AppColor.ink,
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(width: 4),
                if (isToday)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: AppColor.brand,
                      borderRadius: BorderRadius.circular(AppRadius.full),
                    ),
                    child: const Text(
                      '오늘',
                      style: TextStyle(
                        color: AppColor.ink,
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                Icon(
                  Icons.keyboard_arrow_down_rounded,
                  color: AppColor.inkTertiary,
                  size: 17,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(width: AppSpace.sm),
        _NavArrow(icon: Icons.chevron_right_rounded, onTap: onNext),
      ],
    );
  }
}

// 날짜 이동 화살표 — null 이면 비활성(흐림)
class _NavArrow extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;
  const _NavArrow({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null;
    return Pressable(
      onTap: onTap,
      child: Container(
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: AppColor.sunken,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Icon(
          icon,
          size: 20,
          color: AppColor.ink.withValues(alpha: enabled ? 0.8 : 0.25),
        ),
      ),
    );
  }
}

class _ThemeChip extends StatelessWidget {
  final VoidCallback onTap;
  const _ThemeChip({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpace.md,
          vertical: 7,
        ),
        decoration: BoxDecoration(
          color: AppColor.brandSoft,
          borderRadius: BorderRadius.circular(AppRadius.full),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.auto_awesome_rounded,
              color: AppColor.brandDeep,
              size: 13,
            ),
            const SizedBox(width: 4),
            Text(
              '테마',
              style: AppText.micro.copyWith(
                color: AppColor.brandDeep,
                fontWeight: FontWeight.w800,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 소모/잔여 kcal 잠금 안내 (Health Connect 미연동 · figma 951:58)
//   - 추정치 표시 금지 — 색+아이콘+텍스트 병행으로 '연동하면 보여드려요' 톤.
//   - 첫 줄: 지금 표시값이 오늘 기록 합계임을 명시.
//   - 둘째 줄: 워치 아이콘 + 잠금 안내 (소모·잔여 미노출).
// ═══════════════════════════════════════════
class _BurnedKcalLock extends StatelessWidget {
  const _BurnedKcalLock();

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text(
          '오늘 먹은 음식 합계예요',
          style: AppText.caption.copyWith(
            fontWeight: FontWeight.w700,
            color: AppColor.inkSecondary,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: AppColor.sunken,
            borderRadius: BorderRadius.circular(AppRadius.full),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(
                Icons.watch_outlined,
                size: 14,
                color: AppColor.inkTertiary,
              ),
              const SizedBox(width: 5),
              Icon(
                Icons.lock_outline_rounded,
                size: 12,
                color: AppColor.inkTertiary,
              ),
              const SizedBox(width: 6),
              Text(
                '워치를 연동하면 소모·잔여 칼로리도 보여드려요',
                style: AppText.micro.copyWith(
                  color: AppColor.inkSecondary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════
// 탄단지 알약 칩 — 포인트 컬러 (매크로별)
// ═══════════════════════════════════════════
class _MacroPill extends StatelessWidget {
  final String label;
  final int pct;
  final Color color;
  const _MacroPill({
    required this.label,
    required this.pct,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 20,
            height: 20,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            alignment: Alignment.center,
            child: Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 6),
          Text(
            '$pct%',
            style: TextStyle(
              color: AppColor.ink,
              fontSize: 13,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 반원 게이지 + 캐릭터
// ═══════════════════════════════════════════
class _GaugeWithMascot extends StatelessWidget {
  final double ratio;
  final MascotPose pose;
  const _GaugeWithMascot({required this.ratio, required this.pose});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (ctx, box) {
        final w = box.maxWidth;
        final h = w * 0.52;
        return SizedBox(
          width: w,
          height: h + 8,
          child: Stack(
            alignment: Alignment.bottomCenter,
            children: [
              CustomPaint(
                size: Size(w, h),
                painter: _HalfGaugePainter(ratio: ratio),
              ),
              Positioned(
                bottom: 0,
                // 포즈 바뀔 때 부드럽게 페이드 + 살짝 스케일
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 320),
                  switchInCurve: Curves.easeOutBack,
                  transitionBuilder: (child, anim) => FadeTransition(
                    opacity: anim,
                    child: ScaleTransition(
                      scale: Tween<double>(begin: 0.8, end: 1.0).animate(anim),
                      child: child,
                    ),
                  ),
                  child: Image.asset(
                    pose.asset,
                    key: ValueKey(pose),
                    width: h * 0.92,
                    height: h * 0.92,
                    fit: BoxFit.contain,
                    errorBuilder: (context, error, stackTrace) =>
                        SizedBox(width: h * 0.92, height: h * 0.92),
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

class _HalfGaugePainter extends CustomPainter {
  final double ratio;
  _HalfGaugePainter({required this.ratio});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height);
    final radius = size.width / 2 - 14;
    final rect = Rect.fromCircle(center: center, radius: radius);
    const stroke = 16.0;

    // 트랙 — 옅은 회색 (LADS sunken 톤)
    final trackPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round
      ..color = AppColor.sunken;
    canvas.drawArc(rect, math.pi, math.pi, false, trackPaint);

    // 진행 호 — 포인트 컬러 (brand 노랑 그라데)
    final progressPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round
      ..shader = const LinearGradient(
        colors: [Color(0xFFFFD64A), AppColor.brand],
      ).createShader(rect);
    canvas.drawArc(
      rect,
      math.pi,
      math.pi * ratio.clamp(0.02, 1.0),
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(_HalfGaugePainter old) => old.ratio != ratio;
}

// ═══════════════════════════════════════════
// 순탄수/단백질/지방 막대
// ═══════════════════════════════════════════
class _MacroBar extends StatelessWidget {
  final String label;
  final int value;
  final int target;
  final Color color;
  // 0→1 진행 애니메이션 — 막대가 차오르고 숫자 카운트업
  final Animation<double> progress;
  // 목표 미제공 — '/ target' 숨기고 'g' 단위만, 막대는 은은하게 표시.
  final bool totalsOnly;
  const _MacroBar({
    required this.label,
    required this.value,
    required this.target,
    required this.color,
    required this.progress,
    this.totalsOnly = false,
  });

  @override
  Widget build(BuildContext context) {
    // 목표 모드 = value/target, 합계 모드 = 은은한 고정 채움(수치 의미 X).
    final r = totalsOnly
        ? (value > 0 ? 0.5 : 0.0)
        : (target > 0 ? (value / target).clamp(0.0, 1.0) : 0.0);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: AppText.micro.copyWith(
            color: AppColor.inkTertiary,
            fontWeight: FontWeight.w700,
            fontSize: 11.5,
          ),
        ),
        const SizedBox(height: 3),
        Row(
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          children: [
            // 숫자 카운트업
            AnimatedBuilder(
              animation: progress,
              builder: (context, child) => Text(
                '${(progress.value * value).round()}',
                style: TextStyle(
                  color: AppColor.ink,
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            Text(
              totalsOnly ? ' g' : ' / $target g',
              style: AppText.micro.copyWith(
                color: AppColor.inkTertiary,
                fontSize: 11,
              ),
            ),
          ],
        ),
        const SizedBox(height: 5),
        // 막대 차오름
        ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.full),
          child: AnimatedBuilder(
            animation: progress,
            builder: (context, child) => LinearProgressIndicator(
              value: r * progress.value,
              minHeight: 5,
              backgroundColor: AppColor.border,
              valueColor: AlwaysStoppedAnimation(color),
            ),
          ),
        ),
      ],
    );
  }
}
