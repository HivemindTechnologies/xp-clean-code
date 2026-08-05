# Protection Claim Verification — Mutation Catalogue and Worked Checks

Reference for Analysis 4 of the PR Validation skill.

**The rule:** for every assertion the PR body makes about what a check protects against, there must be a test that fails when that protection is removed. Prove it by removing the protection and watching the test fail. A guard whose removal breaks nothing is not a guard — it is decoration, and the PR body is promising the reviewer something the suite does not deliver.

---

## Why reading the code is not enough

Every one of these is a real way a protection claim passes review and fails in production, with a green suite the whole time:

| Failure | What it looks like |
|---|---|
| **Unreachable guard** | An earlier validation already rejects the input, so the new check never runs. Removing it changes nothing. |
| **Over-mocked test** | The test stubs the collaborator that contains the guard. It asserts the stub's return value, not the guard. |
| **Wrong path asserted** | The test gets the expected 403, but from the auth middleware, not from the new ownership check. |
| **Assertion too weak** | `assert result.is_err()` passes for *any* error, including one raised before the guard is reached. |
| **Guard on the wrong layer** | The DB constraint does the work; the application check is dead. (Or the reverse — and the constraint is the one claimed.) |
| **Test asserts the mock was called** | `verify(validator).validate(sku)` passes whether or not validation rejects anything. |
| **Fixture never triggers it** | The test data is valid, so the rejection branch is never exercised; only the happy path runs. |

In all seven cases the code review reads correctly. Only the removal check separates them from a real protection.

---

## The procedure

```bash
# 0. Work somewhere disposable — never mutate the branch under review
git worktree add /tmp/claim-check HEAD
cd /tmp/claim-check

# 1. Baseline: the mapped test passes, and the suite is otherwise green
pytest tests/test_payments.py::test_duplicate_payment_is_ignored -q

# 2. Mutate — one protection, smallest possible edit
#    (edit the guard)

# 3. Re-run ONLY the mapped test — it MUST fail
pytest tests/test_payments.py::test_duplicate_payment_is_ignored -q

# 4. Restore, and confirm green again before the next claim
git checkout -- src/repo/payment_repo.py
pytest tests/test_payments.py::test_duplicate_payment_is_ignored -q
```

Then remove the worktree: `git worktree remove /tmp/claim-check`.

**Non-negotiables:** one mutation at a time; restore before the next; never commit a mutation; confirm the baseline is green before you start, or a pre-existing failure will masquerade as a verified claim.

If the mutation only produces a compile or type error, it was too coarse — the type checker rejected it, not the test. Find a mutation that still compiles (widen a comparison, return a valid-but-wrong value) and repeat.

---

## Mutation catalogue by protection type

### Guard clause / early return — delete it

```python
def withdraw(account: Account, amount: Money) -> Result[Account, WithdrawalError]:
    if amount > account.balance:                      # ← delete these two lines
        return Err(WithdrawalError.InsufficientFunds)
    return Ok(replace(account, balance=account.balance - amount))
```

Expect: the overdraft test fails. If it still passes, the test is asserting on something else — often a balance check performed by the caller.

### Boolean condition — invert it

```typescript
// Claim: "blocks requests without the admin role"
if (!user.roles.includes('admin')) return forbidden();   // original
if (user.roles.includes('admin')) return forbidden();    // mutated
```

Inversion is stronger than deletion here: it fails both directions, so a test that passes under inversion is asserting nothing about the role at all.

### Validation function — make it succeed unconditionally

```rust
// Claim: "prevents malformed SKUs from reaching the database"
impl Sku {
    pub fn parse(raw: &str) -> Result<Self, ValidationError> {
        // if raw.len() != 7 || !raw.starts_with("SKU-") {
        //     return Err(ValidationError::MalformedSku);
        // }
        Ok(Self(raw.to_owned()))
    }
}
```

Expect: the malformed-SKU test fails. A common surprise — it still passes because the *database* rejects the value and the test asserts on the resulting error, meaning the claim belongs to the schema, not to this code.

### Boundary comparison — shift it by one

```scala
// Claim: "rejects orders above the 999-unit maximum"
if (quantity > MaxOrderSize)  // original
if (quantity >= MaxOrderSize) // mutated — now 999 is rejected, 1000 still is
```

This is the mutation that finds off-by-one coverage gaps: a suite that only tests 1 and 5000 passes under both versions, proving the boundary itself is untested.

### Retry / attempt limit — raise it out of reach

```python
MAX_RETRIES = 3      # original
MAX_RETRIES = 10_000 # mutated
```

Expect: the "max retries exceeded" test fails. If it passes, the test is probably asserting the retry *count* after three failures rather than the transition to `PERMANENTLY_FAILED`.

### Idempotency guard — remove it

```rust
// Claim: "redelivered confirmations do not emit duplicate events"
pub fn confirm_once(order: Order) -> (Order, Vec<DomainEvent>) {
    // match order.status {
    //     Status::Confirmed => return (order, vec![]),
    //     _ => {}
    // }
    let id = order.id().clone();
    (Order { status: Status::Confirmed, ..order }, vec![DomainEvent::OrderConfirmed(id)])
}
```

Expect: the double-application test fails on the event count. This mutation is the bridge between Analysis 2 and Analysis 4 — an idempotency claim with no failing removal check is an untested idempotency guard.

### Deduplication key — make it unique per call

```sql
-- Claim: "prevents duplicate payment rows on retry"
INSERT INTO payments (...) VALUES (...) ON CONFLICT (idempotency_key) DO NOTHING;  -- original
INSERT INTO payments (...) VALUES (...);                                           -- mutated
```

