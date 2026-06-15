"""Optional Ultralytics YOLO runner for food image detection."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol, cast

from PIL import Image, UnidentifiedImageError

from src.utils.image_safety import ImageSafetyError, safe_load_with_bomb_guard
from src.vision.base import BoundingBox, VisionError
from src.vision.preprocessing import VisionPreprocessingError, clamp_bounding_box

XYXY_COORDINATE_COUNT = 4
DEFAULT_FOOD_CLIP_PROMPTS = (
    "a photo of food",
    "a meal",
    "a dish",
    "Korean food",
    "restaurant food",
)
DEFAULT_NOT_FOOD_CLIP_PROMPTS = (
    "a table",
    "a plate without food",
    "a hand",
    "a package",
    "a menu",
    "a receipt",
    "a background",
)
EXP16B_UNSUPPORTED_CLASS_LABELS = frozenset(
    {
        "seafood-jjim",
        "seafood-spicy-tang",
        "seafood-clear-tang",
        "squid-dish",
        "shrimp-dish",
        "grilled-beef",
        "jjamppong",
        "fried-rice",
        "dumplings",
        "rice-bowl",
    }
)


class _PredictModel(Protocol):
    """Small protocol for the Ultralytics model methods used by this runner."""

    names: Any

    def predict(self, **kwargs: Any) -> Any:
        """Run object detection.

        Args:
            **kwargs: Keyword arguments passed to ``ultralytics.YOLO.predict``.

        Returns:
            Ultralytics prediction results.
        """
        ...


ModelFactory = Callable[[str], _PredictModel]


class FoodRegionFilter(Protocol):
    """Protocol for optional food/non-food crop filters."""

    def filter(
        self,
        images: Sequence[Image.Image],
        *,
        threshold: float,
    ) -> tuple[Sequence[bool], Sequence[float]]:
        """Return keep decisions and confidence scores for image crops.

        Args:
            images: Cropped food-region candidate images.
            threshold: Minimum food probability required to keep a crop.

        Returns:
            Tuple of keep flags and food scores.
        """
        ...


@dataclass(frozen=True)
class FoodDetection:
    """Sanitized food detector output.

    Attributes:
        label: Model class label for user review.
        confidence: Model confidence from 0.0 to 1.0.
        bbox: Pixel-space object box metadata.
        model: Sanitized detector model label.
        classifier_model: Sanitized classifier model label when crop
            classification supplied the display label.
    """

    label: str
    confidence: float
    bbox: BoundingBox
    model: str
    classifier_model: str | None = None


class FoodYoloDetector:
    """Run a local Ultralytics food detector and expose review-only candidates.

    The detector produces food labels, confidence, and bounding boxes only. It
    does not infer nutrition facts, treatment claims, dosage guidance, or
    medical risk.
    """

    def __init__(
        self,
        *,
        model_path: str,
        model_label: str,
        min_confidence: float,
        max_detections: int,
        iou_threshold: float | None = None,
        agnostic_nms: bool = False,
        image_size: int | None = None,
        clip_filter: FoodRegionFilter | None = None,
        clip_threshold: float = 0.25,
        crop_padding: float = 1.0,
        classifier_model_path: str | None = None,
        classifier_model_label: str | None = None,
        classifier_min_confidence: float = 0.10,
        model_factory: ModelFactory | None = None,
        classifier_model_factory: ModelFactory | None = None,
        excluded_classifier_labels: frozenset[str] = EXP16B_UNSUPPORTED_CLASS_LABELS,
    ) -> None:
        """Initialize a food YOLO detector.

        Args:
            model_path: Local YOLO model path or model tag.
            model_label: Sanitized label exposed in pipeline metadata.
            min_confidence: Minimum detection confidence.
            max_detections: Maximum candidates returned to the review UI.
            iou_threshold: Optional NMS IoU threshold passed to YOLO predict.
            agnostic_nms: Whether YOLO predict should run class-agnostic NMS.
            image_size: Optional YOLO predict image size.
            clip_filter: Optional food/non-food crop filter.
            clip_threshold: Minimum CLIP food probability required to keep a crop.
            crop_padding: Multiplier used when cropping detector boxes.
            classifier_model_path: Optional crop classifier path or tag.
            classifier_model_label: Sanitized classifier label for metadata.
            classifier_min_confidence: Minimum crop classifier confidence.
            model_factory: Optional test factory. Production uses ``ultralytics.YOLO``.
            classifier_model_factory: Optional test classifier factory.
            excluded_classifier_labels: Class labels excluded from the crop classifier
                because they are not supported by the 40-class nutrition subset.

        Raises:
            ValueError: If ``max_detections`` is not positive.
        """
        if max_detections <= 0:
            raise ValueError("max_detections must be > 0")
        if iou_threshold is not None and not 0.0 <= iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be between 0 and 1")
        if image_size is not None and image_size <= 0:
            raise ValueError("image_size must be > 0")
        if not 0.0 <= clip_threshold <= 1.0:
            raise ValueError("clip_threshold must be between 0 and 1")
        if crop_padding < 1.0:
            raise ValueError("crop_padding must be >= 1")
        if not 0.0 <= classifier_min_confidence <= 1.0:
            raise ValueError("classifier_min_confidence must be between 0 and 1")
        self.model_path = model_path
        self.model_label = model_label
        self.min_confidence = min_confidence
        self.max_detections = max_detections
        self.iou_threshold = iou_threshold
        self.agnostic_nms = agnostic_nms
        self.image_size = image_size
        self.clip_filter = clip_filter
        self.clip_threshold = clip_threshold
        self.crop_padding = crop_padding
        self.classifier_model_path = classifier_model_path
        self.classifier_model_label = classifier_model_label
        self.classifier_min_confidence = classifier_min_confidence
        self.model_factory = model_factory
        self.classifier_model_factory = classifier_model_factory
        self.excluded_classifier_labels = excluded_classifier_labels
        self._model: _PredictModel | None = None
        self._classifier_model: _PredictModel | None = None

    def detect_foods(self, image_bytes: bytes) -> list[FoodDetection]:
        """Detect review-only food candidates from validated image bytes.

        Args:
            image_bytes: Validated JPEG/PNG/WebP image bytes.

        Returns:
            Food detection candidates sorted by confidence. Empty list means no
            reviewable food object was found.

        Raises:
            VisionError: If the model cannot load or prediction fails.
        """
        image, image_width, image_height = _decode_image(image_bytes)
        model = self._load_model()
        try:
            prediction_results = model.predict(**self._prediction_kwargs(image))
        except Exception as exc:
            raise VisionError("Food YOLO prediction failed.") from exc

        detections = _normalize_prediction_results(
            prediction_results=prediction_results,
            names=_extract_names(prediction_results, model),
            image_width=image_width,
            image_height=image_height,
            min_confidence=self.min_confidence,
            max_detections=self.max_detections,
            model_label=self.model_label,
        )
        detections = self._apply_clip_filter(image, detections)
        return self._classify_detections(image, detections)

    def _prediction_kwargs(self, image: Image.Image) -> dict[str, object]:
        """Build bounded Ultralytics predict kwargs for detector inference.

        Args:
            image: Decoded PIL image.

        Returns:
            Keyword arguments for ``ultralytics.YOLO.predict``.
        """
        kwargs: dict[str, object] = {
            "source": image,
            "conf": self.min_confidence,
            "verbose": False,
            "max_det": self.max_detections,
            "agnostic_nms": self.agnostic_nms,
        }
        if self.iou_threshold is not None:
            kwargs["iou"] = self.iou_threshold
        if self.image_size is not None:
            kwargs["imgsz"] = self.image_size
        return kwargs

    def _load_model(self) -> _PredictModel:
        """Load the optional Ultralytics model lazily.

        Returns:
            Loaded model object.

        Raises:
            VisionError: If the optional dependency or model is unavailable.
        """
        if self._model is not None:
            return self._model
        factory = self.model_factory or _load_ultralytics_yolo
        try:
            self._model = factory(self.model_path)
        except VisionError:
            raise
        except Exception as exc:
            raise VisionError("Food YOLO model could not be loaded.") from exc
        return self._model

    def _load_classifier_model(self) -> _PredictModel:
        """Load the optional crop classifier lazily.

        Returns:
            Loaded classifier model.

        Raises:
            VisionError: If the classifier path or dependency is unavailable.
        """
        if self._classifier_model is not None:
            return self._classifier_model
        if not self.classifier_model_path:
            raise VisionError("Food classifier model path is not configured.")
        factory = self.classifier_model_factory or _load_ultralytics_yolo
        try:
            self._classifier_model = factory(self.classifier_model_path)
        except VisionError:
            raise
        except Exception as exc:
            raise VisionError("Food classifier model could not be loaded.") from exc
        return self._classifier_model

    def _apply_clip_filter(
        self,
        image: Image.Image,
        detections: list[FoodDetection],
    ) -> list[FoodDetection]:
        """Filter detector crops with optional CLIP food/non-food scoring.

        Args:
            image: Source image.
            detections: Detector candidates.

        Returns:
            Detections that pass the optional CLIP filter.

        Raises:
            VisionError: If the configured filter fails.
        """
        if self.clip_filter is None or not detections:
            return detections
        crop_pairs = _crop_detections(image, detections, self.crop_padding)
        if not crop_pairs:
            return []
        crops = [crop for _, crop in crop_pairs]
        try:
            keep_flags, scores = self.clip_filter.filter(crops, threshold=self.clip_threshold)
        except Exception as exc:
            raise VisionError("Food CLIP filter failed.") from exc

        filtered: list[FoodDetection] = []
        for index, (detection, _) in enumerate(crop_pairs):
            keep = bool(_item_at(list(keep_flags), index))
            score = _float_or_none(_item_at(list(scores), index))
            if keep:
                filtered.append(detection)
            elif score is None:
                continue
        return filtered

    def _classify_detections(
        self,
        image: Image.Image,
        detections: list[FoodDetection],
    ) -> list[FoodDetection]:
        """Classify detector crops into nutrition ``class_en`` labels when configured.

        Args:
            image: Source image.
            detections: Detector or CLIP-filtered candidates.

        Returns:
            Classifier-labelled detections when a classifier is configured;
            otherwise the original detector labels.

        Raises:
            VisionError: If the configured classifier fails.
        """
        if not self.classifier_model_path or not detections:
            return detections
        classifier_model = self._load_classifier_model()
        classifier_names = _names_from_model(classifier_model)
        supported_class_ids = _supported_classifier_class_ids(
            classifier_names,
            self.excluded_classifier_labels,
        )
        classifier_label = self.classifier_model_label or food_classifier_model_label(
            self.classifier_model_path,
            "food_exp16b_local",
        )
        if classifier_label is None:
            raise VisionError("Food classifier metadata label is not configured.")

        classified: list[FoodDetection] = []
        for detection, crop in _crop_detections(image, detections, self.crop_padding):
            kwargs: dict[str, object] = {
                "source": crop,
                "conf": self.classifier_min_confidence,
                "verbose": False,
            }
            if supported_class_ids is not None:
                kwargs["classes"] = supported_class_ids
            try:
                prediction_results = classifier_model.predict(**kwargs)
            except Exception as exc:
                raise VisionError("Food classifier prediction failed.") from exc
            classifier_names = _extract_names(prediction_results, classifier_model)
            label, confidence = _best_classifier_prediction(
                prediction_results,
                classifier_names,
                min_confidence=self.classifier_min_confidence,
                excluded_labels=self.excluded_classifier_labels,
            )
            if label is None or confidence is None:
                continue
            model_label = f"{self.model_label}+{classifier_label}"
            classified.append(
                FoodDetection(
                    label=label,
                    confidence=confidence,
                    bbox=BoundingBox(
                        x=detection.bbox.x,
                        y=detection.bbox.y,
                        width=detection.bbox.width,
                        height=detection.bbox.height,
                        confidence=confidence,
                        label=label,
                        model=model_label,
                    ),
                    model=model_label,
                    classifier_model=classifier_label,
                )
            )
        classified.sort(key=lambda detection: detection.confidence, reverse=True)
        return classified[: self.max_detections]


def food_model_label(model_path: str | None, configured_label: str) -> str | None:
    """Return a sanitized food detector model label for metadata.

    Args:
        model_path: Configured local model path.
        configured_label: Operator-provided public model label.

    Returns:
        Sanitized metadata label, or None if no model path is configured.
    """
    if model_path is None or not model_path.strip():
        return None
    safe_label = configured_label.strip() or "food_yolo_local"
    return f"{safe_label}:{Path(model_path).name}"


def food_classifier_model_label(model_path: str | None, configured_label: str) -> str | None:
    """Return a sanitized crop classifier model label for metadata.

    Args:
        model_path: Configured local classifier model path.
        configured_label: Operator-provided public classifier label.

    Returns:
        Sanitized metadata label, or None if no model path is configured.
    """
    if model_path is None or not model_path.strip():
        return None
    safe_label = configured_label.strip() or "food_exp16b_local"
    return f"{safe_label}:{Path(model_path).name}"


class FoodClipFilter:
    """Lazy CLIP food/non-food filter for YOLO crop candidates."""

    def __init__(
        self,
        *,
        model_id: str,
        food_prompts: Sequence[str] = DEFAULT_FOOD_CLIP_PROMPTS,
        non_food_prompts: Sequence[str] = DEFAULT_NOT_FOOD_CLIP_PROMPTS,
        device: str | None = None,
    ) -> None:
        """Initialize a CLIP crop filter.

        Args:
            model_id: Hugging Face model id loaded through Transformers.
            food_prompts: Positive food text prompts.
            non_food_prompts: Negative non-food text prompts.
            device: Optional torch device string.
        """
        self.model_id = model_id
        self.food_prompts = tuple(food_prompts)
        self.non_food_prompts = tuple(non_food_prompts)
        self.device = device
        self._torch: Any | None = None
        self._model: Any | None = None
        self._processor: Any | None = None

    def filter(
        self,
        images: Sequence[Image.Image],
        *,
        threshold: float,
    ) -> tuple[Sequence[bool], Sequence[float]]:
        """Return keep decisions and CLIP food scores for crop candidates.

        Args:
            images: Cropped candidate images.
            threshold: Minimum food probability required to keep a crop.

        Returns:
            Tuple of keep flags and scores.

        Raises:
            VisionError: If optional CLIP dependencies or model inference fail.
        """
        scores = self.score_batch(images)
        return [score >= threshold for score in scores], scores

    def score_batch(self, images: Sequence[Image.Image]) -> list[float]:
        """Score each crop as food using CLIP text-image similarity.

        Args:
            images: Cropped candidate images.

        Returns:
            Food probabilities in the same order as ``images``.

        Raises:
            VisionError: If optional CLIP dependencies or model inference fail.
        """
        if not images:
            return []
        torch, model, processor = self._load_components()
        prompts = [*self.food_prompts, *self.non_food_prompts]
        try:
            inputs = processor(
                text=prompts,
                images=list(images),
                return_tensors="pt",
                padding=True,
            )
            if self.device:
                inputs = {
                    key: value.to(self.device) if hasattr(value, "to") else value
                    for key, value in inputs.items()
                }
            with torch.inference_mode():
                image_features = model.get_image_features(pixel_values=inputs["pixel_values"])
                text_features = model.get_text_features(
                    input_ids=inputs["input_ids"],
                    attention_mask=inputs.get("attention_mask"),
                )
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                similarity = image_features @ text_features.T
                food_scores = similarity[:, : len(self.food_prompts)].max(dim=1).values
                non_food_scores = similarity[:, len(self.food_prompts) :].max(dim=1).values
                logits = torch.stack([non_food_scores, food_scores], dim=1) * 100.0
                probabilities = torch.softmax(logits, dim=1)[:, 1]
            return [float(value) for value in probabilities.detach().cpu().tolist()]
        except Exception as exc:
            raise VisionError("Food CLIP scoring failed.") from exc

    def _load_components(self) -> tuple[Any, Any, Any]:
        """Load torch, CLIP model, and CLIP processor lazily.

        Returns:
            Tuple of torch module, CLIP model, and CLIP processor.

        Raises:
            VisionError: If optional dependencies are missing or model load fails.
        """
        if self._torch is not None and self._model is not None and self._processor is not None:
            return self._torch, self._model, self._processor
        try:
            torch = import_module("torch")
            transformers = import_module("transformers")
            processor_class = transformers.CLIPProcessor
            model_class = transformers.CLIPModel
            processor = processor_class.from_pretrained(self.model_id)
            model = model_class.from_pretrained(self.model_id)
            if self.device:
                model = model.to(self.device)
            model.eval()
        except ImportError as exc:
            raise VisionError("Install backend .[vision] before enabling food CLIP filtering.") from exc
        except Exception as exc:
            raise VisionError("Food CLIP model could not be loaded.") from exc
        self._torch = torch
        self._processor = processor
        self._model = model
        return torch, model, processor


def _load_ultralytics_yolo(model_path: str) -> _PredictModel:
    """Load ``ultralytics.YOLO`` only when food detection is enabled.

    Args:
        model_path: Local model path or model tag.

    Returns:
        Ultralytics YOLO model instance.

    Raises:
        VisionError: If the optional dependency is not installed.
    """
    try:
        yolo_class = cast(Any, import_module("ultralytics")).YOLO
    except ImportError as exc:
        raise VisionError("Install backend .[vision] before enabling food YOLO.") from exc
    return cast(_PredictModel, yolo_class(model_path))


def _decode_image(image_bytes: bytes) -> tuple[Image.Image, int, int]:
    """Decode image bytes into an RGB PIL image for object detection.

    Args:
        image_bytes: Validated image bytes.

    Returns:
        RGB image and decoded dimensions.

    Raises:
        VisionError: If the image cannot be decoded.
    """
    try:
        decoded = safe_load_with_bomb_guard(image_bytes)
    except ImageSafetyError as exc:
        raise VisionError("Image cannot be decoded for food YOLO.") from exc
    try:
        with decoded as image:
            width, height = image.size
            return image.convert("RGB"), width, height
    except (OSError, UnidentifiedImageError) as exc:
        raise VisionError("Image cannot be decoded for food YOLO.") from exc


def _normalize_prediction_results(
    *,
    prediction_results: Any,
    names: Mapping[Any, Any] | Sequence[Any] | None,
    image_width: int,
    image_height: int,
    min_confidence: float,
    max_detections: int,
    model_label: str,
) -> list[FoodDetection]:
    """Normalize Ultralytics boxes into food review candidates.

    Args:
        prediction_results: Raw result list returned by Ultralytics.
        names: Class-id to label mapping.
        image_width: Source image width.
        image_height: Source image height.
        min_confidence: Minimum accepted confidence.
        max_detections: Maximum returned candidate count.
        model_label: Sanitized detector model label.

    Returns:
        Food detections sorted by confidence.
    """
    result = _first_result(prediction_results)
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return []

    coordinates = _as_list(getattr(boxes, "xyxy", None))
    class_ids = _as_list(getattr(boxes, "cls", None))
    confidences = _as_list(getattr(boxes, "conf", None))

    detections: list[FoodDetection] = []
    for index, coordinate in enumerate(coordinates):
        confidence = _float_or_none(_item_at(confidences, index))
        if confidence is None or confidence < min_confidence:
            continue
        label = _label_for_class(_item_at(class_ids, index), names)
        box = _box_from_xyxy(
            coordinate,
            confidence=confidence,
            label=label,
            model_label=model_label,
        )
        try:
            clamped = clamp_bounding_box(box, image_width=image_width, image_height=image_height)
        except VisionPreprocessingError:
            continue
        detections.append(
            FoodDetection(
                label=label,
                confidence=confidence,
                bbox=clamped,
                model=model_label,
            )
        )

    detections.sort(key=lambda detection: detection.confidence, reverse=True)
    return detections[:max_detections]


def _crop_detections(
    image: Image.Image,
    detections: Sequence[FoodDetection],
    padding: float,
) -> list[tuple[FoodDetection, Image.Image]]:
    """Crop source image regions for detector candidates.

    Args:
        image: Source image.
        detections: Detector candidates.
        padding: Multiplicative bbox expansion factor.

    Returns:
        Valid crop pairs.
    """
    width, height = image.size
    crop_pairs: list[tuple[FoodDetection, Image.Image]] = []
    for detection in detections:
        box = detection.bbox
        center_x = box.x + box.width / 2
        center_y = box.y + box.height / 2
        crop_width = box.width * padding
        crop_height = box.height * padding
        x_min = max(0, round(center_x - crop_width / 2))
        y_min = max(0, round(center_y - crop_height / 2))
        x_max = min(width, round(center_x + crop_width / 2))
        y_max = min(height, round(center_y + crop_height / 2))
        if x_min >= x_max or y_min >= y_max:
            continue
        crop_pairs.append((detection, image.crop((x_min, y_min, x_max, y_max))))
    return crop_pairs


def _best_classifier_prediction(
    prediction_results: Any,
    names: Mapping[Any, Any] | Sequence[Any] | None,
    *,
    min_confidence: float,
    excluded_labels: frozenset[str],
) -> tuple[str | None, float | None]:
    """Return the highest-confidence crop classifier label.

    Args:
        prediction_results: Raw classifier result list.
        names: Class-id to class_en mapping.
        min_confidence: Minimum accepted classifier confidence.
        excluded_labels: Labels excluded from the 40-class nutrition subset.

    Returns:
        Class label and confidence, or ``(None, None)`` when no usable
        classifier output is present.
    """
    result = _first_result(prediction_results)
    box_label, box_confidence = _best_box_prediction(
        getattr(result, "boxes", None),
        names,
        min_confidence=min_confidence,
        excluded_labels=excluded_labels,
    )
    if box_label is not None:
        return box_label, box_confidence
    return _best_probs_prediction(
        getattr(result, "probs", None),
        names,
        min_confidence=min_confidence,
        excluded_labels=excluded_labels,
    )


def _best_box_prediction(
    boxes: Any,
    names: Mapping[Any, Any] | Sequence[Any] | None,
    *,
    min_confidence: float,
    excluded_labels: frozenset[str],
) -> tuple[str | None, float | None]:
    """Return the best YOLO-box style classifier prediction."""
    if boxes is None:
        return None, None
    class_ids = _as_list(getattr(boxes, "cls", None))
    confidences = _as_list(getattr(boxes, "conf", None))
    best_label: str | None = None
    best_confidence: float | None = None
    for index, class_id in enumerate(class_ids):
        confidence = _float_or_none(_item_at(confidences, index))
        if confidence is None or confidence < min_confidence:
            continue
        label = _classifier_label_for_class(class_id, names)
        if label in excluded_labels:
            continue
        if best_confidence is None or confidence > best_confidence:
            best_label = label
            best_confidence = confidence
    return best_label, best_confidence


def _best_probs_prediction(
    probs: Any,
    names: Mapping[Any, Any] | Sequence[Any] | None,
    *,
    min_confidence: float,
    excluded_labels: frozenset[str],
) -> tuple[str | None, float | None]:
    """Return the best classification-probability style prediction."""
    if probs is None:
        return None, None
    top1 = _int_or_none(getattr(probs, "top1", None))
    top1_confidence = _float_or_none(getattr(probs, "top1conf", None))
    if top1 is not None and top1_confidence is not None:
        label = _classifier_label_for_class(top1, names)
        if top1_confidence >= min_confidence and label not in excluded_labels:
            return label, top1_confidence

    probabilities = _as_list(getattr(probs, "data", probs))
    best_label: str | None = None
    best_confidence: float | None = None
    for class_index, raw_confidence in enumerate(probabilities):
        confidence = _float_or_none(raw_confidence)
        if confidence is None or confidence < min_confidence:
            continue
        label = _classifier_label_for_class(class_index, names)
        if label in excluded_labels:
            continue
        if best_confidence is None or confidence > best_confidence:
            best_label = label
            best_confidence = confidence
    return best_label, best_confidence


def _supported_classifier_class_ids(
    names: Mapping[Any, Any] | Sequence[Any] | None,
    excluded_labels: frozenset[str],
) -> list[int] | None:
    """Return supported class ids for the 40-class nutrition subset.

    Args:
        names: Class-id to class_en mapping.
        excluded_labels: Labels excluded from the 40-class nutrition subset.

    Returns:
        Supported class ids, or None when the model does not expose names.
    """
    if names is None:
        return None
    supported: list[int] = []
    iterable = names.items() if isinstance(names, Mapping) else enumerate(names)
    for raw_class_id, raw_label in iterable:
        class_id = _int_or_none(raw_class_id)
        if class_id is None:
            continue
        label = _sanitize_classifier_label(str(raw_label))
        if label and label not in excluded_labels:
            supported.append(class_id)
    return supported or None


def _first_result(prediction_results: Any) -> Any:
    """Return the first result object from an Ultralytics prediction output.

    Args:
        prediction_results: Raw prediction output.

    Returns:
        First result object or the input object when it is not a list.
    """
    if isinstance(prediction_results, Sequence) and not isinstance(prediction_results, str | bytes):
        if not prediction_results:
            return None
        return prediction_results[0]
    return prediction_results


def _extract_names(
    prediction_results: Any,
    model: _PredictModel,
) -> Mapping[Any, Any] | Sequence[Any] | None:
    """Extract class names from the result or loaded model.

    Args:
        prediction_results: Raw prediction output.
        model: Loaded model object.

    Returns:
        Class labels, if exposed by the detector.
    """
    result = _first_result(prediction_results)
    for candidate in (getattr(result, "names", None), getattr(model, "names", None)):
        if isinstance(candidate, Mapping | Sequence) and not isinstance(candidate, str | bytes):
            return candidate
    return None


def _names_from_model(model: _PredictModel) -> Mapping[Any, Any] | Sequence[Any] | None:
    """Return class names exposed directly by an Ultralytics model.

    Args:
        model: Loaded detector or classifier model.

    Returns:
        Class names mapping/list, if present.
    """
    names = getattr(model, "names", None)
    if isinstance(names, Mapping | Sequence) and not isinstance(names, str | bytes):
        return names
    return None


def _as_list(value: Any) -> list[Any]:
    """Convert a tensor-like value into a Python list.

    Args:
        value: Tensor, ndarray, list, tuple, or scalar value.

    Returns:
        Python list representation.
    """
    if value is None:
        return []
    normalized = value
    for method_name in ("detach", "cpu"):
        method = getattr(normalized, method_name, None)
        if callable(method):
            normalized = method()
    tolist = getattr(normalized, "tolist", None)
    if callable(tolist):
        converted = tolist()
        return converted if isinstance(converted, list) else [converted]
    if isinstance(normalized, list):
        return normalized
    if isinstance(normalized, tuple):
        return list(normalized)
    return [normalized]


def _item_at(values: list[Any], index: int) -> Any:
    """Return a list item or None.

    Args:
        values: Candidate list.
        index: Desired item index.

    Returns:
        Item when present.
    """
    return values[index] if index < len(values) else None


def _float_or_none(value: Any) -> float | None:
    """Return a float when conversion is possible.

    Args:
        value: Candidate scalar.

    Returns:
        Float value or None.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _label_for_class(
    class_id: Any,
    names: Mapping[Any, Any] | Sequence[Any] | None,
) -> str:
    """Resolve a class id into a review label.

    Args:
        class_id: Detector class id.
        names: Optional detector names mapping/list.

    Returns:
        Sanitized label.
    """
    class_index = _int_or_none(class_id)
    raw_label: Any = None
    if class_index is not None and names is not None:
        if isinstance(names, Mapping):
            raw_label = names.get(class_index) or names.get(str(class_index))
        elif 0 <= class_index < len(names):
            raw_label = names[class_index]
    if raw_label is None and class_index is not None:
        raw_label = f"class_{class_index}"
    return _sanitize_label(str(raw_label or "unknown_food"))


