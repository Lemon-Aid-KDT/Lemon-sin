// screens/chat_screen.dart — D1 셸
//
// 참조: PROJECT_GUIDE.md §3.1 챗봇 Agent / §3.3 Tool 정의 / §7.3.3

import 'package:flutter/material.dart';

import '../utils/tokens.dart';

class ChatScreen extends StatelessWidget {
  const ChatScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('챗봇')),
      body: Column(
            children: const [
              // TODO(B): 챗봇 메시지 리스트 + ai_input_sheet
              Expanded(
                child: Center(
                  child: Padding(
                    padding: EdgeInsets.all(LemonSpace.lg),
                    child: Text(
                      '"이 영양제 계속 먹어도 돼?" 같이\n자연어로 물어보세요',
                      style: LemonText.body,
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
              ),
            ],
          ),
    );
  }

}
