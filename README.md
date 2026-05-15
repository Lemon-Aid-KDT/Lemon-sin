# Lemon Aid AI Agent Workspace

This worktree is for the `changmin-aiagent` branch.

## Purpose

- Keep AI Agent implementation planning separate from the general planning branch.
- Use `docs/implementation/` as the working area for Agent prerequisites, branch absorption notes, and implementation roadmap.
- Keep source planning guides in `docs/planning/guide/` as references.

## Agent Baseline

- The implementation baseline is `analysis algorithm + 3 Agents`.
- The three Agents are `personalization`, `evaluation`, and `chat`.
- OCR, meal recognition, supplement parsing, and nutrient calculation stay outside the Agent boundary as deterministic analysis pipelines.
- Agent implementation starts mock-first before connecting a real LLM provider.

## Key References

- `docs/implementation/README.md`
- `docs/planning/guide/06-ai-agents.md`
- `docs/planning/guide/09-team-workflow.md`
