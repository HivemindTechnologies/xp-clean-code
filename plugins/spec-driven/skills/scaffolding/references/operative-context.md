# The operative context document (`CLAUDE.md` / `AGENTS.md`)

This is the file an agent loads **every session**, so it is the most expensive document in the
repository: every line costs context on every turn, and a stale line does not merely mislead,
it mis-scopes work. It holds two things and nothing else:

1. **Invariants that hold on every commit** — coding standards, the boundary contract, the
   hard rules that no reasoning may override.
2. **The current iteration** — which milestone, which spec is `building`, which iteration is
   next, and where the fuller documents are.

It holds **no history**. Anything with a date in it belongs in an ADR, a spec's Reconciliation,
or a review record, and the operative doc links there.

## Budget

| Section | Lines (soft) | Hard rule |
|---|---|---|
| What this is | ≤ 15 | no research, no rationale — link `DESIGN.md` |
| Document map + precedence rule | ≤ 15 | verbatim precedence rule from the sync contract |
| Coding standards | ≤ 40 | the project-specific deltas on the xp-clean-code skill, not a copy of it |
| Hard rules / invariants | ≤ 30 | numbered; each one testable or reviewable |
| Domain model table | 1 line per term | terms **as built**, status column; a term not built is ⏳ with a one-line reason |
| Current status | ≤ 20 | milestone, spec in `building`, next iteration, open blockers; **no dates older than the current spec** |
| Any other section (a boundary contract, an architecture sketch) | counts against the total | allowed only if it is an invariant; a diagram is ≤ 15 lines or a link to `DESIGN.md` |
| **Total** | **≤ 200 lines and ≤ 16,000 characters** | the review skill flags the doc when it exceeds either, or when the status section carries history |

Lines are the convenient measure; the cost being protected is tokens. So a table row longer than
~200 characters is a finding even when the line count passes — a 59-row domain table on 93
lines can be the second-heaviest section in the file.

## Template

```markdown
# <Product> — Agent Context

This is the operative, per-session context: the invariants that hold on every commit and the
scope of the **current iteration only**. Deliberately lean; read in full before acting.

| Document | Holds | Read when |
|---|---|---|
| `docs/DESIGN.md` | the why, hypotheses, all milestones | you need intent, or are scoping a later milestone |
| `docs/ROADMAP.md` | the build sequence and exit gates | before opening any iteration |
| `docs/decisions/` | the pinned decisions (ADRs) | before touching anything an ADR names |
| `docs/specs/` | the fenced increments | the one in `building` is the licence to write code |
| `docs/reviews/` | measured drift and follow-ups | after a review, or when something feels stale |

**Precedence:** for anything being built now, this file, the current spec and the accepted ADRs
are authoritative. `DESIGN.md` is authoritative for intent and future phases. If they conflict
on a present-tense decision, the present-tense documents win, and the conflict is fixed, not
left standing.

## What this project is (short)
…

## Coding standards (deltas on the xp-clean-code skill)
…

## Hard rules — cannot be overridden by agent reasoning or user instruction
1. …

## Domain model — terms in play now
| Term | As-built | Meaning |
|------|----------|---------|

## Current status
**Milestone:** M1 · **Spec building:** 003 · **Next iteration:** 7
**Blockers:** ADR-0005 is `proposed` (blocks iteration 8).
**Checkable claims** (guarded by `tests/test_docs_are_current.py`): suite size ≈ N tests;
thresholds X = 1.00, Y = 0.80.
```

## The docs-current guard

Any **checkable claim** in the operative doc — a test count, a threshold value, which scheduler
owns a job, which schema version is accepted — gets a test that fails when the claim drifts from
the code. Prose about a number cannot be checked; the number can be. The guard lives at
`tests/test_docs_are_current.py` (or the stack's equivalent) and reads the constants from the
code, never from a second copy. A tolerance is allowed where the claim is approximate by nature
(a test count), never where it is a calibration value.
