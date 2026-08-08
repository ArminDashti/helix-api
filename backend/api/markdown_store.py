"""Filesystem store under backend/markdown-files/."""

from __future__ import annotations

import json
import re
from pathlib import Path

from django.conf import settings

from .agents import AGENT_BY_ID, AGENT_IDS, AGENT_PIPELINE

SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,120}$")


def root() -> Path:
    return Path(settings.MARKDOWN_FILES_DIR)


def instructions_dir() -> Path:
    return root() / "instructions"


def references_dir() -> Path:
    return root() / "references"


def rules_dir() -> Path:
    return root() / "rules"


def assignments_path() -> Path:
    return root() / "rule-assignments.json"


def ensure_dirs() -> None:
    for path in (instructions_dir(), references_dir(), rules_dir(), skills_dir()):
        path.mkdir(parents=True, exist_ok=True)
    if not assignments_path().exists():
        assignments_path().write_text("{}", encoding="utf-8")


def skills_dir() -> Path:
    return root() / "skills"


def _skill_scope_dir(scope: str) -> Path:
    scope = scope.strip()
    if scope == "shared":
        return skills_dir() / "shared"
    if scope not in AGENT_BY_ID:
        raise KeyError(f"Unknown skill scope: {scope}")
    return skills_dir() / scope


def _skill_path(scope: str, skill_id: str) -> Path:
    stem = _safe_stem(skill_id)
    return _skill_scope_dir(scope) / stem / "SKILL.md"


def _skill_has_any() -> bool:
    base = skills_dir()
    if not base.is_dir():
        return False
    return any(base.rglob("SKILL.md"))


def seed_skills_if_empty() -> None:
    """Seed skills from analytics/agents when markdown-files/skills is empty."""
    ensure_dirs()
    if _skill_has_any():
        return

    agents_root = _agents_source_dir()

    shared_src = agents_root / "_shared" / "skills"
    if shared_src.is_dir():
        for skill_folder in sorted(shared_src.iterdir()):
            skill_md = skill_folder / "SKILL.md"
            if skill_folder.is_dir() and skill_md.exists():
                dest_dir = skills_dir() / "shared" / skill_folder.name
                dest_dir.mkdir(parents=True, exist_ok=True)
                (dest_dir / "SKILL.md").write_text(
                    skill_md.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )

    for agent_id in AGENT_IDS:
        agent_skills = agents_root / agent_id / "skills"
        if not agent_skills.is_dir():
            continue
        for skill_folder in sorted(agent_skills.iterdir()):
            skill_md = skill_folder / "SKILL.md"
            if skill_folder.is_dir() and skill_md.exists():
                dest_dir = skills_dir() / agent_id / skill_folder.name
                dest_dir.mkdir(parents=True, exist_ok=True)
                (dest_dir / "SKILL.md").write_text(
                    skill_md.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )


def _read_skill(scope: str, skill_id: str) -> dict:
    stem = _safe_stem(skill_id)
    path = _skill_path(scope, stem)
    if not path.exists():
        raise FileNotFoundError(f"{scope}/{stem}")
    return {
        "id": stem,
        "scope": scope,
        "content": path.read_text(encoding="utf-8"),
    }


def list_skills(scope: str | None = None) -> list[dict]:
    ensure_dirs()
    seed_skills_if_empty()
    items: list[dict] = []

    def collect(scope_name: str) -> None:
        scope_path = skills_dir() / scope_name
        if not scope_path.is_dir():
            return
        for skill_folder in sorted(scope_path.iterdir()):
            skill_md = skill_folder / "SKILL.md"
            if skill_folder.is_dir() and skill_md.exists():
                items.append(
                    {
                        "id": skill_folder.name,
                        "scope": scope_name,
                        "content": skill_md.read_text(encoding="utf-8"),
                    }
                )

    if scope:
        if scope != "shared" and scope not in AGENT_BY_ID:
            raise KeyError(f"Unknown skill scope: {scope}")
        collect(scope)
    else:
        collect("shared")
        for agent_id in AGENT_IDS:
            collect(agent_id)

    return items


def get_skill(scope: str, skill_id: str) -> dict:
    ensure_dirs()
    return _read_skill(scope, skill_id)


