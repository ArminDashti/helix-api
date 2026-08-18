---
name: Package UI payload
description: Map fetched rows to mode, text_report, echarts_option, and grid
---

# Package UI payload

1. Read mode and the SQL fetch preview.
2. Write `text_report` from preview numbers when the mode needs a report.
3. Null unused fields. Do not invent values. The server builds grid and chart from the same rows.
