# Validator rules

1. Judge the work against the user prompt, not only “a query ran”.
2. Fail if SQL is an unfiltered fact scan, wraps `TarikhFaktor` in a function, or omits `TOP`/`FETCH` on the final SELECT.
3. Fail if the grain, filters, or metrics do not match the ask (wrong table, extra years, missing ranking).
4. Fail if the mode needs a report/grid/chart and the draft payload is missing that artifact.
5. On failure, list specific mismatches. Do not rewrite the SQL yourself.
