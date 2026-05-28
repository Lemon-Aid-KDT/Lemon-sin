import '../../shared/models/json_readers.dart';

Map<String, Object?> _readOptionalJsonMap(
  Map<String, dynamic> json,
  String key,
) {
  final Object? value = json[key];
  if (value == null) {
    return const <String, Object?>{};
  }
  if (value is Map<String, dynamic>) {
    return Map<String, Object?>.from(value);
  }
  if (value is Map<Object?, Object?>) {
    return Map<String, Object?>.from(value);
  }
  throw FormatException('Expected optional object field "$key".');
}

/// One locally selected supplement image and its intended label role.
class SupplementImageUpload {
  /// Creates a local supplement image upload descriptor.
  const SupplementImageUpload({required this.path, this.role = 'unknown'});

  /// Local image path selected by the user.
  final String path;

  /// Client-side image role hint sent to the backend.
  final String role;
}

/// Lightweight backend-created multi-image analysis session.
class SupplementAnalysisSession {
  /// Creates a supplement analysis session descriptor.
  const SupplementAnalysisSession({
    required this.analysisGroupId,
    required this.status,
    required this.imageCount,
    required this.maxImages,
    required this.missingRequiredSections,
    required this.actionRequired,
  });

  /// Backend group id used by subsequent image uploads.
  final String analysisGroupId;

  /// Session lifecycle status.
  final String status;

  /// Number of images currently tied to this session.
  final int imageCount;

  /// Maximum image count accepted by the backend.
  final int maxImages;

  /// Required label sections still expected from the user.
  final List<String> missingRequiredSections;

  /// Next action required before relying on this session.
  final String actionRequired;

  /// Parses a backend-created analysis session response.
  factory SupplementAnalysisSession.fromJson(Map<String, dynamic> json) {
    return SupplementAnalysisSession(
      analysisGroupId: readString(json, 'analysis_group_id'),
      status: readOptionalString(json, 'status') ?? 'created',
      imageCount: readOptionalInt(json, 'image_count') ?? 0,
      maxImages: readOptionalInt(json, 'max_images') ?? 6,
      missingRequiredSections: readOptionalStringList(
        json,
        'missing_required_sections',
      ),
      actionRequired:
          readOptionalString(json, 'action_required') ??
          'additional_label_image_required',
    );
  }
}

/// Multi-image supplement analysis response before user confirmation.
class SupplementMultiImageAnalysisPreview {
  /// Creates a multi-image analysis preview.
  const SupplementMultiImageAnalysisPreview({
    required this.analysisGroupId,
    required this.imageCount,
    required this.previews,
    this.mergedPreview,
    required this.missingRequiredSections,
    required this.actionRequired,
    required this.pipelineMetadata,
    required this.expiresAt,
  });

  /// Ephemeral backend group id for the uploaded batch.
  final String analysisGroupId;

  /// Number of accepted images in the batch.
  final int imageCount;

  /// Per-image analysis previews.
  final List<SupplementAnalysisPreview> previews;

  /// Backend-assembled merged review preview using bounded per-image evidence.
  final SupplementAnalysisPreview? mergedPreview;

  /// Required label sections still missing after aggregating the batch.
  final List<String> missingRequiredSections;

  /// Batch-level next action before relying on the preview.
  final String actionRequired;

  /// Sanitized aggregate OCR, YOLO, and parser metadata.
  final SupplementImagePipelineMetadata pipelineMetadata;

  /// Earliest preview expiration time when provided by the backend.
  final DateTime? expiresAt;

  /// Parses a backend multi-image analysis preview.
  factory SupplementMultiImageAnalysisPreview.fromJson(
    Map<String, dynamic> json,
  ) {
    return SupplementMultiImageAnalysisPreview(
      analysisGroupId: readString(json, 'analysis_group_id'),
      imageCount: readOptionalInt(json, 'image_count') ?? 1,
      previews: readList(json, 'previews')
          .whereType<Map<String, dynamic>>()
          .map(SupplementAnalysisPreview.fromJson)
          .toList(growable: false),
      mergedPreview: readOptionalObject(json, 'merged_preview') == null
          ? null
          : SupplementAnalysisPreview.fromJson(
              readObject(json, 'merged_preview'),
            ),
      missingRequiredSections: readOptionalStringList(
        json,
        'missing_required_sections',
      ),
      actionRequired: readOptionalString(json, 'action_required') ?? 'none',
      pipelineMetadata: readOptionalObject(json, 'pipeline_metadata') == null
          ? SupplementImagePipelineMetadata.intakeOnly
          : SupplementImagePipelineMetadata.fromJson(
              readObject(json, 'pipeline_metadata'),
            ),
      expiresAt: readOptionalString(json, 'expires_at') == null
          ? null
          : DateTime.parse(readString(json, 'expires_at')),
    );
  }

  /// First preview that can seed the existing single-preview review flow.
  SupplementAnalysisPreview? get primaryPreview {
    if (mergedPreview != null) {
      return mergedPreview;
    }
    if (previews.isEmpty) {
      return null;
    }
    for (final SupplementAnalysisPreview preview in previews) {
      if (preview.ingredientCandidates.isNotEmpty ||
          preview.labelSections.isNotEmpty) {
        return preview;
      }
    }
    return previews.first;
  }
}

/// Supplement OCR and parsing preview before user confirmation.
class SupplementAnalysisPreview {
  /// Creates an analysis preview.
  const SupplementAnalysisPreview({
    required this.analysisId,
    required this.status,
    required this.parsedProduct,
    required this.ingredientCandidates,
    required this.layoutAvailable,
    required this.layoutFallbackReason,
    required this.labelSections,
    required this.intakeMethod,
    required this.precautions,
    required this.functionalClaims,
    required this.evidenceSpans,
    required this.imageQualityReport,
    required this.analysisScope,
    required this.actionRequired,
    required this.detectedProductRegions,
    required this.selectedRegionId,
    required this.missingRequiredSections,
    required this.imageRole,
    required this.multiImageGroupId,
    required this.sourceType,
    required this.identityConflict,
    this.pipelineMetadata = SupplementImagePipelineMetadata.intakeOnly,
    required this.lowConfidenceFields,
    required this.warnings,
    required this.algorithmVersion,
    required this.sourceManifestVersion,
    required this.expiresAt,
  });

