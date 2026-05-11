// widgets/error_view.dart — D1 셸
//
// 담당: B UI/UX
// 참조: 에러 화면 정책 (§3.10)

import 'package:flutter/material.dart';

import '../utils/tokens.dart';

class ErrorView extends StatelessWidget {
  const ErrorView({super.key});

  @override
  Widget build(BuildContext context) {
    return const Placeholder(
      fallbackHeight: 80,
      color: LemonColors.brand,
    );
  }
}
