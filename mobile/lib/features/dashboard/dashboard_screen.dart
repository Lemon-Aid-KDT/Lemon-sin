import 'package:flutter/material.dart';

import '../../app_controller.dart';
import '../../shared/theme/lemon_design_tokens.dart';
import '../../shared/widgets/disclaimer_list.dart';
import '../../shared/widgets/empty_state.dart';
import '../../widgets/dashboard/health_hero_card.dart';
import 'dashboard_models.dart';

/// Minimal dashboard summary connected to `/dashboard/summary`.
class DashboardScreen extends StatelessWidget {
  /// Creates the dashboard screen.
  const DashboardScreen({required this.controller, super.key});

  /// App flow controller.
  final AppController controller;

  @override
  Widget build(BuildContext context) {
    final DashboardSummary? summary = controller.dashboardSummary;
    if (summary == null) {
      return EmptyState(
        icon: Icons.dashboard_outlined,
        title: 'No dashboard summary yet',
        message: controller.hasMinimumConsents
            ? 'Refresh the dashboard to load backend summary data.'
            : 'Grant the required consents before loading dashboard data.',
      );
    }

    return RefreshIndicator(
      onRefresh: controller.refreshDashboard,
      color: LemonColors.leaf,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
        children: <Widget>[
          HealthHeroCard(summary: summary),
          const SizedBox(height: 18),
          _MetricGrid(summary: summary),
          const SizedBox(height: 18),
          _BackendStatusStrip(summary: summary),
          const SizedBox(height: 18),
          DisclaimerList(disclaimers: summary.disclaimers),
        ],
      ),
    );
  }
}

class _MetricGrid extends StatelessWidget {
  const _MetricGrid({required this.summary});

  final DashboardSummary summary;

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 2,
      crossAxisSpacing: LemonSpacing.md,
      mainAxisSpacing: LemonSpacing.md,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      childAspectRatio: 1.18,
      children: <Widget>[
        _MetricCard(
          icon: Icons.medication_outlined,
          label: 'Supplements',
          value: '${summary.supplements.registeredCount}',
          detail: '${summary.supplements.requiresReviewCount} need review',
          accent: LemonColors.leaf,
        ),
        _MetricCard(
          icon: Icons.restaurant_outlined,
          label: 'Nutrition',
          value: summary.nutrition.dataStatus,
          detail:
              'Low ${summary.nutrition.lowCount} / High ${summary.nutrition.highCount}',
          accent: LemonColors.lemonDeep,
        ),
        _MetricCard(
          icon: Icons.directions_walk_outlined,
          label: 'Activity',
          value: summary.activity.dataStatus,
          detail: summary.activity.latestSteps == null
              ? 'No step data'
              : '${summary.activity.latestSteps} steps',
          accent: LemonColors.sky,
        ),
        _MetricCard(
          icon: Icons.monitor_weight_outlined,
          label: 'Weight',
          value: summary.weight.dataStatus,
          detail: summary.weight.latestWeightKg == null
              ? 'No weight data'
              : '${summary.weight.latestWeightKg} kg',
          accent: LemonColors.review,
        ),
      ],
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.detail,
    required this.accent,
  });

  final IconData icon;
  final String label;
  final String value;
  final String detail;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LemonColors.paper,
        borderRadius: BorderRadius.circular(LemonRadius.lg),
        border: Border.all(color: LemonColors.border),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            DecoratedBox(
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(LemonRadius.md),
              ),
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: Icon(icon, color: accent, size: 22),
              ),
            ),
            const Spacer(),
            Text(
              label,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: LemonColors.inkSoft,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: LemonColors.ink,
                fontWeight: FontWeight.w800,
                letterSpacing: 0,
              ),
            ),
            const SizedBox(height: 3),
            Text(
              detail,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: LemonColors.inkSoft),
            ),
          ],
        ),
      ),
    );
  }
}

class _BackendStatusStrip extends StatelessWidget {
  const _BackendStatusStrip({required this.summary});

  final DashboardSummary summary;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LemonColors.ink,
        borderRadius: BorderRadius.circular(LemonRadius.lg),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Row(
              children: <Widget>[
                Icon(
                  Icons.verified_outlined,
                  color: LemonColors.lemon,
                  size: 20,
                ),
                SizedBox(width: 8),
                Text(
                  'Backend contract',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              'Live summary: nutrition ${summary.nutrition.dataStatus}, '
              'activity ${summary.activity.dataStatus}, '
              'weight ${summary.weight.dataStatus}',
              style: const TextStyle(
                color: Color(0xFFDCD7C4),
                fontSize: 13,
                height: 1.4,
                letterSpacing: 0,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