  /// Temporary analysis identifier.
  final String analysisId;

  /// Preview status, such as `requires_confirmation`.
  final String status;

  /// Product-level parsed fields.
  final SupplementParsedProduct parsedProduct;

  /// Candidate ingredients requiring user review.
  final List<SupplementIngredientCandidate> ingredientCandidates;

  /// Whether coordinate-derived layout sections are available.
  final bool layoutAvailable;

  /// Safe fallback reason when layout parsing is unavailable.
  final String? layoutFallbackReason;

  /// Bounded label sections for mobile confirmation.
  final List<SupplementPreviewLabelSection> labelSections;

  /// Label-supported intake method candidate.
  final SupplementPreviewIntakeMethod intakeMethod;

  /// Label-supported precaution candidates.
  final List<SupplementPreviewPrecaution> precautions;

  /// Label-supported functional claim candidates.
  final List<SupplementPreviewFunctionalClaim> functionalClaims;

  /// Short redacted evidence excerpts.
  final List<SupplementPreviewEvidenceSpan> evidenceSpans;

  /// Redacted image-quality report returned by the backend.
  final SupplementImageQualityReport? imageQualityReport;

  /// Scope that the preview can safely represent.
  final String analysisScope;

  /// Next user action required before relying on the preview.
  final String actionRequired;

  /// Bounded product or label regions for review UI.
  final List<SupplementDetectedProductRegion> detectedProductRegions;

  /// Backend-selected region id when safe.
  final String? selectedRegionId;

  /// Label sections that need additional image evidence.
  final List<String> missingRequiredSections;

  /// Inferred role of the uploaded image.
  final String imageRole;

  /// Optional multi-image group id.
  final String? multiImageGroupId;

  /// Conservative source classification.
  final String sourceType;

  /// Optional review-only barcode/label identity conflict.
  final SupplementIdentityConflict? identityConflict;

  /// Non-sensitive OCR, YOLO, and parser pipeline metadata.
  final SupplementImagePipelineMetadata pipelineMetadata;

  /// Field names that need extra attention.
  final List<String> lowConfidenceFields;

  /// Safe preview warnings returned by the backend.
  final List<String> warnings;

  /// Parsing contract version.
  final String algorithmVersion;

  /// Reference source manifest version.
  final String? sourceManifestVersion;

  /// Preview expiration time.
  final DateTime expiresAt;

  /// Parses a backend supplement analysis preview.
  factory SupplementAnalysisPreview.fromJson(Map<String, dynamic> json) {
    return SupplementAnalysisPreview(
      analysisId: readString(json, 'analysis_id'),
      status: readString(json, 'status'),
      parsedProduct: SupplementParsedProduct.fromJson(
        readObject(json, 'parsed_product'),
      ),
      ingredientCandidates: readList(json, 'ingredient_candidates')
          .whereType<Map<String, dynamic>>()
          .map(SupplementIngredientCandidate.fromJson)
          .toList(growable: false),
      layoutAvailable: json['layout_available'] == true,
      layoutFallbackReason: readOptionalString(json, 'layout_fallback_reason'),
      labelSections: readOptionalList(json, 'label_sections')
          .whereType<Map<String, dynamic>>()
          .map(SupplementPreviewLabelSection.fromJson)
          .toList(growable: false),
      intakeMethod: readOptionalObject(json, 'intake_method') == null
          ? SupplementPreviewIntakeMethod.empty
          : SupplementPreviewIntakeMethod.fromJson(
              readObject(json, 'intake_method'),
            ),
      precautions: readOptionalList(json, 'precautions')
          .whereType<Map<String, dynamic>>()
          .map(SupplementPreviewPrecaution.fromJson)
          .toList(growable: false),
      functionalClaims: readOptionalList(json, 'functional_claims')
          .whereType<Map<String, dynamic>>()
          .map(SupplementPreviewFunctionalClaim.fromJson)
          .toList(growable: false),
      evidenceSpans: readOptionalList(json, 'evidence_spans')
          .whereType<Map<String, dynamic>>()
          .map(SupplementPreviewEvidenceSpan.fromJson)
          .toList(growable: false),
      imageQualityReport:
          readOptionalObject(json, 'image_quality_report') == null
          ? null
          : SupplementImageQualityReport.fromJson(
              readObject(json, 'image_quality_report'),
            ),
      analysisScope: readOptionalString(json, 'analysis_scope') ?? 'unknown',
      actionRequired: readOptionalString(json, 'action_required') ?? 'none',
      detectedProductRegions: readOptionalList(json, 'detected_product_regions')
          .whereType<Map<String, dynamic>>()
          .map(SupplementDetectedProductRegion.fromJson)
          .toList(growable: false),
      selectedRegionId: readOptionalString(json, 'selected_region_id'),
      missingRequiredSections: readOptionalStringList(
        json,
        'missing_required_sections',
      ),
      imageRole: readOptionalString(json, 'image_role') ?? 'unknown',
      multiImageGroupId: readOptionalString(json, 'multi_image_group_id'),
      sourceType: readOptionalString(json, 'source_type') ?? 'uploaded_image',
      identityConflict: readOptionalObject(json, 'identity_conflict') == null
          ? null
          : SupplementIdentityConflict.fromJson(
              readObject(json, 'identity_conflict'),
            ),
      pipelineMetadata: readOptionalObject(json, 'pipeline_metadata') == null
          ? SupplementImagePipelineMetadata.intakeOnly
          : SupplementImagePipelineMetadata.fromJson(
              readObject(json, 'pipeline_metadata'),
            ),
      lowConfidenceFields: readOptionalStringList(
        json,
        'low_confidence_fields',
      ),
      warnings: readOptionalStringList(json, 'warnings'),
      algorithmVersion: readString(json, 'algorithm_version'),
      sourceManifestVersion: readOptionalString(
        json,
        'source_manifest_version',
      ),
      expiresAt: DateTime.parse(readString(json, 'expires_at')),
    );
  }

