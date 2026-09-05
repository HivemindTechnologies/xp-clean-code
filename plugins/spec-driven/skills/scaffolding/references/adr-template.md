# Architecture decision records (Nygard shape)

An ADR records **one decision that shapes every signature** or determines the correctness of a
core number: a sign convention, a day-count basis, a monetary type, an error-handling style, a
boundary with another system, a validation gate. Small local choices are not ADRs; they are
commits.

ADRs are **immutable once accepted**. A change of mind is a new ADR that supersedes the old one,
so the history of the decision survives. Status moves in one direction:
`proposed → accepted → (superseded by NNNN | deprecated)`.

## File: `docs/decisions/NNNN-<slug>.md`

```markdown
# ADR-0003 · <Decision, stated as a decision, not a topic>

**Status:** proposed | accepted | superseded by ADR-00NN | deprecated
**Date:** YYYY-MM-DD
**Confirmed by:** <the customer>, YYYY-MM-DD        ← required before `accepted`
**Blocks:** roadmap iteration 2 and every later one
**Revisit when:** <the observable trigger that would reopen this — a measurement, a phase, a vendor change>

## Context

What is true that makes this decision necessary. The forces in play, including the ones that
pull the other way. Two to six sentences; measurements where they exist.

## Options considered

- **(A)** … — what it buys, what it costs
- **(B)** … — what it buys, what it costs

## Decision

**(A).** One paragraph. Where it lives in code (a named constant, a module, a boundary function)
so a reader can find it. If it is a heuristic rather than ground truth, say so here.

## Consequences

What becomes easier, what becomes harder, what must now be tested. Name the test that would
detect the decision being violated or silently changed (e.g. a sign-sensitivity test, a
docs-current guard on the constant's value).
```

## File: `docs/decisions/README.md` — the index and the pin gate

```markdown
# Decisions

| ADR | Title | Status | Blocks iteration | Revisit when |
|-----|-------|--------|------------------|--------------|
| 0001 | Result type is hand-rolled, no new runtime dependency | accepted | 1 | a second consumer needs `Validated` |
| 0002 | Day count is ACT/365-fixed, isolated in one function | accepted | 2 | calibration shows trading-time fits better |
| 0003 | … | proposed | 2 | |

## Pin gate

Iteration N may not open while any ADR that blocks it is still `proposed`. The scaffolding skill
writes this table; the spec skill reads it before moving a spec to `confirmed`.
```

## Rules

- **Decision, not topic, in the title.** "Dealer sign convention" is a topic; "Dealers are
  assumed long calls, short puts" is a decision.
- **`Confirmed by` is the customer.** The agent proposes and recommends; the ADR is `proposed`
  until the customer's name is on it.
- **Every ADR names its code location and its guarding test.** A decision nobody can find or
  detect drifting is prose.
- **`Revisit when` is observable.** "When we have more data" is not a trigger; "when the
  cross-check has 33 dated observations" is.
- **Calibration values are ADRs too** when they gate behaviour (a threshold, a tolerance, a
  minimum sample). Their status line should say they are *revisable calibration parameters*, and
  a docs-current guard should hold the documented value to the constant in code.
