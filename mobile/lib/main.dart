import 'package:flutter/material.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

import 'screens/auth/login_screen.dart';

void main() {
  // 카카오 SDK 초기화 — kakao_app_key는 카카오 개발자 콘솔에서 발급받은 네이티브 앱 키
  KakaoSdk.init(nativeAppKey: 'YOUR_KAKAO_NATIVE_APP_KEY');

  runApp(const LemonAidApp());
}

class LemonAidApp extends StatelessWidget {
  const LemonAidApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Lemon Aid',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFFFD600)),
        useMaterial3: true,
      ),
      home: const LoginScreen(),
    );
  }
}
