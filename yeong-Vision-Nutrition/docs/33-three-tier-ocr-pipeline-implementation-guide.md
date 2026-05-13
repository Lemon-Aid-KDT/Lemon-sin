# 33. 3-Tier OCR 파이프라인 상세 구현 가이드

> **문서 정보**
> 버전: v1.0 | 작성일: 2026-05-13 | 상태: 운영 표준 채택 (구현 가이드) | 작성자: yeong-tech

---

## 0. 한 줄 요약

영양제 라벨 분석을 ① **YOLO ROI 보조** ② **Google Cloud Vision Primary OCR(`DOCUMENT_TEXT_DETECTION`)** ③ **Ollama 멀티모달 Fallback + Cross-check 검수** 의 3-tier 파이프라인으로 운영한다. 각 단계는 책임이 명확히 분리되어 있으며, 어느 하나가 실패하거나 게이트 통과 전 비활성 상태여도 다른 단계가 graceful 하게 단독 동작한다.

---

## 1. 채택 결정 + 사용자 의도

### 1.1 사용자 요구

- **Tier 1**: YOLO 로 라벨 영역만 검출(분류·의료 판단 X) → OCR 정확도 향상을 위한 입력 전처리
- **Tier 2**: Google Cloud Vision 으로 텍스트 추출 — 한국어 + 영양제 라벨 정확도 우선
- **Tier 3**: Ollama 멀티모달 LLM(Qwen 3.5 + Gemma 4 vision 보조)
  - *Fallback*: Google Vision 신뢰도가 낮을 때 라벨 이미지를 직접 멀티모달에 보내 텍스트 재추출
  - *Cross-check 검수*: Google Vision 출력이 시각 콘텐츠와 일치하는지 샘플링으로 교차 검증

### 1.2 선택 근거

