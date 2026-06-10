// screens/score_screen.dart — '오늘의 분석' 탭 (figma S-09)
//
// 디자인:
//   - 헤더 '오늘의 분석' + 날짜 칩
//   - 카드 1 '오늘의 종합 분석' + 등급 칩: 도넛 링(점수/100) + 종합 코멘트
//       + 연노랑 CTA '🍋 레몬봇에게 물어보기 ›'
//   - 카드 2 '실천 리스트'('오늘 챙기면 좋은 N가지'): 체크 원형 + 항목들 (세션 메모리)
//   - 카드 3 '스마트 분석' '지난 4주 추이': 점수 이력 영속이 없어 잠금 placeholder
//   - 하단 면책
//
// 데이터:
//   - 종합 점수·등급·코멘트: AppController dashboard summary health_score (배치 A 모델)
//   - 실천 리스트: POST /ai-agent/daily-coaching (AiCoachingRepository)
//   - 하루 1회 캐시 (날짜 키) — 같은 날 재진입 시 재호출하지 않음
//
// 연산은 모두 백엔드. 모바일은 표시만.

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../app_controller.dart';
import '../features/ai_coaching/ai_coaching_models.dart';
import '../features/ai_coaching/ai_coaching_repository.dart';
import '../features/dashboard/home_models.dart';
import '../utils/design_tokens_v2.dart';
import '../widgets/common/pressable.dart';

/// 오늘의 분석 화면 (figma S-09).
class ScoreScreen extends StatefulWidget {
  /// 오늘의 분석 화면을 생성한다.
  ///
  /// Args:
  ///   controller: 점수·당일 식사·등록 영양제를 제공하는 앱 컨트롤러.
  ///   coachingRepository: 실천 리스트(daily-coaching) 호출 저장소.
  const ScoreScreen({
    required this.controller,
    required this.coachingRepository,
    super.key,
  });

  /// 점수·당일 식사·등록 영양제를 제공하는 앱 컨트롤러.
  final AppController controller;

  /// 실천 리스트 호출 저장소.
  final AiCoachingRepository coachingRepository;

  @override
  State<ScoreScreen> createState() => _ScoreScreenState();
}

class _ScoreScreenState extends State<ScoreScreen> {
  // 실천 리스트 로딩 상태.
  bool _loadingCoaching = false;
  // 실천 리스트 호출 실패 여부 (카드 내 가벼운 오류 상태).
  bool _coachingFailed = false;
  // 마지막으로 받은 실천 리스트 결과.
  DailyCoachingResult? _coaching;
  // 하루 1회 캐시 키 (YYYY-MM-DD). 같은 날 재진입 시 재호출 방지.
  String? _cachedDateKey;
  // 실천 항목 체크 토글 — 세션 메모리. // TODO(persist): SharedPreferences 연동.
  final Set<int> _checkedItemIndexes = <int>{};

  AppController get _controller => widget.controller;

  DateTime get _today {
    final DateTime now = DateTime.now();
    return DateTime(now.year, now.month, now.day);
  }

  static String _dateKey(DateTime day) {
    final String month = day.month.toString().padLeft(2, '0');
    final String date = day.day.toString().padLeft(2, '0');
    return '${day.year}-$month-$date';
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadCoaching());
  }

  /// 실천 리스트를 불러온다. 같은 날짜로 이미 받았으면 재호출하지 않는다.
  Future<void> _loadCoaching({bool force = false}) async {
    final String key = _dateKey(_today);
    if (!force && _cachedDateKey == key && _coaching != null) {
      return;
    }
    if (_loadingCoaching) return;
    setState(() {
      _loadingCoaching = true;
      _coachingFailed = false;
    });
    try {
      final DailyCoachingResult result = await widget.coachingRepository
          .runDailyCoaching(
            day: _today,
            meals: _controller.mealsForDay(_today),
            supplements: _controller.homeSupplements.results,
          );
      if (!mounted) return;
      setState(() {
        _coaching = result;
        _cachedDateKey = key;
        _checkedItemIndexes.clear();
        _loadingCoaching = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _coachingFailed = true;
        _loadingCoaching = false;
      });
    }
  }

  void _toggleItem(int index) {
    setState(() {
      if (_checkedItemIndexes.contains(index)) {
        _checkedItemIndexes.remove(index);
      } else {
        _checkedItemIndexes.add(index);
      }
    });
  }

  void _openCamera() {
    context.go('/shell/camera?mode=meal');
  }

  void _openLemonBot() {
    context.go('/shell/chat');
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        final DashboardHealthScore score = _controller.healthScore;
        return Scaffold(
          backgroundColor: AppColor.bg,
          body: SafeArea(
            bottom: false,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(
                AppSpace.page,
                AppSpace.lg,
                AppSpace.page,
                AppSpace.xl + 80,
              ),
              children: <Widget>[
                _Header(today: _today),
                const SizedBox(height: AppSpace.lg),
                _SummaryCard(
                  score: score,
                  onLemonBot: _openLemonBot,
                  onRecord: _openCamera,
                ),
                const SizedBox(height: AppSpace.md),
                _ChecklistCard(
                  loading: _loadingCoaching,
                  failed: _coachingFailed,
                  coaching: _coaching,
                  checkedIndexes: _checkedItemIndexes,
                  onToggle: _toggleItem,
                  onRetry: () => _loadCoaching(force: true),
                ),
                const SizedBox(height: AppSpace.md),
                const _TrendLockedCard(),
                const SizedBox(height: AppSpace.lg),
                const _Disclaimer(),
              ],
            ),
          ),
        );
      },
    );
  }
}

