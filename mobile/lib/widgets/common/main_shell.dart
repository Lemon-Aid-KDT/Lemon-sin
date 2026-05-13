// widgets/common/main_shell.dart — 메인 5 탭 BottomNav 셸
//
// 참조: mobile/CLAUDE.md §4.2 메인 5 탭 / §6.3 만들 것
// 사용자와 함께 디자인 결정 진행 중 — 마지막 디자인 협의 시점에 다시 손볼 것.
//
// 가안 (확정 아님 — 사용자와 같이 결정 중):
//   탭 — 홈 / 카메라 / 챗 / 점수 / 설정
//   카메라는 일반 탭 (중앙 FAB 가설 보류)
//   5 페이지 상태 보존 — StatefulShellRoute.indexedStack 이 자동 처리
//
// 화면 코드는 각 screens/*.dart 가 담당. 셸은 BottomNav + navigationShell 위임만.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../../utils/design_tokens_v2.dart';

class MainShell extends StatefulWidget {
  /// go_router 의 StatefulShellRoute.indexedStack 가 주입.
  /// 5 branch 상태를 자동으로 IndexedStack 으로 보존해 줌.
  final StatefulNavigationShell navigationShell;

  const MainShell({super.key, required this.navigationShell});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  static const List<_TabSpec> _tabs = <_TabSpec>[
    _TabSpec(icon: Icons.home_rounded, label: '홈'),
    _TabSpec(icon: Icons.photo_camera_rounded, label: '카메라'),
    _TabSpec(icon: Icons.chat_bubble_rounded, label: '챗'),
    _TabSpec(icon: Icons.emoji_events_rounded, label: '점수'),
    _TabSpec(icon: Icons.settings_rounded, label: '설정'),
  ];

  void _onTap(int i) {
    HapticFeedback.selectionClick();
    // 같은 탭 재탭 시 해당 branch 의 첫 라우트로 복귀.
    widget.navigationShell.goBranch(
      i,
      initialLocation: i == widget.navigationShell.currentIndex,
    );
  }

  @override
  Widget build(BuildContext context) {
    final int currentIndex = widget.navigationShell.currentIndex;
    return Scaffold(
      backgroundColor: AppColor.bg,
      body: widget.navigationShell,
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: AppColor.surface,
          border: Border(
            top: BorderSide(color: AppColor.border, width: 1),
          ),
        ),
        child: SafeArea(
          top: false,
          child: SizedBox(
            height: 64,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: <Widget>[
                for (int i = 0; i < _tabs.length; i++)
                  Expanded(
                    child: _TabButton(
                      spec: _tabs[i],
                      active: i == currentIndex,
                      onTap: () => _onTap(i),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TabSpec {
  final IconData icon;
  final String label;
  const _TabSpec({required this.icon, required this.label});
}

class _TabButton extends StatelessWidget {
  final _TabSpec spec;
  final bool active;
  final VoidCallback onTap;

  const _TabButton({
    required this.spec,
    required this.active,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final Color color = active ? AppColor.brand : AppColor.inkTertiary;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpace.sm),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Icon(spec.icon, size: 24, color: color),
              const SizedBox(height: AppSpace.xs),
              Text(
                spec.label,
                style: AppText.micro.copyWith(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: color,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
