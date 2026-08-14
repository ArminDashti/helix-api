---
name: Package UI payload
description: Map approved artifacts to mode, text_report, and echarts_option
---

# Package UI payload

1. Read mode and approved artifacts.
2. Build `{ "mode", "text_report", "echarts_option" }` per output contract.
3. Ensure unused fields are null when required by mode.
