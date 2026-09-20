import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from specripple import __version__
from specripple.init_host import (
    CLAUDE_COMMAND,
    MANIFEST_REL,
    SKILL_NAME,
    agents_block,
    managed_paths,
    run_init,
    skill_source_files,
    strip_agents_block,
    thin_shell,
    upsert_agents_block,
)
from specripple.legacy import LEGACY_SKILL_NAMES, legacy_skill_text, legacy_skill_variants

LEGACY_DIRS = ("aligning-changes", "detecting-conflicts", "resolving-conflicts")


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _skill_text() -> str:
    return skill_source_files()["SKILL.md"]


def test_agents_block_has_version_stamp():
    block = agents_block()
    assert block.startswith("<!-- specripple:begin v")
    assert block.rstrip().endswith("<!-- specripple:end -->")
    assert ".agents/skills/specripple/SKILL.md" in block


def test_upsert_is_idempotent():
    once = agents_block()
    assert upsert_agents_block(once) == once


def test_upsert_replaces_old_version_block():
    old = "<!-- specripple:begin v0.0.9 -->\nstale content\n<!-- specripple:end -->\n"
    merged = upsert_agents_block(old)
    assert "v0.0.9" not in merged
    assert "stale content" not in merged
    assert merged == agents_block()


def test_upsert_preserves_existing_content():
    existing = "# My project\n\nCustom notes here.\n"
    merged = upsert_agents_block(existing)
    assert merged.startswith("# My project\n\nCustom notes here.\n\n")
    assert merged.endswith(agents_block())


def test_strip_removes_block_and_keeps_rest():
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
    shell = thin_shell(_skill_text(), SKILL_NAME)
    assert shell.startswith("---\nname: specripple\n")
    assert ".agents/skills/specripple/SKILL.md" in shell
    assert "# specripple — change-driven alignment" not in shell  # pointer, not a copy


def test_unknown_host_raises(tmp_path):
    try:
        run_init(tmp_path, "dsh")
    except ValueError as exc:
        assert "unknown host" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_codex_dry_run_writes_nothing(tmp_path):
    actions = run_init(tmp_path, "codex", dry_run=True)
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / ".agents").exists()
    assert not (tmp_path / ".claude").exists()
    assert actions  # actions were still reported


def test_codex_install_creates_block_skill_and_manifest(tmp_path):
    actions = run_init(tmp_path, "codex")
    assert any("AGENTS.md" in a for a in actions)
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == agents_block()
    for rel, content in skill_source_files().items():
        installed = tmp_path / ".agents" / "skills" / SKILL_NAME / rel
        assert installed.read_text(encoding="utf-8") == content, rel
    # run.py and every reference/template ship with the install
    for rel in ("scripts/run.py", "references/onboarding.md", "references/conflict-checks.md",
                "references/conflict-resolution.md", "references/artifact-format.md",
                "assets/templates/req-entry.md", "assets/templates/rat-entry.md",
                "assets/templates/assertions.yaml"):
        assert (tmp_path / ".agents" / "skills" / SKILL_NAME / rel).is_file(), rel
    manifest = json.loads((tmp_path / MANIFEST_REL).read_text(encoding="utf-8"))
    assert manifest["version"] == __version__
    assert manifest["files"][".agents/skills/specripple/SKILL.md"]
    assert not (tmp_path / ".claude").exists()


def test_codex_reinstall_idempotent(tmp_path):
    run_init(tmp_path, "codex")
    before = (tmp_path / "AGENTS.md").read_bytes()
    actions = run_init(tmp_path, "codex")
    assert (tmp_path / "AGENTS.md").read_bytes() == before
    assert any("already up to date" in a for a in actions)
    assert not any("migrate" in a for a in actions)


def test_claude_install_adds_shell_command_and_manifest(tmp_path):
    run_init(tmp_path, "claude")
    shell = tmp_path / ".claude" / "skills" / SKILL_NAME / "SKILL.md"
    assert shell.read_text(encoding="utf-8") == thin_shell(_skill_text(), SKILL_NAME)
    command = tmp_path / ".claude" / "commands" / "specripple.md"
    assert command.read_text(encoding="utf-8") == CLAUDE_COMMAND
    manifest = json.loads((tmp_path / MANIFEST_REL).read_text(encoding="utf-8"))
    assert ".claude/commands/specripple.md" in manifest["files"]
    assert ".claude/skills/specripple/SKILL.md" in manifest["files"]


def test_claude_remove_cleans_managed_files(tmp_path):
    run_init(tmp_path, "claude")
    actions = run_init(tmp_path, "claude", remove=True)
    assert any("strip specripple block" in a for a in actions)
    assert not (tmp_path / "AGENTS.md").read_text(encoding="utf-8").strip()
    assert not (tmp_path / ".agents" / "skills" / SKILL_NAME / "SKILL.md").exists()
    assert not (tmp_path / ".claude" / "skills" / SKILL_NAME / "SKILL.md").exists()
    assert not (tmp_path / ".claude" / "commands" / "specripple.md").exists()
    assert not (tmp_path / MANIFEST_REL).exists()
    # empty managed dirs are pruned, the roots stay
    assert not (tmp_path / ".agents" / "skills" / SKILL_NAME).exists()
    assert (tmp_path / ".agents").exists()


