import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../theme/lemon_theme.dart';

class LemonMainShell extends StatelessWidget {
  const LemonMainShell({
    super.key,
    required this.child,
    required this.currentPath,
  });

  final Widget child;
  final String currentPath;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: child,
      bottomNavigationBar: _LemonBottomBar(
        currentPath: currentPath,
        onHomeTap: () => context.go('/'),
        onCoachingTap: () => context.go('/coaching'),
        onRecordTap: () => _showRecordSheet(context),
      ),
    );
  }

  void _showRecordSheet(BuildContext context) {
    HapticFeedback.selectionClick();
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: LemonColors.paper,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (BuildContext sheetContext) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: LemonColors.line,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
                const SizedBox(height: 14),
                _RecordTile(
                  icon: Icons.restaurant_menu_rounded,
                  title: '음식 기록',
                  subtitle: '사진과 직접 입력으로 확정 기록을 만듭니다.',
                  color: LemonColors.leaf,
                  backgroundColor: LemonColors.leafSoft,
                  onTap: () {
                    Navigator.of(sheetContext).pop();
                    context.go('/food-capture');
                  },
                ),
                const SizedBox(height: 8),
                _RecordTile(
                  icon: Icons.medication_liquid_rounded,
                  title: '영양제 기록',
                  subtitle: '라벨 preview를 확인한 뒤 저장합니다.',
                  color: LemonColors.warning,
                  backgroundColor: LemonColors.warningSoft,
                  onTap: () {
                    Navigator.of(sheetContext).pop();
                    context.go('/supplement-capture');
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _LemonBottomBar extends StatelessWidget {
  const _LemonBottomBar({
    required this.currentPath,
    required this.onHomeTap,
    required this.onCoachingTap,
    required this.onRecordTap,
  });

  final String currentPath;
  final VoidCallback onHomeTap;
  final VoidCallback onCoachingTap;
  final VoidCallback onRecordTap;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: LemonColors.paper,
        border: Border(top: BorderSide(color: LemonColors.line)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Color(0x14000000),
            blurRadius: 18,
            offset: Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 74,
          child: Stack(
            clipBehavior: Clip.none,
            alignment: Alignment.topCenter,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: _NavItem(
                      icon: Icons.favorite_rounded,
                      label: '홈',
                      active: currentPath == '/',
                      onTap: onHomeTap,
                    ),
                  ),
                  const Expanded(child: SizedBox.shrink()),
                  Expanded(
                    child: _NavItem(
                      icon: Icons.auto_awesome_rounded,
                      label: '코칭',
                      active: currentPath == '/coaching',
                      onTap: onCoachingTap,
                    ),
                  ),
                ],
              ),
              Positioned(
                top: -18,
                child: _RecordFab(onTap: onRecordTap),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.label,
    required this.active,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color color = active ? LemonColors.leaf : LemonColors.inkMuted;
    return InkWell(
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 10),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Icon(icon, color: color, size: active ? 27 : 24),
            const SizedBox(height: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: color,
                    fontWeight: active ? FontWeight.w800 : FontWeight.w600,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RecordFab extends StatelessWidget {
  const _RecordFab({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: const DecoratedBox(
        decoration: BoxDecoration(
          color: LemonColors.lemon,
          shape: BoxShape.circle,
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: Color(0x4DFFCE00),
              blurRadius: 18,
              offset: Offset(0, 8),
            ),
            BoxShadow(
              color: Color(0x1F000000),
              blurRadius: 8,
              offset: Offset(0, 4),
            ),
          ],
        ),
        child: SizedBox(
          width: 62,
          height: 62,
          child: Icon(Icons.add_rounded, color: LemonColors.ink, size: 34),
        ),
      ),
    );
  }
}

class _RecordTile extends StatelessWidget {
  const _RecordTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.backgroundColor,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final Color backgroundColor;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          children: <Widget>[
            DecoratedBox(
              decoration: BoxDecoration(
                color: backgroundColor,
                borderRadius: BorderRadius.circular(8),
              ),
              child: SizedBox(
                width: 48,
                height: 48,
                child: Icon(icon, color: color),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 2),
                  Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
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