  /// Whether image risk metadata needs user attention.
  bool get requiresImageAction => actionRequired != 'none';

  /// Whether the current image action blocks direct supplement registration.
  bool get blocksRegistrationForImageRisk {
    return actionRequired == 'product_region_selection_required' ||
        actionRequired == 'additional_label_image_required' ||
        actionRequired == 'blocked';
  }

  /// Whether registration should show an extra image-risk confirmation dialog.
  bool get promptsImageRiskConfirmation {
    return actionRequired == 'retake_recommended' ||
        actionRequired == 'review_required' ||
        identityConflict != null;
  }

  /// Human-readable action label for compact preview UI.
  String get imageActionLabel {
    if (actionRequired == 'product_region_selection_required') {
      return 'Select product region';
    }
    if (actionRequired == 'additional_label_image_required') {
      return 'Add supplement facts image';
    }
    if (actionRequired == 'retake_recommended') {
      return 'Retake recommended';
    }
    if (actionRequired == 'review_required') {
      return 'Image review required';
    }
    if (actionRequired == 'blocked') {
      return 'Image blocked';
    }
    return 'No image action';
  }
}

/// Non-sensitive image analysis pipeline metadata.
class SupplementImagePipelineMetadata {
  /// Creates image analysis pipeline metadata.
  const SupplementImagePipelineMetadata({
    required this.intakeCompleted,
    this.imageCount = 1,
    this.imageRole = 'unknown',
    required this.visionRoiUsed,
    required this.ocrProvider,
    this.ocrTextPresent = false,
    this.ocrConfidenceBucket = 'none',
    this.roiCount = 0,
    this.sectionCount = 0,
    required this.llmParserUsed,
    this.parserContractVersion,
    this.missingRequiredSections = const <String>[],
    required this.rawImageStored,
    required this.rawOcrTextStored,
  });

  /// Default metadata for legacy intake-only previews.
  static const SupplementImagePipelineMetadata intakeOnly =
      SupplementImagePipelineMetadata(
        intakeCompleted: true,
        imageCount: 1,
        imageRole: 'unknown',
        visionRoiUsed: false,
        ocrProvider: 'intake-only',
        ocrTextPresent: false,
        ocrConfidenceBucket: 'none',
        roiCount: 0,
        sectionCount: 0,
        llmParserUsed: false,
        parserContractVersion: null,
        missingRequiredSections: <String>[],
        rawImageStored: false,
        rawOcrTextStored: false,
      );

  /// Whether validated image intake completed.
  final bool intakeCompleted;

  /// Number of uploaded images represented by this preview.
  final int imageCount;

  /// Inferred role for this image or capture group.
  final String imageRole;

  /// Whether backend YOLO ROI metadata was used before OCR.
  final bool visionRoiUsed;

  /// OCR-like provider label selected by the backend, if any.
  final String? ocrProvider;

  /// Whether OCR produced non-empty text without exposing the raw text.
  final bool ocrTextPresent;

  /// Coarse OCR confidence bucket returned by the backend.
  final String ocrConfidenceBucket;

  /// Number of safe ROI candidates represented by this preview.
  final int roiCount;

  /// Number of bounded label sections available for review.
  final int sectionCount;

  /// Whether the structured parser ran after OCR text extraction.
  final bool llmParserUsed;

  /// Backend parser contract or algorithm version.
  final String? parserContractVersion;

  /// Required label sections still missing from the evidence.
  final List<String> missingRequiredSections;

  /// Whether raw image bytes were retained.
  final bool rawImageStored;

  /// Whether raw OCR text was retained.
  final bool rawOcrTextStored;

  /// Parses sanitized pipeline metadata.
  factory SupplementImagePipelineMetadata.fromJson(Map<String, dynamic> json) {
    final int imageCount = readOptionalInt(json, 'image_count') ?? 1;
    final int roiCount = readOptionalInt(json, 'roi_count') ?? 0;
    final int sectionCount = readOptionalInt(json, 'section_count') ?? 0;
    return SupplementImagePipelineMetadata(
      intakeCompleted: json['intake_completed'] != false,
      imageCount: imageCount < 1 ? 1 : imageCount,
      imageRole: readOptionalString(json, 'image_role') ?? 'unknown',
      visionRoiUsed: json['vision_roi_used'] == true,
      ocrProvider: readOptionalString(json, 'ocr_provider'),
      ocrTextPresent: json['ocr_text_present'] == true,
      ocrConfidenceBucket: _normalizeConfidenceBucket(
        readOptionalString(json, 'ocr_confidence_bucket'),
      ),
      roiCount: roiCount < 0 ? 0 : roiCount,
      sectionCount: sectionCount < 0 ? 0 : sectionCount,
      llmParserUsed: json['llm_parser_used'] == true,
      parserContractVersion: readOptionalString(
        json,
        'parser_contract_version',
      ),
      missingRequiredSections: readOptionalStringList(
        json,
        'missing_required_sections',
      ),
      rawImageStored: json['raw_image_stored'] == true,
      rawOcrTextStored: json['raw_ocr_text_stored'] == true,
    );
  }

  static String _normalizeConfidenceBucket(String? value) {
    switch (value) {
      case 'unknown':
      case 'low':
      case 'medium':
      case 'high':
        return value!;
      case 'none':
      default:
        return 'none';
    }
  }
}

/// Redacted deterministic image-quality report.
class SupplementImageQualityReport {
  /// Creates an image-quality report.
  const SupplementImageQualityReport({
    required this.status,
    required this.issues,
    required this.metrics,
    required this.detectedRois,
    required this.retakeReasons,
  });

