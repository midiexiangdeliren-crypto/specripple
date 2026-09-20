"""Real-distribution-path tests: a normal wheel install must bundle the runtime.

The host installer assembles the bundled runtime from three possible sources:
a repository checkout, an installed skill's own runtime copy, or the installed
package itself (the wheel ships the required build inputs as package data
under ``specripple/_runtime_src/``). These tests pin the wheel payload and
exercise the full distribution path end to end: build wheel -> install into a
fresh venv -> ``init`` a temporary business project -> run the installed
skill's ``run.py`` and check both success and failure exit codes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from specripple import skillbuild

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PAYLOAD = ("pyproject.toml", "uv.lock", "README.md")
COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")

REQ_001 = """---
id: REQ-001
type: req
title: Distribution fixture
status: active
depends_on: []
links:
  - to: TASK-001
    kind: realized-by
---
## Description

Minimal fixture entry so detect can run on a fresh business project.

Source: distribution acceptance test.

## Acceptance

1. **Given** the wheel-installed CLI **When** detect runs **Then** it exits 0
"""

TASK_001 = """---
id: TASK-001
type: task
title: Stay active at the baseline
status: active
depends_on: [REQ-001]
links: []
---
## Description

Onboarding convention: the task stays active so D3 stays quiet at the baseline.

Source: distribution acceptance test.

## Acceptance

1. **Given** the baseline **When** detect runs **Then** no D3 finding appears
"""


def _build_wheel(out_dir: Path) -> Path:
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    wheels = list(out_dir.glob("specripple-*.whl"))
    assert len(wheels) == 1, wheels
    return wheels[0]


def _venv_python(venv: Path) -> Path:
    exe = "python.exe" if sys.platform == "win32" else "python"
    return venv / ("Scripts" if sys.platform == "win32" else "bin") / exe


def _venv_specripple(venv: Path) -> Path:
    exe = "specripple.exe" if sys.platform == "win32" else "specripple"
    return venv / ("Scripts" if sys.platform == "win32" else "bin") / exe


def _write_business_project(proj: Path) -> None:
    (proj / "artifacts" / "spec").mkdir(parents=True)
    (proj / "artifacts" / "tasks").mkdir(parents=True)
    (proj / "artifacts" / "spec" / "REQ-001.md").write_text(REQ_001, encoding="utf-8")
    (proj / "artifacts" / "tasks" / "TASK-001.md").write_text(TASK_001, encoding="utf-8")


def test_wheel_carries_runtime_payload(tmp_path: Path) -> None:
    wheel = _build_wheel(tmp_path)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    for rel in REQUIRED_PAYLOAD:
        assert f"specripple/_runtime_src/{rel}" in names
    # The skill source itself must ship in the wheel (init installs it).
    assert "specripple/skills/specripple/SKILL.md" in names
    assert "specripple/skills/specripple/scripts/run.py" in names


def test_installed_package_runtime_files(tmp_path: Path) -> None:
    pkg = tmp_path / "specripple"
    shutil.copytree(REPO_ROOT / "src" / "specripple", pkg, ignore=COPY_IGNORE)
    payload = pkg / "_runtime_src"
    payload.mkdir()
    for rel in REQUIRED_PAYLOAD:
        shutil.copy2(REPO_ROOT / rel, payload / rel)
    plan = skillbuild.installed_package_runtime_files(pkg)
    rels = [rel for rel, _ in plan]
    for required in REQUIRED_PAYLOAD:
        assert required in rels
    assert "src/specripple/cli.py" in rels
    assert "src/specripple/skills/specripple/SKILL.md" in rels
    assert not any(rel.startswith("src/specripple/_runtime_src") for rel in rels)
    assert not any("__pycache__" in rel for rel in rels)
    assert not any(rel.endswith((".pyc", ".pyo", ".pyd")) for rel in rels)


def test_installed_package_runtime_files_require_payload(tmp_path: Path) -> None:
    pkg = tmp_path / "specripple"
    shutil.copytree(REPO_ROOT / "src" / "specripple", pkg, ignore=COPY_IGNORE)
    with pytest.raises(ValueError):
        skillbuild.installed_package_runtime_files(pkg)


@pytest.mark.slow
def test_wheel_install_init_bundles_runtime_and_runs(tmp_path: Path) -> None:
    wheel = _build_wheel(tmp_path)
    venv = tmp_path / "venv"
    result = subprocess.run(
        ["uv", "venv", str(venv)], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--no-progress",
            "--python",
            str(_venv_python(venv)),
            str(wheel),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    # init on a temporary business project, using the wheel-installed CLI.
    proj = tmp_path / "biz"
    _write_business_project(proj)
    result = subprocess.run(
        [str(_venv_specripple(venv)), "init", "--host", "codex", "--root", str(proj)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    runtime_dir = proj / ".agents" / "skills" / "specripple" / "runtime"
    for rel in REQUIRED_PAYLOAD:
        assert (runtime_dir / rel).is_file()
    assert (runtime_dir / "src" / "specripple" / "cli.py").is_file()
    assert (runtime_dir / "VERSION").is_file()
    assert (runtime_dir / "src" / "specripple" / "skills" / "specripple" / "SKILL.md").is_file()

    # The installed skill's run.py must run the bundled runtime end to end.
    env = os.environ.copy()
    env["SPECRIPPLE_RUNTIME_ENV"] = str(tmp_path / "runtime-env")
    run_py = proj / ".agents" / "skills" / "specripple" / "scripts" / "run.py"
    ok = subprocess.run(
        [sys.executable, str(run_py), "detect", "--root", "."],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr
    bad = subprocess.run(
        [sys.executable, str(run_py), "verify", "--root", "."],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert bad.returncode == 2, bad.stdout + bad.stderr  # assertions.yaml missing
