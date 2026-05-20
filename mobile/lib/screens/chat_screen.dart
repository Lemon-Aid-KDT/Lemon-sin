// screens/chat_screen.dart — 챗 탭 (LADS v2)
//
// 디자인:
//   - 상단: brand 옅은 헤더 + "레몬봇" 마스코트 + 부제
//   - 본문: 인사 + 추천 질문 칩 + 메시지 리스트 (mock 1턴)
//   - 하단: 입력바 (둥근 chip 스타일, 우측 brand 전송)
//
// 의료법 가드: "처방"·"진단"·"치료" 금지 → "확인"·"안내"·"도움" 사용
// 백엔드 챗 API 연동 전까지는 mock 응답 (TODO: 영양제 팀원 API).

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../utils/design_tokens_v2.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollCtl = ScrollController();
  final List<_Message> _messages = [];
  bool _thinking = false;

  static const List<String> _suggestions = [
    '비타민 D 얼마나 먹어야 해?',
    '오메가-3 같이 먹어도 돼?',
    '오늘 점심 어떻게 먹으면 좋아?',
    '나트륨 줄이는 팁 알려줘',
  ];

  void _send(String text) async {
    final body = text.trim();
    if (body.isEmpty || _thinking) return;
    HapticFeedback.selectionClick();
    setState(() {
      _messages.add(_Message(text: body, mine: true));
      _controller.clear();
      _thinking = true;
    });
    _scrollToBottom();

    // mock 답변 (실제는 API 호출)
    await Future.delayed(const Duration(milliseconds: 800));
    if (!mounted) return;
    setState(() {
      _messages.add(_Message(
        text: _mockReply(body),
        mine: false,
      ));
      _thinking = false;
    });
    _scrollToBottom();
  }

  String _mockReply(String q) {
    if (q.contains('비타민')) {
      return '보통 성인은 비타민 D 1000IU 정도가 권장돼요. 햇볕을 적게 본 날은 보충을 고려해볼 수 있어요.\n\n복용 중인 약이 있다면 의사·약사와 상의해주세요.';
    }
    if (q.contains('오메가') || q.contains('함께')) {
      return '오메가-3는 대부분 영양제와 잘 어울려요. 다만 항응고제를 드시고 있다면 의료진과 먼저 확인해주세요.';
    }
    return '좋은 질문이에요. 자세한 안내가 필요하시면 분석 기록과 함께 알려드릴게요.\n\n참고용 정보로, 의사·약사·영양사의 진단을 대신하지 않아요.';
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtl.hasClients) {
        _scrollCtl.animateTo(
          _scrollCtl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 240),
          curve: Curves.easeOutCubic,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.section,
      body: Column(
        children: [
          _ChatHeader(),
          Expanded(
            child: ListView(
              controller: _scrollCtl,
              padding: const EdgeInsets.fromLTRB(
                AppSpace.page, AppSpace.lg, AppSpace.page, AppSpace.lg,
              ),
              children: [
                _IntroCard(),
                const SizedBox(height: AppSpace.md),
                if (_messages.isEmpty) _SuggestionGrid(
                  suggestions: _suggestions,
                  onTap: _send,
                ),
                for (final m in _messages) ...[
                  _MessageBubble(message: m),
                  const SizedBox(height: AppSpace.sm),
                ],
                if (_thinking) const _TypingBubble(),
              ],
            ),
          ),
          _InputBar(
            controller: _controller,
            onSend: _send,
            disabled: _thinking,
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollCtl.dispose();
    super.dispose();
  }
}

// ─── 데이터 모델 ───
class _Message {
  final String text;
  final bool mine;
  _Message({required this.text, required this.mine});
}

// ═══════════════════════════════════════════
// 상단 헤더 (brand soft)
// ═══════════════════════════════════════════
class _ChatHeader extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColor.brand,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.page, AppSpace.lg, AppSpace.page, AppSpace.lg,
          ),
          child: Row(
            children: [
              Container(
                width: 44, height: 44,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.45),
                  shape: BoxShape.circle,
                ),
                alignment: Alignment.center,
                child: const Icon(Icons.chat_bubble_rounded,
                    color: AppColor.ink, size: 22),
              ),
              const SizedBox(width: AppSpace.md),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text(
                    '레몬봇',
                    style: TextStyle(
                      color: AppColor.ink,
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.4,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    '영양·식단 궁금한 거 편하게 물어봐요',
                    style: TextStyle(
                      color: AppColor.ink,
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.2,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 인사 카드 (마스코트)
// ═══════════════════════════════════════════
class _IntroCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.16),
            blurRadius: 14,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Image.asset(
            'assets/mascot/hello-mascot.png',
            width: 64, height: 64, fit: BoxFit.contain,
            errorBuilder: (_, __, ___) => Container(
              width: 64, height: 64,
              decoration: BoxDecoration(
                color: AppColor.brandSoft,
                shape: BoxShape.circle,
              ),
              alignment: Alignment.center,
              child: Icon(Icons.emoji_food_beverage,
                  color: AppColor.brand, size: 32),
            ),
          ),
          const SizedBox(width: AppSpace.md),
          const Expanded(
            child: Text(
              '안녕하세요, 태동님!\n오늘 어떤 게 궁금해요?',
              style: TextStyle(
                color: AppColor.ink,
                fontSize: 15,
                fontWeight: FontWeight.w700,
                height: 1.4,
                letterSpacing: -0.3,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 추천 질문 그리드
// ═══════════════════════════════════════════
class _SuggestionGrid extends StatelessWidget {
  final List<String> suggestions;
  final ValueChanged<String> onTap;
  const _SuggestionGrid({required this.suggestions, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.only(left: 4, bottom: AppSpace.sm),
          child: Text(
            '이런 걸 물어보면 좋아요',
            style: TextStyle(
              color: AppColor.inkSecondary,
              fontSize: 13,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.2,
            ),
          ),
        ),
        Wrap(
          spacing: AppSpace.sm,
          runSpacing: AppSpace.sm,
          children: [
            for (final s in suggestions) _SuggestChip(text: s, onTap: () => onTap(s)),
          ],
        ),
      ],
    );
  }
}

class _SuggestChip extends StatelessWidget {
  final String text;
  final VoidCallback onTap;
  const _SuggestChip({required this.text, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpace.md, vertical: 10,
        ),
        decoration: BoxDecoration(
          color: AppColor.surface,
          borderRadius: BorderRadius.circular(AppRadius.full),
          border: Border.all(color: AppColor.border, width: 1),
        ),
        child: Text(
          text,
          style: const TextStyle(
            color: AppColor.ink,
            fontSize: 13,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.2,
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 메시지 버블
// ═══════════════════════════════════════════
class _MessageBubble extends StatelessWidget {
  final _Message message;
  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final mine = message.mine;
    final bg = mine ? AppColor.brand : AppColor.surface;
    final fg = AppColor.ink;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.78,
        ),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpace.md, vertical: 10,
          ),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(16),
              topRight: const Radius.circular(16),
              bottomLeft: Radius.circular(mine ? 16 : 4),
              bottomRight: Radius.circular(mine ? 4 : 16),
            ),
            boxShadow: mine ? null : const [
              BoxShadow(
                color: Color.fromRGBO(140, 155, 175, 0.14),
                blurRadius: 10,
                offset: Offset(0, 3),
              ),
            ],
          ),
          child: Text(
            message.text,
            style: TextStyle(
              color: fg,
              fontSize: 14,
              fontWeight: mine ? FontWeight.w700 : FontWeight.w500,
              height: 1.45,
              letterSpacing: -0.2,
            ),
          ),
        ),
      ),
    );
  }
}

