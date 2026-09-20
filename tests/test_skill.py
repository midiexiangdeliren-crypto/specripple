"""Single-skill entry integrity: one entry point must reach every needed file."""

import re
from pathlib import Path

from specripple.init_host import SKILL_SOURCE_DIR, skill_source_files

REQUIRED_REFERENCES = (
    "references/onboarding.md",
    "references/conflict-checks.md",
    "references/conflict-resolution.md",
    "references/artifact-format.md",
)
REQUIRED_TEMPLATES = (
    "assets/templates/req-entry.md",
    "assets/templates/rat-entry.md",
    "assets/templates/assertions.yaml",
)


def _skill_text() -> str:
    return skill_source_files()["SKILL.md"]


def test_frontmatter_names_the_single_entry():
    text = _skill_text()
    parts = text.split("---", 2)
    assert len(parts) == 3 and parts[0].strip() == ""
    assert re.search(r"^name:\s*specripple\s*$", parts[1], re.MULTILINE)
    assert re.search(r"^description:\s*\S", parts[1], re.MULTILINE)


def test_every_path_mentioned_in_skill_md_exists():
    text = _skill_text()
    mentioned = set(re.findall(r"(?:references|assets|scripts)/[\w./-]+", text))
    assert mentioned, "SKILL.md must reference its support files explicitly"
    for rel in mentioned:
        assert (SKILL_SOURCE_DIR / rel).is_file(), f"SKILL.md references missing file {rel}"


def test_all_required_support_files_present():
    for rel in REQUIRED_REFERENCES + REQUIRED_TEMPLATES + ("scripts/run.py",):
        assert (SKILL_SOURCE_DIR / rel).is_file(), rel


def test_skill_routes_onboarding_and_checks_and_resolution():
    text = _skill_text()
    assert "references/onboarding.md" in text
    assert "references/conflict-checks.md" in text
    assert "references/conflict-resolution.md" in text
    assert "references/artifact-format.md" in text


def test_skill_has_dual_tool_entry_and_gate():
    text = _skill_text()
    assert "scripts/run.py" in text          # self-contained package entry
    assert "uv tool install git+https://github.com/midiexiangdeliren-crypto/specripple" in text
    assert "--fail-on HIGH" in text          # completion gate
    assert "verify" in text                  # acceptance run
    assert "--root" in text                  # business projects addressed explicitly


def test_onboarding_references_templates_that_exist():
    text = (SKILL_SOURCE_DIR / "references" / "onboarding.md").read_text(encoding="utf-8")
    mentioned = set(re.findall(r"assets/templates/[\w.-]+", text))
    assert mentioned, "onboarding must point at its templates"
    for rel in mentioned:
        assert (SKILL_SOURCE_DIR / rel).is_file(), rel


def test_no_old_skill_hard_dependencies():
    old_names = ("aligning-changes", "detecting-conflicts", "resolving-conflicts")
    for rel, text in skill_source_files().items():
        for old in old_names:
            assert old not in text, f"{rel} still references old skill {old}"


def test_references_are_self_consistent():
    checks = (SKILL_SOURCE_DIR / "references" / "conflict-resolution.md").read_text(encoding="utf-8")
    assert "assets/templates/rat-entry.md" in checks
    for rel in ("conflict-checks.md", "conflict-resolution.md", "onboarding.md", "artifact-format.md"):
        assert (SKILL_SOURCE_DIR / "references" / rel).is_file()


def test_templates_are_loadable_shapes():
    req = (SKILL_SOURCE_DIR / "assets" / "templates" / "req-entry.md").read_text(encoding="utf-8")
    assert req.startswith("---\nid: REQ-NNN")
    assert "## Acceptance" in req and "**Given**" in req
    rat = (SKILL_SOURCE_DIR / "assets" / "templates" / "rat-entry.md").read_text(encoding="utf-8")
    assert "id: RAT-NNN" in rat and "kind: clarifies" in rat
    assertions = (SKILL_SOURCE_DIR / "assets" / "templates" / "assertions.yaml").read_text(encoding="utf-8")
    assert "fail_to_pass:" in assertions and "pass_to_pass:" in assertions
