// screens/score_screen.dart — D1 셸
//
// 참조: PROJECT_GUIDE.md §3.5 식단 점수 / §7.3.4 평가 Agent

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../utils/router.dart';
import '../utils/tokens.dart';

class ScoreScreen extends StatelessWidget {
  const ScoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('식단관리 점수')),
      body: const Center(
            child: Padding(
              padding: EdgeInsets.all(LemonSpace.lg),
              child: Text('끼니별 점수 + 평가 Agent 코멘트', style: LemonText.body),
            ),
          ),
    );
  }

}
