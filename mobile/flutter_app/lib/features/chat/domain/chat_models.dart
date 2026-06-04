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
    required this.answerability,
    required this.sources,
    required this.requiresUserApproval,
    required this.ctas,
  });

  factory ChatbotResponse.fromJson(Map<String, dynamic> json) {
    return ChatbotResponse(
      requestId: json['request_id'] as String? ?? '',
      message: json['message'] as String? ?? '',
      provider: json['provider'] as String? ?? 'unknown',
      usedTools: _stringList(json['used_tools']),
      safetyWarnings: _stringList(json['safety_warnings']),
      sourceFamilies: _stringList(json['source_families']),
      answerability: json['answerability'] as String? ?? 'answerable',
      sources: _sourceList(json['sources']),
      requiresUserApproval: json['requires_user_approval'] as bool? ?? false,
      ctas: _ctaList(json['ctas']),
    );
  }

  final String requestId;
  final String message;
  final String provider;
  final List<String> usedTools;
  final List<String> safetyWarnings;
  final List<String> sourceFamilies;
  final String answerability;
  final List<ChatbotSource> sources;
  final bool requiresUserApproval;
  final List<ChatbotCta> ctas;

  bool get usedAgentMemory => usedTools.contains('agent_memory');
  bool get hasReviewedSources => sources.isNotEmpty;
  bool get hasCtas => ctas.isNotEmpty;
}

enum ChatbotCta {
  completeMissingRecord,
  runOrRefreshAnalysis,
  addChecklistItem,
  askAboutThisResult,
}

ChatbotCta? _chatbotCtaFromJson(String value) {
  return switch (value) {
    'complete_missing_record' => ChatbotCta.completeMissingRecord,
    'run_or_refresh_analysis' => ChatbotCta.runOrRefreshAnalysis,
    'add_checklist_item' => ChatbotCta.addChecklistItem,
    'ask_about_this_result' => ChatbotCta.askAboutThisResult,
    _ => null,
  };
}

class ChatbotSource {
  ChatbotSource({
    required this.sourceId,
    required this.sourceFamily,
    required this.reviewStatus,
    required this.versionLabel,
    required this.reviewedAt,
    required this.expiresAt,
    required this.sourceUrl,
    required this.boundaryCode,
  });

  factory ChatbotSource.fromJson(Map<String, dynamic> json) {
    return ChatbotSource(
      sourceId: json['source_id'] as String? ?? '',
      sourceFamily: json['source_family'] as String? ?? '',
      reviewStatus: json['review_status'] as String? ?? '',
      versionLabel: json['version_label'] as String? ?? '',
      reviewedAt: json['reviewed_at'] as String? ?? '',
      expiresAt: json['expires_at'] as String? ?? '',
      sourceUrl: json['source_url'] as String? ?? '',
      boundaryCode: json['boundary_code'] as String? ?? '',
    );
  }

  final String sourceId;
  final String sourceFamily;
  final String reviewStatus;
  final String versionLabel;
  final String reviewedAt;
  final String expiresAt;
  final String sourceUrl;
  final String boundaryCode;
}

List<String> _stringList(Object? value) {
  if (value is! List<dynamic>) {
    return <String>[];
  }
  return value.whereType<String>().toList(growable: false);
}

List<ChatbotCta> _ctaList(Object? value) {
  return _stringList(value)
      .map(_chatbotCtaFromJson)
      .whereType<ChatbotCta>()
      .take(2)
      .toList(growable: false);
}

List<ChatbotSource> _sourceList(Object? value) {
  if (value is! List<dynamic>) {
    return <ChatbotSource>[];
  }
  return value
      .whereType<Map<String, dynamic>>()
      .map(ChatbotSource.fromJson)
      .toList(growable: false);
}