// ═══════════════════════════════════════════
// 헤더 — '오늘의 분석' + 날짜 칩
// ═══════════════════════════════════════════
class _Header extends StatelessWidget {
  final DateTime today;
  const _Header({required this.today});

  static const List<String> _weekdays = <String>['월', '화', '수', '목', '금', '토', '일'];

  @override
  Widget build(BuildContext context) {
    final String label =
        '${today.month}월 ${today.day}일 (${_weekdays[today.weekday - 1]})';
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: <Widget>[
        Text('오늘의 분석', style: AppText.title),
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpace.md,
            vertical: 6,
          ),
          decoration: BoxDecoration(
            color: AppColor.brandSoft,
            borderRadius: BorderRadius.circular(AppRadius.full),
          ),
          child: Text(
            label,
            style: AppText.caption.copyWith(
              color: AppColor.brandDeep,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════
// 카드 데코 — 대시보드 톤과 통일 (§17)
// ═══════════════════════════════════════════
BoxDecoration _cardDeco() => BoxDecoration(
  color: AppColor.surface,
  borderRadius: BorderRadius.circular(AppRadius.lg),
  boxShadow: const <BoxShadow>[
    BoxShadow(
      color: Color.fromRGBO(140, 155, 175, 0.20),
      blurRadius: 16,
      offset: Offset(0, 5),
    ),
  ],
);

// ═══════════════════════════════════════════
// 카드 1 — 오늘의 종합 분석
//   도넛 링(점수/100) + 등급 칩 + 종합 코멘트 + 레몬봇 CTA
//   not_ready → 기록 추가 안내 + 촬영 CTA
// ═══════════════════════════════════════════
class _SummaryCard extends StatelessWidget {
  final DashboardHealthScore score;
  final VoidCallback onLemonBot;
  final VoidCallback onRecord;
  const _SummaryCard({
    required this.score,
    required this.onLemonBot,
    required this.onRecord,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside + 2),
      decoration: _cardDeco(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              Text('오늘의 종합 분석', style: AppText.subtitle),
              if (score.isReady && score.labelText != null)
                _GradeChip(label: score.labelText!),
            ],
          ),
          const SizedBox(height: AppSpace.lg),
          if (score.isReady)
            _ReadyBody(score: score, onLemonBot: onLemonBot)
          else
            _NotReadyBody(onRecord: onRecord),
        ],
      ),
    );
  }
}

class _ReadyBody extends StatelessWidget {
  final DashboardHealthScore score;
  final VoidCallback onLemonBot;
  const _ReadyBody({required this.score, required this.onLemonBot});

  @override
  Widget build(BuildContext context) {
    final String? message = score.message;
    final bool hasMessage = message != null && message.trim().isNotEmpty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Center(child: _ScoreRing(score: score.score ?? 0)),
        const SizedBox(height: AppSpace.lg),
        Text(
          hasMessage ? message.trim() : '오늘 기록을 바탕으로 한 종합 코멘트예요.',
          style: AppText.body.copyWith(
            color: AppColor.inkSecondary,
            height: 1.55,
          ),
        ),
        const SizedBox(height: AppSpace.lg),
        _LemonBotCta(onTap: onLemonBot),
      ],
    );
  }
}

