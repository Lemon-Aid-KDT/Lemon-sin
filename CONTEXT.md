# Lemon Aid AI Agent Context

This context defines the project language used when deepening the Lemon Aid AI Agent
runtime. It keeps LLM wording, deterministic coaching, and safety decisions distinct.

## Language

**LLM Completion**:
A local or self-hosted model response after runtime transport, response shape, and
empty-text handling have been normalized.
_Avoid_: raw model response, provider output

**Deterministic Coaching**:
Health-management guidance produced from confirmed input, reference ranges, memory
summaries, and rule-based agent logic without relying on model judgment.
_Avoid_: AI diagnosis, model decision

**Safety Envelope**:
The user-facing output package after medical wording, grounding, trace, and fallback
checks have been applied.
_Avoid_: safety filter, guardrail wrapper

**Chat Turn**:
One authenticated user message plus recent conversation, context, policy, knowledge
selection, and response generation result.
_Avoid_: chat request, prompt call

**App Intake**:
The route-owned request data after user ownership, consent context, payload shape, and
internal agent dataclasses are aligned.
_Avoid_: raw payload, input dict

## Example Dialogue

Developer: "This Chat Turn needs an LLM Completion, but deterministic coaching remains
the authority if the model is unavailable."

Reviewer: "Good. The Safety Envelope must still be applied before the response leaves
the AI Agent runtime."

Developer: "The App Intake will reject malformed payloads before DailyHealthAgent sees
them, so the agent can focus on deterministic coaching."
