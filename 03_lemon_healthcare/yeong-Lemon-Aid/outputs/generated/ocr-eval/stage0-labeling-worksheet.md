# Stage 0 Ground-Truth Labeling Worksheet (비타민 9 fixture)

> 본 워크시트는 plan §I Stage 0의 ground-truth 라벨링을 책상 위 참조 자료로 정리한 것이다. 9개 비타민 fixture (비타민A 3 + 비타민B 3 + 멀티비타민 3)에 대해 사용자가 V2/V3 expected snapshot 파일을 채워 넣을 때 사용한다. PaddleOCR auto-seed 결과는 대부분 garbage(`Once Daily`, `SUGGESTED USE:`, `nutricost` 등)이므로 ingredient 정보는 **이미지를 직접 보고** 라벨링한다.

---

## 1. Fixture 인벤토리 (9 case)

이미지 경로 root: `/Users/yeong/99_me/00_github/03_lemon_healthcare/yeong-Lemon-Aid/data/supplement_images/private_workspace/stage0_naver/images/`

라벨링 파일 root: `backend/Nutrition-backend/tests/fixtures/supplement_labels/expected/`

| # | fixture_id | category | image filename | PaddleOCR text (chars) | 라벨링 파일 (V2/V3) |
| --- | --- | --- | --- | ---: | --- |
| 1 | `naver-live-0013` | 멀티비타민 | `naver-live-0013.jpg` | 326 | `naver-live-0013.snapshot_v{2,3}.json` |
| 2 | `naver-live-0015` | 비타민A | `naver-live-0015.jpg` | 718 | `naver-live-0015.snapshot_v{2,3}.json` |
| 3 | `naver-live-0016` | 비타민B | `naver-live-0016.jpg` | ❌ ocrerror | `naver-live-0016.snapshot_v{2,3}.json` (이미지 품질 확인 권장) |
| 4 | `naver-live-0029` | 멀티비타민 | `naver-live-0029.jpg` | 2764 (가장 풍부) | `naver-live-0029.snapshot_v{2,3}.json` |
| 5 | `naver-live-0031` | 비타민A | `naver-live-0031.jpg` | 566 | `naver-live-0031.snapshot_v{2,3}.json` |
| 6 | `naver-live-0032` | 비타민B | `naver-live-0032.jpg` | 181 (정보 적음) | `naver-live-0032.snapshot_v{2,3}.json` |
| 7 | `naver-live-0045` | 멀티비타민 | `naver-live-0045.jpg` | 202 | `naver-live-0045.snapshot_v{2,3}.json` |
| 8 | `naver-live-0047` | 비타민A | `naver-live-0047.webp` | 197 | `naver-live-0047.snapshot_v{2,3}.json` |
| 9 | `naver-live-0048` | 비타민B | `naver-live-0048.jpg` | 128 (정보 가장 적음) | `naver-live-0048.snapshot_v{2,3}.json` |

> 라벨링 우선 권장 순서: `naver-live-0029` (text 많음, 멀티비타민) → `naver-live-0015` → `naver-live-0031` → `naver-live-0013` → `naver-live-0045` → 비타민A 0047 / 비타민B 0032 / 비타민B 0048 → `naver-live-0016` (ocrerror, image 자체가 영양 정보가 부족할 가능성).

---

## 2. 비타민 표준 영양소 코드 (`data/nutrition_reference/nutrient/nutrient_codes.json` 기준)

| 영양소 (한글) | 영양소 (영문) | nutrient_code | 기본 단위 | 일반적 라벨 표기 |
| --- | --- | --- | --- | --- |
| 비타민 A | Vitamin A | `vitamin_a_ug` | ug RAE | `ug`, `mcg`, `μg`, 또는 `IU`(구단위) |
| 비타민 B1 (티아민) | Thiamin | `vitamin_b1_mg` | mg | `mg` |
| 비타민 B2 (리보플라빈) | Riboflavin | `vitamin_b2_mg` | mg | `mg` |
| 비타민 B3 (니아신) | Niacin | `vitamin_b3_mg` | mg | `mg NE`, `mg` |
| 비타민 B5 (판토텐산) | Pantothenic Acid | `vitamin_b5_mg` | mg | `mg` |
| 비타민 B6 (피리독신) | Pyridoxine | `vitamin_b6_mg` | mg | `mg` |
| 비타민 B7 (비오틴) | Biotin | `vitamin_b7_ug` | ug | `ug`, `mcg` |
| 비타민 B9 (엽산) | Folate | `vitamin_b9_ug` | ug DFE | `ug`, `mcg` |
| 비타민 B12 (코발라민) | Cobalamin | `vitamin_b12_ug` | ug | `ug`, `mcg` |
| 비타민 C | Vitamin C | `vitamin_c_mg` | mg | `mg` |
| 비타민 D | Vitamin D | `vitamin_d_ug` | ug | `ug`, `mcg`, `IU` |
| 비타민 E | Vitamin E | `vitamin_e_mg` | mg α-TE | `mg`, `IU` |
| 비타민 K | Vitamin K | `vitamin_k_ug` | ug | `ug`, `mcg` |

