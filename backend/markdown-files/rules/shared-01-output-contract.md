# Output contract

Honor the request `mode` exactly when packaging or planning outputs. See also `references/base-instruction.md`.

| Mode | `text_report` | `echarts_option` | UI |
|------|---------------|------------------|-----|
| `analysis` | Required | `null` | Text only |
| `chart` | `null` | Required | Chart only |
| `both` | Required (explains the chart/data) | Required | **Chart first**, explanation below |

Rules:

1. Do not return both artifacts for `analysis` or `chart`.
2. For `both`, the explanation must refer to the chart/data shown — no unrelated narrative.
3. Payloads must be JSON-serializable for the frontend.
4. Upstream agents must plan only the artifacts required by the mode; Response Publisher nulls unused fields.
