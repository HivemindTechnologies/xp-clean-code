---
name: pr-validation
description: >-
  Validate a pull request against XP and clean code standards. Analyses changed
  functions for purity, idempotency, and BDD scenario coverage. Use when
  reviewing a PR, checking test coverage, identifying coverage gaps, verifying
  that changes are backed by BDD scenarios, or auditing purity and idempotency
  of changed functions. Triggers on phrases like "review PR", "validate PR",
  "validate the PR", "check coverage", "BDD coverage", "coverage gaps",
  "scenario gaps", "pure function check", "idempotency check",
  "verify purity", "analyse coverage", "pull request validation", "PR review",
  "verify idempotency", "test coverage", "missing scenarios",
  "are my functions pure", "is this idempotent", "what's missing from my tests".
  Composes with the xp-clean-code skill: where that skill governs how to build,
  this skill validates that what was built meets those standards.
---

# PR Validation · Purity · Idempotency · BDD Coverage

This skill audits a pull request against the quality standards established in the xp-clean-code skill. It does not enforce how to build — it verifies that what was built meets the standards.

Run this validation on every PR before it is considered ready for review. The output is a structured report, not a verdict by itself. The report identifies findings; the author decides how to address them.

The rules here are non-negotiable defaults. Deviate only when the user explicitly asks and states a reason.

---

## How to Run This Validation

1. Obtain the diff for the PR (changed files, hunks, line ranges).
2. Identify every changed function, method, or procedure.
3. Run each of the three analyses below independently.
4. Produce the structured gap report.

Always work from the diff. Do not analyse unchanged code unless a changed function calls it and the call site is relevant to the analysis.

---

## Analysis 1: Purity Verification

For each changed function, determine whether it is pure.

### Definition

A function is **pure** if:
1. It always returns the same output for the same input (referential transparency).
2. It produces no observable side effects — no writes to shared state, no I/O, no mutation of arguments.

A function is **impure** if it:
- Reads from or writes to a database, file system, or network.
- Reads a clock, random number generator, or environment variable.
- Mutates a shared variable, instance field, or its arguments.
- Throws an unchecked exception as a control-flow mechanism (hidden side effect).
- Calls another impure function.

### Classification

For each changed function, classify it as one of:

| Class | Meaning |
|---|---|
| **Pure** | Referentially transparent; no side effects. |
| **Impure — boundary** | Side effects are expected and justified. The function lives at the I/O boundary by design (e.g. a repository, an HTTP adapter, an event publisher). |
| **Impure — violation** | Side effects are hidden inside domain logic where they do not belong. This is a defect. |

### Verification Checklist

For each changed function, answer every question:

```
□ Does it call any I/O API directly? (db, http, file, clock, random, env)
□ Does it mutate its arguments?
□ Does it mutate any shared or external state?
□ Does it read from the clock, a random source, or an environment variable?
□ Does it call another function that fails any of the above?
□ Is the return type honest about failure? (Either/Result vs unchecked exception)
```

If any box is checked and the function is **not** at the I/O boundary, classify it as **Impure — violation** and flag it.

### Boundary Layer Rules

A function may be classified as **Impure — boundary** (acceptable) only when **all** of the following hold:

1. It lives in an infrastructure or adapter layer — not in `domain/`, `core/`, or `logic/`.
2. All domain logic it invokes is pure — I/O wraps pure functions, not the reverse.
3. Its tests isolate the I/O with test doubles (in-memory store, stub clock, fake HTTP server).
4. Its name or package makes the side effect obvious (`UserRepository`, `EmailSender`, `OrderController`).

### Examples

```python
# PURE — same input always yields same output; no side effects
def apply_discount(price: Money, discount: Discount) -> Money:
    return Money(price.amount * (1 - discount.rate), price.currency)

# IMPURE — BOUNDARY (acceptable: lives in repo layer, wraps pure domain objects)
def save_order(order: Order) -> None:
    db.session.add(order)
    db.session.commit()

# IMPURE — VIOLATION (defect: domain logic performing I/O)
def confirm_order(order_id: str) -> None:
    order = db.find(order_id)          # I/O inside domain logic
    order.status = "CONFIRMED"         # argument mutation
    db.save(order)                     # I/O inside domain logic
    email.send(order.customer_email)   # I/O inside domain logic
```

The fix for the violation above is the functional core / imperative shell split:

```python
# Pure domain function (functional core)
def confirm(order: Order) -> Order:
    return dataclasses.replace(order, status=Status.CONFIRMED)

# Boundary layer (imperative shell) — owns all I/O
order     = db.find(order_id)
confirmed = confirm(order)
db.save(confirmed)
email_queue.enqueue(ConfirmationEmail(confirmed))
```

