---
name: Package payload
---
# Response Publisher rules

1. Honor mode strictly: null unused fields per the output contract.
2. Package `{ mode, text_report, echarts_option, grid }` from approved artifacts and SQL fetch only.
3. Do not invent new analysis — only package approved artifacts.
4. Keep payload JSON-serializable for the frontend.
