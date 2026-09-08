# Roadmap template (`docs/ROADMAP.md`)

The roadmap is the **build sequence**, and it exists to enforce the XP disciplines against a
brief that deliberately runs ahead of the code: one iteration = one scenario (or a tiny
cluster), driven RED → GREEN → CLEAN, landed as one commit. It orders; it does not authorise —
only a confirmed spec does that.

```markdown
# <Product> — Roadmap

**How to use it:** work top-to-bottom. Never open two iterations at once. A component described
in `DESIGN.md` but not yet reached here is future scope, not present work. An iteration is
built only under a `confirmed` spec that lists it.

**Precedence:** for present work, `CLAUDE.md` + the current spec + accepted ADRs win over
`DESIGN.md`.

Status legend: ⏳ not started · 🔨 building (spec NNN) · ✅ shipped · ↩ deferred (reason)

---

## Milestone M0 — Walking skeleton

**Exit gate:** CI green on the default branch running one trivial test and one trivial
`.feature`; the type checker in strict mode; the sync guard installed. Nothing else.

| # | Iteration | Spec | Status |
|---|-----------|------|--------|
| 0 | Repo scaffold, CI, one trivial scenario, `tests/test_specs_are_in_sync.py` | — (plumbing, not TDD) | ⏳ |

## Milestone M1 — <the thinnest slice that tests H1>

**Tests hypothesis:** H1.
**Blocked on decisions:** ADR-0001, ADR-0002 must be `accepted` before iteration 2.
**Exit gate (evidence, not implementation):**
- <a measurement or observation, with its threshold, that the customer will read>
- <the honesty evidence: at least one case where the system declined / refused / reported absence>
- <the calibration evidence, if the product makes predictions>

| # | Scenario (Given / When / Then, one line) | Introduces | Spec | Status |
|---|------------------------------------------|------------|------|--------|
| 1 | | first value object, by first consumer | 001 | ⏳ |
| 2 | | | 001 | ⏳ |
| 3 | | | 002 | ⏳ |

## Milestone M2 — <next small release>

*(gated on M1's exit gate — do not scaffold ahead of it)*

| # | Scenario | Introduces | Spec | Status |
|---|----------|------------|------|--------|

---

## Backlog (deferred from specs)

One line each: the scenario, the spec that deferred it, the date. This is where the spec skill's
"defer" move writes.

| Scenario | Deferred by | Date | Reason |
|----------|-------------|------|--------|

---

## Invariants that hold across every iteration

- One failing test at a time; ≤ ~50 production lines per step; one scenario = one commit.
- The type checker and every scenario green before *and* after every refactor.
- Never a refactor and a feature in the same commit.
- No component built before its iteration, and no iteration built outside a confirmed spec —
  future design is scope, not licence.
- A type is introduced by the first scenario that consumes it, never ahead of a consumer.
```

## Rules for filling it

- **Milestones are small releases.** Each has an exit gate stated as *evidence the customer
  reads*, never as a list of components. "`RiskAgent` built" is implementation; "40 proposals
  logged and at least one declined for a stated reason" is evidence.
- **M0 is always a walking skeleton** with no domain behaviour. It de-risks the toolchain
  before any maths.
- **One scenario per row.** If a row needs "and", split it.
- **The *Introduces* column is the evolutionary-design ledger:** each type or module appears on
  the row of the scenario that first consumes it. A type with no row is built ahead of need.
- **Blocked-on decisions are named by ADR number,** and the ADR index says which iteration each
  blocks.
- **Only the next milestone is detailed.** Later milestones get a title and a one-line gate;
  filling them in is design ahead of evidence.
