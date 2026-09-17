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
