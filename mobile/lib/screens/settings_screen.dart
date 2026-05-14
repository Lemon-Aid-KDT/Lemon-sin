// screens/settings_screen.dart — 설정 (로그아웃만 우선 동작)
//
// 참조: PROJECT_GUIDE.md §3.5 설정 화면 / §20.5 데이터 주체 5권리
// 다른 항목은 추후 구현 — 지금은 로그아웃만 진짜 동작.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/auth_provider.dart';
import '../utils/design_tokens_v2.dart';
import '../widgets/common/app_modals.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: AppColor.bg,
      appBar: AppBar(
        title: const Text('설정'),
        backgroundColor: AppColor.bg,
        elevation: 0,
      ),
      body: ListView(
        children: [
          _SectionLabel('계정'),
          _SettingsTile(label: '내 정보', enabled: false),
          _SettingsTile(label: '동의 관리', enabled: false),
          _SettingsTile(label: '알림 설정', enabled: false),
          _SettingsTile(label: '데이터 내보내기', enabled: false),
          const SizedBox(height: AppSpace.sm),
          const Divider(height: 1, color: AppColor.border),
          _SettingsTile(
            label: '로그아웃',
            onTap: () => _confirmLogout(context, ref),
          ),
          _SettingsTile(label: '계정 탈퇴', enabled: false, danger: true),
          const Divider(height: 1, color: AppColor.border),
          _SettingsTile(
            label: '서비스 정보',
            subtitle: '의료법 · 약사법 · 면책 고지',
            enabled: false,
          ),
        ],
      ),
    );
  }

  Future<void> _confirmLogout(BuildContext context, WidgetRef ref) async {
    final stay = await showAppDialog(
      context,
      title: '로그아웃할까요?',
      body: '다음 로그인 때 이메일 / 비밀번호를 다시 입력해야 해요.',
      primaryLabel: '머무르기',
      secondaryLabel: '로그아웃',
      dangerSecondary: true,
    );
    // stay == false (Secondary 누름) 이면 로그아웃
    if (stay == false) {
      await ref.read(authControllerProvider.notifier).logout();
      // 라우터 가드가 자동으로 /login 으로 보냄
    }
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);
  final String text;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(AppSpace.xl, AppSpace.lg, AppSpace.xl, AppSpace.xs),
      child: Text(
        text,
        style: AppText.caption.copyWith(
          color: AppColor.inkTertiary,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({
    required this.label,
    this.subtitle,
    this.onTap,
    this.enabled = true,
    this.danger = false,
  });

  final String label;
  final String? subtitle;
  final VoidCallback? onTap;
  final bool enabled;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final color = !enabled
        ? AppColor.inkTertiary
        : danger
            ? AppColor.danger
            : AppColor.ink;
    return ListTile(
      onTap: enabled ? onTap : null,
      title: Text(
        label,
        style: AppText.body.copyWith(
          color: color,
          fontWeight: FontWeight.w500,
        ),
      ),
      subtitle: subtitle != null
          ? Text(subtitle!, style: AppText.caption.copyWith(color: AppColor.inkTertiary))
          : null,
      trailing: enabled
          ? const Icon(Icons.chevron_right, color: AppColor.inkTertiary, size: 20)
          : null,
    );
  }
}
