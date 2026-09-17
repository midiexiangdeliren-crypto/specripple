from pathlib import Path

import shutil

from typer.testing import CliRunner

from align_kit.cli import app

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
