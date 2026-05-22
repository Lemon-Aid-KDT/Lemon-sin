import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/state/confirmed_entry_store.dart';
import '../../../shared/theme/lemon_theme.dart';
import '../../../shared/widgets/medical_disclaimer.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final int foodCount = ConfirmedEntryStore.instance.foods.length;
    final int supplementCount = ConfirmedEntryStore.instance.supplements.length;

    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 28),
          children: <Widget>[
            _Header(foodCount: foodCount, supplementCount: supplementCount),
            const SizedBox(height: 16),
            _PrimaryAction(
              onFoodTap: () => context.go('/food-capture'),
              onSupplementTap: () => context.go('/supplement-capture'),
            ),
            const SizedBox(height: 16),
            _CoachingCard(
              foodCount: foodCount,
              supplementCount: supplementCount,
              onTap: () => context.go('/coaching'),
            ),
            const SizedBox(height: 16),
            _ChatCard(onTap: () => context.go('/chat')),
            const SizedBox(height: 16),
            _NotificationCard(onTap: () => context.go('/notifications')),
            const SizedBox(height: 16),
            _ActivityCard(onTap: () => context.go('/activity')),
            const SizedBox(height: 16),
            _EvidenceGrid(
              foodCount: foodCount,
              supplementCount: supplementCount,
            ),
            const SizedBox(height: 20),
            const MedicalDisclaimer(),
          ],
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.foodCount, required this.supplementCount});

  final int foodCount;
  final int supplementCount;

  @override
  Widget build(BuildContext context) {
    final DateTime now = DateTime.now();
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: <Widget>[
        DecoratedBox(
          decoration: BoxDecoration(
            color: LemonColors.lemonSoft,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: LemonColors.line),
          ),
          child: const SizedBox(
            width: 56,
            height: 56,
            child: Icon(
              Icons.local_drink_rounded,
              color: LemonColors.leaf,
              size: 32,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                '${now.month}월 ${now.day}일',
                style: Theme.of(context).textTheme.labelMedium,
              ),
              const SizedBox(height: 2),
              Text(
                'Lemon Aid',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 2),
              Text(
                '확정 입력 음식 $foodCount개, 영양제 $supplementCount개',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _PrimaryAction extends StatelessWidget {
  const _PrimaryAction({
    required this.onFoodTap,
    required this.onSupplementTap,
  });

  final VoidCallback onFoodTap;
  final VoidCallback onSupplementTap;

  @override
  Widget build(BuildContext context) {
    return LemonCard(
      color: LemonColors.lemonSoft,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(Icons.add_a_photo_rounded, color: LemonColors.ink),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '오늘 기록',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: <Widget>[
              Expanded(
                child: FilledButton.icon(
                  onPressed: onFoodTap,
                  icon: const Icon(Icons.restaurant_menu_rounded),
                  label: const Text('음식'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: onSupplementTap,
                  icon: const Icon(Icons.medication_rounded),
                  label: const Text('영양제'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _CoachingCard extends StatelessWidget {
  const _CoachingCard({
    required this.foodCount,
    required this.supplementCount,
    required this.onTap,
  });

  final int foodCount;
  final int supplementCount;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final bool hasConfirmedInput = foodCount + supplementCount > 0;

    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: LemonCard(
        child: Row(
          children: <Widget>[
            DecoratedBox(
              decoration: BoxDecoration(
                color: hasConfirmedInput
                    ? LemonColors.leafSoft
                    : LemonColors.skySoft,
                borderRadius: BorderRadius.circular(8),
              ),
              child: SizedBox(
                width: 48,
                height: 48,
                child: Icon(
                  hasConfirmedInput
                      ? Icons.psychology_alt_rounded
                      : Icons.fact_check_outlined,
                  color: hasConfirmedInput ? LemonColors.leaf : LemonColors.sky,
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Daily coaching',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    hasConfirmedInput
                        ? '확정 입력을 바탕으로 개인화 코칭을 요청할 수 있어요.'
                        : '음식이나 영양제를 확정하면 코칭 근거로 사용할 수 있어요.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded),
          ],
        ),
      ),
    );
  }
}

class _ChatCard extends StatelessWidget {
  const _ChatCard({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: LemonCard(
        child: Row(
          children: <Widget>[
            DecoratedBox(
              decoration: BoxDecoration(
                color: LemonColors.skySoft,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const SizedBox(
                width: 48,
                height: 48,
                child: Icon(
                  Icons.chat_bubble_outline_rounded,
                  color: LemonColors.sky,
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    '챗봇',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '확정한 기록과 최근 코칭 요약을 기준으로 질문할 수 있어요.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded),
          ],
        ),
      ),
    );
  }
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: LemonCard(
        child: Row(
          children: <Widget>[
            DecoratedBox(
              decoration: BoxDecoration(
                color: LemonColors.warningSoft,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const SizedBox(
                width: 48,
                height: 48,
                child: Icon(
                  Icons.notifications_active_rounded,
                  color: LemonColors.warning,
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    '알림 설정',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '영양제, 식사 확인, 코칭 알림 시간을 설정할 수 있어요.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded),
          ],
        ),
      ),
    );
  }
}

class _ActivityCard extends StatelessWidget {
  const _ActivityCard({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: LemonCard(
        child: Row(
          children: <Widget>[
            DecoratedBox(
              decoration: BoxDecoration(
                color: LemonColors.leafSoft,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const SizedBox(
                width: 48,
                height: 48,
                child: Icon(
                  Icons.directions_walk_rounded,
                  color: LemonColors.leaf,
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    '활동 기록',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '수동으로 확인한 걸음수와 활동 시간을 코칭 근거에 추가할 수 있어요.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded),
          ],
        ),
      ),
    );
  }
}

class _EvidenceGrid extends StatelessWidget {
  const _EvidenceGrid({required this.foodCount, required this.supplementCount});

  final int foodCount;
  final int supplementCount;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Expanded(
          child: _MetricTile(
            icon: Icons.restaurant_rounded,
            label: '음식',
            value: '$foodCount',
            color: LemonColors.leaf,
            backgroundColor: LemonColors.leafSoft,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _MetricTile(
            icon: Icons.medication_liquid_rounded,
            label: '영양제',
            value: '$supplementCount',
            color: LemonColors.warning,
            backgroundColor: LemonColors.warningSoft,
          ),
        ),
      ],
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
    required this.backgroundColor,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;
  final Color backgroundColor;

  @override
  Widget build(BuildContext context) {
    return LemonCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          LemonPill(
            label: label,
            color: color,
            backgroundColor: backgroundColor,
          ),
          const SizedBox(height: 14),
          Row(
            children: <Widget>[
              Icon(icon, color: color),
              const Spacer(),
              Text(value, style: Theme.of(context).textTheme.headlineSmall),
            ],
          ),
        ],
      ),
    );
  }
}
