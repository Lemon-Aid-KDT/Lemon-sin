# Regression Evals

Regression evals protect existing scenario behavior after schemas, prompts, or
mock Agent outputs change.

Initial regression gates:

- same fixture produces same deterministic mock output
- `analysis` is never accepted as an Agent name
- generated logs omit forbidden raw fields

