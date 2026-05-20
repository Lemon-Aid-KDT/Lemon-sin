"""Structured supplement OCR parser schemas."""

from __future__ import annotations

import re
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SUPPLEMENT_PARSER_OUTPUT_V2: Literal["supplement-parser-output-v2"] = "supplement-parser-output-v2"
EVIDENCE_GROUNDING_WARNING = "evidence_grounding_mismatch"

ParserEvidenceSource = Literal["ocr_text", "label_layout", "barcode", "manual"]
ParserSectionType = Literal[
    "nutrition_info",
    "functional_info",
    "intake_method",
    "precautions",
    "ingredients",
    "storage_method",
    "unknown",
]
ParserFrequency = Literal["daily", "weekly", "as_needed", "unknown"]
ParserWithFoodFlag = Literal["yes", "no", "unknown"]
ParserPrecautionCategory = Literal[
    "pregnancy",
    "disease",
    "medication",
    "allergy",
    "age",
    "general",
    "unknown",
]
ParserPrecautionSeverity = Literal["label_warning", "label_caution", "unknown"]
ParserFunctionalClaimType = Literal["label_claim", "functionality", "unknown"]


def _normalize_unique_strings(values: list[str]) -> list[str]:
    """Normalize a list of strings while preserving first-seen order.

    Args:
        values: Candidate string values.

    Returns:
        Trimmed non-empty strings with duplicates removed.
    """
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = value.strip()
        if not stripped or stripped in seen:
            continue
        normalized.append(stripped)
        seen.add(stripped)
    return normalized


def _normalize_evidence_text(value: object) -> str:
    """Normalize label evidence text for deterministic containment checks.

    Args:
        value: Candidate value from a parser field or evidence excerpt.

    Returns:
        Case-folded text with punctuation collapsed to spaces.
    """
    if value is None:
        return ""
    raw = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
    return " ".join(re.sub(r"[^\w가-힣]+", " ", raw.casefold()).split())


def _is_value_grounded(value: object, evidence_text: str) -> bool:
    """Return whether a parser value is explicitly visible in referenced evidence.

    Args:
        value: Parser field value.
        evidence_text: Combined normalized evidence excerpt text.

    Returns:
        True when the value is empty or appears in the evidence text.
    """
    normalized = _normalize_evidence_text(value)
    if not normalized:
        return True
    return normalized in evidence_text


def _append_unique_bounded(values: list[str], value: str, *, limit: int) -> None:
    """Append a string once while preserving a schema field's bounded length.

    Args:
        values: Mutable target list.
        value: Candidate value to append.
        limit: Maximum list size.
    """
    if value not in values and len(values) < limit:
        values.append(value)


class SupplementParserProduct(BaseModel):
    """Product-level facts extracted from supplement OCR text.

    Attributes:
        product_name: Product name candidate exactly supported by the label text.
        manufacturer: Manufacturer candidate exactly supported by the label text.
        serving_size: Serving-size text from the label.
        daily_servings: Daily serving count stated on the label.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    product_name: str | None = Field(default=None, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=160)
    serving_size: str | None = Field(default=None, max_length=120)
    daily_servings: float | None = Field(default=None, ge=0, le=20)


class SupplementParserIngredientCandidate(BaseModel):
    """Ingredient candidate extracted from supplement OCR text.

    Attributes:
        display_name: Ingredient name shown to the user for confirmation.
        nutrient_code: Always null at the LLM extraction stage; deterministic mapping happens later.
        amount: Ingredient amount per serving when visible.
        unit: Ingredient unit when visible.
        confidence: Extraction confidence from 0.0 to 1.0.
        source: Stable parser source marker.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str = Field(min_length=1, max_length=120)
    nutrient_code: Literal[None] = Field(default=None)
    amount: float | None = Field(default=None, ge=0, le=1_000_000)
    unit: str | None = Field(default=None, max_length=40)
    confidence: float = Field(ge=0, le=1)
    source: Literal["ollama_structured"] = "ollama_structured"


