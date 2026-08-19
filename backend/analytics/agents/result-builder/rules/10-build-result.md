# result-builder build-result rules

1. Honor mode strictly: null unused fields per the output contract.
2. Write `text_report` from the SQL fetch preview only.
3. Do not invent figures that are not in the fetch preview.
4. Optional `chart_type` hint when mode needs a chart. Server builds grid and chart.