class _NotReadyBody extends StatelessWidget {
  final VoidCallback onRecord;
  const _NotReadyBody({required this.onRecord});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          '기록을 추가하면 점수를 보여드려요.',
          style: AppText.body.copyWith(
            color: AppColor.inkSecondary,
            height: 1.55,
          ),
        ),
        const SizedBox(height: AppSpace.lg),
        SizedBox(
          width: double.infinity,
          child: AppPrimaryButton(label: '촬영하기', onPressed: onRecord),
        ),
      ],
    );
  }
}

/// 등급 칩 (예: '좋아요').
class _GradeChip extends StatelessWidget {
  final String label;
  const _GradeChip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpace.md, vertical: 5),
      decoration: BoxDecoration(
        color: AppColor.successSoft,
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
      child: Text(
        label,
        style: AppText.caption.copyWith(
          color: AppColor.success,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

/// 도넛 링 점수 (점수/100).
class _ScoreRing extends StatelessWidget {
  final int score;
  const _ScoreRing({required this.score});

  @override
  Widget build(BuildContext context) {
    final double ratio = (score.clamp(0, 100)) / 100;
    return SizedBox(
      width: 148,
      height: 148,
      child: Stack(
        alignment: Alignment.center,
        children: <Widget>[
          SizedBox(
            width: 148,
            height: 148,
            child: CircularProgressIndicator(
              value: ratio,
              strokeWidth: 12,
              backgroundColor: const Color(0xFFF1F3F6),
              valueColor: const AlwaysStoppedAnimation<Color>(AppColor.brand),
            ),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Text(
                '$score',
                style: const TextStyle(
                  fontFamily: 'Pretendard',
                  color: AppColor.ink,
                  fontSize: 44,
                  fontWeight: FontWeight.w800,
                  height: 1,
                  letterSpacing: 0,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                '/ 100',
                style: AppText.caption.copyWith(color: AppColor.inkTertiary),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// 연노랑 '레몬봇에게 물어보기' CTA.
class _LemonBotCta extends StatelessWidget {
  final VoidCallback onTap;
  const _LemonBotCta({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpace.lg,
          vertical: AppSpace.md + 2,
        ),
        decoration: BoxDecoration(
          color: AppColor.brandSoft,
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        child: Row(
          children: <Widget>[
            const Text('🍋', style: TextStyle(fontSize: 18)),
            const SizedBox(width: AppSpace.sm),
            Expanded(
              child: Text(
                '레몬봇에게 물어보기',
                style: AppText.body.copyWith(
                  color: AppColor.brandDeep,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const Icon(
              Icons.chevron_right_rounded,
              color: AppColor.brandDeep,
              size: 22,
            ),
          ],
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 카드 2 — 실천 리스트 ('오늘 챙기면 좋은 N가지')
//   recommendations + actions → 체크 원형 항목 (세션 메모리)
//   requires_user_approval=true → '기록을 확정하면 맞춤 제안을 드려요' 안내
//   호출 실패 → 가벼운 오류 상태 + 재시도 버튼
// ═══════════════════════════════════════════
class _ChecklistCard extends StatelessWidget {
  final bool loading;
  final bool failed;
  final DailyCoachingResult? coaching;
  final Set<int> checkedIndexes;
  final ValueChanged<int> onToggle;
  final VoidCallback onRetry;
  const _ChecklistCard({
    required this.loading,
    required this.failed,
    required this.coaching,
    required this.checkedIndexes,
    required this.onToggle,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    final DailyCoachingResult? result = coaching;
    final int count = result?.items.length ?? 0;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside + 2),
      decoration: _cardDeco(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            count > 0 ? '오늘 챙기면 좋은 $count가지' : '실천 리스트',
            style: AppText.subtitle,
          ),
          const SizedBox(height: AppSpace.md),
          _buildBody(result),
        ],
      ),
    );
  }

  Widget _buildBody(DailyCoachingResult? result) {
    if (loading && result == null) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: AppSpace.lg),
        child: Center(
          child: SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(
              strokeWidth: 2.4,
              valueColor: AlwaysStoppedAnimation<Color>(AppColor.brand),
            ),
          ),
        ),
      );
    }
    if (failed && result == null) {
      return _ChecklistError(onRetry: onRetry);
    }
    if (result != null && result.requiresUserApproval && result.items.isEmpty) {
      return _ChecklistHint(
        text: '기록을 확정하면 맞춤 제안을 드려요.',
      );
    }
    if (result == null || result.items.isEmpty) {
      return _ChecklistHint(
        text: '오늘 끼니와 영양제를 기록하면 실천 항목을 만들어 드려요.',
      );
    }
    return Column(
      children: <Widget>[
        for (int i = 0; i < result.items.length; i++) ...<Widget>[
          _ChecklistRow(
            item: result.items[i],
            checked: checkedIndexes.contains(i),
            onToggle: () => onToggle(i),
          ),
          if (i != result.items.length - 1)
            Divider(color: AppColor.border, height: AppSpace.lg),
        ],
      ],
    );
  }
}

class _ChecklistRow extends StatelessWidget {
  final DailyCoachingItem item;
  final bool checked;
  final VoidCallback onToggle;
  const _ChecklistRow({
    required this.item,
    required this.checked,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final bool hasSubtitle = item.subtitle.trim().isNotEmpty;
    return Pressable(
      onTap: onToggle,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          // 체크 원형
          Container(
            margin: const EdgeInsets.only(top: 1),
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: checked ? AppColor.brand : const Color(0xFFE5E8EB),
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: const Icon(
              Icons.check_rounded,
              color: Colors.white,
              size: 16,
            ),
          ),
          const SizedBox(width: AppSpace.sm + 2),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  item.title.isNotEmpty ? item.title : '실천 항목',
                  style: AppText.body.copyWith(
                    color: checked ? AppColor.inkTertiary : AppColor.ink,
                    fontWeight: FontWeight.w700,
                    decoration: checked ? TextDecoration.lineThrough : null,
                  ),
                ),
                if (hasSubtitle) ...<Widget>[
                  const SizedBox(height: 2),
                  Text(
                    item.subtitle.trim(),
                    style: AppText.caption.copyWith(
                      color: AppColor.inkSecondary,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ChecklistHint extends StatelessWidget {
  final String text;
  const _ChecklistHint({required this.text});

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: AppText.body.copyWith(color: AppColor.inkSecondary, height: 1.5),
    );
  }
}

class _ChecklistError extends StatelessWidget {
  final VoidCallback onRetry;
  const _ChecklistError({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: AppColor.inkTertiary.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(AppRadius.sm - 2),
          ),
          alignment: Alignment.center,
          child: const Icon(
            Icons.cloud_off_rounded,
            size: 18,
            color: AppColor.inkTertiary,
          ),
        ),
        const SizedBox(width: AppSpace.sm),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                '실천 리스트를 불러오지 못했어요',
                style: AppText.body.copyWith(
                  color: AppColor.ink,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: AppSpace.sm),
              Pressable(
                onTap: onRetry,
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
                    '다시 시도',
                    style: AppText.caption.copyWith(
                      color: AppColor.brandDeep,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
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
// 카드 3 — 스마트 분석 '지난 4주 추이' (잠금 placeholder)
//   점수 이력 영속이 P0 범위 밖이라 빈 상태로 안내.
// ═══════════════════════════════════════════
class _TrendLockedCard extends StatelessWidget {
  const _TrendLockedCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside + 2),
      decoration: _cardDeco(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Text('스마트 분석', style: AppText.subtitle),
              const SizedBox(width: AppSpace.sm),
              Text(
                '지난 4주 추이',
                style: AppText.caption.copyWith(color: AppColor.inkTertiary),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.lg),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpace.lg,
              vertical: AppSpace.xl,
            ),
            decoration: BoxDecoration(
              color: AppColor.sunken,
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            child: Column(
              children: <Widget>[
                Icon(
                  Icons.lock_outline_rounded,
                  color: AppColor.inkTertiary,
                  size: 28,
                ),
                const SizedBox(height: AppSpace.sm),
                Text(
                  '기록이 쌓이면 추이를 보여드려요',
                  style: AppText.body.copyWith(
                    color: AppColor.inkSecondary,
                    fontWeight: FontWeight.w600,
                  ),
                  textAlign: TextAlign.center,
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
// 하단 면책 (LADS §14)
// ═══════════════════════════════════════════
class _Disclaimer extends StatelessWidget {
  const _Disclaimer();

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
        children: <Widget>[
          Icon(Icons.info_outline, color: AppColor.brandDeep, size: 18),
          const SizedBox(width: AppSpace.sm),
          Expanded(
            child: Text(
              '이 분석은 건강 관리를 돕는 참고 정보예요.\n의사·약사·영양사의 진단을 대신하진 않아요.',
              style: AppText.caption.copyWith(color: AppColor.ink, height: 1.5),
            ),
          ),
        ],
      ),
    );
  }
}
