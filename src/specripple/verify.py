"""Assertion verification: fail_to_pass / pass_to_pass runner."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

CHECKERS = ("file_exists", "file_contains", "file_not_contains", "regex_match", "command")

COMMAND_DETAIL_LIMIT = 200


class Assertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checker: str
    file: str = ""
    text: str = ""
    pattern: str = ""
    command: str = ""
    timeout: float = 120.0

    @field_validator("checker")
    @classmethod
    def _known_checker(cls, value: str) -> str:
        if value not in CHECKERS:
            raise ValueError(f"unknown checker {value!r} (expected one of {', '.join(CHECKERS)})")
        return value

    @model_validator(mode="after")
    def _required_params(self) -> "Assertion":
        if self.checker == "command":
            if not self.command:
                raise ValueError("command requires 'command'")
            if self.timeout <= 0:
                raise ValueError("'timeout' must be positive")
            return self
        if not self.file:
            raise ValueError("'file' is required")
        if self.checker == "regex_match":
            if not self.pattern:
                raise ValueError("regex_match requires 'pattern'")
            try:
                re.compile(self.pattern)
            except re.error as exc:
                raise ValueError(f"invalid regex {self.pattern!r}: {exc}") from exc
        elif self.checker != "file_exists" and not self.text:
            raise ValueError(f"{self.checker} requires 'text'")
        return self


def load_assertions(project_root: Path) -> dict[str, list[Assertion]]:
    """Load and validate assertions.yaml from the project root."""
    path = project_root / "assertions.yaml"
    if not path.is_file():
        raise ValueError(f"{path.as_posix()}: assertions.yaml not found")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{path.as_posix()}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path.as_posix()}: top level must be a mapping")
    groups: dict[str, list[Assertion]] = {}
    for group in ("fail_to_pass", "pass_to_pass"):
        items = data.get(group) or []
        if not isinstance(items, list):
            raise ValueError(f"{path.as_posix()}: '{group}' must be a list")
        parsed: list[Assertion] = []
        for position, item in enumerate(items):
            try:
                parsed.append(Assertion(**item))
            except Exception as exc:
                raise ValueError(f"{path.as_posix()}: {group} #{position + 1}: {exc}") from exc
        groups[group] = parsed
    return groups


def _check_command(assertion: Assertion, project_root: Path) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            assertion.command,
            shell=True,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=assertion.timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"timeout after {assertion.timeout:g}s"
    if completed.returncode == 0:
        return True, ""
    tail = (completed.stderr or completed.stdout or "").strip()[-COMMAND_DETAIL_LIMIT:]
    return False, f"exit {completed.returncode}: {tail}" if tail else f"exit {completed.returncode}"


def _check(assertion: Assertion, project_root: Path) -> tuple[bool, str]:
    if assertion.checker == "command":
        return _check_command(assertion, project_root)
    path = project_root / assertion.file
    if assertion.checker == "file_exists":
        return path.is_file(), "" if path.is_file() else "missing file"
    if not path.is_file():
        return False, f"missing file: {assertion.file}"
    content = path.read_text(encoding="utf-8", errors="replace")
    if assertion.checker == "file_contains":
        ok = assertion.text in content
        return ok, "" if ok else f"text {assertion.text!r} not found"
    if assertion.checker == "file_not_contains":
        ok = assertion.text not in content
        return ok, "" if ok else f"text {assertion.text!r} found"
    ok = re.search(assertion.pattern, content) is not None
    return ok, "" if ok else f"pattern {assertion.pattern!r} did not match"


def run_verify(project_root: Path) -> dict:
    """Execute every assertion; report per-item status and a summary."""
    groups = load_assertions(project_root)
    report_groups: dict[str, list[dict]] = {}
    total = 0
    failed = 0
    for group in ("fail_to_pass", "pass_to_pass"):
        items: list[dict] = []
        for position, assertion in enumerate(groups[group]):
            ok, detail = _check(assertion, project_root)
            total += 1
            if not ok:
                failed += 1
            items.append(
                {
                    "index": position,
                    "checker": assertion.checker,
                    "file": assertion.file,
                    "command": assertion.command,
                    "status": "pass" if ok else "fail",
                    "detail": detail,
                }
            )
        report_groups[group] = items
    return {
        "groups": report_groups,
        "summary": {"total": total, "passed": total - failed, "failed": failed},
    }
