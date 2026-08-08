"""Canonical agent pipeline metadata."""

AGENT_PIPELINE = [
    {
        "id": "task_validator",
        "name": "Task Validator",
        "description": "Validates the user prompt and mode",
    },
    {
        "id": "solution_strategist",
        "name": "Solution Strategist",
        "description": "Non-technical solution narrative",
    },
    {
        "id": "technical_architect",
        "name": "Technical Architect",
        "description": "Technical blueprint for the builder",
    },
    {
        "id": "code_builder",
        "name": "Code Builder",
        "description": "Implement as sandbox Python",
    },
    {
        "id": "sql_guardian",
        "name": "SQL Guardian",
        "description": "Validate every SQL statement",
    },
    {
        "id": "implementation_auditor",
        "name": "Implementation Auditor",
        "description": "Verify build matches the architect plan",
    },
    {
        "id": "response_publisher",
        "name": "Response Publisher",
        "description": "Package UI payload",
    },
]

AGENT_IDS = [a["id"] for a in AGENT_PIPELINE]
AGENT_BY_ID = {a["id"]: a for a in AGENT_PIPELINE}
