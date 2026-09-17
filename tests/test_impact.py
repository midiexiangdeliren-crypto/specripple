from pathlib import Path

import pytest

from align_kit.impact import compute_impact
from align_kit.repo import load_entries

FIXTURES = Path(__file__).parent / "fixtures" / "mini"


def _entries():
    return load_entries(FIXTURES)


def test_impact_closure_from_req001():
    result = compute_impact(_entries(), "REQ-001")
    assert [n["id"] for n in result["impacts"]] == ["REQ-002", "TASK-001", "TASK-002"]
    assert result["root"] == "REQ-001"
    assert result["unresolved"] == []


def test_impact_depth_and_evidence_chains():
    result = compute_impact(_entries(), "REQ-001")
    by_id = {n["id"]: n for n in result["impacts"]}
    assert by_id["REQ-002"]["depth"] == 1
    assert by_id["REQ-002"]["edges"] == ["depended-on-by"]
    assert by_id["TASK-001"]["depth"] == 1
    assert by_id["TASK-001"]["edges"] == ["realized-by"]
    assert by_id["TASK-002"]["depth"] == 2
    assert by_id["TASK-002"]["path"] == ["REQ-001", "REQ-002", "TASK-002"]
    assert by_id["TASK-002"]["edges"] == ["depended-on-by", "depended-on-by"]


def test_impact_from_leaf_task_is_empty():
    result = compute_impact(_entries(), "TASK-002")
    assert result["impacts"] == []
    assert result["unresolved"] == []


def test_unresolved_reference_reported():
    result = compute_impact(_entries(), "REQ-003")
    assert result["unresolved"] == ["REQ-999"]
    assert [n["id"] for n in result["impacts"]] == []


def test_unknown_root_raises_keyerror():
    with pytest.raises(KeyError):
        compute_impact(_entries(), "REQ-404")
