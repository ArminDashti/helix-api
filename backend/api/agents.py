"""Canonical agent pipeline metadata."""

AGENT_PIPELINE = [
    {
        "id": "task_validator",
        "name": "Task Validator",
        "human_name": "Tommy",
        "description": "Validates the user prompt and mode",
    },
    {
        "id": "solution_strategist",
        "name": "Solution Strategist",
        "human_name": "Sara",
        "description": "Non-technical solution narrative",
    },
    {
        "id": "technical_architect",
        "name": "Technical Architect",
        "human_name": "James",
        "description": "Technical blueprint for the builder",
    },
    {
        "id": "code_builder",
        "name": "Code Builder",
        "human_name": "Emma",
        "description": "Implement as sandbox Python",
    },
    {
        "id": "sql",
        "name": "SQL",
        "human_name": "Noah",
        "description": "Fetch warehouse data and enforce SQL validation rules",
    },
    {
        "id": "implementation_auditor",
        "name": "Implementation Auditor",
        "human_name": "Lily",
        "description": "Check the work against the Technical Architect blueprint",
    },
    {
        "id": "response_publisher",
        "name": "Response Publisher",
        "human_name": "Owen",
        "description": "Package UI payload",
    },
]

AGENT_IDS = [a["id"] for a in AGENT_PIPELINE]
AGENT_BY_ID = {a["id"]: a for a in AGENT_PIPELINE}


def is_builtin_agent(agent_id: str) -> bool:
    return agent_id in AGENT_BY_ID
