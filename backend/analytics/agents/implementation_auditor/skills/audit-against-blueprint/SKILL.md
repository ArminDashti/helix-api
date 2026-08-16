---
name: Audit against blueprint
description: Checklist verification of the run versus the Technical Architect plan
---

# Audit against blueprint

1. Diff planned sources, transforms, and outputs vs what was fetched.
2. Confirm the SQL matches the mode's data need (report, chart, or grid).
3. Emit pass or fail with a short actionable checklist.
4. Do not fail because text_report or echarts_option are missing in this step; the server packages those from sql_fetch after a pass.
