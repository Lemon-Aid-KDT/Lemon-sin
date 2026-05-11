// screens/auth/verify_email_screen.dart — D1 셸
//
// 참조: PROJECT_GUIDE.md §3.4 인증 흐름 / backend/src/services/email.py

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../utils/router.dart';
import '../../utils/tokens.dart';

class VerifyEmailScreen extends StatelessWidget {
  const VerifyEmailScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('이메일 인증')),
      body: Padding(
            padding: const EdgeInsets.all(LemonSpace.lg),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.mark_email_unread, size: 64, color: LemonColors.brand),
                const SizedBox(height: LemonSpace.lg),
                const Text('메일을 확인해주세요', style: LemonText.title),
                const SizedBox(height: LemonSpace.md),
                const Text(
                  '입력하신 이메일로 인증 링크를 보냈어요.\n링크를 클릭하면 다음 단계로 진행됩니다.',
                  style: LemonText.body,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: LemonSpace.xl),
                ElevatedButton(
                  onPressed: () => context.go(AppRoute.consent),
                  child: const Text('인증 완료'),
                ),
                const SizedBox(height: LemonSpace.sm),
                TextButton(
                  onPressed: () {},
                  child: const Text('인증 메일 다시 보내기'),
                ),
              ],
            ),
          ),
    );
  }

}
