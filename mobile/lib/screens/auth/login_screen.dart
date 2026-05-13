import 'package:flutter/material.dart';

import '../../services/auth_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _isLoading = false;

  Future<void> _handleLogin(Future<void> Function() loginFn) async {
    setState(() => _isLoading = true);
    try {
      await loginFn();
      if (mounted) {
        // TODO: 로그인 성공 시 홈 화면으로 이동
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('로그인 성공!')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString())),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFFFDE7),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                '🍋 Lemon Aid',
                style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                '만성질환 관리를 시작하세요',
                style: TextStyle(fontSize: 16, color: Colors.black54),
              ),
              const SizedBox(height: 48),

              if (_isLoading)
                const CircularProgressIndicator()
              else ...[
                // 구글 로그인 버튼
                _SocialLoginButton(
                  label: 'Google로 계속하기',
                  backgroundColor: Colors.white,
                  textColor: Colors.black87,
                  borderColor: Colors.grey.shade300,
                  icon: _GoogleIcon(),
                  onTap: () => _handleLogin(AuthService.signInWithGoogle),
                ),
                const SizedBox(height: 12),

                // 카카오 로그인 버튼
                _SocialLoginButton(
                  label: '카카오로 계속하기',
                  backgroundColor: const Color(0xFFFEE500),
                  textColor: Colors.black87,
                  icon: const Icon(Icons.chat_bubble, color: Colors.black54, size: 20),
                  onTap: () => _handleLogin(AuthService.signInWithKakao),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _SocialLoginButton extends StatelessWidget {
  final String label;
  final Color backgroundColor;
  final Color textColor;
  final Color? borderColor;
  final Widget icon;
  final VoidCallback onTap;

  const _SocialLoginButton({
    required this.label,
    required this.backgroundColor,
    required this.textColor,
    required this.icon,
    required this.onTap,
    this.borderColor,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: OutlinedButton.icon(
        icon: icon,
        label: Text(label, style: TextStyle(color: textColor, fontSize: 15)),
        style: OutlinedButton.styleFrom(
          backgroundColor: backgroundColor,
          side: BorderSide(color: borderColor ?? Colors.transparent),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        onPressed: onTap,
      ),
    );
  }
}

class _GoogleIcon extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return const Text('G', style: TextStyle(
      fontSize: 18,
      fontWeight: FontWeight.bold,
      color: Color(0xFF4285F4),
    ));
  }
}
