"""Local Ollama vision assist for OCR fallback candidate extraction."""

from __future__ import annotations

import base64
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from src.config import Settings
from src.llm.ollama import (
    OllamaChatClient,
    OllamaClientError,
    OllamaConfigurationError,
    OllamaReadiness,
    OllamaStructuredOutputError,
    extract_ollama_message_content,
    extract_ollama_model_names,
    validate_local_ollama_settings,
)
from src.ocr.base import OCRAdapter, OCRImageInput, OCRResult
from src.vision.preprocessing import VisionPreprocessingError, crop_image_to_bounding_box

OLLAMA_VISION_ASSIST_PROVIDER = "ollama_vision_assist"

OLLAMA_VISION_ASSIST_SYSTEM_PROMPT = """
You are a local supplement label OCR fallback component.
Extract only text fragments that are visibly present in the image.
Do not infer ingredients, amounts, dosage, health effects, risks, or product facts
from outside knowledge. Do not provide medical or nutrition advice. If text is not
visible, return an empty list or null. Return only JSON matching the supplied schema.
""".strip()


class OllamaVisionTextCandidateResult(BaseModel):
    """Validated visible-text candidates returned by a local vision model.

    Attributes:
        visible_text_fragments: Text fragments visibly present in the image.
        possible_product_name: Product name candidate only when visibly present.
        source_region: Whether the image sent to the model was full image or YOLO ROI.
        low_confidence_fields: Candidate fields requiring user review.
        warnings: Non-medical warnings to surface in preview metadata.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    visible_text_fragments: list[str] = Field(default_factory=list, max_length=30)
    possible_product_name: str | None = Field(default=None, max_length=200)
    source_region: Literal["full_image", "yolo_roi"]
    low_confidence_fields: list[str] = Field(default_factory=list, max_length=20)
    warnings: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("visible_text_fragments", "low_confidence_fields", "warnings")
    @classmethod
    def _normalize_string_list(cls, values: list[str]) -> list[str]:
        """Normalize model-produced string lists and remove duplicates.

        Args:
            values: Candidate string values.

        Returns:
            Trimmed non-empty strings in first-seen order.
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


class OllamaVisionAssistAdapter(OCRAdapter):
    """OCR-like fallback adapter backed by a local Ollama vision model.

    This adapter is intentionally not a primary OCR provider. Callers must invoke it
    only when OCR is empty or low-confidence according to runtime policy.
    """

    def __init__(
        self,
        settings: Settings,
        client: OllamaChatClient | None = None,
    ) -> None:
        """Initialize the local Ollama vision assist adapter.

        Args:
            settings: Runtime settings containing local Ollama and model configuration.
            client: Optional injected Ollama transport for tests.
        """
        self.settings = settings
        self.client = client or OllamaChatClient(settings)

    async def extract_text(self, image: OCRImageInput) -> OCRResult:
        """Extract visible text candidates from an image as OCR fallback.

        Args:
            image: Validated image input. If ``label_region`` is present, only that
                crop is sent to the local vision model.

        Returns:
            OCR-like text candidate result with provider ``ollama_vision_assist``.

        Raises:
            OllamaConfigurationError: If the feature flag or local model is invalid.
            OllamaClientError: If the local Ollama API call fails.
            OllamaStructuredOutputError: If model output fails schema validation.
        """
        _validate_vision_settings(self.settings)
        image_payload, source_region = _build_image_payload(image)
        schema = OllamaVisionTextCandidateResult.model_json_schema()
        payload = _build_vision_chat_payload(
            image_payload=image_payload,
            source_region=source_region,
            schema=schema,
            settings=self.settings,
        )
        response_data = await self.client.post_chat(payload)
        content = extract_ollama_message_content(response_data)
        try:
            result = OllamaVisionTextCandidateResult.model_validate_json(content)
        except ValidationError as exc:
            raise OllamaStructuredOutputError(
                "Ollama vision assist output failed schema validation."
            ) from exc
        return OCRResult(
            text=_candidate_text(result),
            provider=OLLAMA_VISION_ASSIST_PROVIDER,
            confidence=None,
        )


