"""Conditional pipeline DAG: structured flow, persistence, validation, walk helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .agents import AGENT_BY_ID
from .config_loader import get_agent_display_names, get_all_agent_metas, known_agent_ids, load_config, save_config

WHEN_TYPES = frozenset({"always", "on_success", "on_failure", "on_retry", "on_status"})
EDGE_ROLES = frozenset({"then", "else", "loop"})
EDGE_KINDS = frozenset({"if", "forward", "back", "result_is"})
MAX_STEPS = 64
DEFAULT_EDGE_LIMIT = 3
MAX_VISITS_PER_NODE = DEFAULT_EDGE_LIMIT
FLOW_TYPES = frozenset({"sequence", "agent", "if", "loop"})


def default_pipeline_graph() -> dict[str, Any]:
    """Linear remaining pipeline agents plus sql_guardian → code_builder retry edge."""
    flow = default_pipeline_flow()
    return compile_pipeline_flow(flow)


def default_pipeline_flow() -> dict[str, Any]:
    metas = [
        meta
        for meta in get_all_agent_metas()
        if meta.get("builtin") or meta["id"] in AGENT_BY_ID
    ]
    if not metas:
        metas = list(get_all_agent_metas())
    ids = [meta["id"] for meta in metas]
    children: list[dict[str, Any]] = []
    i = 0
    while i < len(ids):
        if (
            i + 1 < len(ids)
            and ids[i] == "code_builder"
            and ids[i + 1] == "sql_guardian"
        ):
            children.append(
                {
                    "type": "loop",
                    "id": "loop_default_retry",
                    "when": {"type": "on_retry"},
                    "limit": DEFAULT_EDGE_LIMIT,
                    "body": {
                        "type": "sequence",
                        "children": [
                            {"type": "agent", "id": "code_builder"},
                            {"type": "agent", "id": "sql_guardian"},
                        ],
                    },
                }
            )
            i += 2
            continue
        children.append({"type": "agent", "id": ids[i]})
        i += 1
    return {"type": "sequence", "children": children}


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


def _optional_role(raw: Any) -> str | None:
    if not isinstance(raw, dict):
        return None
    role = raw.get("role")
    if role is None or role == "":
        return None
    role = str(role).strip().lower()
    if role not in EDGE_ROLES:
        raise ValueError(f"Invalid edge role: {role}")
    return role


def _optional_max_visits(raw: Any) -> int | None:
    return _optional_limit(raw)


def _optional_limit(raw: Any) -> int | None:
    if not isinstance(raw, dict):
        return None
    value = raw.get("limit")
    if value is None:
        value = raw.get("max_visits")
    if value is None:
        value = raw.get("forward_limit")
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit must be an integer") from exc
    if parsed < 1:
        raise ValueError("limit must be >= 1")
    return parsed


def _infer_kind(entry: dict[str, Any], when: dict[str, Any], role: str | None) -> str:
    raw = str(entry.get("kind") or "").strip().lower()
    if raw:
        if raw not in EDGE_KINDS:
            raise ValueError(f"Invalid edge kind: {raw}")
        return raw
    if role == "loop" or when.get("type") == "on_retry":
        return "back"
    if when.get("type") == "on_status":
        return "result_is"
    if role in ("then", "else"):
        return "if"
    return "forward"


def _kind_for_if(when: dict[str, Any] | None, role: str) -> str:
    if role == "then" and (when or {}).get("type") == "on_status":
        return "result_is"
    return "if"


def _default_edge_id(
    kind: str,
    source: str,
    target: str,
    index: int,
    role: str | None = None,
) -> str:
    if kind == "forward":
        return f"e_fwd_{source}_{target}"
    if kind == "back":
        return f"e_back_{source}_{target}"
    if kind == "result_is":
        return f"e_result_{source}_{target}"
    branch = role if role in ("then", "else") else str(index)
    return f"e_if_{source}_{target}_{branch}"


def edge_limit(edge: dict[str, Any] | None) -> int:
    if not edge:
        return DEFAULT_EDGE_LIMIT
    value = edge.get("limit")
    if value is None:
        value = edge.get("max_visits")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_EDGE_LIMIT
    return parsed if parsed >= 1 else DEFAULT_EDGE_LIMIT


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
        when = _normalize_when(entry.get("when"))
        role = _optional_role(entry)
        kind = _infer_kind(entry, when, role)
        limit = _optional_limit(entry)
        if limit is None:
            limit = DEFAULT_EDGE_LIMIT
        direction = str(entry.get("direction") or "").strip().lower()
        if direction not in ("forward", "back"):
            direction = "back" if kind == "back" else "forward"
        edge_id = str(entry.get("id") or "").strip()
        if not edge_id:
            edge_id = _default_edge_id(kind, source, target, i, role)
        if edge_id in edge_ids:
            raise ValueError(f"Duplicate edge id: {edge_id}")
        edge_ids.add(edge_id)
        item: dict[str, Any] = {
            "id": edge_id,
            "source": source,
            "target": target,
            "direction": direction,
            "kind": kind,
            "when": when,
            "limit": limit,
        }
        if role:
            item["role"] = role
        edges.append(item)

    entry = payload.get("entry")
    if entry is not None:
        entry = str(entry).strip()
        if entry and entry not in node_ids:
            raise ValueError(f"entry must be a graph node: {entry}")
    if not entry:
        entry = _infer_entry(nodes, edges)

    return {"entry": entry, "nodes": nodes, "edges": edges}


def _empty_sequence() -> dict[str, Any]:
    return {"type": "sequence", "children": []}


def _first_agent_id(block: dict[str, Any] | None) -> str | None:
    if not block or not isinstance(block, dict):
        return None
    btype = block.get("type")
    if btype == "agent":
        return str(block.get("id") or "") or None
    if btype == "sequence":
        for child in block.get("children") or []:
            found = _first_agent_id(child)
            if found:
                return found
        return None
    if btype == "loop":
        return _first_agent_id(block.get("body"))
    if btype == "if":
        return _first_agent_id(block.get("then")) or _first_agent_id(block.get("else"))
    return None


def _collect_agent_ids(block: dict[str, Any] | None, out: list[str]) -> None:
    if not block or not isinstance(block, dict):
        return
    btype = block.get("type")
    if btype == "agent":
        aid = str(block.get("id") or "").strip()
        if aid:
            out.append(aid)
        return
    if btype == "sequence":
        for child in block.get("children") or []:
            _collect_agent_ids(child, out)
        return
    if btype == "if":
        _collect_agent_ids(block.get("then"), out)
        _collect_agent_ids(block.get("else"), out)
        return
    if btype == "loop":
        _collect_agent_ids(block.get("body"), out)


def _agent_count(block: dict[str, Any] | None) -> int:
    ids: list[str] = []
    _collect_agent_ids(block, ids)
    return len(ids)


def normalize_pipeline_flow(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload or not isinstance(payload, dict):
        return default_pipeline_flow()
    block = _normalize_block(payload, ids_seen=set(), counter={"if": 0, "loop": 0})
    if block.get("type") != "sequence":
        block = {"type": "sequence", "children": [block]}
    ids: list[str] = []
    _collect_agent_ids(block, ids)
    if not ids:
        raise ValueError("pipeline_flow must include at least one agent")
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"Duplicate agent in flow: {sorted(dupes)[0]}")
    allowed = known_agent_ids()
    for agent_id in ids:
        if agent_id not in allowed:
            raise ValueError(f"Unknown agent node: {agent_id}")
    return block


def _normalize_block(raw: Any, ids_seen: set[str], counter: dict[str, int]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Flow block must be an object")
    btype = str(raw.get("type") or "").strip().lower()
    if btype not in FLOW_TYPES:
        raise ValueError(f"Invalid flow type: {btype or '(empty)'}")
    if btype == "agent":
        agent_id = str(raw.get("id") or "").strip()
        if not agent_id:
            raise ValueError("Agent block needs id")
        out: dict[str, Any] = {"type": "agent", "id": agent_id}
        forward_limit = _optional_limit(raw)
        if forward_limit is not None:
            out["forward_limit"] = forward_limit
        return out
    if btype == "sequence":
        children_raw = raw.get("children")
        if not isinstance(children_raw, list):
            children_raw = []
        children = [_normalize_block(child, ids_seen, counter) for child in children_raw]
        return {"type": "sequence", "children": children}
    if btype == "if":
        counter["if"] += 1
        block_id = str(raw.get("id") or f"if_{counter['if']}").strip()
        then_block = _normalize_block(raw.get("then") or _empty_sequence(), ids_seen, counter)
        else_block = _normalize_block(raw.get("else") or _empty_sequence(), ids_seen, counter)
        if then_block.get("type") != "sequence":
            then_block = {"type": "sequence", "children": [then_block]}
        if else_block.get("type") != "sequence":
            else_block = {"type": "sequence", "children": [else_block]}
        then_n = _agent_count(then_block)
        else_n = _agent_count(else_block)
        if then_n == 0 and else_n > 0:
            raise ValueError("If / Else needs a Then branch when Else is filled")
        limit = _optional_limit(raw)
        if_block: dict[str, Any] = {
            "type": "if",
            "id": block_id,
            "when": _normalize_when(raw.get("when")),
            "then": then_block,
            "else": else_block,
        }
        if limit is not None:
            if_block["limit"] = limit
        return if_block
    counter["loop"] += 1
    block_id = str(raw.get("id") or f"loop_{counter['loop']}").strip()
    body = _normalize_block(raw.get("body") or _empty_sequence(), ids_seen, counter)
    if body.get("type") != "sequence":
        body = {"type": "sequence", "children": [body]}
    if _agent_count(body) == 0:
        raise ValueError("Loop needs at least one agent in its body")
    limit = _optional_limit(raw)
    if limit is None:
        limit = DEFAULT_EDGE_LIMIT
    return {
        "type": "loop",
        "id": block_id,
        "when": _normalize_when(raw.get("when") or {"type": "on_retry"}),
        "limit": limit,
        "body": body,
    }


def compile_pipeline_flow(
    flow: dict[str, Any],
    positions: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    flow = normalize_pipeline_flow(flow)
    compiler = _FlowCompiler(positions or {})
    exits = compiler.compile_seq(flow, incoming=[])
    if not compiler.nodes:
        raise ValueError("pipeline_flow must include at least one agent")
    entry = _first_agent_id(flow) or compiler.nodes[0]["id"]
    _ = exits
    return {"entry": entry, "nodes": compiler.nodes, "edges": compiler.edges}


class _FlowCompiler:
    def __init__(self, positions: dict[str, dict[str, float]]) -> None:
        self.positions = positions
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self.seen: set[str] = set()
        self.y = 0.0
        self.edge_ids: set[str] = set()

    def add_agent(self, agent_id: str, depth: int) -> None:
        if agent_id in self.seen:
            raise ValueError(f"Duplicate node id: {agent_id}")
        self.seen.add(agent_id)
        pos = self.positions.get(agent_id)
        if not pos:
            pos = {"x": float(depth * 48), "y": self.y}
        self.y = max(self.y, pos["y"] + 100)
        self.nodes.append({"id": agent_id, "position": {"x": pos["x"], "y": pos["y"]}})

    def add_edge(
        self,
        source: str,
        target: str,
        when: dict[str, Any],
        role: str | None = None,
        limit: int | None = None,
        kind: str | None = None,
        edge_id: str | None = None,
    ) -> None:
        when = when or {"type": "always"}
        kind = kind or _infer_kind({"kind": kind, "role": role}, when, role)
        cap = int(limit) if limit is not None else DEFAULT_EDGE_LIMIT
        if cap < 1:
            cap = DEFAULT_EDGE_LIMIT
        eid = (edge_id or "").strip() or _default_edge_id(kind, source, target, len(self.edges), role)
        if eid in self.edge_ids:
            eid = f"{eid}_{len(self.edges)}"
        self.edge_ids.add(eid)
        item: dict[str, Any] = {
            "id": eid,
            "source": source,
            "target": target,
            "direction": "back" if kind == "back" else "forward",
            "kind": kind,
            "when": when,
            "limit": cap,
        }
        if role:
            item["role"] = role
        self.edges.append(item)

    def connect_incoming(
        self,
        incoming: list[dict[str, Any]],
        target: str,
        depth: int,
    ) -> None:
        _ = depth
        for item in incoming:
            role = item.get("role")
            when = item.get("when") or {"type": "always"}
            kind = item.get("kind") or _infer_kind(item, when, role)
            block_id = item.get("block_id")
            edge_id = item.get("id")
            if not edge_id:
                if kind == "forward":
                    edge_id = f"e_fwd_{item['source']}_{target}"
                elif kind == "back":
                    edge_id = f"e_back_{block_id or item['source']}"
                elif kind == "result_is":
                    edge_id = (
                        f"e_result_{block_id}_{role}"
                        if block_id
                        else f"e_result_{item['source']}_{target}"
                    )
                elif kind == "if" and block_id and role in ("then", "else"):
                    edge_id = f"e_if_{block_id}_{role}"
                else:
                    edge_id = _default_edge_id(kind, item["source"], target, len(self.edges), role)
            self.add_edge(
                item["source"],
                target,
                when,
                role=role,
                limit=item.get("limit"),
                kind=kind,
                edge_id=edge_id,
            )

    def compile_seq(
        self,
        seq: dict[str, Any],
        incoming: list[dict[str, Any]],
        depth: int = 0,
    ) -> list[dict[str, Any]]:
        exits = incoming
        children = seq.get("children") or []
        for child in children:
            ctype = child.get("type")
            if ctype == "agent":
                self.add_agent(child["id"], depth)
                self.connect_incoming(exits, child["id"], depth)
                fwd_limit = child.get("forward_limit")
                if fwd_limit is None:
                    fwd_limit = DEFAULT_EDGE_LIMIT
                exits = [
                    {
                        "source": child["id"],
                        "when": {"type": "always"},
                        "kind": "forward",
                        "limit": int(fwd_limit),
                    }
                ]
            elif ctype == "if":
                if not exits:
                    raise ValueError("If / Else needs an agent before it")
                then_n = _agent_count(child.get("then"))
                else_n = _agent_count(child.get("else"))
                if then_n == 0 and else_n == 0:
                    continue
                if_when = child.get("when") or {"type": "always"}
                if_limit = child.get("limit")
                if if_limit is None:
                    if_limit = DEFAULT_EDGE_LIMIT
                then_kind = _kind_for_if(if_when, "then")
                then_in = [
                    {
                        "source": item["source"],
                        "when": if_when,
                        "role": "then",
                        "kind": then_kind,
                        "limit": int(if_limit),
                        "block_id": child.get("id"),
                        "id": (
                            f"e_result_{child.get('id')}_then"
                            if then_kind == "result_is"
                            else f"e_if_{child.get('id')}_then"
                        ),
                    }
                    for item in exits
                ]
                else_in = [
                    {
                        "source": item["source"],
                        "when": {"type": "always"},
                        "role": "else",
                        "kind": "if",
                        "limit": int(if_limit),
                        "block_id": child.get("id"),
                        "id": f"e_if_{child.get('id')}_else",
                    }
                    for item in exits
                ]
                then_exits = self.compile_seq(child.get("then") or _empty_sequence(), then_in, depth + 1)
                else_exits = (
                    self.compile_seq(child.get("else") or _empty_sequence(), else_in, depth + 1)
                    if else_n
                    else []
                )
                exits = then_exits + else_exits
            elif ctype == "loop":
                body = child.get("body") or _empty_sequence()
                first = _first_agent_id(body)
                if not first:
                    raise ValueError("Loop needs at least one agent in its body")
                body_exits = self.compile_seq(body, exits, depth + 1)
                last_ids = []
                for item in body_exits:
                    src = item.get("source")
                    if src and src not in last_ids:
                        last_ids.append(src)
                loop_limit = child.get("limit")
                if loop_limit is None:
                    loop_limit = child.get("max_visits") or DEFAULT_EDGE_LIMIT
                for last in last_ids:
                    back_id = (
                        f"e_back_{child.get('id')}"
                        if len(last_ids) == 1
                        else f"e_back_{child.get('id')}_{last}"
                    )
                    self.add_edge(
                        last,
                        first,
                        child.get("when") or {"type": "on_retry"},
                        role="loop",
                        limit=int(loop_limit),
                        kind="back",
                        edge_id=back_id,
                    )
                exits = body_exits
        return exits


def _when_key(when: dict[str, Any] | None) -> tuple[str, str]:
    when = when or {}
    return (str(when.get("type") or "always"), str(when.get("status") or ""))


def _topology(graph: dict[str, Any]) -> set[tuple[str, str, str, str]]:
    return {
        (e["source"], e["target"], *_when_key(e.get("when")))
        for e in graph.get("edges") or []
    }


def infer_pipeline_flow(graph: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Best-effort structured flow from a graph. None if Arrange cannot represent it."""
    try:
        graph = normalize_pipeline_graph(graph)
        flow = _infer_from_spine(graph)
        compiled = compile_pipeline_flow(
            flow,
            {n["id"]: n["position"] for n in graph.get("nodes") or []},
        )
        if {n["id"] for n in compiled["nodes"]} != {n["id"] for n in graph["nodes"]}:
            return None, "Arrange needs a single Then/Else per If."
        if _topology(compiled) != _topology(graph):
            return None, "Arrange needs a single Then/Else per If."
        return flow, None
    except (ValueError, KeyError, TypeError) as exc:
        return None, str(exc) or "Arrange needs a single Then/Else per If."


