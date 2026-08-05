---
name: pr-validation
description: >-
  Validate a pull request against XP and clean code standards: purity and
  idempotency of changed functions, BDD scenario coverage, and whether every
  protection the PR body claims ("prevents", "guards against", "blocks") is
  backed by a test that fails when that protection is removed. Triggers on
  "review PR", "validate PR", "PR review", "pull request validation",
  "check coverage", "BDD coverage", "coverage gaps", "missing scenarios",
  "test coverage", "pure function check", "verify purity", "are my functions
  pure", "idempotency check", "verify idempotency", "is this idempotent",
  "verify claims", "PR body claims", "unsubstantiated claim", "mutation check",
  "does this test actually fail", "what's missing from my tests". Composes with
  the xp-clean-code skill: where that skill governs how to build, this skill
  validates that what was built meets those standards.
---

# PR Validation · Purity · Idempotency · BDD Coverage · Protection Claims

This skill audits a pull request against the quality standards established in the xp-clean-code skill. It does not enforce how to build — it verifies that what was built meets the standards.

Run this validation on every PR before it is considered ready for review. The output is a structured report, not a verdict by itself. The report identifies findings; the author decides how to address them.

The rules here are non-negotiable defaults. Deviate only when the user explicitly asks and states a reason.

---

## How to Run This Validation

1. Obtain the diff for the PR (changed files, hunks, line ranges) **and the PR body, title, and commit messages** — Analysis 4 validates the prose against the tests.
2. Identify every changed function, method, or procedure.
3. Run each of the four analyses below independently.
4. Produce the structured gap report.

Always work from the diff. Do not analyse unchanged code unless a changed function calls it and the call site is relevant to the analysis.

| Analysis | Question |
|---|---|
| 1 · Purity | Is each changed function referentially transparent, or justifiably at the boundary? |
| 2 · Idempotency | Is every state transition safe to apply twice? |
| 3 · BDD coverage | Does a scenario exercise every changed behaviour? |
| 4 · Protection claims | Does every protection the PR body claims have a test that fails without it? |

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

The same three classes in Rust, where the signature usually gives the answer before the body does:

```rust
// PURE — consumes and returns; no observable mutation, no ambient input
fn apply_discount(price: Money, discount: Discount) -> Money {
    Money::new(price.amount() * (1.0 - discount.rate()), price.currency())
}

// IMPURE — BOUNDARY (acceptable: adapter module, async, wraps a pure domain value)
async fn save_order(order: &Order, pool: &PgPool) -> Result<(), RepositoryError> {
    sqlx::query!("INSERT INTO orders (id, status) VALUES ($1, $2)", order.id(), order.status())
        .execute(pool)
        .await?;
    Ok(())
}

// IMPURE — VIOLATION (defect: domain module doing I/O, mutating its argument, panicking)
async fn confirm_order(order: &mut Order, pool: &PgPool) {
    let stored = repo::find(order.id(), pool).await.unwrap();  // I/O + panic on failure
    order.status = Status::Confirmed;                          // argument mutation
    repo::save(&stored, pool).await.unwrap();                  // I/O inside domain logic
    email::send(order.customer_email()).await.unwrap();        // I/O inside domain logic
}
```

The fix is the same split — `fn confirm(self) -> Order` in the domain, `async fn` in the adapter:

```rust
// Functional core — total, synchronous, no dependencies on infrastructure
pub fn confirm(order: Order) -> Order {
    Order { status: Status::Confirmed, ..order }
}

// Imperative shell — owns every effect, and every failure is typed
pub async fn confirm_order(id: &OrderId, pool: &PgPool, mail: &impl Mailer)
    -> Result<Order, ConfirmError>
{
    let order     = repo::find(id, pool).await?.ok_or(ConfirmError::NotFound)?;
    let confirmed = confirm(order);
    repo::save(&confirmed, pool).await?;
    mail.enqueue(ConfirmationEmail::for_order(&confirmed)).await?;
    Ok(confirmed)
}
```

For language-specific impurity detection signals (Python, Scala, Java, TypeScript, Rust), see `references/purity-checklist.md`.

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