  /// Aggregate quality status.
  final String status;

  /// Bounded quality issues.
  final List<SupplementImageQualityIssue> issues;

  /// Numeric quality metrics without raw image or OCR text.
  final Map<String, Object?> metrics;

  /// Sanitized ROI metadata.
  final List<SupplementImageQualityRegion> detectedRois;

  /// Reason codes that should prompt a better image.
  final List<String> retakeReasons;

  /// Parses a backend image-quality report.
  factory SupplementImageQualityReport.fromJson(Map<String, dynamic> json) {
    return SupplementImageQualityReport(
      status: readString(json, 'status'),
      issues: readOptionalList(json, 'issues')
          .whereType<Map<String, dynamic>>()
          .map(SupplementImageQualityIssue.fromJson)
          .toList(growable: false),
      metrics: _readOptionalJsonMap(json, 'metrics'),
      detectedRois: readOptionalList(json, 'detected_rois')
          .whereType<Map<String, dynamic>>()
          .map(SupplementImageQualityRegion.fromJson)
          .toList(growable: false),
      retakeReasons: readOptionalStringList(json, 'retake_reasons'),
    );
  }
}

/// One bounded image-quality issue.
class SupplementImageQualityIssue {
  /// Creates an image-quality issue.
  const SupplementImageQualityIssue({
    required this.reasonCode,
    required this.severity,
    required this.message,
    required this.evidence,
  });

  /// Stable reason code.
  final String reasonCode;

  /// Review severity.
  final String severity;

  /// Safe user-facing message.
  final String message;

  /// Numeric or categorical evidence only.
  final Map<String, Object?> evidence;

  /// Parses a backend quality issue.
  factory SupplementImageQualityIssue.fromJson(Map<String, dynamic> json) {
    return SupplementImageQualityIssue(
      reasonCode: readString(json, 'reason_code'),
      severity: readString(json, 'severity'),
      message: readString(json, 'message'),
      evidence: _readOptionalJsonMap(json, 'evidence'),
    );
  }
}

/// Sanitized image-quality ROI metadata.
class SupplementImageQualityRegion {
  /// Creates a quality-region object.
  const SupplementImageQualityRegion({
    required this.label,
    required this.x,
    required this.y,
    required this.width,
    required this.height,
    required this.confidence,
    required this.areaRatio,
  });

  /// Detector or annotation label.
  final String? label;

  /// Left coordinate in input-image pixels.
  final int x;

  /// Top coordinate in input-image pixels.
  final int y;

  /// Region width in pixels.
  final int width;

  /// Region height in pixels.
  final int height;

  /// Detector confidence.
  final double confidence;

  /// Region area divided by full image area.
  final double? areaRatio;

  /// Parses backend ROI metadata.
  factory SupplementImageQualityRegion.fromJson(Map<String, dynamic> json) {
    return SupplementImageQualityRegion(
      label: readOptionalString(json, 'label'),
      x: readInt(json, 'x'),
      y: readInt(json, 'y'),
      width: readInt(json, 'width'),
      height: readInt(json, 'height'),
      confidence: readDouble(json, 'confidence'),
      areaRatio: readOptionalDouble(json, 'area_ratio'),
    );
  }
}

/// Selectable product or label region for review UI.
class SupplementDetectedProductRegion {
  /// Creates a selectable detected product region.
  const SupplementDetectedProductRegion({
    required this.regionId,
    required this.label,
    required this.x,
    required this.y,
    required this.width,
    required this.height,
    required this.confidence,
    required this.areaRatio,
    required this.selected,
  });

  /// Request-local region id.
  final String regionId;

  /// Detector or annotation label.
  final String? label;

  /// Left coordinate in input-image pixels.
  final int x;

  /// Top coordinate in input-image pixels.
  final int y;

  /// Region width in pixels.
  final int width;

  /// Region height in pixels.
  final int height;

  /// Detector confidence.
  final double confidence;

  /// Region area divided by full image area.
  final double? areaRatio;

  /// Whether this region was selected by the backend.
  final bool selected;

  /// Parses backend selectable ROI metadata.
  factory SupplementDetectedProductRegion.fromJson(Map<String, dynamic> json) {
    return SupplementDetectedProductRegion(
      regionId: readString(json, 'region_id'),
      label: readOptionalString(json, 'label'),
      x: readInt(json, 'x'),
      y: readInt(json, 'y'),
      width: readInt(json, 'width'),
      height: readInt(json, 'height'),
      confidence: readDouble(json, 'confidence'),
      areaRatio: readOptionalDouble(json, 'area_ratio'),
      selected: json['selected'] == true,
    );
  }
}

/// Review-only barcode and parsed-label identity conflict.
class SupplementIdentityConflict {
  /// Creates an identity-conflict object.
  const SupplementIdentityConflict({
    required this.conflictType,
    required this.severity,
    required this.message,
    required this.evidence,
  });

  /// Stable conflict code.
  final String conflictType;

  /// Review severity.
  final String severity;

  /// Safe user-facing message.
  final String message;

  /// Redacted numeric or categorical evidence.
  final Map<String, Object?> evidence;

  /// Parses backend identity-conflict metadata.
  factory SupplementIdentityConflict.fromJson(Map<String, dynamic> json) {
    return SupplementIdentityConflict(
      conflictType: readString(json, 'conflict_type'),
      severity: readString(json, 'severity'),
      message: readString(json, 'message'),
      evidence: _readOptionalJsonMap(json, 'evidence'),
    );
  }
}

/// Product-level supplement fields parsed from label text.
class SupplementParsedProduct {
  /// Creates parsed product fields.
  const SupplementParsedProduct({
    required this.productName,
    required this.manufacturer,
    required this.servingSize,
    required this.dailyServings,
  });

  /// Product name candidate.
  final String? productName;

  /// Manufacturer candidate.
  final String? manufacturer;

  /// Serving-size label text.
  final String? servingSize;

  /// Daily serving count candidate.
  final double? dailyServings;

