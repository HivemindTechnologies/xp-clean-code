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

## Procedure

The mode is **decided after** steps 1 and 2, because the inventory and the guard's output are
what decide it. Do not guess it from the directory listing.

### Step 1 — Inventory

List what exists, with counts: operative doc (lines and characters, per section), `DESIGN.md`
(sections; its document-level status line and any built/future labels — "none" if it has
neither), `ROADMAP.md` (milestones, iterations by status), ADRs (by status), specs (by status),
feature files (owned / unowned), test modules (bound / unbound), the guards present
(`test_docs_are_current`, `test_specs_are_in_sync`). This table is the *Measured state* section
of the record. Measure; do not estimate.

### Step 2 — Run the mechanical checks

- `python spec-sync-guard.py <project-root>` (or the project's own `tests/test_specs_are_in_sync.py`) → counts of specs and owned/unowned feature files, mirror drift, malformed spec headers; exit 1 on drift.
- The project's docs-current guard, if present → stale claims.
- The type checker and the full suite → the baseline you are reviewing should be green.
  Distinguish two kinds of non-green: a **failing** test or type error is finding F1 🔴 and the
  review continues; a test or check **blocked by the environment** (a private dependency not
  installed, a secret absent, a service unreachable) is not a red baseline — it is a
  reproducibility finding 🟡 ("N tests cannot run without X"), and the review says which tests it
  therefore could not observe.

### Step 2b — Decide the mode

| Mode | Criterion (by path — a file *named* SPEC outside `docs/specs/` does not count) | Then |
|---|---|---|
| **sync** | `docs/specs/` exists and the guard reports owned feature files ≥ unowned | continue with Step 3 |
| **retrofit** | `docs/specs/` is absent, or unowned feature files outnumber owned | a **retrofit review**: continue with Step 3 over what exists, and add to the record a *sequenced retrofit plan* built from `references/retrofit.md` — one row per document to derive, each sized as one iteration. The review itself writes **no** feature file, spec, ADR or brief; those are its follow-ups, landed one per commit once the customer has sequenced them. |

State the mode and the criterion's numbers at the top of the record.

### Step 3 — Walk the drift patterns

Take `references/drift-patterns.md` sections A–D — A operative doc, B spec ⇄ feature ⇄ test,
C decisions, D design ⇄ roadmap ⇄ code — and for each pattern record one of three verdicts:
a **finding** with its evidence; **none found** (looked, nothing there); or **not applicable**
(the pattern has no subject — e.g. *mirror drift* with zero specs). "Not applicable" is not a
pass and is never written where the subject exists. Silence on a pattern reads as a pass it did
not earn; write the verdict.

Where a document plays a role without having the shape — a decisions file that is not Nygard
ADRs, a spec outside `docs/specs/` — count its entries in the role they play (confirmed decisions
count as accepted ADRs) and file the shape as its own finding.

Two patterns deserve deliberate effort because they hide:

- **Built ahead of need.** For every type and module in the domain layer, name a **production
  call site** that consumes it. "Consumes" means production code, not a scenario: a module with
  production consumers and no scenario is *behaviour without a scenario* (pattern B), a
  different finding. None → built ahead of need.
- **The inert check.** For every guard, threshold and veto, ask whether it has ever produced a
  non-default outcome on the recorded data. Count it (0 of N). When the record is not reachable
  from the review (a live database elsewhere), count from the figures the documents themselves
  record, or establish inertness **by construction** (the input the check reads is absent by
  design for these cases) — and say which you did. A check that cannot fire is worse than no
  check, because it is trusted.

### Step 4 — Open questions and risks (drift-patterns section E)

Section E is not drift and is collected here rather than in Step 3: the brief's untested
hypotheses, the ADRs' fired `Revisit when` triggers, markers older than one milestone, single
points of failure no ADR names. Each row names who could answer it and *by when* — a calendar
fact where one exists (a sample floor's expected date, a settlement, a phase gate), otherwise
"standing".

### Step 5 — Sequence the follow-ups

Every finding becomes a follow-up row: one iteration's worth, typed as one of:

| Type | Meaning | Lands as |
|---|---|---|
| **docs-only** | move history, write an ADR born `accepted`, fill a Reconciliation | its own commit, no spec |
| **test-only** | bind a scenario, add a guard, tag a scenario | its own commit, no spec |
| **refactor** | a behaviour-preserving code change (a duplicated constant, a seam extraction) | its own commit under xp-clean-code's refactor rules — green before and after, never with a feature |
| **environment** | toolchain or reproducibility (a stub for a private dependency, a CI floor) | its own commit |
| **spec needed** | behaviour without a scenario, or a change in behaviour | the roadmap backlog; built later under a spec, under TDD |

Severity: 🔴 mis-scopes the next session's work or contradicts the code (a wrong claim in the
operative doc, an ADR the code violates, an unauthorised behaviour); 🟡 will become 🔴 if left
(history accreting, an unguarded decision, a stuck spec); 🟢 costs a reader time and nothing
else. Order the follow-ups 🔴 first, then by how many later follow-ups each unblocks.

A follow-up that is not one iteration's worth is split: "bind 38 test modules" is 38 rows, or
one row per module with the hard-rule modules first.

### Step 6 — Write the record

`docs/reviews/YYYY-MM-DD-<slug>.md`:

```markdown
# Review · <slug> — YYYY-MM-DD, against <commit>

**Mode:** sync | retrofit (criterion: N owned / M unowned feature files)
**Plugin:** spec-driven <version read from plugin.json>   **No code changed by this document.**

## Measured state
<the inventory table; baseline: passed / failed / environment-blocked, with the blocker>

## Findings
### F1 — <title>  🔴 | 🟡 | 🟢
**Pattern:** <from drift-patterns.md>  **Evidence:** <symbols, sections, counts>
**Follow-up:** <one iteration; docs-only / test-only / spec needed>

## Patterns checked with nothing found, and patterns not applicable
<two lists — so a reader knows they were looked at, and that N/A was not counted as a pass>

## Open questions and risks
| # | Question / risk | Who can answer | By when |

## Sequenced follow-ups
| # | Finding | Type (docs-only / test-only / refactor / environment / spec needed) | Order |

## Retrofit plan (retrofit mode only)
<one row per document to derive, from references/retrofit.md, each one iteration, in that file's order>

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
- **Every pattern gets a verdict**: finding, none found, or not applicable — and not applicable
  is never a pass.
- **A retrofit review writes only the record.** The documents it calls for are follow-ups the
  customer sequences; the review does not produce them.
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
□ Inventory measured, not estimated      □ Guards run: mirror, docs-current, unowned features
□ Baseline: green, red (F1), or environment-blocked (🟡, named) — never conflated
□ Mode decided from the guard's numbers, stated with them
□ Every drift pattern A–D: finding / none found / not applicable (N/A is not a pass)
□ Built-ahead-of-need: every domain type names a production call site
□ Inert checks counted (0 of N), or shown inert by construction, and said which
□ Open questions: owner, and "by when" from a calendar fact or "standing"
□ Every finding → one-iteration follow-up, typed docs-only / test-only / refactor / environment / spec needed
□ Retrofit mode: the plan is rows in the record, not documents written
□ Record written under docs/reviews/; no code changed
```