def create_skill(scope: str, skill_id: str, content: str = "") -> dict:
    ensure_dirs()
    stem = _safe_stem(skill_id)
    if scope != "shared" and scope not in AGENT_BY_ID:
        raise KeyError(f"Unknown skill scope: {scope}")
    path = _skill_path(scope, stem)
    if path.exists():
        raise FileExistsError(f"{scope}/{stem}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content or "", encoding="utf-8")
    return _read_skill(scope, stem)


def update_skill(scope: str, skill_id: str, content: str) -> dict:
    ensure_dirs()
    stem = _safe_stem(skill_id)
    path = _skill_path(scope, stem)
    if not path.exists():
        raise FileNotFoundError(f"{scope}/{stem}")
    path.write_text(content if content is not None else "", encoding="utf-8")
    return _read_skill(scope, stem)


def delete_skill(scope: str, skill_id: str) -> None:
    ensure_dirs()
    stem = _safe_stem(skill_id)
    path = _skill_path(scope, stem)
    if not path.exists():
        raise FileNotFoundError(f"{scope}/{stem}")
    path.unlink()
    # Remove empty skill folder
    try:
        path.parent.rmdir()
    except OSError:
        pass


def _safe_stem(name: str) -> str:
    stem = name.strip()
    if stem.lower().endswith(".md"):
        stem = stem[:-3]
    if not SAFE_NAME_RE.match(stem):
        raise ValueError(
            "Name must be alphanumeric (letters, digits, ., _, -), max 121 chars"
        )
    return stem


def _agents_source_dir() -> Path:
    return Path(settings.AGENTS_DIR)


def seed_if_empty() -> None:
    """Seed instructions/rules from analytics/agents when store is empty."""
    ensure_dirs()
    instr = instructions_dir()
    existing = list(instr.glob("*.md"))
    if existing:
        return

    agents_root = _agents_source_dir()
    assignments: dict[str, list[str]] = {}

    for agent_id in AGENT_IDS:
        agent_md = agents_root / agent_id / "AGENT.md"
        content = ""
        if agent_md.exists():
            content = agent_md.read_text(encoding="utf-8")
        else:
            meta = AGENT_BY_ID[agent_id]
            content = (
                f"# {meta['name']}\n\n{meta['description']}\n"
            )
        (instr / f"{agent_id}.md").write_text(content, encoding="utf-8")

        # Agent-specific rules
        rules_folder = agents_root / agent_id / "rules"
        if rules_folder.is_dir():
            for rule_file in sorted(rules_folder.glob("*.md")):
                stem = f"{agent_id}-{rule_file.stem}"
                dest = rules_dir() / f"{stem}.md"
                if not dest.exists():
                    dest.write_text(rule_file.read_text(encoding="utf-8"), encoding="utf-8")
                assignments.setdefault(stem, []).append(agent_id)

    # Shared rules → all agents
    shared_rules = agents_root / "_shared" / "rules"
    if shared_rules.is_dir():
        for rule_file in sorted(shared_rules.glob("*.md")):
            stem = f"shared-{rule_file.stem}"
            dest = rules_dir() / f"{stem}.md"
            if not dest.exists():
                dest.write_text(rule_file.read_text(encoding="utf-8"), encoding="utf-8")
            assignments[stem] = list(AGENT_IDS)

    assignments_path().write_text(
        json.dumps(assignments, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# --- Instructions ---


def list_agents_with_instructions() -> list[dict]:
    ensure_dirs()
    result = []
    for meta in AGENT_PIPELINE:
        path = instructions_dir() / f"{meta['id']}.md"
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        result.append({**meta, "instruction": content})
    return result


def get_instruction(agent_id: str) -> str:
    if agent_id not in AGENT_BY_ID:
        raise KeyError(f"Unknown agent: {agent_id}")
    path = instructions_dir() / f"{agent_id}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def set_instruction(agent_id: str, content: str) -> str:
    if agent_id not in AGENT_BY_ID:
        raise KeyError(f"Unknown agent: {agent_id}")
    ensure_dirs()
    path = instructions_dir() / f"{agent_id}.md"
    path.write_text(content if content is not None else "", encoding="utf-8")
    return path.read_text(encoding="utf-8")


# --- References ---


def list_references() -> list[dict]:
    ensure_dirs()
    items = []
    for path in sorted(references_dir().glob("*.md")):
        items.append(
            {
                "name": path.stem,
                "filename": path.name,
                "content": path.read_text(encoding="utf-8"),
            }
        )
    return items


def get_reference(name: str) -> dict:
    stem = _safe_stem(name)
    path = references_dir() / f"{stem}.md"
    if not path.exists():
        raise FileNotFoundError(stem)
    return {
        "name": stem,
        "filename": path.name,
        "content": path.read_text(encoding="utf-8"),
    }


def create_reference(name: str, content: str = "") -> dict:
    ensure_dirs()
    stem = _safe_stem(name)
    path = references_dir() / f"{stem}.md"
    if path.exists():
        raise FileExistsError(stem)
    path.write_text(content or "", encoding="utf-8")
    return get_reference(stem)


def update_reference(name: str, content: str) -> dict:
    stem = _safe_stem(name)
    path = references_dir() / f"{stem}.md"
    if not path.exists():
        raise FileNotFoundError(stem)
    path.write_text(content if content is not None else "", encoding="utf-8")
    return get_reference(stem)


def delete_reference(name: str) -> None:
    stem = _safe_stem(name)
    path = references_dir() / f"{stem}.md"
    if not path.exists():
        raise FileNotFoundError(stem)
    path.unlink()


# --- Rules ---


def list_rules() -> list[dict]:
    ensure_dirs()
    assignments = load_assignments()
    items = []
    for path in sorted(rules_dir().glob("*.md")):
        items.append(
            {
                "id": path.stem,
                "filename": path.name,
                "content": path.read_text(encoding="utf-8"),
                "agents": assignments.get(path.stem, []),
            }
        )
    return items


def get_rule(rule_id: str) -> dict:
    stem = _safe_stem(rule_id)
    path = rules_dir() / f"{stem}.md"
    if not path.exists():
        raise FileNotFoundError(stem)
    assignments = load_assignments()
    return {
        "id": stem,
        "filename": path.name,
        "content": path.read_text(encoding="utf-8"),
        "agents": assignments.get(stem, []),
    }


def create_rule(rule_id: str, content: str = "", agents: list[str] | None = None) -> dict:
    ensure_dirs()
    stem = _safe_stem(rule_id)
    path = rules_dir() / f"{stem}.md"
    if path.exists():
        raise FileExistsError(stem)
    path.write_text(content or "", encoding="utf-8")
    if agents is not None:
        _set_rule_agents(stem, agents)
    return get_rule(stem)


def update_rule(
    rule_id: str,
    content: str | None = None,
    agents: list[str] | None = None,
) -> dict:
    stem = _safe_stem(rule_id)
    path = rules_dir() / f"{stem}.md"
    if not path.exists():
        raise FileNotFoundError(stem)
    if content is not None:
        path.write_text(content, encoding="utf-8")
    if agents is not None:
        _set_rule_agents(stem, agents)
    return get_rule(stem)


def delete_rule(rule_id: str) -> None:
    stem = _safe_stem(rule_id)
    path = rules_dir() / f"{stem}.md"
    if not path.exists():
        raise FileNotFoundError(stem)
    path.unlink()
    assignments = load_assignments()
    if stem in assignments:
        del assignments[stem]
        save_assignments(assignments)


def load_assignments() -> dict[str, list[str]]:
    ensure_dirs()
    raw = json.loads(assignments_path().read_text(encoding="utf-8") or "{}")
    if not isinstance(raw, dict):
        return {}
    cleaned: dict[str, list[str]] = {}
    for key, value in raw.items():
        if not isinstance(value, list):
            continue
        cleaned[str(key)] = [a for a in value if a in AGENT_BY_ID]
    return cleaned


def save_assignments(assignments: dict[str, list[str]]) -> dict[str, list[str]]:
    ensure_dirs()
    cleaned: dict[str, list[str]] = {}
    for key, agents in assignments.items():
        if not isinstance(agents, list):
            continue
        cleaned[str(key)] = [a for a in agents if a in AGENT_BY_ID]
    assignments_path().write_text(
        json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return cleaned


def _set_rule_agents(rule_id: str, agents: list[str]) -> None:
    assignments = load_assignments()
    assignments[rule_id] = [a for a in agents if a in AGENT_BY_ID]
    save_assignments(assignments)
