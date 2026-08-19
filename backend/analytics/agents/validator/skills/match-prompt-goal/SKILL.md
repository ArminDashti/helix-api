---
name: match-prompt-goal
description: Check fetched SQL and packaged artifacts against the original user prompt
---

# Match prompt goal

1. Read the user prompt, mode, SQL, row preview, validator visit count, and draft payload (second visit).
2. Ask: does this implementation answer that prompt?

## First visit (after data-gatherer)

3. Pass only when SELECT-only SQL and fetch match the asked table, filters, grain, and metrics.
4. Fail with a short checklist of gaps (wrong table, missing filter, wrong grain, missing metric, unbounded scan).
5. Set `result` to `fail` when any gap exists. The pipeline sends your message to `data-gatherer` for SQL revision. Do not pass leniently.

## Second visit (after result-builder)

6. Pass when SQL, fetch, and draft payload match the prompt and mode.
7. Fail with gaps in the report or mode artifacts. The pipeline sends work to `result-builder`.

8. Do not invent a new query or rewrite the report here.
