# Agent registry

Pipeline order (not executed in this phase):

```text
task_validator
  → solution_strategist
  → technical_architect
  → code_builder
  → sql_guardian          (reject → code_builder)
  → implementation_auditor (reject → code_builder)
  → response_publisher
```

| # | Id | Display name | When to use |
|---|-----|--------------|-------------|
| 1 | `task_validator` | Task Validator | First gate: is the prompt + mode feasible for Helix? |
| 2 | `solution_strategist` | Solution Strategist | Non-technical solution narrative |
| 3 | `technical_architect` | Technical Architect | Technical blueprint for the builder |
| 4 | `code_builder` | Code Builder | Implement as sandbox Python |
| 5 | `sql_guardian` | SQL Guardian | Validate every SQL (SELECT-only, not heavy) |
| 6 | `implementation_auditor` | Implementation Auditor | Does the build match the architect plan? |
| 7 | `response_publisher` | Response Publisher | Package `{ text_report, echarts_option }` for the UI |

**Models:** set per agent under `openrouter.agents.<id>.model` in `helix.config.yaml` (see `helix.config.example.yaml`). Never hardcode models in `AGENT.md`.
