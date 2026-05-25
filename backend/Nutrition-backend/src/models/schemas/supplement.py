"""Supplement intake API contract schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.schemas.image_quality import ImageQualityReport
from src.models.schemas.supplement_image import SupplementImagePipelineMetadata

SupplementImageRiskActionRequired = Literal[
    "none",
    "review_required",
    "retake_recommended",
    "additional_label_image_required",
    "product_region_selection_required",
    "manual_entry_required",
    "blocked",
]
SupplementImageAnalysisScope = Literal[
    "unknown",
    "full_label",
    "identity_only",
    "full_image_review",
    "selected_roi_review",
    "multi_product_review",
]
SupplementImageRole = Literal[
    "unknown",
    "front_label",
    "supplement_facts",
    "ingredients",
    "precautions",
    "barcode",
    "mixed",
]
SupplementImageSourceType = Literal["uploaded_image", "screenshot_or_catalog", "unknown"]
SupplementMissingRequiredSection = Literal[
    "supplement_facts",
    "ingredients",
    "precautions",
    "barcode",
]


class SupplementAnalysisStatus(StrEnum):
    """Supplement analysis contract states.

    Attributes:
        REQUIRES_CONFIRMATION: Preview must be reviewed by the user before storage.
        CONFIRMED: Preview was confirmed into a user supplement.
        EXPIRED: Preview can no longer be confirmed.
        FAILED: Preview analysis failed before confirmation.
    """

    REQUIRES_CONFIRMATION = "requires_confirmation"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    FAILED = "failed"


class SupplementIngredientCandidate(BaseModel):
    """Ingredient candidate extracted from a supplement label.

    Attributes:
        display_name: Ingredient name shown to the user for confirmation.
        nutrient_code: Internal nutrient code when mapped.
        amount: Ingredient amount per serving.
        unit: Ingredient unit.
        confidence: Extraction confidence from 0.0 to 1.0.
        source: Source that produced the candidate.
    """

    display_name: str = Field(min_length=1, max_length=120)
    nutrient_code: str | None = Field(default=None, max_length=80)
    amount: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=40)
    confidence: float = Field(ge=0, le=1)
    source: str = Field(min_length=1, max_length=80)


class MatchedSupplementCandidate(BaseModel):
    """Product candidate matched from a supplement reference source.

    Attributes:
        source_id: Reference source identifier.
        product_name: Matched product name.
        manufacturer: Product manufacturer when available.
        match_score: Matching score from 0.0 to 1.0.
    """

    source_id: str = Field(min_length=1, max_length=120)
    product_name: str = Field(min_length=1, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=160)
    match_score: float = Field(ge=0, le=1)


class SupplementBarcodeLookupRequest(BaseModel):
    """Request to look up official FoodQR product candidates by barcode.

    Attributes:
        barcode_text: Barcode value or QR payload supplied by the client scanner.
        barcode_format: Optional scanner format label such as EAN_13 or QR_CODE.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    barcode_text: str = Field(min_length=1, max_length=256)
    barcode_format: str | None = Field(default=None, max_length=40)


class SupplementBarcodeProviderObservation(BaseModel):
    """Sanitized provider observation for barcode lookup.

    Attributes:
        provider: Provider label.
        status: Provider status after normalization.
        message_code: Provider message code when available.
        item_count: Number of allowlisted provider rows.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    provider: str = Field(min_length=1, max_length=40)
    status: str = Field(min_length=1, max_length=40)
    message_code: str | None = Field(default=None, max_length=80)
    item_count: int = Field(default=0, ge=0, le=1000)


class SupplementBarcodeProductCandidate(BaseModel):
    """Official product candidate returned by barcode lookup.

    Attributes:
        source_id: Stable source identifier for this candidate.
        provider: Official provider that produced the candidate.
        product_name: Product name returned by the provider.
        manufacturer: Manufacturer or business name when available.
        barcode: Barcode value returned by the provider.
        report_no: MFDS item report number when available.
        version: FoodQR version when available.
        valid_from: FoodQR validity start date when available.
        valid_to: FoodQR validity end date when available.
        match_score: Review-only ranking score. It is not an accuracy metric.
        review_required_reason: Reason this candidate cannot be auto-confirmed.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(min_length=1, max_length=160)
    provider: Literal["foodqr"] = "foodqr"
    product_name: str = Field(min_length=1, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=160)
    barcode: str | None = Field(default=None, max_length=32)
    report_no: str | None = Field(default=None, max_length=80)
    version: str | None = Field(default=None, max_length=40)
    valid_from: str | None = Field(default=None, max_length=8)
    valid_to: str | None = Field(default=None, max_length=8)
    match_score: float = Field(ge=0, le=1)
    review_required_reason: str = Field(min_length=1, max_length=80)


