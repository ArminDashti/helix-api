# publisher package-payload rules

1. Honor mode strictly: null unused fields per the output contract.
2. Confirm `text_report`, grid, and chart requirements against the fetch and draft payload.
3. Keep payload JSON-serializable for the frontend.
4. On packaging error, return `fail`/`failed` with a concrete reason.
