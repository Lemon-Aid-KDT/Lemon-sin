/// Backend `POST /api/v1/supplements/analyze/comprehensive` 의 입출력을 위한
/// Dart 모델. SupplementAnalysisPreview 의 후속 호출로 5-card UI 의 5종 카드
/// 데이터를 모두 채운다.
library;

import 'package:flutter/foundation.dart';

/// 만성질환 인디케이션 토큰 (Pydantic ChronicCondition Literal 과 일치).
typedef ChronicCondition = String;

/// `ComprehensiveIngredient` 입력 구조.
@immutable
class ComprehensiveIngredientPayload {
  const ComprehensiveIngredientPayload({
    required this.displayName,
    this.nutrientCode,
    this.amount,
    this.unit,
  });

  final String displayName;
  final String? nutrientCode;
  final double? amount;
  final String? unit;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'display_name': displayName,
        if (nutrientCode != null) 'nutrient_code': nutrientCode,
        if (amount != null) 'amount': amount,
        if (unit != null) 'unit': unit,
      };
}

/// `UserProfileInput` 입력 구조.
@immutable
class UserProfilePayload {
  const UserProfilePayload({
    required this.age,
    required this.sex,
    this.chronicConditions = const <ChronicCondition>[],
    this.isPregnant = false,
  });

  final int age;
  final String sex; // 'male' | 'female'
  final List<ChronicCondition> chronicConditions;
  final bool isPregnant;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'age': age,
        'sex': sex,
        'chronic_conditions': chronicConditions,
        'is_pregnant': isPregnant,
      };
}

@immutable
class DeficientNutrient {
  const DeficientNutrient({
    required this.nutrientCode,
    required this.displayName,
    required this.currentIntake,
    required this.recommendedIntake,
    required this.unit,
    required this.deficitRatio,
  });

  final String nutrientCode;
  final String displayName;
  final double currentIntake;
  final double recommendedIntake;
  final String unit;
  final double deficitRatio;

  factory DeficientNutrient.fromJson(Map<String, dynamic> json) {
    return DeficientNutrient(
      nutrientCode: json['nutrient_code'] as String? ?? '',
      displayName: json['display_name'] as String? ?? '',
      currentIntake: (json['current_intake'] as num?)?.toDouble() ?? 0.0,
      recommendedIntake: (json['recommended_intake'] as num?)?.toDouble() ?? 0.0,
      unit: json['unit'] as String? ?? '',
      deficitRatio: (json['deficit_ratio'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

@immutable
class ExcessiveNutrient {
  const ExcessiveNutrient({
    required this.nutrientCode,
    required this.displayName,
    required this.currentIntake,
    required this.upperLimit,
    required this.unit,
    required this.excessRatio,
  });

  final String nutrientCode;
  final String displayName;
  final double currentIntake;
  final double upperLimit;
  final String unit;
  final double excessRatio;

  factory ExcessiveNutrient.fromJson(Map<String, dynamic> json) {
    return ExcessiveNutrient(
      nutrientCode: json['nutrient_code'] as String? ?? '',
      displayName: json['display_name'] as String? ?? '',
      currentIntake: (json['current_intake'] as num?)?.toDouble() ?? 0.0,
      upperLimit: (json['upper_limit'] as num?)?.toDouble() ?? 0.0,
      unit: json['unit'] as String? ?? '',
      excessRatio: (json['excess_ratio'] as num?)?.toDouble() ?? 1.0,
    );
  }
}

@immutable
class CautionaryComponent {
  const CautionaryComponent({
    required this.component,
    required this.reason,
    required this.severity,
    required this.message,
  });

  final String component;
  final String reason;
  final String severity; // 'low' | 'medium' | 'high'
  final String message;

  factory CautionaryComponent.fromJson(Map<String, dynamic> json) {
    return CautionaryComponent(
      component: json['component'] as String? ?? '',
      reason: json['reason'] as String? ?? '',
      severity: json['severity'] as String? ?? 'low',
      message: json['message'] as String? ?? '',
    );
  }
}

@immutable
class PurposeTarget {
  const PurposeTarget({
    required this.condition,
    required this.relevanceScore,
    required this.evidenceLevel,
    required this.message,
  });

  final ChronicCondition condition;
  final double relevanceScore;
  final String evidenceLevel; // 'strong' | 'moderate' | 'weak' | 'insufficient'
  final String message;

  factory PurposeTarget.fromJson(Map<String, dynamic> json) {
    return PurposeTarget(
      condition: json['condition'] as String? ?? '',
      relevanceScore: (json['relevance_score'] as num?)?.toDouble() ?? 0.0,
      evidenceLevel: json['evidence_level'] as String? ?? 'insufficient',
      message: json['message'] as String? ?? '',
    );
  }
}

@immutable
class SupplementComprehensiveAnalysis {
  const SupplementComprehensiveAnalysis({
    required this.persona,
    required this.deficientNutrients,
    required this.excessiveNutrients,
    required this.cautionaryComponents,
    required this.dietScore,
    required this.dietScoreLabel,
    required this.dietScoreMessage,
    required this.purposeTargets,
    required this.chronicDiseaseIndications,
    required this.algorithmVersion,
    required this.warnings,
    this.analysisId,
  });

  final String? analysisId;
  final String persona; // 'A' | 'B'
  final List<DeficientNutrient> deficientNutrients;
  final List<ExcessiveNutrient> excessiveNutrients;
  final List<CautionaryComponent> cautionaryComponents;
  final int dietScore; // 0~100
  final String dietScoreLabel; // 'excellent' | 'good' | 'moderate' | 'warning' | 'critical'
  final String dietScoreMessage;
  final List<PurposeTarget> purposeTargets;
  final List<ChronicCondition> chronicDiseaseIndications;
  final String algorithmVersion;
  final List<String> warnings;

  factory SupplementComprehensiveAnalysis.fromJson(Map<String, dynamic> json) {
    return SupplementComprehensiveAnalysis(
      analysisId: json['analysis_id'] as String?,
      persona: json['persona'] as String? ?? 'B',
      deficientNutrients: ((json['deficient_nutrients'] as List?) ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(DeficientNutrient.fromJson)
          .toList(growable: false),
      excessiveNutrients: ((json['excessive_nutrients'] as List?) ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(ExcessiveNutrient.fromJson)
          .toList(growable: false),
      cautionaryComponents: ((json['cautionary_components'] as List?) ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(CautionaryComponent.fromJson)
          .toList(growable: false),
      dietScore: (json['diet_score'] as num?)?.toInt() ?? 0,
      dietScoreLabel: json['diet_score_label'] as String? ?? 'moderate',
      dietScoreMessage: json['diet_score_message'] as String? ?? '',
      purposeTargets: ((json['purpose_targets'] as List?) ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(PurposeTarget.fromJson)
          .toList(growable: false),
      chronicDiseaseIndications: ((json['chronic_disease_indications'] as List?) ?? const [])
          .whereType<String>()
          .toList(growable: false),
      algorithmVersion: json['algorithm_version'] as String? ?? 'unknown',
      warnings: ((json['warnings'] as List?) ?? const [])
          .whereType<String>()
          .toList(growable: false),
    );
  }
}
