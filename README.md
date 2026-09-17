# align-kit

Change-driven multi-artifact alignment for AI coding agents: modify a requirement, and every affected artifact (plan / spec / tasks / constitution) stays aligned.

This repository hosts the deterministic core CLI (zero-LLM) plus the host integration layer (`align init` ships a versioned AGENTS.md block and three agent skills; an MCP server is a planned phase-2 layer).

## Status

v0.1.0 — all commands implemented and tested (schema v0): index / impact / detect / verify / demo / init / import-speckit. Live-tested end to end on Codex CLI (non-interactive flow and interactive conflict resolution) and DeepSeek Harness (headless flow and MCP bridge); see "Verified hosts" below.

## Quick start

```bash
uv sync
uv run pytest -q
uv run align demo
```

Try the commands on the bundled mini project:

```bash
uv run align index --root tests/fixtures/mini
uv run align impact REQ-001 --root tests/fixtures/mini
uv run align impact REQ-001 --root tests/fixtures/mini --json
```

## Artifact format (schema v0)

Each artifact is one markdown file with YAML frontmatter:

```markdown
---
id: REQ-001
type: req
title: User login with email and password
status: active
depends_on: [REQ-000]
links:
  - to: TASK-001
    kind: realized-by
    src: manual
---

## Acceptance

- Given ..., when ..., then ...
```

`index.json` is a rebuildable derived artifact (gitignored); rebuild it with `align index`.

## Commands

- `align index` — parse `artifacts/**/*.md`, validate schema, write `index.json`.
- `align impact <ID>` — BFS closure over outgoing links plus reverse `depends_on` edges; reports the impacted artifact set with evidence chains and unresolved references.
- `align detect` — zero-token rule layer: dangling refs, duplicate ids, state-machine violations, structure violations, residue markers, glossary terms; CRITICAL/HIGH/MEDIUM/LOW report.
- `align verify` — run `assertions.yaml` (fail_to_pass / pass_to_pass) with file_exists / file_contains / file_not_contains / regex_match checkers; nonzero exit on any failure.
- `align demo` — copy the bundled demo project to a temp dir and run the full flow end to end.
- `align init --host codex|claude [--remove] [--dry-run]` — install host integration: a versioned marked block in AGENTS.md plus the three skills in `.agents/skills/` (Claude Code additionally gets thin mirrors in `.claude/skills/` and a `/align` command). Idempotent and reversible.
- `align import-speckit <src>` — convert Spec Kit artifacts (spec.md / plan.md / tasks.md / constitution.md) into the entry repository: user stories become REQ entries (P1=active), checkbox tasks become TASK entries wired to their story via `depends_on`, plan and constitution become PLAN/CON entries. Guarded by a golden-snapshot test.

## Host integration

`align init` writes only files it owns. The AGENTS.md block sits between `<!-- align-kit:begin vX.Y.Z -->` and `<!-- align-kit:end -->` markers and is replaced (never duplicated) on re-init. `--remove` strips the block and deletes managed skill files, but skips any file you have modified.

Skills (single source in the package, copied on init):

- `aligning-changes` — the main workflow: impact -> route (L0-L3) -> edit -> detect -> resolve -> verify, with evidence-before-declaration discipline.
- `detecting-conflicts` — the six semantic checks (duplication, ambiguity, underspecification, constitution alignment, coverage gaps, inconsistency) that the rule layer cannot catch.
- `resolving-conflicts` — one-question-at-a-time resolution protocol with options, recommendations, and rationale entries.

## Verified hosts

Live runs against a demo-derived project (change an entry, agent propagates autonomously, detect/verify green):

- **Codex CLI** (`align init --host codex`): agent reads the skills unprompted, runs index/impact/edits/detect/verify itself, adds rationale entries for breaking changes per CON, and balances assertions.yaml. Both the autonomous flow and the interactive resolution protocol (one question, options, recommendation, RAT entry) behaved as designed. Note: the workspace sandbox may block the bundled apply-patch helper; agents typically fall back to the sandbox-accessible copy under `~/.codex/.sandbox-bin/`.
- **DeepSeek Harness** (dsh >= 0.1.5, headless profile): natively compatible with `align init` output with zero adaptation — `dsh-agent-instructions` reads AGENTS.md by default and `dsh-skill-filesystem` scans `<project>/.agents/skills`. MCP servers can be attached per profile via a `dsh-mcp-client` insert in the profile's `cordis.patch.yml` (stdio; on Windows wrap the command with `cmd /c`).
- **Claude Code** (`align init --host claude`): installs thin skill mirrors in `.claude/skills/` and a `/align` command; live run deferred.