  /// Empty parsed product fallback.
  static const SupplementParsedProduct empty = SupplementParsedProduct(
    productName: null,
    manufacturer: null,
    servingSize: null,
    dailyServings: null,
  );

  /// Parses backend parsed-product fields.
  factory SupplementParsedProduct.fromJson(Map<String, dynamic> json) {
    return SupplementParsedProduct(
      productName: readOptionalString(json, 'product_name'),
      manufacturer: readOptionalString(json, 'manufacturer'),
      servingSize: readOptionalString(json, 'serving_size'),
      dailyServings: readOptionalDouble(json, 'daily_servings'),
    );
  }
}

/// Ingredient candidate extracted from preview text.
class SupplementIngredientCandidate {
  /// Creates an ingredient candidate.
  const SupplementIngredientCandidate({
    required this.displayName,
    required this.nutrientCode,
    required this.amount,
    required this.unit,
    required this.confidence,
    required this.source,
  });

  /// Ingredient display name.
  final String displayName;

  /// Internal nutrient code when mapped.
  final String? nutrientCode;

  /// Amount per serving.
  final double? amount;

  /// Ingredient unit.
  final String? unit;

  /// Extraction confidence from 0.0 to 1.0.
  final double confidence;

  /// Source that produced this candidate.
  final String source;

  /// Parses a backend ingredient candidate.
  factory SupplementIngredientCandidate.fromJson(Map<String, dynamic> json) {
    return SupplementIngredientCandidate(
      displayName: readString(json, 'display_name'),
      nutrientCode: readOptionalString(json, 'nutrient_code'),
      amount: readOptionalDouble(json, 'amount'),
      unit: readOptionalString(json, 'unit'),
      confidence: readDouble(json, 'confidence'),
      source: readString(json, 'source'),
    );
  }
}

/// Short bounded evidence excerpt for supplement preview review.
class SupplementPreviewEvidenceSpan {
  /// Creates an evidence span.
  const SupplementPreviewEvidenceSpan({
    required this.spanId,
    required this.sourceType,
    required this.sectionType,
    required this.textExcerpt,
    required this.pageIndex,
    required this.cellRef,
    required this.confidence,
  });

  /// Stable evidence id.
  final String spanId;

  /// Evidence source bucket.
  final String sourceType;

  /// Normalized label section type.
  final String sectionType;

  /// Short redacted text excerpt.
  final String textExcerpt;

  /// Optional zero-based page index.
  final int? pageIndex;

  /// Optional layout cell reference.
  final String? cellRef;

  /// Optional OCR/layout confidence.
  final double? confidence;

  /// Parses a backend evidence span.
  factory SupplementPreviewEvidenceSpan.fromJson(Map<String, dynamic> json) {
    return SupplementPreviewEvidenceSpan(
      spanId: readString(json, 'span_id'),
      sourceType: readString(json, 'source_type'),
      sectionType: readString(json, 'section_type'),
      textExcerpt: readString(json, 'text_excerpt'),
      pageIndex: readOptionalInt(json, 'page_index'),
      cellRef: readOptionalString(json, 'cell_ref'),
      confidence: readOptionalDouble(json, 'confidence'),
    );
  }
}

/// Bounded label section summary for supplement preview review.
class SupplementPreviewLabelSection {
  /// Creates a label section preview.
  const SupplementPreviewLabelSection({
    required this.sectionId,
    required this.sectionType,
    required this.headingText,
    required this.textBundle,
    required this.confidence,
    required this.requiresReview,
    required this.evidenceRefs,
  });

  /// Stable section id.
  final String sectionId;

  /// Normalized section type.
  final String sectionType;

  /// Optional section heading.
  final String? headingText;

  /// Bounded section text bundle.
  final String? textBundle;

  /// Optional section confidence.
  final double? confidence;

  /// Whether the section should be reviewed.
  final bool requiresReview;

  /// Evidence ids supporting the section.
  final List<String> evidenceRefs;

  /// Parses a backend label section preview.
  factory SupplementPreviewLabelSection.fromJson(Map<String, dynamic> json) {
    return SupplementPreviewLabelSection(
      sectionId: readString(json, 'section_id'),
      sectionType: readString(json, 'section_type'),
      headingText: readOptionalString(json, 'heading_text'),
      textBundle: readOptionalString(json, 'text_bundle'),
      confidence: readOptionalDouble(json, 'confidence'),
      requiresReview: json['requires_review'] == true,
      evidenceRefs: readOptionalStringList(json, 'evidence_refs'),
    );
  }
}

/// Conservative structured intake method parsed from label text.
class SupplementPreviewStructuredIntakeMethod {
  /// Creates a structured intake method.
  const SupplementPreviewStructuredIntakeMethod({
    required this.frequency,
    required this.timesPerDay,
    required this.amountPerTime,
    required this.amountUnit,
    required this.timeOfDay,
    required this.withFood,
  });

  /// Empty structured intake fallback.
  static const SupplementPreviewStructuredIntakeMethod empty =
      SupplementPreviewStructuredIntakeMethod(
        frequency: 'unknown',
        timesPerDay: null,
        amountPerTime: null,
        amountUnit: null,
        timeOfDay: <String>[],
        withFood: 'unknown',
      );

  /// Frequency candidate.
  final String frequency;

  /// Candidate daily intake count.
  final double? timesPerDay;

  /// Candidate amount per intake.
  final double? amountPerTime;

  /// Candidate amount unit.
  final String? amountUnit;

  /// Optional time-of-day labels.
  final List<String> timeOfDay;

  /// Label-supported food timing marker.
  final String withFood;

  /// Parses a backend structured intake method.
  factory SupplementPreviewStructuredIntakeMethod.fromJson(
    Map<String, dynamic> json,
  ) {
    return SupplementPreviewStructuredIntakeMethod(
      frequency: readString(json, 'frequency'),
      timesPerDay: readOptionalDouble(json, 'times_per_day'),
      amountPerTime: readOptionalDouble(json, 'amount_per_time'),
      amountUnit: readOptionalString(json, 'amount_unit'),
      timeOfDay: readOptionalStringList(json, 'time_of_day'),
      withFood: readString(json, 'with_food'),
    );
  }
}