def _infer_from_spine(graph: dict[str, Any]) -> dict[str, Any]:
    node_ids = [n["id"] for n in graph.get("nodes") or []]
    if not node_ids:
        raise ValueError("pipeline_graph.nodes must include at least one agent")
    outgoing: dict[str, list[dict[str, Any]]] = {nid: [] for nid in node_ids}
    incoming_count: dict[str, int] = {nid: 0 for nid in node_ids}
    for edge in graph.get("edges") or []:
        outgoing[edge["source"]].append(edge)
        incoming_count[edge["target"]] = incoming_count.get(edge["target"], 0) + 1

    entry = graph.get("entry") or node_ids[0]
    used_edges: set[str] = set()

    def take_forwards(source: str) -> list[dict[str, Any]]:
        found = []
        for edge in outgoing.get(source) or []:
            if edge["id"] in used_edges:
                continue
            role = edge.get("role")
            kind = edge.get("kind")
            wtype = (edge.get("when") or {}).get("type")
            if kind == "back" or role == "loop" or wtype == "on_retry":
                continue
            found.append(edge)
        return found

    def take_loops(source: str) -> list[dict[str, Any]]:
        found = []
        for edge in outgoing.get(source) or []:
            if edge["id"] in used_edges:
                continue
            role = edge.get("role")
            kind = edge.get("kind")
            wtype = (edge.get("when") or {}).get("type")
            if kind == "back" or role == "loop" or wtype == "on_retry":
                found.append(edge)
        return found

    loop_counter = 0
    if_counter = 0

    def parse_until(start: str | None, stops: set[str], depth: int = 0) -> tuple[list[dict[str, Any]], str | None]:
        nonlocal loop_counter, if_counter
        children: list[dict[str, Any]] = []
        current = start
        seen_local: set[str] = set()
        while current and current not in stops:
            if current in seen_local:
                raise ValueError("Arrange needs a single Then/Else per If.")
            seen_local.add(current)
            children.append({"type": "agent", "id": current})
            loops = take_loops(current)
            forwards = take_forwards(current)
            then_edges = [
                e for e in forwards if e.get("role") == "then" or e.get("kind") in ("if", "result_is")
            ]
            else_edges = [e for e in forwards if e.get("role") == "else"]
            then_edges = [e for e in then_edges if e not in else_edges]
            fail_edges = [
                e
                for e in forwards
                if (e.get("when") or {}).get("type") == "on_failure" and e.get("role") not in ("then", "else")
            ]
            always_edges = [
                e
                for e in forwards
                if e not in then_edges
                and e not in else_edges
                and e not in fail_edges
            ]

            if loops and len(loops) > 1:
                raise ValueError("Arrange needs a single Then/Else per If.")
            if loops:
                back = loops[0]
                used_edges.add(back["id"])
                target = back["target"]
                if target not in [c.get("id") for c in children if c.get("type") == "agent"]:
                    raise ValueError("Arrange needs a single Then/Else per If.")
                # Wrap from target agent through current as a loop.
                start_idx = next(
                    i
                    for i, c in enumerate(children)
                    if c.get("type") == "agent" and c.get("id") == target
                )
                body_children = children[start_idx:]
                children = children[:start_idx]
                loop_counter += 1
                children.append(
                    {
                        "type": "loop",
                        "id": f"loop_{loop_counter}",
                        "when": deepcopy(back.get("when") or {"type": "on_retry"}),
                        "limit": edge_limit(back),
                        "body": {"type": "sequence", "children": body_children},
                    }
                )

            branch_then = then_edges or fail_edges
            branch_else = else_edges
            if not branch_then and not branch_else and len(always_edges) > 1:
                raise ValueError("Arrange needs a single Then/Else per If.")
            if branch_then or (len(always_edges) + len(fail_edges) > 1 and fail_edges):
                if len(branch_then) > 1 or len(branch_else) > 1:
                    raise ValueError("Arrange needs a single Then/Else per If.")
                then_edge = branch_then[0] if branch_then else None
                else_edge = branch_else[0] if branch_else else None
                leftover_always = [
                    e
                    for e in always_edges
                    if (not else_edge or e["id"] != else_edge["id"])
                    and (not then_edge or e["id"] != then_edge["id"])
                ]
                if not else_edge and leftover_always:
                    else_edge = leftover_always[0]
                    leftover_always = leftover_always[1:]
                if leftover_always:
                    raise ValueError("Arrange needs a single Then/Else per If.")
                then_target = then_edge["target"] if then_edge else None
                else_target = else_edge["target"] if else_edge else None
                if then_edge:
                    used_edges.add(then_edge["id"])
                if else_edge:
                    used_edges.add(else_edge["id"])
                join = _find_join(then_target, else_target, outgoing, node_ids)
                then_children, _ = parse_until(then_target, {join} if join else set(), depth + 1) if then_target else ([], None)
                else_children, _ = parse_until(else_target, {join} if join else set(), depth + 1) if else_target else ([], None)
                if_counter += 1
                when = deepcopy((then_edge or {}).get("when") or {"type": "on_failure"})
                then_id = str((then_edge or {}).get("id") or "")
                if_id = f"if_{if_counter}"
                if then_id.startswith("e_if_") and then_id.endswith("_then"):
                    if_id = then_id[len("e_if_") : -len("_then")]
                elif then_id.startswith("e_result_") and then_id.endswith("_then"):
                    if_id = then_id[len("e_result_") : -len("_then")]
                if_block: dict[str, Any] = {
                    "type": "if",
                    "id": if_id,
                    "when": when,
                    "then": {"type": "sequence", "children": then_children},
                    "else": {"type": "sequence", "children": else_children},
                }
                cap = edge_limit(then_edge or else_edge)
                if cap != DEFAULT_EDGE_LIMIT:
                    if_block["limit"] = cap
                children.append(if_block)
                current = join
                continue

            if len(always_edges) == 1:
                used_edges.add(always_edges[0]["id"])
                cap = edge_limit(always_edges[0])
                if children and children[-1].get("type") == "agent" and cap != DEFAULT_EDGE_LIMIT:
                    children[-1]["forward_limit"] = cap
                current = always_edges[0]["target"]
                continue
            if not always_edges:
                current = None
                continue
            raise ValueError("Arrange needs a single Then/Else per If.")
        return children, current

    children, _ = parse_until(entry, set())
    unused = [e for e in graph.get("edges") or [] if e["id"] not in used_edges]
    if unused:
        raise ValueError("Arrange needs a single Then/Else per If.")
    covered: list[str] = []
    flow = {"type": "sequence", "children": children}
    _collect_agent_ids(flow, covered)
    if set(covered) != set(node_ids):
        raise ValueError("Arrange needs a single Then/Else per If.")
    return flow