class SupplementBarcodeLookupResponse(BaseModel):
    """Review-only barcode lookup response.

    Attributes:
        status: Lookup status. Candidate-bearing responses still require user review.
        normalized_barcode: Normalized barcode value returned only to the requester.
        barcode_format: Optional scanner format label.
        barcode_symbology: Symbology inferred from the barcode length.
        barcode_hash: One-way hash suitable for audit metadata.
        check_digit_valid: Whether barcode checksum validation passed.
        candidate_count: Number of review-only candidates.
        candidates: Official candidates requiring user confirmation.
        provider_observations: Sanitized provider status observations.
        warnings: Safe warnings for the UI.
        raw_value_stored: Always false for audit/log storage.
        raw_provider_payload_stored: Always false.
        auto_confirmed: Always false because barcode lookup is candidate-only.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal[
        "not_configured",
        "invalid_request",
        "not_found",
        "review_required",
        "provider_error",
    ]
    normalized_barcode: str | None = Field(default=None, max_length=32)
    barcode_format: str | None = Field(default=None, max_length=40)
    barcode_symbology: Literal["ean8", "upca", "ean13", "gtin14"] | None = None
    barcode_hash: str | None = Field(default=None, max_length=80)
    check_digit_valid: bool | None = None
    candidate_count: int = Field(default=0, ge=0, le=1000)
    candidates: list[SupplementBarcodeProductCandidate] = Field(default_factory=list)
    provider_observations: list[SupplementBarcodeProviderObservation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    raw_value_stored: Literal[False] = False
    raw_provider_payload_stored: Literal[False] = False
    auto_confirmed: Literal[False] = False


class SupplementDetectedProductRegion(BaseModel):
    """Bounded product or label-region metadata for mobile review.

    Attributes:
        region_id: Request-local stable id for region selection UI.
        label: Detector or annotation label.
        x: Left coordinate in input-image pixels.
        y: Top coordinate in input-image pixels.
        width: Region width in pixels.
        height: Region height in pixels.
        confidence: Detector confidence.
        area_ratio: Region area divided by full image area.
        selected: Whether the backend selected this region for OCR metadata.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    region_id: str = Field(min_length=1, max_length=80)
    label: str | None = Field(default=None, max_length=80)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    confidence: float = Field(ge=0, le=1)
    area_ratio: float | None = Field(default=None, ge=0, le=1)
    selected: bool = False


class SupplementIdentityConflict(BaseModel):
    """Review-only identity conflict between barcode and parsed label metadata.

    Attributes:
        conflict_type: Stable conflict code for UI and evaluation.
        severity: Review severity. This is not a medical risk level.
        message: Safe user-facing message without raw provider payloads.
        evidence: Numeric or categorical conflict evidence without raw OCR text.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    conflict_type: Literal["barcode_product_mismatch"]
    severity: Literal["review"] = "review"
    message: str = Field(min_length=1, max_length=240)
    evidence: dict[str, int | float | str | bool | None] = Field(
        default_factory=dict,
        max_length=20,
    )


class SupplementImageRiskActionContract(BaseModel):
    """Structured action contract derived from image quality and identity metadata.

    Attributes:
        analysis_scope: Scope that the preview can safely represent.
        action_required: Next user action required before relying on the preview.
        detected_product_regions: Bounded ROI candidates for review UI.
        selected_region_id: Region id selected by the backend when safe.
        missing_required_sections: Label sections that still need a better image.
        image_role: Inferred role of the uploaded image in a multi-image flow.
        multi_image_group_id: Optional client/backend group id for future multi-image merging.
        source_type: Conservative source classification for the uploaded image.
        identity_conflict: Optional review-only barcode/label identity conflict.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    analysis_scope: SupplementImageAnalysisScope = "unknown"
    action_required: SupplementImageRiskActionRequired = "none"
    detected_product_regions: list[SupplementDetectedProductRegion] = Field(
        default_factory=list,
        max_length=20,
    )
    selected_region_id: str | None = Field(default=None, max_length=80)
    missing_required_sections: list[SupplementMissingRequiredSection] = Field(
        default_factory=list,
        max_length=10,
    )
    image_role: SupplementImageRole = "unknown"
    multi_image_group_id: str | None = Field(default=None, max_length=120)
    source_type: SupplementImageSourceType = "uploaded_image"
    identity_conflict: SupplementIdentityConflict | None = None


