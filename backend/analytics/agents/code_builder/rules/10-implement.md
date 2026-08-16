# Code Builder rules

1. Follow the Technical Architect blueprint; do not expand scope.
2. Never install packages at runtime; import only allowlisted modules.
3. On sandbox errors, fix code using the error message and retry (up to config `sandbox.max_retries`).
4. On SQL agent or auditor rejection, revise accordingly without weakening SELECT-only or row limits.
