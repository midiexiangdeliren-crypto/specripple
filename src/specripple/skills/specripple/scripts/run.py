#!/usr/bin/env python3
"""Run the specripple CLI from the bundled skill runtime.

Usage (from anywhere; the runtime is located relative to this file, not the cwd):

    python <skill dir>/scripts/run.py <specripple command and args>

Example:

    python .agents/skills/specripple/scripts/run.py detect --root .

Behaviour:
- Locates ``<skill dir>/runtime`` (pyproject.toml + uv.lock + src/specripple) by
  this script's own path, so the working directory does not matter.
- Runs the locked environment with ``uv run --frozen --no-dev --project
  <runtime> specripple ...``. The virtualenv lives in a dedicated user-cache
  directory (override with SPECRIPPLE_RUNTIME_ENV), never inside the business
  project. The first run may need network to prepare dependencies; later runs
  reuse the cache.
- Passes stdout/stderr through untouched and returns the CLI's exit code
  (0 ok, 1 checks failed, 2 config error).
- Exits 2 with a message on stderr when the bundled runtime is missing, and 3
  when ``uv`` is unavailable or dependency preparation fails. It never falls
  back silently: if the tool cannot run, say so instead of claiming success.

This script only locates the environment and forwards arguments; all checking
logic lives in the specripple core.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

USAGE = "usage: run.py <specripple command and args>  (e.g. run.py detect --root .)"


def _cache_env_dir(runtime: Path) -> Path:
    override = os.environ.get("SPECRIPPLE_RUNTIME_ENV")
    if override:
        return Path(override)
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))
    version = "dev"
    version_file = runtime / "VERSION"
    if version_file.is_file():
        stamped = version_file.read_text(encoding="utf-8").strip()
        if stamped:
            version = stamped
    return base / "specripple" / f"skill-runtime-v{version}"


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE, file=sys.stderr if not argv else sys.stdout)
        return 2 if not argv else 0
    runtime = Path(__file__).resolve().parent.parent / "runtime"
    if not (runtime / "pyproject.toml").is_file() or not (runtime / "uv.lock").is_file():
        print(
            "specripple skill: bundled runtime not found or incomplete "
            f"(expected pyproject.toml and uv.lock under {runtime.as_posix()}). "
            "Install the full skill package, or use the installed `specripple` CLI instead.",
            file=sys.stderr,
        )
        return 2
    uv = shutil.which("uv")
    if uv is None:
        print(
            "specripple skill: `uv` is required to run the bundled runtime but was not found on PATH. "
            "Install uv (https://docs.astral.sh/uv/), or use the installed `specripple` CLI instead.",
            file=sys.stderr,
        )
        return 3
    env = os.environ.copy()
    env["UV_PROJECT_ENVIRONMENT"] = str(_cache_env_dir(runtime))
    command = [uv, "run", "--frozen", "--no-dev", "--project", str(runtime), "specripple", *argv]
    try:
        completed = subprocess.run(command, env=env)  # inherits stdout/stderr unchanged
    except OSError as exc:
        print(f"specripple skill: failed to launch the runtime environment: {exc}", file=sys.stderr)
        return 3
    return completed.returncode


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
