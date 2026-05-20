// screens/notifications_screen.dart — 알림 리스트 (LADS v2)
//
// 디자인:
//   - 상단 흰 헤더 (뒤로 + "알림")
//   - 본문: 오늘 / 이번 주 / 이전 그룹
//   - 항목: 아이콘 칩 + 제목 + 설명 + 시간 + (안 읽음 dot)
//   - 항목 탭 → 관련 화면으로 (mock)

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../utils/design_tokens_v2.dart';

class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.section,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _Header(),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(
                  AppSpace.page, AppSpace.md,
                  AppSpace.page, AppSpace.xl,
                ),
                children: [
                  _GroupLabel('오늘'),
                  _NotifGroup(items: const [
                    _NotifItem(
                      icon: Icons.medication_rounded,
                      color: AppColor.brand,
                      title: '비타민 D 복용 시간',
                      sub: '오전 9시 복용을 잊지 마세요',
                      time: '3시간 전',
                      unread: true,
                    ),
                    _NotifItem(
                      icon: Icons.workspace_premium_rounded,
                      color: Color(0xFFFFB200),
                      title: '어제 식단 점수가 나왔어요',
                      sub: '78점 · 비타민이 부족했어요',
                      time: '6시간 전',
                      unread: true,
                    ),
                  ]),
                  const SizedBox(height: AppSpace.lg),
                  _GroupLabel('이번 주'),
                  _NotifGroup(items: const [
                    _NotifItem(
                      icon: Icons.auto_awesome_rounded,
                      color: Color(0xFF22B07D),
                      title: '주간 평가 리포트 도착',
                      sub: '이번 주 평균 78점 · 지난 주 대비 +3',
                      time: '2일 전',
                    ),
                    _NotifItem(
                      icon: Icons.flag_rounded,
                      color: Color(0xFF4D7BFF),
                      title: '당뇨 목적 알림',
                      sub: '저녁 GI 지수가 높았어요',
                      time: '3일 전',
                    ),
                  ]),
                  const SizedBox(height: AppSpace.lg),
                  _GroupLabel('이전'),
                  _NotifGroup(items: const [
                    _NotifItem(
                      icon: Icons.celebration_rounded,
                      color: Color(0xFFFF6B6B),
                      title: '레몬에이드 가입을 환영해요',
                      sub: '약관에 동의해주셔서 감사해요',
                      time: '12일 전',
                    ),
                  ]),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColor.section,
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.sm, AppSpace.page, AppSpace.sm,
      ),
      child: Row(
        children: [
          GestureDetector(
            onTap: () => context.canPop()
                ? context.pop()
                : context.go('/shell/home'),
            child: Container(
              width: 40, height: 40,
              alignment: Alignment.center,
              child: const Icon(Icons.arrow_back_rounded,
                  color: AppColor.ink, size: 22),
            ),
          ),
          const Spacer(),
          const Text(
            '알림',
            style: TextStyle(
              color: AppColor.ink,
              fontSize: 16,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.3,
            ),
          ),
          const Spacer(),
          GestureDetector(
            onTap: () {},
            child: Container(
              width: 40, height: 40,
              alignment: Alignment.center,
              child: const Icon(Icons.checklist_rounded,
                  color: AppColor.inkSecondary, size: 22),
            ),
          ),
        ],
      ),
    );
  }
}

class _GroupLabel extends StatelessWidget {
  final String text;
  const _GroupLabel(this.text);
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

class _NotifGroup extends StatelessWidget {
  final List<Widget> items;
  const _NotifGroup({required this.items});
  @override
  Widget build(BuildContext context) {
    final sep = <Widget>[];
    for (int i = 0; i < items.length; i++) {
      sep.add(items[i]);
      if (i < items.length - 1) {
        sep.add(const Divider(
          height: 1, thickness: 1,
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
      child: Column(children: sep),
    );
  }
}

class _NotifItem extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final String sub;
  final String time;
  final bool unread;
  const _NotifItem({
    required this.icon,
    required this.color,
    required this.title,
    required this.sub,
    required this.time,
    this.unread = false,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () {},
      borderRadius: BorderRadius.circular(AppRadius.lg),
      child: Padding(
        padding: const EdgeInsets.all(AppSpace.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                color: color.withOpacity(0.14),
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              alignment: Alignment.center,
              child: Icon(icon, color: color, size: 20),
            ),
            const SizedBox(width: AppSpace.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          title,
                          style: const TextStyle(
                            color: AppColor.ink,
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.2,
                          ),
                        ),
                      ),
                      if (unread)
                        Container(
                          width: 8, height: 8,
                          margin: const EdgeInsets.only(left: 6),
                          decoration: const BoxDecoration(
                            color: AppColor.brand,
                            shape: BoxShape.circle,
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    sub,
                    style: const TextStyle(
                      color: AppColor.inkSecondary,
                      fontSize: 12.5,
                      fontWeight: FontWeight.w500,
                      height: 1.45,
                      letterSpacing: -0.2,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    time,
                    style: const TextStyle(
                      color: AppColor.inkTertiary,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