/// Label-supported intake method preview.
class SupplementPreviewIntakeMethod {
  /// Creates an intake method preview.
  const SupplementPreviewIntakeMethod({
    required this.text,
    required this.structured,
    required this.confidence,
    required this.requiresReview,
    required this.evidenceRefs,
  });

  /// Empty intake method fallback.
  static const SupplementPreviewIntakeMethod empty =
      SupplementPreviewIntakeMethod(
        text: null,
        structured: SupplementPreviewStructuredIntakeMethod.empty,
        confidence: null,
        requiresReview: false,
        evidenceRefs: <String>[],
      );

  /// Bounded raw label instruction text.
  final String? text;

  /// Conservative structured candidate.
  final SupplementPreviewStructuredIntakeMethod structured;

  /// Optional confidence.
  final double? confidence;

  /// Whether this field should be reviewed.
  final bool requiresReview;

  /// Evidence ids supporting this field.
  final List<String> evidenceRefs;

  /// Parses a backend intake method preview.
  factory SupplementPreviewIntakeMethod.fromJson(Map<String, dynamic> json) {
    final Map<String, dynamic>? structured = readOptionalObject(
      json,
      'structured',
    );
    return SupplementPreviewIntakeMethod(
      text: readOptionalString(json, 'text'),
      structured: structured == null
          ? SupplementPreviewStructuredIntakeMethod.empty
          : SupplementPreviewStructuredIntakeMethod.fromJson(structured),
      confidence: readOptionalDouble(json, 'confidence'),
      requiresReview: json['requires_review'] == true,
      evidenceRefs: readOptionalStringList(json, 'evidence_refs'),
    );
  }
}

/// Label-supported precaution preview.
class SupplementPreviewPrecaution {
  /// Creates a precaution preview.
  const SupplementPreviewPrecaution({
    required this.text,
    required this.category,
    required this.severity,
    required this.confidence,
    required this.requiresReview,
    required this.evidenceRefs,
  });

  /// Bounded precaution text.
  final String text;

  /// Conservative category.
  final String category;

  /// Label warning severity marker.
  final String severity;

  /// Optional confidence.
  final double? confidence;

  /// Whether this row should be reviewed.
  final bool requiresReview;

  /// Evidence ids supporting this precaution.
  final List<String> evidenceRefs;

  /// Parses a backend precaution preview.
  factory SupplementPreviewPrecaution.fromJson(Map<String, dynamic> json) {
    return SupplementPreviewPrecaution(
      text: readString(json, 'text'),
      category: readString(json, 'category'),
      severity: readString(json, 'severity'),
      confidence: readOptionalDouble(json, 'confidence'),
      requiresReview: json['requires_review'] == true,
      evidenceRefs: readOptionalStringList(json, 'evidence_refs'),
    );
  }
}

/// Label-supported functional claim preview.
class SupplementPreviewFunctionalClaim {
  /// Creates a functional claim preview.
  const SupplementPreviewFunctionalClaim({
    required this.text,
    required this.claimType,
    required this.confidence,
    required this.requiresReview,
    required this.evidenceRefs,
  });

  /// Bounded label claim text.
  final String text;

  /// Conservative claim type.
  final String claimType;

  /// Optional confidence.
  final double? confidence;

  /// Whether this row should be reviewed.
  final bool requiresReview;

  /// Evidence ids supporting this claim.
  final List<String> evidenceRefs;

  /// Parses a backend functional claim preview.
  factory SupplementPreviewFunctionalClaim.fromJson(Map<String, dynamic> json) {
    return SupplementPreviewFunctionalClaim(
      text: readString(json, 'text'),
      claimType: readString(json, 'claim_type'),
      confidence: readOptionalDouble(json, 'confidence'),
      requiresReview: json['requires_review'] == true,
      evidenceRefs: readOptionalStringList(json, 'evidence_refs'),
    );
  }
}

/// Request payload for parsing OCR text against an existing preview.
class SupplementOCRTextParseRequest {
  /// Creates an OCR text parse request.
  const SupplementOCRTextParseRequest({
    required this.ocrText,
    this.ocrProvider = 'manual_demo',
    this.ocrConfidence,
  });

  /// Raw OCR text held transiently by the client.
  final String ocrText;

  /// Provider label sent to the backend.
  final String ocrProvider;

  /// Optional provider confidence.
  final double? ocrConfidence;

  /// Serializes the request to backend JSON.
  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'ocr_text': ocrText,
      'ocr_provider': ocrProvider,
      'ocr_confidence': ocrConfidence,
    };
  }
}

/// User-confirmed supplement registration request.
class UserSupplementCreate {
  /// Creates a user-confirmed supplement registration request.
  const UserSupplementCreate({
    required this.analysisId,
    required this.displayName,
    required this.manufacturer,
    required this.ingredients,
    required this.serving,
    required this.intakeSchedule,
  });

  /// Temporary analysis identifier used for traceability.
  final String? analysisId;

  /// User-confirmed supplement name.
  final String displayName;

  /// User-confirmed manufacturer.
  final String? manufacturer;

  /// User-confirmed ingredient list.
  final List<UserSupplementIngredientInput> ingredients;

  /// User-confirmed serving values.
  final SupplementServing serving;

  /// Optional user-confirmed intake schedule.
  final SupplementIntakeSchedule? intakeSchedule;

  /// Serializes the request to backend JSON.
  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'analysis_id': analysisId,
      'display_name': displayName,
      'manufacturer': manufacturer,
      'ingredients': ingredients
          .map(
            (UserSupplementIngredientInput ingredient) => ingredient.toJson(),
          )
          .toList(growable: false),
      'serving': serving.toJson(),
      'intake_schedule': intakeSchedule?.toJson(),
      'user_confirmed': true,
    };
  }
}

