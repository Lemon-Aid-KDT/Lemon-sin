// models/agent_memory.dart — Agent 작업 컨텍스트 & 실행 로그
//
// 참조: mobile/CLAUDE.md §3 (만성질환자용 영양 Agent) + mobile/docs/integration_notes.md
// 사용자와 함께 디자인 결정 진행 중 — 마지막 디자인 협의 시점에 다시 손볼 것.
//
// 챗 화면이 Agent 호출 전후로 보관할 사용자 컨텍스트 + 호출 로그.
// 백엔드 합치기 시 — 별도 GET 엔드포인트가 있을 수도, dashboard 통합으로 빠질 수도 있음.
// 화면이 의존하는 getter 시그니처만 안정적으로 유지.

class AgentMemory {
  final String userId;
  final String? recentLabSummary;
  final List<String>? chronicTags;
  final String? medicationInfo;
  final List<String>? recentCautions;
  final num? dietScore;
  final DateTime? updatedAt;
  final Map<String, dynamic>? raw;

  const AgentMemory({
    required this.userId,
    this.recentLabSummary,
    this.chronicTags,
    this.medicationInfo,
    this.recentCautions,
    this.dietScore,
    this.updatedAt,
    this.raw,
  });

  factory AgentMemory.fromJson(Map<String, dynamic> json) {
    return AgentMemory(
      userId: (json['user_id'] ?? json['userId'] ?? '').toString(),
      recentLabSummary:
          (json['recent_lab_summary'] ?? json['recentLabSummary']) as String?,
      chronicTags: _stringList(json['chronic_tags']),
      medicationInfo:
          (json['medication_info'] ?? json['medicationInfo']) as String?,
      recentCautions: _stringList(json['recent_cautions']),
      dietScore: json['diet_score'] as num?,
      updatedAt: _parseDate(json['updated_at']),
      raw: Map<String, dynamic>.from(json),
    );
  }
}

class AgentRun {
  final String id;
  final String? userId;
  final DateTime? ranAt;
  final String? model;
  final String? inputDigest;
  final String? outputDigest;
  final int? latencyMs;
  final Map<String, dynamic>? raw;

  const AgentRun({
    required this.id,
    this.userId,
    this.ranAt,
    this.model,
    this.inputDigest,
    this.outputDigest,
    this.latencyMs,
    this.raw,
  });

  factory AgentRun.fromJson(Map<String, dynamic> json) {
    return AgentRun(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? json['userId'])?.toString(),
      ranAt: _parseDate(json['ran_at']),
      model: json['model'] as String?,
      inputDigest: (json['input_digest'] ?? json['inputDigest']) as String?,
      outputDigest: (json['output_digest'] ?? json['outputDigest']) as String?,
      latencyMs: (json['latency_ms'] as num?)?.toInt(),
      raw: Map<String, dynamic>.from(json),
    );
  }
}

DateTime? _parseDate(dynamic v) {
  if (v == null) return null;
  if (v is DateTime) return v;
  if (v is String) return DateTime.tryParse(v);
  return null;
}

List<String>? _stringList(dynamic v) {
  if (v == null) return null;
  if (v is List) return v.map((e) => e.toString()).toList();
  return null;
}
