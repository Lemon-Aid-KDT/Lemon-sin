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
            '오늘의 건강 관리',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 16),
          _DashboardAction(
            title: '식단 코칭',
            subtitle: '확인된 식단 기록으로 AI Agent 코칭을 요청합니다.',
            icon: Icons.chat_bubble_outline,
            onTap: () => context.go('/coaching'),
          ),
          const SizedBox(height: 12),
          _DashboardAction(
            title: '영양제 촬영',
            subtitle: '카메라 또는 갤러리에서 라벨 이미지를 선택합니다.',
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
