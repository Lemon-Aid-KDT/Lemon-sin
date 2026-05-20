import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/widgets/medical_disclaimer.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Lemon Aid')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: <Widget>[
          Text(
            'Today',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 16),
          _DashboardAction(
            title: 'Daily coaching',
            subtitle: 'Run AI Agent coaching with confirmed meal data.',
            icon: Icons.chat_bubble_outline,
            onTap: () => context.go('/coaching'),
          ),
          const SizedBox(height: 12),
          _DashboardAction(
            title: 'Food input',
            subtitle: 'Capture a food photo and confirm the meal details manually.',
            icon: Icons.restaurant_outlined,
            onTap: () => context.go('/food-capture'),
          ),
          const SizedBox(height: 12),
          _DashboardAction(
            title: 'Supplement capture',
            subtitle: 'Capture or select a supplement label image.',
            icon: Icons.photo_camera_outlined,
            onTap: () => context.go('/supplement-capture'),
          ),
          const SizedBox(height: 24),
          const MedicalDisclaimer(),
        ],
      ),
    );
  }
}

class _DashboardAction extends StatelessWidget {
  const _DashboardAction({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(icon),
        title: Text(title),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
