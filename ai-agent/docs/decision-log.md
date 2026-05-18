# Decision Log

## 2026-05-18: AI Agent direction

- Work happens on branch `changmin-aiagent`.
- New Agent work is isolated under `ai-agent/`.
- The MVP is treated as the minimum commercial product path, not a throwaway
  demo.
- Blood glucose and CGM integrations are excluded from MVP implementation.
- The Agent interface keeps a generic health trend input for future glucose,
  CGM, weight, activity, and score trends.
- External LLM APIs are not the preferred production path for sensitive health
  data. The architecture assumes server-operated/self-hosted LLM capability.
- OCR low-confidence handling is not the center of this work. The main problem
  is converting reliable OCR intake data into safe health-management coaching.
- Supplement suggestions are ingredient-level in MVP. Specific product
  recommendations are out of scope until legal, pharmacy, advertising, and
  conflict-of-interest review are complete.
- LLM output is not authoritative for health judgment. Official data,
  deterministic nutrition logic, user context, and Safety Guard policy remain
  authoritative.

