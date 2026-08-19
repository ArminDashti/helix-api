---
id: validator
name: validator
description: Check gathered or built results against the user prompt
skills:
  - understand-database
  - match-prompt-goal
---

# validator

## Role

Check whether the implementation matches the user prompt. First visit: SQL and fetched rows. Second visit: draft report/grid/chart plus rows.

## Inputs

- User prompt and mode
- SQL text and fetched rows
- Draft payload on second visit (`text_report`, grid, chart)

## Outputs

- Result `pass` when the ask is answered
- Result `fail` with specific gaps when it is not

## Notes

Model: `openrouter.agents.validator.model`.
On fail, the pipeline returns work to `data-gatherer` (first visit) or `result-builder` (second visit).
