---
name: Implement sandbox script
description: Generate and repair sandbox Python until it runs without errors
---

# Implement sandbox script

1. Emit a complete script that produces mode-correct artifacts.
2. Keep all SQL SELECT-only and row-bounded for the SQL agent.
3. If the sandbox returns an error, patch the script using that feedback only (error loop — do not re-judge analytics quality).
