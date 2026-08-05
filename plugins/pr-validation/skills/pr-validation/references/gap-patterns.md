# BDD Coverage Gap Patterns

Common patterns of missing or inadequate BDD scenario coverage. Use this reference during Analysis 3 of the PR Validation skill to identify gaps systematically.

---

## Pattern 1: Happy Path Only

**Signal:** The only scenario tests the golden path. No failure scenarios exist.

**Example — gap:**
```
Scenario: User logs in successfully
  Given a registered user with email "alice@example.com" and password "correct"
  When the user submits the login form
  Then the user is redirected to the dashboard
```

**Missing scenarios:**
```
Scenario: Login fails with wrong password
  Given a registered user with email "alice@example.com"
  When the user submits the login form with password "wrong"
  Then an authentication error is returned
   And the user remains on the login page

Scenario: Login fails for unknown email
  Given no user registered with email "unknown@example.com"
  When the user submits the login form
  Then a "credentials not found" error is returned

Scenario: Login is rejected after too many failed attempts
  Given a user account locked after 5 failed attempts
  When the user submits the login form with correct credentials
  Then a "account locked" error is returned
   And the lockout expiry time is included in the response
```

---

## Pattern 2: Missing Idempotency Scenario

**Signal:** A state-transition operation exists but there is no scenario for double-application.

**Example — gap:**
```
Scenario: Order is confirmed on payment success
  Given an order in PENDING state
  When payment is received
  Then the order moves to CONFIRMED state
   And an OrderConfirmed event is emitted
```

**Missing scenario:**
```
Scenario: Confirming an already-confirmed order is a no-op
  Given an order already in CONFIRMED state
  When payment confirmation is received again
  Then the order remains in CONFIRMED state
   And no duplicate OrderConfirmed event is emitted
```

**Why this matters:** At-least-once delivery is standard in event-driven systems. If the payment confirmation message is redelivered, the handler runs twice. Without an idempotency scenario, this case is untested.

---

## Pattern 3: Missing Boundary / Edge Case

**Signal:** Scenarios exist for typical values but not for boundaries (zero, empty, maximum, null).

**Example — gap:**
```
Scenario: Discount is applied to the total
  Given an order total of £100
  When a 20% discount is applied
  Then the discounted total is £80
```

**Missing scenarios:**
```
Scenario: Zero discount leaves the total unchanged
  Given an order total of £100
  When a 0% discount is applied
  Then the discounted total is £100

Scenario: Full discount zeroes the total
  Given an order total of £100
  When a 100% discount is applied
  Then the discounted total is £0

Scenario: Discount is not applied to a zero-value order
  Given an order total of £0
  When any discount is applied
  Then the total remains £0
```

---

## Pattern 4: Each Conditional Branch Needs a Scenario

**Signal:** A function contains an `if`/`when`/`match` with N branches, but fewer than N scenarios cover it.

**Code under review:**
```python
def calculate_shipping(order: Order) -> Money:
    if order.is_express:
        return EXPRESS_RATE * order.weight
    elif order.destination.is_international:
        return INTERNATIONAL_RATE * order.weight
    else:
        return STANDARD_RATE * order.weight
```

**Required scenarios (one per branch):**
```
Scenario: Express orders use the express shipping rate
Scenario: International standard orders use the international rate
Scenario: Domestic standard orders use the standard rate
```

If any branch lacks a scenario, the PR is missing coverage.

**The same check on an exhaustive `match`** — every arm is a scenario, including the ones the compiler
forced the author to write:

```rust
pub fn shipping_cost(order: &Order) -> Money {
    match (order.speed(), order.destination().region()) {
        (Speed::Express, _)                 => EXPRESS_RATE * order.weight(),
        (Speed::Standard, Region::Domestic) => STANDARD_RATE * order.weight(),
        (Speed::Standard, Region::Eu)       => EU_RATE * order.weight(),
        (Speed::Standard, Region::RestOfWorld) => INTERNATIONAL_RATE * order.weight(),
    }
}
```

```
Scenario: Express orders use the express rate regardless of destination
Scenario: Standard domestic orders use the standard rate
Scenario: Standard EU orders use the EU rate
Scenario: Standard rest-of-world orders use the international rate
```

