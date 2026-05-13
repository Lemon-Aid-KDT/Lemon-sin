// models/user.dart — 사용자 / 프로필 모델 (느슨한 컨테이너)
//
// 참조: mobile/CLAUDE.md §6 + mobile/docs/integration_notes.md §3 (sunghoon-database)
// 사용자와 함께 디자인 결정 진행 중 — 마지막 디자인 협의 시점에 다시 손볼 것.
//
// 원칙 (mobile/lib/models/README.md):
//   - 필수: id / userId 만 final.
//   - 나머지 모두 nullable.
//   - raw 로 원본 JSON 통째 보존 → 키명 차이 합치기 시 fromJson 만 손보면 됨.
//
// 합치기 키 차이 (integration_notes.md):
//   nickname  ↔ sunghoon `display_name`
//   age/sex/height_cm/weight_kg ↔ yeong-tech UserProfile (확정)
//   gender    ↔ sunghoon "M"/"F"  vs  yeong-tech "male"/"female"
//   user_id   ↔ sunghoon int      vs  yeong-tech UUID

class User {
  final String id;
  final String? email;
  final String? nickname;
  final DateTime? createdAt;
  final DateTime? lastLoginAt;
  final Map<String, dynamic>? raw;

  const User({
    required this.id,
    this.email,
    this.nickname,
    this.createdAt,
    this.lastLoginAt,
    this.raw,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: (json['id'] ?? json['user_id'] ?? '').toString(),
      email: json['email'] as String?,
      nickname: (json['nickname'] ?? json['display_name']) as String?,
      createdAt: _parseDate(json['created_at']),
      lastLoginAt: _parseDate(json['last_login_at']),
      raw: Map<String, dynamic>.from(json),
    );
  }
}

class Profile {
  final String userId;
  final int? age;
  final String? gender;
  final double? heightCm;
  final double? weightKg;
  final List<String>? chronicDiseases;
  final List<String>? medications;
  final DateTime? updatedAt;
  final Map<String, dynamic>? raw;

  const Profile({
    required this.userId,
    this.age,
    this.gender,
    this.heightCm,
    this.weightKg,
    this.chronicDiseases,
    this.medications,
    this.updatedAt,
    this.raw,
  });

  factory Profile.fromJson(Map<String, dynamic> json) {
    return Profile(
      userId: (json['user_id'] ?? json['userId'] ?? json['id'] ?? '').toString(),
      age: (json['age'] as num?)?.toInt(),
      // sunghoon 은 "M"/"F", yeong-tech 는 "male"/"female" — 그대로 String 으로 보관.
      gender: (json['gender'] ?? json['sex']) as String?,
      heightCm: (json['height_cm'] as num?)?.toDouble(),
      weightKg: (json['weight_kg'] as num?)?.toDouble(),
      chronicDiseases: _stringList(json['chronic_diseases']),
      medications: _stringList(json['medications']),
      updatedAt: _parseDate(json['updated_at']),
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
