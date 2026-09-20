# specripple

English | [简体中文](README.zh-CN.md)

Change-driven multi-artifact alignment for AI coding agents: modify a requirement, and your agent lists the impact with evidence, propagates edits, resolves conflicts with you, and gates completion on executable acceptance — instead of claiming "done".

One skill is the product. A deterministic zero-LLM CLI does the checking underneath.

## Status

v0.2.0 (2026-09-20): skill-first product — the former three skills are merged into a single `specripple` skill with a self-contained runtime (`scripts/run.py` — no CLI install needed), a content-fingerprinted installer with legacy-skill migration and bundled runtime on every install path (source checkout, skill package, wheel), and onboarding flows. See [docs/architecture.md](docs/architecture.md) and [CHANGELOG.md](CHANGELOG.md).

## Quick start (60 seconds)

```bash
uvx --from git+https://github.com/midiexiangdeliren-crypto/specripple specripple demo
```

No PyPI release (maintainer decision) — uv pulls straight from GitHub.

## Install into your project

**Path A — skill package (recommended).** Get the self-contained package (`specripple build-skill --out dist` from a checkout, or the zip from GitHub releases), unzip it, and copy the top-level `specripple/` directory into your project's `.agents/skills/specripple/`. The skill's `run.py` builds its own cached runtime via uv on first use. Then hand `.agents/skills/specripple/references/onboarding.md` to your agent for first-touch setup (four paths: already configured / import Spec Kit / minimal entries for a plain project / acceptance config only).

**Path B — CLI + installer.**

```bash
uv tool install git+https://github.com/midiexiangdeliren-crypto/specripple
specripple init --host codex      # or --host claude, in your project root
```

`init` copies the skill, writes a versioned marked block into AGENTS.md, and records every managed file with a sha256 fingerprint in `.agents/specripple-manifest.json`. Re-running `init` upgrades; `--remove` uninstalls; files you modified are never touched. Coming from v0.1.1's three-skill install? Re-running `init` migrates it: unmodified legacy skills are removed automatically, modified ones are kept and reported for you to reconcile. Details: [docs/migration.md](docs/migration.md).

## How an alignment run goes

You change a requirement and tell your agent "sync this". The skill drives: `specripple index` → `detect` (report mode) + `impact` (impacted candidates with evidence chains) → the agent edits affected artifacts and code (candidates must end in one of three states: modified / checked-no-change-needed / unconfirmed — unreachable in the graph is not "unaffected") → conflicts resolved one question at a time with rationale entries → gate `detect --fail-on HIGH` + `verify` (FAIL_TO_PASS / PASS_TO_PASS assertions, including a `command` checker that runs your real tests) → a report that distinguishes passed / failed / evidence-insufficient.

## The deterministic core

- `specripple index` — parse `artifacts/**/*.md` (YAML frontmatter: id / type / status / depends_on / links), validate, rebuild `index.json`.
- `specripple impact <ID>` — BFS closure over explicit links plus reverse `depends_on`, with evidence chains. The result is a candidate set, not a verdict.
- `specripple detect` — zero-token rule layer D1–D6 (dangling refs, duplicate ids, state machine, structure, residue markers, glossary) with `--fail-on <level>` as a completion gate. Understands official Spec Kit markers (`**Acceptance Scenarios**:`, `[NEEDS CLARIFICATION: ...]`).
- `specripple verify` — run `assertions.yaml` with file_exists / file_contains / file_not_contains / regex_match / command checkers; any failure exits nonzero. Strict config validation.
- `specripple import-speckit <src>` — convert Spec Kit spec/plan/tasks/constitution into the entry repository (golden-snapshot tested; `##`/`###`/`####` acceptance headings and the bold label all normalized and kept inside their story).
- `specripple build-skill` — build the self-contained skill package (bundled runtime, verified file manifest).
- `specripple init` / `specripple demo` — host installation with migration, and an end-to-end demo with real code.

Exit semantics everywhere: 0 ok / 1 checks failed / 2 config error.

## Verified hosts

- **Codex CLI** — live-tested end to end (autonomous propagation, interactive conflict resolution, and a run where requirements, code, and tests were updated in one dialogue turn with verify green).
- **DeepSeek Harness** (dsh ≥ 0.1.5) — zero-adaptation compatible: `dsh-agent-instructions` reads AGENTS.md, `dsh-skill-filesystem` scans `.agents/skills`.
- **Claude Code** — `init --host claude` generates `.claude/` thin shells and a `/specripple` command; live run deferred (maintainer decision).
- **Copilot / Cursor** — nothing host-specific is generated; they read AGENTS.md and `.agents/skills/` natively. Not live-tested.

## Documentation

- [docs/architecture.md](docs/architecture.md) — components, data flow, host compatibility facts
- [docs/migration.md](docs/migration.md) — install, upgrade from old skills, Spec Kit import, uninstall
- [docs/development-plan.md](docs/development-plan.md) — current state and next phases
- [docs/roadmap.md](docs/roadmap.md) — priorities, the benefit-validation experiment, explicit non-goals
- [docs/archive/pre-skill-product/](docs/archive/pre-skill-product/) — superseded planning documents (byte-identical archive)

## Development

```bash
git clone https://github.com/midiexiangdeliren-crypto/specripple
cd specripple
uv sync
uv run pytest -q
```

No telemetry, no network calls (dependency installation via uv excepted). License: see [docs/roadmap.md](docs/roadmap.md) (pending maintainer decision).
