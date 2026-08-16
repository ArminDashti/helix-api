---
name: package-ui-payload
description: Map approved artifacts to mode, text_report, echarts_option, and grid
---

# Package UI payload

1. Read mode and approved artifacts plus SQL fetch.
2. Build `{ "mode", "text_report", "echarts_option", "grid" }` per the output contract.
3. Null unused fields. Do not invent values.