def _find_join(
    then_start: str | None,
    else_start: str | None,
    outgoing: dict[str, list[dict[str, Any]]],
    node_ids: list[str],
) -> str | None:
    def reachable(start: str | None) -> set[str]:
        if not start:
            return set()
        seen: set[str] = set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            for edge in outgoing.get(node) or []:
                role = edge.get("role")
                kind = edge.get("kind")
                wtype = (edge.get("when") or {}).get("type")
                if kind == "back" or role == "loop" or wtype == "on_retry":
                    continue
                stack.append(edge["target"])
        return seen

    then_r = reachable(then_start)
    else_r = reachable(else_start)
    if not then_start:
        return else_start
    if not else_start:
        return then_start
    both = then_r & else_r
    if not both:
        return None
    for nid in node_ids:
        if nid in both:
            return nid
    return next(iter(both), None)


def _infer_entry(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> str | None:
    targets = {e["target"] for e in edges if e.get("when", {}).get("type") in ("always", "on_success")}
    for node in nodes:
        if node["id"] not in targets:
            return node["id"]
    return nodes[0]["id"] if nodes else None


def _positions_from_graph(graph: dict[str, Any] | None) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    if not graph or not isinstance(graph, dict):
        return out
    for node in graph.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("id") or "").strip()
        pos = node.get("position") if isinstance(node.get("position"), dict) else {}
        if nid:
            try:
                out[nid] = {"x": float(pos.get("x", 0)), "y": float(pos.get("y", 0))}
            except (TypeError, ValueError):
                out[nid] = {"x": 0.0, "y": 0.0}
    return out


