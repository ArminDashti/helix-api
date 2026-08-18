"""Canonical agent pipeline metadata."""

AGENT_PIPELINE = [
    {
        "id": "guardian",
        "name": "Guardian",
        "human_name": "Gale",
        "description": "Block dangerous prompts and check the caller's permission",
    },
    {
        "id": "sql_fetcher",
        "name": "SQL fetcher",
        "human_name": "Ned",
        "description": "Write a cheap SELECT and fetch warehouse rows",
    },
    {
        "id": "response_builder",
        "name": "Response builder",
        "human_name": "Remy",
        "description": "Build report, grid, and chart from fetched rows",
    },
    {
        "id": "validator",
        "name": "Validator",
        "human_name": "Vera",
        "description": "Check the result against the user prompt",
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
        "sql_guardian",
        "implementation_auditor",
        "response_publisher",
    }
)

LEGACY_AGENT_RENAMES = {
    "task_validator": "guardian",
    "sql": "sql_fetcher",
    "sql_guardian": "sql_fetcher",
    "response_publisher": "response_builder",
    "implementation_auditor": "validator",
}


def is_builtin_agent(agent_id: str) -> bool:
    return agent_id in AGENT_BY_ID
