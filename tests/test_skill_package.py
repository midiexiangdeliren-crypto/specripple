"""Skill package build + standalone run.py behaviour (no source checkout needed)."""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

from specripple.init_host import SKILL_SOURCE_DIR
from specripple.skillbuild import (
    REQUIRED_SKILL_FILES,
    build_package,
    build_package_zip_members,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_PY = SKILL_SOURCE_DIR / "scripts" / "run.py"

REQ_BODY = """---
id: REQ-001
type: req
title: Greeting
status: active
depends_on: []
links: []
---
## Description

The CLI greets the user.

Source: user request

## Acceptance

1. **Given** the CLI **When** run **Then** it prints hello
"""

ASSERTIONS_PASS = """fail_to_pass:
  - checker: file_contains
    file: artifacts/spec/REQ-001.md
    text: "prints hello"
pass_to_pass:
  - checker: file_exists
    file: artifacts/spec/REQ-001.md
"""


def _load_run_module():
    spec = importlib.util.spec_from_file_location("specripple_skill_run", RUN_PY)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # never drop __pycache__ into the skill source dir
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def _build(tmp_path: Path) -> Path:
    result = build_package(REPO_ROOT, tmp_path / "dist")
    assert result["package"].is_dir()
    return result["package"]


def _business_project(root: Path, assertions: str = ASSERTIONS_PASS) -> Path:
    project = root / "业务 项目"
    (project / "artifacts" / "spec").mkdir(parents=True)
    (project / "artifacts" / "spec" / "REQ-001.md").write_text(REQ_BODY, encoding="utf-8")
    (project / "assertions.yaml").write_text(assertions, encoding="utf-8")
    return project


def _run_run_py(package: Path, args: list[str], cwd: Path, env: dict | None = None):
    cmd = [sys.executable, str(package / "scripts" / "run.py"), *args]
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        env=env,
    )


# ---------------------------------------------------------------- build tests


def test_build_package_layout(tmp_path):
    package = _build(tmp_path)
    for rel in REQUIRED_SKILL_FILES:
        assert (package / rel).is_file(), rel
    for rel in ("runtime/pyproject.toml", "runtime/uv.lock", "runtime/README.md", "runtime/VERSION"):
        assert (package / rel).is_file(), rel
    assert (package / "runtime" / "src" / "specripple" / "cli.py").is_file()
    for junk in ("__pycache__", ".pytest_cache", ".git"):
        assert not any(package.rglob(junk))


def test_build_zip_contains_package(tmp_path):
    result = build_package(REPO_ROOT, tmp_path / "dist")
    members = build_package_zip_members(result["zip"])
    assert "specripple/SKILL.md" in members
    assert "specripple/scripts/run.py" in members
    assert "specripple/runtime/uv.lock" in members
    assert "specripple/runtime/src/specripple/cli.py" in members


def test_build_version_stamp_matches_pyproject(tmp_path):
    package = _build(tmp_path)
    stamped = (package / "runtime" / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    import re

    expected = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE).group(1)
    assert stamped == expected


def test_build_refuses_existing_output_without_force(tmp_path):
    build_package(REPO_ROOT, tmp_path / "dist")
    import pytest

    with pytest.raises(ValueError, match="not empty"):
        build_package(REPO_ROOT, tmp_path / "dist")
    build_package(REPO_ROOT, tmp_path / "dist", force=True)  # replaces cleanly


def test_build_refuses_protected_output_paths(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="protected"):
        build_package(REPO_ROOT, REPO_ROOT / "src" / "specripple" / "skills" / "somewhere")


def test_build_fails_loudly_on_missing_skill_file(tmp_path):
    import pytest

    fake = tmp_path / "fake-repo"
    (fake / "src" / "specripple" / "skills").mkdir(parents=True)
    for rel in ("pyproject.toml", "uv.lock", "README.md"):
        shutil.copy2(REPO_ROOT / rel, fake / rel)
    shutil.copytree(SKILL_SOURCE_DIR, fake / "src" / "specripple" / "skills" / "specripple")
    (fake / "src" / "specripple" / "skills" / "specripple" / "references" / "artifact-format.md").unlink()
    with pytest.raises(ValueError, match="artifact-format"):
        build_package(fake, tmp_path / "out")


# ------------------------------------------------------------- run.py unit-ish


def test_run_module_usage_and_missing_runtime():
    run = _load_run_module()
    assert run.main([]) == 2  # no args: usage + error
    assert run.main(["index", "--root", "."]) == 2  # source tree ships no runtime/


def test_cache_env_override_and_version_key(tmp_path, monkeypatch):
    run = _load_run_module()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    monkeypatch.setenv("SPECRIPPLE_RUNTIME_ENV", str(tmp_path / "override"))
    assert run._cache_env_dir(runtime) == tmp_path / "override"
    monkeypatch.delenv("SPECRIPPLE_RUNTIME_ENV")
    assert run._cache_env_dir(runtime).name == "skill-runtime-v9.9.9"


# ------------------------------------------------------------ standalone runs


def test_run_py_missing_runtime_exits_2(tmp_path):
    package = _build(tmp_path)
    shutil.rmtree(package / "runtime")
    project = _business_project(tmp_path)
    result = _run_run_py(package, ["detect", "--root", str(project)], cwd=tmp_path)
    assert result.returncode == 2
    assert "runtime" in result.stderr


def test_run_py_without_uv_exits_3(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", "")
    package = _build(tmp_path)
    project = _business_project(tmp_path)
    result = _run_run_py(package, ["detect", "--root", str(project)], cwd=tmp_path)
    assert result.returncode == 3
    assert "uv" in result.stderr


def test_run_py_standalone_end_to_end(tmp_path):
    """The packaged skill runs the locked core on a business project with a
    Chinese + space path, from a foreign cwd, without any global CLI."""
    package = _build(tmp_path / "pkgdist")
    project = _business_project(tmp_path / "workspace")
    elsewhere = tmp_path / "cwd"
    elsewhere.mkdir()

    detect = _run_run_py(package, ["detect", "--root", str(project)], cwd=elsewhere)
    assert detect.returncode == 0, detect.stderr
    assert "0 finding" in detect.stdout

    verify = _run_run_py(package, ["verify", "--root", str(project)], cwd=elsewhere)
    assert verify.returncode == 0, verify.stderr
    assert "PASS" in verify.stdout

    (project / "assertions.yaml").write_text(
        ASSERTIONS_PASS.replace("prints hello", "prints goodbye"), encoding="utf-8"
    )
    failing = _run_run_py(package, ["verify", "--root", str(project)], cwd=elsewhere)
    assert failing.returncode == 1  # CLI exit codes pass through unchanged
