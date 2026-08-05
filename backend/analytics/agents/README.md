# Helix agents

This directory holds the **agent army**: shared rules/skills/schema plus one folder per pipeline agent.

## Status

Agents are **arranged and configured** (Markdown + `helix.config.example.yaml` models). They are **not executed** yet — no orchestrator, OpenRouter calls, or sandbox runs in this phase.

## Layout

| Path | Purpose |
|------|---------|
| `_shared/rules/` | Army-wide policies (filename sort = priority) |
| `_shared/skills/` | Reusable playbooks (`SKILL.md`) |
| `_shared/schema/tables.md` | SQL allowlist + descriptions |
| `<agent_id>/AGENT.md` | Identity, role, skills list (no model — models live in config) |
| `<agent_id>/rules/` | Agent-specific rules |
| `<agent_id>/skills/` | Agent-specific skills |
| `registry.md` | Pipeline index |

## Adding an agent

1. Create `agents/<agent_id>/` with `AGENT.md`.
2. Add optional `rules/` and `skills/`.
3. Register in `registry.md`.
4. Add `openrouter.agents.<agent_id>.model` in `helix.config.example.yaml` / your local `helix.config.yaml`.

See [registry.md](registry.md) for the current seven-agent pipeline.
