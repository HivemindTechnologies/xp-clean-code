---
name: xp-clean-code
description: >-
  Apply Extreme Programming (XP), Clean Code, Domain-Driven Design (DDD),
  and pure functional programming discipline to software development. Use
  this skill whenever writing, reviewing, or extending production code —
  especially when the task involves implementing new behaviour, refactoring,
  adding tests, or defining acceptance criteria. Triggers on phrases like
  "implement feature", "add tests", "refactor", "write a spec", "acceptance
  criteria", "Given/When/Then", "TDD", "BDD", "domain model", "value
  object", "aggregate", "pure function", "side effect", "referential
  transparency", "idempotent", "monad", "Either", "Option", "type hint",
  "type annotation", "mypy", "pyright", or any request to build something
  non-trivial. Composes cleanly with Karpathy-style
  behavioural guidelines: where those address how an agent should reason,
  this skill addresses how code should be built.
---

# XP · Clean Code · DDD · Functional Design

This skill enforces Extreme Programming discipline, Clean Code principles, Domain-Driven Design modelling, and pure functional programming practices when building software. It governs **how** to build, complementing any guidelines that govern **how to reason** (e.g. don't assume, minimal footprint, surgical changes).

The rules here are non-negotiable defaults. Deviate only when the user explicitly asks and states a reason.

---

## The Principles

### 1. Test First — Always

Never write production code without a failing test that demands it.

**The cycle is strict and sequential:**
```
RED   → write a failing test that describes the desired behaviour
GREEN → write the minimum code needed to make it pass — nothing more
CLEAN → refactor to remove duplication and improve clarity
```

Each phase is complete before the next begins. Mixing them is the primary source of over-engineered, hard-to-test code.

**Enforcement rules:**
- If asked to implement something, write the test first. If the user hasn't provided a spec, derive one and confirm it before writing any test.
- "Minimum code to go green" means exactly that. No helper methods, no abstractions, no configuration that the test doesn't exercise.
- A test that never fails proves nothing. Always verify the test fails before making it pass.

---

### 2. BDD Scenarios as Success Criteria

All non-trivial behaviour must be specified as one or more Given/When/Then scenarios **before implementation begins**.

```
Given  [a context or precondition that is true]
When   [an action or event occurs]
Then   [an observable outcome results]
```

**Why this format:**
- *Given* makes implicit preconditions explicit, preventing silent assumptions.
- *When* defines the single trigger — if you need two Whens, you have two scenarios.
- *Then* is a verifiable assertion, not a vague goal.

**Example — bad spec:**
> "The payment service should handle errors gracefully."

**Example — good scenarios:**
```
Given a payment request with an expired card
When the payment is submitted
Then the order remains in PENDING state
 And the caller receives error code CARD_EXPIRED

Given a payment request with a valid card
When the payment gateway times out after 3 seconds
Then the order remains in PENDING state
 And a retry is scheduled for 60 seconds later
```

Scenarios replace free-form success criteria. They are the contract between intent and implementation.

**Rules:**
- Write scenarios before writing tests. Tests are the executable form of scenarios.
- One scenario = one test (or one parameterised case). Never bundle multiple Whens.
- If you cannot write a scenario for it, you do not understand it well enough to build it. Stop and clarify.
- The `And` keyword extends a Given or Then — use it; don't cram multiple conditions into one line.

---

### 3. One Step at a Time

Work in the smallest possible increments. Each step must be independently verifiable.

**The increment contract:**
1. Pick **one** scenario from the backlog.
2. Write **one** failing test for it.
3. Make **only that test** pass.
4. Refactor.
5. Commit.
6. Repeat.

**Hard limits:**
- Never have more than one failing test at a time.
- Never implement ahead of a test — no "I'll need this later" code.
- Never tackle a scenario whose prerequisites are not already green.
- If a change touches more than ~50 lines of production code, the step is too large. Split the scenario.

**Why this matters:** Large steps hide feedback. When something breaks, small steps make the cause obvious. They also make partial progress safe to ship.

---

### 4. Clean Code Invariants

Code is read far more often than it is written. These rules are not style preferences — they are constraints on long-term maintainability.

#### Names reveal intent
```java
// Bad
int d;
List<int[]> list1;

// Good
int elapsedDays;
List<Cell> flaggedCells;
```
- No single-letter names outside loop counters (`i`, `j`) in short, obvious loops.
- No abbreviations unless the domain universally uses them (e.g. `URL`, `HTTP`).
- Boolean names read as questions: `isExpired`, `hasPermission`, `canRetry`.
- Method names are verbs: `calculateTotal`, `sendNotification`, `parseConfig`.

#### Functions do one thing
A function does one thing if you cannot meaningfully extract a sub-function from it with a name that is not a restatement of its implementation. If you need "and" to describe what a function does, split it.

```python
# Bad — does two things
def validate_and_save(user):
    ...

# Good — each does one thing, caller composes them
def validate(user): ...
def save(user): ...
```

#### Comments explain *why*, not *what*
Code describes what it does. Comments explain why a non-obvious decision was made.

```java
// Bad — restates the code
// increment counter
i++;

// Good — explains the why
// Skip the first element; it's always the sentinel value added by the upstream producer
i++;
```

Delete commented-out code. Use version control for history.

#### No surprise side effects
A function that queries should not modify state. A function named `getX()` should not write to a database, send a network request, or mutate a shared object. Side effects must be obvious from the name and signature.

#### Keep it small
- Functions: fits comfortably on one screen (~20 lines is a strong signal to reconsider).
- Classes: one responsibility, one reason to change.
- Files: cohesive. If you need to scroll past unrelated concepts, the file is too large.

---

### 5. Refactor as a Separate Phase

Refactoring is the act of improving the structure of code **without changing its behaviour**. It is not a feature. It is not cleanup. It is a distinct, protected phase in the TDD cycle.

**The refactor contract:**
- All tests must be green before refactoring begins.
- All tests must still be green when refactoring ends.
- No new functionality is introduced during a refactor. If you discover needed behaviour, stop, write a scenario, and come back.
- Refactor in the smallest safe steps: rename → extract → move → inline. Run the tests after each step.

**Common refactor triggers (not excuses to skip green):**
- Duplication: if two code paths look alike, extract the common concept.
- Primitive obsession: if you're passing five related primitives, introduce a value object.
- Long method: extract until each chunk has a clear name.
- Unclear name: rename relentlessly until the code reads like intent.

**What refactoring is NOT:**
- Rewriting a working module because you'd do it differently.
- Cleaning up code you didn't write as part of your current change (see Karpathy: surgical changes).
- Doing a refactor and a feature in the same commit.

---

### 6. Domain-Driven Design as the Modelling Language

The domain model is the core of the software. Code structure must reflect domain structure, not technical infrastructure.

#### Ubiquitous language
Every concept that matters to a domain expert has one precise name, used consistently in code, tests, scenarios, and conversation. When the domain expert says "shipment", the code says `Shipment` — not `DeliveryRecord`, `ShipmentDTO`, or `OrderItem`. Divergence between spoken language and code is a defect.

```python
# Bad — vocabulary diverged from the domain
class DeliveryRecord:
    order_ref: str        # domain expert says "order id"
    dest_address: str     # domain expert says "delivery address"

# Good — ubiquitous language throughout
class Shipment:
    order_id: OrderId
    delivery_address: Address
```

#### Value objects over primitives
Replace primitive obsession with value objects. A value object has no identity — two instances with the same data are equal. Value objects are immutable by definition, eliminating an entire class of mutation bugs and making the domain contract explicit in the type signature.

```scala
// Bad — stringly typed, no contract
def charge(cardNumber: String, amount: Double): Unit

// Good — types encode the domain contract
def charge(card: CardNumber, amount: Money): ChargeResult
```

#### Entities have identity, not structural equality
An `Order` is the same order whether its status is `PENDING` or `CONFIRMED`. Model identity explicitly. Never compare entities by field value.

#### Aggregates enforce consistency boundaries
Only the aggregate root is reachable from outside the aggregate. Invariants that span multiple objects belong in the aggregate, not in a service. If a service is enforcing an invariant, it belongs inside an aggregate.

#### Domain events make state transitions explicit
Rather than mutating state silently, emit a typed, immutable event for every significant transition:
```
OrderPlaced  PaymentConfirmed  ShipmentDispatched  OrderCancelled
```
Events are value objects. They are the auditable history of the domain and the natural integration point between bounded contexts.

#### Bounded contexts prevent model leakage
A `Customer` in the billing context is not the same type as a `Customer` in the shipping context. Expect name collisions across contexts; resolve them with anti-corruption layers, never by sharing a single model across boundaries.

---

### 7. Pure Functions and Explicit Effects

Prefer pure functions everywhere the language and domain allow. Push side effects to the boundary and make them explicit in the type system.

#### Referential transparency
A function is referentially transparent if any call to it can be replaced with its return value without changing the program's behaviour. This is the strongest correctness guarantee a function can provide — it is trivially testable, freely composable, and safe to retry.

```scala
// Not referentially transparent — depends on hidden external state
def currentDiscount(): BigDecimal = discountService.fetch()

// Referentially transparent — same input, always same output
def applyDiscount(price: Money, discount: Discount): Money =
  price * (1 - discount.rate)
```

#### Immutability by default
Never mutate data. Produce new values through transformations. Use `val`, frozen dataclasses, records, or persistent data structures by default. Mutation is the exception and must be justified.

#### Side effects at the boundary
Pure domain logic must not reach out to databases, clocks, random number generators, or network services. Pass what is needed as an argument; return what changed as a value. I/O belongs at the outermost layer.

```python
# Bad — I/O buried in domain logic, impossible to test without mocks
def confirm_order(order_id: str) -> None:
    order = db.find(order_id)
    order.status = "CONFIRMED"
    db.save(order)
    email_service.send_confirmation(order)

# Good — pure core; caller owns the I/O
def confirm(order: Order) -> Order:
    return dataclasses.replace(order, status=Status.CONFIRMED)

# At the boundary:
order     = db.find(order_id)
confirmed = confirm(order)
db.save(confirmed)
email_queue.enqueue(ConfirmationEmail(confirmed))
```

#### Idempotency
Design operations so that applying them more than once produces the same result as applying them once. This is essential for retries, event replay, and at-least-once delivery guarantees. Always write an explicit scenario for double-application:

```
Scenario: Confirming an already-confirmed order is a no-op
  Given an order in CONFIRMED state
  When confirm is called again
  Then the order remains in CONFIRMED state
   And no duplicate ConfirmationEvent is emitted
```

#### Function composition over mutation
Chain pure transformations rather than accumulating mutations on a shared variable. Prefer pipelines.

```scala
// Bad — mutates a shared variable through sequential statements
var result = order
result = applyDiscount(result)
result = addTax(result)
result = applyLoyaltyPoints(result)

// Good — composed pipeline; each step is independently testable
val result = applyLoyaltyPoints(addTax(applyDiscount(order)))

// Or with pipe syntax where available
val result = order |> applyDiscount |> addTax |> applyLoyaltyPoints
```

#### Monadic types for explicit effects
When a computation may fail, be absent, or involve I/O, encode that in the return type. Never use `null`, unchecked exceptions, or hidden I/O as substitutes for an honest type signature.

| Effect | Preferred type |
|---|---|
| Value may be absent | `Option[A]` / `Maybe a` / `Optional<A>` |
| Recoverable failure | `Either[Error, A]` / `Result<A, E>` |
| Async / I/O | `IO[A]` / `Future[A]` / `Task<A>` |
| Multiple validation errors | `Validated[Errors, A]` |

Compose effects with `map`, `flatMap` / `bind`, and `fold`. Never unwrap a monadic type inside domain logic — propagate it to the caller.

```scala
// for-comprehension sequences effects; any Left short-circuits the chain
def processPayment(order: Order, card: CardNumber): Either[PaymentError, Receipt] =
  for {
    validated <- validateCard(card)
    charged   <- gateway.charge(validated, order.total)
    receipt   <- Receipt.from(charged)
  } yield receipt
```

The happy path reads linearly. Error handling is structural, not scattered across catch blocks.

#### Declarative types in dynamically typed languages

Type annotations in Python and similar languages are not enforced at runtime, but they are a first-class requirement. They are the machine-readable contract of every function — enabling static analysis, IDE support, and early error detection via mypy or pyright. An unannotated function is a build failure, not a style issue. Run `mypy --strict` or `pyright` in CI.

**Every function signature must be fully annotated:**

```python
# Bad — reader must trace the body to understand what flows in and out
def calculate_discount(customer, order_total):
    ...

# Good — contract is visible at the call site
def calculate_discount(customer: Customer, order_total: Money) -> Discount:
    ...
```

**Use `NewType` for domain identifiers — never raw primitives:**

```python
from typing import NewType
from decimal import Decimal

OrderId    = NewType("OrderId", str)
CustomerId = NewType("CustomerId", str)

# The type system now rejects passing a CustomerId where OrderId is expected
def find_order(order_id: OrderId) -> Optional[Order]: ...
```

This is the Python expression of *value objects over primitives* (Principle 6). A `NewType` wrapper is zero-cost at runtime but catches entire classes of argument-order bugs statically.

**Use `@dataclass(frozen=True)` for value objects:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

@dataclass(frozen=True)
class Order:
    id: OrderId
    customer_id: CustomerId
    total: Money
    status: OrderStatus
```

`frozen=True` enforces immutability at runtime and signals value-object intent. Never use plain `dict` for structured domain data.

**Parameterise all collections; declare optionality explicitly:**

```python
# Bad
def get_orders(customer_id) -> list:
    ...

# Good
def get_orders(customer_id: CustomerId) -> list[Order]:
    ...

def find_customer(customer_id: CustomerId) -> Optional[Customer]:
    ...
```

---

## Interaction with Other Guidelines

This skill is additive. When used alongside Karpathy-style behavioural rules:

| Karpathy Principle | Reinforcement |
|---|---|
| Clarify before acting | Write the BDD scenario first — it forces shared understanding before any code exists |
| Minimal footprint | TDD enforces this mechanically — you cannot write code without a test that demands it |
| Surgical changes | Refactor-as-separate-phase keeps structural improvements out of feature commits |
| Goal-driven execution | Given/When/Then *is* the success criterion, made verifiable |
| Don't assume | Ubiquitous language surfaces hidden assumptions — if the name is wrong, the model is wrong |
| Avoid hidden state | Pure functions and immutability make all state explicit and traceable |

---

## Quick Reference

```
Before any code:    Write scenario (Given/When/Then)
Before production:  Write failing test (RED)
To pass the test:   Minimum code only (GREEN)
After green:        Refactor separately (CLEAN)
Commit unit:        One scenario, green + clean

Names:              Ubiquitous language — match domain expert vocabulary exactly
Types:              Value objects over primitives; types encode the domain contract
Aggregates:         One root, enforces its own invariants, emits domain events
Contexts:           Bounded — never share a model across context boundaries

Functions:          Pure by default — referentially transparent, no hidden I/O
Immutability:       Default to val / frozen / record; mutation requires justification
Effects:            Push I/O to the boundary; model with Option / Either / IO
Composition:        map/flatMap over mutation; pipelines over sequential statements
Idempotency:        Write a scenario for double-application of every state transition
Typing:             Annotate every signature in dynamic languages; unannotated = build failure

Comments:           Why, never what
```

For language- or framework-specific testing patterns, see `references/testing-patterns.md`.
For worked examples of BDD scenarios across common problem types, see `references/scenario-examples.md`.
