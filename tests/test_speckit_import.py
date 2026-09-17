from pathlib import Path

import pytest

from specripple.detect import detect
from specripple.repo import load_entries
from specripple.speckit_import import import_speckit

FIXTURES = Path(__file__).parent / "fixtures" / "speckit-sample"
GOLDEN = Path(__file__).parent / "golden" / "speckit_import"


def test_counts_and_mapping(tmp_path):
    result = import_speckit(FIXTURES, tmp_path)
    assert result["counts"] == {"req": 3, "task": 6, "plan": 1, "con": 1}
    assert result["warnings"] == []

    entries = {e.id: e for e in load_entries(tmp_path)}
    assert entries["REQ-001"].title == "User Authentication"
    assert entries["REQ-001"].status.value == "draft"
    assert entries["REQ-002"].title == "Email login"
    assert entries["REQ-002"].status.value == "active"
    assert entries["REQ-003"].title == "Session persistence"
    assert entries["REQ-003"].status.value == "draft"

    assert entries["TASK-001"].depends_on == []  # setup phase, no story context
    assert entries["TASK-002"].depends_on == ["REQ-002"]  # story 1
    assert entries["TASK-003"].depends_on == ["REQ-002"]
    assert entries["TASK-004"].depends_on == ["REQ-003"]  # story 2
    assert entries["TASK-005"].depends_on == ["REQ-003"]
    assert entries["TASK-006"].depends_on == []  # Final Review resets context

    assert entries["TASK-001"].status.value == "draft"
    assert "T001" in entries["TASK-001"].title

    assert entries["PLAN-001"].type.value == "plan"
    assert entries["PLAN-001"].title == "Implementation Plan: User Authentication"
    assert entries["CON-001"].type.value == "con"
    assert entries["CON-001"].title == "Project Constitution"


def test_acceptance_heading_normalized(tmp_path):
    import_speckit(FIXTURES, tmp_path)
    entries = {e.id: e for e in load_entries(tmp_path)}
    assert "## Acceptance" in entries["REQ-002"].body
    assert "Acceptance Scenarios" not in entries["REQ-002"].body
    assert "Given" in entries["REQ-002"].body


def test_imported_repository_is_detect_clean(tmp_path):
    import_speckit(FIXTURES, tmp_path)
    assert detect(load_entries(tmp_path), tmp_path) == []


def test_checked_task_maps_to_done(tmp_path):
    tasks = tmp_path / "tasks.md"
    tasks.write_text(
        "# Tasks\n\n## Phase 2: User Story 1 - Email login (Priority: P1)\n\n- [x] T001 Implement login\n",
        encoding="utf-8",
    )
    spec = tmp_path / "spec.md"
    spec.write_text(
        "# Feature: X\n\n### User Story 1 - Email login (Priority: P1)\n\nBody.\n\n## Requirements\n\n- **FR-1**: x\n",
        encoding="utf-8",
    )
    result = import_speckit(tmp_path, tmp_path / "out")
    assert result["counts"] == {"req": 2, "task": 1}
    entries = {e.id: e for e in load_entries(tmp_path / "out")}
    assert entries["TASK-001"].status.value == "done"


def test_task_referencing_unknown_story_warns(tmp_path):
    tasks = tmp_path / "tasks.md"
    tasks.write_text(
        "# Tasks\n\n## Phase 2: User Story 9 - Missing (Priority: P1)\n\n- [ ] T001 Work\n",
        encoding="utf-8",
    )
    spec = tmp_path / "spec.md"
    spec.write_text("# Feature: X\n\n### User Story 1 - A (Priority: P1)\n\nBody.\n", encoding="utf-8")
    result = import_speckit(tmp_path, tmp_path / "out")
    assert len(result["warnings"]) == 1
    entries = {e.id: e for e in load_entries(tmp_path / "out")}
    assert entries["TASK-001"].depends_on == []


def test_refuses_non_empty_artifacts(tmp_path):
    import_speckit(FIXTURES, tmp_path)
    with pytest.raises(ValueError, match="not empty"):
        import_speckit(FIXTURES, tmp_path)


def test_missing_source_dir(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        import_speckit(tmp_path / "nope", tmp_path / "out")


def test_no_speckit_files(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "readme.md").write_text("nothing here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no spec-kit artifacts"):
        import_speckit(tmp_path / "src", tmp_path / "out")


def test_golden_snapshot(tmp_path):
    import_speckit(FIXTURES, tmp_path)
    produced = {p.relative_to(tmp_path / "artifacts").as_posix(): p for p in (tmp_path / "artifacts").rglob("*.md")}
    expected = {p.relative_to(GOLDEN).as_posix(): p for p in GOLDEN.rglob("*.md")}
    assert sorted(produced) == sorted(expected)
    for rel, path in produced.items():
        assert path.read_text(encoding="utf-8") == expected[rel].read_text(encoding="utf-8"), rel
