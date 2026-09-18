"""Import Spec Kit artifacts (spec/plan/tasks/constitution) into the entry repository."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .index_build import build_index
from .repo import load_entries

SPECKIT_FILES = ("spec", "plan", "tasks", "constitution")

_STORY_HEADING = re.compile(r"^###\s+User Story\s+(\d+)\s*[-\u2013\u2014:]\s*(.+?)\s*$")
_PRIORITY = re.compile(r"\(Priority:\s*P(\d)\)")
_H123 = re.compile(r"^#{1,3}\s")
_H12 = re.compile(r"^#{1,2}\s")
_ACCEPTANCE_HEADING = re.compile(r"^#{2,4}\s*Acceptance Scenarios.*$")
# Official template form (github/spec-kit v1.0.8): a bold label on its own line,
# e.g. `**Acceptance Scenarios**:` — colon optional, case-insensitive.
_ACCEPTANCE_BOLD = re.compile(r"^\s*\*\*Acceptance Scenarios\*\*\s*:?\s*$", re.IGNORECASE)
_TASK_LINE = re.compile(r"^\s*-\s+\[([ xX])\]\s+(.+?)\s*$")
_TASK_CODE = re.compile(r"^(T\d+)[\s:.](.+)$")
_HEADING_STORY_CTX = re.compile(r"^#{1,4}.*User Story\s+(\d+)")
_BOLD_STORY_CTX = re.compile(r"^\*\*.*User Story\s+(\d+)")


def _first_h1(text: str) -> str | None:
    for line in text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1)
    return None


def _clean_title(raw: str) -> str:
    title = re.sub(r"^Feature:\s*", "", raw)
    title = _PRIORITY.sub("", title)
    return title.strip()


def _parse_spec(text: str) -> tuple[dict | None, list[dict]]:
    """Split spec.md into an overview entry and per-user-story entries."""
    overview_lines: list[str] = []
    stories: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        story_match = _STORY_HEADING.match(line)
        if story_match:
            current = {"num": int(story_match.group(1)), "heading": story_match.group(2), "lines": []}
            stories.append(current)
            continue
        if current is not None and _H123.match(line):
            current = None  # a new H1-H3 heading ends the story region
        if current is not None:
            current["lines"].append(line)
        else:
            overview_lines.append(line)

    for story in stories:
        priority_match = _PRIORITY.search(story["heading"])
        story["priority"] = int(priority_match.group(1)) if priority_match else 1
        story["title"] = _clean_title(story["heading"])
        story["lines"] = [
            _ACCEPTANCE_BOLD.sub("## Acceptance", _ACCEPTANCE_HEADING.sub("## Acceptance", line))
            for line in story["lines"]
        ]

    overview_body = "\n".join(overview_lines).strip("\n")
    if not overview_body:
        return None, stories
    h1 = _first_h1(overview_body)
    overview_title = _clean_title(h1) if h1 else "Specification overview"
    return {"title": overview_title or "Specification overview", "body": overview_body + "\n"}, stories


def _parse_tasks(text: str) -> list[dict]:
    """Extract checkbox tasks with their user-story context."""
    tasks: list[dict] = []
    current_story: int | None = None
    for line in text.splitlines():
        ctx = _HEADING_STORY_CTX.match(line) or _BOLD_STORY_CTX.match(line)
        if ctx:
            current_story = int(ctx.group(1))
            continue
        if ctx is None and _H12.match(line):
            current_story = None  # phase-level heading without a story resets context
            continue
        task_match = _TASK_LINE.match(line)
        if not task_match:
            continue
        checked = task_match.group(1).lower() == "x"
        rest = task_match.group(2)
        code_match = _TASK_CODE.match(rest)
        title = f"{code_match.group(1)} {code_match.group(2).strip()}" if code_match else rest
        tasks.append(
            {
                "title": title,
                "status": "done" if checked else "draft",
                "story": current_story,
                "line": line.strip(),
            }
        )
    return tasks


def _write_entry(dir_path: Path, meta: dict, body: str) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{meta['id']}.md"
    yaml_text = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=10**6).strip()
    path.write_text(f"---\n{yaml_text}\n---\n{body}", encoding="utf-8")
    return path


def import_speckit(src: Path, root: Path) -> dict:
    """Convert Spec Kit artifacts under ``src`` into entries under ``root/artifacts``.

    Mapping: spec.md overview sections -> REQ overview entry; each
    ``### User Story N`` -> REQ (P1=active, P2+=draft, ``#### Acceptance
    Scenarios`` normalized to ``## Acceptance``); tasks.md checkboxes ->
    TASK (unchecked=draft, checked=done, ``depends_on`` = owning story's
    REQ); plan.md -> PLAN-001; constitution.md -> CON-001.
    """
    src = Path(src)
    root = Path(root)
    if not src.is_dir():
        raise ValueError(f"{src.as_posix()}: source directory not found")
    present = [name for name in SPECKIT_FILES if (src / f"{name}.md").is_file()]
    if not present:
        raise ValueError(
            f"{src.as_posix()}: no spec-kit artifacts found "
            "(expected spec.md, plan.md, tasks.md, and/or constitution.md)"
        )
    artifacts = root / "artifacts"
    if artifacts.is_dir() and any(artifacts.rglob("*.md")):
        raise ValueError(
            f"{artifacts.as_posix()}: artifacts directory is not empty; refusing to import over existing entries"
        )

    created: list[dict] = []
    warnings: list[str] = []
    story_map: dict[int, str] = {}

    def add(kind_dir: str, entry_id: str, entry_type: str, title: str, status: str, depends_on: list[str], body: str) -> None:
        meta = {
            "id": entry_id,
            "type": entry_type,
            "title": title,
            "status": status,
            "depends_on": depends_on,
            "links": [],
        }
        path = _write_entry(artifacts / kind_dir, meta, body)
        created.append({"id": entry_id, "type": entry_type, "path": path.relative_to(root).as_posix()})

    if "spec" in present:
        overview, stories = _parse_spec((src / "spec.md").read_text(encoding="utf-8"))
        seq = 1
        if overview is not None:
            add("spec", f"REQ-{seq:03d}", "req", overview["title"], "draft", [], overview["body"])
            seq += 1
        for story in stories:
            req_id = f"REQ-{seq:03d}"
            seq += 1
            story_map[story["num"]] = req_id
            body = (
                "## Description\n\n"
                f"Imported from spec.md (User Story {story['num']}).\n\n"
                + "\n".join(story["lines"]).strip("\n")
                + "\n"
            )
            add("spec", req_id, "req", story["title"], "active" if story["priority"] == 1 else "draft", [], body)

    if "tasks" in present:
        for index, task in enumerate(_parse_tasks((src / "tasks.md").read_text(encoding="utf-8")), start=1):
            depends: list[str] = []
            if task["story"] is not None:
                req_id = story_map.get(task["story"])
                if req_id:
                    depends.append(req_id)
                else:
                    warnings.append(
                        f"task {index} references User Story {task['story']} "
                        "which spec.md does not define; dependency omitted"
                    )
            add(
                "tasks",
                f"TASK-{index:03d}",
                "task",
                task["title"],
                task["status"],
                depends,
                f"## Description\n\n{task['line']}\n",
            )

    if "plan" in present:
        plan_text = (src / "plan.md").read_text(encoding="utf-8")
        plan_title = _clean_title(_first_h1(plan_text) or "Implementation plan") or "Implementation plan"
        add("plan", "PLAN-001", "plan", plan_title, "active", [], plan_text.strip("\n") + "\n")

    if "constitution" in present:
        con_text = (src / "constitution.md").read_text(encoding="utf-8")
        con_title = _first_h1(con_text) or "Project constitution"
        add("constitution", "CON-001", "con", con_title, "active", [], con_text.strip("\n") + "\n")

    # Round-trip validation: everything written must parse and index cleanly.
    build_index(load_entries(root))

    counts: dict[str, int] = {}
    for item in created:
        counts[item["type"]] = counts.get(item["type"], 0) + 1
    return {"created": created, "counts": counts, "warnings": warnings}
