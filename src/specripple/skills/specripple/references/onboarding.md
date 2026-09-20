# Onboarding and first-touch flows

How to bring a project into specripple coverage. Run the Step-0 check from `../SKILL.md` first, then follow the section for the project state you found.

## Boundaries (state these honestly)

- This flow does not fully parse arbitrary Markdown documents and does not automatically understand an entire repository.
- Only build structured entries and links for the current change. Record where each entry came from (source document, code path, test path).
- Do not mass-copy existing documents into `artifacts/`; that creates a second, competing specification.
- Graph-unreachable is not "confirmed unaffected" — see the main workflow, step 3.

## A. Configured project (artifacts + assertions.yaml exist)

Reuse everything as-is: no re-init, no re-import, no duplicate entries. Go straight to the main workflow. If the setup looks wrong (index fails), fix the errors instead of re-initializing.

## B. Spec Kit documents present

1. Confirm the import scope with the user if any of spec/plan/tasks/constitution is missing or the mapping is ambiguous.
2. Run `import-speckit <src dir> --root .` (fails safely on a non-empty `artifacts/`).
3. Inspect the result: open the created REQ entries, check the `## Acceptance` regions were preserved, and run `detect --root .` (report mode) plus `index --root .`.
4. `import-speckit` creates entries without `assertions.yaml`. For a real acceptance gate, create `assertions.yaml` next (section D) — until then the project runs in report mode only, and you must say so.
5. Then continue with the main workflow.

## C. Plain project (code and ordinary docs, no structured artifacts)

Goal: the smallest entry set that covers the current change, traceable to its sources.

1. Identify the change's requirement(s): which behavior changes, which documents describe it, which code and tests implement it. Read those, not the whole repository.
2. Create entries from `assets/templates/req-entry.md`:
   - One REQ per behavior-level requirement the change touches. `status: active` for what must hold after this change.
   - `## Acceptance` with concrete Given/When/Then cases derived from the requirement text and the user's request.
   - TASK entries (one per unit of implementation work that already exists or is implied), linked to their REQ with `kind: realized-by`.
   - A CON entry only if the project states explicit principles worth enforcing.
3. Record provenance in the entry body (`Imported from <path>` / `Source: <path>`), and link REQ → TASK with `realized-by`.
4. Run `index --root .` and `detect --root .` to confirm the new set is well-formed.
5. Do not import unrelated features "while you are at it". If the user asks for a full-project inventory, say plainly that this is out of scope for the change flow and agree on a separate effort.

## D. Acceptance configuration (creating assertions.yaml)

Never fabricate acceptance criteria. Derive assertions from explicit requirements, the user's stated expectations, or existing tests:

- `fail_to_pass`: assertions that encode the change — they may fail before the edit and must pass after. For a behavior change with a real test command, a `command` checker calling the project's test is the strongest evidence.
- `pass_to_pass`: existing behavior that must survive (existing tests, invariants stated in docs).
- If there are no executable tests and the user cannot name observable acceptance criteria, stop and report **evidence insufficient**. An empty or trivial assertions file is worse than none: it manufactures fake confidence.

## What may be derived vs. what must be asked

- Derivable from explicit sources (requirement text, user request, existing tests): entry structure, link wiring, assertion drafting.
- Needs the user: behavior ambiguity, product trade-offs, conflicting requirements, anything that would delete or weaken existing acceptance conditions.
- Asking one focused question beats guessing; but do not force the user to hand-fill configuration that explicit sources already determine.
