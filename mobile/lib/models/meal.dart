// models/meal.dart — 식단 / 음식 후보 / 100g 영양 프로필
//
// 참조: mobile/CLAUDE.md §3.4 + mobile/docs/integration_notes.md §4 (work-space/jongpil)
// 사용자와 함께 디자인 결정 진행 중 — 마지막 디자인 협의 시점에 다시 손볼 것.
//
// 합치기 키 차이 (integration_notes.md §4 — jongpil meal pipeline):
//   FoodCandidate.canonicalName ↔ jongpil `class_name_ko` (YOLO/GCV) 또는 `name_ko` (Fusion 후)
//   FoodCandidate.foodCode      ↔ jongpil `food_code` (농진청)
//   FoodCandidate.confidence    ↔ jongpil 0~1 float
//   FoodCandidate.source        ↔ jongpil "yolo_v8" | "google_vision"

class Meal {
  final String id;
  final String userId;
  final DateTime? takenAt;
  final String? photoUrl;
  final List<FoodCandidate>? candidates;
  final bool? reviewFlag;
  final double? gramsInput;
  final String? servingInput;
  final Map<String, dynamic>? raw;

  const Meal({
    required this.id,
    required this.userId,
    this.takenAt,
    this.photoUrl,
    this.candidates,
    this.reviewFlag,
    this.gramsInput,
    this.servingInput,
    this.raw,
  });

  factory Meal.fromJson(Map<String, dynamic> json) {
    final List<dynamic>? candsRaw = json['candidates'] as List<dynamic>?;
    return Meal(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? json['userId'] ?? '').toString(),
      takenAt: _parseDate(json['taken_at']),
      photoUrl: (json['photo_url'] ?? json['photoUrl']) as String?,
      candidates: candsRaw == null
          ? null
          : candsRaw
              .map((e) => FoodCandidate.fromJson(Map<String, dynamic>.from(e as Map)))
              .toList(),
      reviewFlag: (json['review_flag'] ?? json['needs_user_review']) as bool?,
      gramsInput: (json['grams_input'] as num?)?.toDouble(),
      servingInput: json['serving_input'] as String?,
      raw: Map<String, dynamic>.from(json),
    );
  }
}

class FoodCandidate {
  final String? foodCode;
  final String? canonicalName;
  final double? confidence;
  final String? source;
  final Map<String, dynamic>? raw;

  const FoodCandidate({
    this.foodCode,
    this.canonicalName,
    this.confidence,
    this.source,
    this.raw,
  });

  factory FoodCandidate.fromJson(Map<String, dynamic> json) {
    return FoodCandidate(
      foodCode: (json['food_code'] ?? json['foodCode']) as String?,
      canonicalName: (json['canonical_name'] ??
          json['name_ko'] ??
          json['class_name_ko']) as String?,
      confidence: (json['confidence'] as num?)?.toDouble(),
      source: json['source'] as String?,
      raw: Map<String, dynamic>.from(json),
    );
  }
}

class FoodNutritionProfile {
  final String? foodCode;
  final String? canonicalName;
  final String? category;
  final double? baseAmountGrams;
  final String? defaultServing;
  final Map<String, dynamic>? nutrientsPer100g;
  final List<String>? highlights;
  final List<String>? cautions;
  final bool? needsUserReview;
  final Map<String, dynamic>? raw;

  const FoodNutritionProfile({
    this.foodCode,
    this.canonicalName,
    this.category,
    this.baseAmountGrams,
    this.defaultServing,
    this.nutrientsPer100g,
    this.highlights,
    this.cautions,
    this.needsUserReview,
    this.raw,
  });

  factory FoodNutritionProfile.fromJson(Map<String, dynamic> json) {
    return FoodNutritionProfile(
      foodCode: (json['food_code'] ?? json['foodCode']) as String?,
      canonicalName: (json['canonical_name'] ?? json['name_ko']) as String?,
      category: json['category'] as String?,
      baseAmountGrams: (json['base_amount_grams'] as num?)?.toDouble(),
      defaultServing: json['default_serving'] as String?,
      nutrientsPer100g: json['nutrients_per_100g'] == null
          ? null
          : Map<String, dynamic>.from(json['nutrients_per_100g'] as Map),
      highlights: _stringList(json['highlights']),
      cautions: _stringList(json['cautions']),
      needsUserReview: json['needs_user_review'] as bool?,
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