For language-specific impurity detection signals (Python, Scala, Java, TypeScript), see `references/purity-checklist.md`.

---

## Analysis 2: Idempotency Verification

For each changed function that performs a **state transition** or **write operation**, verify it is idempotent.

### Definition

An operation is **idempotent** if applying it more than once produces the same result as applying it once:

```
f(f(x)) = f(x)   for all x
```

### Scope: Which Functions Require This Analysis

Idempotency analysis applies to:
- Functions that write to a database or external store.
- Functions that publish events or send messages.
- Functions that transition the status or state of a domain entity.
- Event handlers and consumers (at-least-once delivery is the norm in event-driven systems).
- HTTP endpoints that are not idempotent by protocol (POST with side effects, non-safe PATCH).
- Scheduled jobs and background workers.

Idempotency does **not** need to be verified for pure read operations or pure transformations — by definition, applying a pure function twice is always safe.

### Verification Checklist

For each state-changing or write operation in the diff:

```
□ What state does this operation produce?
□ If called again on that produced state — what happens?
□ Does it emit an event or message? Would it emit a duplicate on a second call?
□ If the operation fails mid-way, is the partial result safe to retry?
□ Is there a BDD scenario written for the double-application case?
```

If the operation is not idempotent and no guard is in place, flag it. If the idempotency scenario is absent from the test suite, add it to the coverage gaps.

### The Canonical Idempotency Scenario

Every state-transition operation must have a scenario for the double-application case. If it does not exist, it must be added:

```
Scenario: <Operation> is a no-op when already in target state
  Given a <entity> already in <target-state>
  When <operation> is called again
  Then the <entity> remains in <target-state>
   And no duplicate <event/message/notification> is emitted
```

### Examples

```scala
// IDEMPOTENT — setting a field to a fixed value; second call is identical
def confirm(order: Order): Order =
  order.copy(status = Status.Confirmed)
// Caveat: if this emits an OrderConfirmed event, the event handler must also be idempotent.

// NOT IDEMPOTENT — increments a counter; each call changes the value
def recordAttempt(order: Order): Order =
  order.copy(attempts = order.attempts + 1)
// Fix: use a set of attempt timestamps instead of a counter, or add a guard.

// NOT IDEMPOTENT — unconditional insert; duplicates on retry
def registerPayment(payment: Payment): Unit =
  db.payments.insert(payment)
// Fix: upsert on a unique idempotency key, or check for existence first.
```

---

## Analysis 3: BDD Scenario Coverage

Map every changed function to the BDD scenarios that exercise it. Identify functions with no scenario coverage and scenarios with no implementation path.

### Step 1: Enumerate Changed Functions

List every function, method, or procedure modified in the diff. Group by module or class.

### Step 2: Enumerate Available Scenarios

List all Given/When/Then scenarios in the test suite that exercise, or could be affected by, the changed functions. Include:
- Unit-level scenarios (ScalaTest FeatureSpec, pytest, JUnit 5 `@DisplayName`).
- Integration-level scenarios.
- End-to-end and acceptance scenarios.
- Gherkin feature files.

### Step 3: Build the Coverage Matrix

For each changed function, answer:
1. Is there at least one scenario that exercises the **happy path**?
2. Is there at least one scenario per distinct **failure mode**?
3. Is there a scenario for **double-application** (idempotency), where relevant?
4. Is the scenario testing **behaviour** (what the function does) rather than **implementation** (how it does it)?

Example matrix:

| Function | Happy Path | Failure Modes | Idempotency | Notes |
|---|---|---|---|---|
| `confirm(order)` | ✓ | ✓ CARD_EXPIRED | ✗ Missing | No double-apply scenario |
| `applyDiscount(price, discount)` | ✓ | — | N/A (pure) | Missing 0% and 100% edge cases |
| `registerPayment(payment)` | ✓ | ✓ InvalidCard | ✗ Missing | Duplicate payment scenario absent |

### Step 4: Check Scenario Quality

For each scenario found, verify it meets the xp-clean-code BDD standard:

- **One `When` per scenario.** If you need two `When`s, you have two scenarios.
- **`Then` is a verifiable assertion**, not a vague goal. "Then the error is handled" is not verifiable. "Then the caller receives error code CARD_EXPIRED" is.
- **`Given` makes preconditions explicit** — no invisible setup hidden inside fixtures.
- **No implementation detail** in the scenario. No class names, method signatures, or SQL in Given/When/Then.

