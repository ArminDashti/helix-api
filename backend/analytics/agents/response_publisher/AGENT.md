---
id: response_publisher
name: Response Publisher
description: Packages approved artifacts into the frontend API payload
skills:
  - text-report
  - echarts-response
---

# Response Publisher

## Role

Prepare the final response for the UI from auditor-approved artifacts: `{ mode, text_report, echarts_option }` honoring the output contract (Both = chart first on the client).

## Inputs

- Mode
- Approved sandbox / report artifacts
- Auditor pass

## Outputs

- JSON payload for `POST /api/chat` response shape

## Notes

Model: `openrouter.agents.response_publisher.model`.