```rust
// IDEMPOTENT — assigns a fixed state; the second call produces the same value
pub fn confirm(order: Order) -> Order {
    Order { status: Status::Confirmed, ..order }
}

// NOT IDEMPOTENT — increments; every call changes the result
pub fn record_attempt(order: Order) -> Order {
    Order { attempts: order.attempts + 1, ..order }
}
// Fix: store a Set<AttemptId> of observed attempt ids, or guard on the id of the attempt being recorded.

// NOT IDEMPOTENT — unconditional insert; a redelivered message duplicates the row
pub async fn register_payment(payment: &Payment, pool: &PgPool) -> Result<(), RepositoryError> {
    sqlx::query!("INSERT INTO payments (id, order_id, amount) VALUES ($1, $2, $3)",
        payment.id(), payment.order_id(), payment.amount())
        .execute(pool).await?;
    Ok(())
}
// Fix: ON CONFLICT (idempotency_key) DO NOTHING, and assert the returned row count in the test.

// IDEMPOTENT — the state transition is a no-op when already applied, and the event
// is emitted only on an actual transition
pub fn confirm_once(order: Order) -> (Order, Vec<DomainEvent>) {
    match order.status {
        Status::Confirmed => (order, vec![]),
        _ => {
            let id = order.id().clone();
            (Order { status: Status::Confirmed, ..order }, vec![DomainEvent::OrderConfirmed(id)])
        }
    }
}
```

Returning events as a value rather than publishing them makes the "no duplicate event" half of the
idempotency scenario directly assertable — a Rust function that publishes from inside the domain
fails both Analysis 1 and Analysis 2.

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
| **Toothless test** | The test passes when the code it claims to cover is deleted — see Analysis 4 |

For worked examples of each pattern with before/after scenarios, see `references/gap-patterns.md`.

---

## Analysis 4: Protection Claim Verification

**For every assertion the PR body makes about what a check protects against, verify there is a test that fails when that protection is removed.**

A claim of protection is a testable statement. If removing the guard leaves the suite green, the claim is unsubstantiated — the guard is untested, unreachable, or the test passes for an unrelated reason. This analysis is mandatory and applies to the PR body, the PR title, and the commit messages, whoever wrote them.

### Step 1 — Extract the claims

Read the PR body, title, and commit messages. Enumerate every statement that asserts the change prevents, blocks, or handles something. Claim verbs to look for:

```
prevents · protects against · guards against · blocks · rejects · validates
sanitises · ensures · enforces · makes safe · avoids · eliminates · fixes
handles · catches · retries · deduplicates · no longer possible · can't happen
```

Statements that are **not** claims and need no test: renames, refactors with no behaviour change, documentation edits, dependency bumps, formatting, and descriptions of *what the code does* rather than *what it prevents* ("adds a `Region` enum" is not a claim; "prevents shipping to unsupported regions" is).

Record each claim verbatim — the exact sentence from the body — so the report can be checked against the source.

### Step 2 — Locate the protection and its test

For each claim, identify two things in the diff:

1. **The protection site** — the specific lines that implement the guard: the validation, the conditional, the constraint, the retry limit, the idempotency key.
2. **The covering test** — the test or scenario that asserts the protected behaviour.

If you cannot find the protection site, the claim describes something the diff does not do. Flag it immediately as **UNSUBSTANTIATED** and stop; there is nothing to mutate.

If you cannot find a covering test, the claim is **UNSUBSTANTIATED**. Do not proceed to Step 3 — record the missing scenario instead.

### Step 3 — The removal check

Establish a green baseline, then remove the protection and re-run only the mapped tests. **The mapped test must fail.**

```
1. Confirm the mapped test passes as-is.          → baseline green
2. Remove or invert the protection.               → one mutation, smallest possible
3. Re-run the mapped test.                        → it MUST fail
4. Confirm the failure is about the claim.        → not a compile error, not an unrelated assertion
5. Restore the code exactly.                      → git checkout -- <file>
6. Confirm the test passes again.                 → baseline restored
```

**Common mutations, by protection type:**

| Protection | Mutation |
|---|---|
| Guard clause / early return | Delete it |
| Boolean condition | Invert it |
| Validation function | Make it return success unconditionally |
| Boundary comparison | `<` → `<=`, `>=` → `>` |
| Retry / attempt limit | Raise it to a value the test cannot reach |
| Idempotency guard or dedup key | Remove the guard; make the key unique per call |
| Auth / permission check | Return "authorised" unconditionally |
| Error branch | Return a default value instead of the error |
| Timeout | Remove it, or set it beyond the test's window |
| Constraint (DB, type, enum) | Widen it to admit the rejected value |

**Interpreting the outcome:**

| Outcome | Verdict | Meaning |
|---|---|---|
| Mapped test fails, for the claimed reason | **VERIFIED** | The claim is backed by a test with teeth |
| Mapped test still passes | **NOT DETECTED** | The test does not exercise the protection — over-mocked, wrong path, weak assertion, or the guard is unreachable |
| A *different* test fails, mapped test passes | **MISATTRIBUTED** | Coverage exists but the mapped scenario is the wrong one; re-map and repeat |
| Only a compile / type error results | **INCONCLUSIVE** | The mutation was too coarse — the type system rejected it, not the test. Try a subtler mutation that still compiles |
| Tests cannot be run in this environment | **UNVERIFIABLE** | Report the claim as unverified and say why. Never report VERIFIED from reading code alone |