class SupplementStructuredParseResult(BaseModel):
    """Validated structured output returned by the supplement parser.

    Attributes:
        parsed_product: Product-level parsed fields.
        ingredient_candidates: Ingredient candidates that require user confirmation.
        low_confidence_fields: Field paths that need extra user review.
        warnings: Safe non-medical warnings for the preview UI.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    parsed_product: SupplementParserProduct = Field(default_factory=SupplementParserProduct)
    ingredient_candidates: list[SupplementParserIngredientCandidate] = Field(
        default_factory=list,
        max_length=80,
    )
    low_confidence_fields: list[str] = Field(default_factory=list, max_length=80)
    warnings: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("low_confidence_fields", "warnings")
    @classmethod
    def _normalize_string_list(cls, values: list[str]) -> list[str]:
        """Normalize parser-produced string lists and remove duplicates.

        Args:
            values: Candidate strings produced by the parser.

        Returns:
            Trimmed non-empty strings in first-seen order.
        """
        return _normalize_unique_strings(values)


class ParserEvidenceSpan(BaseModel):
    """Short redacted evidence excerpt supporting a parser field.

    Attributes:
        span_id: Stable identifier referenced by parser fields.
        source_type: Evidence source category.
        section_type: Normalized label section category.
        text_excerpt: Short label-supported excerpt, never the full OCR text.
        page_index: Optional zero-based OCR page index.
        char_start: Optional start character offset in normalized OCR text.
        char_end: Optional end character offset in normalized OCR text.
        cell_ref: Optional layout cell reference.
        confidence: Optional OCR/layout confidence for this span.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    span_id: str = Field(min_length=1, max_length=120)
    source_type: ParserEvidenceSource
    section_type: ParserSectionType = "unknown"
    text_excerpt: str = Field(min_length=1, max_length=240)
    page_index: int | None = Field(default=None, ge=0)
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)
    cell_ref: str | None = Field(default=None, max_length=160)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_offsets(self) -> Self:
        """Validate optional character offsets.

        Returns:
            Validated evidence span.

        Raises:
            ValueError: If the end offset is not greater than the start offset.
        """
        if (
            self.char_start is not None
            and self.char_end is not None
            and self.char_end <= self.char_start
        ):
            raise ValueError("char_end must be greater than char_start.")
        return self


class ParserProduct(BaseModel):
    """Product facts visible on the label.

    Attributes:
        product_name: Product name candidate supported by label text.
        manufacturer: Manufacturer candidate supported by label text.
        evidence_refs: Evidence span ids supporting product facts.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    product_name: str | None = Field(default=None, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=160)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("evidence_refs")
    @classmethod
    def normalize_evidence_refs(cls, values: list[str]) -> list[str]:
        """Normalize evidence references.

        Args:
            values: Evidence span ids.

        Returns:
            Trimmed unique evidence span ids.
        """
        return _normalize_unique_strings(values)


class ParserServing(BaseModel):
    """Serving facts visible on the label.

    Attributes:
        serving_size_text: Original serving-size text.
        serving_amount: Parsed amount per serving when explicit.
        serving_unit: Parsed serving unit when explicit.
        daily_servings: Label-stated servings per day.
        total_amount: Label-stated total amount, not inferred.
        total_unit: Label-stated total amount unit.
        evidence_refs: Evidence span ids supporting serving facts.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    serving_size_text: str | None = Field(default=None, max_length=120)
    serving_amount: float | None = Field(default=None, ge=0, le=1_000_000)
    serving_unit: str | None = Field(default=None, max_length=40)
    daily_servings: float | None = Field(default=None, ge=0, le=20)
    total_amount: float | None = Field(default=None, ge=0, le=100_000_000)
    total_unit: str | None = Field(default=None, max_length=40)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("evidence_refs")
    @classmethod
    def normalize_evidence_refs(cls, values: list[str]) -> list[str]:
        """Normalize evidence references.

        Args:
            values: Evidence span ids.

        Returns:
            Trimmed unique evidence span ids.
        """
        return _normalize_unique_strings(values)


class ParserIngredient(BaseModel):
    """Ingredient fact candidate visible on the label.

    The LLM parser is not allowed to emit nutrient codes. Deterministic nutrient
    matching happens after this model validates.

    Attributes:
        display_name: Ingredient name as shown on the label.
        amount: Parsed ingredient amount when explicit.
        unit: Ingredient unit when explicit.
        amount_text: Original amount text when numeric parsing is uncertain.
        confidence: Parser confidence for this extraction candidate.
        source: Stable parser source marker.
        evidence_refs: Evidence span ids supporting the ingredient.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str = Field(min_length=1, max_length=120)
    amount: float | None = Field(default=None, ge=0, le=1_000_000)
    unit: str | None = Field(default=None, max_length=40)
    amount_text: str | None = Field(default=None, max_length=120)
    confidence: float = Field(ge=0, le=1)
    source: Literal["ollama_structured"] = "ollama_structured"
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("evidence_refs")
    @classmethod
    def normalize_evidence_refs(cls, values: list[str]) -> list[str]:
        """Normalize evidence references.

        Args:
            values: Evidence span ids.

        Returns:
            Trimmed unique evidence span ids.
        """
        return _normalize_unique_strings(values)


class ParserLabelSection(BaseModel):
    """Label section candidate from OCR text or layout context.

    Attributes:
        section_type: Normalized section type.
        heading_text: Section heading text from the label.
        evidence_refs: Evidence span ids supporting the section.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    section_type: ParserSectionType
    heading_text: str | None = Field(default=None, max_length=120)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("evidence_refs")
    @classmethod
    def normalize_evidence_refs(cls, values: list[str]) -> list[str]:
        """Normalize evidence references.

        Args:
            values: Evidence span ids.

        Returns:
            Trimmed unique evidence span ids.
        """
        return _normalize_unique_strings(values)