/// User-confirmed supplement ingredient row.
class UserSupplementIngredientInput {
  /// Creates a user-confirmed ingredient input.
  const UserSupplementIngredientInput({
    required this.displayName,
    required this.nutrientCode,
    required this.amount,
    required this.unit,
    required this.confidence,
    required this.source,
  });

  /// User-confirmed ingredient name.
  final String displayName;

  /// Internal nutrient code when deterministically mapped.
  final String? nutrientCode;

  /// Ingredient amount per serving.
  final double? amount;

  /// Ingredient unit.
  final String? unit;

  /// Extraction or confirmation confidence.
  final double confidence;

  /// Source marker accepted by the backend.
  final String source;

  /// Serializes the ingredient row to backend JSON.
  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'display_name': displayName,
      'nutrient_code': nutrientCode,
      'amount': amount,
      'unit': unit,
      'confidence': confidence,
      'source': source,
    };
  }
}

/// User-confirmed supplement serving values.
class SupplementServing {
  /// Creates serving values.
  const SupplementServing({
    required this.amount,
    required this.unit,
    required this.dailyServings,
  });

  /// Serving amount.
  final double? amount;

  /// Serving unit.
  final String? unit;

  /// Daily serving count confirmed by the user.
  final double dailyServings;

  /// Serializes serving values to backend JSON.
  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'amount': amount,
      'unit': unit,
      'daily_servings': dailyServings,
    };
  }
}

/// User-confirmed supplement intake schedule.
class SupplementIntakeSchedule {
  /// Creates an intake schedule.
  const SupplementIntakeSchedule({
    required this.frequency,
    required this.timeOfDay,
  });

  /// Human-readable frequency.
  final String frequency;

  /// Optional time labels such as morning or evening.
  final List<String> timeOfDay;

  /// Serializes intake schedule to backend JSON.
  Map<String, dynamic> toJson() {
    return <String, dynamic>{'frequency': frequency, 'time_of_day': timeOfDay};
  }
}

/// Persisted current-user supplement response.
class UserSupplementResponse {
  /// Creates a persisted supplement response.
  const UserSupplementResponse({
    required this.id,
    required this.displayName,
    required this.manufacturer,
  });

  /// Persisted supplement identifier.
  final String id;

  /// User-confirmed supplement name.
  final String displayName;

  /// User-confirmed manufacturer.
  final String? manufacturer;

  /// Parses a backend persisted supplement response.
  factory UserSupplementResponse.fromJson(Map<String, dynamic> json) {
    return UserSupplementResponse(
      id: readString(json, 'id'),
      displayName: readString(json, 'display_name'),
      manufacturer: readOptionalString(json, 'manufacturer'),
    );
  }
}

/// Request payload for deterministic supplement impact preview.
class SupplementImpactPreviewRequest {
  /// Creates a supplement impact preview request.
  const SupplementImpactPreviewRequest({
    this.selectedSupplementIds = const <String>[],
    this.includeAllActiveSupplements = true,
  });

  /// Optional supplement id subset.
  final List<String> selectedSupplementIds;

  /// Whether to include all active supplements.
  final bool includeAllActiveSupplements;

  /// Serializes the request to backend JSON.
  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'selected_supplement_ids': selectedSupplementIds,
      'include_all_active_supplements': includeAllActiveSupplements,
      'profile_override': null,
    };
  }
}

/// Ingredient contribution aggregate returned by the backend.
class SupplementContributionAggregate {
  /// Creates a contribution aggregate.
  const SupplementContributionAggregate({
    required this.nutrientCode,
    required this.nutrientName,
    required this.referenceUnit,
    required this.totalDailyAmount,
    required this.contributionCount,
    required this.warnings,
  });

  /// Internal nutrient code.
  final String nutrientCode;

  /// Display nutrient name when available.
  final String? nutrientName;

  /// Reference unit when available.
  final String? referenceUnit;

  /// Total supplement daily amount in reference unit when available.
  final double? totalDailyAmount;

  /// Number of contributing ingredient rows.
  final int contributionCount;

  /// Safe warning codes/messages.
  final List<String> warnings;

  /// Parses a backend contribution aggregate.
  factory SupplementContributionAggregate.fromJson(Map<String, dynamic> json) {
    return SupplementContributionAggregate(
      nutrientCode: readString(json, 'nutrient_code'),
      nutrientName: readOptionalString(json, 'nutrient_name'),
      referenceUnit: readOptionalString(json, 'reference_unit'),
      totalDailyAmount: readOptionalDouble(json, 'total_daily_amount'),
      contributionCount: readInt(json, 'contribution_count'),
      warnings: readOptionalStringList(json, 'warnings'),
    );
  }
}

/// Safe deterministic supplement insight.
class SupplementNutritionInsight {
  /// Creates a nutrition insight.
  const SupplementNutritionInsight({
    required this.nutrientCode,
    required this.nutrientName,
    required this.actionLabel,
    required this.reasonCode,
    required this.supplementDailyAmount,
    required this.estimatedTotalAmount,
    required this.referenceUnit,
    required this.userMessage,
  });

  /// Internal nutrient code.
  final String nutrientCode;

  /// Nutrient display name when available.
  final String? nutrientName;

  /// Safe action label.
  final String actionLabel;

  /// Deterministic reason code.
  final String reasonCode;

  /// Supplement daily amount when available.
  final double? supplementDailyAmount;

  /// Estimated total amount when available.
  final double? estimatedTotalAmount;

  /// Reference unit when available.
  final String? referenceUnit;

  /// Safe user-facing message.
  final String userMessage;

  /// Parses a backend nutrition insight.
  factory SupplementNutritionInsight.fromJson(Map<String, dynamic> json) {
    return SupplementNutritionInsight(
      nutrientCode: readString(json, 'nutrient_code'),
      nutrientName: readOptionalString(json, 'nutrient_name'),
      actionLabel: readString(json, 'action_label'),
      reasonCode: readString(json, 'reason_code'),
      supplementDailyAmount: readOptionalDouble(
        json,
        'supplement_daily_amount',
      ),
      estimatedTotalAmount: readOptionalDouble(json, 'estimated_total_amount'),
      referenceUnit: readOptionalString(json, 'reference_unit'),
      userMessage: readString(json, 'user_message'),
    );
  }
}

