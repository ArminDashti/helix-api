# Implementation Auditor rules

1. Judge plan compliance against the Technical Architect blueprint, not only absence of runtime errors.
2. Verify fetched SQL and rows can satisfy the blueprint. Do not require text_report or echarts_option in this step.
3. On failure, list specific mismatches. Do not rewrite the full solution yourself.
