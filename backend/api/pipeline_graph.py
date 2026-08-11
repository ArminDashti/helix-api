"""Conditional pipeline DAG: persistence, validation, and walk helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .agents import AGENT_BY_ID, AGENT_PIPELINE
from .config_loader import known_agent_ids, load_config, save_config

WHEN_TYPES = frozenset({"always", "on_success", "on_failure", "on_retry", "on_status"})
MAX_STEPS = 64
MAX_VISITS_PER_NODE = 3


def default_pipeline_graph() -> dict[str, Any]:
    """Linear AGENT_PIPELINE plus sql_guardian → code_builder retry edge."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    x = 0.0
    y = 0.0
    for i, meta in enumerate(AGENT_PIPELINE):
        nodes.append(
            {
                "id": meta["id"],
                "position": {"x": x, "y": y + i * 100},
            }
        )
        if i > 0:
            prev = AGENT_PIPELINE[i - 1]["id"]
            edges.append(
                {
                    "id": f"e_{prev}_{meta['id']}",
                    "source": prev,
                    "target": meta["id"],
                    "direction": "forward",
                    "when": {"type": "always"},
                }
            )
    edges.append(
        {
            "id": "e_sql_guardian_code_builder_retry",
            "source": "sql_guardian",
            "target": "code_builder",
            "direction": "forward",
            "when": {"type": "on_retry"},
        }
    )
    return {
        "entry": AGENT_PIPELINE[0]["id"] if AGENT_PIPELINE else None,
        "nodes": nodes,
        "edges": edges,
    }


def _normalize_when(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"type": "always"}
    wtype = str(raw.get("type") or "always").strip().lower()
    if wtype not in WHEN_TYPES:
        raise ValueError(f"Invalid edge when.type: {wtype}")
    out: dict[str, Any] = {"type": wtype}
    if wtype == "on_status":
        status = str(raw.get("status") or "").strip()
        if not status:
            raise ValueError("on_status edges require when.status")
        out["status"] = status
    return out


def normalize_pipeline_graph(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload or not isinstance(payload, dict):
        return default_pipeline_graph()

    raw_nodes = payload.get("nodes")
    raw_edges = payload.get("edges")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValueError("pipeline_graph.nodes must be a non-empty list")
    if not isinstance(raw_edges, list):
        raise ValueError("pipeline_graph.edges must be a list")

    allowed = known_agent_ids()
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in raw_nodes:
        if not isinstance(entry, dict):
            continue
        node_id = str(entry.get("id") or "").strip()
        if not node_id:
            continue
        if node_id not in allowed:
            raise ValueError(f"Unknown agent node: {node_id}")
        if node_id in seen:
            raise ValueError(f"Duplicate node id: {node_id}")
        seen.add(node_id)
        pos = entry.get("position") if isinstance(entry.get("position"), dict) else {}
        try:
            px = float(pos.get("x", 0))
            py = float(pos.get("y", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid position for node {node_id}") from exc
        nodes.append({"id": node_id, "position": {"x": px, "y": py}})

    if not nodes:
        raise ValueError("pipeline_graph.nodes must include at least one agent")

    node_ids = {n["id"] for n in nodes}
    edges: list[dict[str, Any]] = []
    edge_ids: set[str] = set()
    for i, entry in enumerate(raw_edges):
        if not isinstance(entry, dict):
            continue
        source = str(entry.get("source") or "").strip()
        target = str(entry.get("target") or "").strip()
        if not source or not target:
            raise ValueError("Each edge needs source and target")
        if source not in node_ids or target not in node_ids:
            raise ValueError(f"Edge endpoints must be graph nodes: {source} → {target}")
        edge_id = str(entry.get("id") or f"e_{source}_{target}_{i}").strip()
        if edge_id in edge_ids:
            raise ValueError(f"Duplicate edge id: {edge_id}")
        edge_ids.add(edge_id)
        edges.append(
            {
                "id": edge_id,
                "source": source,
                "target": target,
                "direction": "forward",
                "when": _normalize_when(entry.get("when")),
            }
        )

    entry = payload.get("entry")
    if entry is not None:
        entry = str(entry).strip()
        if entry and entry not in node_ids:
            raise ValueError(f"entry must be a graph node: {entry}")
    if not entry:
        entry = _infer_entry(nodes, edges)

    return {"entry": entry, "nodes": nodes, "edges": edges}


def _infer_entry(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> str | None:
    targets = {e["target"] for e in edges if e.get("when", {}).get("type") in ("always", "on_success")}
    for node in nodes:
        if node["id"] not in targets:
            return node["id"]
    return nodes[0]["id"] if nodes else None


def get_pipeline_graph() -> dict[str, Any]:
    data = load_config()
    raw = data.get("pipeline_graph")
    if not isinstance(raw, dict) or not raw.get("nodes"):
        return default_pipeline_graph()
    try:
        return normalize_pipeline_graph(raw)
    except ValueError:
        return default_pipeline_graph()


def update_pipeline_graph(payload: dict[str, Any]) -> dict[str, Any]:
    graph = normalize_pipeline_graph(payload)
    data = load_config()
    data["pipeline_graph"] = deepcopy(graph)
    save_config(data)
    return graph


def reset_pipeline_graph() -> dict[str, Any]:
    return update_pipeline_graph(default_pipeline_graph())


def edge_matches(when: dict[str, Any], status: str) -> bool:
    wtype = when.get("type") or "always"
    if wtype in ("always", "on_success"):
        return status in ("done", "success")
    if wtype == "on_failure":
        return status in ("failed", "failure", "error")
    if wtype == "on_retry":
        return status == "retry"
    if wtype == "on_status":
        return status == when.get("status")
    return False


def next_targets(
    graph: dict[str, Any], source_id: str, status: str
) -> list[str]:
    """First matching outgoing edge wins (edges kept in saved order)."""
    for edge in graph.get("edges") or []:
        if edge.get("source") != source_id:
            continue
        if edge_matches(edge.get("when") or {}, status):
            return [edge["target"]]
    return []


def agent_display_name(agent_id: str) -> str:
    meta = AGENT_BY_ID.get(agent_id)
    if meta:
        return meta["name"]
    return agent_id.replace("_", " ").title()
