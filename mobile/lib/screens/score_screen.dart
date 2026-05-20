// screens/score_screen.dart — 점수 탭 (LADS v2)
//
// 디자인:
//   - 상단 brand 헤더 (이번 주 평균 점수 강조)
//   - 본문 라운드 (Pillyze 톤)
//   - 주간 점수 그래프 (7일 막대) — CustomPainter 직접
//   - 카테고리별 점수 (균형·영양·일관성 등)
//   - 최근 평가 코멘트 (mock)
//   - 의료 면책

import 'package:flutter/material.dart';

import '../utils/design_tokens_v2.dart';

class ScoreScreen extends StatelessWidget {
  const ScoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.bg,
      body: Column(
        children: [
          const _ScoreHeader(weeklyAvg: 78),
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
                    AppSpace.page, AppSpace.xl,
                    AppSpace.page, AppSpace.xl + 80,
                  ),
                  children: const [
                    _WeeklyChart(),
                    SizedBox(height: AppSpace.md),
                    _CategoryScores(),
                    SizedBox(height: AppSpace.md),
                    _CommentCard(),
                    SizedBox(height: AppSpace.lg),
                    _Disclaimer(),
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
// 상단 헤더
// ═══════════════════════════════════════════
class _ScoreHeader extends StatelessWidget {
  final int weeklyAvg;
  const _ScoreHeader({required this.weeklyAvg});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColor.brand,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.page, AppSpace.lg, AppSpace.page, AppSpace.xl + AppSpace.lg,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '식단 점수',
                style: TextStyle(
                  color: AppColor.ink,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: AppSpace.md),
              Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  const Text(
                    '이번 주 평균',
                    style: TextStyle(
                      color: AppColor.ink,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.2,
                    ),
                  ),
                  const SizedBox(width: AppSpace.sm),
                  Text(
                    '$weeklyAvg',
                    style: const TextStyle(
                      color: AppColor.ink,
                      fontSize: 40,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -1.2,
                      height: 1,
                    ),
                  ),
                  const Text(
                    '점',
                    style: TextStyle(
                      color: AppColor.ink,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(width: AppSpace.sm),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.5),
                      borderRadius: BorderRadius.circular(AppRadius.full),
                    ),
                    child: const Text(
                      '+3 ↑',
                      style: TextStyle(
                        color: AppColor.ink,
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                      ),
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
}

// ═══════════════════════════════════════════
// 주간 그래프 (CustomPainter)
// ═══════════════════════════════════════════
class _WeeklyChart extends StatelessWidget {
  const _WeeklyChart();

  static const List<_DayScore> _data = [
    _DayScore('월', 72),
    _DayScore('화', 68),
    _DayScore('수', 80),
    _DayScore('목', 75),
    _DayScore('금', 82),
    _DayScore('토', 78),
    _DayScore('일', 86),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(
        AppSpace.cardInside, AppSpace.lg,
        AppSpace.cardInside, AppSpace.md,
      ),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.18),
            blurRadius: 14,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '이번 주',
            style: TextStyle(
              color: AppColor.ink,
              fontSize: 15,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: AppSpace.lg),
          SizedBox(
            height: 160,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                for (final d in _data)
                  Expanded(child: _BarItem(day: d, isToday: d.label == '수')),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DayScore {
  final String label;
  final int score;
  const _DayScore(this.label, this.score);
}

class _BarItem extends StatelessWidget {
  final _DayScore day;
  final bool isToday;
  const _BarItem({required this.day, required this.isToday});

  @override
  Widget build(BuildContext context) {
    // 100점 = 120px 높이 기준
    final h = (day.score / 100) * 120;
    final color = isToday ? AppColor.brand : const Color(0xFFE5E8EB);
    final txtColor = isToday ? AppColor.brandDeep : AppColor.inkTertiary;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 3),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          Text(
            '${day.score}',
            style: TextStyle(
              color: txtColor,
              fontSize: 11,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
            child: Container(
              width: double.infinity,
              height: h,
              color: color,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            day.label,
            style: TextStyle(
              color: isToday ? AppColor.ink : AppColor.inkTertiary,
              fontSize: 12,
              fontWeight: isToday ? FontWeight.w800 : FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 카테고리별 점수
// ═══════════════════════════════════════════
class _CategoryScores extends StatelessWidget {
  const _CategoryScores();

  static const List<_Cat> _cats = [
    _Cat('균형',   84, Color(0xFF22B07D)),
    _Cat('영양',   76, Color(0xFFFFB200)),
    _Cat('일관성', 70, Color(0xFF4D7BFF)),
    _Cat('주의',   88, Color(0xFFFF6B6B)),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.18),
            blurRadius: 14,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '카테고리별',
            style: TextStyle(
              color: AppColor.ink,
              fontSize: 15,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: AppSpace.md),
          for (int i = 0; i < _cats.length; i++) ...[
            _CatRow(cat: _cats[i]),
            if (i < _cats.length - 1) const SizedBox(height: AppSpace.sm),
          ],
        ],
      ),
    );
  }
}

class _Cat {
  final String label;
  final int score;
  final Color color;
  const _Cat(this.label, this.score, this.color);
}

class _CatRow extends StatelessWidget {
  final _Cat cat;
  const _CatRow({required this.cat});

  @override
  Widget build(BuildContext context) {
    final ratio = cat.score / 100;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              cat.label,
              style: const TextStyle(
                color: AppColor.ink,
                fontSize: 13,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.2,
              ),
            ),
            Text(
              '${cat.score}점',
              style: TextStyle(
                color: cat.color,
                fontSize: 13,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.full),
          child: LinearProgressIndicator(
            value: ratio,
            minHeight: 6,
            backgroundColor: const Color(0xFFF1F3F6),
            valueColor: AlwaysStoppedAnimation(cat.color),
          ),
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════
// 평가 코멘트
// ═══════════════════════════════════════════
class _CommentCard extends StatelessWidget {
  const _CommentCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.18),
            blurRadius: 14,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36, height: 36,
                decoration: BoxDecoration(
                  color: AppColor.brandSoft,
                  shape: BoxShape.circle,
                ),
                alignment: Alignment.center,
                child: Icon(Icons.auto_awesome_rounded,
                    color: AppColor.brandDeep, size: 18),
              ),
              const SizedBox(width: AppSpace.sm),
              const Text(
                '이번 주 평가',
                style: TextStyle(
                  color: AppColor.ink,
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.3,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          const Text(
            '균형은 잘 잡혔어요. 다만 비타민 D와 마그네슘이 꾸준히 부족했어요.\n'
            '주말엔 햇볕 30분 + 견과류 한 줌이면 도움이 될 거예요.',
            style: TextStyle(
              color: AppColor.inkSecondary,
              fontSize: 13.5,
              fontWeight: FontWeight.w500,
              height: 1.55,
              letterSpacing: -0.2,
            ),
          ),
        ],
      ),
    );
  }
}

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
        children: [
          Icon(Icons.info_outline_rounded,
              color: AppColor.brandDeep, size: 18),
          const SizedBox(width: AppSpace.sm),
          Expanded(
            child: Text(
              '이 점수는 식단 균형의 참고 지표예요.\n의사·약사·영양사의 진단을 대신하지 않아요.',
              style: TextStyle(
                color: AppColor.ink,
                fontSize: 12.5,
                height: 1.5,
                letterSpacing: -0.2,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