### Common Gap Patterns

These patterns reliably indicate missing coverage. Check each one for every changed function:

| Pattern | Signal |
|---|---|
| **Happy path only** | No failure scenario exists alongside the success scenario |
| **Missing idempotency** | State-transition function has no double-application scenario |
| **Missing boundary values** | No scenario for zero, empty, maximum, or null |
| **Uncovered branch** | An `if`/`when`/`match` branch in the function has no corresponding scenario |
| **Vague `Then`** | The assertion is not verifiable ("handled gracefully", "appropriate message") |
| **Hidden fixture** | `Given` is one line but the fixture sets up significant hidden preconditions |
| **Bundled `When`** | A scenario contains two actions — it is two scenarios collapsed into one |
| **Missing contract test** | A dependency is always mocked; no scenario verifies the real contract |
| **No rollback scenario** | A multi-step write has no scenario for what happens if a later step fails |

For worked examples of each pattern with before/after scenarios, see `references/gap-patterns.md`.

---

## Output Format

Produce a structured report with three sections. Use this exact structure:

```
## PR Validation Report

### 1. Purity Analysis

| Function | Module | Classification | Issue |
|---|---|---|---|
| `confirm(order)` | `domain/order.py` | Pure | — |
| `confirm_order(order_id)` | `service/order_service.py` | Impure — violation | Calls db.find and db.save inside domain logic |

**Violations requiring action:**
- `confirm_order` in `service/order_service.py` (line 42): moves db.find/save out of the domain function and into the boundary layer.

---

### 2. Idempotency Analysis

| Operation | Module | Idempotent | Issue |
|---|---|---|---|
| `confirm(order)` | `domain/order.py` | ✓ | — |
| `registerPayment(payment)` | `repo/payment_repo.py` | ✗ | Unconditional insert; no upsert or idempotency key |

**Missing idempotency scenarios:**
- `registerPayment`: no scenario for duplicate payment submission.

---

### 3. BDD Coverage Gaps

**Functions with no scenario coverage:**
- `applyLoyaltyPoints(order, customer)` in `domain/pricing.py` — no scenario exercises this function.

**Functions with incomplete scenario coverage:**
- `confirm(order)`: missing double-application scenario (idempotency).
- `applyDiscount(price, discount)`: missing 0% and 100% boundary cases.

**Scenario quality issues:**
- `"Order is confirmed"` scenario: `Then` clause says "order is handled correctly" — not verifiable; specify the exact state and emitted event.

---

**Verdict:** FAIL — 1 purity violation, 1 idempotency gap, 3 coverage gaps.
```

If all three analyses pass with no findings, abbreviate the report to:

```
## PR Validation Report
All changed functions are pure or appropriately boundary-impure. All state-changing
operations are idempotent and covered by double-application scenarios. BDD scenario
coverage is complete, with no quality issues found.

**Verdict:** PASS
```

---

## Interaction with the xp-clean-code Skill

This skill is the validation layer for the xp-clean-code skill. The relationship is:

| xp-clean-code | pr-validation |
|---|---|
| Write scenarios before writing tests | Verify every changed function has a covering scenario |
| Pure functions and explicit effects | Classify each changed function as Pure / Boundary / Violation |
| Idempotency scenario for every state transition | Check for the double-application scenario in the test suite |
| Refactor as a separate phase | Verify that the diff does not mix behaviour changes with structural changes |
| One step at a time | Flag PRs that touch more than one scenario in a single commit |

---

## Quick Reference

```
Before reporting PASS:
  □ Every changed function classified (Pure / Boundary / Violation)
  □ Every Violation has a specific recommended fix
  □ Every state-changing operation checked for idempotency
  □ Every state-changing operation has a double-application scenario
  □ Coverage matrix built — happy path, failure modes, edge cases
  □ Each scenario checked for one-When, verifiable-Then, explicit-Given

Purity:         Same input → same output; no hidden I/O; no argument mutation
Boundary:       I/O at the outermost layer only; domain logic must be pure
Idempotency:    f(f(x)) = f(x); every state transition needs a double-apply scenario
Coverage:       One scenario per happy path, per failure mode, per edge case
Gap patterns:   Happy-path-only, missing boundary, vague Then, hidden fixture,
                bundled When, missing contract, missing rollback

Report:         Three sections — Purity | Idempotency | Coverage
Verdict:        PASS only when all three sections have zero actionable findings
```

For language-specific impurity detection patterns, see `references/purity-checklist.md`.
For worked examples of each coverage gap pattern, see `references/gap-patterns.md`.
