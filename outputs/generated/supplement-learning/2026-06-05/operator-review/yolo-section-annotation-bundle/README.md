# Supplement YOLO Section Annotation Bundle

Open `annotation-index.html` locally to inspect materialized detail-page images.

Annotate section boxes for supplement label regions only:
`product_identity`, `supplement_facts`, `ingredient_amounts`, `intake_method`,
`precautions`, `other_ingredients`, `functional_claims`.

Use normalized `xywh` values in source-image coordinate space:

```json
{"label":"supplement_facts","x_center":0.5,"y_center":0.5,"width":0.4,"height":0.3}
```

All coordinate values must be between 0 and 1. Draw multiple boxes when a
section is visually split across separated regions.

## Section Guide

- `product_identity`: Product name, brand, front label, or title block.
- `supplement_facts`: The full Supplement Facts or Nutrition Facts panel.
- `ingredient_amounts`: Ingredient rows, amounts, units, and daily-value table cells.
- `intake_method`: Suggested use, directions, dosage schedule, or serving instructions.
- `precautions`: Warnings, cautions, allergy notes, contraindications, or consult-doctor text.
- `other_ingredients`: Other ingredients, inactive ingredients, capsule shell, or additives.
- `functional_claims`: Structure/function claims, benefits, marketing claim text, or certifications.

Do not copy raw OCR text, provider payloads, local paths, product folder names,
or image bytes into `annotation.todo.jsonl`.

After human review, accepted rows can be passed to
`promote_supplement_yolo_annotation_template.py`, then
`materialize_supplement_section_yolo_dataset.py`.
