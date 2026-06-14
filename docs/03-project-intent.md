# 03. Project Intent

> Status: team-wide summary
> Detailed source: [Nutrition-docs/03-project-intent.md](./Nutrition-docs/03-project-intent.md)

## Intent

The project should be framed as an AI healthcare and health-management service, not as a generic big-data project. Data and AI are implementation tools; the user-facing value is safer, more personalized health guidance.

## Differentiation Direction

- Connect supplement, food, activity, and chat information into one health context.
- Prioritize Korean users, Korean food context, Korean/English supplement labels, and KDRIs-based nutrition references.
- Keep chronic-condition and regulated-document features behind explicit review gates.
- Avoid claims that imply diagnosis, prescription, cure, or guaranteed treatment effect.

## Part-Level Intent

| Part | Intent |
|------|--------|
| Nutrition | Convert supplement/health/nutrition inputs into structured, consent-safe health-management insights. |
| Food | Identify meal context and food categories so nutrition gaps are not inferred from supplements alone. |
| Chat | Explain results and collect follow-up context without crossing into medical advice. |
| Integration | Ensure all parts share one product language, one CI/PR process, and one demo flow. |

## Decision Rule

When a feature can be described in multiple ways, choose the wording that is:

1. health-management oriented,
2. non-diagnostic,
3. evidence-aware,
4. testable in the current codebase,
5. consistent with team ownership folders.

## Related Documents

- Project overview: [01-project-overview.md](./01-project-overview.md)
- Technical map: [06-tech-stack.md](./06-tech-stack.md)
- Compliance guardrails: [10-compliance-checklist.md](./10-compliance-checklist.md)
- Nutrition detailed strategy: [Nutrition-docs/03-project-intent.md](./Nutrition-docs/03-project-intent.md)
