import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/theme/lemon_theme.dart';
import '../../../shared/widgets/medical_disclaimer.dart';

class CaptureResultScreen extends StatelessWidget {
  const CaptureResultScreen({
    super.key,
    required this.type,
    required this.title,
    required this.subtitle,
    required this.details,
  });

  final String type;
  final String title;
  final String subtitle;
  final List<String> details;

  @override
  Widget build(BuildContext context) {
    final bool isFood = type == 'food';
    final Color accent = isFood ? LemonColors.leaf : LemonColors.warning;
    final Color accentSoft =
        isFood ? LemonColors.leafSoft : LemonColors.warningSoft;
    final IconData icon = isFood
        ? Icons.restaurant_menu_rounded
        : Icons.medication_liquid_rounded;

    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 28),
          children: <Widget>[
            Row(
              children: <Widget>[
                IconButton(
                  onPressed: () => context.go('/'),
                  icon: const Icon(Icons.close_rounded),
                ),
                Expanded(
                  child: Text(
                    '확정 완료',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            LemonCard(
              color: accentSoft,
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  DecoratedBox(
                    decoration: BoxDecoration(
                      color: LemonColors.paper,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: SizedBox(
                      width: 54,
                      height: 54,
                      child: Icon(icon, color: accent, size: 30),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(title, style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 6),
                  Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
                ],
              ),
            ),
            const SizedBox(height: 16),
            LemonCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  if (details.isNotEmpty) ...<Widget>[
                    Text(
                      '확인한 내용',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 10),
                    for (final String detail in details)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Icon(
                              Icons.check_circle_rounded,
                              color: accent,
                              size: 20,
                            ),
                            const SizedBox(width: 8),
                            Expanded(child: Text(detail)),
                          ],
                        ),
                      ),
                    const SizedBox(height: 10),
                  ],
                  Text('다음 단계', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 10),
                  Text(
                    '방금 확정한 기록은 앱 세션의 confirmed entry로 보관되며, Daily coaching 요청에만 근거로 포함됩니다.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 14),
                  FilledButton.icon(
                    onPressed: () => context.go('/coaching'),
                    icon: const Icon(Icons.auto_awesome_rounded),
                    label: const Text('코칭으로 이동'),
                  ),
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    onPressed: () => context.go(
                      isFood ? '/food-capture' : '/supplement-capture',
                    ),
                    icon: const Icon(Icons.add_rounded),
                    label: Text(isFood ? '음식 더 기록' : '영양제 더 기록'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            const MedicalDisclaimer(),
          ],
        ),
      ),
    );
  }
}
