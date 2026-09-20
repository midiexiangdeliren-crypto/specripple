"""Original texts of the pre-skill-product skills (migration reference data).

These are the exact SKILL.md bodies distributed before the single-skill
rework, covering every released revision (the maintenance round edited
``aligning-changes`` and ``detecting-conflicts``, so both the ``e49998a``
and the ``6d996a4`` revisions are recorded; ``resolving-conflicts`` shipped
unchanged). The installer uses them to tell unmodified legacy installs (safe
to migrate away) from user-modified ones (kept and reported as a conflict).
They are reference data, not an active skill: never place them under a
directory hosts scan for skills.
"""

from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent
LEGACY_SKILL_NAMES = ("aligning-changes", "detecting-conflicts", "resolving-conflicts")

# Oldest revision first; the last entry is the most recently shipped text.
_VARIANT_FILES: dict[str, tuple[str, ...]] = {
    "aligning-changes": ("aligning-changes@e49998a.md", "aligning-changes.md"),
    "detecting-conflicts": ("detecting-conflicts@e49998a.md", "detecting-conflicts.md"),
    "resolving-conflicts": ("resolving-conflicts.md",),
}


def legacy_skill_variants(name: str) -> tuple[str, ...]:
    """Every known released SKILL.md text for a legacy skill, deduplicated."""
    if name not in LEGACY_SKILL_NAMES:
        raise ValueError(f"unknown legacy skill {name!r} (expected one of {', '.join(LEGACY_SKILL_NAMES)})")
    texts: list[str] = []
    for filename in _VARIANT_FILES[name]:
        text = (_DIR / filename).read_text(encoding="utf-8")
        if text not in texts:
            texts.append(text)
    return tuple(texts)


def legacy_skill_text(name: str) -> str:
    """The most recently shipped SKILL.md text for a legacy skill."""
    return legacy_skill_variants(name)[-1]
