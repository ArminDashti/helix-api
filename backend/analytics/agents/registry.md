# Agent registry

Pipeline order:

```text
guardian
  → sql_fetcher
  → response_builder
  → validator
      (fail → sql_fetcher, limited)
```

| # | Id | Display name | When to use |
|---|-----|--------------|-------------|
| 1 | `guardian` | Guardian | Block dangerous prompts and check permission |
| 2 | `sql_fetcher` | SQL fetcher | Cheap SELECT + fetch (row-capped) |
| 3 | `response_builder` | Response builder | Report / grid / chart from those rows |
| 4 | `validator` | Validator | Does the result match the user prompt? |

**Models:** set per agent under `openrouter.agents.<id>.model` in `helix.config.yaml` (see `helix.config.example.yaml`). Never hardcode models in `AGENT.md`.