class _TypingBubble extends StatefulWidget {
  const _TypingBubble();
  @override
  State<_TypingBubble> createState() => _TypingBubbleState();
}

class _TypingBubbleState extends State<_TypingBubble>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctl;
  @override
  void initState() {
    super.initState();
    _ctl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat();
  }

  @override
  void dispose() {
    _ctl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpace.md, vertical: 12,
        ),
        decoration: BoxDecoration(
          color: AppColor.surface,
          borderRadius: BorderRadius.circular(16),
          boxShadow: const [
            BoxShadow(
              color: Color.fromRGBO(140, 155, 175, 0.14),
              blurRadius: 10,
              offset: Offset(0, 3),
            ),
          ],
        ),
        child: AnimatedBuilder(
          animation: _ctl,
          builder: (_, __) {
            Widget dot(double phase) {
              final t = (_ctl.value + phase) % 1.0;
              final opacity = (t < 0.5 ? t : 1 - t) * 2;
              return Container(
                width: 6, height: 6,
                margin: const EdgeInsets.symmetric(horizontal: 2),
                decoration: BoxDecoration(
                  color: AppColor.inkTertiary.withOpacity(0.3 + 0.7 * opacity),
                  shape: BoxShape.circle,
                ),
              );
            }
            return Row(
              mainAxisSize: MainAxisSize.min,
              children: [dot(0), dot(0.33), dot(0.66)],
            );
          },
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 입력바
// ═══════════════════════════════════════════
class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final ValueChanged<String> onSend;
  final bool disabled;
  const _InputBar({
    required this.controller,
    required this.onSend,
    required this.disabled,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColor.section,
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.page, AppSpace.sm, AppSpace.page, AppSpace.md,
          ),
          child: Row(
            children: [
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    color: AppColor.surface,
                    borderRadius: BorderRadius.circular(AppRadius.full),
                    border: Border.all(color: AppColor.border, width: 1),
                  ),
                  child: TextField(
                    controller: controller,
                    enabled: !disabled,
                    minLines: 1,
                    maxLines: 4,
                    style: const TextStyle(
                      color: AppColor.ink,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.2,
                    ),
                    decoration: InputDecoration(
                      hintText: '메시지를 입력하세요',
                      hintStyle: TextStyle(
                        color: AppColor.inkTertiary,
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                      border: InputBorder.none,
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 18, vertical: 12,
                      ),
                    ),
                    onSubmitted: onSend,
                    textInputAction: TextInputAction.send,
                  ),
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              GestureDetector(
                onTap: disabled ? null : () => onSend(controller.text),
                child: Container(
                  width: 44, height: 44,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [Color(0xFFFFD43A), AppColor.brand],
                    ),
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AppColor.brand.withOpacity(0.35),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  alignment: Alignment.center,
                  child: const Icon(Icons.arrow_upward_rounded,
                      color: AppColor.ink, size: 22),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
