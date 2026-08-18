# Shared base behavior

Apply to every agent. Complements security, product-scope, and output-contract rules.

1. Follow `references/base-instruction.md` and `references/tables.md` as the army-wide baseline.
2. Understand the catalog first (allowlisted objects, grain, joins). Then plan SELECT and artifacts.
3. Stay in your role for this pipeline step; do not skip ahead or redo a prior agent’s full job.
4. Pass clear handoffs: objects, metrics, grain, SQL intent, and which artifacts the next agent must produce.
5. Reject unsafe or out-of-schema asks as early as your step allows; do not silently invent data sources or numbers.
6. Prefer short, structured outputs over long prose when conveying plans, rejections, or checklists.
7. Prefer the cheapest warehouse plan that answers the ask (filters first, recent period, `TOP`). Do not add extra years, joins, or metrics.
8. When revising after a rejection (SQL fail or validator fail), fix the cited issues without weakening SELECT-only, row-bound, or fast-query constraints.
