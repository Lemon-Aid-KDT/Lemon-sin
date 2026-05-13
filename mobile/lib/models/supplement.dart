// models/supplement.dart — 영양제 + 성분 (느슨한 컨테이너)
//
// 참조: mobile/CLAUDE.md §3.4 + mobile/docs/integration_notes.md §2.1 (yeong-tech supplement.py)
// 사용자와 함께 디자인 결정 진행 중 — 마지막 디자인 협의 시점에 다시 손볼 것.
//
// 합치기 키 차이 (integration_notes.md §2.1):
//   SupplementIngredient.name        ↔ yeong-tech `display_name`
//   SupplementIngredient.confidence  ↔ yeong-tech 0~1 float
//   previewApproved                  ↔ yeong-tech SupplementAnalysisStatus.CONFIRMED 와 매핑

class Supplement {
  final String id;
  final String userId;
  final DateTime? takenAt;
  final String? photoUrl;
  final String? ocrText;
  final List<SupplementIngredient>? ingredients;
  final bool? previewApproved;
  final Map<String, dynamic>? raw;

  const Supplement({
    required this.id,
    required this.userId,
    this.takenAt,
    this.photoUrl,
    this.ocrText,
    this.ingredients,
    this.previewApproved,
    this.raw,
  });

  factory Supplement.fromJson(Map<String, dynamic> json) {
    final List<dynamic>? ingsRaw =
        (json['ingredients'] ?? json['candidates']) as List<dynamic>?;
    final dynamic status = json['analysis_status'] ?? json['status'];
    final bool? approved = status == null
        ? json['preview_approved'] as bool?
        : (status.toString() == 'confirmed');
    return Supplement(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? json['userId'] ?? '').toString(),
      takenAt: _parseDate(json['taken_at']),
      photoUrl: (json['photo_url'] ?? json['photoUrl']) as String?,
      ocrText: (json['ocr_text'] ?? json['ocrText']) as String?,
      ingredients: ingsRaw == null
          ? null
          : ingsRaw
              .map((e) =>
                  SupplementIngredient.fromJson(Map<String, dynamic>.from(e as Map)))
              .toList(),
      previewApproved: approved,
      raw: Map<String, dynamic>.from(json),
    );
  }
}

class SupplementIngredient {
  final String? name;
  final double? amount;
  final String? unit;
  final double? confidence;
  final Map<String, dynamic>? raw;

  const SupplementIngredient({
    this.name,
    this.amount,
    this.unit,
    this.confidence,
    this.raw,
  });

  factory SupplementIngredient.fromJson(Map<String, dynamic> json) {
    return SupplementIngredient(
      name: (json['name'] ?? json['display_name']) as String?,
      amount: (json['amount'] as num?)?.toDouble(),
      unit: json['unit'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble(),
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
