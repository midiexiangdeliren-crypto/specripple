---
name: resolving-conflicts
description: Use when an alignment change or a detection finding needs a user decision - conflicting requirements, constitution conflicts, unreachable dependencies, L3-class goal changes; or when the user asks to clarify or adjudicate an artifact conflict.
---

# Resolving Conflicts

Resolve conflicts between a change and the existing artifact set through focused, one-at-a-time questions.

## Protocol

1. **Classify first** - for each CRITICAL/HIGH finding decide: auto-adjudicable (fix it yourself), needs-user (ask), needs-info (ask for the missing fact). Only needs-user and needs-info reach the user; handle the rest yourself and say so in the final report.
2. **One question at a time** - never batch questions. Each question contains exactly: the conflict in one sentence, the evidence (entry ids and why they clash), then 2-4 answer options with one option marked as recommended and one sentence saying why.
3. **Atomic write-back** - apply each answer immediately: edit the entry body (replace the conflicting text, do not append a decision log), update frontmatter `depends_on`/`links` as needed, then move to the next question.
4. **Record rationale** - after each resolution, create a rationale entry (id prefix `RAT-NNN`) stating: the conflict, the chosen option, why, and `links` with kind `clarifies` pointing at every entry it affected. Rebuild the index afterwards.
5. **Resume the pipeline** - return to aligning-changes at the detect step. Never skip re-detection after resolutions.

## Hard rules

- Never resolve a conflict by deleting acceptance criteria or weakening a CON principle without explicit user approval.
- If the options change project goals (L3), present the goal-level conflict itself, not an implementation detail.
- Maximum 3 rounds on one conflict. If it is still unresolved, park it as a `[NEEDS CLARIFICATION]` marker in the entry body and report it - rule D5 will keep it visible until it is resolved.
