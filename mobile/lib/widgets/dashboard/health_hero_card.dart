import 'package:flutter/material.dart';

import '../../features/dashboard/dashboard_models.dart';
import '../../shared/theme/lemon_design_tokens.dart';
import '../common/pressable.dart';

/// Backend-connected version of the UIUX branch dashboard hero card.
class HealthHeroCard extends StatelessWidget {
  /// Creates a dashboard hero from live `/dashboard/summary` data.
  ///
  /// Args:
  ///   summary: Backend dashboard summary.
  ///   onTapReview: Optional action for review-needed supplement records.
  const HealthHeroCard({required this.summary, this.onTapReview, super.key});

  /// Live dashboard summary.
  final DashboardSummary summary;

  /// Optional review tap callback.
  final VoidCallback? onTapReview;

  @override
  Widget build(BuildContext context) {
    final int reviewCount = summary.supplements.requiresReviewCount;
    final String statusLabel = _overallStatusLabel(summary);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LemonColors.paper,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: LemonColors.border),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.08),
            blurRadius: 18,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 18, 18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        _greeting(DateTime.now()),
                        style: const TextStyle(
                          color: LemonColors.inkSoft,
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        statusLabel,
                        style: Theme.of(context).textTheme.headlineSmall
                            ?.copyWith(
                              color: LemonColors.ink,
                              fontFamily: 'AtoZ',
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0,
                            ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Updated ${_formatAsOf(summary.asOf)}',
                        style: const TextStyle(
                          color: LemonColors.inkSoft,
                          fontSize: 12,
                          height: 1.35,
                          letterSpacing: 0,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox(
                  width: 94,
                  height: 94,
                  child: Image.asset(
                    reviewCount > 0
                        ? LemonAssets.mascotWorking
                        : LemonAssets.mascotFresh,
                    fit: BoxFit.contain,
                    errorBuilder:
                        (
                          BuildContext context,
                          Object error,
                          StackTrace? stackTrace,
                        ) {
                          return const Icon(
                            Icons.health_and_safety_outlined,
                            color: LemonColors.leaf,
                            size: 54,
                          );
                        },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                _HeroMetricChip(
                  icon: Icons.medication_outlined,
                  label: 'Supplements',
                  value: '${summary.supplements.registeredCount}',
                  color: LemonColors.leaf,
                ),
                Pressable(
                  onTap: onTapReview,
                  child: _HeroMetricChip(
                    icon: Icons.manage_search_outlined,
                    label: 'Review',
                    value: '$reviewCount',
                    color: reviewCount > 0
                        ? LemonColors.review
                        : LemonColors.lemonDeep,
                  ),
                ),
                _HeroMetricChip(
                  icon: Icons.directions_walk_outlined,
                  label: 'Activity',
                  value: summary.activity.latestActivityScore == null
                      ? summary.activity.dataStatus
                      : summary.activity.latestActivityScore!
                            .round()
                            .toString(),
                  color: LemonColors.sky,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  static String _overallStatusLabel(DashboardSummary summary) {
    if (summary.supplements.requiresReviewCount > 0) {
      return '확인이 필요한 분석이 있어요';
    }
    if (summary.nutrition.dataStatus == 'ready' ||
        summary.activity.dataStatus == 'ready' ||
        summary.weight.dataStatus == 'ready') {
      return '오늘 데이터가 연결됐어요';
    }
    return '영양제 OCR 테스트 준비 완료';
  }

  static String _greeting(DateTime now) {
    if (now.hour < 11) {
      return '좋은 아침이에요';
    }
    if (now.hour < 17) {
      return '오늘도 차분히 점검해요';
    }
    return '오늘 기록을 확인해요';
  }

  static String _formatAsOf(DateTime value) {
    final DateTime local = value.toLocal();
    final String month = local.month.toString().padLeft(2, '0');
    final String day = local.day.toString().padLeft(2, '0');
    final String hour = local.hour.toString().padLeft(2, '0');
    final String minute = local.minute.toString().padLeft(2, '0');
    return '$month/$day $hour:$minute';
  }
}

class _HeroMetricChip extends StatelessWidget {
  const _HeroMetricChip({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(LemonRadius.pill),
        border: Border.all(color: color.withValues(alpha: 0.18)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(icon, color: color, size: 16),
            const SizedBox(width: 6),
            Text(
              '$label $value',
              style: const TextStyle(
                color: LemonColors.ink,
                fontSize: 12,
                fontWeight: FontWeight.w800,
                letterSpacing: 0,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
