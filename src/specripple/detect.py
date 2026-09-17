"""Rule-based detection layer (zero-token diagnostics)."""

from __future__ import annotations

import re
from pathlib import Path

from .models import Entry, EntryStatus, EntryType

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")

TODO_PATTERN = re.compile(r"\b(?:TODO|FIXME)\b|\[NEEDS CLARIFICATION\]", re.IGNORECASE)
GWT_PATTERN = re.compile(r"\b(?:Given|When|Then)\b")
ACCEPTANCE_PATTERN = re.compile(r"^#{2,3}\s+Acceptance\b", re.MULTILINE)
BOLD_PATTERN = re.compile(r"\*\*([^*\n]+)\*\*")


def _finding(
    rule: str,
    severity: str,
    message: str,
    entry_id: str | None = None,
    path: str | None = None,
) -> dict:
    return {"rule": rule, "severity": severity, "entry_id": entry_id, "path": path, "message": message}


def detect(entries: list[Entry], project_root: Path) -> list[dict]:
    """Run the v0 rule set and return findings sorted by severity.

    Rules: D1 dangling references (CRITICAL), D2 duplicate ids (CRITICAL),
    D3 done entry depending on unfinished upstream (HIGH), D4 active req
    without Acceptance block or Given/When/Then wording (MEDIUM), D5
    unresolved residue markers (HIGH), D6 bold terms missing from
    glossary.md (LOW, only when glossary.md exists).
    """
    findings: list[dict] = []
    by_id: dict[str, list[Entry]] = {}
    for entry in entries:
        by_id.setdefault(entry.id, []).append(entry)
    known = set(by_id)

    # D1 dangling references
    for entry in entries:
        targets = list(entry.depends_on) + [link.to for link in entry.links]
        for target in sorted(set(targets) - known):
            findings.append(
                _finding(
                    "D1",
                    "CRITICAL",
                    f"{entry.id} references unknown id {target}",
                    entry.id,
                    entry.path.as_posix(),
                )
            )

    # D2 duplicate ids
    for entry_id in sorted(by_id):
        group = by_id[entry_id]
        if len(group) > 1:
            paths = ", ".join(sorted(e.path.as_posix() for e in group))
            findings.append(_finding("D2", "CRITICAL", f"{entry_id} defined {len(group)} times: {paths}", entry_id))

    # D3 done entry depending on unfinished upstream
    for entry in entries:
        if entry.status != EntryStatus.DONE:
            continue
        for dep in sorted(set(entry.depends_on)):
            group = by_id.get(dep)
            if not group:
                continue  # dangling reference is D1's job
            if group[0].status in (EntryStatus.DRAFT, EntryStatus.ACTIVE):
                findings.append(
                    _finding(
                        "D3",
                        "HIGH",
                        f"{entry.id} is done but depends on {dep} which is {group[0].status.value}",
                        entry.id,
                        entry.path.as_posix(),
                    )
                )

    # D4 active reqs need an Acceptance block and Given/When/Then wording
    for entry in entries:
        if entry.type != EntryType.REQ or entry.status != EntryStatus.ACTIVE:
            continue
        if not ACCEPTANCE_PATTERN.search(entry.body):
            findings.append(
                _finding(
                    "D4",
                    "MEDIUM",
                    f"{entry.id} (active req) has no '## Acceptance' block",
                    entry.id,
                    entry.path.as_posix(),
                )
            )
        if not GWT_PATTERN.search(entry.body):
            findings.append(
                _finding(
                    "D4",
                    "MEDIUM",
                    f"{entry.id} (active req) has no Given/When/Then acceptance wording",
                    entry.id,
                    entry.path.as_posix(),
                )
            )

    # D5 unresolved residue markers
    for entry in entries:
        match = TODO_PATTERN.search(entry.body)
        if match:
            findings.append(
                _finding(
                    "D5",
                    "HIGH",
                    f"{entry.id} contains unresolved marker {match.group(0)!r}",
                    entry.id,
                    entry.path.as_posix(),
                )
            )

    # D6 bold terms not defined in glossary.md (rule active only when it exists)
    glossary = project_root / "glossary.md"
    if glossary.is_file():
        defined = {term.casefold() for term in BOLD_PATTERN.findall(glossary.read_text(encoding="utf-8"))}
        seen: set[tuple[str, str]] = set()
        for entry in entries:
            for term in BOLD_PATTERN.findall(entry.body):
                if term.casefold() in defined:
                    continue
                key = (entry.id, term.casefold())
                if key not in seen:
                    seen.add(key)
                    findings.append(
                        _finding(
                            "D6",
                            "LOW",
                            f"bold term {term!r} not defined in glossary.md",
                            entry.id,
                            entry.path.as_posix(),
                        )
                    )

    return sorted(
        findings,
        key=lambda f: (SEVERITIES.index(f["severity"]), f["rule"], f["entry_id"] or "", f["message"]),
    )
