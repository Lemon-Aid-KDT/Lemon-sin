// models/daily_score.dart — 하루 점수 + 다음 행동 한 줄
//
// 참조: mobile/CLAUDE.md §3.2 "하루 마무리 — 점수 + 다음 할 일 한 줄"
// 사용자와 함께 디자인 결정 진행 중 — 마지막 디자인 협의 시점에 다시 손볼 것.
//
// integration_notes.md §6 미확인 영역:
//   yeong-tech 응답에 단일 0~100 점수 키 명확히 없음.
//   대안 1 — dashboard 의 `activity.latest_activity_score` (0~120 float)
//   대안 2 — 모바일 측 집계 (영양 + 활동 + 체중 가중)
//   여기선 mock 가안 — 합치기 시 fromJson 만 수정.

class DailyScore {
  final String userId;
  final DateTime? date;

  /// 0~100 / 0~1 / "82" 모두 흡수 가능. 화면에서 정수 처리.
  final num? totalScore;

  final String? nextActionHint;
  final num? deltaFromYesterday;
  final DateTime? updatedAt;
  final Map<String, dynamic>? raw;

  const DailyScore({
    required this.userId,
    this.date,
    this.totalScore,
    this.nextActionHint,
    this.deltaFromYesterday,
    this.updatedAt,
    this.raw,
  });

  factory DailyScore.fromJson(Map<String, dynamic> json) {
    return DailyScore(
      userId: (json['user_id'] ?? json['userId'] ?? '').toString(),
      date: _parseDate(json['date']),
      totalScore: (json['total_score'] ??
              json['totalScore'] ??
              json['latest_activity_score'])
          as num?,
      nextActionHint:
          (json['next_action_hint'] ?? json['nextActionHint']) as String?,
      deltaFromYesterday:
          (json['delta_from_yesterday'] ?? json['deltaFromYesterday']) as num?,
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