async def check_ollama_vision_readiness(
    settings: Settings,
    client: OllamaChatClient | None = None,
) -> OllamaReadiness:
    """Check whether the configured local Ollama vision model is available.

    Args:
        settings: Runtime settings.
        client: Optional Ollama transport, primarily for tests.

    Returns:
        Sanitized readiness status for the configured vision model.
    """
    model = settings.ollama_vision_model or ""
    try:
        validate_local_ollama_settings(settings)
        if not model:
            raise OllamaConfigurationError("OLLAMA_VISION_MODEL is required.")
    except OllamaConfigurationError:
        return OllamaReadiness(
            base_url=settings.ollama_base_url,
            model=model,
            ready=False,
            model_present=False,
            error_code="configuration_invalid",
        )

    active_client = client or OllamaChatClient(settings)
    try:
        response_data = await active_client.list_models()
        model_names = extract_ollama_model_names(response_data)
    except OllamaClientError:
        return OllamaReadiness(
            base_url=settings.ollama_base_url,
            model=model,
            ready=False,
            model_present=False,
            error_code="ollama_unavailable",
        )

    model_present = model in model_names
    return OllamaReadiness(
        base_url=settings.ollama_base_url,
        model=model,
        ready=model_present,
        model_present=model_present,
        model_names=model_names,
        error_code=None if model_present else "model_missing",
    )


def _validate_vision_settings(settings: Settings) -> None:
    """Validate local-only settings before sending image bytes to Ollama.

    Args:
        settings: Runtime settings.

    Raises:
        OllamaConfigurationError: If the feature is disabled or not local-only.
    """
    if not settings.enable_multimodal_llm:
        raise OllamaConfigurationError("ENABLE_MULTIMODAL_LLM=false blocks vision assist.")
    if not settings.ollama_vision_model:
        raise OllamaConfigurationError("OLLAMA_VISION_MODEL is required for vision assist.")
    validate_local_ollama_settings(settings)


def _build_image_payload(image: OCRImageInput) -> tuple[str, Literal["full_image", "yolo_roi"]]:
    """Build a base64 image payload without persisting raw image bytes.

    Args:
        image: Validated image input.

    Returns:
        Base64 image payload and source-region marker.

    Raises:
        OllamaClientError: If a requested ROI crop cannot be produced.
    """
    if image.label_region is None:
        return base64.b64encode(image.image_bytes).decode("ascii"), "full_image"
    try:
        cropped = crop_image_to_bounding_box(image.image_bytes, image.label_region)
    except VisionPreprocessingError as exc:
        raise OllamaClientError("Vision assist ROI crop failed.") from exc
    return base64.b64encode(cropped).decode("ascii"), "yolo_roi"


def _build_vision_chat_payload(
    *,
    image_payload: str,
    source_region: Literal["full_image", "yolo_roi"],
    schema: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    """Build an Ollama Chat API payload for visible-text candidate extraction.

    Args:
        image_payload: Base64-encoded image bytes.
        source_region: Source marker for the submitted image.
        schema: JSON Schema for structured output.
        settings: Runtime settings.

    Returns:
        JSON payload for ``POST /api/chat``.
    """
    user_prompt = (
        "Extract only text that is visibly present on this supplement image. "
        f"The submitted image source is {source_region}. "
        "Do not infer hidden ingredients, amounts, dosage, benefits, risks, or advice. "
        "Use null or empty arrays for unknown values.\n\n"
        "Return JSON that conforms to this JSON Schema:\n"
        f"{json.dumps(schema, ensure_ascii=False)}"
    )
    return {
        "model": settings.ollama_vision_model,
        "messages": [
            {"role": "system", "content": OLLAMA_VISION_ASSIST_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt, "images": [image_payload]},
        ],
        "stream": False,
        "think": False,
        "format": schema,
        "options": {"temperature": settings.ollama_temperature},
    }


def _candidate_text(result: OllamaVisionTextCandidateResult) -> str:
    """Convert visible-text candidates into parser input text.

    Args:
        result: Schema-validated vision assist result.

    Returns:
        Newline-delimited candidate text. The text remains a preview input and is
        never persisted raw by downstream parser storage.
    """
    fragments = list(result.visible_text_fragments)
    if result.possible_product_name and result.possible_product_name not in fragments:
        fragments.insert(0, result.possible_product_name)
    return "\n".join(fragments).strip()