Four arms, four scenarios. A catch-all `_ =>` arm is its own scenario and a smell besides: it silences
the exhaustiveness check, so a new `Region` variant will route to a default rate with no test failure.
Flag `_` arms over domain enums in the report.

---

## Pattern 5: Vague `Then` Clause

**Signal:** The `Then` states an intention rather than a verifiable assertion.

**Defective scenarios:**
```
# Too vague — "gracefully" is not verifiable
Then the system handles the error gracefully

# Too vague — "appropriate" is subjective
Then an appropriate error message is displayed

# Tests implementation, not behaviour
Then the OrderService.confirm method is called once
```

**Fixed scenarios:**
```
# Specific, verifiable outcome
Then the caller receives error code CARD_EXPIRED
 And the order remains in PENDING state

# Specific user-facing output
Then the user sees the message "Your card has expired. Please update your payment details."

# Behaviour, not implementation
Then the order moves to CONFIRMED state
 And an OrderConfirmed event is emitted with the confirmation timestamp
```

---

## Pattern 6: Given Hides Preconditions in Fixtures

**Signal:** The `Given` is short but the test fixture sets up significant hidden state. The scenario is not self-describing.

**Defective scenario:**
```
Given the standard test setup
When an order is placed
Then the order is accepted
```

**Fixed scenario:**
```
Given a registered customer with a valid payment method on file
 And inventory showing 3 units of product SKU-001 in stock
When the customer places an order for 2 units of SKU-001
Then the order is accepted
 And inventory is decremented to 1 unit of SKU-001
```

The `Given` must state every precondition that affects the outcome. A reader should understand the scenario without reading the fixture.

---

## Pattern 7: Multiple `When` Clauses (Two Scenarios Bundled as One)

**Signal:** A scenario has more than one `When`, or uses `And` to add a second action.

**Defective scenario:**
```
Given a cart with 3 items
When the user adds a 4th item
 And the user checks out
Then the order total includes all 4 items
```

**Fixed — split into two scenarios:**
```
Scenario: Adding an item increases the cart total
  Given a cart with 3 items totalling £60
  When the user adds a £20 item
  Then the cart total is £80
   And the cart contains 4 items

Scenario: Checkout creates an order from the current cart
  Given a cart with 4 items totalling £80
  When the user checks out
  Then an order is created with total £80
   And the cart is emptied
```

---

## Pattern 8: Missing Integration / Contract Scenario

**Signal:** A function calls an external dependency, but the only scenarios mock the dependency out completely. No scenario verifies the contract with the real system.

**Code under review:**
```python
def notify_customer(order: Order, notification_service: NotificationService) -> None:
    notification_service.send(
        recipient=order.customer_email,
        template="order_confirmed",
        context={"order_id": order.id, "total": str(order.total)},
    )
```

**Gap:** All tests stub `NotificationService`. No scenario verifies that the template `"order_confirmed"` exists or that the context keys match what the template expects.

**Recommended scenario (integration level):**
```
Scenario: Order confirmation email renders correctly
  Given a confirmed order with id "ORD-001" and total £99.99
  When the order confirmation notification is sent
  Then an email is delivered to the customer
   And the email subject contains "Order ORD-001 confirmed"
   And the email body contains "£99.99"
```

---

## Pattern 9: Concurrent / Race Condition Scenarios

**Signal:** A function modifies shared state but has no scenario for concurrent access.

**Relevant when:**
- A function reads-then-writes (check-then-act).
- Multiple instances can run simultaneously (workers, distributed systems).
- The function uses optimistic locking or versioning.

**Example gap:**
```python
def reserve_seat(seat_id: SeatId, booking_id: BookingId) -> Seat:
    seat = seat_repo.find(seat_id)
    if seat.is_available:
        return seat_repo.save(seat.reserve(booking_id))
    raise SeatUnavailableError(seat_id)
```

**Missing scenario:**
```
Scenario: Concurrent reservation attempts — only one succeeds
  Given seat A1 is available
  When two booking requests attempt to reserve A1 simultaneously
  Then exactly one reservation succeeds
   And the other receives a SeatUnavailable error
   And seat A1 has exactly one confirmed booking
```

---

## Pattern 10: No Scenario for Partial Failure / Rollback

**Signal:** A function performs multiple writes or side effects but has no scenario for what happens if one step fails after others have succeeded.

