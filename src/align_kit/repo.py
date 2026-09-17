"""Loading and parsing of artifact entry files."""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import Entry


def parse_entry_file(path: Path) -> Entry:
    """Parse one markdown entry file: YAML frontmatter + markdown body."""
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3 or parts[0].strip() != "":
        raise ValueError(f"{path}: missing YAML frontmatter (file must start with '---')")
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid frontmatter YAML: {exc}") from exc
    if not isinstance(meta, dict):
        raise ValueError(f"{path}: frontmatter must be a YAML mapping")
    meta["path"] = path
    meta["body"] = parts[2]
    try:
        return Entry(**meta)
    except Exception as exc:
        raise ValueError(f"{path}: {exc}") from exc


def load_entries(project_root: Path) -> list[Entry]:
    """Load every artifacts/**/*.md entry under the project root."""
    artifacts_dir = project_root / "artifacts"
    if not artifacts_dir.is_dir():
        raise ValueError(f"{artifacts_dir.as_posix()}: artifacts directory not found")
    return [parse_entry_file(path) for path in sorted(artifacts_dir.rglob("*.md"))]