def get_pipeline_bundle() -> dict[str, Any]:
    data = load_config()
    raw_graph = data.get("pipeline_graph")
    raw_flow = data.get("pipeline_flow")
    graph: dict[str, Any]
    flow: dict[str, Any] | None
    arrange_error: str | None = None

    if isinstance(raw_graph, dict) and raw_graph.get("nodes"):
        try:
            graph = normalize_pipeline_graph(raw_graph)
        except ValueError:
            graph = default_pipeline_graph()
            flow = default_pipeline_flow()
            return {
                "pipeline_graph": graph,
                "pipeline_flow": flow,
                "arrange_compatible": True,
                "arrange_error": None,
            }
    else:
        flow = default_pipeline_flow()
        graph = compile_pipeline_flow(flow)
        return {
            "pipeline_graph": graph,
            "pipeline_flow": flow,
            "arrange_compatible": True,
            "arrange_error": None,
        }

    if isinstance(raw_flow, dict) and raw_flow.get("type"):
        try:
            flow = normalize_pipeline_flow(raw_flow)
            compiled = compile_pipeline_flow(flow, _positions_from_graph(graph))
            if {n["id"] for n in compiled["nodes"]} == {n["id"] for n in graph["nodes"]}:
                graph = {
                    "entry": compiled["entry"],
                    "nodes": [
                        {
                            "id": n["id"],
                            "position": next(
                                (g["position"] for g in graph["nodes"] if g["id"] == n["id"]),
                                n["position"],
                            ),
                        }
                        for n in compiled["nodes"]
                    ],
                    "edges": compiled["edges"],
                }
            else:
                inferred, err = infer_pipeline_flow(graph)
                flow, arrange_error = inferred, err
        except ValueError as exc:
            inferred, err = infer_pipeline_flow(graph)
            flow, arrange_error = inferred, err or str(exc)
    else:
        inferred, err = infer_pipeline_flow(graph)
        flow, arrange_error = inferred, err

    return {
        "pipeline_graph": graph,
        "pipeline_flow": flow,
        "arrange_compatible": flow is not None and not arrange_error,
        "arrange_error": arrange_error,
    }


