import 'package:flutter/material.dart';

import '../../app_controller.dart';
import '../../shared/widgets/disclaimer_list.dart';
import '../../shared/widgets/empty_state.dart';
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
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: <Widget>[
          Text('Dashboard', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 4),
          Text('Updated ${summary.asOf.toLocal()}'),
          const SizedBox(height: 16),
          _MetricGrid(summary: summary),
          const SizedBox(height: 16),
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
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      childAspectRatio: 1.35,
      children: <Widget>[
        _MetricCard(
          icon: Icons.medication_outlined,
          label: 'Supplements',
          value: '${summary.supplements.registeredCount}',
          detail: '${summary.supplements.requiresReviewCount} need review',
        ),
        _MetricCard(
          icon: Icons.restaurant_outlined,
          label: 'Nutrition',
          value: summary.nutrition.dataStatus,
          detail:
              'Low ${summary.nutrition.lowCount} / High ${summary.nutrition.highCount}',
        ),
        _MetricCard(
          icon: Icons.directions_walk_outlined,
          label: 'Activity',
          value: summary.activity.dataStatus,
          detail: summary.activity.latestSteps == null
              ? 'No step data'
              : '${summary.activity.latestSteps} steps',
        ),
        _MetricCard(
          icon: Icons.monitor_weight_outlined,
          label: 'Weight',
          value: summary.weight.dataStatus,
          detail: summary.weight.latestWeightKg == null
              ? 'No weight data'
              : '${summary.weight.latestWeightKg} kg',
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
  });

  final IconData icon;
  final String label;
  final String value;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(icon),
            const Spacer(),
            Text(label, style: Theme.of(context).textTheme.labelLarge),
            Text(value, style: Theme.of(context).textTheme.titleLarge),
            Text(detail, maxLines: 1, overflow: TextOverflow.ellipsis),
          ],
        ),
      ),
    );
  }
}
