// features/chat/chat_models.dart — 레몬봇 챗 API 데이터 모델
//
// 백엔드 `/ai-agent/chat` 계약을 표현하는 순수 Dart 모델.
// 모든 fromJson 은 null-safe 하게 작성해 서버 응답 변동에 견디게 한다.
//
// 의료법 가드: 사용자 노출 라벨은 "확인"·"안내"·"근거" 사용
// (진단/처방/치료/효능·효과 금지).

/// One conversation turn carried in the chatbot request history.
class ChatTurn {
  /// Creates a conversation turn.
  ///
  /// Args:
  ///   role: Either `user` or `assistant`.
  ///   content: Message text for the turn.
  ///   createdAt: Local timestamp; serialized as ISO 8601.
  ChatTurn({
    required this.role,
    required this.content,
    required this.createdAt,
  });

  /// Either `user` or `assistant`.
  final String role;

  /// Message text for the turn.
  final String content;

  /// Timestamp serialized as ISO 8601 in the request payload.
  final DateTime createdAt;

  /// Serializes the turn for the request `conversation` array.
  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'role': role,
      'content': content,
      'created_at': createdAt.toIso8601String(),
    };
  }
}

/// Decoded `/ai-agent/chat` response.
class ChatbotResponse {
  /// Creates a chatbot response.
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
    required this.analysisSnapshot,
    required this.todayAnalysis,
    required this.smartAnalysis,
    required this.checklistCandidates,
    required this.approvalPreview,
  });

  /// Parses a response from a decoded JSON object.
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
      ctas: _stringList(json['ctas']),
      analysisSnapshot: _objectMap(json['analysis_snapshot']),
      todayAnalysis: _objectMap(json['today_analysis']),
      smartAnalysis: _objectMap(json['smart_analysis']),
      checklistCandidates: _checklistCandidateList(
        json['checklist_candidates'],
      ),
      approvalPreview: ChatbotApprovalPreview.fromJson(
        _objectMap(json['approval_preview']),
      ),
    );
  }

  /// Server-echoed request id.
  final String requestId;

  /// Assistant message text rendered in the chat bubble.
  final String message;

  /// Provider that produced the answer.
  final String provider;

  /// Tools the agent used while answering.
  final List<String> usedTools;

  /// Safety warning strings surfaced by the agent.
  final List<String> safetyWarnings;

  /// Source family identifiers backing the answer.
  final List<String> sourceFamilies;

  /// One of `answerable`, `needs_more_info`, `unknown_no_reviewed_source`.
  final String answerability;

  /// Reviewed sources backing the answer.
  final List<ChatbotSource> sources;

  /// Whether the answer requires an explicit user approval before any action.
  final bool requiresUserApproval;

  /// Up to three suggested follow-up prompts.
  final List<String> ctas;

  /// Raw analysis snapshot payload (kept opaque for the chat tab).
  final Map<String, dynamic> analysisSnapshot;

  /// Raw today-analysis payload.
  final Map<String, dynamic> todayAnalysis;

  /// Raw smart-analysis payload.
  final Map<String, dynamic> smartAnalysis;

  /// Checklist candidates suggested by the agent.
  final List<ChatbotChecklistCandidate> checklistCandidates;

  /// Approval preview describing a gated analysis run.
  final ChatbotApprovalPreview approvalPreview;

  /// Whether the agent retrieved any reviewed source.
  bool get hasReviewedSources => sources.isNotEmpty;

  /// Whether the answer is fully answerable from reviewed knowledge.
  bool get isAnswerable => answerability == 'answerable';

  /// Whether the response gates an analysis run behind explicit approval.
  bool get needsAnalysisApproval {
    return requiresUserApproval &&
        approvalPreview.approvalState == 'approval_required';
  }
}

/// A single checklist candidate suggested by the agent.
class ChatbotChecklistCandidate {
  /// Creates a checklist candidate.
  ChatbotChecklistCandidate({
    required this.candidateId,
    required this.kind,
    required this.title,
    required this.source,
    required this.approvalState,
    required this.sideEffect,
    required this.deferredAction,
  });

  /// Parses a checklist candidate from a decoded JSON object.
  factory ChatbotChecklistCandidate.fromJson(Map<String, dynamic> json) {
    return ChatbotChecklistCandidate(
      candidateId: json['candidate_id'] as String? ?? '',
      kind: json['kind'] as String? ?? '',
      title: json['title'] as String? ?? '',
      source: json['source'] as String? ?? '',
      approvalState: json['approval_state'] as String? ?? '',
      sideEffect: json['side_effect'] as String? ?? '',
      deferredAction: json['deferred_action'] as String? ?? '',
    );
  }

