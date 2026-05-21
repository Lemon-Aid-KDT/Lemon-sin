/// Backend `POST /api/v1/supplements/analyze` 응답을 Flutter 측에서 strongly typed로
/// 다루기 위한 Dart 모델.
///
/// 백엔드의 Pydantic 모델 `SupplementAnalysisPreview` (Nutrition-backend
/// `src/models/schemas/supplement.py:451`) 와 1:1 매핑된다. nested 클래스가 매우
/// 많아 핵심 필드만 strongly typed로 정의하고 나머지는 원본 `Map<String, dynamic>`을
/// 유지해 schema drift에 강건하도록 한다.
library;

import 'package:flutter/foundation.dart';

/// `SupplementParsedProduct` 매핑 (제품명, 제조사, 1회 분량 등).
@immutable
class SupplementParsedProduct {
  const SupplementParsedProduct({
    this.productName,
    this.manufacturer,
    this.servingSize,
    this.dailyServings,
  });

  final String? productName;
  final String? manufacturer;
  final String? servingSize;
  final double? dailyServings;

  factory SupplementParsedProduct.fromJson(Map<String, dynamic> json) {
    return SupplementParsedProduct(
      productName: json['product_name'] as String?,
      manufacturer: json['manufacturer'] as String?,
      servingSize: json['serving_size'] as String?,
      dailyServings: (json['daily_servings'] as num?)?.toDouble(),
    );
  }
}

/// `SupplementIngredientCandidate` 매핑.
@immutable
class SupplementIngredientCandidate {
  const SupplementIngredientCandidate({
    required this.displayName,
    required this.confidence,
    required this.source,
    this.nutrientCode,
    this.amount,
    this.unit,
  });

  final String displayName;
  final String? nutrientCode;
  final double? amount;
  final String? unit;
  final double confidence;
  final String source;

  factory SupplementIngredientCandidate.fromJson(Map<String, dynamic> json) {
    return SupplementIngredientCandidate(
      displayName: json['display_name'] as String? ?? '',
      nutrientCode: json['nutrient_code'] as String?,
      amount: (json['amount'] as num?)?.toDouble(),
      unit: json['unit'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      source: json['source'] as String? ?? 'unknown',
    );
  }
}

/// `SupplementPreviewPrecaution` 의 단순 매핑 (자유 텍스트 위주).
@immutable
class SupplementPreviewPrecaution {
  const SupplementPreviewPrecaution({required this.text, this.severity});

  final String text;
  final String? severity;

  factory SupplementPreviewPrecaution.fromJson(Map<String, dynamic> json) {
    return SupplementPreviewPrecaution(
      text: json['text'] as String? ?? '',
      severity: json['severity'] as String?,
    );
  }
}

/// `SupplementAnalysisPreview` 의 핵심 필드 매핑.
///
/// 모든 nested 객체는 nullable + 누락 시 빈 리스트/null. 백엔드 schema가
/// 진화해도 client 가 crash 하지 않도록 방어적 파싱을 사용한다.
@immutable
class SupplementAnalysisPreview {
  const SupplementAnalysisPreview({
    required this.analysisId,
    required this.status,
    required this.parsedProduct,
    required this.ingredientCandidates,
    required this.precautions,
    required this.warnings,
    required this.lowConfidenceFields,
    required this.algorithmVersion,
    this.layoutAvailable = false,
    this.layoutFallbackReason,
    this.analysisScope = 'unknown',
    this.actionRequired = 'none',
    this.sourceType = 'uploaded_image',
    this.rawPayload,
  });

  final String analysisId;
  final String status;
  final SupplementParsedProduct parsedProduct;
  final List<SupplementIngredientCandidate> ingredientCandidates;
  final List<SupplementPreviewPrecaution> precautions;
  final List<String> warnings;
  final List<String> lowConfidenceFields;
  final String algorithmVersion;
  final bool layoutAvailable;
  final String? layoutFallbackReason;

  /// 분석 적용 범위. `nutrition_facts` 등 backend 의 분기에 사용.
  final String analysisScope;

  /// 사용자에게 요청해야 할 후속 액션 (`none` / `retake` / `confirm` 등).
  final String actionRequired;

  /// 업로드 이미지의 보수적 분류 (`uploaded_image` / `camera_capture` 등).
  final String sourceType;

  /// 백엔드 응답 원본 (디버그 / 향후 확장용).
  final Map<String, dynamic>? rawPayload;

  factory SupplementAnalysisPreview.fromJson(Map<String, dynamic> json) {
    return SupplementAnalysisPreview(
      analysisId: (json['analysis_id'] ?? '').toString(),
      status: json['status'] as String? ?? 'unknown',
      parsedProduct: SupplementParsedProduct.fromJson(
        (json['parsed_product'] as Map<String, dynamic>?) ?? const <String, dynamic>{},
      ),
      ingredientCandidates: ((json['ingredient_candidates'] as List?) ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(SupplementIngredientCandidate.fromJson)
          .toList(growable: false),
      precautions: ((json['precautions'] as List?) ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(SupplementPreviewPrecaution.fromJson)
          .toList(growable: false),
      warnings: ((json['warnings'] as List?) ?? const [])
          .whereType<String>()
          .toList(growable: false),
      lowConfidenceFields: ((json['low_confidence_fields'] as List?) ?? const [])
          .whereType<String>()
          .toList(growable: false),
      algorithmVersion: json['algorithm_version'] as String? ?? 'unknown',
      layoutAvailable: json['layout_available'] as bool? ?? false,
      layoutFallbackReason: json['layout_fallback_reason'] as String?,
      analysisScope: json['analysis_scope'] as String? ?? 'unknown',
      actionRequired: json['action_required'] as String? ?? 'none',
      sourceType: json['source_type'] as String? ?? 'uploaded_image',
      rawPayload: json,
    );
  }
}

/// 분석 호출 시 발생하는 도메인 예외. HTTP 상태별 한국어 메시지로 변환된다.
class SupplementAnalyzeException implements Exception {
  SupplementAnalyzeException({
    required this.statusCode,
    required this.code,
    required this.message,
  });

  final int statusCode;
  final String code;
  final String message;

  /// HTTP 상태/에러 코드별 사용자 친화 한국어 메시지.
  String get userMessage {
    switch (statusCode) {
      case 401:
        return '로그인이 필요해요. 다시 시도해주세요.';
      case 409:
        return '같은 사진을 다시 분석 요청했어요. 잠시 후 다시 시도해주세요.';
      case 413:
        return '이미지가 너무 커요. 더 작은 이미지를 사용해주세요.';
      case 415:
        return '지원하지 않는 이미지 형식이에요.';
      case 422:
        return '이미지를 읽지 못했어요. 다른 사진으로 다시 시도해주세요.';
      case 429:
        return '잠시 후 다시 시도해주세요.';
      case 0:
        return '네트워크 연결을 확인해주세요.';
      default:
        return message.isNotEmpty ? message : '분석 중 문제가 발생했어요.';
    }
  }

  @override
  String toString() => 'SupplementAnalyzeException($statusCode, $code): $message';
}
