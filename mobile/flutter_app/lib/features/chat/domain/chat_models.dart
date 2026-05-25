class ChatTurn {
  ChatTurn({
    required this.role,
    required this.content,
    required this.createdAt,
  });

  final String role;
  final String content;
  final DateTime createdAt;

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'role': role,
      'content': content,
      'created_at': createdAt.toIso8601String(),
    };
  }
}

class ChatbotRequest {
  ChatbotRequest({
    required this.requestId,
    required this.userId,
    required this.message,
    required this.conversation,
    required this.context,
  });

  factory ChatbotRequest.compose({
    required String message,
    required List<ChatTurn> conversation,
  }) {
    return ChatbotRequest(
      requestId: 'mobile-chat-${DateTime.now().millisecondsSinceEpoch}',
      userId: 'mobile-client-placeholder',
      message: message,
      conversation: conversation,
      context: <String, dynamic>{
        'profile': <String, dynamic>{
          'goals': <String>['meal_management'],
        },
      },
    );
  }

  final String requestId;
  final String userId;
  final String message;
  final List<ChatTurn> conversation;
  final Map<String, dynamic> context;

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'request_id': requestId,
      'user_id': userId,
      'message': message,
      'conversation': conversation
          .map((ChatTurn turn) => turn.toJson())
          .toList(growable: false),
      'context': context,
    };
  }
}

class ChatbotResponse {
  ChatbotResponse({
    required this.requestId,
    required this.message,
    required this.provider,
    required this.usedTools,
    required this.safetyWarnings,
    required this.sourceFamilies,
    required this.requiresUserApproval,
  });

  factory ChatbotResponse.fromJson(Map<String, dynamic> json) {
    return ChatbotResponse(
      requestId: json['request_id'] as String? ?? '',
      message: json['message'] as String? ?? '',
      provider: json['provider'] as String? ?? 'unknown',
      usedTools: _stringList(json['used_tools']),
      safetyWarnings: _stringList(json['safety_warnings']),
      sourceFamilies: _stringList(json['source_families']),
      requiresUserApproval:
          json['requires_user_approval'] as bool? ?? false,
    );
  }

  final String requestId;
  final String message;
  final String provider;
  final List<String> usedTools;
  final List<String> safetyWarnings;
  final List<String> sourceFamilies;
  final bool requiresUserApproval;

  bool get usedAgentMemory => usedTools.contains('agent_memory');
}

List<String> _stringList(Object? value) {
  if (value is! List<dynamic>) {
    return <String>[];
  }
  return value.whereType<String>().toList(growable: false);
}