def _classifier_label_for_class(
    class_id: Any,
    names: Mapping[Any, Any] | Sequence[Any] | None,
) -> str:
    """Resolve a classifier class id into a nutrition ``class_en`` label.

    Args:
        class_id: Classifier class id.
        names: Optional class-id to label mapping/list.

    Returns:
        Bounded class label preserving hyphens for ``food_nutrition.class_en`` joins.
    """
    class_index = _int_or_none(class_id)
    raw_label: Any = None
    if class_index is not None and names is not None:
        if isinstance(names, Mapping):
            raw_label = names.get(class_index) or names.get(str(class_index))
        elif 0 <= class_index < len(names):
            raw_label = names[class_index]
    if raw_label is None and class_index is not None:
        raw_label = f"class_{class_index}"
    return _sanitize_classifier_label(str(raw_label or "unknown-food"))


def _int_or_none(value: Any) -> int | None:
    """Return an int when conversion is possible.

    Args:
        value: Candidate scalar.

    Returns:
        Integer value or None.
    """
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _sanitize_label(value: str) -> str:
    """Normalize a detector label for safe user review.

    Args:
        value: Raw detector label.

    Returns:
        Bounded label string.
    """
    normalized = value.strip().replace("_", " ")
    if not normalized:
        return "unknown food"
    return normalized[:120]


