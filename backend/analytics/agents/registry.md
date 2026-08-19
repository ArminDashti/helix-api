# Agent registry

Pipeline order:

```text
guardian
  → data-gatherer
  → validator
  → result-builder
  → validator
  → publisher
      (validator fail → data-gatherer or result-builder, limited)
```

| # | Id | When to use |
|---|-----|-------------|
| 1 | `guardian` | Block dangerous prompts and check permission |
| 2 | `data-gatherer` | Cheap SELECT + fetch (row-capped) |
| 3 | `validator` | Does the fetch match the user prompt? |
| 4 | `result-builder` | Report from fetched rows |
| 5 | `validator` | Does the built result match the prompt? |
| 6 | `publisher` | Package UI payload |

**Models:** set per agent under `openrouter.agents.<id>.model` in `helix.config.yaml` (see `helix.config.example.yaml`). Never hardcode models in `AGENT.md`.
