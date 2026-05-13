// screens/settings_screen.dart — D1 셸
//
// 참조: PROJECT_GUIDE.md §3.5 설정 화면 / §20.5 데이터 주체 5권리

import 'package:flutter/material.dart';

import '../utils/tokens.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('설정')),
      body: ListView(
            children: const [
              ListTile(title: Text('내 정보', style: LemonText.body)),
              ListTile(title: Text('동의 관리', style: LemonText.body)),
              ListTile(title: Text('알림 설정', style: LemonText.body)),
              ListTile(title: Text('데이터 내보내기', style: LemonText.body)),
              Divider(),
              ListTile(title: Text('로그아웃', style: LemonText.body)),
              ListTile(title: Text('계정 탈퇴', style: LemonText.body)),
              Divider(),
              ListTile(
                title: Text('서비스 정보', style: LemonText.body),
                subtitle: Text('의료법·약사법·면책 고지', style: LemonText.caption),
              ),
            ],
          ),
    );
  }

}
