# Changelog

Not published to PyPI (maintainer decision); install via
`uv tool install git+https://github.com/midiexiangdeliren-crypto/specripple`.

## v0.2.0 (git tag v0.2.0, 2026-09-20)

Skill-first product release: the three host skills merge into a single
`specripple` skill with a self-contained bundled runtime, a
fingerprint-manifest installer, and onboarding flows.

### Added

- Single skill entry `src/specripple/skills/specripple/` (SKILL.md +
  `scripts/run.py` self-contained launcher + references + templates). The
  former three-skill set is archived verbatim under `src/specripple/legacy/`,
  including the e49998a release variants so migration matches every released
  revision, not only the latest text.
- `specripple build-skill`: assembles the self-contained distribution package
  (skill files + bundled runtime: pyproject.toml + uv.lock + src/specripple +
  VERSION) and verifies it against an explicit required-file manifest. The
  installer reuses the same assembly plan.
- Wheel installs bundle the runtime too: the wheel force-includes the
  runtime's build inputs as `specripple/_runtime_src/` package data, and
  `init` assembles the runtime from a fallback chain (source checkout ->
  installed skill's own runtime -> wheel payload), so the installed skill's
  `run.py` works without any global CLI.
- Onboarding flows (`references/onboarding.md`): four first-touch paths,
  including minimal entry onboarding for a plain project.
- Installer manifest `.agents/specripple-manifest.json` (version + per-file
  sha256) with a reinstall guard: unmodified managed files upgrade, files the
  user modified (or of unknown origin) are kept and reported as conflicts,
  never overwritten. Legacy three-skill migration: unmodified skills are
  removed, modified ones kept with a conflict report. `--remove` and
  `--dry-run` semantics; Claude mirror + `/specripple` command cleanup.
- `tests/test_distribution.py`: real-distribution-path regression — build
  wheel -> install into a fresh venv -> `init` a temporary business project ->
  run the installed skill's `run.py` and assert success (0), gate-failure (1),
  and config-error (2) exit codes.
- Docs restructure: architecture / development-plan / migration / roadmap +
  `docs/archive/pre-skill-product/` (byte-identical archives of superseded
  planning docs); bilingual skill-first READMEs.

### Fixed

- Reinstall no longer overwrites user-modified managed files (previous
  installer only consulted fingerprints on `--remove`).
- `init`-installed skill runs standalone: the bundled runtime was missing
  outside source checkouts and `run.py` exited 2.
- Legacy migration recognition covers all released legacy revisions.
- import-speckit: `##`/`###`-level Acceptance Scenarios headings are
  recognized before story-boundary logic; acceptance content no longer leaks
  into the "spec overview" section.
- Install docs: the zip's top-level directory is `specripple/` (not
  `skills/specripple/`); `index` writes `index.json` at the project root; the
  `command` checker does not fail on empty stdout (nonzero exit only);
  architecture no longer implies a PyPI `uvx specripple`.

### Tests

- 150 green, including the real-distribution e2e. Host replay evidence for
  the new single skill (plain project -> init -> codex exec onboarding ->
  requirement change to green gates) lives in `manual-tests/skill-run/`.

## v0.1.1 (git tag v0.1.1)

Maintenance round (commit 6d996a4): unified verify exit semantics, stricter
verify config validation, Spec Kit official-format compatibility,
`detect --fail-on` gate, install commands switched to git direct install
(no PyPI). Followed pre-0.2.0 by the import boundary fix above.

## v0.1.0 (git tag v0.1.0)

Initial release after the align-kit -> specripple rename (commit 6c7631a):
deterministic core CLI (index / impact / detect / verify / import-speckit /
demo / init), schema v0 entry repository, six detection rules, dual-group
assertions with the command checker, demo project with real code, three-host
install.
