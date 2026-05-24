// utils/page_transitions.dart — 화면 전환 애니메이션 (현업 톤)
//
// CLAUDE.md §7-8 모션 룰:
//   모든 화면 전환은 즉각 교체 금지. 페이드+슬라이드 (iOS/토스 톤).
//
// 사용:
//   GoRoute(
//     pageBuilder: (ctx, st) => slidePage(st, const SomeScreen()),
//   )

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

const Duration _kDur = Duration(milliseconds: 340);
const Duration _kRevDur = Duration(milliseconds: 280);

/// 기본 화면 전환 — 우→좌 슬라이드 + 페이드 (iOS push 톤).
/// 일반 화면 진입(대시보드 ↔ 상세 등)에 사용.
CustomTransitionPage<void> slidePage(GoRouterState state, Widget child) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    transitionDuration: _kDur,
    reverseTransitionDuration: _kRevDur,
    child: child,
    transitionsBuilder: (ctx, anim, secondary, child) {
      final slide = Tween<Offset>(
        begin: const Offset(0.06, 0),
        end: Offset.zero,
      ).animate(CurvedAnimation(parent: anim, curve: Curves.easeOutQuart));
      return FadeTransition(
        opacity: CurvedAnimation(parent: anim, curve: Curves.easeOutQuart),
        child: SlideTransition(position: slide, child: child),
      );
    },
  );
}

/// 모달성 전환 — 아래→위 슬라이드 + 페이드.
/// 카메라·분석결과·시트성 화면에 사용.
CustomTransitionPage<void> modalPage(GoRouterState state, Widget child) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    transitionDuration: _kDur,
    reverseTransitionDuration: _kRevDur,
    child: child,
    transitionsBuilder: (ctx, anim, secondary, child) {
      final slide = Tween<Offset>(
        begin: const Offset(0, 0.06),
        end: Offset.zero,
      ).animate(CurvedAnimation(parent: anim, curve: Curves.easeOutQuart));
      return FadeTransition(
        opacity: CurvedAnimation(parent: anim, curve: Curves.easeOutQuart),
        child: SlideTransition(position: slide, child: child),
      );
    },
  );
}

/// 페이드만 — 스플래시·로그인 등 방향성 없는 전환.
CustomTransitionPage<void> fadePage(GoRouterState state, Widget child) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    transitionDuration: _kDur,
    reverseTransitionDuration: _kRevDur,
    child: child,
    transitionsBuilder: (ctx, anim, secondary, child) {
      return FadeTransition(
        opacity: CurvedAnimation(parent: anim, curve: Curves.easeOutQuart),
        child: child,
      );
    },
  );
}
