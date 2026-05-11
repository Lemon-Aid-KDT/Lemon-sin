// screens/raffle_screen.dart — D1 셸
//
// 참조: PROJECT_GUIDE.md §3.8 사진 기록 응모권 UX

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../utils/router.dart';
import '../utils/tokens.dart';

class RaffleScreen extends StatelessWidget {
  const RaffleScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('응모권')),
      body: const Center(
            child: Padding(
              padding: EdgeInsets.all(LemonSpace.lg),
              child: Text('사진 기록 참여 응모권', style: LemonText.body),
            ),
          ),
    );
  }

}
