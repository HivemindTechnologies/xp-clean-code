---
name: spec
description: >-
  Write and drive a spec — one small release, expressed as a scope fence plus the Given/When/Then
  scenarios that are its acceptance tests — and build it under XP discipline with the scope
  frozen. Use this whenever a roadmap iteration or a story is ready to become code: "write a
  spec", "spec this out", "start iteration 7", "next increment", "what's in scope", "scope creep",
  "amend the spec", "is this in the spec", "reconcile the spec", "mark the spec shipped",
  "feature file out of sync with the spec". The spec is the single instrument of product
  building in the spec-driven plugin: brainstorming and scaffolding produce intent, this skill
  turns one slice of it into an authorised, executable, fenced increment, and review measures
  the result. Composes with xp-clean-code (how each scenario is built) and pr-validation (how
  the PR is checked against the spec).
---

# Spec · One small release, fenced and executable

A spec is **the acceptance-test set for one small release, plus a scope fence.** It is not a
requirements document, not a design document, and not a task list. Upstream documents
(`DESIGN.md`, `ROADMAP.md`, ADRs) supply intent; the spec is where intent becomes an authorised
set of scenarios, and the scenarios are what the code is built to. Scope creep is forbidden,
YAGNI is the default, and design is evolutionary: a type, a module or an abstraction exists
only because a scenario in a confirmed spec demanded it.

Read `references/sync-contract.md` before using this skill. It defines the lifecycle, the
scope-creep rule and the spec ⇄ feature-file mirror that this skill enforces. The template is
`references/spec-template.md`; the mirror guard is `references/spec-sync-guard.py`.

The rules here are non-negotiable defaults. Deviate only when the customer explicitly asks and
states a reason — and record the reason in the spec's Amendments.

---

## When a spec is the right size

A spec covers **one small release**: something the customer can observe working when it ships,
typically 3–12 scenarios and one to three roadmap iterations. Two tests:

- **The purpose fits in one paragraph.** A second paragraph means a second spec.
- **Every scenario shares one `Feature:`** (or a tightly related pair). Scenarios from unrelated
  features are unrelated increments.

Too small is also a defect: one scenario is an iteration, not a release, and belongs in the
roadmap under an existing spec. Too large hides feedback exactly the way a large step does.

---

## Procedure

### Step 1 — Draft

1. Take the story or roadmap iteration(s) the customer named. Read the brief's hypothesis it
   serves and the ADRs it relies on. If an ADR it needs is still `proposed`, stop: the spec
   cannot reach `confirmed` until the decision is accepted (see the scaffolding skill).
2. Create `docs/specs/NNN-<slug>.md` from the template with `Status: draft`.
3. Write **§1 Purpose** as one paragraph and **§2 Scope fence** with an explicit *Out* list.
   Write the *Out* list before the scenarios — it is easier to see what you are excluding
   before the scenarios make the inclusions feel complete.
4. Write **§3 Scenarios** in Gherkin, inside the spec. For every behaviour: a happy path, one
   scenario per distinct failure mode, boundary values, and a double-application scenario for
   every state transition. Apply the xp-clean-code scenario standard: one `When`, a verifiable
   `Then`, explicit `Given`, no implementation detail.
5. Write **§4 Design notes** with only what the scenarios force, and an *Explicitly not designed
   here* line. Write **§5 Exit evidence**.
6. If a scenario cannot be written, the behaviour is not understood. Stop and ask the customer;
   do not write a vague `Then` to keep moving.

### Step 2 — Confirm

Present the spec to the customer in full — purpose, fence, scenarios, exit evidence. The
customer confirms or edits. Only the customer moves `Status` to `confirmed`. Record who
confirmed and when in the header or the Amendments table.

Nothing in `tests/`, `src/` or the equivalent may change while the spec is `draft`.

### Step 3 — Open the build

The first commit of the build:

1. Copies the Gherkin block(s) **verbatim** into the feature file(s) named in the header.
2. Binds them to tests (`scenarios("x.feature")` in pytest-bdd, or the stack's equivalent) and
   tags every scenario not yet being built `@wip`, deselected in the runner (`-m "not wip"` in
   pytest-bdd; the equivalent tag filter in Cucumber). The guard ignores tag lines, so removing
   `@wip` as each scenario's turn comes is not drift. This keeps *one failing test at a time*
   true while the feature file already holds the whole authorised set.
3. Sets `Status: building`.
4. Adds the sync guard to the suite if the project does not have it yet (copy
   `references/spec-sync-guard.py` to `tests/test_specs_are_in_sync.py`).

From this commit on the **feature file is authoritative** and the spec's Gherkin block is a
mirror. The guard keeps them equal.

### Step 4 — Build, one scenario at a time

For each scenario, in the roadmap's order, run the xp-clean-code loop exactly: RED (verify the
test fails) → GREEN (minimum code) → CLEAN (refactor, separate commit) → commit. One scenario =
one commit, `≤ ~50` production lines per step, `mypy --strict` / the stack's type checker green.