class SupplementParsedProduct(BaseModel):
    """Parsed supplement product fields from OCR and structured parsing.

    Attributes:
        product_name: Product name candidate.
        manufacturer: Manufacturer candidate.
        serving_size: Serving size text from the label.
        daily_servings: Suggested daily serving count from the label.
    """

    product_name: str | None = Field(default=None, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=160)
    serving_size: str | None = Field(default=None, max_length=120)
    daily_servings: float | None = Field(default=None, ge=0, le=20)


SupplementPreviewSectionType = Literal[
    "nutrition_info",
    "functional_info",
    "intake_method",
    "precautions",
    "ingredients",
    "storage_method",
    "unknown",
]


class SupplementPreviewEvidenceSpan(BaseModel):
    """Short redacted label excerpt supporting a preview field.

    Attributes:
        span_id: Stable evidence id referenced by preview fields.
        source_type: Evidence source category.
        section_type: Normalized supplement label section.
        text_excerpt: Short bounded excerpt, never the full OCR text.
        page_index: Optional zero-based OCR page index.
        cell_ref: Optional layout cell reference.
        confidence: Optional OCR/layout confidence.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    span_id: str = Field(min_length=1, max_length=120)
    source_type: str = Field(min_length=1, max_length=80)
    section_type: SupplementPreviewSectionType = "unknown"
    text_excerpt: str = Field(min_length=1, max_length=240)
    page_index: int | None = Field(default=None, ge=0)
    cell_ref: str | None = Field(default=None, max_length=160)
    confidence: float | None = Field(default=None, ge=0, le=1)


class SupplementPreviewLabelSection(BaseModel):
    """Bounded label section summary for mobile review.

    Attributes:
        section_id: Stable section id in visual or deterministic order.
        section_type: Normalized supplement label section.
        heading_text: Section heading or anchor text.
        text_bundle: Bounded section text when layout context is available.
        confidence: Optional average section confidence.
        requires_review: Whether the UI should highlight this section.
        evidence_refs: Evidence ids supporting the section.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    section_id: str = Field(min_length=1, max_length=80)
    section_type: SupplementPreviewSectionType
    heading_text: str | None = Field(default=None, max_length=120)
    text_bundle: str | None = Field(default=None, max_length=2_000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    requires_review: bool = False
    evidence_refs: list[str] = Field(default_factory=list, max_length=80)


class SupplementPreviewStructuredIntakeMethod(BaseModel):
    """Conservative structured intake-method candidate for mobile review.

    Attributes:
        frequency: Label-supported frequency candidate.
        times_per_day: Candidate daily intake count.
        amount_per_time: Candidate amount per intake.
        amount_unit: Candidate intake amount unit.
        time_of_day: Label-supported time-of-day labels.
        with_food: Whether the label mentions food timing.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    frequency: str = Field(default="unknown", max_length=40)
    times_per_day: float | None = Field(default=None, ge=0, le=20)
    amount_per_time: float | None = Field(default=None, ge=0, le=1_000_000)
    amount_unit: str | None = Field(default=None, max_length=40)
    time_of_day: list[str] = Field(default_factory=list, max_length=8)
    with_food: str = Field(default="unknown", max_length=40)


class SupplementPreviewIntakeMethod(BaseModel):
    """Label-supported intake method preview for mobile review.

    Attributes:
        text: Bounded intake instruction text from the label.
        structured: Conservative structured candidate.
        confidence: Optional confidence derived from supporting evidence.
        requires_review: Whether the UI should ask for review.
        evidence_refs: Evidence ids supporting this field.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str | None = Field(default=None, max_length=500)
    structured: SupplementPreviewStructuredIntakeMethod = Field(
        default_factory=SupplementPreviewStructuredIntakeMethod
    )
    confidence: float | None = Field(default=None, ge=0, le=1)
    requires_review: bool = False
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class SupplementPreviewPrecaution(BaseModel):
    """Label-supported precaution preview for mobile review.

    Attributes:
        text: Bounded precaution text from the label.
        category: Conservative precaution category.
        severity: Label warning severity marker.
        confidence: Optional confidence derived from supporting evidence.
        requires_review: Whether the UI should ask for review.
        evidence_refs: Evidence ids supporting this precaution.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=500)
    category: str = Field(default="unknown", max_length=80)
    severity: str = Field(default="unknown", max_length=40)
    confidence: float | None = Field(default=None, ge=0, le=1)
    requires_review: bool = False
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class SupplementPreviewFunctionalClaim(BaseModel):
    """Label-supported functional claim preview for mobile review.

    Attributes:
        text: Bounded functional claim text from the label.
        claim_type: Conservative functional claim category.
        confidence: Optional confidence derived from supporting evidence.
        requires_review: Whether the UI should ask for review.
        evidence_refs: Evidence ids supporting this claim.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=500)
    claim_type: str = Field(default="unknown", max_length=80)
    confidence: float | None = Field(default=None, ge=0, le=1)
    requires_review: bool = False
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class SupplementAnalysisPreview(BaseModel):
    """Supplement OCR and parsing preview before user confirmation.

    Attributes:
        analysis_id: Temporary analysis identifier.
        status: Preview status.
        parsed_product: Product-level parsed fields.
        ingredient_candidates: Ingredient candidates requiring user review.
        matched_product_candidates: Product reference matches.
        barcode_lookup: Optional official barcode lookup result.
        layout_available: Whether deterministic section layout is available.
        layout_fallback_reason: Safe reason when section layout fell back.
        label_sections: Bounded section summaries for mobile review.
        intake_method: Label-supported intake method candidate.
        precautions: Label-supported precaution candidates.
        functional_claims: Label-supported functional claim candidates.
        evidence_spans: Short redacted evidence excerpts.
        image_quality_report: Redacted image-quality report for OCR review UX.
        analysis_scope: Scope that the preview can safely represent.
        action_required: Next user action required before relying on the preview.
        detected_product_regions: Bounded ROI candidates for review UI.
        selected_region_id: Region id selected by the backend when safe.
        missing_required_sections: Label sections that still need a better image.
        image_role: Inferred role of the uploaded image in a multi-image flow.
        multi_image_group_id: Optional client/backend group id for future multi-image merging.
        source_type: Conservative source classification for the uploaded image.
        identity_conflict: Optional review-only barcode/label identity conflict.
        pipeline_metadata: Non-sensitive OCR/YOLO/parser metadata for smoke tests.
        low_confidence_fields: Field names that require extra user attention.
        warnings: Safe warnings for the preview screen.
        algorithm_version: Parsing contract version.
        source_manifest_version: Reference source manifest version.
        expires_at: Time when this preview should no longer be used.
    """

    analysis_id: UUID
    status: SupplementAnalysisStatus
    parsed_product: SupplementParsedProduct
    ingredient_candidates: list[SupplementIngredientCandidate]
    matched_product_candidates: list[MatchedSupplementCandidate] = Field(default_factory=list)
    barcode_lookup: SupplementBarcodeLookupResponse | None = None
    layout_available: bool = False
    layout_fallback_reason: str | None = Field(default=None, max_length=120)
    label_sections: list[SupplementPreviewLabelSection] = Field(default_factory=list)
    intake_method: SupplementPreviewIntakeMethod = Field(
        default_factory=SupplementPreviewIntakeMethod
    )
    precautions: list[SupplementPreviewPrecaution] = Field(default_factory=list)
    functional_claims: list[SupplementPreviewFunctionalClaim] = Field(default_factory=list)
    evidence_spans: list[SupplementPreviewEvidenceSpan] = Field(default_factory=list)
    image_quality_report: ImageQualityReport | None = None
    analysis_scope: SupplementImageAnalysisScope = "unknown"
    action_required: SupplementImageRiskActionRequired = "none"
    detected_product_regions: list[SupplementDetectedProductRegion] = Field(default_factory=list)
    selected_region_id: str | None = Field(default=None, max_length=80)
    missing_required_sections: list[SupplementMissingRequiredSection] = Field(default_factory=list)
    image_role: SupplementImageRole = "unknown"
    multi_image_group_id: str | None = Field(default=None, max_length=120)
    source_type: SupplementImageSourceType = "uploaded_image"
    identity_conflict: SupplementIdentityConflict | None = None
    pipeline_metadata: SupplementImagePipelineMetadata = Field(
        default_factory=lambda: SupplementImagePipelineMetadata(intake_completed=True)
    )
    low_confidence_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    algorithm_version: str
    source_manifest_version: str | None
    expires_at: datetime