def test_remove_skips_user_modified_files(tmp_path):
    run_init(tmp_path, "codex")
    skill = tmp_path / ".agents" / "skills" / SKILL_NAME / "SKILL.md"
    skill.write_text("# my customized workflow\n", encoding="utf-8")
    actions = run_init(tmp_path, "codex", remove=True)
    assert any("skip" in a and SKILL_NAME in a for a in actions)
    assert skill.read_text(encoding="utf-8") == "# my customized workflow\n"
    assert not (tmp_path / ".agents" / "skills" / SKILL_NAME / "references" / "onboarding.md").exists()


def test_remove_without_manifest_falls_back_to_content_compare(tmp_path):
    run_init(tmp_path, "codex")
    (tmp_path / MANIFEST_REL).unlink()
    actions = run_init(tmp_path, "codex", remove=True)
    assert any("remove" in a for a in actions)
    assert not (tmp_path / ".agents" / "skills" / SKILL_NAME / "SKILL.md").exists()


def _write_legacy_install(tmp_path, host: str = "codex", modified: str | None = None) -> None:
    for name in LEGACY_DIRS:
        original = legacy_skill_text(name)
        text = modified if (modified is not None and name == "aligning-changes") else original
        path = tmp_path / ".agents" / "skills" / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if host == "claude":
            mirror = tmp_path / ".claude" / "skills" / name / "SKILL.md"
            mirror.parent.mkdir(parents=True, exist_ok=True)
            mirror.write_text(thin_shell(original, name), encoding="utf-8")


def test_unmodified_legacy_skills_are_migrated_away(tmp_path):
    _write_legacy_install(tmp_path)
    actions = run_init(tmp_path, "codex")
    migrated = [a for a in actions if "migrate: remove legacy skill" in a]
    assert len(migrated) == 3, migrated
    for name in LEGACY_DIRS:
        assert not (tmp_path / ".agents" / "skills" / name).exists()
    assert (tmp_path / ".agents" / "skills" / SKILL_NAME / "SKILL.md").is_file()


def test_modified_legacy_skill_is_kept_and_reported(tmp_path):
    _write_legacy_install(tmp_path, modified="# my customized workflow\n")
    actions = run_init(tmp_path, "codex")
    kept = [a for a in actions if "kept" in a and "aligning-changes" in a]
    assert len(kept) == 1, actions
    assert "two workflows" in kept[0] or "resolve the overlap" in kept[0]
    migrated = [a for a in actions if "migrate: remove legacy skill" in a]
    assert len(migrated) == 2, migrated
    kept_file = tmp_path / ".agents" / "skills" / "aligning-changes" / "SKILL.md"
    assert kept_file.read_text(encoding="utf-8") == "# my customized workflow\n"
    # new skill installed alongside; conflict is visible in the action report
    assert (tmp_path / ".agents" / "skills" / SKILL_NAME / "SKILL.md").is_file()


def test_claude_legacy_mirrors_migrate_too(tmp_path):
    _write_legacy_install(tmp_path, host="claude")
    actions = run_init(tmp_path, "claude")
    migrated = [a for a in actions if "migrate: remove legacy skill" in a]
    assert len(migrated) == 6, migrated  # 3 x (.agents original + .claude mirror)
    assert not (tmp_path / ".claude" / "skills" / "aligning-changes").exists()


FORBIDDEN_LEGACY = ("uvx align", "uv run align", "align-kit")
OLD_SKILL_NAMES = ("aligning-changes", "detecting-conflicts", "resolving-conflicts")


def test_no_legacy_command_or_package_references():
    sources = [agents_block(), CLAUDE_COMMAND] + list(skill_source_files().values())
    for text in sources:
        for forbidden in FORBIDDEN_LEGACY:
            assert forbidden not in text, forbidden
        for old_name in OLD_SKILL_NAMES:
            assert old_name not in text, old_name


def test_install_instructions_use_github_distribution():
    block = agents_block()
    assert "uvx --from git+https://github.com/midiexiangdeliren-crypto/specripple specripple" in block
    assert "uv tool install git+https://github.com/midiexiangdeliren-crypto/specripple" in block
    assert "--root" in block  # business projects are addressed via --root
    skill = _skill_text()
    assert "uvx --from git+https://github.com/midiexiangdeliren-crypto/specripple specripple" in skill
    assert "uv tool install git+https://github.com/midiexiangdeliren-crypto/specripple" in skill


def test_detect_gate_instruction_present():
    assert "--fail-on HIGH" in agents_block()
    assert "--fail-on HIGH" in _skill_text()


