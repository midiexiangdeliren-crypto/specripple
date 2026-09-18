from pathlib import Path

import shutil

from typer.testing import CliRunner

from specripple.cli import app

runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures" / "mini"


def _all_output(result) -> str:
    out = result.output
    try:
        out += result.stderr
    except Exception:
        pass
    return out


def _copy_project(tmp_path) -> Path:
    project = tmp_path / "proj"
    shutil.copytree(FIXTURES, project)
    return project


def test_index_writes_index_json(tmp_path):
    project = _copy_project(tmp_path)
    result = runner.invoke(app, ["index", "--root", str(project)])
    assert result.exit_code == 0, _all_output(result)
    index_file = project / "index.json"
    assert index_file.exists()
    data = index_file  # content checked below via json
    import json

    payload = json.loads(data.read_text(encoding="utf-8"))
    assert len(payload["entries"]) == 5


def test_impact_json_output(tmp_path):
    project = _copy_project(tmp_path)
    result = runner.invoke(app, ["impact", "REQ-001", "--root", str(project), "--json"])
    assert result.exit_code == 0, _all_output(result)
    import json

    payload = json.loads(result.output)
    assert [n["id"] for n in payload["impacts"]] == ["REQ-002", "TASK-001", "TASK-002"]
    assert payload["unresolved"] == []


def test_impact_human_output_mentions_chains(tmp_path):
    project = _copy_project(tmp_path)
    result = runner.invoke(app, ["impact", "REQ-001", "--root", str(project)])
    assert result.exit_code == 0, _all_output(result)
    assert "REQ-002" in result.output
    assert "depended-on-by" in result.output
    assert "realized-by" in result.output


def test_unknown_id_exits_2(tmp_path):
    project = _copy_project(tmp_path)
    result = runner.invoke(app, ["impact", "REQ-404", "--root", str(project)])
    assert result.exit_code == 2
    assert "unknown artifact id" in _all_output(result)


def test_detect_reports_severities(tmp_path):
    project = _copy_project(tmp_path)
    result = runner.invoke(app, ["detect", "--root", str(project)])
    assert result.exit_code == 0, _all_output(result)
    assert "[CRITICAL D1]" in result.output
    assert "[HIGH D5]" in result.output


def test_detect_json(tmp_path):
    project = _copy_project(tmp_path)
    result = runner.invoke(app, ["detect", "--root", str(project), "--json"])
    assert result.exit_code == 0, _all_output(result)
    import json

    payload = json.loads(result.output)
    assert payload["summary"]["total"] == 2
    assert payload["summary"]["counts"]["CRITICAL"] == 1
    assert payload["summary"]["counts"]["HIGH"] == 1


def test_detect_fail_on_high_exits_1_report_still_printed(tmp_path):
    project = _copy_project(tmp_path)
    result = runner.invoke(app, ["detect", "--root", str(project), "--fail-on", "HIGH"])
    assert result.exit_code == 1
    assert "[CRITICAL D1]" in result.output  # report is still printed in gate mode
    assert "[HIGH D5]" in result.output


def test_detect_fail_on_lowercase_accepted(tmp_path):
    project = _copy_project(tmp_path)
    result = runner.invoke(app, ["detect", "--root", str(project), "--fail-on", "high"])
    assert result.exit_code == 1


def test_detect_fail_on_threshold_respected(tmp_path):
    project = tmp_path / "proj"
    (project / "artifacts" / "spec").mkdir(parents=True)
    clean_req = (
        "---\nid: REQ-001\ntype: req\ntitle: x\nstatus: active\n---\n\n"
        "## Description\n\nFine.\n\n"
        "## Acceptance\n\n- Given a user, when the app restarts, then the session persists.\n"
    )
    (project / "artifacts" / "spec" / "REQ-001.md").write_text(clean_req, encoding="utf-8")
    ok = runner.invoke(app, ["detect", "--root", str(project), "--fail-on", "HIGH"])
    assert ok.exit_code == 0
    # a LOW finding does not trip a MEDIUM threshold but does trip LOW
    (project / "glossary.md").write_text("- **Widget**: a component.\n", encoding="utf-8")
    (project / "artifacts" / "spec" / "REQ-001.md").write_text(
        clean_req.replace("## Description\n\nFine.", "Uses **Gadget** here."),
        encoding="utf-8",
    )
    medium = runner.invoke(app, ["detect", "--root", str(project), "--fail-on", "MEDIUM"])
    assert medium.exit_code == 0
    low = runner.invoke(app, ["detect", "--root", str(project), "--fail-on", "LOW"])
    assert low.exit_code == 1