class SupplementServing(BaseModel):
    """User-confirmed supplement serving values.

    Attributes:
        amount: Serving amount.
        unit: Serving unit.
        daily_servings: Daily serving count confirmed by the user.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    amount: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=40)
    daily_servings: float = Field(ge=0, le=20)


class SupplementIntakeSchedule(BaseModel):
    """User-confirmed supplement intake schedule.

    Attributes:
        frequency: Human-readable frequency.
        time_of_day: Optional time labels such as morning or evening.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    frequency: str = Field(min_length=1, max_length=80)
    time_of_day: list[str] = Field(default_factory=list, max_length=8)


class UserSupplementIngredientInput(BaseModel):
    """User-confirmed supplement ingredient input.

    Attributes:
        display_name: User-confirmed ingredient name.
        nutrient_code: Internal nutrient code when deterministically mapped.
        amount: User-confirmed ingredient amount per serving.
        unit: User-confirmed ingredient unit.
        confidence: Retained extraction confidence, or 1.0 for manual confirmation.
        source: Source marker for the confirmed ingredient row.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str = Field(min_length=1, max_length=120)
    nutrient_code: str | None = Field(default=None, max_length=80)
    amount: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=40)
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: Literal["user_confirmed", "ocr_llm_preview"] = "user_confirmed"


class UserSupplementCreate(BaseModel):
    """Request to store a user-confirmed supplement record.

    Attributes:
        analysis_id: Temporary preview identifier used for traceability.
        display_name: User-confirmed supplement name.
        manufacturer: User-confirmed manufacturer.
        ingredients: User-confirmed ingredient list.
        serving: User-confirmed serving values.
        intake_schedule: User-confirmed intake schedule.
        user_confirmed: Must be true because preview values cannot be stored as final data.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    analysis_id: UUID | None = None
    display_name: str = Field(min_length=1, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=160)
    ingredients: list[UserSupplementIngredientInput] = Field(min_length=1, max_length=80)
    serving: SupplementServing
    intake_schedule: SupplementIntakeSchedule | None = None
    user_confirmed: Literal[True] = True


class UserSupplementResponse(BaseModel):
    """Persisted current-user supplement response.

    Attributes:
        id: Persisted supplement identifier.
        display_name: User-confirmed supplement name.
        manufacturer: User-confirmed manufacturer.
        ingredients: Stored ingredient list.
        serving: Stored serving values.
        intake_schedule: Stored intake schedule.
        user_confirmed_at: Time when the user confirmed the values.
        created_at: Server-side record creation time.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    manufacturer: str | None
    ingredients: list[SupplementIngredientCandidate]
    serving: SupplementServing
    intake_schedule: SupplementIntakeSchedule | None
    user_confirmed_at: datetime
    created_at: datetime


class UserSupplementListResponse(BaseModel):
    """Paginated current-user supplement list response.

    Attributes:
        results: Supplement records visible to the current owner.
        limit: Maximum requested row count.
        offset: Requested row offset.
    """

    results: list[UserSupplementResponse]
    limit: int
    offset: int
