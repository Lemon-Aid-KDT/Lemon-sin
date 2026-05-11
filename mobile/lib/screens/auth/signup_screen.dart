// screens/auth/signup_screen.dart — D1 셸
//
// 참조: PROJECT_GUIDE.md §3.4 인증·온보딩 흐름

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../utils/router.dart';
import '../../utils/tokens.dart';

class SignupScreen extends StatelessWidget {
  const SignupScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('회원가입')),
      body: Padding(
            padding: const EdgeInsets.all(LemonSpace.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const TextField(
                  decoration: InputDecoration(
                    labelText: '이메일',
                    helperText: '인증 메일을 보내드려요',
                  ),
                  keyboardType: TextInputType.emailAddress,
                ),
                const SizedBox(height: LemonSpace.md),
                const TextField(
                  decoration: InputDecoration(labelText: '비밀번호'),
                  obscureText: true,
                ),
                const SizedBox(height: LemonSpace.md),
                const TextField(
                  decoration: InputDecoration(labelText: '비밀번호 확인'),
                  obscureText: true,
                ),
                const SizedBox(height: LemonSpace.md),
                const TextField(
                  decoration: InputDecoration(labelText: '이름 (선택)'),
                ),
                const SizedBox(height: LemonSpace.lg),
                ElevatedButton(
                  onPressed: () => context.push(AppRoute.verifyEmail),
                  child: const Text('다음'),
                ),
              ],
            ),
          ),
    );
  }

}