def test_detect_fail_on_invalid_threshold_exit_2(tmp_path):
    project = _copy_project(tmp_path)
    result = runner.invoke(app, ["detect", "--root", str(project), "--fail-on", "TURBO"])
    assert result.exit_code == 2


def test_detect_fail_on_json_structure_preserved(tmp_path):
    project = _copy_project(tmp_path)
    result = runner.invoke(app, ["detect", "--root", str(project), "--json", "--fail-on", "HIGH"])
    assert result.exit_code == 1
    import json

    payload = json.loads(result.output)
    assert payload["summary"]["counts"]["CRITICAL"] == 1
    assert payload["summary"]["counts"]["HIGH"] == 1
    assert payload["findings"][0]["rule"] == "D1"


def test_verify_pass_then_fail(tmp_path):
    project = _copy_project(tmp_path)
    (project / "assertions.yaml").write_text(
        "fail_to_pass: []\n"
        "pass_to_pass:\n"
        "  - checker: file_exists\n"
        "    file: artifacts/spec/REQ-001.md\n",
        encoding="utf-8",
    )
    ok = runner.invoke(app, ["verify", "--root", str(project)])
    assert ok.exit_code == 0, _all_output(ok)
    assert "verify: PASS" in ok.output

    (project / "assertions.yaml").write_text(
        "fail_to_pass:\n"
        "  - checker: file_contains\n"
        "    file: artifacts/spec/REQ-001.md\n"
        "    text: no-such-text-here\n"
        "pass_to_pass: []\n",
        encoding="utf-8",
    )
    bad = runner.invoke(app, ["verify", "--root", str(project)])
    assert bad.exit_code == 1
    assert "FAIL" in _all_output(bad)


def test_verify_missing_config_exit_2(tmp_path):
    project = _copy_project(tmp_path)
    result = runner.invoke(app, ["verify", "--root", str(project)])
    assert result.exit_code == 2
    assert "assertions.yaml not found" in _all_output(result)


def test_verify_json_fail_exits_1_with_parseable_stdout(tmp_path):
    project = _copy_project(tmp_path)
    (project / "assertions.yaml").write_text(
        "fail_to_pass:\n"
        "  - checker: file_contains\n"
        "    file: artifacts/spec/REQ-001.md\n"
        "    text: no-such-text-here\n"
        "pass_to_pass: []\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["verify", "--root", str(project), "--json"])
    assert result.exit_code == 1
    import json

    payload = json.loads(result.output)  # stdout must be complete parseable JSON
    assert payload["summary"]["failed"] == 1
    assert payload["groups"]["fail_to_pass"][0]["status"] == "fail"
    assert payload["groups"]["fail_to_pass"][0]["detail"]


def test_verify_json_pass_exits_0(tmp_path):
    project = _copy_project(tmp_path)
    (project / "assertions.yaml").write_text(
        "fail_to_pass: []\n"
        "pass_to_pass:\n"
        "  - checker: file_exists\n"
        "    file: artifacts/spec/REQ-001.md\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["verify", "--root", str(project), "--json"])
    assert result.exit_code == 0
    import json

    payload = json.loads(result.output)
    assert payload["summary"]["failed"] == 0


def test_verify_json_missing_config_exit_2_stderr_not_json(tmp_path):
    project = _copy_project(tmp_path)
    result = runner.invoke(app, ["verify", "--root", str(project), "--json"])
    assert result.exit_code == 2
    assert "assertions.yaml not found" in _all_output(result)


def test_verify_malformed_config_exit_2(tmp_path):
    project = _copy_project(tmp_path)
    (project / "assertions.yaml").write_text("just a string\n", encoding="utf-8")
    result = runner.invoke(app, ["verify", "--root", str(project)])
    assert result.exit_code == 2


def test_verify_empty_assertions_exit_2(tmp_path):
    project = _copy_project(tmp_path)
    (project / "assertions.yaml").write_text("fail_to_pass: []\npass_to_pass: []\n", encoding="utf-8")
    result = runner.invoke(app, ["verify", "--root", str(project)])
    assert result.exit_code == 2
    assert "no assertions" in _all_output(result)
