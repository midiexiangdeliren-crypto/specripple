# align-kit

Change-driven multi-artifact alignment for AI coding agents: modify a requirement, and every affected artifact (plan / spec / tasks / constitution) stays aligned.

This repository hosts the deterministic core CLI (zero-LLM). Host integrations (AGENTS.md blocks, agent skills, MCP server) are planned layers on top.

## Status

v0.1.0 — work in progress. Schema v0 with `align index` and `align impact`.

## Quick start

```bash
uv sync
uv run pytest -q
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
