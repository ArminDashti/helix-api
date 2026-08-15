"""Filesystem store under backend/markdown-files/."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings

from .agents import AGENT_BY_ID, AGENT_IDS

SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,120}$")
_NUMERIC_PREFIX_RE = re.compile(r"^\d+[-_]")

RULE_ID_MIGRATION = {
    "shared-00-security": "security",
    "shared-01-output-contract": "output-contract",
    "shared-02-base-behavior": "base-behavior",
    "task_validator-10-feasibility": "feasibility",
    "solution_strategist-10-non-technical": "non-technical",
    "technical_architect-10-blueprint": "blueprint",
    "code_builder-10-implement": "implement",
    "sql_guardian-10-select-only": "select-only",
    "implementation_auditor-10-verify-plan": "verify-plan",
    "response_publisher-10-package-payload": "package-payload",
}

RULE_DISPLAY_NAMES = {
    "security": "Security",
    "output-contract": "Output contract",
    "base-behavior": "Base behavior",
    "feasibility": "Feasibility",
    "non-technical": "Non-technical",
    "blueprint": "Blueprint",
    "implement": "Implement",
    "select-only": "Select only",
    "verify-plan": "Verify plan",
    "package-payload": "Package payload",
}

SKILL_DISPLAY_NAMES = {
    "echarts-response": "ECharts response",
    "sandbox-python": "Sandbox Python",
    "sql-safety": "SQL safety",
    "text-report": "Text report",
    "validate-feasibility": "Validate feasibility",
    "craft-solution-narrative": "Craft solution narrative",
    "write-technical-blueprint": "Write technical blueprint",
    "implement-sandbox-script": "Implement sandbox script",
    "review-sql-statements": "Review SQL statements",
    "audit-against-blueprint": "Audit against blueprint",
    "package-ui-payload": "Package UI payload",
}


def _parse_md_meta(content: str) -> dict[str, Any]:
    meta: dict[str, Any] = {"name": "", "disabled": False}
    if not content or not content.startswith("---"):
        return meta
    rest = content[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    end = rest.find("\n---")
    if end < 0:
        return meta
    try:
        data = yaml.safe_load(rest[:end]) or {}
    except yaml.YAMLError:
        return meta
    if not isinstance(data, dict):
        return meta
    name = data.get("name")
    meta["name"] = "" if name is None else str(name).strip()
    meta["disabled"] = bool(data.get("disabled"))
    return meta


def _set_md_meta(
    content: str,
    *,
    name: str | None = None,
    disabled: bool | None = None,
) -> str:
    body = content or ""
    data: dict[str, Any] = {}
    rest = body
    if body.startswith("---"):
        after = body[3:]
        if after.startswith("\n"):
            after = after[1:]
        end = after.find("\n---")
        if end >= 0:
            try:
                parsed = yaml.safe_load(after[:end]) or {}
            except yaml.YAMLError:
                parsed = {}
            if isinstance(parsed, dict):
                data = dict(parsed)
            rest = after[end + 4 :]
            if rest.startswith("\n"):
                rest = rest[1:]
    if name is not None:
        cleaned = str(name).strip()
        if cleaned:
            data["name"] = cleaned
        else:
            data.pop("name", None)
    if disabled is not None:
        if disabled:
            data["disabled"] = True
        else:
            data.pop("disabled", None)
    if not data:
        return rest
    dumped = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{dumped}\n---\n{rest}"


def _strip_numeric_prefix(stem: str) -> str:
    return _NUMERIC_PREFIX_RE.sub("", stem)


def _humanize_id(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").strip().title()


def migrate_rule_ids() -> None:
    """Rename legacy numbered/prefixed rule files and set display names."""
    ensure_dirs()
    rules = rules_dir()
    assignments = None
    assignments_changed = False
    if assignments_path().exists():
        raw = json.loads(assignments_path().read_text(encoding="utf-8") or "{}")
        assignments = raw if isinstance(raw, dict) else {}
    else:
        assignments = {}

    for old_id, new_id in RULE_ID_MIGRATION.items():
        old_path = rules / f"{old_id}.md"
        new_path = rules / f"{new_id}.md"
        if old_path.exists() and not new_path.exists():
            new_path.write_text(old_path.read_text(encoding="utf-8"), encoding="utf-8")
            old_path.unlink()
        if old_id in assignments and new_id not in assignments:
            assignments[new_id] = assignments.pop(old_id)
            assignments_changed = True
        elif old_id in assignments:
            del assignments[old_id]
            assignments_changed = True

    for path in sorted(rules.glob("*.md")):
        wanted = RULE_DISPLAY_NAMES.get(path.stem)
        if not wanted:
            continue
        content = path.read_text(encoding="utf-8")
        meta = _parse_md_meta(content)
        if meta["name"] == wanted:
            continue
        path.write_text(_set_md_meta(content, name=wanted), encoding="utf-8")

    if assignments_changed:
        assignments_path().write_text(
            json.dumps(assignments, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def ensure_skill_display_names() -> None:
    ensure_dirs()
    base = skills_dir()
    if not base.is_dir():
        return
    for skill_md in base.rglob("SKILL.md"):
        skill_id = skill_md.parent.name
        wanted = SKILL_DISPLAY_NAMES.get(skill_id)
        if not wanted:
            continue
        content = skill_md.read_text(encoding="utf-8")
        meta = _parse_md_meta(content)
        if meta["name"] == wanted:
            continue
        skill_md.write_text(_set_md_meta(content, name=wanted), encoding="utf-8")


def _known_agent_ids() -> set[str]:
    from .config_loader import known_agent_ids

    return known_agent_ids()


def _all_agent_metas() -> list[dict]:
    from .config_loader import get_all_agent_metas

    return get_all_agent_metas()


def _agent_scope_ids() -> list[str]:
    return [meta["id"] for meta in _all_agent_metas()]


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


def skill_assignments_path() -> Path:
    return root() / "skill-assignments.json"


def ensure_dirs() -> None:
    for path in (instructions_dir(), references_dir(), rules_dir(), skills_dir()):
        path.mkdir(parents=True, exist_ok=True)
    if not assignments_path().exists():
        assignments_path().write_text("{}", encoding="utf-8")
    if not skill_assignments_path().exists():
        skill_assignments_path().write_text("{}", encoding="utf-8")


def skills_dir() -> Path:
    return root() / "skills"


def _skill_scope_dir(scope: str) -> Path:
    scope = scope.strip()
    if scope == "shared":
        return skills_dir() / "shared"
    if scope not in _known_agent_ids():
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
        ensure_skill_display_names()
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
                    _set_md_meta(
                        skill_md.read_text(encoding="utf-8"),
                        name=SKILL_DISPLAY_NAMES.get(skill_folder.name)
                        or _humanize_id(skill_folder.name),
                    ),
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
                    _set_md_meta(
                        skill_md.read_text(encoding="utf-8"),
                        name=SKILL_DISPLAY_NAMES.get(skill_folder.name)
                        or _humanize_id(skill_folder.name),
                    ),
                    encoding="utf-8",
                )


def _skill_assign_key(scope: str, skill_id: str) -> str:
    return f"{scope}/{skill_id}"


def load_skill_assignments() -> dict[str, list[str]]:
    ensure_dirs()
    raw = json.loads(skill_assignments_path().read_text(encoding="utf-8") or "{}")
    if not isinstance(raw, dict):
        return {}
    known = _known_agent_ids()
    cleaned: dict[str, list[str]] = {}
    for key, value in raw.items():
        if not isinstance(value, list):
            continue
        cleaned[str(key)] = [a for a in value if a in known]
    return cleaned


def save_skill_assignments(assignments: dict[str, list[str]]) -> dict[str, list[str]]:
    ensure_dirs()
    known = _known_agent_ids()
    cleaned: dict[str, list[str]] = {}
    for key, agents in assignments.items():
        if not isinstance(agents, list):
            continue
        cleaned[str(key)] = [a for a in agents if a in known]
    skill_assignments_path().write_text(
        json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return cleaned


def _default_skill_agents(scope: str) -> list[str]:
    if scope == "shared":
        return list(_agent_scope_ids())
    return [scope]


def _set_skill_agents(scope: str, skill_id: str, agents: list[str]) -> None:
    assignments = load_skill_assignments()
    known = _known_agent_ids()
    assignments[_skill_assign_key(scope, skill_id)] = [a for a in agents if a in known]
    save_skill_assignments(assignments)


def _skill_item(scope: str, skill_id: str, content: str) -> dict[str, Any]:
    meta = _parse_md_meta(content)
    key = _skill_assign_key(scope, skill_id)
    assigned = load_skill_assignments().get(key)
    agents = assigned if assigned is not None else _default_skill_agents(scope)
    return {
        "id": skill_id,
        "scope": scope,
        "name": meta["name"] or skill_id,
        "disabled": bool(meta["disabled"]),
        "agents": agents,
        "content": content,
    }


def _read_skill(scope: str, skill_id: str) -> dict:
    stem = _safe_stem(skill_id)
    path = _skill_path(scope, stem)
    if not path.exists():
        raise FileNotFoundError(f"{scope}/{stem}")
    return _skill_item(scope, stem, path.read_text(encoding="utf-8"))


def list_skills(scope: str | None = None) -> list[dict]:
    ensure_dirs()
    seed_skills_if_empty()
    ensure_skill_display_names()
    items: list[dict] = []

    def collect(scope_name: str) -> None:
        scope_path = skills_dir() / scope_name
        if not scope_path.is_dir():
            return
        for skill_folder in sorted(scope_path.iterdir()):
            skill_md = skill_folder / "SKILL.md"
            if skill_folder.is_dir() and skill_md.exists():
                items.append(
                    _skill_item(
                        scope_name,
                        skill_folder.name,
                        skill_md.read_text(encoding="utf-8"),
                    )
                )

    if scope:
        if scope != "shared" and scope not in _known_agent_ids():
            raise KeyError(f"Unknown skill scope: {scope}")
        collect(scope)
    else:
        collect("shared")
        for agent_id in _agent_scope_ids():
            collect(agent_id)

    return items


def get_skill(scope: str, skill_id: str) -> dict:
    ensure_dirs()
    return _read_skill(scope, skill_id)


def create_skill(
    scope: str,
    skill_id: str,
    content: str = "",
    *,
    agents: list[str] | None = None,
    name: str | None = None,
    disabled: bool = False,
) -> dict:
    ensure_dirs()
    stem = _safe_stem(skill_id)
    known = _known_agent_ids()
    assigned = None
    if agents is not None:
        assigned = [a for a in agents if a in known]
        if not scope:
            scope = assigned[0] if len(assigned) == 1 else "shared"
    if not scope:
        scope = "shared"
    if scope != "shared" and scope not in known:
        raise KeyError(f"Unknown skill scope: {scope}")
    path = _skill_path(scope, stem)
    if path.exists():
        raise FileExistsError(f"{scope}/{stem}")
    text = _set_md_meta(content or "", name=name, disabled=disabled)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if assigned is not None:
        _set_skill_agents(scope, stem, assigned)
    return _read_skill(scope, stem)


def update_skill(
    scope: str,
    skill_id: str,
    content: str | None = None,
    *,
    agents: list[str] | None = None,
    name: str | None = None,
    disabled: bool | None = None,
) -> dict:
    ensure_dirs()
    stem = _safe_stem(skill_id)
    path = _skill_path(scope, stem)
    if not path.exists():
        raise FileNotFoundError(f"{scope}/{stem}")
    text = path.read_text(encoding="utf-8") if content is None else content
    if name is not None or disabled is not None:
        text = _set_md_meta(text, name=name, disabled=disabled)
    path.write_text(text if text is not None else "", encoding="utf-8")
    if agents is not None:
        _set_skill_agents(scope, stem, agents)
    return _read_skill(scope, stem)


def delete_skill(scope: str, skill_id: str) -> None:
    ensure_dirs()
    stem = _safe_stem(skill_id)
    path = _skill_path(scope, stem)
    if not path.exists():
        raise FileNotFoundError(f"{scope}/{stem}")
    path.unlink()
    try:
        path.parent.rmdir()
    except OSError:
        pass
    assignments = load_skill_assignments()
    key = _skill_assign_key(scope, stem)
    if key in assignments:
        del assignments[key]
        save_skill_assignments(assignments)


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
                stem = _strip_numeric_prefix(rule_file.stem)
                dest = rules_dir() / f"{stem}.md"
                name = RULE_DISPLAY_NAMES.get(stem) or _humanize_id(stem)
                if not dest.exists():
                    dest.write_text(
                        _set_md_meta(rule_file.read_text(encoding="utf-8"), name=name),
                        encoding="utf-8",
                    )
                assignments.setdefault(stem, []).append(agent_id)

    # Shared rules → all agents
    shared_rules = agents_root / "_shared" / "rules"
    if shared_rules.is_dir():
        for rule_file in sorted(shared_rules.glob("*.md")):
            stem = _strip_numeric_prefix(rule_file.stem)
            dest = rules_dir() / f"{stem}.md"
            name = RULE_DISPLAY_NAMES.get(stem) or _humanize_id(stem)
            if not dest.exists():
                dest.write_text(
                    _set_md_meta(rule_file.read_text(encoding="utf-8"), name=name),
                    encoding="utf-8",
                )
            assignments[stem] = list(AGENT_IDS)

    assignments_path().write_text(
        json.dumps(assignments, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# --- Instructions ---


def list_agents_with_instructions() -> list[dict]:
    ensure_dirs()
    # Lazy import avoids circular import at module load
    from .config_loader import get_agent_display_names

    names = get_agent_display_names()
    result = []
    for meta in _all_agent_metas():
        path = instructions_dir() / f"{meta['id']}.md"
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        result.append(
            {
                **meta,
                "name": names.get(meta["id"], meta["name"]),
                "instruction": content,
            }
        )
    return result

def get_instruction(agent_id: str) -> str:
    if agent_id not in _known_agent_ids():
        raise KeyError(f"Unknown agent: {agent_id}")
    path = instructions_dir() / f"{agent_id}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def set_instruction(agent_id: str, content: str) -> str:
    if agent_id not in _known_agent_ids():
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
    migrate_rule_ids()
    assignments = load_assignments()
    items = []
    for path in sorted(rules_dir().glob("*.md")):
        content = path.read_text(encoding="utf-8")
        meta = _parse_md_meta(content)
        items.append(
            {
                "id": path.stem,
                "name": meta["name"] or path.stem,
                "disabled": bool(meta["disabled"]),
                "filename": path.name,
                "content": content,
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
    content = path.read_text(encoding="utf-8")
    meta = _parse_md_meta(content)
    return {
        "id": stem,
        "name": meta["name"] or stem,
        "disabled": bool(meta["disabled"]),
        "filename": path.name,
        "content": content,
        "agents": assignments.get(stem, []),
    }


def create_rule(
    rule_id: str,
    content: str = "",
    agents: list[str] | None = None,
    *,
    name: str | None = None,
    disabled: bool = False,
) -> dict:
    ensure_dirs()
    stem = _safe_stem(rule_id)
    path = rules_dir() / f"{stem}.md"
    if path.exists():
        raise FileExistsError(stem)
    text = _set_md_meta(content or "", name=name, disabled=disabled)
    path.write_text(text, encoding="utf-8")
    if agents is not None:
        _set_rule_agents(stem, agents)
    return get_rule(stem)


def update_rule(
    rule_id: str,
    content: str | None = None,
    agents: list[str] | None = None,
    *,
    name: str | None = None,
    disabled: bool | None = None,
) -> dict:
    stem = _safe_stem(rule_id)
    path = rules_dir() / f"{stem}.md"
    if not path.exists():
        raise FileNotFoundError(stem)
    text = path.read_text(encoding="utf-8") if content is None else content
    if name is not None or disabled is not None:
        text = _set_md_meta(text, name=name, disabled=disabled)
    if content is not None or name is not None or disabled is not None:
        path.write_text(text, encoding="utf-8")
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
    known = _known_agent_ids()
    cleaned: dict[str, list[str]] = {}
    for key, value in raw.items():
        if not isinstance(value, list):
            continue
        cleaned[str(key)] = [a for a in value if a in known]
    return cleaned


def save_assignments(assignments: dict[str, list[str]]) -> dict[str, list[str]]:
    ensure_dirs()
    known = _known_agent_ids()
    cleaned: dict[str, list[str]] = {}
    for key, agents in assignments.items():
        if not isinstance(agents, list):
            continue
        cleaned[str(key)] = [a for a in agents if a in known]
    assignments_path().write_text(
        json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return cleaned


def _set_rule_agents(rule_id: str, agents: list[str]) -> None:
    assignments = load_assignments()
    known = _known_agent_ids()
    assignments[rule_id] = [a for a in agents if a in known]
    save_assignments(assignments)

def rename_rule(old_id: str, new_id: str) -> dict:
    ensure_dirs()
    old_stem = _safe_stem(old_id)
    new_stem = _safe_stem(new_id)
    if old_stem == new_stem:
        return get_rule(old_stem)
    old_path = rules_dir() / f"{old_stem}.md"
    new_path = rules_dir() / f"{new_stem}.md"
    if not old_path.exists():
        raise FileNotFoundError(old_stem)
    if new_path.exists():
        raise FileExistsError(new_stem)
    content = old_path.read_text(encoding="utf-8")
    new_path.write_text(content, encoding="utf-8")
    old_path.unlink()
    assignments = load_assignments()
    if old_stem in assignments:
        assignments[new_stem] = assignments.pop(old_stem)
        save_assignments(assignments)
    return get_rule(new_stem)


def rename_skill(scope: str, old_id: str, new_id: str) -> dict:
    ensure_dirs()
    if scope != "shared" and scope not in _known_agent_ids():
        raise KeyError(f"Unknown skill scope: {scope}")
    old_stem = _safe_stem(old_id)
    new_stem = _safe_stem(new_id)
    if old_stem == new_stem:
        return _read_skill(scope, old_stem)
    old_path = _skill_path(scope, old_stem)
    new_path = _skill_path(scope, new_stem)
    if not old_path.exists():
        raise FileNotFoundError(f"{scope}/{old_stem}")
    if new_path.exists():
        raise FileExistsError(f"{scope}/{new_stem}")
    new_path.parent.mkdir(parents=True, exist_ok=True)
    content = old_path.read_text(encoding="utf-8")
    new_path.write_text(content, encoding="utf-8")
    old_path.unlink()
    try:
        old_path.parent.rmdir()
    except OSError:
        pass
    assignments = load_skill_assignments()
    old_key = _skill_assign_key(scope, old_stem)
    new_key = _skill_assign_key(scope, new_stem)
    if old_key in assignments:
        assignments[new_key] = assignments.pop(old_key)
        save_skill_assignments(assignments)
    return _read_skill(scope, new_stem)
