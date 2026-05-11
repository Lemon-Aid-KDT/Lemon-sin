// screens/auth/consent_screen.dart — D1 셸
//
// 참조: PROJECT_GUIDE.md §3.4 인증 흐름 + §20.5 민감정보 처리

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../utils/router.dart';
import '../../utils/tokens.dart';

class ConsentScreen extends StatelessWidget {
  const ConsentScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('약관 동의')),
      body: SingleChildScrollView(
            padding: const EdgeInsets.all(LemonSpace.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('이용에 필요한 동의', style: LemonText.heading),
                const SizedBox(height: LemonSpace.md),
                const Text(
                  '서비스 이용을 위해 아래 항목에 동의해주세요.',
                  style: LemonText.body,
                ),
                const SizedBox(height: LemonSpace.lg),

                // 필수
                _consentTile(
                  title: '[필수] 서비스 이용약관',
                  detail: '서비스 제공을 위한 기본 약관입니다.',
                ),
                _consentTile(
                  title: '[필수] 개인정보 처리방침',
                  detail: '이름·이메일·기본정보 수집',
                ),

                const Divider(height: LemonSpace.xl),
                const Text('선택 동의 (안 해도 가입은 가능해요)', style: LemonText.subheading),
                const SizedBox(height: LemonSpace.sm),

                _consentTile(
                  title: '[선택] 민감정보 수집·이용',
                  detail: '만성질환·복약·검진기록·걸음수·심박수 등',
                ),
                _consentTile(
                  title: '[선택] AI 분석을 위한 데이터 사용',
                  detail: 'Claude API 등 외부 LLM 호출 시 익명 처리',
                ),
                _consentTile(
                  title: '[선택] 마케팅 알림',
                  detail: '응모권·이벤트 안내',
                ),

                const SizedBox(height: LemonSpace.xl),
                const Text(
                  '본 서비스는 진단·치료를 제공하지 않는 웰니스 기반 건강관리 보조 서비스입니다. 의사·약사·영양사의 전문적 진단이나 처방을 대체하지 않습니다.',
                  style: LemonText.disclaimer,
                ),
                const SizedBox(height: LemonSpace.lg),
                ElevatedButton(
                  onPressed: () => context.go(AppRoute.onboarding),
                  child: const Text('동의하고 다음으로'),
                ),
              ],
            ),
          ),
    );
  }
  Widget _consentTile({required String title, required String detail}) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        title: Text(title, style: LemonText.subheading),
        subtitle: Text(detail, style: LemonText.caption),
        trailing: const Icon(Icons.chevron_right),
        onTap: () {
          // TODO(B): 동의 항목 상세 모달
        },
      ),
    );
  }
}
