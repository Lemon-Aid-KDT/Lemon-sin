# 10. Compliance Checklist

> Status: team-wide summary
> Detailed source: [Nutrition-docs/10-compliance-checklist.md](./Nutrition-docs/10-compliance-checklist.md)

## Legal Notice

This document is an engineering and collaboration checklist. It is not legal advice. Any production release involving healthcare, prescription, lab, or sensitive personal data needs legal and domain review.

## Common Prohibitions

- Do not provide diagnosis, prescription, treatment instructions, or disease confirmation.
- Do not recommend direct dose changes for medication or supplements as a definitive instruction.
- Do not imply guaranteed treatment, cure, or prevention.
- Do not expose raw health images, OCR text, personal identifiers, or sensitive health data without explicit consent and retention rules.
- Do not call external OCR/LLM providers for sensitive data unless the feature gate, user consent, and environment policy allow it.

## Required Output Style

Use health-management wording:

| Avoid | Prefer |
|------|--------|
| "You have disease X." | "This result may require professional review." |
| "Take more of ingredient X." | "Your intake appears below the reference range; consider reviewing this with a professional." |
| "Stop/change this medication." | "Medication changes must be confirmed by a clinician or pharmacist." |
| "This food cures fatigue." | "This food may help support nutrient intake related to fatigue management." |

## Cross-Part Gates

| Gate | Applies To | Required Before Activation |
|------|------------|----------------------------|
| External OCR | supplement images, food images, regulated documents | consent, environment flag, provider review |
| Local or external LLM | chat, supplement text parsing, explanation generation | prompt/output guardrails, no raw sensitive leakage |
| Regulated document intake | prescription, lab result, medical documents | intake-only contract, no diagnosis or dose-change output |
| Learning data storage | image/text embeddings, vector DB, model improvement | explicit learning consent, retention policy, deletion support |

## Related Documents

- Common project overview: [01-project-overview.md](./01-project-overview.md)
- Common product intent: [03-project-intent.md](./03-project-intent.md)
- Common tech stack: [06-tech-stack.md](./06-tech-stack.md)
- Nutrition detailed compliance checklist: [Nutrition-docs/10-compliance-checklist.md](./Nutrition-docs/10-compliance-checklist.md)
