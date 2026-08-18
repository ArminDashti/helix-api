---
name: Package payload
---
# Response builder rules

1. Honor mode strictly: null unused fields per the output contract.
2. Build `{ mode, text_report, echarts_option, grid }` from the SQL fetch only.
3. Do not invent figures that are not in the fetch preview.
4. Keep payload JSON-serializable for the frontend.