def test_managed_paths_match_installed_content(tmp_path):
    run_init(tmp_path, "claude")
    for path, expected in managed_paths(tmp_path, "claude").items():
        assert path.read_text(encoding="utf-8") == expected


def test_reinstall_preserves_user_modified_managed_file(tmp_path):
    run_init(tmp_path, "codex")
    ref = tmp_path / ".agents" / "skills" / SKILL_NAME / "references" / "onboarding.md"
    ref.write_text("# my onboarding customization\n", encoding="utf-8")
    actions = run_init(tmp_path, "codex")
    assert ref.read_text(encoding="utf-8") == "# my onboarding customization\n"
    kept = [a for a in actions if "onboarding.md" in a and ("conflict" in a or "keep" in a)]
    assert kept, actions
    remove_actions = run_init(tmp_path, "codex", remove=True)
    assert ref.exists()
    assert any("onboarding.md" in a and "skip" in a for a in remove_actions)


def test_upgrade_rewrites_file_matching_previous_manifest_fingerprint(tmp_path):
    run_init(tmp_path, "codex")
    ref = tmp_path / ".agents" / "skills" / SKILL_NAME / "references" / "conflict-checks.md"
    new_content = ref.read_text(encoding="utf-8")
    old_release_content = new_content + "\n<!-- older released revision -->\n"
    ref.write_text(old_release_content, encoding="utf-8")
    manifest_file = tmp_path / MANIFEST_REL
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    rel = ".agents/skills/specripple/references/conflict-checks.md"
    manifest["files"][rel] = _fingerprint(old_release_content)
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    actions = run_init(tmp_path, "codex")
    assert ref.read_text(encoding="utf-8") == new_content
    assert any("conflict-checks.md" in a and a.startswith("upgrade") for a in actions), actions
    assert not any(a.startswith("conflict:") and "conflict-checks.md" in a for a in actions), actions


def test_unknown_content_without_manifest_record_is_kept_on_reinstall(tmp_path):
    run_init(tmp_path, "codex")
    (tmp_path / MANIFEST_REL).unlink()
    ref = tmp_path / ".agents" / "skills" / SKILL_NAME / "references" / "onboarding.md"
    ref.write_text("# customized before any manifest\n", encoding="utf-8")
    actions = run_init(tmp_path, "codex")
    assert ref.read_text(encoding="utf-8") == "# customized before any manifest\n"
    assert any("onboarding.md" in a and ("conflict" in a or "keep" in a) for a in actions), actions


def test_runtime_is_installed_with_init(tmp_path):
    run_init(tmp_path, "codex")
    runtime = tmp_path / ".agents" / "skills" / SKILL_NAME / "runtime"
    assert (runtime / "pyproject.toml").is_file()
    assert (runtime / "uv.lock").is_file()
    assert (runtime / "VERSION").is_file()
    assert (runtime / "src" / "specripple" / "cli.py").is_file()
    assert not list(runtime.rglob("__pycache__"))
    manifest = json.loads((tmp_path / MANIFEST_REL).read_text(encoding="utf-8"))
    for rel in (
        ".agents/skills/specripple/runtime/pyproject.toml",
        ".agents/skills/specripple/runtime/uv.lock",
        ".agents/skills/specripple/runtime/src/specripple/cli.py",
    ):
        assert rel in manifest["files"], rel


def test_init_only_install_runs_skill_without_global_cli(tmp_path):
    run_init(tmp_path, "codex")
    shutil.copytree(Path(__file__).parent / "fixtures" / "mini", tmp_path, dirs_exist_ok=True)
    script = tmp_path / ".agents" / "skills" / SKILL_NAME / "scripts" / "run.py"
    proc = subprocess.run(
        [sys.executable, str(script), "detect", "--root", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_legacy_variants_match_every_released_revision():
    variant_counts = {name: len(legacy_skill_variants(name)) for name in LEGACY_SKILL_NAMES}
    # the maintenance round edited aligning-changes and detecting-conflicts, so
    # both released revisions must be known; resolving-conflicts shipped once
    assert variant_counts["aligning-changes"] == 2
    assert variant_counts["detecting-conflicts"] == 2
    assert variant_counts["resolving-conflicts"] >= 1
    for name, count in variant_counts.items():
        assert len(set(legacy_skill_variants(name))) == count  # no duplicate variants


def test_unmodified_legacy_install_of_older_release_migrates(tmp_path):
    for name in LEGACY_SKILL_NAMES:
        for index, variant in enumerate(legacy_skill_variants(name)):
            project = tmp_path / f"{name}-{index}"
            skill_dir = project / ".agents" / "skills" / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(variant, encoding="utf-8")
            actions = run_init(project, "codex")
            assert any("migrate: remove legacy skill" in a and name in a for a in actions), (name, index, actions)
            assert not skill_dir.exists()
