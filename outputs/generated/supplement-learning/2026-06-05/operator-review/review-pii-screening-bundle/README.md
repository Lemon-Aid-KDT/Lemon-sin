# Supplement PII Screening Review Bundle

Open `review-index.html` locally and inspect each materialized review image.

Edit `decisions.todo.jsonl` only after review. A row can be cleared only when
no face, name, contact detail, address, order detail, or other personal data is
visible. Do not copy raw label text or review text into the decision file.

## Decision Guide

- `cleared_no_personal_data`: Use only when no face, name, contact, address,
  order, or other personal data is visible.
- `contains_personal_data`: Use when any personal data is visible; teacher OCR
  transfer stays blocked.
- `needs_rescreen`: Use when the image is ambiguous, cropped, blurry, or needs
  another reviewer.
- `reject`: Use for unrelated, wrong type, unreadable, or unsafe images.

## Reason Codes

- `no_personal_data_visible`: Required for cleared rows.
- `face_visible`: A face or identifiable person is visible.
- `name_visible`: A personal name is visible.
- `contact_visible`: Phone, email, account id, or similar contact data is visible.
- `address_visible`: Address or delivery location is visible.
- `receipt_or_order_visible`: Receipt, order number, invoice, or shipping/order
  context is visible.
- `other_personal_data_visible`: Any other personal data is visible.
- `unreadable`: Image cannot be safely reviewed.
- `needs_manual_rescreen`: Second pass needed before any provider transfer.
- `wrong_image_type`: Not a supplement label/review image suitable for OCR benchmark work.

## Cleared Row Requirements

Rows with `decision=cleared_no_personal_data` must set all of these to `true`:

- `attest_local_screening_completed`
- `attest_no_personal_data_visible`
- `attest_no_raw_text_copied`
- `attest_teacher_ocr_transfer_allowed`

After completing decisions, run `apply_supplement_review_pii_screening_decisions.py`
against the original candidate manifest and the edited decision JSONL.
