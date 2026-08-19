# validator match-goal rules

1. Judge the work against the user prompt, not only "a query ran".
2. Fail if SQL is an unfiltered fact scan, wraps date keys in a function, or omits `TOP`/`FETCH`/`LIMIT` on the final SELECT.
3. Fail if the grain, filters, or metrics do not match the ask (wrong table, extra years, missing ranking).
4. On first visit, fail if the fetch does not answer the prompt. On second visit, fail if the draft payload misses a required mode artifact.
5. On first visit failure, set `result` to `fail` with a gap checklist. The pipeline returns work to `data-gatherer` with your message. Do not pass leniently when SQL or fetch is wrong.
6. On second visit failure, set `result` to `fail`; the pipeline returns work to `result-builder`.
7. On failure, list specific mismatches. Do not rewrite the SQL or report yourself.
