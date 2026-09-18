from pathlib import Path

from specripple.detect import detect
from specripple.repo import load_entries

FIXTURES = Path(__file__).parent / "fixtures" / "mini"


def _write(tmp_path, name, frontmatter, body=""):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / name).write_text(f"---\n{frontmatter}\n---\n{body}\n", encoding="utf-8")


def _rules(entries, root):
    return [f["rule"] for f in detect(entries, root)]


def test_d1_dangling_reference_critical():
    findings = detect(load_entries(FIXTURES), FIXTURES)
    d1 = [f for f in findings if f["rule"] == "D1"]
    assert len(d1) == 1
    assert d1[0]["severity"] == "CRITICAL"
    assert d1[0]["entry_id"] == "REQ-003"
    assert "REQ-999" in d1[0]["message"]


def test_d1_negative_no_dangling_refs_in_wellformed_entries():
    entries = [e for e in load_entries(FIXTURES) if e.id != "REQ-003"]
    assert "D1" not in _rules(entries, FIXTURES)


def test_d2_duplicate_id_critical(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    text = (FIXTURES / "artifacts" / "spec" / "REQ-001.md").read_text(encoding="utf-8")
    (artifacts / "a.md").write_text(text, encoding="utf-8")
    (artifacts / "b.md").write_text(text, encoding="utf-8")
    findings = detect(load_entries(tmp_path), tmp_path)
    d2 = [f for f in findings if f["rule"] == "D2"]
    assert len(d2) == 1
    assert d2[0]["severity"] == "CRITICAL"


def test_d2_negative_unique_ids():
    assert "D2" not in _rules(load_entries(FIXTURES), FIXTURES)


def test_d3_done_entry_with_active_dependency(tmp_path):
    _write(tmp_path, "REQ-001.md", "id: REQ-001\ntype: req\ntitle: base\nstatus: active")
    _write(tmp_path, "TASK-001.md", "id: TASK-001\ntype: task\ntitle: work\nstatus: done\ndepends_on: [REQ-001]")
    findings = detect(load_entries(tmp_path), tmp_path)
    d3 = [f for f in findings if f["rule"] == "D3"]
    assert len(d3) == 1
    assert d3[0]["severity"] == "HIGH"
    assert "TASK-001" in d3[0]["message"]
    assert "REQ-001" in d3[0]["message"]


def test_d3_negative_done_depends_on_done(tmp_path):
    _write(tmp_path, "REQ-001.md", "id: REQ-001\ntype: req\ntitle: base\nstatus: done")
    _write(tmp_path, "TASK-001.md", "id: TASK-001\ntype: task\ntitle: work\nstatus: done\ndepends_on: [REQ-001]")
    findings = detect(load_entries(tmp_path), tmp_path)
    assert [f for f in findings if f["rule"] == "D3"] == []


def test_d4_active_req_without_acceptance(tmp_path):
    _write(tmp_path, "REQ-001.md", "id: REQ-001\ntype: req\ntitle: x\nstatus: active", "Plain prose, no acceptance.")
    findings = detect(load_entries(tmp_path), tmp_path)
    d4 = [f for f in findings if f["rule"] == "D4"]
    assert len(d4) == 2  # missing Acceptance block + missing GWT wording
    assert all(f["severity"] == "MEDIUM" for f in d4)


def test_d4_negative_tasks_draft_reqs_and_valid_reqs():
    findings = detect(load_entries(FIXTURES), FIXTURES)
    assert [f for f in findings if f["rule"] == "D4"] == []


def test_d4_gwt_bold_list_form_clean(tmp_path):
    # Official template style: numbered bold Given/When/Then list.
    _write(
        tmp_path,
        "REQ-001.md",
        "id: REQ-001\ntype: req\ntitle: x\nstatus: active",
        "Body.\n\n## Acceptance\n\n1. **Given** a registered user, **When** credentials are submitted, **Then** a session is issued\n",
    )
    assert [f for f in detect(load_entries(tmp_path), tmp_path) if f["rule"] == "D4"] == []


def test_d4_gwt_table_form_clean(tmp_path):
    _write(
        tmp_path,
        "REQ-001.md",
        "id: REQ-001\ntype: req\ntitle: x\nstatus: active",
        "Body.\n\n## Acceptance\n\n| Given | When | Then |\n| --- | --- | --- |\n| Registered user | Valid credentials | Session issued |\n",
    )
    assert [f for f in detect(load_entries(tmp_path), tmp_path) if f["rule"] == "D4"] == []


def test_d4_gwt_outside_acceptance_does_not_count(tmp_path):
    _write(
        tmp_path,
        "REQ-001.md",
        "id: REQ-001\ntype: req\ntitle: x\nstatus: active",
        "Given the context, When nothing happens, Then nothing changes.\n\n## Acceptance\n\nThe system shall behave correctly.\n",
    )
    d4 = [f for f in detect(load_entries(tmp_path), tmp_path) if f["rule"] == "D4"]
    assert len(d4) == 1
    assert "Given/When/Then" in d4[0]["message"]


def test_d4_gwt_split_across_regions_does_not_count(tmp_path):
    body = (
        "## Acceptance\n\n- Given a user, when the session expires, redirect to login.\n\n"
        "## Other\n\nText.\n\n"
        "## Acceptance\n\nThen the user stays logged in.\n"
    )
    _write(tmp_path, "REQ-001.md", "id: REQ-001\ntype: req\ntitle: x\nstatus: active", body)
    d4 = [f for f in detect(load_entries(tmp_path), tmp_path) if f["rule"] == "D4"]
    assert len(d4) == 1
    assert "Given/When/Then" in d4[0]["message"]


def test_d4_gwt_case_insensitive(tmp_path):
    _write(
        tmp_path,
        "REQ-001.md",
        "id: REQ-001\ntype: req\ntitle: x\nstatus: active",
        "## Acceptance\n\n- given a user, WHEN the app restarts, then the session persists.\n",
    )
    assert [f for f in detect(load_entries(tmp_path), tmp_path) if f["rule"] == "D4"] == []


def test_d4_region_boundary_is_same_or_higher_heading(tmp_path):
    # A `### Acceptance` region must not swallow a following `##` section.
    body = (
        "### Acceptance\n\nThe system shall behave.\n\n"
        "## Notes\n\nGiven something, when it happens, then record it.\n"
    )
    _write(tmp_path, "REQ-001.md", "id: REQ-001\ntype: req\ntitle: x\nstatus: active", body)
    d4 = [f for f in detect(load_entries(tmp_path), tmp_path) if f["rule"] == "D4"]
    assert len(d4) == 1
    assert "Given/When/Then" in d4[0]["message"]


def test_d5_residue_marker():
    findings = detect(load_entries(FIXTURES), FIXTURES)
    d5 = [f for f in findings if f["rule"] == "D5"]
    assert len(d5) == 1
    assert d5[0]["severity"] == "HIGH"
    assert d5[0]["entry_id"] == "REQ-003"
    assert "TODO" in d5[0]["message"]


def test_d5_needs_clarification_bare(tmp_path):
    _write(
        tmp_path,
        "REQ-001.md",
        "id: REQ-001\ntype: req\ntitle: x\nstatus: draft",
        "Pending [NEEDS CLARIFICATION] here.",
    )
    d5 = [f for f in detect(load_entries(tmp_path), tmp_path) if f["rule"] == "D5"]
    assert len(d5) == 1
    assert d5[0]["severity"] == "HIGH"
    assert "NEEDS CLARIFICATION" in d5[0]["message"]


def test_d5_needs_clarification_with_question(tmp_path):
    # Official Spec Kit placeholder form: github/spec-kit commit
    # 0cc9a6a1159471a3108b9bad718ba17006dd6039 (v1.0.8), templates/spec-template.md lines 98-99.
    _write(
        tmp_path,
        "REQ-001.md",
        "id: REQ-001\ntype: req\ntitle: x\nstatus: draft",
        "System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]",
    )
    d5 = [f for f in detect(load_entries(tmp_path), tmp_path) if f["rule"] == "D5"]
    assert len(d5) == 1
    assert d5[0]["severity"] == "HIGH"


def test_d5_needs_clarification_case_and_whitespace(tmp_path):
    _write(
        tmp_path,
        "REQ-001.md",
        "id: REQ-001\ntype: req\ntitle: x\nstatus: draft",
        "Retention for [needs  clarification : 90 days] pending decision.",
    )
    d5 = [f for f in detect(load_entries(tmp_path), tmp_path) if f["rule"] == "D5"]
    assert len(d5) == 1
    assert d5[0]["severity"] == "HIGH"


def test_d5_negative_clean_body(tmp_path):
    _write(tmp_path, "TASK-001.md", "id: TASK-001\ntype: task\ntitle: clean\nstatus: active", "All clear, nothing pending.")
    assert [f for f in detect(load_entries(tmp_path), tmp_path) if f["rule"] == "D5"] == []


def test_d6_undefined_bold_term_low(tmp_path):
    _write(
        tmp_path,
        "REQ-001.md",
        "id: REQ-001\ntype: req\ntitle: x\nstatus: active",
        "Uses **Widget** and **Gadget** here.\n\n## Acceptance\n\n- Given a **Widget**, when it is used, then it works.",
    )
    (tmp_path / "glossary.md").write_text("- **Widget**: a reusable component.\n", encoding="utf-8")
    findings = detect(load_entries(tmp_path), tmp_path)
    d6 = [f for f in findings if f["rule"] == "D6"]
    assert len(d6) == 1
    assert d6[0]["severity"] == "LOW"
    assert "Gadget" in d6[0]["message"]


def test_d6_negative_all_terms_defined(tmp_path):
    _write(
        tmp_path,
        "REQ-001.md",
        "id: REQ-001\ntype: req\ntitle: x\nstatus: active",
        "Uses **Widget** only.\n\n## Acceptance\n\n- Given a **Widget**, when it is used, then it works.",
    )
    (tmp_path / "glossary.md").write_text("- **Widget**: a reusable component.\n", encoding="utf-8")
    assert [f for f in detect(load_entries(tmp_path), tmp_path) if f["rule"] == "D6"] == []


def test_d6_disabled_without_glossary(tmp_path):
    _write(
        tmp_path,
        "REQ-001.md",
        "id: REQ-001\ntype: req\ntitle: x\nstatus: active",
        "Bold **Undefined** term.\n\n## Acceptance\n\n- Given x, when y, then z.",
    )
    assert [f for f in detect(load_entries(tmp_path), tmp_path) if f["rule"] == "D6"] == []


def test_empty_repository_no_findings(tmp_path):
    (tmp_path / "artifacts").mkdir()
    assert detect(load_entries(tmp_path), tmp_path) == []


def test_findings_sorted_by_severity():
    findings = detect(load_entries(FIXTURES), FIXTURES)
    assert [(f["rule"], f["severity"]) for f in findings] == [("D1", "CRITICAL"), ("D5", "HIGH")]
