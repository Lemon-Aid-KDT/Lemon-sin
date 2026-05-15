# Lemon Aid Agent Harness

This harness keeps Agent development testable before the app has a complete
backend and mobile integration.

For a Korean plain-language explanation, see [EXPLANATION.md](./EXPLANATION.md).

It follows the Lemon Aid baseline:

- `analysis` is a deterministic pipeline, not an Agent.
- The only Agents are `personalization`, `evaluation`, and `chat`.
- Agent behavior starts with deterministic mocks.
- Tools return previews first. They do not create reminders, calendar events,
  intake records, or database writes until a user approves them.
- Raw OCR, raw LLM output, and personal health source text must not be logged.

## Layout

```text
harness/
  config/       # Harness and safety policy
  fixtures/     # Users, analysis results, and agent memory snapshots
  scenarios/    # End-to-end Agent behavior scenarios
  evals/        # Capability, regression, and safety eval notes
  reports/      # Generated run reports, ignored by git except .gitkeep
  scripts/      # Dependency-free runner and report grader
```

The `*.yaml` files are JSON-compatible YAML. This keeps the runner
dependency-free while preserving the intended file names.

## Run

Run all scenarios:

```powershell
python harness\scripts\run_harness.py
```

Run one scenario:

```powershell
python harness\scripts\run_harness.py --scenario chat_tool_preview
```

Write a report:

```powershell
python harness\scripts\run_harness.py --write-report
```

Grade a saved JSON report:

```powershell
python harness\scripts\grade_report.py harness\reports\<report>.json
```

## Pass Criteria

A run passes only when all scenario checks pass:

- expected status matches
- required Agent steps ran
- required Tool preview appears
- blocked scenarios stop before Agent/tool side effects
- safety policy blocks forbidden medical or medication wording
- no forbidden log fields are present
