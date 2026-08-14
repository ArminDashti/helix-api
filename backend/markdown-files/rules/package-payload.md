---
name: Package payload
---
# Response Publisher rules

1. Honor mode strictly: null out unused fields (`analysis` → no chart; `chart` → no text).
2. For `both`, include both fields; UI will render chart then explanation.
3. Do not invent new analysis — only package approved artifacts.
4. Keep payload JSON-serializable for the frontend.