Expect: the retry test fails on `SELECT count(*)`. If the test only asserts "no error was raised", it never checked for the duplicate at all.

### Auth / permission check — authorise unconditionally

```python
# Claim: "users can no longer read other users' orders"
def can_read(user: User, order: Order) -> bool:
    return True   # was: return order.customer_id == user.customer_id
```

Expect: the cross-user test fails with 200 instead of 403. The classic false pass: the test's request has no token, so the middleware returns 401 and the ownership check is never reached.

### Error branch — return a default instead

```typescript
// Claim: "malformed messages go to the dead-letter queue instead of crashing the consumer"
const parsed = OrderEvent.safeParse(raw);
if (!parsed.success) return deadLetter(raw);   // ← replace with: return;
```

Expect: the DLQ test fails on queue size. A test that only asserts "the consumer did not throw" passes under the mutation and proves nothing about the DLQ.

### Timeout — remove it

```rust
// Claim: "a hanging gateway can no longer block the worker indefinitely"
let response = tokio::time::timeout(Duration::from_secs(5), gateway.charge(card)).await;
// mutated: let response = gateway.charge(card).await;
```

Expect: the timeout test fails — ideally by exceeding its own deadline rather than hanging forever. Give any such test its own harness timeout so the mutated run terminates.

### Constraint (schema, enum, type) — widen it

```sql
ALTER TABLE orders ALTER COLUMN customer_id DROP NOT NULL;   -- mutation, in a scratch DB only
```

Expect: the migration or repository test fails on insert. Rust and TypeScript equivalents: replace an exhaustive `match` with a catch-all arm, or a discriminated union with `any` — then check that a test notices.

---

## Worked example: a claim that fails verification

**PR body:** "Prevents cross-user order access — users can only read their own orders."

**Protection site** — `api/orders.py:57`:
```python
@router.get("/api/orders/{order_id}")
async def get_order(order_id: OrderId, user: User = Depends(current_user)) -> OrderResponse:
    order = await repo.find(order_id)
    if order.customer_id != user.customer_id:      # the claimed protection
        raise HTTPException(403, detail="FORBIDDEN")
    return OrderResponse.from_domain(order)
```

**Mapped test** — the only test mentioning 403:
```python
async def test_forbidden_for_other_user(client: TestClient) -> None:
    response = await client.get("/api/orders/ORD-999")
    assert response.status_code == 403
```

**Mutation:** replace the condition with `if False:`.

**Result:** the test still passes → **NOT DETECTED**.

**Diagnosis:** the request carries no auth token, so `current_user` rejects it before the handler body runs. The 403 comes from the dependency, not from the ownership check. The claimed protection has no coverage whatsoever.

**The finding, as it belongs in the report:**

```
Gap: Unverified protection claim
Claim: "Prevents cross-user order access — users can only read their own orders."
Protection site: api/orders.py:57 (customer_id comparison)
Mapped test: test_forbidden_for_other_user — passes with the check disabled
Missing scenario:
  Given a user "user-42" with a valid token
   And an order "ORD-999" belonging to "user-99"
  When GET /api/orders/ORD-999 is called
  Then the response status is 403
   And the response body contains error code FORBIDDEN
   And no order data is returned
Severity: Critical
Reason: The claimed authorisation check is untested. The existing 403 test exercises the
        missing-token path. Deleting line 57 leaves the suite green, so any refactor can
        silently expose every user's orders.
```

Note what the fixed test needs: a *valid* token for the wrong user. That is exactly the precondition the original `Given` omitted — which is why gap Pattern 6 (hidden fixture preconditions) and unverified claims so often appear together.

---

## Reporting statuses

Use these verbatim in the report table:

| Status | Meaning | Action for the author |
|---|---|---|
| **VERIFIED** | Mapped test failed on removal, for the claimed reason | None |
| **NOT DETECTED** | Test passed with the protection removed | Add or fix the scenario; the claim stands only once its test fails |
| **MISATTRIBUTED** | A different test caught the mutation | Re-map the claim to that test and re-run; usually a naming problem |
| **UNSUBSTANTIATED** | No protection site, or no test, found for the claim | Add the check and the test, or delete the claim from the PR body |
| **INCONCLUSIVE** | Every available mutation failed to compile | Try a subtler mutation; if none exists, say so and explain what the type system already guarantees |
| **UNVERIFIABLE** | Tests could not be run here | State the reason explicitly; never report VERIFIED from a static reading |

Severity for Analysis 4 findings:

- **Critical** — an unverified security, authorisation, data-integrity, or idempotency claim.
- **High** — an unverified claim about a failure mode, boundary, or retry limit.
- **Medium** — a claim that is covered, but by a test asserting the outcome indirectly.
- **Low** — an imprecise claim where the protection and its test both exist and pass the removal check, but the body describes them loosely.

---

## Writing claims that survive verification

When you author the PR body, the claim and its evidence go in together:

```markdown
<!-- Bad — a promise with nothing behind it -->
Prevents duplicate payments.

<!-- Good — the claim, the guard, and the test that fails without it -->
Prevents duplicate payment rows when a confirmation message is redelivered
(`payment_repo.py:31`, `ON CONFLICT (idempotency_key) DO NOTHING`).
Verified: `test_duplicate_payment_is_ignored` fails on row count with the
`ON CONFLICT` clause removed.

<!-- Also good — descriptive, asserts no protection, needs no removal check -->
Adds a length and prefix check to `Sku::parse`.
```

If the removal check has not been run, the third form is the honest one. Reword rather than promise.
