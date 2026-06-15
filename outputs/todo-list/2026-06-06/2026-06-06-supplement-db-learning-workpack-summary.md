# 2026-06-06 - Supplement DB and learning workpack summary

## Summary

- 영양제 성분 카테고리 DB 검증 결과, `crawling-image` 기준 43개 카테고리가 모두 active DB category와 매칭된 상태를 확인했다.
- 영양제 브랜드/제품 자동 매핑 검증 결과, 387개 제품과 387개 제품-카테고리 매핑이 DB 기준으로 일치했다.
- 음식 taxonomy 적용 검증 결과, 팀원 food 분류 기반 `taxo59` catalog 59개와 nutrition row 59개가 active DB 기준으로 일치했다.
- PII screening, OCR ground truth, YOLO section bbox 검토는 자동 입력하지 않고 operator review gate로 유지했다.
- operator workpack에서 PII/YOLO 검토자가 실제로 봐야 하는 HTML visual index 안내가 누락처럼 보이던 문제를 개선했다.

## Verified DB State

| Area | Current result | Evidence artifact |
| --- | ---: | --- |
| Supplement category seed | 43 / 43 matched | `outputs/generated/supplement-learning/2026-06-05/operator-review/category-seed-db-verification-current.json` |
| Supplement brand products | 387 / 387 products matched | `outputs/generated/supplement-learning/2026-06-05/operator-review/brand-products-auto.db-verification.json` |
| Product-category mappings | 387 / 387 mappings matched | `outputs/generated/supplement-learning/2026-06-05/operator-review/brand-products-auto.db-verification.json` |
| Food catalog taxo59 | 59 / 59 active catalog rows | `outputs/generated/supplement-learning/2026-06-05/operator-review/food-taxo59-db-verification.json` |
| Food nutrition taxo59 | 59 / 59 active nutrition rows | `outputs/generated/supplement-learning/2026-06-05/operator-review/food-taxo59-db-verification.json` |

## Workpack Fix

### Problem

- PII review와 YOLO annotation workpack에 `Visual Review Contact Sheet: none`만 보여서, 검토자가 시각 자료가 없는 것으로 오해할 수 있었다.
- 실제 bundle에는 HTML 기반 visual index가 존재하므로, workpack Markdown과 summary JSON에 이를 명시해야 했다.

### Change

- `backend/scripts/build_supplement_operator_review_workpack.py`
  - workpack summary에 `visual_index_available`, `visual_index_file_name`, `visual_index_reviewable_row_count`, `visual_index_image_count`를 추가했다.
  - PII/YOLO workpack Markdown에 `## Visual Review Index` 섹션을 추가했다.
  - contact sheet가 없지만 visual index가 있는 경우, `Visual Review Index`를 사용하라고 안내하도록 수정했다.
  - YOLO bundle optional file key를 `label_studio_tasks_name` 기준으로 정리했다.
- `backend/Nutrition-backend/tests/unit/scripts/test_build_supplement_operator_review_workpack.py`
  - PII/YOLO visual index 안내, image count, Label Studio task file 노출 여부를 검증하도록 테스트를 추가했다.

## Regenerated Artifacts

| Artifact | Purpose |
| --- | --- |
| `outputs/generated/supplement-learning/2026-06-05/operator-review/workpack/summary.json` | Workpack-level visual index metadata |
| `outputs/generated/supplement-learning/2026-06-05/operator-review/workpack/review_pii_screening-001.md` | PII screening batch guide |
| `outputs/generated/supplement-learning/2026-06-05/operator-review/workpack/yolo_section_annotation-001.md` | YOLO section annotation batch guide |
| `outputs/generated/supplement-learning/2026-06-05/operator-review/operator-next-command-checklist.json` | Execution-state aware operator commands |
| `outputs/generated/supplement-learning/2026-06-05/operator-review/operator-next-command-checklist.md` | Human-readable command checklist |

## Current Human Gates

| Gate | Remaining work | Why blocked |
| --- | ---: | --- |
| Brand/product review | 388 rows | Operator must confirm product/manufacturer decisions |
| Review-image PII screening | 215 rows | Operator must classify whether review images can enter OCR benchmark work |
| YOLO section bbox annotation | 205 rows | Operator must draw/approve supplement section boxes |
| OCR benchmark and teacher OCR | blocked | Requires PII screening completion and explicit external OCR opt-in |
| YOLO dataset materialization | blocked | Requires section bbox annotation completion |
| PaddleOCR improvement loop | blocked | Requires ground truth and benchmark gate evidence |

## Validation

```bash
cd backend
.venv/bin/python -m pytest --no-cov Nutrition-backend/tests/unit/scripts/test_build_supplement_operator_review_workpack.py -q
.venv/bin/python -m pytest --no-cov Nutrition-backend/tests/unit/scripts/test_build_supplement_operator_review_workpack.py Nutrition-backend/tests/unit/scripts/test_build_supplement_operator_next_command_checklist.py Nutrition-backend/tests/unit/scripts/test_build_supplement_learning_completion_audit.py Nutrition-backend/tests/unit/scripts/test_build_supplement_operator_unblock_runbook.py -q
.venv/bin/python -m ruff check scripts/build_supplement_operator_review_workpack.py scripts/build_supplement_operator_next_command_checklist.py Nutrition-backend/tests/unit/scripts/test_build_supplement_operator_review_workpack.py Nutrition-backend/tests/unit/scripts/test_build_supplement_operator_next_command_checklist.py
```

- Focused workpack test: `5 passed`
- Operator regression tests: `30 passed`
- Ruff: passed
- `git diff --check`: passed

## Safety Notes

- DB verification and workpack regeneration did not perform DB writes.
- No external OCR provider call was performed during workpack regeneration.
- No LLM call or training job was started.
- Raw OCR text, provider payloads, local absolute paths, source image paths, owner hashes, secrets, and unreviewed visible text were not added to this report.
- PII decisions, OCR ground truth, and YOLO bbox labels remain human-review-only data.

## Next Step

1. Complete `brand_product_review:001` first, then rerun the batch preflight and reconcile flow.
2. Continue `review_pii_screening:001` using its HTML visual index, without copying visible text into notes.
3. Continue `yolo_section_annotation:001` using the annotation HTML index and Label Studio task file.
4. Only after the relevant gates pass, run teacher OCR comparison and PaddleOCR benchmark/training steps.

## Official References

- SQLAlchemy ORM Select: https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html
- PostgreSQL constraints: https://www.postgresql.org/docs/current/ddl-constraints.html
- Supabase Row Level Security: https://supabase.com/docs/guides/database/postgres/row-level-security
- Ultralytics detection dataset format: https://docs.ultralytics.com/datasets/detect/
- PaddleOCR OCR pipeline usage: https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html
- Google Cloud Vision OCR: https://cloud.google.com/vision/docs/ocr
- NAVER Cloud CLOVA OCR API: https://api.ncloud-docs.com/docs/en/ai-application-service-ocr