> 단위 환산 (라벨이 IU로 표기된 경우):
> - 비타민 A: 1 IU ≈ 0.3 μg RAE
> - 비타민 D: 1 IU = 0.025 μg (40 IU = 1 μg)
> - 비타민 E: 1 IU ≈ 0.67 mg α-TE (천연), 0.45 mg (합성)

---

## 3. 멀티비타민 라벨에서 자주 등장하는 미네랄 코드

| 영양소 (한글) | nutrient_code (예) | 기본 단위 |
| --- | --- | --- |
| 칼슘 | `calcium_mg` | mg |
| 마그네슘 | `magnesium_mg` | mg |
| 철분 | `iron_mg` | mg |
| 아연 | `zinc_mg` | mg |
| 셀레늄 | `selenium_ug` | ug |
| 망간 | `manganese_mg` | mg |
| 구리 | `copper_mg` 또는 `copper_ug` | mg 또는 ug |
| 크롬 | `chromium_ug` | ug |
| 몰리브덴 | `molybdenum_ug` | ug |
| 요오드 | `iodine_ug` | ug |

> 실제 코드는 `data/nutrition_reference/nutrient/nutrient_codes.json`에서 확인. nutrient_code_candidates에 적을 때 `match_method: "alias_exact"`(라벨에 한글/영어로 정확히 일치) 또는 `"alias_fuzzy"`(부분 일치), `confidence: 1.0`(사람 검수)로 기록한다.

---

## 4. 라벨링 표준 (V2 vs V3 차이 요약)

### V2 (`SupplementParsedSnapshotV2`)
- `product`: `{product_name, manufacturer, barcode_text, barcode_format}`
- `ingredient_candidates[]` 각 항목:
  ```json
  {
    "display_name": "비타민 A",
    "normalized_name": "비타민 a",
    "nutrient_code_candidates": [
      {"nutrient_code": "vitamin_a_ug", "match_method": "alias_exact", "confidence": 1.0}
    ],
    "amount": 750.0,
    "unit": "ug",
    "daily_amount": 750.0,
    "confidence": 1.0,
    "source": "human_label",
    "evidence_refs": []
  }
  ```

### V3 (`SupplementParsedSnapshotV3`)
- `source`에 `parser_schema_version: "supplement-parser-output-v2"`, `raw_model_response_stored: false` 추가
- `product`: `{product_name, manufacturer, barcode_candidates: [], evidence_refs: []}` (V2의 barcode_text/format 대체)
- `ingredients[]` (V2 `ingredient_candidates`와 동일 구조 + `daily_unit`)
- `precautions[]` 항목에 `severity: "unknown"` 추가
- `evidence_spans[]` 별도 (라벨링 시 비워두면 됨)

### V2/V3 공통 작성 필드
- `requires_user_confirmation: true` (그대로)
- `source.raw_image_stored / raw_ocr_text_stored / raw_provider_payload_stored`: 모두 `false` (필수)
- `serving`: `serving_size_text` (예: "1일 1정"), `serving_amount: 1`, `serving_unit: "정"`, `daily_servings: 1`
- `intake_method.text`: 라벨에 적힌 섭취 안내 그대로
- `intake_method.structured.frequency`: `"daily"` / `"weekly"` / `"as_needed"` / `"unknown"`
- `precautions[]`: 임산부/약물 복용자 주의 등
- `functional_claims[]`: 라벨에 적힌 기능성 문구. **의료 표현 금지** (`치료`, `진단`, `처방` 등)
- `low_confidence_fields: []` (사람 라벨이므로 비움)
- `warnings`: 기존 `ground_truth_pending_human_review`는 라벨링 후 제거 가능, `category:...`, `labels:...`는 유지

---

## 5. 라벨링 워크플로 (1 fixture 기준)

1. 이미지 열기 (Finder/Preview 등 OS 도구):
   ```
   open "/Users/yeong/99_me/00_github/03_lemon_healthcare/yeong-Lemon-Aid/data/supplement_images/private_workspace/stage0_naver/images/naver-live-0029.jpg"
   ```
2. V2 파일 열기:
   ```
   backend/Nutrition-backend/tests/fixtures/supplement_labels/expected/naver-live-0029.snapshot_v2.json
   ```
