from specripple.init_host import (
    CLAUDE_COMMAND,
    agents_block,
    managed_paths,
    run_init,
    skill_source_text,
    strip_agents_block,
    thin_shell,
)

SKILL_NAMES = ("aligning-changes", "detecting-conflicts", "resolving-conflicts")


def test_agents_block_has_version_stamp():
    block = agents_block()
    assert block.startswith("<!-- specripple:begin v")
    assert block.rstrip().endswith("<!-- specripple:end -->")
    assert "aligning-changes" in block


def test_upsert_is_idempotent():
    from specripple.init_host import upsert_agents_block

    once = agents_block()
    assert upsert_agents_block(once) == once


def test_upsert_replaces_old_version_block():
    from specripple.init_host import upsert_agents_block

    old = "<!-- specripple:begin v0.0.9 -->\nstale content\n<!-- specripple:end -->\n"
    merged = upsert_agents_block(old)
    assert "v0.0.9" not in merged
    assert "stale content" not in merged
    assert merged == agents_block()


def test_upsert_preserves_existing_content():
    from specripple.init_host import upsert_agents_block

    existing = "# My project\n\nCustom notes here.\n"
    merged = upsert_agents_block(existing)
    assert merged.startswith("# My project\n\nCustom notes here.\n\n")
    assert merged.endswith(agents_block())


def test_strip_removes_block_and_keeps_rest():
    from specripple.init_host import upsert_agents_block

    existing = "# My project\n\nCustom notes here.\n"
    merged = upsert_agents_block(existing)
    stripped, changed = strip_agents_block(merged)
    assert changed
    assert stripped.strip() == existing.strip()


def test_strip_without_block_is_noop():
    stripped, changed = strip_agents_block("# My project\n")
    assert not changed
    assert stripped == "# My project\n"


def test_thin_shell_keeps_frontmatter():
    shell = thin_shell(skill_source_text("aligning-changes"), "aligning-changes")
    assert shell.startswith("---\nname: aligning-changes\n")
    assert ".agents/skills/aligning-changes/SKILL.md" in shell
    assert "# Aligning Changes" not in shell  # body is a pointer, not a copy


def test_unknown_host_raises(tmp_path):
    try:
        run_init(tmp_path, "dsh")
    except ValueError as exc:
        assert "unknown host" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_codex_dry_run_writes_nothing(tmp_path):
    actions = run_init(tmp_path, "codex", dry_run=True)
    assert any("dry" not in a for a in actions)  # actions are plain strings
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / ".agents").exists()


def test_codex_install_creates_block_and_skills(tmp_path):
    actions = run_init(tmp_path, "codex")
    assert any("AGENTS.md" in a for a in actions)
    agents = tmp_path / "AGENTS.md"
    assert agents.read_text(encoding="utf-8") == agents_block()
    for name in SKILL_NAMES:
        skill = tmp_path / ".agents" / "skills" / name / "SKILL.md"
        assert skill.read_text(encoding="utf-8") == skill_source_text(name)
    assert not (tmp_path / ".claude").exists()


def test_codex_reinstall_idempotent(tmp_path):
    run_init(tmp_path, "codex")
    before = (tmp_path / "AGENTS.md").read_bytes()
    actions = run_init(tmp_path, "codex")
    assert (tmp_path / "AGENTS.md").read_bytes() == before
    assert any("already up to date" in a for a in actions)


def test_claude_install_adds_shells_and_command(tmp_path):
    run_init(tmp_path, "claude")
    for name in SKILL_NAMES:
        shell = tmp_path / ".claude" / "skills" / name / "SKILL.md"
        assert shell.read_text(encoding="utf-8") == thin_shell(skill_source_text(name), name)
    command = tmp_path / ".claude" / "commands" / "specripple.md"
    assert command.read_text(encoding="utf-8") == CLAUDE_COMMAND


def test_claude_remove_cleans_managed_files(tmp_path):
    run_init(tmp_path, "claude")
    actions = run_init(tmp_path, "claude", remove=True)
    assert any("strip specripple block" in a for a in actions)
    assert not (tmp_path / "AGENTS.md").read_text(encoding="utf-8").strip()
    for name in SKILL_NAMES:
        assert not (tmp_path / ".agents" / "skills" / name / "SKILL.md").exists()
        assert not (tmp_path / ".claude" / "skills" / name / "SKILL.md").exists()
    assert not (tmp_path / ".claude" / "commands" / "specripple.md").exists()


def test_remove_skips_user_modified_files(tmp_path):
    run_init(tmp_path, "codex")
    skill = tmp_path / ".agents" / "skills" / "aligning-changes" / "SKILL.md"
    skill.write_text("# my customized workflow\n", encoding="utf-8")
    actions = run_init(tmp_path, "codex", remove=True)
    assert any("skip" in a and "aligning-changes" in a for a in actions)
    assert skill.read_text(encoding="utf-8") == "# my customized workflow\n"
    assert not (tmp_path / ".agents" / "skills" / "detecting-conflicts" / "SKILL.md").exists()


def test_managed_paths_match_installed_content(tmp_path):
    run_init(tmp_path, "claude")
    for path, expected in managed_paths(tmp_path, "claude").items():
        assert path.read_text(encoding="utf-8") == expected
