import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/theme/lemon_theme.dart';
import '../../../shared/widgets/medical_disclaimer.dart';
import '../data/chat_repository.dart';
import '../domain/chat_models.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final ChatRepository _repository = ChatRepository();
  final TextEditingController _controller = TextEditingController();
  final List<ChatTurn> _conversation = <ChatTurn>[];
  ChatbotResponse? _lastResponse;
  bool _isSending = false;
  bool _hasError = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final String message = _controller.text.trim();
    if (message.isEmpty || _isSending) {
      return;
    }

    setState(() {
      _isSending = true;
      _hasError = false;
      _controller.clear();
    });

    try {
      await _repository.grantSensitiveHealthAnalysisConsent();
      final ChatbotResponse response = await _repository.sendMessage(
        ChatbotRequest.compose(
          message: message,
          conversation: List<ChatTurn>.unmodifiable(_conversation),
        ),
      );
      if (!mounted) {
        return;
      }
      final DateTime now = DateTime.now();
      setState(() {
        _conversation.add(
          ChatTurn(role: 'user', content: message, createdAt: now),
        );
        _conversation.add(
          ChatTurn(
            role: 'assistant',
            content: response.message,
            createdAt: DateTime.now(),
          ),
        );
        _lastResponse = response;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _hasError = true;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final String memoryLabel =
        _lastResponse?.usedAgentMemory == true ? '사용' : '미사용';

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: <Widget>[
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 10, 16, 8),
              child: Row(
                children: <Widget>[
                  IconButton(
                    onPressed: () => context.go('/'),
                    icon: const Icon(Icons.arrow_back_rounded),
                  ),
                  Expanded(
                    child: Text(
                      '챗봇',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                  ),
                  if (_lastResponse != null)
                    LemonPill(
                      label: _lastResponse!.provider,
                      color: LemonColors.leaf,
                      backgroundColor: LemonColors.leafSoft,
                    ),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                children: <Widget>[
                  if (_lastResponse != null)
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: <Widget>[
                        LemonPill(
                          label: 'memory $memoryLabel',
                          color: LemonColors.sky,
                          backgroundColor: LemonColors.skySoft,
                        ),
                        for (final String sourceFamily
                            in _lastResponse!.sourceFamilies)
                          LemonPill(
                            label: _sourceFamilyLabel(sourceFamily),
                            color: LemonColors.leaf,
                            backgroundColor: LemonColors.leafSoft,
                          ),
                        if (_lastResponse!.requiresUserApproval)
                          const LemonPill(
                            label: '승인 필요',
                            color: LemonColors.warning,
                            backgroundColor: LemonColors.warningSoft,
                          ),
                      ],
                    ),
                  if (_lastResponse != null) const SizedBox(height: 12),
                  if (_conversation.isEmpty) const _EmptyChatState(),
                  for (final ChatTurn turn in _conversation)
                    _ChatBubble(turn: turn),
                  if (_hasError) const _ChatErrorPanel(),
                  const SizedBox(height: 12),
                  const MedicalDisclaimer(),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              child: Row(
                children: <Widget>[
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      minLines: 1,
                      maxLines: 4,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _send(),
                      decoration: const InputDecoration(
                        hintText: '확정한 기록에 대해 물어보기',
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _isSending ? null : _send,
                    icon: _isSending
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.send_rounded),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

String _sourceFamilyLabel(String sourceFamily) {
  return switch (sourceFamily) {
    'nutrition_reference' => '영양 기준',
    'supplement_reference' => '영양제 참고',
    'drug_safety_boundary' => '복약 주의',
    'chronic_condition' => '만성질환 맥락',
    'general_medical' => '일반 건강정보',
    'emergency_escalation' => '응급 안내',
    'mental_health_escalation' => '안전 위기 안내',
    _ => sourceFamily.replaceAll('_', ' '),
  };
}

class _EmptyChatState extends StatelessWidget {
  const _EmptyChatState();

  @override
  Widget build(BuildContext context) {
    return LemonCard(
      color: LemonColors.lemonSoft,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Icon(Icons.chat_bubble_outline_rounded),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              '오늘 확정한 음식, 영양제 기록을 기준으로 확인할 점을 물어보세요.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  const _ChatBubble({required this.turn});

  final ChatTurn turn;

  @override
  Widget build(BuildContext context) {
    final bool isUser = turn.role == 'user';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 320),
        child: Padding(
          padding: const EdgeInsets.only(top: 10),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: isUser ? LemonColors.lemon : LemonColors.paper,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: LemonColors.line),
            ),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(
                turn.content,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: LemonColors.ink,
                    ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ChatErrorPanel extends StatelessWidget {
  const _ChatErrorPanel();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.only(top: 12),
      child: LemonCard(
        color: LemonColors.dangerSoft,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(Icons.error_outline_rounded, color: LemonColors.danger),
            SizedBox(width: 10),
            Expanded(
              child: Text('챗봇 응답을 받지 못했습니다. 백엔드 연결과 인증 상태를 확인해 주세요.'),
            ),
          ],
        ),
      ),
    );
  }
}