### Safety rules for the removal check

- Mutate a scratch copy or a throwaway worktree, never the branch under review.
- **Never commit a mutation.** Restore after every single one, and verify the restore before the next.
- One mutation at a time. Two simultaneous mutations make the failure unattributable.
- Run only the mapped tests, not the full suite — but confirm the full suite's baseline is green before you start, or a pre-existing failure will read as a verified claim.
- If the toolchain is unavailable (no dependencies installed, no test runner, secrets required), report **UNVERIFIABLE** with the reason. A static reading is not a removal check, and must not be presented as one.

### When you are the author of the PR body

The same rule applies to your own writing, before the PR is opened:

- Do not write a protection claim you have not put through the removal check.
- If the check is unverified, either add the test that makes it fail, or reword the sentence to describe the change without asserting protection: "adds a length check on `Sku`" rather than "prevents malformed SKUs from reaching the database".
- Claims copied from the issue or ticket are not exempt. If the ticket says it prevents X, verify it prevents X.

An unverified protection claim in a PR body is a defect in the PR, on the same footing as a purity violation. It sends a reviewer a guarantee the test suite does not provide.

For worked examples of each mutation type, and for the claim-to-mutation mapping in Python, Scala, TypeScript, and Rust, see `references/claim-verification.md`.

---

## Output Format

Produce a structured report with four sections. Use this exact structure:

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

### 4. Protection Claim Verification

| Claim (from PR body) | Protection site | Mapped test | Mutation applied | Result |
|---|---|---|---|---|
| "Prevents duplicate payments on message redelivery" | `repo/payment_repo.py:31` (`ON CONFLICT DO NOTHING`) | `test_duplicate_payment_is_ignored` | Removed the `ON CONFLICT` clause | **VERIFIED** — test failed on duplicate row count |
| "Blocks cross-user order access" | `api/orders.py:57` (owner check) | `test_forbidden_for_other_user` | Made the owner check return `True` | **NOT DETECTED** — test still passed; it asserts on a 403 produced by the auth middleware, not by this check |
| "Guards against malformed SKUs reaching the database" | not found in diff | — | — | **UNSUBSTANTIATED** — no validation added |

**Unverified claims requiring action:**
- "Blocks cross-user order access": the owner check at `api/orders.py:57` is not covered. The passing test exercises the missing-token path instead. Add a scenario with a valid token for user-42 requesting user-99's order, asserting 403 from the ownership check.
- "Guards against malformed SKUs reaching the database": no such check exists in the diff. Either add it with a covering scenario, or remove the claim from the PR body.

---

**Verdict:** FAIL — 1 purity violation, 1 idempotency gap, 3 coverage gaps, 2 unverified claims.
```

If all four analyses pass with no findings, abbreviate the report to:

```
## PR Validation Report
All changed functions are pure or appropriately boundary-impure. All state-changing
operations are idempotent and covered by double-application scenarios. BDD scenario
coverage is complete, with no quality issues found. Every protection claim in the PR
body was confirmed by a removal check: each mapped test fails when its guard is removed.

**Verdict:** PASS
```

State the removal-check outcome explicitly even when the PR body makes no claims ("the PR body asserts
no protections; Analysis 4 is not applicable") and when the checks could not be run ("Analysis 4:
UNVERIFIABLE — `cargo test` requires a database that is not available in this environment"). Silence
on Analysis 4 reads as a pass it did not earn.

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
| A test that never fails proves nothing | Remove each protection and prove its test fails — for every claim the PR body makes |

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
  □ Every protection claim in the PR body extracted verbatim
  □ Every claim mapped to a protection site and a test
  □ Every mapped test proven to FAIL with its protection removed
  □ Every mutation restored, and the baseline confirmed green again

Purity:         Same input → same output; no hidden I/O; no argument mutation
Boundary:       I/O at the outermost layer only; domain logic must be pure
Idempotency:    f(f(x)) = f(x); every state transition needs a double-apply scenario
Coverage:       One scenario per happy path, per failure mode, per edge case
Gap patterns:   Happy-path-only, missing boundary, vague Then, hidden fixture,
                bundled When, missing contract, missing rollback
Claims:         Every "prevents / blocks / guards against" in the PR body needs a test
                that fails when the guard is removed. No removal check → no claim.

Report:         Four sections — Purity | Idempotency | Coverage | Claims
Verdict:        PASS only when all four sections have zero actionable findings
```

For language-specific impurity detection patterns, see `references/purity-checklist.md`.
For worked examples of each coverage gap pattern, see `references/gap-patterns.md`.
For the claim-to-mutation catalogue and worked removal checks, see `references/claim-verification.md`.
