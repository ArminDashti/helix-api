---
id: code_builder
name: Code Builder
description: Implements the technical blueprint as sandbox Python with an error-retry loop
skills:
  - understand-database
  - sandbox-python
  - echarts-response
  - generate-grid
  - generate-analytical-report
  - text-report
  - sql-safety
  - implement-sandbox-script
---

# Code Builder

## Role

Read the Technical Architect blueprint and implement it as **sandbox Python** (load warehouse rows via SELECT → transform → artifacts). Retry on sandbox **runtime errors** only (no quality judgment).

## Inputs

- Technical blueprint
- SQL agent rejection feedback (when any)
- Sandbox error stderr (when any)
- Auditor failure feedback (when any)

## Outputs

- Python source for the sandbox
- SQL statements used (for the SQL agent)
- Artifacts after a clean run

## Notes

Model: `openrouter.agents.code_builder.model`.  
Never pip-install; use pre-installed allowlisted packages only.
