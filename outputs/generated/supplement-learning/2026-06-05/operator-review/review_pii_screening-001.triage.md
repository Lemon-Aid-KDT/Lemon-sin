# Supplement Operator Review Batch Triage

Schema: `supplement-operator-review-batch-triage-markdown-v1`

이 문서는 operator JSONL batch의 검토 우선순위만 표시합니다.
fixture id, 이미지 경로, source ref, bbox 좌표, OCR 원문, provider payload는 포함하지 않습니다.

## Batch

- Queue: `review_pii_screening`
- File: `review_pii_screening-001.jsonl`
- Rows: `50`
- Valid rows: `0`
- Blank rows: `50`
- Pending rows: `0`
- Invalid rows: `0`

## Priority Counts

- `p2_privacy_screening_required`: `50`

## Reason Counts

- `blank_decision`: `50`

## Row Hints

- row `1`: `p2_privacy_screening_required` (`blank_decision`)
- row `2`: `p2_privacy_screening_required` (`blank_decision`)
- row `3`: `p2_privacy_screening_required` (`blank_decision`)
- row `4`: `p2_privacy_screening_required` (`blank_decision`)
- row `5`: `p2_privacy_screening_required` (`blank_decision`)
- row `6`: `p2_privacy_screening_required` (`blank_decision`)
- row `7`: `p2_privacy_screening_required` (`blank_decision`)
- row `8`: `p2_privacy_screening_required` (`blank_decision`)
- row `9`: `p2_privacy_screening_required` (`blank_decision`)
- row `10`: `p2_privacy_screening_required` (`blank_decision`)
- row `11`: `p2_privacy_screening_required` (`blank_decision`)
- row `12`: `p2_privacy_screening_required` (`blank_decision`)
- row `13`: `p2_privacy_screening_required` (`blank_decision`)
- row `14`: `p2_privacy_screening_required` (`blank_decision`)
- row `15`: `p2_privacy_screening_required` (`blank_decision`)
- row `16`: `p2_privacy_screening_required` (`blank_decision`)
- row `17`: `p2_privacy_screening_required` (`blank_decision`)
- row `18`: `p2_privacy_screening_required` (`blank_decision`)
- row `19`: `p2_privacy_screening_required` (`blank_decision`)
- row `20`: `p2_privacy_screening_required` (`blank_decision`)
- row `21`: `p2_privacy_screening_required` (`blank_decision`)
- row `22`: `p2_privacy_screening_required` (`blank_decision`)
- row `23`: `p2_privacy_screening_required` (`blank_decision`)
- row `24`: `p2_privacy_screening_required` (`blank_decision`)
- row `25`: `p2_privacy_screening_required` (`blank_decision`)

## Next Steps

- `complete_blank_privacy_decisions`
- `run_batch_file_preflight_before_reconcile`
- `run_strict_pii_preflight_before_teacher_ocr`

## Rule

이 triage는 수동 검토 순서만 제안합니다. PII clearance, teacher OCR, YOLO dataset promotion, training은 별도 gate를 통과해야 합니다.
