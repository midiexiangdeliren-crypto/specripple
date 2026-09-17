from pathlib import Path

import pytest

from align_kit.verify import run_verify


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
