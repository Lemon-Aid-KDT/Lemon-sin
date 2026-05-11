// screens/health_screen.dart — D1 셸
//
// 참조: PROJECT_GUIDE.md §9.3 건강 데이터 연동 (HealthKit / Health Connect)

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../utils/router.dart';
import '../utils/tokens.dart';

class HealthScreen extends StatelessWidget {
  const HealthScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('건강 데이터')),
      body: const Center(
            child: Padding(
              padding: EdgeInsets.all(LemonSpace.lg),
              child: Text('걸음수·체중·심박 시계열 차트', style: LemonText.body),
            ),
          ),
    );
  }

}