class ParserStructuredIntakeMethod(BaseModel):
    """Structured intake-method candidate derived only from label text.

    Attributes:
        frequency: Label-stated frequency category.
        times_per_day: Parsed times per day when explicit.
        amount_per_time: Parsed amount per intake when explicit.
        amount_unit: Parsed intake amount unit.
        time_of_day: Label-stated time-of-day strings.
        with_food: Whether the label mentions taking with food.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    frequency: ParserFrequency = "unknown"
    times_per_day: float | None = Field(default=None, ge=0, le=20)
    amount_per_time: float | None = Field(default=None, ge=0, le=1_000_000)
    amount_unit: str | None = Field(default=None, max_length=40)
    time_of_day: list[str] = Field(default_factory=list, max_length=8)
    with_food: ParserWithFoodFlag = "unknown"

    @field_validator("time_of_day")
    @classmethod
    def normalize_time_of_day(cls, values: list[str]) -> list[str]:
        """Normalize time-of-day labels.

        Args:
            values: Candidate time labels.

        Returns:
            Trimmed unique time labels.
        """
        return _normalize_unique_strings(values)


class ParserIntakeMethod(BaseModel):
    """Label-supported intake method candidate.

    Attributes:
        text: Intake instruction text from the label.
        structured: Conservative structured intake candidate.
        evidence_refs: Evidence span ids supporting intake facts.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str | None = Field(default=None, max_length=500)
    structured: ParserStructuredIntakeMethod = Field(default_factory=ParserStructuredIntakeMethod)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("evidence_refs")
    @classmethod
    def normalize_evidence_refs(cls, values: list[str]) -> list[str]:
        """Normalize evidence references.

        Args:
            values: Evidence span ids.

        Returns:
            Trimmed unique evidence span ids.
        """
        return _normalize_unique_strings(values)


class ParserPrecaution(BaseModel):
    """Label-supported precaution candidate.

    Attributes:
        text: Precaution text from the label.
        category: Conservative precaution category.
        severity: Label warning severity marker.
        evidence_refs: Evidence span ids supporting the precaution.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=500)
    category: ParserPrecautionCategory = "unknown"
    severity: ParserPrecautionSeverity = "unknown"
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("evidence_refs")
    @classmethod
    def normalize_evidence_refs(cls, values: list[str]) -> list[str]:
        """Normalize evidence references.

        Args:
            values: Evidence span ids.

        Returns:
            Trimmed unique evidence span ids.
        """
        return _normalize_unique_strings(values)


class ParserFunctionalClaim(BaseModel):
    """Label-supported functional claim candidate.

    Attributes:
        text: Functional claim text from the label.
        claim_type: Conservative claim category.
        evidence_refs: Evidence span ids supporting the claim.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=500)
    claim_type: ParserFunctionalClaimType = "unknown"
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("evidence_refs")
    @classmethod
    def normalize_evidence_refs(cls, values: list[str]) -> list[str]:
        """Normalize evidence references.

        Args:
            values: Evidence span ids.

        Returns:
            Trimmed unique evidence span ids.
        """
        return _normalize_unique_strings(values)


