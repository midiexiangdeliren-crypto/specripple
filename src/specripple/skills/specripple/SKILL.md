---
name: specripple
description: Use when the user asks to change a requirement or behavior and sync related specs/artifacts/code/tests; when asked to align, propagate, or update artifacts managed by specripple; when asked to check artifacts for conflicts, deviations, or coverage gaps; or when asked to set up specripple in a project or import Spec Kit documents. Do not use for ordinary Q&A, unrelated refactoring, or typo-only edits that touch no managed behavior.
---

# specripple — change-driven alignment (single skill entry)

Propagate a requirement change through every affected artifact (and the code and tests they govern), then prove nothing broke with deterministic checks. The CLI owns structure; you own semantics and editing. You do not need to know the command order in advance — this file and the reference you need at each step are enough.

## Tool entry (run every specripple command through one of these)

- Self-contained skill package (this skill dir bundles `runtime/`):
  `python <this skill dir>/scripts/run.py <command> --root <project root>`
- Installed CLI:
  `specripple <command> --root <project root>`
  (GitHub distribution, no PyPI: `uvx --from git+https://github.com/midiexiangdeliren-crypto/specripple specripple <command>`, or install once with `uv tool install git+https://github.com/midiexiangdeliren-crypto/specripple`.)
- If `scripts/run.py` reports a missing runtime, use the installed CLI instead. If neither path works, report the environment failure and stop — never claim checks passed without running them.
- Every command takes `--root <project root>` (use `.` when the working directory is the project root) and `--json`. Exit codes: `0` ok, `1` checks failed (assertions failed, or findings at the `--fail-on` threshold), `2` config error. `scripts/run.py` exits `2` when the bundled runtime is missing and `3` when `uv` is unavailable or dependency preparation fails.

## Step 0 — Check the project state (first touch in this session)

Check before editing: the project root path; whether `artifacts/` holds entries; whether `assertions.yaml` exists; what test command the project uses; and what is currently uncommitted.

- Configured project (artifacts + assertions present) → continue at step 1. Reuse the existing setup; do not re-init.
- Spec Kit documents present (`spec.md`/`plan.md`/`tasks.md`/`constitution.md`) → follow the import flow in `references/onboarding.md`, confirm the conversion result, then continue at step 1.
- Plain project (code and ordinary docs, no structured artifacts) → follow minimal onboarding in `references/onboarding.md`: build the smallest entry set that covers the current change, record which documents, code paths, and tests it came from. Do not mass-import existing docs and do not create a second competing specification.
- No executable tests or no valid acceptance configuration → the evidence will be insufficient. Proceed only if the user accepts that limitation, and report the result as "evidence insufficient", never as success.

## Workflow (configured project)

1. **Index** — run `index --root .`. Fix any parse, schema, or duplicate-id error it reports first; those mean the repository is not well-formed.
2. **Baseline + impact** — run `detect --root .` once in report mode (no `--fail-on`) to record pre-existing findings, then `impact <ID> --root .` for each changed entry. The impact set is your work queue; every item carries an evidence chain explaining why it is affected.
3. **Impact queue = deterministic links + supplementary candidates.** The tool output covers only explicit links. Additionally search the code, docs, and tests for references the graph cannot see, and add them as candidates. Never interpret "unreachable in the graph" as "confirmed unaffected". Every candidate you checked must end in exactly one of three conclusions, reported at the end: **modified**, **checked — no change needed (with the reason)**, or **unconfirmed (with the missing evidence named)**.
4. **Edit by change class:**

   | Class | Situation | Action |
   | --- | --- | --- |
   | L0 | Constant/text swap (id, title wording, numbers) | Apply the same replacement mechanically to each affected entry |
   | L1 | Single-entry semantics change | Rewrite that entry minimally; keep EARS + Acceptance valid |
   | L2 | Cross-entry structure change (new/removed dependencies, split or merged entries) | Revise incrementally, entry by entry; keep `depends_on`/`links` consistent |
   | L3 | Goal-level or constitution conflict | Stop editing. Follow `references/conflict-resolution.md` first, then resume |

   Make the minimal diff on each impacted file. When a relationship changes, update frontmatter `depends_on`/`links` in the same edit. Preserve the user's existing modifications and keep the change scope tight. Every L1+ edit gets a short note: root cause, expected fix, what could break, acceptance cases that would catch it.

5. **Semantic checks** — run `detect --root .`, fix every CRITICAL/HIGH finding you introduced, then run the checklist in `references/conflict-checks.md` for the semantic issues the rule layer cannot see.
6. **User decisions** — route needs-user findings through `references/conflict-resolution.md`: one question at a time, atomic write-back, one RAT rationale entry per decision (format in `references/artifact-format.md`).
7. **Gate** — run `detect --root . --fail-on HIGH` (must exit 0) and `verify --root .`. A nonzero gate exit means CRITICAL/HIGH findings remain and completion must not be declared. If your change altered behavior that `assertions.yaml` should cover, add or update assertions in the same turn; explain any deletion or replacement of existing acceptance conditions.
8. **Report** — list changed files; give the three-state conclusion for every candidate; paste the verify summary; and state the verdict exactly as one of: **passed this acceptance** (configured checks passed and all listed impact items are handled), **acceptance failed**, or **evidence insufficient** (tool did not run, no valid acceptance, or unconfirmed impacts remain). "Passed this acceptance" never means the whole project is proven consistent.

Entry, assertion, and RAT formats live in `references/artifact-format.md` — read it before creating or heavily editing entries, not before every small edit.

## Hard rules

- Never make a finding disappear by editing the finding's target without fixing the underlying inconsistency.
- Never mark an entry done while an upstream dependency is draft/active (rule D3).
- Dangling references (D1) must be fixed or explicitly resolved with the user — never silently dropped.
- If propagation requires a product or goal decision, stop at the decision point and ask; do not guess.
- Do not claim offline operation: the self-contained runtime may need network on first dependency preparation.
- Sandbox note (Codex and similar): writing to `artifacts/` and running the CLI may need write approval — request it once, up front, for the whole workflow.
