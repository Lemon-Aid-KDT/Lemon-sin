// screens/settings_screen.dart — 설정 + 마이페이지 (LADS v2)
//
// 디자인:
//   - 상단 brand 헤더 + 프로필 카드 (오버랩)
//   - 본문 라운드 (Pillyze 톤)
//   - 섹션: 내 건강 / 알림 / 계정 / 안내
//   - 로그아웃은 진짜 동작, 나머지는 라우트 push (구현 단계별)

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../utils/design_tokens_v2.dart';
import '../widgets/common/app_modals.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: AppColor.section,
      body: Column(
        children: [
          const _ProfileHeader(),
          Expanded(
            child: Transform.translate(
              offset: const Offset(0, -36),
              child: Container(
                decoration: const BoxDecoration(
                  color: AppColor.section,
                  borderRadius: BorderRadius.only(
                    topLeft: Radius.circular(28),
                    topRight: Radius.circular(28),
                  ),
                ),
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(
                    AppSpace.page, AppSpace.lg,
                    AppSpace.page, AppSpace.xl + 80,
                  ),
                  children: [
                    _SectionLabel('내 건강'),
                    _SettingsGroup(children: [
                      _SettingsTile(
                        icon: Icons.medical_services_rounded,
                        iconColor: const Color(0xFF22B07D),
                        label: '만성질환·복약 정보',
                        sub: '복약 교차 점검에 쓰여요',
                        onTap: () =>
                            context.push('/shell/settings/health-profile'),
                      ),
                      _SettingsTile(
                        icon: Icons.flag_rounded,
                        iconColor: const Color(0xFF4D7BFF),
                        label: '관심 목적',
                        sub: '당뇨 · 혈압 · 체중 관리',
                        onTap: () => context.push(
                            '/shell/settings/health-profile?tab=goal'),
                      ),
                      _SettingsTile(
                        icon: Icons.straighten_rounded,
                        iconColor: const Color(0xFFFF9500),
                        label: '신체 정보',
                        sub: '키·몸무게·성별·나이',
                        onTap: () => context.push(
                            '/shell/settings/health-profile?tab=body'),
                      ),
                    ]),

                    const SizedBox(height: AppSpace.lg),
                    _SectionLabel('알림'),
                    _SettingsGroup(children: [
                      _SettingsTile(
                        icon: Icons.notifications_rounded,
                        iconColor: AppColor.brand,
                        label: '알림 설정',
                        sub: '복약 시간 · 평가 리포트',
                        onTap: () {},
                      ),
                    ]),

                    const SizedBox(height: AppSpace.lg),
                    _SectionLabel('계정'),
                    _SettingsGroup(children: [
                      _SettingsTile(
                        icon: Icons.person_rounded,
                        iconColor: AppColor.inkSecondary,
                        label: '내 정보',
                        onTap: () {},
                      ),
                      _SettingsTile(
                        icon: Icons.privacy_tip_rounded,
                        iconColor: AppColor.inkSecondary,
                        label: '동의 관리',
                        onTap: () {},
                      ),
                      _SettingsTile(
                        icon: Icons.download_rounded,
                        iconColor: AppColor.inkSecondary,
                        label: '데이터 내보내기',
                        onTap: () {},
                      ),
                    ]),

                    const SizedBox(height: AppSpace.lg),
                    _SectionLabel('안내'),
                    _SettingsGroup(children: [
                      _SettingsTile(
                        icon: Icons.info_outline_rounded,
                        iconColor: AppColor.inkSecondary,
                        label: '서비스 정보',
                        sub: '의료법 · 약사법 · 면책 고지',
                        onTap: () {},
                      ),
                      _SettingsTile(
                        icon: Icons.help_outline_rounded,
                        iconColor: AppColor.inkSecondary,
                        label: '도움말 / 문의',
                        onTap: () {},
                      ),
                    ]),

                    const SizedBox(height: AppSpace.lg),
                    _SettingsGroup(children: [
                      _SettingsTile(
                        icon: Icons.logout_rounded,
                        iconColor: AppColor.danger,
                        label: '로그아웃',
                        labelColor: AppColor.danger,
                        onTap: () => _confirmLogout(context, ref),
                      ),
                    ]),

                    const SizedBox(height: AppSpace.lg),
                    Center(
                      child: Text(
                        'v0.1.0 · Lemon Aid',
                        style: AppText.caption.copyWith(
                          color: AppColor.inkTertiary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
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
    if (stay == false) {
      await ref.read(authControllerProvider.notifier).logout();
    }
  }
}

// ═══════════════════════════════════════════
// 프로필 헤더 (brand BG + 카드)
// ═══════════════════════════════════════════
class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColor.brand,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.page, AppSpace.lg, AppSpace.page, AppSpace.xl + AppSpace.xl,
          ),
          child: Row(
            children: [
              Container(
                width: 64, height: 64,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.5),
                  shape: BoxShape.circle,
                ),
                alignment: Alignment.center,
                child: const Icon(Icons.person_rounded,
                    color: AppColor.ink, size: 32),
              ),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text(
                      '태동님',
                      style: TextStyle(
                        color: AppColor.ink,
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.5,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      '레몬에이드와 함께한 지 12일',
                      style: TextStyle(
                        color: AppColor.ink,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.2,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                width: 36, height: 36,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.4),
                  shape: BoxShape.circle,
                ),
                alignment: Alignment.center,
                child: const Icon(Icons.edit_rounded,
                    color: AppColor.ink, size: 18),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);
  final String text;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 0, 4, AppSpace.sm),
      child: Text(
        text,
        style: const TextStyle(
          color: AppColor.inkTertiary,
          fontSize: 12,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.2,
        ),
      ),
    );
  }
}

class _SettingsGroup extends StatelessWidget {
  final List<Widget> children;
  const _SettingsGroup({required this.children});

  @override
  Widget build(BuildContext context) {
    final separated = <Widget>[];
    for (int i = 0; i < children.length; i++) {
      separated.add(children[i]);
      if (i < children.length - 1) {
        separated.add(const Divider(
          height: 1,
          thickness: 1,
          color: AppColor.border,
          indent: 60,
        ));
      }
    }
    return Container(
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.14),
            blurRadius: 12,
            offset: Offset(0, 3),
          ),
        ],
      ),
      child: Column(children: separated),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String label;
  final String? sub;
  final Color? labelColor;
  final VoidCallback onTap;
  const _SettingsTile({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.onTap,
    this.sub,
    this.labelColor,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpace.md, AppSpace.md, AppSpace.md, AppSpace.md,
        ),
        child: Row(
          children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                color: iconColor.withOpacity(0.12),
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              alignment: Alignment.center,
              child: Icon(icon, color: iconColor, size: 20),
            ),
            const SizedBox(width: AppSpace.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(
                      color: labelColor ?? AppColor.ink,
                      fontSize: 14.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.2,
                    ),
                  ),
                  if (sub != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      sub!,
                      style: const TextStyle(
                        color: AppColor.inkTertiary,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded,
                color: AppColor.inkTertiary, size: 20),
          ],
        ),
      ),
    );
  }
}
