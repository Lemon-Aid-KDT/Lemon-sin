class SupplementAnalysisPreview {
  SupplementAnalysisPreview({
    required this.analysisId,
    required this.status,
    required this.ocrProvider,
    required this.warnings,
  });

  factory SupplementAnalysisPreview.fromJson(Map<String, dynamic> json) {
    return SupplementAnalysisPreview(
      analysisId: json['analysis_id'] as String? ?? '',
      status: json['status'] as String? ?? 'unknown',
      ocrProvider: json['ocr_provider'] as String? ?? 'unknown',
      warnings: _stringList(json['warnings']),
    );
  }

  final String analysisId;
  final String status;
  final String ocrProvider;
  final List<String> warnings;
}

List<String> _stringList(Object? value) {
  if (value is! List<dynamic>) {
    return <String>[];
  }
  return value.whereType<String>().toList(growable: false);
}