3. `product.product_name`, `product.manufacturer` 채우기. 바코드가 라벨에 있으면 `barcode_text`도.
4. `serving` 4개 필드 채우기.
5. `ingredient_candidates[]`에 라벨의 영양·기능정보 표를 한 줄씩 옮기기.
   - `display_name`: 한글/영문 그대로
   - `normalized_name`: 소문자 + 공백 정리 (예: "비타민 A" → "비타민 a")
   - `amount`, `unit`: 라벨 그대로
   - `daily_amount`: `amount × daily_servings` (대부분 같음)
   - `nutrient_code_candidates`: 위 표 코드 사용
   - `confidence: 1.0`, `source: "human_label"`
6. `intake_method.text`, `precautions`, `functional_claims` 채우기.
7. `warnings`에서 `ground_truth_pending_human_review` 제거 (또는 그대로 두고 verifier가 제거 가능).
8. V3 파일도 같은 정보로 채우기 (구조 차이만 주의).
9. schema 검증:
   ```bash
   cd /Users/yeong/99_me/00_github/03_lemon_healthcare/yeong-Lemon-Aid/backend
   .venv/bin/python -c "
   import json, sys
   from pathlib import Path
   sys.path.insert(0, 'Nutrition-backend')
   from src.models.schemas.supplement_snapshot import SupplementParsedSnapshotV2, SupplementParsedSnapshotV3
   d = Path('Nutrition-backend/tests/fixtures/supplement_labels/expected')
   SupplementParsedSnapshotV2.model_validate(json.loads((d/'naver-live-0029.snapshot_v2.json').read_text()))
   SupplementParsedSnapshotV3.model_validate(json.loads((d/'naver-live-0029.snapshot_v3.json').read_text()))
   print('ok')
   "
   ```

---

## 6. 진행 추적 체크리스트

라벨링 완료한 fixture에 ✅ 마크. 9개 모두 마치면 task #32 (LLM parser wiring) + Stage 0 재실행으로 넘어간다.

- [ ] `naver-live-0029` (멀티비타민, text 가장 풍부) — V2 ✅ / V3 ✅
- [ ] `naver-live-0015` (비타민A) — V2 / V3
- [ ] `naver-live-0031` (비타민A) — V2 / V3
- [ ] `naver-live-0013` (멀티비타민) — V2 / V3
- [ ] `naver-live-0045` (멀티비타민) — V2 / V3
- [ ] `naver-live-0047` (비타민A, webp) — V2 / V3
- [ ] `naver-live-0032` (비타민B) — V2 / V3
- [ ] `naver-live-0048` (비타민B) — V2 / V3
- [ ] `naver-live-0016` (비타민B, ocrerror) — V2 / V3 (라벨이 부족하면 `warnings`에 `image_label_insufficient` 추가 후 skip 가능)

> 9개 모두 마치지 않아도 1개라도 채우면 task #32 wiring 후 첫 `ingredient_name_exact_rate` 측정 가능.

---

## 7. 자주 발생하는 문제

- **단위 표기**: PaddleOCR가 `μg`를 `ug`로 읽거나 `IU`를 `IU`로 잘 읽지만, `ug` ↔ `μg` 같은 표기는 라벨링 시 한 가지로 통일한다 (예: `ug`).
- **여러 nutrient_code 후보**: 한 영양소가 여러 형태(예: 비타민 D2 vs D3)인 경우 가장 가까운 단일 코드를 first, 나머지를 list 후속 항목으로.
- **nutrient_code 모름**: `nutrient_code_candidates: []`로 두고 `warnings`에 `nutrient_code_unmatched:<display_name>` 추가.
- **라벨이 사진에 안 나오는 부분**: `null` 또는 빈 list로 두고 `warnings`에 `field_not_visible:<field>` 추가.
- **bracket/괄호**: `display_name`에 `(50% NE)` 같은 보조 표기는 그대로 유지. `normalized_name`에서는 제거.

---

## 8. 라벨링 완료 후 다음 단계

1. 9개 (또는 일부) 라벨링 완료 + schema 검증 통과
2. 사용자가 알려주면 task #32 (LLM parser wiring을 `collect_supplement_ocr_observations.py`에 추가) 본격 시작
3. Stage 0 재실행 (prepare → collect with LLM → build_three_tier_manifest → evaluate_ocr_three_tier)
4. `ingredient_name_exact_rate` 첫 실측값 산출
5. Stage 1 (L1-E 영문 anchor, L1-H PaddleOCR 전처리, L1-G domain correction) 효과 정량 비교

이 워크시트 자체는 `outputs/generated/ocr-eval/stage0-labeling-worksheet.md`에 commit 가능 (재현성 + 사용자 reference).