  /// Stable candidate identifier.
  final String candidateId;

  /// Candidate kind discriminator.
  final String kind;

  /// Human-readable candidate title.
  final String title;

  /// Source label for the candidate.
  final String source;

  /// Approval state for the candidate.
  final String approvalState;

  /// Declared side effect.
  final String sideEffect;

  /// Deferred action identifier.
  final String deferredAction;
}

/// Approval preview describing a gated analysis run.
///
/// Backend contract:
///   `{required, approval_state, analysis_kind, snapshot_preview, side_effects}`.
class ChatbotApprovalPreview {
  /// Creates an approval preview.
  ChatbotApprovalPreview({
    required this.hasPreview,
    required this.requiredApproval,
    required this.approvalState,
    required this.analysisKind,
    required this.snapshotPreview,
    required this.sideEffects,
  });

  /// Returns an empty preview that gates nothing.
  factory ChatbotApprovalPreview.empty() {
    return ChatbotApprovalPreview(
      hasPreview: false,
      requiredApproval: false,
      approvalState: '',
      analysisKind: '',
      snapshotPreview: const <String, dynamic>{},
      sideEffects: const <String>[],
    );
  }

  /// Parses an approval preview from a decoded JSON object.
  factory ChatbotApprovalPreview.fromJson(Map<String, dynamic> json) {
    if (json.isEmpty) {
      return ChatbotApprovalPreview.empty();
    }
    return ChatbotApprovalPreview(
      hasPreview: true,
      requiredApproval: json['required'] as bool? ?? false,
      approvalState: json['approval_state'] as String? ?? '',
      analysisKind: json['analysis_kind'] as String? ?? '',
      snapshotPreview: _objectMap(json['snapshot_preview']),
      sideEffects: _stringList(json['side_effects']),
    );
  }

  /// Whether the server sent a non-empty preview.
  final bool hasPreview;

  /// Whether approval is required before running the analysis.
  final bool requiredApproval;

  /// Approval state; `approval_required` gates the run.
  final String approvalState;

  /// Analysis kind echoed back on the approval resend.
  final String analysisKind;

  /// Opaque snapshot preview payload.
  final Map<String, dynamic> snapshotPreview;

  /// Declared side effects of running the analysis.
  final List<String> sideEffects;
}

/// A reviewed source backing the answer.
class ChatbotSource {
  /// Creates a source.
  ChatbotSource({
    required this.title,
    required this.sourceId,
    required this.sourceFamily,
    required this.sourceUrl,
  });

  /// Parses a source from a decoded JSON object.
  factory ChatbotSource.fromJson(Map<String, dynamic> json) {
    return ChatbotSource(
      title: json['title'] as String? ?? '',
      sourceId: json['source_id'] as String? ?? '',
      sourceFamily: json['source_family'] as String? ?? '',
      sourceUrl: json['source_url'] as String? ?? '',
    );
  }

  /// Human-readable source title.
  final String title;

  /// Stable source identifier.
  final String sourceId;

  /// Source family identifier.
  final String sourceFamily;

  /// Source URL when present.
  final String sourceUrl;

  /// Best-effort short label for an inline source chip.
  String get label {
    if (title.trim().isNotEmpty) {
      return title.trim();
    }
    if (sourceId.trim().isNotEmpty) {
      return sourceId.trim();
    }
    return sourceFamily.trim();
  }
}

List<String> _stringList(Object? value) {
  if (value is! List<dynamic>) {
    return <String>[];
  }
  return value.whereType<String>().toList(growable: false);
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

Map<String, dynamic> _objectMap(Object? value) {
  if (value is! Map<dynamic, dynamic>) {
    return <String, dynamic>{};
  }
  return value.map(
    (dynamic key, dynamic item) =>
        MapEntry<String, dynamic>(key.toString(), item),
  );
}

List<ChatbotChecklistCandidate> _checklistCandidateList(Object? value) {
  if (value is! List<dynamic>) {
    return <ChatbotChecklistCandidate>[];
  }
  return value
      .map(_objectMap)
      .where((Map<String, dynamic> item) => item.isNotEmpty)
      .map(ChatbotChecklistCandidate.fromJson)
      .toList(growable: false);
}
