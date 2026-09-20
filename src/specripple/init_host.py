"""Host integration: AGENTS.md marked block and skill copies (idempotent).

Installs the single ``specripple`` skill together with its bundled runtime
(assembled from the same sources as ``build-skill``), and migrates the legacy
three-skill set: unmodified legacy files are removed, user-modified ones are
kept and reported as a conflict. A manifest with content fingerprints records
what the installer manages; upgrades consult it so user modifications are
never overwritten, and uninstall can distinguish managed files from edits.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from . import __version__, skillbuild
from .legacy import LEGACY_SKILL_NAMES, legacy_skill_variants

SKILLS_DIR = Path(__file__).parent / "skills"
SKILL_NAME = "specripple"
SKILL_SOURCE_DIR = SKILLS_DIR / SKILL_NAME
MANIFEST_REL = ".agents/specripple-manifest.json"
HOSTS = ("codex", "claude")
BLOCK_END = "<!-- specripple:end -->"

AGENTS_BODY = """\
## Alignment layer (specripple)

`artifacts/` holds the entry repository: one markdown file per entry (REQ/TASK/PLAN/CON/RAT), YAML frontmatter, schema v0.

- When the user changes a requirement or behavior, or asks to sync/align artifacts, code, or tests, follow the `specripple` skill at `.agents/skills/specripple/SKILL.md`. It is the single entry: project onboarding, the alignment workflow, conflict checks and resolution, and the artifact/assertion formats.
- Run the deterministic CLI through the skill's tool entry before announcing completion (see install notes below for how to invoke it).
- Baseline detection stays in report mode so pre-existing findings stay visible. Gate completion on `specripple detect --root . --fail-on HIGH` exiting 0: a nonzero exit means CRITICAL/HIGH findings remain and completion must not be declared. Fix or explicitly resolve every CRITICAL/HIGH finding with the user. Evidence before declaration: paste the `specripple verify` summary and report every supplementary candidate as modified, checked (with reason), or unconfirmed.
- Skills are discovered by the host when supported; when in doubt, read and follow `.agents/skills/specripple/SKILL.md` explicitly instead of assuming it was auto-loaded.

Install / invoke the CLI (specripple is distributed via GitHub, not PyPI):

- No install: `uvx --from git+https://github.com/midiexiangdeliren-crypto/specripple specripple <command>`
- Or install once: `uv tool install git+https://github.com/midiexiangdeliren-crypto/specripple`, then call `specripple <command>`
- `uv run specripple` only works inside the specripple source checkout. When the working directory is not this project's root, pass the project explicitly: `specripple <command> --root <path to project root>`.
"""

CLAUDE_COMMAND = """\
---
description: Align a requirement change across artifacts, code, and tests (specripple)
---

