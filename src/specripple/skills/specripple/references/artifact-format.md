# Artifact and assertion formats

Everything the deterministic core parses. Keep entries in these shapes or `index` will fail.

## Entry repository layout

- `artifacts/<kind>/<ID>.md` — one markdown file per entry, kinds: `spec/` (REQ, PLAN), `tasks/` (TASK), `constitution/` (CON), `rationale/` (RAT). `index --root .` writes the derived `index.json` at the project root; never edit it by hand.

## Entry file shape

```markdown
---
id: REQ-002
type: req
title: Email login
status: active
depends_on: [REQ-001]
links:
  - to: TASK-002
    kind: realized-by
    src: manual
---
## Description

...

## Acceptance

1. **Given** a registered user **When** login succeeds **Then** the dashboard loads
```

- `id`: `REQ|TASK|PLAN|CON|RAT` + `-` + 3 digits. Duplicate ids are a CRITICAL finding (D2).
- `type`: `req` | `task` | `plan` | `con` | `rationale`.
- `status`: `draft` | `active` | `done` | `deprecated`.
- `depends_on`: list of ids; every id must exist (D1 dangles are CRITICAL). A `done` entry must not depend on a draft/active upstream (D3, HIGH).
- `links`: list of `{to, kind, src}`; `kind` is one of `realized-by`, `refines`, `verifies`, `clarifies`; `src` defaults to `manual` (the importer writes its own source value).
- Active reqs need a `##`/`###` `Acceptance` region containing Given/When/Then as whole words inside that region (D4, MEDIUM). Bold list form `1. **Given** ... **When** ... **Then** ...` and tables both work; the wording must sit inside the Acceptance region, not elsewhere in the file.
- Unresolved markers `TODO`, `FIXME`, `[NEEDS CLARIFICATION]` (with or without the question text) are HIGH findings (D5) — they keep parked decisions visible.
- If `glossary.md` exists at the project root, every bold `**term**` used in entries must be defined there (D6, LOW).

## assertions.yaml (project root)

```yaml
fail_to_pass:
  - checker: file_contains
    file: artifacts/spec/REQ-002.md
    text: "minimum length of 12"
pass_to_pass:
  - checker: command
    command: python tests/test_login.py
```

- Exactly two top-level keys: `fail_to_pass` (must pass after the change; may fail before) and `pass_to_pass` (must stay green). Unknown keys, non-list values, empty file, or both groups empty are config errors (exit 2). Omitted group means empty.
- `checker` is one of: `file_exists`, `file_contains`, `file_not_contains`, `regex_match`, `command`.
- `file_contains`/`file_not_contains`/`regex_match` need `file` (+ `text`/`pattern`); `command` runs `command` from the project root and fails on a nonzero exit code (its stdout is passed through verbatim and is not itself checked). Paths are relative to the project root (`--root`).
- Exit codes: `0` all pass, `1` any assertion failed, `2` config missing/malformed. Validation completes before any check runs — a later invalid assertion means nothing executes.

## RAT rationale entries

One per resolved conflict (`RAT-NNN`, type `rationale`): the conflict, the chosen option, why, and `links` with kind `clarifies` pointing at every entry the decision affected. Template: `assets/templates/rat-entry.md`. Rebuild the index after creating one.

## Importing Spec Kit documents

`import-speckit <src dir> --root .` maps: spec.md overview → REQ overview entry, each `### User Story N` → REQ (P1 → active, others draft); `##`/`###`/`####` `Acceptance Scenarios` headings and the bold `**Acceptance Scenarios**:` label are normalized to `## Acceptance` inside their story; tasks.md checkboxes → TASK (unchecked draft, checked done, `depends_on` = owning story's REQ); plan.md → PLAN-001; constitution.md → CON-001. Import refuses to overwrite a non-empty `artifacts/`.
