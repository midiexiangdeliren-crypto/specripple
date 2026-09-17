"""Build the derived index.json artifact."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Entry

SCHEMA_VERSION = 1
INDEX_FILENAME = "index.json"


def _summary(body: str) -> str:
    """First non-heading, non-empty body line, truncated to 100 chars."""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:100]
    return ""


def build_index(entries: list[Entry]) -> dict:
    """Build a deterministic index payload from parsed entries."""
    ids = [entry.id for entry in entries]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate artifact ids: {', '.join(duplicates)}")

    ordered = sorted(entries, key=lambda entry: entry.id)
    entries_payload = [
        {
            "id": entry.id,
            "type": entry.type.value,
            "title": entry.title,
            "status": entry.status.value,
            "path": entry.path.as_posix(),
            "summary": _summary(entry.body),
        }
        for entry in ordered
    ]
    adjacency: dict[str, list[str]] = {}
    for entry in ordered:
        targets = set(entry.depends_on) | {link.to for link in entry.links}
        adjacency[entry.id] = sorted(targets)
    return {
        "schema_version": SCHEMA_VERSION,
        "entries": entries_payload,
        "adjacency": adjacency,
    }


def write_index(index: dict, project_root: Path) -> Path:
    """Write index.json deterministically (stable key order, trailing newline)."""
    out = project_root / INDEX_FILENAME
    out.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out
