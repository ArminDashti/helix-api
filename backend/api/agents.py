"""Canonical agent pipeline metadata."""

AGENT_PIPELINE = [
    {
        "id": "guardian",
        "name": "guardian",
        "description": "Block dangerous prompts and check the caller's permission",
    },
    {
        "id": "data-gatherer",
        "name": "data-gatherer",
        "description": "Write a cheap SELECT from catalog and references, then fetch rows",
    },
    {
        "id": "validator",
        "name": "validator",
        "description": "Check gathered or built results against the user prompt",
    },
    {
        "id": "result-builder",
        "name": "result-builder",
        "description": "Build report text from fetched rows",
    },
    {
        "id": "publisher",
        "name": "publisher",
        "description": "Package report, grid, and chart for the UI",
    },
]

AGENT_IDS = [a["id"] for a in AGENT_PIPELINE]
AGENT_BY_ID = {a["id"]: a for a in AGENT_PIPELINE}

LEGACY_AGENT_IDS = frozenset(
    {
        "task_validator",
        "solution_strategist",
        "technical_architect",
        "code_builder",
        "sql",
        "sql_fetcher",
        "sql_guardian",
        "response_builder",
        "response_publisher",
        "implementation_auditor",
    }
)

LEGACY_AGENT_RENAMES = {
    "task_validator": "guardian",
    "sql": "data-gatherer",
    "sql_fetcher": "data-gatherer",
    "sql_guardian": "data-gatherer",
    "response_builder": "result-builder",
    "response_publisher": "result-builder",
    "implementation_auditor": "validator",
}


def resolve_agent_definition_id(agent_id: str) -> str:
    """Map graph instance id (e.g. validator__2) to roster agent id."""
    if "__" in agent_id:
        base = agent_id.rsplit("__", 1)[0]
        if base in AGENT_BY_ID or base in LEGACY_AGENT_RENAMES:
            return LEGACY_AGENT_RENAMES.get(base, base)
    return LEGACY_AGENT_RENAMES.get(agent_id, agent_id)


def is_builtin_agent(agent_id: str) -> bool:
    return resolve_agent_definition_id(agent_id) in AGENT_BY_ID
