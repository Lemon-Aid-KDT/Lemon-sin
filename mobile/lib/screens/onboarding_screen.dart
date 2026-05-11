// screens/onboarding_screen.dart — D1 셸
//
// 참조: PROJECT_GUIDE.md §3.4 인증·온보딩 흐름 / §9.3 건강 데이터 연동

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../utils/router.dart';
import '../utils/tokens.dart';

class OnboardingScreen extends StatelessWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('내 정보 입력')),
      body: SingleChildScrollView(
            padding: const EdgeInsets.all(LemonSpace.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('기본 정보', style: LemonText.heading),
                const SizedBox(height: LemonSpace.md),
                const Text(
                  '맞춤 권고를 위해 알려주세요.',
                  style: LemonText.body,
                ),
                const SizedBox(height: LemonSpace.lg),

                // TODO(A): 나이·성별·키·몸무게 입력 필드
                // TODO(A): 만성질환 다중선택 (당뇨/고혈압/심혈관/관절/호흡기/없음)
                // TODO(A): 복약 입력
                // TODO(A): 목적 선택 (눈/간/피로/체중)
                // TODO(A): 건강 데이터 권한 요청 (health 패키지)
                // TODO(A): 알림 권한 요청

                ElevatedButton(
                  onPressed: () => context.go(AppRoute.home),
                  child: const Text('완료'),
                ),
              ],
            ),
          ),
    );
  }

}
