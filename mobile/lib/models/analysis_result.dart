// models/analysis_result.dart — AI 분석 결과 (출력 카드 정본 모델)
//
// 참조: mobile/CLAUDE.md §3.4 결과 카드 4 요소 + mobile/docs/integration_notes.md §2.1
// 사용자와 함께 디자인 결정 진행 중 — 마지막 디자인 협의 시점에 다시 손볼 것.
//
// 핵심 — AI 응답 메타 4 키 (CLAUDE.md §9 발주처 합의 대기):
//   confidence       — 0~1 float (백엔드 yeong-tech 일관 형식)
//   source           — "공식 DB · 마지막 업데이트 시각 등 작은 라벨" 원본 문자열
//   editable_fields  — 사용자가 고칠 수 있는 필드 목록
//   fallback_text    — 결과가 비어있을 때 카드 본문 대체 문자열
//
// 합치기 키 차이 (integration_notes.md §2.1):
//   kind              ↔ yeong-tech `analysis_type` StrEnum (3종: activity_score / weight_prediction / nutrition_analysis)
//                       — 기획서 5종 (nutrient/kdri/weight/activity/goal) 과 다름.
//                       — String? 으로 둬서 백엔드 변경 자유롭게 흡수.
//   snapshot          ↔ yeong-tech `result_snapshot: dict[str, Any]` — Map 으로 통째 보관.
//   algorithmVersion  ↔ yeong-tech `algorithm_version`
//   kdrisSourceVersion↔ yeong-tech `kdris_source_manifest_version`

class AnalysisResult {
  final String id;
  final String? userId;
  final DateTime? createdAt;

  /// 결과 카드 종류. 화면 분기용. 백엔드 값을 그대로 받음 — enum 없음.
  final String? kind;

  /// 카드 헤드라인 (큰 글씨).
  final String? headline;

  /// 카드 본문 1~2줄.
  final String? detail;

  /// 출처 / 시간 라벨 (예: "농진청 식품 DB · 5분 전").
  final String? source;

  /// 0~1 정규화 confidence. 백엔드 형식 차이 (0.85 / 85 / "85%") 는 parseConfidence 가 흡수.
  final double? confidence;

  /// 사용자가 인라인 수정할 수 있는 필드 키 목록.
  final List<String>? editableFields;

  /// 결과 빈 상태 대체 본문.
  final String? fallbackText;

  /// 백엔드 result_snapshot 통째.
  final Map<String, dynamic>? snapshot;

  final String? algorithmVersion;
  final String? kdrisSourceVersion;
  final bool? previewApproved;
  final Map<String, dynamic>? raw;

  const AnalysisResult({
    required this.id,
    this.userId,
    this.createdAt,
    this.kind,
    this.headline,
    this.detail,
    this.source,
    this.confidence,
    this.editableFields,
    this.fallbackText,
    this.snapshot,
    this.algorithmVersion,
    this.kdrisSourceVersion,
    this.previewApproved,
    this.raw,
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    final dynamic snap = json['result_snapshot'] ?? json['snapshot'];
    return AnalysisResult(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? json['userId'])?.toString(),
      createdAt: _parseDate(json['created_at']),
      kind: (json['kind'] ?? json['analysis_type'] ?? json['type']) as String?,
      headline: (json['headline'] ?? json['title']) as String?,
      detail: (json['detail'] ?? json['body']) as String?,
      source: (json['source'] ?? json['source_label']) as String?,
      confidence: parseConfidence(json['confidence']),
      editableFields: _stringList(json['editable_fields']),
      fallbackText: (json['fallback_text'] ?? json['fallbackText']) as String?,
      snapshot: snap is Map ? Map<String, dynamic>.from(snap) : null,
      algorithmVersion: json['algorithm_version'] as String?,
      kdrisSourceVersion:
          json['kdris_source_manifest_version'] as String?,
      previewApproved: json['preview_approved'] as bool?,
      raw: Map<String, dynamic>.from(json),
    );
  }

  /// 0.85 / 85 / "85%" / "85" 등을 0~1 float 으로 정규화.
  /// null / 파싱 실패 시 null.
  static double? parseConfidence(dynamic v) {
    if (v == null) return null;
    if (v is num) return v <= 1.0 ? v.toDouble() : v.toDouble() / 100;
    if (v is String) {
      final String cleaned = v.replaceAll('%', '').trim();
      final double? n = double.tryParse(cleaned);
      if (n == null) return null;
      return n <= 1.0 ? n : n / 100;
    }
    return null;
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