**Example:**
```python
def transfer_funds(source: Account, target: Account, amount: Money) -> Transfer:
    debit(source, amount)       # succeeds
    credit(target, amount)      # fails — what now?
    return emit_transfer_event(source, target, amount)
```

**Missing scenario:**
```
Scenario: Failed credit leaves source account unchanged
  Given a source account with £500 and a target account
  When a transfer of £100 is attempted and the credit step fails
  Then the source account balance remains £500
   And no transfer event is emitted
   And the caller receives a TransferFailedError
```

---

## Pattern 11: Absence Conflated With Failure

**Signal:** A function returns an `Option`/nullable, and the empty value has more than one cause. No scenario distinguishes "there was genuinely nothing to return" from "the computation could not be performed".

**Code under review:**
```python
def gamma_flip(chain: Sequence[ChainOption], spot: float) -> Optional[Strike]:
    """The strike where net dealer gamma crosses zero. None if there is no crossing."""
```

Two very different facts arrive as the same `None`:

1. Net gamma has the same sign at every strike — **the market has no flip in this range.**
2. Only a narrow window of strikes was fetched, so any crossing lies outside it — **the search could not see the flip.**

**Existing scenario:**
```
Scenario: A chain with no gamma crossing reports no flip
  Given a chain whose net gamma is positive at every strike
  When the gamma flip is computed
  Then no flip is reported
```

**Missing scenario — and the reason the model is wrong:**
```
Scenario: A flip outside the searched strike range is reported as un-searched, not absent
  Given a chain fetched over a +/-2% window around spot
   And net gamma of the same sign at both ends of that window
  When the gamma flip is computed
  Then the result reports that no crossing was found within the searched range
   And the searched range is included in the result
   And it is distinguishable from a chain that has no crossing at all
```

The scenario cannot be written against `Optional[Strike]` — there is nowhere for "the searched range" to live. That is the tell: **when a missing scenario cannot be expressed against the current return type, the return type is the defect.** The fix is a result type carrying the bounds (`FlipSearch { low, high, gex_at_low, gex_at_high, flip }`), or an ADT with `NoCrossing` and `OutsideSearchedRange` as distinct cases.

**Why this matters:** a consumer deciding whether to act on a signal treats "no flip exists" as information and "we could not look far enough" as a data problem. Collapsed into one `None`, the second reads as the first, and the system acts confidently on a measurement it never made. This pattern is a coverage gap and a modelling defect at once — report it under both Analysis 1 (dishonest signature) and Analysis 3.

**How to screen for it quickly:** read the docstring of every `Option`-returning function in the diff. If the sentence explaining the empty case contains "or", or the body has more than one `return None`, look closer.

**Then apply the deciding test, because that screen over-triggers.** Several guards can serve one cause:

```python
def compute_vol_richness(history: VolHistory, min_sample: int) -> Optional[VolRichness]:
    """None when there is no screen to compute at all — an empty series on either side,
    or a zero current HV."""
    if not iv or not hv or hv[-1] == 0.0:
        return None
```

Three conditions, one `None`, an "or" in the docstring — and it is correctly modelled. Every branch means *"there is no usable series"*, and the caller withholds the reading in all three cases. Splitting it would produce variants no caller branches on.

> The deciding test is not how many ways the function can return empty. It is whether a caller would **act differently**, **report differently**, or need a **different scenario** depending on which way it did.

Apply it before writing the finding. `_to_nomination`'s five rejections fail the test (each is a different malformed-output report a debugger needs); `compute_vol_richness`'s three guards pass it. A report that flags both has spent its credibility on the one that was already right.

---

## Coverage Gap Summary Template

When reporting gaps, use this format for each finding:

```
Gap: <Pattern name>
Function: <function or module>
Missing scenario:
  Given <precondition>
  When  <trigger>
  Then  <outcome>
Severity: Critical | High | Medium | Low
Reason: <why this gap matters — what could go wrong without this scenario>
```

Severity guidance:
- **Critical** — missing idempotency, missing failure rollback, missing concurrent access.
- **High** — missing primary failure mode, missing boundary value that triggers different branch.
- **Medium** — missing edge case that is handled but untested, vague Then.
- **Low** — fixture transparency, cosmetic scenario quality.
