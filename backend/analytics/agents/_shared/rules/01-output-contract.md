# Output contract

Honor the request `mode` exactly when packaging or planning outputs:

| Mode | `text_report` | `echarts_option` | UI |
|------|---------------|------------------|-----|
| `analysis` | Required | `null` | Text only |
| `chart` | `null` | Required | Chart only |
| `both` | Required (explains the chart/data) | Required | **Chart first**, explanation below |

Do not return both artifacts for `analysis` or `chart`. For `both`, explanation must refer to the chart/data shown.
