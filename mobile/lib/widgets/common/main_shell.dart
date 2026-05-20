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
  // Pillyze 톤 — 둥글둥글 + 채워진(filled) 무게감 있는 픽토그램.
  // 활성/비활성 둘 다 filled 사용, 색만 다름 (시각 무게 일관)
  static const List<_TabSpec> _leftTabs = <_TabSpec>[
    _TabSpec(
      branchIndex: 0,
      iconOutline: Icons.favorite_rounded,
      iconFilled: Icons.favorite_rounded,
      label: '홈',
    ),
    _TabSpec(
      branchIndex: 2,
      iconOutline: Icons.chat_bubble_rounded,
      iconFilled: Icons.chat_bubble_rounded,
      label: '챗',
    ),
  ];
  static const List<_TabSpec> _rightTabs = <_TabSpec>[
    _TabSpec(
      branchIndex: 3,
      iconOutline: Icons.workspace_premium_rounded,
      iconFilled: Icons.workspace_premium_rounded,
      label: '점수',
    ),
    _TabSpec(
      branchIndex: 4,
      iconOutline: Icons.settings_rounded,
      iconFilled: Icons.settings_rounded,
      label: '설정',
    ),
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
    // 카메라 branch 일 때는 풀스크린 — 탭바 + 배경 검정으로
    final bool isCamera = currentIndex == _cameraBranchIndex;
    return Scaffold(
      backgroundColor: isCamera ? Colors.black : AppColor.bg,
      // extendBody = 카메라 모드일 때 body 가 시스템 영역까지 확장
      extendBody: isCamera,
      body: widget.navigationShell,
      bottomNavigationBar: isCamera
          ? null
          : _BottomBar(
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
        // Pillyze 시안: 상단에 매우 옅은 1px 구분선 + soft shadow
        border: Border(
          top: BorderSide(color: Color(0xFFF1F3F6), width: 1),
        ),
        boxShadow: [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.06),
            blurRadius: 16,
            offset: Offset(0, -2),
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
              Row(
                children: [
                  for (final t in leftTabs)
                    Expanded(
                      child: _TabItem(
                        spec: t,
                        active: t.branchIndex == currentIndex,
                        onTap: () => onTabTap(t.branchIndex),
                      ),
                    ),
                  // 중앙 공간 (FAB 자리)
                  const Expanded(child: SizedBox.shrink()),
                  for (final t in rightTabs)
                    Expanded(
                      child: _TabItem(
                        spec: t,
                        active: t.branchIndex == currentIndex,
                        onTap: () => onTabTap(t.branchIndex),
                      ),
                    ),
                ],
              ),
              // 중앙 카메라 FAB — 탭바 위로 20dp 떠있음 (64px 크기 비율)
              Positioned(
                top: -20,
                child: _CameraFab(
                  active: cameraActive,
                  onTap: onCameraTap,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TabItem extends StatelessWidget {
  final _TabSpec spec;
  final bool active;
  final VoidCallback onTap;
  const _TabItem({required this.spec, required this.active, required this.onTap});

  @override
  Widget build(BuildContext context) {
    // 포커스: brand 비비드 노랑
    // 비활성: 옅은 그레이지 (#C5CBD6) — 너무 회색이면 묻히고, 너무 진하면 활성과 안 구분
    const inactive = Color(0xFFC5CBD6);
    final iconColor = active ? AppColor.brand : inactive;
    // 라벨은 활성 시 ink(검정), 비활성은 한 톤 위 (#8A92A5 = inkTertiary)
    final labelColor = active ? AppColor.ink : AppColor.inkTertiary;
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpace.sm),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // 아이콘 — Pillyze 처럼 둥글둥글, 활성 시 더 큰 사이즈로 강조
            AnimatedSize(
              duration: const Duration(milliseconds: 180),
              curve: Curves.easeOutCubic,
              child: Icon(
                active ? spec.iconFilled : spec.iconOutline,
                size: active ? 26 : 24,
                color: iconColor,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              spec.label,
              style: AppText.micro.copyWith(
                fontSize: 11,
                fontWeight: active ? FontWeight.w700 : FontWeight.w500,
                color: labelColor,
                letterSpacing: -0.2,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CameraFab extends StatelessWidget {
  final bool active;
  final VoidCallback onTap;
  const _CameraFab({required this.active, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOutCubic,
        width: 64,
        height: 64,
        decoration: BoxDecoration(
          // 위→아래 살짝 그라데이션 (밝은 노랑 → 살짝 더 진한 노랑)
          gradient: const LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0xFFFFD43A),   // 위: brand 보다 한 톤 밝게
              AppColor.brand,      // 아래: #FFC700
            ],
          ),
          shape: BoxShape.circle,
          boxShadow: [
            // brand 색 hue 그림자 — Pillyze 처럼 색상 잔향
            BoxShadow(
              color: AppColor.brand.withOpacity(active ? 0.50 : 0.35),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
            // 미세 검정 — 깊이감
            const BoxShadow(
              color: Color.fromRGBO(0, 0, 0, 0.10),
              blurRadius: 6,
              offset: Offset(0, 3),
            ),
          ],
        ),
        alignment: Alignment.center,
        // 굵은 + 기호 (Pillyze 시안 그대로)
        child: const Icon(
          Icons.add_rounded,
          color: AppColor.ink,
          size: 32,
          weight: 700,
        ),
      ),
    );
  }
}
