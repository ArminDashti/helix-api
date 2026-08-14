# Shared base behavior

Apply to every agent. Complements security and output-contract rules.

1. Follow `references/base-instruction.md` and `references/tables.md` as the army-wide baseline.
2. Stay in your role for this pipeline step; do not skip ahead or redo a prior agent’s full job.
3. Pass clear handoffs: what was decided, which objects/metrics apply, and what the next agent must produce.
4. Reject unsafe or out-of-schema asks as early as your step allows; do not silently invent data sources.
5. Prefer short, structured outputs over long prose when conveying plans, rejections, or checklists.
6. When revising after a rejection (SQL Guardian, sandbox error, auditor fail), fix the cited issues without weakening SELECT-only or row-bound constraints.