def get_pipeline_graph() -> dict[str, Any]:
    return get_pipeline_bundle()["pipeline_graph"]


def get_pipeline_flow() -> dict[str, Any] | None:
    return get_pipeline_bundle().get("pipeline_flow")


def update_pipeline_bundle(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    data = load_config()
    raw_flow = payload.get("pipeline_flow")
    raw_graph = payload.get("pipeline_graph")
    if raw_flow is None and isinstance(payload.get("type"), str):
        raw_flow = payload
    if raw_graph is None and isinstance(payload.get("nodes"), list):
        raw_graph = payload

    positions = _positions_from_graph(raw_graph if isinstance(raw_graph, dict) else None)

    if isinstance(raw_flow, dict) and raw_flow.get("type"):
        flow = normalize_pipeline_flow(raw_flow)
        graph = compile_pipeline_flow(flow, positions)
        data["pipeline_flow"] = deepcopy(flow)
        data["pipeline_graph"] = deepcopy(graph)
        save_config(data)
        return {
            "pipeline_graph": graph,
            "pipeline_flow": flow,
            "arrange_compatible": True,
            "arrange_error": None,
        }

    if isinstance(raw_graph, dict):
        graph = normalize_pipeline_graph(raw_graph)
        flow, err = infer_pipeline_flow(graph)
        data["pipeline_graph"] = deepcopy(graph)
        data["pipeline_flow"] = deepcopy(flow) if flow else None
        save_config(data)
        return {
            "pipeline_graph": graph,
            "pipeline_flow": flow,
            "arrange_compatible": flow is not None and not err,
            "arrange_error": err,
        }

    raise ValueError("Provide pipeline_flow or pipeline_graph")


def update_pipeline_graph(payload: dict[str, Any]) -> dict[str, Any]:
    bundle = update_pipeline_bundle({"pipeline_graph": payload})
    return bundle["pipeline_graph"]


def reset_pipeline_graph() -> dict[str, Any]:
    flow = default_pipeline_flow()
    graph = compile_pipeline_flow(flow)
    data = load_config()
    data["pipeline_graph"] = deepcopy(graph)
    data["pipeline_flow"] = deepcopy(flow)
    save_config(data)
    return graph


def reset_pipeline_bundle() -> dict[str, Any]:
    reset_pipeline_graph()
    return get_pipeline_bundle()


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


def next_edge(
    graph: dict[str, Any],
    source_id: str,
    status: str,
    edge_uses: dict[str, int] | None = None,
) -> dict[str, Any] | None:
    """First matching outgoing edge that is still under its limit."""
    uses = edge_uses or {}
    for edge in graph.get("edges") or []:
        if edge.get("source") != source_id:
            continue
        if not edge_matches(edge.get("when") or {}, status):
            continue
        used = int(uses.get(str(edge.get("id") or ""), 0))
        if used >= edge_limit(edge):
            continue
        return edge
    return None


def circuit_open_edge(
    graph: dict[str, Any],
    source_id: str,
    status: str,
    edge_uses: dict[str, int] | None = None,
) -> dict[str, Any] | None:
    """Matching edge that was skipped because its circuit is open."""
    uses = edge_uses or {}
    for edge in graph.get("edges") or []:
        if edge.get("source") != source_id:
            continue
        if not edge_matches(edge.get("when") or {}, status):
            continue
        used = int(uses.get(str(edge.get("id") or ""), 0))
        if used >= edge_limit(edge):
            return edge
    return None


def next_targets(
    graph: dict[str, Any], source_id: str, status: str
) -> list[str]:
    """First matching outgoing edge wins (edges kept in saved order)."""
    edge = next_edge(graph, source_id, status, {})
    if edge:
        return [edge["target"]]
    return []


def visit_cap_for(graph: dict[str, Any], node_id: str) -> int:
    caps = [
        edge_limit(edge)
        for edge in graph.get("edges") or []
        if (edge.get("source") == node_id or edge.get("target") == node_id)
        and (edge.get("kind") == "back" or edge.get("role") == "loop")
    ]
    return max(caps) if caps else DEFAULT_EDGE_LIMIT


def agent_display_name(agent_id: str) -> str:
    names = get_agent_display_names()
    if agent_id in names:
        return names[agent_id]
    meta = AGENT_BY_ID.get(agent_id)
    if meta:
        return meta["name"]
    return agent_id.replace("_", " ").title()
