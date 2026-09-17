from pathlib import Path

import pytest

from specripple.repo import load_entries, parse_entry_file

FIXTURES = Path(__file__).parent / "fixtures" / "mini"


def test_load_entries_parses_all_five_in_sorted_order():
    entries = load_entries(FIXTURES)
    assert [e.id for e in entries] == ["REQ-001", "REQ-002", "REQ-003", "TASK-001", "TASK-002"]


def test_parse_fields_of_req001():
    entry = parse_entry_file(FIXTURES / "artifacts" / "spec" / "REQ-001.md")
    assert entry.id == "REQ-001"
    assert entry.type.value == "req"
    assert entry.status.value == "active"
    assert entry.title == "User login with email and password"
    assert entry.depends_on == []
    assert len(entry.links) == 1
    assert entry.links[0].to == "TASK-001"
    assert entry.links[0].kind.value == "realized-by"
    assert entry.links[0].src == "manual"
    assert "email and password" in entry.body


def test_depends_on_parsed():
    entries = {e.id: e for e in load_entries(FIXTURES)}
    assert entries["REQ-002"].depends_on == ["REQ-001"]
    assert entries["TASK-002"].depends_on == ["REQ-002"]
    assert entries["TASK-001"].depends_on == ["REQ-001"]


def test_missing_frontmatter_raises(tmp_path):
    f = tmp_path / "REQ-100.md"
    f.write_text("no frontmatter here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="frontmatter"):
        parse_entry_file(f)


def test_invalid_id_raises(tmp_path):
    f = tmp_path / "BAD-001.md"
    f.write_text("---\nid: BAD-001\ntype: req\ntitle: x\n---\nbody\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid artifact id"):
        parse_entry_file(f)


def test_unknown_type_raises(tmp_path):
    f = tmp_path / "REQ-101.md"
    f.write_text("---\nid: REQ-101\ntype: milestone\ntitle: x\n---\nbody\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_entry_file(f)


def test_missing_artifacts_dir_raises(tmp_path):
    with pytest.raises(ValueError, match="artifacts directory not found"):
        load_entries(tmp_path)
