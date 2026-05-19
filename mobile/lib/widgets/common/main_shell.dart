// widgets/common/main_shell.dart — 메인 5 탭 BottomNav 셸
//
// 디자인 (Pillyze 시안 기반, LADS 톤으로 변환):
//   - 5 탭: 홈 / 챗 / [중앙 카메라 FAB] / 점수 / 설정
//   - 중앙 카메라 = 큰 brand 원형 FAB (탭바 위로 16dp 떠있음)
//   - 활성 탭 = brand 아이콘 + 아래 작은 dot (•)
//   - 비활성 = inkTertiary outline 아이콘
//   - 배경 흰색, 상단 border 없음, 옅은 soft shadow 만
//   - 5 페이지 상태 보존 — StatefulShellRoute.indexedStack 자동 처리

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../../utils/design_tokens_v2.dart';

class MainShell extends StatefulWidget {
  final StatefulNavigationShell navigationShell;
  const MainShell({super.key, required this.navigationShell});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  // 카메라(인덱스 1)는 중앙 FAB. 일반 탭 4개 + 중앙 1개.
  // 라우터 branch 순서: home(0) / camera(1) / chat(2) / score(3) / settings(4)
  // 탭바 시각 순서: home, chat, [camera FAB], score, settings
  static const List<_TabSpec> _leftTabs = <_TabSpec>[
    _TabSpec(branchIndex: 0, iconOutline: Icons.home_outlined, iconFilled: Icons.home_rounded, label: '홈'),
    _TabSpec(branchIndex: 2, iconOutline: Icons.chat_bubble_outline_rounded, iconFilled: Icons.chat_bubble_rounded, label: '챗'),
  ];
  static const List<_TabSpec> _rightTabs = <_TabSpec>[
    _TabSpec(branchIndex: 3, iconOutline: Icons.emoji_events_outlined, iconFilled: Icons.emoji_events_rounded, label: '점수'),
    _TabSpec(branchIndex: 4, iconOutline: Icons.settings_outlined, iconFilled: Icons.settings_rounded, label: '설정'),
  ];
  static const int _cameraBranchIndex = 1;

  void _goBranch(int branchIndex) {
    HapticFeedback.selectionClick();
    widget.navigationShell.goBranch(
      branchIndex,
      initialLocation: branchIndex == widget.navigationShell.currentIndex,
    );
  }

  @override
  Widget build(BuildContext context) {
    final int currentIndex = widget.navigationShell.currentIndex;
    return Scaffold(
      backgroundColor: AppColor.bg,
      body: widget.navigationShell,
      // FAB 가 탭바 위에 살짝 떠있는 구조 → Stack 으로 직접 조합
      bottomNavigationBar: _BottomBar(
        leftTabs: _leftTabs,
        rightTabs: _rightTabs,
        currentIndex: currentIndex,
        onTabTap: _goBranch,
        onCameraTap: () => _goBranch(_cameraBranchIndex),
        cameraActive: currentIndex == _cameraBranchIndex,
      ),
    );
  }
}

class _TabSpec {
  final int branchIndex;
  final IconData iconOutline;
  final IconData iconFilled;
  final String label;
  const _TabSpec({
    required this.branchIndex,
    required this.iconOutline,
    required this.iconFilled,
    required this.label,
  });
}

class _BottomBar extends StatelessWidget {
  final List<_TabSpec> leftTabs;
  final List<_TabSpec> rightTabs;
  final int currentIndex;
  final ValueChanged<int> onTabTap;
  final VoidCallback onCameraTap;
  final bool cameraActive;

  const _BottomBar({
    required this.leftTabs,
    required this.rightTabs,
    required this.currentIndex,
    required this.onTabTap,
    required this.onCameraTap,
    required this.cameraActive,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColor.surface,
        boxShadow: [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.10),
            blurRadius: 20,
            offset: Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 72,
          child: Stack(
            clipBehavior: Clip.none,
            alignment: Alignment.topCenter,
            children: [
              // 4 일반 탭 (좌 2 + 우 2) — Row 로 균등 분배
        