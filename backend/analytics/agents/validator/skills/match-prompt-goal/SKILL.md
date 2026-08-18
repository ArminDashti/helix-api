---
name: Match prompt goal
description: Check fetched SQL and packaged artifacts against the original user prompt
---

# Match prompt goal

1. Read the user prompt, mode, SQL, row preview, and draft payload.
2. Ask: does this implementation answer that prompt?
3. Pass when SELECT-only SQL and artifacts match the asked table, filters, grain, and mode.
4. Fail with a short checklist of gaps. Do not invent a new query here.
