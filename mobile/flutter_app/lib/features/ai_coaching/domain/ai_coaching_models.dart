class DailyCoachingRequest {
  DailyCoachingRequest({
    required this.requestId,
    required this.userId,
    required this.context,
    required this.payload,
  });

  factory DailyCoachingRequest.confirmedMealSample() {
    final String requestId = 'mobile-daily-coaching-${DateTime.now().millisecondsSinceEpoch}';
    return DailyCoachingRequest(
      requestId: requestId,
      userId: 'mobile-client-placeholder',
      context: <String, dynamic>{
        'profile': <String, dynamic>{
          'age': 52,
          'gender': 'male',
          'goals': <String>['meal_management'],
          'chronic_conditions': <String>['hypertension'],
          'medications': <String>['blood_pressure_medication'],
        },
      },
      payload: <String, dynamic>{
        'date': DateTime.now().toIso8601String().substring(0, 10),
        'sources': <Map<String, dynamic>>[
          <String, dynamic>{
            'source_type': 'food_ocr',
            'image_id': '$requestId-image',
            'raw_ocr_text': 'instant noodles sodium 2600mg',
            'user_confirmed': true,
          },
        ],
        'foods': <Map<String, dynamic>>[
          <String, dynamic>{
            'name': 'instant noodles',
            'meal_type': 'lunch',
            'serving_label': '1 bowl',
            'nutrients': <Map<String, dynamic>>[
              <String, dynamic>{'name': 'sodium', 'amount': 2600, 'unit': 'mg'},
              <String, dynamic>{'name': 'protein', 'amount': 25, 'unit': 'g'},
            ],
          },
        ],
        'supplements': <Map<String, dynamic>>[],
        'health_trends': <Map<String, dynamic>>[],
      },
    );
  }

  final String requestId;
  final String userId;
  final Map<String, dynamic> context;
  final Map<String, dynamic> payload;

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'request_id': requestId,
      'user_id': userId,
      'context': context,
      'payload': payload,
    };
  }
}

class DailyCoachingResponse {
  DailyCoachingResponse({
    required this.requestId,
    required this.status,
    required this.approvalStatus,
    required this.message,
    required this.provider,
    required this.usedTools,
    required this.findings,
    required this.safetyWarnings,
  });

  factory DailyCoachingResponse.fromJson(Map<String, dynamic> json) {
    return DailyCoachingResponse(
      requestId: json['request_id'] as String? ?? '',
      status: json['status'] as String? ?? 'unknown',
      approvalStatus: json['approval_status'] as String? ?? 'unknown',
      message: json['message'] as String? ?? '',
      provider: json['provider'] as String? ?? 'unknown',
      usedTools: _stringList(json['used_tools']),
      findings: _mapList(json['findings']),
      safetyWarnings: _stringList(json['safety_warnings']),
    );
  }

  final String requestId;
  final String status;
  final String approvalStatus;
  final String message;
  final String provider;
  final List<String> usedTools;
  final List<Map<String, dynamic>> findings;
  final List<String> safetyWarnings;

  bool get usedAgentMemory => usedTools.contains('agent_memory');
}

List<String> _stringList(Object? value) {
  if (value is! List<dynamic>) {
    return <String>[];
  }
  return value.whereType<String>().toList(growable: false);
}

List<Map<String, dynamic>> _mapList(Object? value) {
  if (value is! List<dynamic>) {
    return <Map<String, dynamic>>[];
  }
  return value
      .whereType<Map<dynamic, dynamic>>()
      .map((Map<dynamic, dynamic> item) => Map<String, dynamic>.from(item))
      .toList(growable: false);
}