Follow the `specripple` skill (`.claude/skills/specripple/SKILL.md`, mirrored from `.agents/skills/specripple/SKILL.md`) end to end: check the project state and onboard if needed (see the skill's references), index the repository, compute impact for the changed entries, track deterministic links plus supplementary candidates to a modified/checked/unconfirmed conclusion, route and edit every impacted artifact, run `specripple detect` (report mode) plus the conflict-checks checklist, resolve conflicts with the user via the conflict-resolution reference when needed, then gate completion on `specripple detect --root . --fail-on HIGH` and `specripple verify`, and report the verify summary plus the candidate conclusions as evidence before declaring completion.
"""

_BLOCK_PATTERN = re.compile(r"<!-- specripple:begin [^>]*-->.*?<!-- specripple:end -->\n?", re.DOTALL)


def agents_block() -> str:
    header = f"<!-- specripple:begin v{__version__} -->"
    return f"{header}\n{AGENTS_BODY}{BLOCK_END}\n"


def upsert_agents_block(existing: str) -> str:
    """Replace any existing specripple block with the current one (idempotent)."""
    text = _BLOCK_PATTERN.sub("", existing).rstrip("\n")
    block = agents_block().rstrip("\n")
    if not text.strip():
        return block + "\n"
    return f"{text}\n\n{block}\n"


def strip_agents_block(existing: str) -> tuple[str, bool]:
    """Remove the specripple block; return (new_text, whether_removed)."""
    new_text, count = _BLOCK_PATTERN.subn("", existing)
    if count == 0:
        return existing, False
    cleaned = new_text.strip("\n")
    return (cleaned + "\n" if cleaned else ""), True


SKILL_SOURCE_TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".json", ".txt"}


def skill_source_files() -> dict[str, str]:
    """Every text file of the single skill source, as {relative posix path: text}.

    Bytecode caches and other non-source files are excluded: the skill dir
    must be installable from a clean snapshot even if a stray __pycache__
    appeared next to the scripts.
    """
    files: dict[str, str] = {}
    for path in sorted(SKILL_SOURCE_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(SKILL_SOURCE_DIR)
        if any(part == "__pycache__" for part in rel.parts):
            continue
        if path.suffix not in SKILL_SOURCE_TEXT_SUFFIXES:
            continue
        files[rel.as_posix()] = path.read_text(encoding="utf-8")
    return files


@lru_cache(maxsize=1)
def _runtime_source_files_impl() -> dict[str, str] | None:
    """Bundled runtime files as {runtime-relative posix path: text}, or None.

    The runtime is assembled in source order from three layouts: a repository
    checkout (``<root>/pyproject.toml`` + ``<root>/src/specripple``), an
    installed skill's own runtime copy (running init from a bundled runtime,
    ``<skill>/runtime/...``), or a normal wheel installation (the package
    directory itself plus the ``_runtime_src/`` build-input payload that the
    wheel force-includes). When none applies, the installer degrades to skill
    files only and reports it.
    """
    root = Path(__file__).resolve().parents[2]
    plan: list[tuple[str, Path]] | None = None
    if (
        (root / "pyproject.toml").is_file()
        and (root / "uv.lock").is_file()
        and (root / "src" / "specripple").is_dir()
    ):
        try:
            plan = skillbuild.runtime_file_plan(root)
        except ValueError:
            plan = None
    if plan is None:
        try:
            plan = skillbuild.installed_package_runtime_files()
        except ValueError:
            return None
    try:
        files = {f"runtime/{rel}": source.read_text(encoding="utf-8") for rel, source in plan}
    except UnicodeDecodeError as exc:  # a non-text core file breaks the text-manifest model
        raise ValueError(f"runtime assembly expects text files only; {exc}") from exc
    files["runtime/VERSION"] = f"{__version__}\n"
    return files


def runtime_source_files() -> dict[str, str] | None:
    return _runtime_source_files_impl()


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


def manifest_path(root: Path) -> Path:
    return root / MANIFEST_REL


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def managed_paths(root: Path, host: str) -> dict[Path, str]:
    """Map of files init writes -> the exact content init writes.

    Includes the skill source files and, when available from this
    installation, the bundled runtime under ``runtime/``.
    """
    mapping: dict[Path, str] = {}
    skill_text = skill_source_files()["SKILL.md"]
    for rel, content in skill_source_files().items():
        mapping[root / ".agents" / "skills" / SKILL_NAME / rel] = content
    runtime = runtime_source_files()
    if runtime is not None:
        for rel, content in runtime.items():
            mapping[root / ".agents" / "skills" / SKILL_NAME / rel] = content
    if host == "claude":
        mapping[root / ".claude" / "skills" / SKILL_NAME / "SKILL.md"] = thin_shell(skill_text, SKILL_NAME)
        mapping[root / ".claude" / "commands" / "specripple.md"] = CLAUDE_COMMAND
    return mapping


def _remove_empty_parents(root: Path, directory: Path) -> None:
    """Remove now-empty directories climbing from ``directory``; stop at the
    project root and at the .agents/.claude roots themselves."""
    current = directory.resolve()
    root_res = root.resolve()
    while current != root_res and current.name not in (".agents", ".claude"):
        try:
            current.rmdir()  # succeeds only when empty
        except OSError:
            return
        current = current.parent


def _migrate_legacy_skills(root: Path, host: str, actions: list[str], dry_run: bool) -> None:
    for name in LEGACY_SKILL_NAMES:
        variants = legacy_skill_variants(name)
        for base, expected in (
            (root / ".agents" / "skills" / name / "SKILL.md", tuple(variants)),
            (root / ".claude" / "skills" / name / "SKILL.md", tuple(thin_shell(v, name) for v in variants)),
        ):
            if not base.is_file():
                continue
            rel = base.relative_to(root).as_posix()
            if base.read_text(encoding="utf-8") in expected:
                actions.append(f"migrate: remove legacy skill {name} ({rel}, unmodified original)")
                if not dry_run:
                    base.unlink()
                    _remove_empty_parents(root, base.parent)
            else:
                actions.append(
                    f"legacy skill {name} kept ({rel} was modified by user); the new skill is at "
                    f".agents/skills/{SKILL_NAME} - resolve the overlap so two workflows do not stay active"
                )


def _load_manifest(root: Path) -> dict | None:
    path = manifest_path(root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("files"), dict) else None


def run_init(root: Path, host: str, remove: bool = False, dry_run: bool = False) -> list[str]:
    """Install, migrate, or remove specripple host integration; return action lines."""
    if host not in HOSTS:
        raise ValueError(f"unknown host {host!r} (expected one of {', '.join(HOSTS)})")
    actions: list[str] = []
    agents = root / "AGENTS.md"

    if remove:
        if agents.is_file():
            new_text, changed = strip_agents_block(agents.read_text(encoding="utf-8"))
            if changed:
                actions.append("strip specripple block from AGENTS.md")
                if not dry_run:
                    agents.write_text(new_text, encoding="utf-8")
        manifest = _load_manifest(root)
        for path, expected in managed_paths(root, host).items():
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if manifest is not None:
                recorded = manifest["files"].get(rel)
                managed = recorded is not None and recorded == _fingerprint(path.read_text(encoding="utf-8"))
            else:
                managed = path.read_text(encoding="utf-8") == expected
            if not managed:
                actions.append(f"skip {rel} (modified by user, not removing)")
                continue
            actions.append(f"remove {rel}")
            if not dry_run:
                path.unlink()
                _remove_empty_parents(root, path.parent)
        if manifest is not None and not dry_run:
            manifest_path(root).unlink(missing_ok=True)
            actions.append(f"remove {MANIFEST_REL}")
        return actions

    _migrate_legacy_skills(root, host, actions, dry_run)

    if runtime_source_files() is None:
        actions.append(
            "note: bundled runtime is not available from this installation of the installer; "
            "the installed skill will need the specripple CLI or uvx (self-contained installs "
            "come from the built skill package)"
        )

    current = agents.read_text(encoding="utf-8") if agents.is_file() else ""
    new_text = upsert_agents_block(current)
    if new_text == current:
        actions.append("AGENTS.md block already up to date")
    else:
        actions.append("create AGENTS.md" if not agents.is_file() else "upsert specripple block in AGENTS.md")
        if not dry_run:
            agents.write_text(new_text, encoding="utf-8")

    # Upgrade guard: a managed file may only be rewritten when its current
    # content matches the previous manifest's fingerprint (i.e. the installer
    # wrote it and nobody touched it since). Differing or unknown content is
    # user work - it is kept and reported, never overwritten.
    previous = _load_manifest(root)
    recorded_files: dict[str, str] = previous["files"] if previous else {}
    for path, content in managed_paths(root, host).items():
        rel = path.relative_to(root).as_posix()
        current_text = path.read_text(encoding="utf-8") if path.is_file() else None
        if current_text is not None and current_text == content:
            actions.append(f"{rel} already up to date")
            continue
        if current_text is not None:
            if recorded_files.get(rel) == _fingerprint(current_text):
                actions.append(f"upgrade {rel}")
            else:
                actions.append(
                    f"conflict: keep {rel} (modified by user or of unknown origin); "
                    "the new version was not written - reconcile manually"
                )
                continue
        else:
            actions.append(f"write {rel}")
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    if not dry_run:
        manifest = {
            "version": __version__,
            "files": {
                rel: _fingerprint(content) for rel, content in _installed_rel_contents(root, host).items()
            },
        }
        manifest_path(root).parent.mkdir(parents=True, exist_ok=True)
        manifest_path(root).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return actions


def _installed_rel_contents(root: Path, host: str) -> dict[str, str]:
    """Relative-path -> content view of what install writes (for the manifest)."""
    return {
        path.relative_to(root).as_posix(): content for path, content in managed_paths(root, host).items()
    }
