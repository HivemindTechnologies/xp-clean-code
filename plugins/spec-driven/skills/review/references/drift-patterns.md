# Drift patterns

Each pattern names what to measure, the signal that it is present, and the evidence a finding
must carry. Findings cite **symbols and document sections, not line numbers** — line numbers
are stale by the time the record is read.

## A · Operative context document

| Pattern | Signal | Evidence to record |
|---|---|---|
| **History in the operative doc** | dated sentences, "fixed 2026-…", issue numbers narrated in the status section | count of dated lines; where each belongs (ADR / spec Reconciliation / review) |
| **Over budget** | total lines or a section beyond `operative-context.md`'s budget | measured lines per section |
| **Unguarded checkable claim** | a number, version, schedule or owner stated in prose with no test reading the constant | the claim, the constant it should read, the guard to add |
| **Stale claim** | a guarded or unguarded claim that is simply false against the code | the claim vs the measured value |
| **Missing precedence rule** | no statement of which document wins on present-tense conflict | — |

## B · Spec ⇄ feature file ⇄ test

| Pattern | Signal | Evidence to record |
|---|---|---|
| **Mirror drift** | `spec-sync-guard.py` reports a step diff or an unauthorised scenario | the guard's output |
| **Unowned feature file** | a `.feature` no spec names | list; suggested owning spec or "retrofit spec needed" |
| **Unbound scenario** | a scenario in a feature file with no `scenarios()`/glue binding | title and file |
| **Behaviour without a scenario** | a test module or test function exercising behaviour that no feature file describes | module; the scenario it implies |
| **Stuck spec** | `building` with every scenario green (should be `shipped`); `shipped` for > one iteration without Reconciliation | spec id, state, age |
| **Silent amendment** | a scenario in a feature file whose title is absent from the spec's Amendments and was not in the confirmed version | title; the commit that added it |
| **Scope fence breached** | production code, a knob or an abstraction no scenario in the owning spec exercises | symbol; the spec's *Out* list entry it violates, if any |

## C · Decisions

| Pattern | Signal | Evidence to record |
|---|---|---|
| **Decision in code, not in an ADR** | a named constant with a calibration comment; a sign convention; a day-count; a tolerance; a "we decided" in a docstring | symbol; the ADR to write, born `accepted` with the commit as `Confirmed by` |
| **ADR without a guard** | an accepted ADR naming no test that would detect its violation | ADR id; the sensitivity or docs-current test to add |
| **ADR contradicted by code** | code does the option the ADR rejected | ADR id, symbol |
| **Pin gate bypassed** | an iteration shipped while an ADR it depends on was `proposed` | iteration, ADR |
| **Revisit trigger fired** | the ADR's `Revisit when` condition is now observably true | ADR id, the observation |

## D · Design ⇄ roadmap ⇄ code

| Pattern | Signal | Evidence to record |
|---|---|---|
| **Design ahead of roadmap** | a component in `DESIGN.md` with no roadmap row — fine, if labelled future; a finding if the operative doc treats it as current | component |
| **Built ahead of need** | a type or module with no scenario consuming it | symbol; "delete or find the consumer" |
| **Roadmap row without a spec** | an iteration marked building/shipped that no spec lists | iteration |
| **Exit gate unmeasured** | a milestone marked complete with no recorded evidence against its gate | milestone |
| **Design says X, code does Y** | a documented behaviour the code contradicts | section; symbol |

## Verdicts

Every pattern in A–D receives one of: **finding** (with evidence), **none found**, or **not
applicable** (no subject exists — zero specs makes *mirror drift* N/A). Not applicable is
recorded so a reader knows it was not skipped, and it is never a pass.

## E · Open questions and risks

Not drift, and collected in the review's Step 4 rather than Step 3, but the review is the only
stage that looks across everything, so it owns them:

- `TODO` / `deferred` / `open` / `⏳` markers older than one milestone, with no backlog row.
- Hypotheses in the brief with no evidence gathered yet, and how many iterations have shipped
  against them.
- Single points of failure the ADRs do not mention (one vendor, one credential, one cron).
- Places where the code's honest failure path exists but nothing observes it (a WARNING nobody
  reads; a check that cannot fire — see the *inert check* pattern below).

**The inert check.** A guard, threshold or veto that is present and cannot fire on the data it
screens — a threshold calibrated on one series and applied to another, a check gated on a
sample that takes a year to mature, a smoke test that skips green. Signal: the check has never
produced a non-default outcome in the recorded history. Evidence: the count (0 of N). This
pattern recurs, and it is found by asking what a default fixture value is doing and by sweeping
a range rather than asserting one point.