Introduce a type, module or abstraction **only when the current scenario's GREEN step needs it**.
The design notes' *Explicitly not designed here* list is checked, not aspirational: if you find
yourself writing one of those things, stop.

### Step 5 — The scope-creep rule

A behaviour discovered during the build that no scenario in the spec authorises **stops the
work**. Exactly two moves are permitted:

| Move | When | How |
|---|---|---|
| **Amend** | the increment is not shippable without it | add the scenario to §3, add an Amendments row (date, scenario, why unforeseen, who confirmed); the customer confirms **before** the RED test; the amendment lands in the same PR |
| **Defer** | the increment ships without it | one line in the roadmap backlog, carry on inside the fence |

There is no third move. In particular, none of these is permitted without an amendment: a
helper "we'll need later", a configuration knob no scenario reads, a second adapter, a cache, a
retry, a broader error type than the scenario's failure mode requires, or a scenario added to
the feature file "while I was there".

### Step 6 — Ship

When every authorised scenario is green on the default branch, set `Status: shipped`. Check the
**exit evidence** (§5) and record what was observed. If the evidence cannot be gathered yet
(e.g. it needs live data), say so in §5 with the date it is expected; do not mark the spec
`reconciled` on tests alone when §5 asked for more.

### Step 7 — Reconcile

Fill **§7 Reconciliation** with every as-built deviation from the confirmed spec: renamed terms,
scenarios amended, design notes that turned out wrong, a fence moved. "None" is allowed and
should be rare enough to be suspicious. Set `Status: reconciled`. Update the domain-model table
in the operative doc with the terms that were actually built, and tick the roadmap iterations.

---

## Hard rules

- **The spec's scenarios are the only licence to write production code.** `DESIGN.md`
  describing a component is scope, not licence; the roadmap listing an iteration is order, not
  licence.
- **No per-scenario status in the spec.** Done means present in the feature file and green.
  Hand-written checklists drift, and the guard cannot check them.
- **The customer confirms; the agent proposes.** The agent never moves a spec to `confirmed`.
- **One spec, one PR series.** The PR body names the spec (`Spec: NNN`) so pr-validation
  Analysis 5 can check the diff against it.
- **The mirror is maintained by the guard, not by memory.** If the guard fails, copy in the
  direction the state dictates and record why the behaviour moved.
- **A spec is never edited to match code silently.** A change to §3 after `confirmed` is an
  Amendments row; a change after `shipped` is a Reconciliation entry.

---

## What this skill refuses

- To write production code from a `draft` or unconfirmed spec.
- To write a scenario with a `Then` that cannot be asserted ("handles errors gracefully").
- To include a scenario for a behaviour the *Out* list names.
- To bundle two small releases into one spec because "they touch the same file".
- To mark a spec `reconciled` while §5's evidence is outstanding or §7 is empty.

---

## Interaction with the other skills

| Skill | Hands this skill | Receives from this skill |
|---|---|---|
| brainstorming | the story and the hypothesis it tests | nothing directly; a spike may be requested when a scenario cannot be written |
| scaffolding | the roadmap iteration(s), the milestone's exit gate, the ADRs relied on | ticked iterations; new terms for the domain-model table |
| xp-clean-code | — | each scenario, to be built RED → GREEN → CLEAN |
| pr-validation | — | the spec id in the PR body; Analysis 5 checks the diff against it |
| review | — | `shipped`/`reconciled` specs, the mirror, unowned feature files |

---

## Quick reference

```
Before Status: confirmed
  □ Purpose is one paragraph          □ Out list written before the scenarios
  □ Every behaviour: happy path, each failure mode, boundaries, double-application
  □ One When per scenario; Then is assertable; no implementation detail
  □ Design notes name only what scenarios force, plus "explicitly not designed here"
  □ Exit evidence stated              □ Every ADR relied on is `accepted`
  □ The customer, not the agent, sets confirmed

During Status: building
  □ First commit: Gherkin copied verbatim to the named feature file(s); guard installed
  □ One scenario = one commit; ≤ ~50 production lines; one failing test at a time
  □ Anything not authorised → stop → amend (customer confirms first) or defer
  □ PR body carries `Spec: NNN`

Before Status: reconciled
  □ Every scenario green on the default branch     □ Exit evidence observed and recorded
  □ Reconciliation section filled                  □ Roadmap ticked, domain table updated
```
