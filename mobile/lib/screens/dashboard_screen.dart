// screens/dashboard_screen.dart — D1 셸
//
// 참조: PROJECT_GUIDE.md §3.5 주요 화면 / §8 5종 출력

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../utils/router.dart';
import '../utils/tokens.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('오늘의 건강')),
      body: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: const [
                // TODO(B): 5종 출력 카드 (§3.5)
                // 1. 부족 영양소 추천
                // 2. 권장 섭취량 (KDRIs)
                // 3. 체중 예측
                // 4. 활동 권고 (v4)
                // 5. 목적별 분석 (눈/간/피로)
                Padding(
                  padding: EdgeInsets.all(LemonSpace.lg),
                  child: Text('5종 출력 대시보드 (구현 예정)', style: LemonText.body),
                ),
              ],
            ),
          ),
      floatingActionButton: FloatingActionButton.extended(
            onPressed: () => context.push(AppRoute.camera),
            backgroundColor: LemonColors.brand,
            foregroundColor: Colors.white,
            label: const Text('카메라'),
            icon: const Icon(Icons.photo_camera),
          ),
    );
  }

}