def _sanitize_classifier_label(value: str) -> str:
    """Normalize a classifier label while preserving class_en punctuation.

    Args:
        value: Raw classifier label.

    Returns:
        Bounded classifier label.
    """
    normalized = value.strip()
    if not normalized:
        return "unknown-food"
    return normalized[:120]


def _box_from_xyxy(
    coordinate: Any,
    *,
    confidence: float,
    label: str,
    model_label: str,
) -> BoundingBox:
    """Build a BoundingBox from an Ultralytics xyxy coordinate row.

    Args:
        coordinate: Sequence-like ``[x1, y1, x2, y2]``.
        confidence: Detection confidence.
        label: Detection label.
        model_label: Detector model label.

    Returns:
        Bounding box metadata.

    Raises:
        VisionPreprocessingError: If coordinates are malformed.
    """
    values = _as_list(coordinate)
    if len(values) < XYXY_COORDINATE_COUNT:
        raise VisionPreprocessingError("Food YOLO box is missing coordinates.")
    x_min, y_min, x_max, y_max = (round(float(values[i])) for i in range(4))
    if x_min >= x_max or y_min >= y_max:
        raise VisionPreprocessingError("Food YOLO box has invalid coordinate order.")
    return BoundingBox(
        x=x_min,
        y=y_min,
        width=x_max - x_min,
        height=y_max - y_min,
        confidence=confidence,
        label=label,
        model=model_label,
    )
