---
name: review
description: >-
  Measure the drift between a codebase and its document structure — operative context, design
  brief, roadmap, ADRs, specs, feature files and tests — and record findings, open questions and
  architectural risks as a dated review with sequenced follow-ups and no code changes. Two entry
  modes: sync (a repo already under the spec-driven shape) and retrofit (bootstrap the documents
  from an existing codebase). Use for: "review the docs against the code", "reconcile",
  "are the docs current", "doc drift", "what's stale", "gap analysis", "retrofit",
  "bring this repo under spec-driven", "extract scenarios from tests", "which decisions aren't
  recorded", "open questions", "architecture risks", "retrospective". Fourth stage of the
  spec-driven plugin; composes with pr-validation, which does the same at diff scale.
---

# Review · Measure the drift, sequence the follow-ups, change no code

Review is XP's retrospective applied to the artefacts: it asks whether the documents still
describe the code, whether the code still serves the documents, and what nobody has written
down. It **measures rather than judges**, cites symbols rather than line numbers, and produces
a record whose invariant is *no code changed by this document*. Every finding becomes a
follow-up sized as one iteration, so the fix runs through the ordinary spec loop rather than
around it.

Read `../spec/references/sync-contract.md` first. Patterns are in
`references/drift-patterns.md`; the retrofit procedure is in `references/retrofit.md`; the
mirror guard is `../spec/references/spec-sync-guard.py`, whose `__main__` mode prints exactly the
summary this skill needs.

The rules here are non-negotiable defaults.

---

## Choose the mode

| Mode | When | Starts from |
|---|---|---|
| **sync** | `docs/specs/` exists and at least one spec is `building` or later | the existing documents |
| **retrofit** | no specs, or feature files that no spec owns are the majority | tests, code, git log, README — see `references/retrofit.md`, then return here for step 3 onward |

State the mode at the top of the record.

---

## Procedure (sync mode)

### Step 1 — Inventory

List what exists, with counts: operative doc (lines, per section), `DESIGN.md` (sections,
status), `ROADMAP.md` (milestones, iterations by status), ADRs (by status), specs (by status),
feature files (owned / unowned), test modules (bound / unbound), the guards present
(`test_docs_are_current`, `test_specs_are_in_sync`). This table is the *Measured state* section
of the record. Measure; do not estimate.

### Step 2 — Run the mechanical checks

- `python spec-sync-guard.py` (or the project's copy) → mirror drift and unowned feature files.
- The project's docs-current guard, if present → stale claims.
- The type checker and the full suite → the baseline you are reviewing must be green; if it is
  not, that is finding F1 and the review continues.

### Step 3 — Walk the drift patterns

Take `references/drift-patterns.md` section by section — A operative doc, B spec ⇄ feature ⇄
test, C decisions, D design ⇄ roadmap ⇄ code, E open questions and risks — and for each pattern
record either a finding with its evidence or "none found". Silence on a pattern reads as a pass
it did not earn; write the "none found".

Two patterns deserve deliberate effort because they hide:

- **Built ahead of need.** For every type and module in the domain layer, name the scenario
  that consumes it. None → finding.
- **The inert check.** For every guard, threshold and veto, ask whether it has ever produced a
  non-default outcome on the recorded data. Count it (0 of N). A check that cannot fire is
  worse than no check, because it is trusted.

### Step 4 — Collect open questions and risks

From the brief's untested hypotheses, the ADRs' fired `Revisit when` triggers, markers older
than one milestone, and single points of failure no ADR names. Each with who could answer it.

### Step 5 — Sequence the follow-ups

Every finding becomes a follow-up row: one iteration's worth, typed as **docs-only** (move
history, write an ADR born `accepted`, fill a Reconciliation), **test-only** (bind a scenario,
add a guard), or **spec needed** (behaviour without a scenario — goes to the roadmap backlog and
is built under TDD later). Order by the damage the drift can do to the next session's work:
mis-scoping claims in the operative doc first, then unguarded decisions, then everything else.

### Step 6 — Write the record

`docs/reviews/YYYY-MM-DD-<slug>.md`:

```markdown
# Review · <slug> — YYYY-MM-DD, against <commit>

**Mode:** sync | retrofit   **No code changed by this document.**

## Measured state
<the inventory table>

## Findings
### F1 — <title>  🔴 | 🟡 | 🟢
**Pattern:** <from drift-patterns.md>  **Evidence:** <symbols, sections, counts>
**Follow-up:** <one iteration; docs-only / test-only / spec needed>

## Patterns checked with nothing found
<list — so a reader knows they were looked at>

## Open questions and risks
| # | Question / risk | Who can answer | By when |

## Sequenced follow-ups
| # | Finding | Type | Iteration size | Order |

## Exit gate for this review's follow-ups
<evidence that they are done: the guard passes, the operative doc is under budget, …>
```

### Step 7 — Hand to the customer

Present the record. The customer sequences (or drops) follow-ups. Docs-only and test-only
follow-ups may then be landed as their own commits; anything typed *spec needed* waits for a
spec.

---

## Hard rules

- **No code changed by a review.** Findings about code become follow-ups; the review does not
  fix them. Moving prose between documents and adding a test binding or a guard are the only
  edits a review's follow-ups may make without a spec.
- **Measure, cite symbols, count.** "Coverage seems thin" is not a finding; "14 of 60 test
  modules bind no scenario" is.
- **Every pattern gets a verdict**, including "none found".
- **A retrofitted document describes what is built.** It never invents intent; inferred
  intent is marked *inferred*.
- **The operative doc is held to its budget and to zero history.** This is the single most
  valuable finding a review produces, because that document is loaded every session.

## What this skill refuses

- To refactor, fix or "tidy" code it finds wanting.
- To write a scenario for behaviour no test exercises (that is spec work under TDD).
- To mark a spec `reconciled` on the author's behalf — it reports the stuck spec.
- To plan the next milestone. Retrofit leaves it empty for the customer.

## Interaction with the other skills

| Skill | Relationship |
|---|---|
| pr-validation | the same questions at diff scale; a review is pr-validation over the whole tree plus the documents |
| spec | review reports stuck specs, silent amendments, fence breaches; the spec skill fixes them through Amendments / Reconciliation |
| scaffolding | review checks the *Introduces* ledger, exit-gate evidence, ADR guards and the operative doc's budget that scaffolding set |
| brainstorming | review reports hypotheses with no evidence gathered |

## Quick reference

```
□ Mode stated (sync / retrofit)          □ Baseline green, or F1 says it is not
□ Inventory measured, not estimated      □ Guards run: mirror, docs-current, unowned features
□ Every drift pattern: finding or "none found"
□ Built-ahead-of-need: every domain type names its consuming scenario
□ Inert checks counted (0 of N)          □ Open questions have an owner
□ Every finding → one-iteration follow-up, typed docs-only / test-only / spec needed
□ Record written under docs/reviews/; no code changed
```