/// Deterministic supplement impact preview response.
class SupplementImpactPreviewResponse {
  /// Creates a supplement impact preview response.
  const SupplementImpactPreviewResponse({
    required this.calculationVersion,
    required this.referenceVersion,
    required this.sourceManifestVersion,
    required this.dataStatus,
    required this.currentSupplementContributions,
    required this.deficiencySupportCandidates,
    required this.excessOrDuplicateRisks,
    required this.missingProfileFields,
    required this.safeUserMessage,
    required this.clinicalDisclaimer,
    required this.warnings,
    required this.requiresUserConfirmation,
    this.rawJson = const <String, dynamic>{},
  });

  /// Server calculation algorithm version.
  final String calculationVersion;

  /// KDRI reference version.
  final String referenceVersion;

  /// KDRI source manifest version.
  final String? sourceManifestVersion;

  /// Readiness status.
  final String dataStatus;

  /// Current supplement contribution aggregates.
  final List<SupplementContributionAggregate> currentSupplementContributions;

  /// Nutrients whose low intake overlaps with supplement inputs.
  final List<SupplementNutritionInsight> deficiencySupportCandidates;

  /// Duplicate or upper-limit review insights.
  final List<SupplementNutritionInsight> excessOrDuplicateRisks;

  /// Missing fields for personalized comparison.
  final List<String> missingProfileFields;

  /// Safe summary message.
  final String safeUserMessage;

  /// Clinical disclaimer.
  final String clinicalDisclaimer;

  /// Safe warning codes/messages.
  final List<String> warnings;

  /// Whether UI should ask for user review.
  final bool requiresUserConfirmation;

  /// Original backend JSON for explain requests.
  final Map<String, dynamic> rawJson;

  /// Parses a backend supplement impact preview.
  factory SupplementImpactPreviewResponse.fromJson(Map<String, dynamic> json) {
    return SupplementImpactPreviewResponse(
      calculationVersion: readString(json, 'calculation_version'),
      referenceVersion: readString(json, 'reference_version'),
      sourceManifestVersion: readOptionalString(
        json,
        'source_manifest_version',
      ),
      dataStatus: readString(json, 'data_status'),
      currentSupplementContributions:
          readOptionalList(json, 'current_supplement_contributions')
              .whereType<Map<String, dynamic>>()
              .map(SupplementContributionAggregate.fromJson)
              .toList(growable: false),
      deficiencySupportCandidates:
          readOptionalList(json, 'deficiency_support_candidates')
              .whereType<Map<String, dynamic>>()
              .map(SupplementNutritionInsight.fromJson)
              .toList(growable: false),
      excessOrDuplicateRisks:
          readOptionalList(json, 'excess_or_duplicate_risks')
              .whereType<Map<String, dynamic>>()
              .map(SupplementNutritionInsight.fromJson)
              .toList(growable: false),
      missingProfileFields: readOptionalStringList(
        json,
        'missing_profile_fields',
      ),
      safeUserMessage: readString(json, 'safe_user_message'),
      clinicalDisclaimer: readString(json, 'clinical_disclaimer'),
      warnings: readOptionalStringList(json, 'warnings'),
      requiresUserConfirmation: json['requires_user_confirmation'] == true,
      rawJson: Map<String, dynamic>.unmodifiable(json),
    );
  }

  /// Serializes the original backend response for explain requests.
  Map<String, dynamic> toJson() {
    if (rawJson.isNotEmpty) {
      return Map<String, dynamic>.from(rawJson);
    }
    return <String, dynamic>{
      'calculation_version': calculationVersion,
      'reference_version': referenceVersion,
      'source_manifest_version': sourceManifestVersion,
      'data_status': dataStatus,
      'current_supplement_contributions': <Map<String, dynamic>>[],
      'deficiency_support_candidates': <Map<String, dynamic>>[],
      'excess_or_duplicate_risks': <Map<String, dynamic>>[],
      'missing_profile_fields': missingProfileFields,
      'safe_user_message': safeUserMessage,
      'clinical_disclaimer': clinicalDisclaimer,
      'warnings': warnings,
      'requires_user_confirmation': requiresUserConfirmation,
    };
  }
}

/// Safe explanation response for a deterministic supplement impact preview.
class SupplementRecommendationExplainResponse {
  /// Creates an explanation response.
  const SupplementRecommendationExplainResponse({
    required this.safeUserMessage,
    required this.explanationBullets,
    required this.clinicalDisclaimer,
    required this.blockedTermsDetected,
    required this.llmUsed,
    required this.warnings,
  });

  /// Safe summary message.
  final String safeUserMessage;

  /// Bounded explanation bullets.
  final List<String> explanationBullets;

  /// Clinical disclaimer.
  final String clinicalDisclaimer;

  /// Blocked terms detected by the backend.
  final List<String> blockedTermsDetected;

  /// Whether local LLM wording was accepted.
  final bool llmUsed;

  /// Safe warning codes/messages.
  final List<String> warnings;

  /// Parses a backend explanation response.
  factory SupplementRecommendationExplainResponse.fromJson(
    Map<String, dynamic> json,
  ) {
    return SupplementRecommendationExplainResponse(
      safeUserMessage: readString(json, 'safe_user_message'),
      explanationBullets: readOptionalStringList(json, 'explanation_bullets'),
      clinicalDisclaimer: readString(json, 'clinical_disclaimer'),
      blockedTermsDetected: readOptionalStringList(
        json,
        'blocked_terms_detected',
      ),
      llmUsed: json['llm_used'] == true,
      warnings: readOptionalStringList(json, 'warnings'),
    );
  }
}
