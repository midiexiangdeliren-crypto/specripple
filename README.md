# align-kit

Change-driven multi-artifact alignment for AI coding agents: modify a requirement, and every affected artifact (plan / spec / tasks / constitution) stays aligned.

This repository hosts the deterministic core CLI (zero-LLM). Host integrations (AGENTS.md blocks, agent skills, MCP server) are planned layers on top.

## Status

v0.1.0 — work in progress. Schema v0 with index / impact / detect / verify / demo.

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

## Host integration

`align init` writes only files it owns. The AGENTS.md block sits between `<!-- align-kit:begin vX.Y.Z -->` and `<!-- align-kit:end -->` markers and is replaced (never duplicated) on re-init. `--remove` strips the block and deletes managed skill files, but skips any file you have modified.

Skills (single source in the package, copied on init):

- `aligning-changes` — the main workflow: impact -> route (L0-L3) -> edit -> detect -> resolve -> verify, with evidence-before-declaration discipline.
- `detecting-conflicts` — the six semantic checks (duplication, ambiguity, underspecification, constitution alignment, coverage gaps, inconsistency) that the rule layer cannot catch.
- `resolving-conflicts` — one-question-at-a-time resolution protocol with options, recommendations, and rationale entries.
