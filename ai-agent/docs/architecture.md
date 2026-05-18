# AI Agent Architecture

## Goal

The Agent system converts accurate food and supplement intake data into
practical health-management guidance:

- what to reduce in meals
- what to add through food first
- which nutrient ingredients may be considered if food intake is difficult
- which reminders or daily missions can help the user follow through

It must not diagnose, treat, prescribe, or guarantee outcomes.

## Components

### Intake Agent

Normalizes OCR and structured app inputs into canonical daily intake records.
It should preserve source metadata and user approval state, but this first
workspace assumes OCR has already provided accurate product, ingredient, and
amount data.

### Nutrition Engine

Deterministically aggregates food and supplement nutrients, compares them with
reference targets and upper limits, and produces nutrient-level findings.

### Health Trend Engine

Summarizes recent health signals such as meal-score trends, weight trend,
activity trend, or future glucose trend fields. Glucose and CGM are excluded
from MVP implementation, but trend input is deliberately generic.

### Personalization Agent

Turns user profile, goals, chronic conditions, medications, and trend summaries
into coaching constraints. It does not create clinical rules by itself.

### Coaching Agent

Creates user-facing guidance from nutrition findings and personalization
constraints. It must follow this priority:

1. Reduce excessive intake patterns.
2. Suggest food-first improvements.
3. Suggest ingredient-level supplement consideration only when food intake may
   be difficult.
4. Propose reminders or small daily missions when useful.

### Safety Guard

Blocks diagnosis, prescription, treatment claims, medication guarantees, product
promotion, and direct medication recommendations. It also ensures supplement
recommendations remain ingredient-level in the MVP.

### Action Agent

Prepares actions such as supplement reminders or daily missions. It never
executes actions without explicit user approval.

## LLM Strategy

The product direction is server-operated AI. External LLM API keys should not be
the default path for sensitive health information. The code should keep a model
provider boundary so a self-hosted model can be used behind the Agent layer.

The deterministic engines remain authoritative for nutrition math, trend
aggregation, and policy decisions.

