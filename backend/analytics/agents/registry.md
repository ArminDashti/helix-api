# Agent registry

Pipeline order:

```text
task_validator
  → solution_strategist
  → technical_architect
  → code_builder
  → sql
  → implementation_auditor
  → response_publisher
```

| # | Id | Display name | When to use |
|---|-----|--------------|-------------|
| 1 | `task_validator` | Task Validator | First gate: is the prompt + mode feasible for Helix? |
| 2 | `solution_strategist` | Solution Strategist | Non-technical solution narrative |
| 3 | `technical_architect` | Technical Architect | Technical blueprint for the builder |
| 4 | `code_builder` | Code Builder | Implement as sandbox Python |
| 5 | `sql` | SQL | Fetch warehouse data and enforce SQL validation rules |
| 6 | `implementation_auditor` | Implementation Auditor | Was the task done based on the Technical Architect blueprint? |
| 7 | `response_publisher` | Response Publisher | Package `{ text_report, echarts_option, grid }` for the UI |

**Models:** set per agent under `openrouter.agents.<id>.model` in `helix.config.yaml` (see `helix.config.example.yaml`). Never hardcode models in `AGENT.md`.
