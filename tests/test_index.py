from pathlib import Path

import pytest

from align_kit.index_build import build_index, write_index
from align_kit.repo import load_entries

FIXTURES = Path(__file__).parent / "fixtures" / "mini"


def test_build_index_sorted_entries():
    idx = build_index(load_entries(FIXTURES))
    assert idx["schema_version"] == 1
    assert [e["id"] for e in idx["entries"]] == [
        "REQ-001",
        "REQ-002",
        "REQ-003",
        "TASK-001",
        "TASK-002",
    ]


def test_build_index_entry_payload_fields():
    idx = build_index(load_entries(FIXTURES))
    req1 = idx["entries"][0]
    assert req1["type"] == "req"
    assert req1["status"] == "active"
    assert req1["title"] == "User login with email and password"
    assert req1["path"].endswith("REQ-001.md")
    assert req1["summary"].startswith("Users log in")


def test_build_index_adjacency_merges_depends_and_links():
    idx = build_index(load_entries(FIXTURES))
    assert idx["adjacency"]["REQ-001"] == ["TASK-001"]
    assert idx["adjacency"]["REQ-002"] == ["REQ-001"]
    assert idx["adjacency"]["TASK-002"] == ["REQ-002"]


def test_index_is_deterministic_byte_identical(tmp_path):
    p1 = write_index(build_index(load_entries(FIXTURES)), tmp_path)
    p2 = write_index(build_index(load_entries(FIXTURES)), tmp_path)
    assert p1.read_bytes() == p2.read_bytes()


def test_duplicate_id_raises(tmp_path):
    target = tmp_path / "artifacts"
    target.mkdir()
    text = (FIXTURES / "artifacts" / "spec" / "REQ-001.md").read_text(encoding="utf-8")
    (target / "a.md").write_text(text, encoding="utf-8")
    (target / "b.md").write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate artifact ids"):
        build_index(load_entries(tmp_path))
