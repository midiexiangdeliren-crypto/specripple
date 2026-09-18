from pathlib import Path

import pytest

from specripple.verify import run_verify


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


GOOD_YAML = r"""fail_to_pass:
  - checker: file_contains
    file: artifacts/spec/REQ-001.md
    text: hello
pass_to_pass:
  - checker: file_exists
    file: notes.txt
  - checker: file_not_contains
    file: artifacts/spec/REQ-001.md
    text: forbidden-marker
  - checker: regex_match
    file: notes.txt
    pattern: 'alpha\s+beta'
"""


def _setup(root: Path, yaml_text: str) -> None:
    _write(root, "artifacts/spec/REQ-001.md", "hello world\n")
    _write(root, "notes.txt", "alpha beta\n")
    _write(root, "assertions.yaml", yaml_text)


def test_all_pass(tmp_path):
    _setup(tmp_path, GOOD_YAML)
    report = run_verify(tmp_path)
    assert report["summary"]["total"] == 4
    assert report["summary"]["failed"] == 0


def test_fail_to_pass_failure(tmp_path):
    _setup(tmp_path, GOOD_YAML.replace("text: hello", "text: absent-string"))
    report = run_verify(tmp_path)
    assert report["summary"]["failed"] == 1
    assert report["groups"]["fail_to_pass"][0]["status"] == "fail"


def test_pass_to_pass_broken(tmp_path):
    _setup(tmp_path, GOOD_YAML.replace("text: forbidden-marker", "text: hello"))
    report = run_verify(tmp_path)
    assert report["summary"]["failed"] == 1
    assert report["groups"]["pass_to_pass"][1]["status"] == "fail"
    assert "found" in report["groups"]["pass_to_pass"][1]["detail"]


def test_missing_file_is_failure_not_crash(tmp_path):
    _setup(
        tmp_path,
        "fail_to_pass:\n"
        "  - checker: file_exists\n"
        "    file: artifacts/spec/REQ-001.md\n"
        "pass_to_pass:\n"
        "  - checker: file_contains\n"
        "    file: ghost.md\n"
        "    text: x\n",
    )
    report = run_verify(tmp_path)
    assert report["summary"]["failed"] == 1
    assert report["groups"]["pass_to_pass"][0]["detail"].startswith("missing file")


def test_regex_non_match_fails(tmp_path):
    _setup(tmp_path, GOOD_YAML.replace(r"'alpha\s+beta'", "'no-such-thing'"))
    report = run_verify(tmp_path)
    assert report["summary"]["failed"] == 1
    assert report["groups"]["pass_to_pass"][2]["status"] == "fail"


def test_unknown_checker_raises(tmp_path):
    _setup(tmp_path, "fail_to_pass:\n  - checker: telepathy\n    file: notes.txt\npass_to_pass: []\n")
    with pytest.raises(ValueError, match="unknown checker"):
        run_verify(tmp_path)


def test_invalid_regex_raises(tmp_path):
    _setup(
        tmp_path,
        "fail_to_pass:\n"
        "  - checker: regex_match\n"
        "    file: notes.txt\n"
        "    pattern: '([unclosed'\n"
        "pass_to_pass: []\n",
    )
    with pytest.raises(ValueError, match="invalid regex"):
        run_verify(tmp_path)


def test_missing_assertions_file(tmp_path):
    _write(tmp_path, "artifacts/spec/REQ-001.md", "hello\n")
    with pytest.raises(ValueError, match="assertions.yaml not found"):
        run_verify(tmp_path)


def test_command_pass_and_fail(tmp_path):
    _write(
        tmp_path,
        "assertions.yaml",
        "fail_to_pass:\n"
        "  - checker: command\n"
        '    command: python -c "import sys; sys.exit(0)"\n'
        "pass_to_pass:\n"
        "  - checker: command\n"
        '    command: python -c "import sys; sys.exit(3)"\n',
    )
    report = run_verify(tmp_path)
    assert report["summary"]["failed"] == 1
    fail_item = report["groups"]["pass_to_pass"][0]
    assert fail_item["status"] == "fail"
    assert "exit 3" in fail_item["detail"]


def test_command_runs_at_project_root(tmp_path):
    _write(tmp_path, "notes.txt", "x\n")
    _write(tmp_path, "check_root.py", "import pathlib, sys\nsys.exit(0 if pathlib.Path('notes.txt').is_file() else 1)\n")
    _write(
        tmp_path,
        "assertions.yaml",
        "fail_to_pass: []\npass_to_pass:\n  - checker: command\n    command: python check_root.py\n",
    )
    report = run_verify(tmp_path)
    assert report["summary"]["failed"] == 0


def test_command_timeout_is_failure(tmp_path):
    _write(
        tmp_path,
        "assertions.yaml",
        "fail_to_pass:\n"
        "  - checker: command\n"
        '    command: python -c "import time; time.sleep(5)"\n'
        "    timeout: 0.5\n"
        "pass_to_pass: []\n",
    )
    report = run_verify(tmp_path)
    item = report["groups"]["fail_to_pass"][0]
    assert item["status"] == "fail"
    assert "timeout" in item["detail"]


def test_command_requires_command_field(tmp_path):
    _write(tmp_path, "assertions.yaml", "fail_to_pass:\n  - checker: command\npass_to_pass: []\n")
    with pytest.raises(ValueError, match="command requires 'command'"):
        run_verify(tmp_path)


def test_command_negative_timeout_rejected(tmp_path):
    _write(
        tmp_path,
        "assertions.yaml",
        "fail_to_pass:\n  - checker: command\n    command: python -c \"pass\"\n    timeout: -1\npass_to_pass: []\n",
    )
    with pytest.raises(ValueError, match="timeout"):
        run_verify(tmp_path)
