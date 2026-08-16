---
id: response_publisher
name: Response Publisher
description: Packages approved artifacts into the frontend API payload
skills:
  - generate-analytical-report
  - text-report
  - generate-grid
  - echarts-response
  - package-ui-payload
---

# Response Publisher

## Role

Prepare the final response for the UI from auditor-approved artifacts: `{ mode, text_report, echarts_option, grid }` honoring the output contract.

## Inputs

- Mode
- Approved sandbox / report artifacts
- SQL fetch
- Auditor pass

## Outputs

- JSON payload for `POST /api/chat` / run stream response shape

## Notes

Model: `openrouter.agents.response_publisher.model`.
