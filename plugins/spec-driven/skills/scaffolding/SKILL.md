---
name: scaffolding
description: >-
  Turn a confirmed design brief into the structure of an MVP: the first small release and its
  evidence-based exit gate, a roadmap of one-scenario iterations, Nygard-style architecture
  decision records with a customer confirmation gate, a walking-skeleton Iteration 0, the
  lean operative context document (CLAUDE.md / AGENTS.md) with its docs-current guard, and the
  spec sync guard. Use when the brief is confirmed and nothing is planned yet: "scaffold",
  "roadmap", "milestones", "release plan", "iteration plan", "ADR", "architecture decision",
  "decisions to pin", "walking skeleton", "set up the project structure", "write CLAUDE.md",
  "what do we build first". This is XP release planning made explicit; it is the second stage
  of the spec-driven plugin, between brainstorming and spec.
---

# Scaffolding · From brief to a controlled build sequence

Scaffolding concretises **structure without building behaviour**: which small release comes
first and what evidence closes it, in which order the scenarios land, which decisions must be
pinned before the first signature is written, and what the agent must hold in context on every
session. It ends with a walking skeleton — CI green on a trivial test — and not one line of
domain code.

XP calls this release planning. The customer chooses value; the developers order by dependency
and risk; both agree what "done" looks like before the first iteration opens. The evolutionary
design principle is enforced mechanically here: every type on the roadmap is introduced by the
scenario that first consumes it.

Templates: `references/roadmap-template.md`, `references/adr-template.md`,
`references/operative-context.md`. Read `../spec/references/sync-contract.md` for the artefact
map and precedence rule that scaffolding writes into the project.

The rules here are non-negotiable defaults.

---

## Preconditions

- `docs/DESIGN.md` exists and the customer has confirmed its stories and hypotheses.
- Every spike the brief named as blocking is closed, with its record under `docs/spikes/`.
- No production code exists yet — or, for an existing codebase, the review skill's retrofit has
  run first.

If a precondition fails, say which and stop. Scaffolding on an unconfirmed brief plans a product
nobody has agreed to.

---

## Procedure

### Step 1 — Choose the first small release

From the confirmed stories, pick the **thinnest slice that tests the primary hypothesis** (H1 in
the brief). Not the most valuable story, not the easiest: the one whose shipping produces
evidence for or against the bet the product rests on. Name it milestone M1.

### Step 2 — Write M1's exit gate as evidence

The gate is a list of **observations the customer will read**, each with a threshold: a count, a
measured value, a duration of operation, a case where the system declined or reported absence
(the honesty evidence). Never a list of components. Thresholds are revisable calibration
parameters; record each as an ADR so the value has a home and a guard.

### Step 3 — Pin the decisions

Enumerate every decision that **shapes every downstream signature or determines the correctness
of a core number**: the error/absence types, the monetary and time representations, the
day-count, sign or unit conventions, the boundary with each external system, the validation
gate. Write each as an ADR in `proposed` state with options, a recommendation, a code location,
a guarding test and a `Revisit when`. Fill the index's **pin gate** table: which iteration each
ADR blocks.

Present the set to the customer. The customer confirms or overrides each; only then does an ADR
become `accepted`. Iteration N cannot open while an ADR blocking it is `proposed`.

### Step 4 — Write the roadmap

- **Iteration 0 — walking skeleton.** Repo layout, CI running the type checker in strict mode
  and the test runner, one trivial passing test, one trivial `.feature`, and the spec sync guard.
  No domain behaviour. It is plumbing, not TDD, and the roadmap says so.
- **M1's iterations**, one scenario per row, in dependency order, each with its *Introduces*
  column: the first value object, module or boundary that scenario forces into existence.
  Nothing appears in *Introduces* ahead of a consumer.
- **Later milestones** get a title and a one-line gate only. Detailing them is design ahead of
  evidence.
- The backlog table, empty, and the invariants block.

### Step 5 — Seed the domain model table

From the brief's ubiquitous-language seed, list the terms M1's scenarios will need, each ⏳ with
the iteration that introduces it. This table lives in the operative doc and is updated by the
spec skill as terms are built. A term with no introducing iteration stays in the brief.

### Step 6 — Write the operative context document

`CLAUDE.md` (or `AGENTS.md`) under `operative-context.md`'s budget — declared on the document's
own `**Context budget:**` line, sized by the invariants it must hold (its sizing table), the
default when in doubt: what the project is in ≤ 15 lines, the document map with the precedence rule verbatim, the coding standards as **deltas on
the xp-clean-code skill** (never a copy of it), the hard rules, the domain table, and a current
status of ≤ 20 lines with no history. For every checkable claim it makes, add
`tests/test_docs_are_current.py` reading the constant from the code.

### Step 7 — Build Iteration 0 and stop

Land the walking skeleton. Confirm CI is green on the default branch. Then stop: the next thing
that happens is the spec skill drafting spec 001 for M1's first iterations, and that is a
separate conversation.

---

## Hard rules

- **Exit gates are evidence, not implementation.** If a gate row names a component, rewrite it
  as the observation that component would produce.
- **Decisions are pinned before the signatures they shape,** and the customer accepts them. A
  `proposed` ADR blocks the iterations that depend on it.
- **One scenario per roadmap row. Types by first consumer.** The *Introduces* column is checked
  by the review skill: a type with no row was built ahead of need.
- **Only the next milestone is detailed.**
- **The operative doc carries no history and stays under budget.**
- **Iteration 0 has no domain behaviour.** The temptation to "just add the first value object
  while the CI is being set up" is exactly the step this stage exists to refuse.

## What this skill refuses

- To scaffold an unconfirmed brief, or ahead of an open blocking spike.
- To write a component, a value object, an adapter or a schema — even an empty one.
- To add a runtime dependency without an ADR the customer accepted.
- To detail milestone M2 beyond a title and a one-line gate.
- To copy the xp-clean-code skill into the operative doc.

## Interaction with the other skills

| Skill | Relationship |
|---|---|
| brainstorming | supplies the confirmed brief, closed spikes, language seed |
| spec | consumes roadmap iterations and the pin gate; reports back ticked iterations and built terms |
| review | measures the roadmap's *Introduces* ledger, the exit-gate evidence, the ADR guards and the operative doc's budget |
| xp-clean-code | the coding standards in the operative doc are deltas on it |

## Quick reference

```
□ Brief confirmed; blocking spikes closed
□ M1 = thinnest slice that tests H1; exit gate = observations with thresholds, incl. honesty evidence
□ Every signature-shaping decision is an ADR: options, recommendation, code location, guard, revisit trigger
□ Pin gate table filled; customer accepts before the blocked iteration opens
□ Roadmap: Iteration 0 skeleton → one scenario per row → Introduces by first consumer → M2 title only
□ Domain table seeded, all ⏳ with introducing iteration
□ Operative doc within its declared budget (default 200 lines · 16k chars), no history, precedence rule verbatim, docs-current guard for each claim and for the budget
□ Iteration 0 landed, CI green, and then STOP
```