- [docs/27](./27-ot-s2b-google-vision-ocr-review-plan.md) — Google Vision 의 한글 OCR 정확도가 시장에서 가장 안정적
- [docs/30 §1](./30-multimodal-yolo-experiment-plan.md) — `OCR-first + optional ROI + optional vision assist` 결론
- 웹 검색 결과(2026-05 기준):
  - **Qwen 3.5 9B** ([`qwen3.5:9b`](https://ollama.com/library/qwen3.5)) 은 docs/12 §3 에서 이미 1차 텍스트 파서 기본 모델로 채택. Tier 3 의 *텍스트 구조화* 단계도 동일 모델로 통일해 운영 모델 수를 최소화한다.
  - 멀티모달(이미지 → 텍스트) 호출은 Qwen 3.5 의 텍스트 한계를 보완하기 위해 **Gemma 4 vision 보조 채널** 을 함께 사용한다 — Gemma 4 9B 는 2026-04-02 출시되어 로컬 vision + tool calling + structured output 을 제공([Best Ollama Models 2026](https://mljourney.com/best-ollama-models-in-2026-a-practical-guide-by-use-case/)).
  - **Gemma 4 9B (vision + tool calling)** 가 2026-04-02 출시되어 로컬 structured output 운영안에 권장 ([Ollama Vision Search](https://ollama.com/search?c=vision))
  - **Gemma 3 27B** 는 DocVQA 85.6 점으로 문서 작업에서 LLaVA 와 폐쇄형 VLM 다수를 능가 ([Ollama Models Cheat Sheet 2026](https://computingforgeeks.com/ollama-models-cheat-sheet/))
  - Google Cloud Vision 의 **`DOCUMENT_TEXT_DETECTION`** 은 밀집 텍스트(영양제 라벨)에 적합하며 모든 지원 언어를 자동 감지 ([Cloud Vision OCR](https://cloud.google.com/vision/docs/ocr), [Dense document text detection](https://cloud.google.com/vision/docs/fulltext-annotations), [OCR language support](https://docs.cloud.google.com/vision/docs/languages))

### 1.3 기존 문서와의 관계

| 문서 | 관계 |
| --- | --- |
| [docs/25](./25-ocr-text-supplement-analysis-plan.md) | OCR text → structured parse 흐름. 본 가이드는 그 흐름의 *입력* 을 책임진다. |
| [docs/26](./26-ot-s2-ocr-provider-adapter-implementation-plan.md) | `OCRAdapter` 인터페이스 표준. 본 가이드는 그 표준을 그대로 채택한다. |
| [docs/27](./27-ot-s2b-google-vision-ocr-review-plan.md) | Google Vision 리뷰. 본 가이드 §4 에서 `DOCUMENT_TEXT_DETECTION` 으로 결정을 갱신한다. |
| [docs/28](./28-ollama-local-llm-connection-implementation-plan.md) | Ollama 텍스트 파서 연결. 본 가이드 §5 의 Pydantic structured output 단계에서 재사용. |
| [docs/30](./30-multimodal-yolo-experiment-plan.md) | 실험 결론. 본 가이드는 그 결론을 **운영 표준** 으로 격상. |
| [docs/32](./32-paddleocr-local-fallback-plan.md) | PaddleOCR 비용 최적화 폴백. 본 가이드 §5.2 라우팅 트리에 후순위 폴백으로 포함. |
| [docs/31](./31-backend-feature-specifications.md) | 현행 기능 명세. 본 가이드 채택 후 §4 OCR·§5 LLM·§6 Vision 섹션 링크 갱신. |

---

## 2. End-to-End 파이프라인

```mermaid
sequenceDiagram
    participant M as Flutter Mobile
    participant API as FastAPI /supplements/analyze
    participant SVC as supplement_image_analysis
    participant YOLO as YoloLabelDetector (Tier 1)
    participant GV as GoogleVisionOCRAdapter (Tier 2)
    participant OLV as OllamaVisionAssist (Tier 3)
    participant PARSE as OllamaSupplementParser
    participant DB as PostgreSQL

    M->>API: POST multipart 이미지
    API->>SVC: orchestrate
    SVC->>YOLO: detect_label_region(image)
    alt ROI 검출 성공
        YOLO-->>SVC: BoundingBox
        SVC->>SVC: crop_image_to_bounding_box()
    else 미검출
        SVC->>SVC: 원본 이미지 사용
    end
    SVC->>GV: extract_text(cropped_or_original)
    GV-->>SVC: OCRResult(confidence)
    alt confidence >= 0.85
        SVC->>PARSE: parse_supplement_ocr_text(text)
    else confidence < 0.85
        SVC->>OLV: analyze_multimodal(prompt, image)
        OLV-->>SVC: OCRResult (visible text)
        SVC->>PARSE: parse_supplement_ocr_text(fallback_text)
    end
    opt cross-check 샘플 (N%)
        SVC->>OLV: verify_against_ocr(ocr_text, image)
        OLV-->>SVC: similarity score
    end
    PARSE-->>SVC: SupplementStructuredParseResult
    SVC->>DB: save preview (requires_confirmation)
    SVC-->>API: response (low_confidence_fields 포함)
    API-->>M: 사용자 확인 화면
```

응답 시간 목표: P95 < 6초 ([docs/06 §3.4](./06-tech-stack.md) 의 Redis 캐싱과 함께).

---

## 3. Tier 1 — YOLO ROI 보조 (Image Preprocessing)

### 3.1 책임
**영양제 라벨이 차지하는 픽셀 영역만** `BoundingBox` 로 반환. 분류·성분 추출·의료 판단 출력 절대 금지(CLAUDE.md Rule 1).

### 3.2 사용 모델

| 단계 | 모델 | 메모리 | 정확도 |
| --- | --- | --- | --- |
| Phase 3 게이트 #2 통과 직후 | `yolov8n.pt` (COCO pretrained, ~6MB) | ~50MB 추론 메모리 | mAP50 ~37(범용 객체), 영양제 라벨 IoU ~0.7~0.8 추정 |
| Phase 4 fine-tuning 이후 | `yolov8n-supplement.pt` (자체 학습 가중치) | 동일 | mAP50 0.85+ 목표 |

웹 검색 ([Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8/), [Predict Mode](https://docs.ultralytics.com/modes/predict/)) 결과를 docs/30 §3 에서 이미 검증 완료.

### 3.3 검출 클래스 화이트리스트

`backend/src/vision/taxonomy.py` 의 `VisionLabel` enum 만 허용:
- `SUPPLEMENT_BOTTLE`
- `SUPPLEMENT_LABEL`
- `BLISTER_PACK`

모델 출력의 의료 클래스(예: `pill_label`, `prescription_label`)는 alias 매핑에서 제외. 별칭은 `VISION_LABEL_ALIASES` 만 사용.

### 3.4 출력

- `BoundingBox(x, y, width, height, confidence)`
- ROI 우선순위(`VISION_ROI_LABEL_PRIORITY`): `SUPPLEMENT_LABEL` > `SUPPLEMENT_BOTTLE` > `BLISTER_PACK`
- 미검출 시: `None` 반환 → Tier 2 가 원본 이미지를 입력으로 사용 (graceful "ROI 옵션 비활성" — fallback 패턴이 아니라 옵션 단계 스킵)

### 3.5 데이터셋 전략

- Phase 3 게이트 #2 통과 직후: pretrained `yolov8n.pt` 그대로 사용. 영양제 라벨이 일반 "bottle" / "rectangular object" 검출과 호환되므로 zero-shot 운영 가능
- 자체 데이터셋 수집 (Phase 3 후반):
  - 영양제 라벨 사진 100~200장 수동 라벨링 (CVAT / Roboflow)
  - AI Hub 음식 이미지 데이터셋 ([docs/09 §4.1](./09-data-catalog.md)) 보조 학습 (배경 다양성)
  - 학습 결과 `yolov8n-supplement.pt` 를 `backend/data/models/` 에 보관, `vision_classifier_model` 환경 변수로 교체

### 3.6 라이선스 — Ultralytics AGPL-3.0

Ultralytics 는 AGPL-3.0 또는 Enterprise 라이선스. 발주처 인수인계 시점 ([docs/dev-guides/25](./dev-guides/25-handover-checklist.md)) 라이선스 영향 검토 필수. AGPL 의 *network use* 조항이 SaaS 운영에 미치는 영향을 docs/15 §3 의 게이트 #2 산출물에 포함.

### 3.7 활성화 조건

본 단계가 동작하려면 모두 동시 충족:
1. [docs/17 §8](./17-image-collection-consent-plan.md) 게이트 #2 통과
2. `Settings.enable_vision_classifier=True`
3. `pip install ".[vision]"` (docs/06 §2.3 vision extras 설치)

게이트 미통과 시 `vision/yolo.py` 가 `VisionError` 를 발생시키므로 호출처는 `try/except` 로 옵션 비활성 처리.

---

## 4. Tier 2 — Google Cloud Vision Primary OCR

### 4.1 책임
Tier 1 이 잘라낸 라벨 영역(또는 원본)에서 **텍스트와 신뢰도** 만 추출. 의미 추론·구조화는 다음 단계(`OllamaSupplementParser`)가 담당.

### 4.2 API 선택 — `DOCUMENT_TEXT_DETECTION`

docs/27 의 `TEXT_DETECTION`/`DOCUMENT_TEXT_DETECTION` 결정을 본 문서에서 갱신:

| 기능 | TEXT_DETECTION | DOCUMENT_TEXT_DETECTION ★ |
| --- | --- | --- |
| 적합 사례 | 일반 사진 안의 텍스트 | 밀집 텍스트(영양제 라벨·약 봉지·스캔 문서) |
| 언어 자동 감지 | 부분 집합 | 전체 지원 언어(한국어 포함) |
| 페이지·블록 단위 신뢰도 | 단어 단위만 | 페이지·블록·단어 모두 |
| 우선순위 | — | 두 옵션 동시 요청 시 자동 우선 |

근거: [Cloud Vision OCR docs](https://cloud.google.com/vision/docs/ocr), [Dense document text detection tutorial](https://cloud.google.com/vision/docs/fulltext-annotations).

### 4.3 입력 / 출력

- 입력: `OCRImageInput(image_bytes, mime_type, width, height, label_region: BoundingBox | None)` — `label_region` 이 있으면 Tier 1 에서 이미 크롭된 이미지
- 최대 크기: `Settings.supplement_image_max_bytes`(5MB), `supplement_image_max_pixels`(12M px)
- 출력: `OCRResult(text, provider="google_vision_document", confidence)`
- 신뢰도 계산: 페이지·블록·단어 평균을 가중치 [0.3, 0.5, 0.2] 로 합산하여 `[0.0, 1.0]` 범위로 정규화

### 4.4 인증 + 운영

- Service Account JSON 을 `GOOGLE_APPLICATION_CREDENTIALS` 환경 변수로 주입
- production 환경: `validate_production_security` 에서 `google_application_credentials` 비어 있으면 `ValueError`
- 비밀 관리: GitHub Secrets(개발 CI), NCP KMS(운영)
- 비용: 월 1,000건 무료 + 1,000건당 $1.5 ([docs/32 §1.2](./32-paddleocr-local-fallback-plan.md) 비용 시뮬레이션 인용)

### 4.5 한국어 처리

`DOCUMENT_TEXT_DETECTION` 의 자동 감지는 한국어를 포함한 모든 지원 언어를 대상으로 함 ([OCR language support](https://docs.cloud.google.com/vision/docs/languages)). 명시적 `language_hints` 는 한국어 라벨 정확도를 *낮출 수 있어* 사용하지 않음.

### 4.6 활성화 조건

본 단계는 게이트 없음(기본 운영). 단:
1. 외부 송출 동의 ([docs/17 §3 동의 매트릭스](./17-image-collection-consent-plan.md) 1번 분석용 임시 처리) 필요
2. EXIF·GPS·파일명 식별 정보 제거 ([docs/17 §4.1](./17-image-collection-consent-plan.md))
3. 응답 후 원본 이미지 즉시 삭제 (`Settings.image_retention_days=0` 기본)

---

## 5. Tier 3 — Ollama 멀티모달 Fallback + Cross-check 검수

### 5.1 책임
두 가지 모드로 동작:
- **Fallback 모드**: Tier 2 의 신뢰도가 임계값(0.85) 미만이면 라벨 이미지를 직접 멀티모달에 보내 *visible text* 만 재추출
- **Cross-check 검수 모드**: Tier 2 결과를 받아 동일 이미지의 시각 콘텐츠와 비교, 유사도 임계값(0.80) 미만이면 사용자 확인 화면으로 escalation

### 5.2 라우팅 트리(우선순위 통합)

[docs/32 §4.2](./32-paddleocr-local-fallback-plan.md) 의 폴백 체인과 통합:

```
Tier 1: YOLO ROI 검출
        ├─ 검출 성공  → 이미지 크롭
        └─ 미검출     → 원본 사용

Tier 2: Google Vision DOCUMENT_TEXT_DETECTION
        ├─ confidence >= 0.85 → 텍스트 채택
        │                       (옵션) cross-check 샘플링 → 불일치 시 escalation
        └─ confidence <  0.85 → Tier 3 Fallback 진입

Tier 3: Ollama 멀티모달 (Gemma 4 vision 보조 + Qwen 3.5 텍스트 구조화)
        ├─ confidence >= local_ocr_confidence_threshold(0.75) → 텍스트 채택
        └─ 미달 → Tier 4 진입

Tier 4 (옵션): PaddleOCR (docs/32, 무료 quota 보호 또는 폐쇄망)
        └─ 미달 → Tier 5

Tier 5 (옵션): CLOVA OCR (기본 OFF, 비용)
        └─ 모두 실패 → 사용자 확인 화면 (수동 텍스트 입력)
```

### 5.3 권장 모델 — Qwen 3.5 + Gemma 4 vision 이중 채널

Tier 3 는 두 책임을 분리해 운영한다.

| 역할 | 모델 | Ollama 태그 | 메모리(M4 Pro 24GB) | 비고 |
| --- | --- | --- | --- | --- |
| **이미지 → 텍스트 (멀티모달 추출)** ⭐ | Gemma 4 9B vision | `gemma4:9b` | ~9GB | 2026-04-02 출시. vision + tool calling + structured output. docs/12 §3 가 이미 `gemma4:e4b` 로 채택. |
| **텍스트 구조화 (Pydantic JSON)** ⭐ | Qwen 3.5 9B | `qwen3.5:9b` | ~9GB | docs/12 §3 1차 기본 텍스트 파서. 본 단계에서도 동일 모델 재사용 → 메모리 상주 모델 1개로 통일 가능(Ollama hot-swap 시 두 모델 모두 캐시). |
| 보강(선택) | Gemma 3 27B | `gemma3:27b` | ~27GB(M4 Pro 권장 X) | DocVQA 85.6, 사내 GPU 서버 또는 발주처 인프라 전용. |

권장 운영 방식:

1. **이미지 입력**은 `ollama_vision_model=gemma4:9b` 또는 docs/12 의 기본값 `gemma4:e4b` 로 호출 → visible text 만 추출
2. 추출된 텍스트는 **Qwen 3.5 9B**(docs/12 §3 와 동일)에 다시 보내 `SupplementStructuredParseResult` 로 구조화
3. 두 모델 모두 로컬 Ollama 에서 실행되며, 식별 가능 환자 정보 외부 송출 없음(docs/12 §2)

운영자는 `ollama_vision_model` (이미지 → 텍스트)과 `ollama_model` (텍스트 → JSON) 두 환경 변수를 분리해 설정. Qwen 3.5 의 vision 변종(`qwen3.5-vl:*` 등)이 Ollama 라이브러리에 정식 등록되면 그 시점에 `gemma4:9b` 와 교체 가능 — 환경 변수 한 줄만 변경하면 됨(Adapter 패턴).

> 📌 **결정**: 본 가이드는 docs/12 §3 의 Qwen 3.5 텍스트 + Gemma 4 vision 정책을 그대로 따른다. 별도의 Qwen-VL/Qwen2.5-VL 라인은 도입하지 않는다.

### 5.4 시스템 프롬프트 (재사용)

`backend/src/llm/ollama_vision.py` 의 `OLLAMA_VISION_ASSIST_SYSTEM_PROMPT` 를 그대로 재사용:

```
You are a local supplement label OCR fallback component.
Extract only text fragments that are visibly present in the image.
Do not infer ingredients, amounts, dosage, health effects, risks, or product facts
from outside knowledge. Do not provide medical or nutrition advice. If text is not
visible, return an empty list or null. Return only JSON matching the supplied schema.
```

본 프롬프트는 CLAUDE.md Rule 1(의료 판단 출력 금지) + docs/17 §7(의료기기법 회피) 의 핵심 안전장치.

### 5.5 두 모드의 상세

#### 5.5.1 Fallback 모드

- 트리거: `enable_multimodal_fallback=True` AND Tier 2 confidence < 0.85
- 입력: Tier 1 크롭된 이미지(또는 원본) + 시스템 프롬프트
- Ollama Chat API 의 `images` 배열에 base64 인코딩된 이미지 전달 ([Ollama Vision docs](https://ollama.com/blog/multimodal-models))
- 출력: `OCRResult(text, provider="ollama_vision_assist", confidence)` — 신뢰도는 모델이 응답한 라인별 점수 평균

#### 5.5.2 Cross-check 검수 모드

- 트리거: `enable_multimodal_verification=True` AND 확률 `multimodal_verification_sample_rate`(기본 5%) 추첨 통과
- 입력: 이미지 + Tier 2 의 텍스트
- 비교 방식: 멀티모달에 동일 이미지를 보내 텍스트를 추출하고 두 결과의 character-level Levenshtein 거리(또는 token recall)로 유사도 계산
- 임계값: `multimodal_verification_threshold`(기본 0.80) 미만 시 결과를 *requires_confirmation* 상태로 표시, 사용자에게 수동 검토 유도

### 5.6 활성화 조건

본 단계가 동작하려면:
1. [docs/17 §8](./17-image-collection-consent-plan.md) 게이트 #1 통과
2. `Settings.enable_multimodal_llm=True`
3. 모드별 추가 플래그: `enable_multimodal_fallback` 또는 `enable_multimodal_verification`
4. Ollama 로컬 호스트(`127.0.0.1`/`localhost`/`::1`) 만 허용 (docs/12 §2 환자 정보 외부 송출 금지)

---

## 6. 코드 변경 범위(파일별)

본 가이드 채택 후 후속 PR 에서 다음 변경을 단계적으로 적용한다.

### 6.1 `backend/src/config.py`

기존 게이트 플래그(docs/17 §9) 아래에 신규 필드 4개:

```python
# 3-Tier OCR 파이프라인 운영 플래그 (docs/33 §5)
enable_multimodal_fallback: bool = Field(
    default=False,
    description="Google Vision 저신뢰 시 Ollama 멀티모달 재추출. docs/33 §5.5.1.",
)
enable_multimodal_verification: bool = Field(
    default=False,
    description="Cross-check 샘플링 검수 활성화. docs/33 §5.5.2.",
)
multimodal_verification_sample_rate: float = Field(default=0.05, ge=0.0, le=1.0)
multimodal_verification_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
google_vision_feature: Literal["DOCUMENT_TEXT_DETECTION", "TEXT_DETECTION"] = "DOCUMENT_TEXT_DETECTION"
```

`validate_production_security` 가드:
- `enable_multimodal_fallback=True` 면 `enable_multimodal_llm=True` 강제
- `enable_multimodal_verification=True` 면 동일하게 `enable_multimodal_llm=True` 강제 + sample_rate 가 `(0, 1]` 범위 검증

### 6.2 신규 `backend/src/ocr/providers/google_vision.py`

`GoogleVisionOCRAdapter(OCRAdapter)`:
- `extract_text(image: OCRImageInput) -> OCRResult` 구현
- 내부에서 `google.cloud.vision_v1.ImageAnnotatorAsyncClient` 사용
- 요청 feature 는 `Settings.google_vision_feature` 에서 가져옴
- 응답의 `full_text_annotation` 에서 페이지·블록·단어 평균 신뢰도 계산
- Service Account JSON 부재 시 `OCRError` 즉시 발생

### 6.3 `backend/src/services/supplement_image_analysis.py`

신규 헬퍼:

```python
async def _run_three_tier_ocr(
    settings: Settings,
    yolo: VisionAdapter | None,
    google_vision: OCRAdapter,
    ollama_vision: OCRAdapter | None,
    paddle: OCRAdapter | None,
    clova: OCRAdapter | None,
    image: OCRImageInput,
) -> OCRResult:
    """Run YOLO ROI → Google Vision → optional Ollama fallback chain.

    See docs/33 §5.2 routing tree.
    """
```

기존 `_run_ocr_chain` (docs/32 §5.5) 가 있다면 그것과 통합. 단일 진입점만 유지.

Cross-check 로직은 별도 헬퍼:

```python
async def _maybe_cross_check(
    settings: Settings,
    ollama_vision: OCRAdapter,
    image: OCRImageInput,
    primary_text: str,
) -> CrossCheckOutcome:
    """Optional verification when verification flag + sample-rate match."""
```

### 6.4 `backend/src/vision/yolo.py`

현재 fail-closed scaffold (`enable_vision_classifier=False` 면 즉시 `VisionError`). 활성화 후 동작:
- `detect_label_region()` 가 검출 실패 시 `VisionError` 대신 `None` 반환 옵션을 추가
- `UltralyticsYoloRunner` lazy-load (`import` 가 `try/except`)
- `detect_regions()` 결과 중 화이트리스트 클래스만 통과
- 최우선 ROI 한 개를 `BoundingBox` 로 반환

### 6.5 `backend/src/llm/ollama_vision.py`

기존 `OllamaVisionAssist` 에 추가:

```python
async def verify_against_ocr(
    self,
    ocr_text: str,
    image: OCRImageInput,
) -> VerificationOutcome:
    """Re-extract visible text and compare to OCR text by Levenshtein recall."""
```

### 6.6 `backend/.env.example`

3-Tier 운영 플래그 4종 + `GOOGLE_VISION_FEATURE` 라인 추가. production validator 경고를 한 줄 주석으로 안내.

### 6.7 `backend/pyproject.toml`

기존 `[project.optional-dependencies] vision` 그룹에 `google-cloud-vision>=3.7` 이 포함되어 있는지 확인. 미포함 시 base requirements 로 이동(기본 운영에 필요).

### 6.8 `docs/31-backend-feature-specifications.md`

채택 후:
- §4.1 `OCR Adapter ABC` 항목 끝에 "운영 파이프라인은 [docs/33](./33-three-tier-ocr-pipeline-implementation-guide.md) 참조" 한 줄 추가
- §5.2 `Ollama Vision Assist` 항목에 fallback / cross-check 모드 구분 한 줄 추가
- §6.2 `YOLO 검출기` 항목에 ROI-only 운영 원칙과 docs/33 §3 링크 추가

---

## 7. 테스트 전략

### 7.1 단위 테스트

- `tests/unit/ocr/providers/test_google_vision.py`:
  - mock `ImageAnnotatorAsyncClient` 응답으로 페이지·블록·단어 신뢰도 가중 평균 검증
  - 빈 응답·인증 실패 시 `OCRError`
  - `DOCUMENT_TEXT_DETECTION` 요청 feature 가 정확히 전달되는지 확인
- `tests/unit/vision/test_yolo.py`:
  - mock `YoloRegionRunner` → ROI 출력 → `BoundingBox` 변환 + 화이트리스트 필터 검증
  - 미검출 시 `None` 반환 (graceful 옵션 비활성)
- `tests/unit/llm/test_ollama_vision_verify.py`:
  - `verify_against_ocr` 의 Levenshtein recall 계산 정확도
  - 응답 JSON 검증 실패 시 재시도 1회

### 7.2 통합 테스트 — `tests/integration/test_three_tier_ocr_pipeline.py`

| 시나리오 | 입력 | 기대 결과 |
| --- | --- | --- |
| A | ROI 성공 + Google 신뢰도 0.92 | Google 결과 반환, Ollama 미호출 |
| B | ROI 실패 + Google 0.60 + Ollama 0.78 | Ollama fallback 결과 반환 |
| C | Google 0.95 + cross-check 통과(유사도 0.92) | Google 결과 반환, 추가 escalation 없음 |
| D | Google 0.95 + cross-check 실패(유사도 0.50) | `requires_confirmation` 플래그 부착, 사용자 확인 화면 |
| E | 모든 게이트 OFF | Google 단독 동작 (기존 동작 보장) |
| F | Google 0.5 + Ollama 0.5 + Paddle 0.6 + CLOVA OFF | Paddle 결과 반환 (docs/32 §4.2 와 통합) |
| G | 모든 폴백 실패 | 사용자 수동 텍스트 입력 화면 escalation |

### 7.3 라벨 100장 PoC

세 구성을 비교한 후 게이트 #1·#2 산출물에 첨부:

| 구성 | 측정 지표 | 비고 |
| --- | --- | --- |
| Google 단독 | 성분명 F1, 함량 F1, 단위 정규화율, P95 latency | baseline |
| Google + YOLO ROI | 동일 | ROI 가 정확도를 얼마나 끌어올리는지 |
| Google + YOLO + Ollama fallback | 동일 + Ollama 호출 비율 | 저신뢰 케이스 회복률 |

목표:
- 성분명 F1 ≥ 0.85
- 함량 F1 ≥ 0.80
- 단위 정규화 성공률 ≥ 0.90
- P95 OCR latency ≤ 6초

---

## 8. 컴플라이언스 평가

| 항목 | Tier 1 (YOLO) | Tier 2 (Google Vision) | Tier 3 (Ollama 멀티모달) |
| --- | --- | --- | --- |
| 환자 정보 외부 전송 | 없음(로컬) | **있음** | 없음(로컬, `127.0.0.1` 강제) |
| docs/17 §3 동의 카테고리 | 1번 분석용 임시 | 1번 분석용 임시 + 외부 송출 동의 | 1번 분석용 임시 |
| docs/17 §7 의료기기법 회피 | ROI metadata 만 출력 | 텍스트만 출력 | system prompt 로 의료 판단 금지 |
| docs/15 §3 규제 검토 | 라이선스(AGPL-3.0) 검토 | 외부 API 약관 | 로컬 처리로 면제 |
| EXIF / GPS 제거 (§4.1) | 적용 | 적용 | 적용 |
| `image_retention_days=0` 기본 | 적용 | 적용 | 적용 |

발주처 리뷰 게이트 매핑:
- 게이트 #1 — Tier 3 활성화 ([docs/17 §8](./17-image-collection-consent-plan.md))
- 게이트 #2 — Tier 1 활성화 + Ultralytics 라이선스 검토
- Tier 2 는 별도 게이트 없이 외부 송출 동의로 운영

---

## 9. 운영 모니터링

### 9.1 Golden Signals 확장

[dev-guides/26-operations-manual.md](./dev-guides/26-operations-manual.md) 에 추가:

| 지표 | 목표 | 임계 알람 |
| --- | --- | --- |
| OCR P95 latency | < 6초 | > 8초 |
| Google Vision 무료 quota 소진율 | < 80% / 월 | 80% 도달 시 알람 |
| YOLO ROI 검출 성공률 | > 90% | < 80% |
| Ollama fallback 진입률 | < 20% | > 30% (Google Vision 또는 YOLO 회귀 의심) |
| Cross-check 불일치율 | < 5% | > 10% |
| 사용자 수동 입력 escalation 비율 | < 5% | > 10% |

### 9.2 Datadog/Grafana 대시보드

`backend/src/services/supplement_image_analysis.py` 에 metric emit 추가:
- `ocr.tier.{1,2,3}.duration_ms`
- `ocr.tier.{1,2,3}.success_total`
- `ocr.tier.{1,2,3}.failure_total`
- `ocr.fallback.entered_total{from="tier2"}`
- `ocr.crosscheck.mismatch_total`

---

## 10. 도입 일정 (단일 개발자 기준)

| Day | 작업 | 산출물 |
| --- | --- | --- |
| 1 | `GoogleVisionOCRAdapter` 구현 + 단위 테스트 | google_vision.py + 5건 테스트 |
| 2 | Settings 4종 + `.env.example` + production validator | config.py 변경 |
| 3 | YOLO 실제 추론 연결(`UltralyticsYoloRunner` 활성) + ROI crop 통합 | yolo.py + ultralytics_runner.py |
| 4 | Ollama 멀티모달 fallback + verification 통합 + `_run_three_tier_ocr` | supplement_image_analysis.py + ollama_vision.py |
| 5 | 라벨 100장 PoC + 정확도 리포트 | docs/33 부록 또는 별도 PoC 노트 |
| 6 | 발주처 리뷰 게이트 #1·#2 산출물 제출 | 리포트 + 라이선스 검토 |
| 7 | docs/31·12·27 후속 갱신 + README 의 OCR 섹션 보강 | 문서 PR |

총 약 1주.

---

## 11. 발주처 게이트 매핑 요약

| 게이트 | 시점 | 대상 | 본 가이드 매핑 |
| --- | --- | --- | --- |
| 게이트 #1 | Phase 2 후반 | Ollama 멀티모달 활성 | Tier 3 fallback/verification |
| 게이트 #2 | Phase 3 초반 | YOLO 추론 활성 + AGPL 검토 | Tier 1 |
| 게이트 #3 | Phase 4 이후 | 학습 적재(pgvector) | 본 가이드 범위 외 ([docs/17 §8](./17-image-collection-consent-plan.md)) |

게이트 #1·#2 산출물에 §7.3 의 PoC 결과를 포함하여 발주처 컴플라이언스 담당 + PM 공동 리뷰.

---

## 12. 변경 이력

| 날짜 | 변경 내용 | 작성자 |
| --- | --- | --- |
| 2026-05-13 | 최초 작성. docs/30 실험 결론을 3-tier 운영 표준으로 격상. Tier 별 책임·라우팅 트리·코드 변경 범위·테스트 시나리오 7건·일정 1주 정의. | yeong-tech |

## 13. 관련 문서

- [docs/06-tech-stack.md](./06-tech-stack.md) §2.3 — vision extras
- [docs/09-data-catalog.md](./09-data-catalog.md) §4.1·§5.1 — AI Hub, Google Vision
- [docs/11-detailed-feature-implementation-plan.md](./11-detailed-feature-implementation-plan.md) §745 — OCR 정확도 리스크
- [docs/12-local-llm-ollama-migration.md](./12-local-llm-ollama-migration.md) §3 — Ollama 모델 운영안
- [docs/15-regulated-feature-feasibility-and-compliance-plan.md](./15-regulated-feature-feasibility-and-compliance-plan.md) §3 — 라이선스·규제 검토
- [docs/17-image-collection-consent-plan.md](./17-image-collection-consent-plan.md) §3·§7·§8·§9 — 동의 매트릭스·게이트
- [docs/25-ocr-text-supplement-analysis-plan.md](./25-ocr-text-supplement-analysis-plan.md) — OCR text → structured parse
- [docs/26-ot-s2-ocr-provider-adapter-implementation-plan.md](./26-ot-s2-ocr-provider-adapter-implementation-plan.md) — OCR adapter 인터페이스
- [docs/27-ot-s2b-google-vision-ocr-review-plan.md](./27-ot-s2b-google-vision-ocr-review-plan.md) — Google Vision 리뷰
- [docs/28-ollama-local-llm-connection-implementation-plan.md](./28-ollama-local-llm-connection-implementation-plan.md) — Ollama 텍스트 파서
- [docs/30-multimodal-yolo-experiment-plan.md](./30-multimodal-yolo-experiment-plan.md) — 본 가이드의 사상적 기반
- [docs/31-backend-feature-specifications.md](./31-backend-feature-specifications.md) §4·§5·§6 — 현행 기능 명세
- [docs/32-paddleocr-local-fallback-plan.md](./32-paddleocr-local-fallback-plan.md) — Tier 4 PaddleOCR
- [dev-guides/26-operations-manual.md](./dev-guides/26-operations-manual.md) — 모니터링 절차

외부 참조:
- [Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8/)
- [Ultralytics Object Detection](https://docs.ultralytics.com/tasks/detect/)
- [Cloud Vision OCR](https://cloud.google.com/vision/docs/ocr)
- [Cloud Vision Dense Document Text Detection](https://cloud.google.com/vision/docs/fulltext-annotations)
- [Cloud Vision Language Support](https://docs.cloud.google.com/vision/docs/languages)
- [Ollama Multimodal Models](https://ollama.com/blog/multimodal-models)
- [Ollama qwen3.5](https://ollama.com/library/qwen3.5)
- [Ollama gemma4](https://ollama.com/library/gemma4)
- [Ollama Vision Search](https://ollama.com/search?c=vision)
- [Best Ollama Models in 2026](https://mljourney.com/best-ollama-models-in-2026-a-practical-guide-by-use-case/)
- [Ollama Models Cheat Sheet 2026](https://computingforgeeks.com/ollama-models-cheat-sheet/)
