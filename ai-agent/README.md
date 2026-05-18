# Lemon Aid AI Agent

Server-side AI Agent workspace for turning reliable food and supplement intake
data into health-management coaching.

This package is intentionally separate from the current app code. It defines the
first production-oriented boundaries for:

- intake normalization from OCR results
- nutrition and supplement aggregation
- recent health-trend interpretation
- personalized coaching
- safety filtering and action approval

## Product Direction

Lemon Aid is not a general chatbot. The Agent system must combine structured
intake data, official nutrition references, user context, and safety policy.
The LLM is an assistant inside the workflow, not the sole source of health
judgment.

The MVP excludes blood glucose and CGM integration, but the schemas keep a
generic `health_trends` input so glucose-like trend signals can be added later
without redesigning the Agent interface.

## Runtime Shape

```text
OCR food/supplement result
-> Intake Agent
-> Nutrition Engine
-> Health Trend Engine
-> Personalization Agent
-> Coaching Agent
-> Safety Guard
-> Action Agent
-> user preview and approval
```

## Local Verification

```powershell
python -m unittest discover ai-agent/tests
```

