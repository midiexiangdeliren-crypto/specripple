---
name: aligning-changes
description: Use when the user modifies a requirement, spec, plan, or task artifact and asks to sync, align, propagate, or update dependent artifacts or code; or when a change request touches entries managed by specripple (artifacts/ entry repository).
---

# Aligning Changes

Propagate a requirement change through every affected artifact, then prove nothing broke.

## Preconditions

- Entry repository under `artifacts/`: one markdown file per entry (REQ/TASK/PLAN/CON/RAT), YAML frontmatter, `## Acceptance` with Given/When/Then for active reqs.
- `specripple` CLI available. No install needed: `uvx --from git+https://github.com/midiexiangdeliren-crypto/specripple specripple <command>`; or install once with `uv tool install git+https://github.com/midiexiangdeliren-crypto/specripple` and call `specripple <command>` directly. (`uv run specripple` works only inside the specripple source checkout.) All commands take `--root <project root>` (use `.` when the working directory is the project root) and support `--json`.
- If `artifacts/` is empty, create the entries first (or convert Spec Kit output with import-speckit). Never sync an empty repository.

## Workflow

1. **Index** - run `specripple index --root .`. Fix any parse, schema, or duplicate-id errors it reports before continuing; they mean the repository is not well-formed.
2. **Baseline + impact** - run `specripple detect --root .` once (report mode, no `--fail-on`) to record pre-existing findings (so you can tell them apart from what you introduce). Then run `specripple impact <ID> --root .` for each changed entry. The impact set is your work queue; every item comes with an evidence chain explaining why it is affected.
3. **Route each impacted entry by change class:**

   | Class | Situation | Action |
   | --- | --- | --- |
   | L0 | Constant/text swap (id, title wording, numbers) | Apply the same replacement mechanically to each affected entry |
   | L1 | Single-entry semantics change | Rewrite that entry minimally; keep EARS + Acceptance valid |
   | L2 | Cross-entry structure change (new/removed dependencies, split or merged entries) | Revise incrementally, entry by entry; keep `depends_on`/`links` consistent |
   | L3 | Goal-level or constitution conflict | Stop editing. Invoke resolving-conflicts first, then resume here |

4. **Edit** - make the minimal diff on each impacted file. When a relationship changes, update frontmatter `depends_on`/`links` in the same edit. Never leave an impact-queue item untouched without an explicit reason recorded in your final report.
5. **Proposal notes** - for every L1+ edit, note: root cause, the expected fix, what could break, and the acceptance cases that would catch it. These notes feed resolution dialogue and review.
6. **Detect** - run `specripple detect --root .`. Fix every CRITICAL/HIGH finding you introduced. Then run the detecting-conflicts skill checklist for semantic issues the rule layer cannot see (duplication, ambiguity, underspecification, constitution alignment, coverage gaps, inconsistency).
7. **Verify** - run `specripple verify --root .`. fail_to_pass assertions must pass; pass_to_pass must stay green. If your change altered behavior that assertions.yaml should cover, add or update assertions in the same turn.
8. **Evidence before declaration** - do not announce completion until `specripple index`, `specripple impact`, `specripple detect --root . --fail-on HIGH`, and `specripple verify` have all been run in this turn and their outputs support the claim. The `--fail-on HIGH` gate exits 1 while any CRITICAL/HIGH finding remains: a nonzero exit means completion must not be declared. Paste the verify summary as evidence.

## Hard rules

- Never make a warning disappear by editing the warning's target without fixing the underlying inconsistency.
- Never mark an entry done while an upstream dependency is draft/active (rule D3).
- Dangling references (D1) must be fixed or explicitly resolved with the user - never silently dropped.
- If propagation requires a user decision, stop at the decision point and ask; do not guess.
- Sandbox note (Codex and similar): writing to `artifacts/` and running `specripple` may need write approval - request it once, up front, for the whole workflow.
