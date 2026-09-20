"""Build a self-contained, installable skill package from the single source tree.

The package bundles the skill files (SKILL.md, scripts, references, assets)
with a runtime copy of the core (pyproject.toml, uv.lock, src/specripple) so
the skill can run on hosts where neither the source checkout nor a globally
installed ``specripple`` CLI is available. The runtime is a generated build
output, never a second hand-maintained source tree.
"""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

SKILL_NAME = "specripple"

# Explicit manifest: everything the package must contain. The skill tree is
# copied whole, then verified against this list, so a missing reference file
# fails the build instead of shipping silently.
REQUIRED_SKILL_FILES = (
    "SKILL.md",
    "scripts/run.py",
    "references/onboarding.md",
    "references/conflict-checks.md",
    "references/conflict-resolution.md",
    "references/artifact-format.md",
    "assets/templates/req-entry.md",
    "assets/templates/rat-entry.md",
    "assets/templates/assertions.yaml",
)
REQUIRED_RUNTIME_FILES = ("pyproject.toml", "uv.lock", "README.zh-CN.md")

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest-tmp",
    "node_modules",
    "dist",
    "build",
    ".trash",
    ".idea",
    ".vscode",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".pyd"}


def _copy_tree(src: Path, dst: Path) -> list[str]:
    """Copy ``src`` into ``dst`` skipping caches, VCS dirs, and build artifacts."""
    copied: list[str] = []
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.is_dir():
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(rel.as_posix())
    return copied


def _read_version(repo_root: Path) -> str:
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    if not match:
        raise ValueError(f"{(repo_root / 'pyproject.toml').as_posix()}: no version = \"...\" found")
    return match.group(1)


def _guard_out_path(out: Path, repo_root: Path, skill_src: Path) -> None:
    """Refuse output paths that would overwrite the sources we build from."""
    out_res = out.resolve()
    if out_res == repo_root.resolve():
        raise ValueError(f"refusing to build the skill package into the repo root {out.as_posix()}")
    core_src = (repo_root / "src" / "specripple").resolve()
    protected = [skill_src.resolve(), skill_src.parent.resolve(), core_src, core_src.parent]
    for g in protected:
        if out_res == g or g in out_res.parents:
            raise ValueError(f"refusing to build the skill package into protected source path {out.as_posix()}")


def runtime_file_plan(repo_root: Path) -> list[tuple[str, Path]]:
    """The bundled runtime as (runtime-relative posix path, source path) pairs.

    Single source of truth for which files make up the runtime; both the
    package builder and the host installer assemble from this plan. Raises
    ValueError when a required build input is missing.
    """
    repo_root = Path(repo_root).resolve()
    for rel in REQUIRED_RUNTIME_FILES:
        if not (repo_root / rel).is_file():
            raise ValueError(f"{(repo_root / rel).as_posix()}: required build input not found")
    core_src = repo_root / "src" / "specripple"
    if not core_src.is_dir():
        raise ValueError(f"{core_src.as_posix()}: core package source not found")
    plan: list[tuple[str, Path]] = [(rel, repo_root / rel) for rel in REQUIRED_RUNTIME_FILES]
    for path in sorted(core_src.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(core_src)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        plan.append((f"src/specripple/{rel.as_posix()}", path))
    return plan


def installed_package_runtime_files(pkg_dir: Path | None = None) -> list[tuple[str, Path]]:
    """The runtime plan assembled from an installed (wheel) specripple package.

    A wheel install has no repository checkout, so the runtime's ``src/specripple``
    is the installed package directory itself and its build inputs ship as
    package data under ``specripple/_runtime_src/`` (pyproject force-include).
    The returned pairs use the same runtime-relative paths as
    ``runtime_file_plan``. Raises ValueError when the payload is missing or
    incomplete (e.g. the payload was stripped after installation).
    """
    pkg_dir = Path(pkg_dir) if pkg_dir is not None else Path(__file__).resolve().parent
    payload = pkg_dir / "_runtime_src"
    plan: list[tuple[str, Path]] = []
    for rel in REQUIRED_RUNTIME_FILES:
        source = payload / Path(rel).name
        if not source.is_file():
            raise ValueError(
                f"{source.as_posix()}: required runtime payload file not found; "
                "this installation does not carry the bundled runtime payload"
            )
        plan.append((rel, source))
    for path in sorted(pkg_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(pkg_dir)
        if rel.parts[0] == "_runtime_src":
            continue
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        plan.append((f"src/specripple/{rel.as_posix()}", path))
    return plan


def build_package(repo_root: Path, out_parent: Path, force: bool = False) -> dict:
    """Assemble the skill package under ``out_parent/specripple`` and zip it.

    Returns a summary dict with the version, package path, zip path, and the
    relative file list. Raises ValueError on invalid inputs (missing sources,
    existing non-empty output without ``force``).
    """
    repo_root = Path(repo_root).resolve()
    out_parent = Path(out_parent).resolve()
    skill_src = repo_root / "src" / "specripple" / "skills" / SKILL_NAME
    core_src = repo_root / "src" / "specripple"
    if not skill_src.is_dir():
        raise ValueError(f"{skill_src.as_posix()}: skill source directory not found")
    for rel in REQUIRED_RUNTIME_FILES:
        if not (repo_root / rel).is_file():
            raise ValueError(f"{(repo_root / rel).as_posix()}: required build input not found")

    out = out_parent / SKILL_NAME
    _guard_out_path(out, repo_root, skill_src)
    if out.exists() and any(out.iterdir()):
        if not force:
            raise ValueError(
                f"{out.as_posix()}: output directory is not empty; pass force (or --force) to replace it"
            )
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    version = _read_version(repo_root)

    copied: list[str] = []
    # 1. Skill files (SKILL.md, scripts/, references/, assets/).
    for rel in REQUIRED_SKILL_FILES:
        if not (skill_src / rel).is_file():
            raise ValueError(f"{(skill_src / rel).as_posix()}: required skill file missing from source")
    copied += [f"{rel}" for rel in _copy_tree(skill_src, out)]
    # 2. Bundled runtime: build inputs + the core package, cache-free.
    runtime = out / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    for rel, source in runtime_file_plan(repo_root):
        target = runtime / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(f"runtime/{rel}")
    (runtime / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    copied.append("runtime/VERSION")

    missing = sorted(set(REQUIRED_SKILL_FILES) - set(copied))
    if missing:
        raise ValueError(f"build verification failed; missing from package: {', '.join(missing)}")
    junk = [
        rel
        for rel in copied
        if any(part in EXCLUDED_DIRS for part in Path(rel).parts) or Path(rel).suffix in EXCLUDED_SUFFIXES
    ]
    if junk:  # pragma: no cover - _copy_tree already filters
        raise ValueError(f"build verification failed; excluded content leaked into package: {', '.join(junk[:5])}")

    zip_base = out_parent / f"{SKILL_NAME}-skill-v{version}"
    zip_path = Path(shutil.make_archive(zip_base.as_posix(), "zip", root_dir=out_parent, base_dir=SKILL_NAME))

    return {
        "version": version,
        "package": out,
        "zip": zip_path,
        "file_count": len(copied),
        "files": sorted(copied),
    }


def build_package_zip_members(zip_path: Path) -> list[str]:
    """Read back the member names of a built zip (helper for verification)."""
    with zipfile.ZipFile(zip_path) as archive:
        return sorted(archive.namelist())