class SupplementStructuredParseResultV2(BaseModel):
    """Expanded label-fact structured output returned by the LLM parser.

    This model deliberately excludes nutrient-code and recommendation fields.
    Nutrient-code candidates are added only by deterministic post-processing.

    Attributes:
        schema_version: Fixed parser output schema version.
        product: Product facts from the label.
        serving: Serving facts from the label.
        ingredients: Ingredient fact candidates from the label.
        label_sections: Label section candidates.
        intake_method: Label-supported intake method candidate.
        precautions: Label-supported precaution candidates.
        functional_claims: Label-supported functional claim candidates.
        evidence_spans: Short redacted evidence snippets.
        low_confidence_fields: Field paths requiring user review.
        warnings: Safe non-medical warnings for preview UI.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["supplement-parser-output-v2"] = SUPPLEMENT_PARSER_OUTPUT_V2
    product: ParserProduct = Field(default_factory=ParserProduct)
    serving: ParserServing = Field(default_factory=ParserServing)
    ingredients: list[ParserIngredient] = Field(default_factory=list, max_length=80)
    label_sections: list[ParserLabelSection] = Field(default_factory=list, max_length=40)
    intake_method: ParserIntakeMethod = Field(default_factory=ParserIntakeMethod)
    precautions: list[ParserPrecaution] = Field(default_factory=list, max_length=40)
    functional_claims: list[ParserFunctionalClaim] = Field(default_factory=list, max_length=40)
    evidence_spans: list[ParserEvidenceSpan] = Field(default_factory=list, max_length=160)
    low_confidence_fields: list[str] = Field(default_factory=list, max_length=80)
    warnings: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("low_confidence_fields", "warnings")
    @classmethod
    def normalize_string_lists(cls, values: list[str]) -> list[str]:
        """Normalize parser-produced review lists.

        Args:
            values: Candidate field paths or warnings.

        Returns:
            Trimmed unique strings.
        """
        return _normalize_unique_strings(values)

    @model_validator(mode="after")
    def validate_evidence_refs(self) -> Self:
        """Validate non-empty evidence references point to known spans.

        Returns:
            Validated structured parser output with ungrounded fields flagged
            for user review.

        Raises:
            ValueError: If any evidence reference is dangling.
        """
        spans_by_id = {span.span_id: span for span in self.evidence_spans}
        span_ids = set(spans_by_id)
        refs: list[str] = []
        refs.extend(self.product.evidence_refs)
        refs.extend(self.serving.evidence_refs)
        refs.extend(self.intake_method.evidence_refs)
        for ingredient in self.ingredients:
            refs.extend(ingredient.evidence_refs)
        for section in self.label_sections:
            refs.extend(section.evidence_refs)
        for precaution in self.precautions:
            refs.extend(precaution.evidence_refs)
        for claim in self.functional_claims:
            refs.extend(claim.evidence_refs)
        missing = sorted({ref for ref in refs if ref not in span_ids})
        if missing:
            raise ValueError(f"Unknown evidence_refs: {missing}")
        self._mark_ungrounded_evidence_fields(spans_by_id)
        return self

    def _mark_ungrounded_evidence_fields(
        self,
        spans_by_id: dict[str, ParserEvidenceSpan],
    ) -> None:
        """Flag parser fields that are not visible in their referenced evidence.

        Args:
            spans_by_id: Evidence spans keyed by span id.
        """
        self._check_grounded_values(
            "product",
            self.product.evidence_refs,
            {
                "product_name": self.product.product_name,
                "manufacturer": self.product.manufacturer,
            },
            spans_by_id,
        )
        self._check_grounded_values(
            "serving",
            self.serving.evidence_refs,
            {
                "serving_size_text": self.serving.serving_size_text,
                "serving_amount": self.serving.serving_amount,
                "serving_unit": self.serving.serving_unit,
                "daily_servings": self.serving.daily_servings,
                "total_amount": self.serving.total_amount,
                "total_unit": self.serving.total_unit,
            },
            spans_by_id,
        )
        for index, ingredient in enumerate(self.ingredients):
            self._check_grounded_values(
                f"ingredients.{index}",
                ingredient.evidence_refs,
                {
                    "display_name": ingredient.display_name,
                    "amount": ingredient.amount,
                    "unit": ingredient.unit,
                    "amount_text": ingredient.amount_text,
                },
                spans_by_id,
            )
        self._check_grounded_values(
            "intake_method",
            self.intake_method.evidence_refs,
            {
                "text": self.intake_method.text,
                "times_per_day": self.intake_method.structured.times_per_day,
                "amount_per_time": self.intake_method.structured.amount_per_time,
                "amount_unit": self.intake_method.structured.amount_unit,
            },
            spans_by_id,
        )
        for index, precaution in enumerate(self.precautions):
            self._check_grounded_values(
                f"precautions.{index}",
                precaution.evidence_refs,
                {"text": precaution.text},
                spans_by_id,
            )

    def _check_grounded_values(
        self,
        field_prefix: str,
        evidence_refs: list[str],
        values: dict[str, object],
        spans_by_id: dict[str, ParserEvidenceSpan],
    ) -> None:
        """Flag values that do not appear in their referenced excerpts.

        Args:
            field_prefix: Parser field path prefix.
            evidence_refs: Evidence span ids supporting the fields.
            values: Field names and values to verify.
            spans_by_id: Evidence spans keyed by span id.
        """
        if not evidence_refs:
            return
        evidence_text = _normalize_evidence_text(
            " ".join(spans_by_id[ref].text_excerpt for ref in evidence_refs if ref in spans_by_id)
        )
        for field_name, value in values.items():
            if _is_value_grounded(value, evidence_text):
                continue
            _append_unique_bounded(
                self.low_confidence_fields,
                f"{field_prefix}.{field_name}",
                limit=80,
            )
            _append_unique_bounded(self.warnings, EVIDENCE_GROUNDING_WARNING, limit=20)

    @property
    def parsed_product(self) -> SupplementParserProduct:
        """Return a legacy product view for compatibility.

        Returns:
            Legacy product view derived from V2 fields.
        """
        return SupplementParserProduct(
            product_name=self.product.product_name,
            manufacturer=self.product.manufacturer,
            serving_size=self.serving.serving_size_text,
            daily_servings=self.serving.daily_servings,
        )

    @property
    def ingredient_candidates(self) -> list[SupplementParserIngredientCandidate]:
        """Return legacy ingredient candidates for compatibility.

        Returns:
            Legacy ingredient candidate views derived from V2 ingredients.
        """
        return [
            SupplementParserIngredientCandidate(
                display_name=ingredient.display_name,
                amount=ingredient.amount,
                unit=ingredient.unit,
                confidence=ingredient.confidence,
            )
            for ingredient in self.ingredients
        ]


StructuredParseResultLike = SupplementStructuredParseResult | SupplementStructuredParseResultV2


def coerce_supplement_structured_parse_result_v2(
    result: StructuredParseResultLike,
) -> SupplementStructuredParseResultV2:
    """Convert legacy or expanded parser output into the V2 parser contract.

    Args:
        result: Legacy or V2 parser result.

    Returns:
        V2 structured parser output.
    """
    if isinstance(result, SupplementStructuredParseResultV2):
        return result
    return SupplementStructuredParseResultV2(
        product=ParserProduct(
            product_name=result.parsed_product.product_name,
            manufacturer=result.parsed_product.manufacturer,
        ),
        serving=ParserServing(
            serving_size_text=result.parsed_product.serving_size,
            daily_servings=result.parsed_product.daily_servings,
        ),
        ingredients=[
            ParserIngredient(
                display_name=candidate.display_name,
                amount=candidate.amount,
                unit=candidate.unit,
                confidence=candidate.confidence,
            )
            for candidate in result.ingredient_candidates
        ],
        low_confidence_fields=result.low_confidence_fields,
        warnings=result.warnings,
    )


class SupplementOCRTextParseRequest(BaseModel):
    """Request payload for attaching OCR text to an existing preview.

    Attributes:
        ocr_text: OCR text extracted from a supplement label. The API normalizes,
            hashes, and parses this text without storing it raw.
        ocr_provider: Bounded OCR provider label, such as ``manual`` or ``clova``.
        ocr_confidence: Optional provider-level OCR confidence from 0.0 to 1.0.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ocr_text: str = Field(min_length=1, max_length=50_000)
    ocr_provider: str = Field(min_length=1, max_length=64)
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)


__all__ = [
    "EVIDENCE_GROUNDING_WARNING",
    "SUPPLEMENT_PARSER_OUTPUT_V2",
    "ParserEvidenceSource",
    "ParserEvidenceSpan",
    "ParserFrequency",
    "ParserFunctionalClaim",
    "ParserFunctionalClaimType",
    "ParserIngredient",
    "ParserIntakeMethod",
    "ParserLabelSection",
    "ParserPrecaution",
    "ParserPrecautionCategory",
    "ParserPrecautionSeverity",
    "ParserProduct",
    "ParserSectionType",
    "ParserServing",
    "ParserStructuredIntakeMethod",
    "ParserWithFoodFlag",
    "StructuredParseResultLike",
    "SupplementOCRTextParseRequest",
    "SupplementParserIngredientCandidate",
    "SupplementParserProduct",
    "SupplementStructuredParseResult",
    "SupplementStructuredParseResultV2",
    "coerce_supplement_structured_parse_result_v2",
]
