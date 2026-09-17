"""Impact analysis: BFS closure over outgoing links and reverse dependencies."""

from __future__ import annotations

from collections import deque

from .models import Entry

REVERSE_DEP_EDGE = "depended-on-by"


def compute_impact(entries: list[Entry], root_id: str) -> dict:
    """Return the transitive impact set of changing ``root_id``.

    Edges: every ``links[].to`` target (outgoing) plus every entry listing
    this one in its ``depends_on`` (reverse dependency, edge name
    ``depended-on-by``). Dangling targets are reported under ``unresolved``.
    """
    by_id = {entry.id: entry for entry in entries}
    if root_id not in by_id:
        raise KeyError(f"unknown artifact id: {root_id}")

    dependents: dict[str, list[str]] = {}
    for entry in entries:
        for dep in entry.depends_on:
            dependents.setdefault(dep, []).append(entry.id)

    def successors(entry: Entry) -> list[tuple[str, str]]:
        out = [(link.to, link.kind.value) for link in entry.links]
        out.extend((dep, REVERSE_DEP_EDGE) for dep in sorted(dependents.get(entry.id, [])))
        return out

    visited: dict[str, dict] = {}
    unresolved: set[str] = set()
    queue: deque[tuple[str, list[str], list[str]]] = deque()
    queue.append((root_id, [root_id], []))
    while queue:
        node_id, path, edges = queue.popleft()
        if node_id in visited:
            continue
        entry = by_id.get(node_id)
        if entry is None:
            unresolved.add(node_id)
            continue
        visited[node_id] = {"id": node_id, "path": path, "edges": edges, "depth": len(path) - 1}
        for target, edge in successors(entry):
            if target != node_id:
                queue.append((target, path + [target], edges + [edge]))

    impacts = sorted(
        (node for node in visited.values() if node["id"] != root_id),
        key=lambda node: node["id"],
    )
    return {"root": root_id, "impacts": impacts, "unresolved": sorted(unresolved)}
