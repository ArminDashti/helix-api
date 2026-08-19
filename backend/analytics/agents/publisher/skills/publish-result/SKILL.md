---
name: publish-result
description: Final check and handoff for UI payload packaging
---

# Publish result

1. Read mode, language, `sql_fetch`, and `text_report`.
2. Confirm the draft matches mode requirements.
3. Set `result` to `done` when ready for server packaging, or `fail` with gaps.
4. The server emits `{ text_report, grid, echarts_option }` from the same fetch.
