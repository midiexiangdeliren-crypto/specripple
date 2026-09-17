---
name: detecting-conflicts
description: Use after propagating or aligning artifact changes, or when asked to check artifacts for conflicts, contradictions, or quality issues that the align detect rule layer cannot catch.
---

# Detecting Conflicts (LLM layer)

Run this checklist AFTER `align detect` (the zero-token rule layer). The rule layer owns structure; you own semantics. Grade every finding CRITICAL / HIGH / MEDIUM / LOW exactly like detect does, and cite entry ids plus quoted text as evidence.

## Six checks (Spec Kit /analyze categories, run incrementally after each propagation)

1. **Duplication** - two entries now state the same requirement or task; links disagree about which one is canonical.
2. **Ambiguity** - a changed entry uses vague terms (fast, appropriate, robust, etc.), or its [NEEDS CLARIFICATION] semantics leak into dependent entries.
3. **Underspecification** - an active req without measurable acceptance cases, or a task with no definition of done.
4. **Constitution alignment** - the change violates a CON entry principle (for example: acceptance criteria required before implementation, every task traces to a requirement).
5. **Coverage gaps** - a new or changed REQ has no realizing TASK (no realized-by link), or an acceptance case no task covers.
6. **Inconsistency** - sibling entries now contradict each other: statuses, dependencies, glossary usage, or acceptance cases that cannot all hold at once.

## Output discipline

- For each finding report: category, severity, affected entry ids, one-sentence evidence, suggested fix.
- Auto-fixable findings: fix them directly, then re-run `align detect` to confirm the structure is still legal.
- Needs-user findings: hand them to resolving-conflicts, one question at a time.
- Dual control: never report an LLM-layer finding about structure without `align detect` agreeing the surrounding structure is parseable and legal - model self-reports must pass the rule layer, never replace it.
