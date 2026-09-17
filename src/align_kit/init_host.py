"""Host integration: AGENTS.md marked block and skill copies (idempotent)."""

from __future__ import annotations

import re
from pathlib import Path

from . import __version__

SKILLS_DIR = Path(__file__).parent / "skills"
SKILL_NAMES = ("aligning-changes", "detecting-conflicts", "resolving-conflicts")
HOSTS = ("codex", "claude")
BLOCK_END = "<!-- align-kit:end -->"

AGENTS_BODY = """\
## Alignment layer (align-kit)

`artifacts/` holds the entry repository: one markdown file per entry (REQ/TASK/PLAN/CON/RAT), YAML frontmatter, schema v0.

- When the user changes a requirement or asks to sync/align artifacts, follow the `aligning-changes` skill in `.agents/skills/aligning-changes/SKILL.md`.
- Run the deterministic CLI before announcing completion: `align index`, `align impact <ID>`, `align detect`, `align verify` (via `uvx align`, or `uv run align` inside the align-kit checkout).
- Fix or explicitly resolve with the user every CRITICAL/HIGH detect finding before completion. Evidence before declaration: paste the `align verify` summary.
"""

CLAUDE_COMMAND = """\
---
description: Align a requirement change across artifacts (align-kit)
---

Follow the `aligning-changes` skill (`.claude/skills/aligning-changes/SKILL.md`) end to end: index the repository, compute impact for the changed entries, route and edit every impacted artifact, run `align detect` plus the detecting-conflicts checklist, resolve conflicts with the user via resolving-conflicts when needed, run `align verify`, and report the verify summary as evidence before declaring completion.
"""

_BLOCK_PATTERN = re.compile(r"<!-- align-kit:begin [^>]*-->.*?<!-- align-kit:end -->\n?", re.DOTALL)


def agents_block() -> str:
    header = f"<!-- align-kit:begin v{__version__} -->"
    return f"{header}\n{AGENTS_BODY}{BLOCK_END}\n"


def upsert_agents_block(existing: str) -> str:
    """Replace any existing align-kit block with the current one (idempotent)."""
    text = _BLOCK_PATTERN.sub("", existing).rstrip("\n")
    block = agents_block().rstrip("\n")
    if not text.strip():
        return block + "\n"
    return f"{text}\n\n{block}\n"


def strip_agents_block(existing: str) -> tuple[str, bool]:
    """Remove the align-kit block; return (new_text, whether_removed)."""
    new_text, count = _BLOCK_PATTERN.subn("", existing)
    if count == 0:
        return existing, False
    cleaned = new_text.strip("\n")
    return (cleaned + "\n" if cleaned else ""), True


def skill_source_dir(name: str) -> Path:
    return SKILLS_DIR / name


def skill_source_text(name: str) -> str:
    return (skill_source_dir(name) / "SKILL.md").read_text(encoding="utf-8")


def thin_shell(skill_text: str, name: str) -> str:
    """A .claude/skills mirror that keeps the frontmatter and points at .agents."""
    parts = skill_text.split("---", 2)
    frontmatter = ""
    if len(parts) == 3 and parts[0].strip() == "":
        frontmatter = f"---{parts[1]}---"
    body = (
        f"This is a thin mirror of `.agents/skills/{name}/SKILL.md`.\n\n"
        "Read that file now and follow it as written.\n"
    )
    return f"{frontmatter}\n{body}" if frontmatter else body


def managed_paths(root: Path, host: str) -> dict[Path, str]:
    """Map of files init writes -> the exact content init writes."""
    mapping: dict[Path, str] = {}
    for name in SKILL_NAMES:
        mapping[root / ".agents" / "skills" / name / "SKILL.md"] = skill_source_text(name)
        if host == "claude":
            mapping[root / ".claude" / "skills" / name / "SKILL.md"] = thin_shell(skill_source_text(name), name)
    if host == "claude":
        mapping[root / ".claude" / "commands" / "align.md"] = CLAUDE_COMMAND
    return mapping


def run_init(root: Path, host: str, remove: bool = False, dry_run: bool = False) -> list[str]:
    """Install or remove align-kit host integration; return a list of action lines."""
    if host not in HOSTS:
        raise ValueError(f"unknown host {host!r} (expected one of {', '.join(HOSTS)})")
    actions: list[str] = []
    agents = root / "AGENTS.md"

    if remove:
        if agents.is_file():
            new_text, changed = strip_agents_block(agents.read_text(encoding="utf-8"))
            if changed:
                actions.append("strip align-kit block from AGENTS.md")
                if not dry_run:
                    agents.write_text(new_text, encoding="utf-8")
        for path, expected in managed_paths(root, host).items():
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if path.read_text(encoding="utf-8") != expected:
                actions.append(f"skip {rel} (modified by user, not removing)")
                continue
            actions.append(f"remove {rel}")
            if not dry_run:
                path.unlink()
        return actions

    current = agents.read_text(encoding="utf-8") if agents.is_file() else ""
    new_text = upsert_agents_block(current)
    if new_text == current:
        actions.append("AGENTS.md block already up to date")
    else:
        actions.append("create AGENTS.md" if not agents.is_file() else "upsert align-kit block in AGENTS.md")
        if not dry_run:
            agents.write_text(new_text, encoding="utf-8")

    for path, content in managed_paths(root, host).items():
        rel = path.relative_to(root).as_posix()
        if path.is_file() and path.read_text(encoding="utf-8") == content:
            actions.append(f"{rel} already up to date")
            continue
        actions.append(f"write {rel}")
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    return actions
