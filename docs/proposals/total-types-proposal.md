# Proposal · Total Types and Explicit Outcomes

> **Status: adopted with amendments** (see `plugins/xp-clean-code/skills/xp-clean-code/SKILL.md`
> Principle 8 and `references/total-types.md`). §§1–5, 7, 8 and 10 were taken as written; §6 was
> trimmed to the four rules `mypy --strict` cannot enforce, to stop the skill duplicating tool
> configuration; §9's "zero optional fields" was restated as *every optional carries a one-line
> reason, and dependent optionals become a sum type*, because a literal reading flags
> well-modelled measurement snapshots. The proposed four-file per-language split was rejected in
> favour of one `total-types.md` with per-language sections, matching the existing
> `purity-checklist.md` shape, and Rust was added — the proposal predates it.
>
> Kept for provenance. The skill, not this file, is the operative version.

---

Your current skill already states the right principle—absence and recoverable failure should appear explicitly in return types—but it needs stronger **decision rules, boundary rules, and enforcement rules**. At present, `Option`, `Either`, and `Optional` are grouped as “monadic types for explicit effects,” while Python examples still use `Optional` without defining when absence is legitimate or how callers must eliminate it. 

I would introduce a language-neutral section called something like **Total Types and Explicit Outcomes**.

## 1. Start with the semantic distinction

The most important rule is that these types are not interchangeable:

| Situation | Model |
|---|---|
| A value genuinely may not exist, and absence is expected | `Option<T>` |
| An operation can fail for a known, recoverable reason | `Either<E, T>` / `Result<T, E>` |
| A value can be one of several domain cases | Sealed ADT / discriminated union |
| Multiple independent validation errors should accumulate | `Validated<E, T>` or equivalent |
| An invariant is broken or the process cannot continue | Exception, assertion, or process failure |

This prevents the common pattern where `Optional` becomes a generic “something went wrong” container.

A useful governing rule is:

> Use `Option` only when the caller does not need an explanation for absence. Use `Either` when the caller may need to distinguish, report, recover from, or test the unsuccessful outcome.

For example:

```text
findPromotion(code) -> Option<Promotion>
```

Absence is normal: no applicable promotion exists.

```text
placeOrder(command) -> Either<PlaceOrderError, Order>
```

Failure has business meaning: customer suspended, item unavailable, payment rejected.

## 2. Ban nullable domain types

Establish a strict invariant:

> Within the typed application core, no domain value may be `null`, `None`, or `undefined`.

Allow nullable values only in explicitly identified boundary representations:

- Database rows
- JSON or HTTP payloads
- Framework callbacks
- Legacy APIs
- Deserialization DTOs
- Foreign library interfaces

Every boundary must immediately translate nullable representations into domain types.

```typescript
type CustomerRow = {
  display_name: string | null;
};

type CustomerName =
  | { readonly kind: "known"; readonly value: string }
  | { readonly kind: "anonymous" };

function toCustomerName(value: string | null): CustomerName {
  return value === null
    ? { kind: "anonymous" }
    : { kind: "known", value };
}
```

The critical idea is not merely “check for null.” It is **normalize at the boundary so null cannot travel through the application**.

## 3. Prefer ADTs over combinations of booleans and optionals

An optional field is often hiding multiple states.

Bad:

```typescript
type Payment = {
  receipt?: Receipt;
  failureReason?: string;
  isProcessing: boolean;
};
```

This permits contradictory and impossible states.

Better:

```typescript
type Payment =
  | { readonly kind: "pending" }
  | { readonly kind: "processing"; readonly startedAt: Instant }
  | { readonly kind: "succeeded"; readonly receipt: Receipt }
  | { readonly kind: "failed"; readonly error: PaymentError };
```

Add this rule:

> When optional fields depend on one another, replace the containing structure with a sum type.

Typical warning signs:

- More than one optional field in a domain object
- An optional value whose validity depends on a status enum
- Boolean flags that control whether another field exists
- Comments such as “only populated when…”
- Constructors that accept partially valid states

## 4. Require exhaustive elimination

Introducing an ADT is not sufficient. Callers must consume it safely.

The policy should require:

- Exhaustive pattern matching
- No default branch for closed domain ADTs
- No forced unwrap
- No unchecked casts to remove optionality
- No `get()`, `.value`, `!!`, `as T`, or equivalent escape hatches
- No silently substituting arbitrary defaults

TypeScript:

```typescript
function assertNever(value: never): never {
  throw new Error(`Unhandled case: ${JSON.stringify(value)}`);
}

function messageFor(result: PaymentResult): string {
  switch (result.kind) {
    case "approved":
      return `Receipt ${result.receipt.id}`;
    case "declined":
      return result.reason.message;
    case "unavailable":
      return "Payment service unavailable";
    default:
      return assertNever(result);
  }
}
```

Java:

```java
return switch (result) {
    case Approved approved ->
        "Receipt " + approved.receipt().id();
    case Declined declined ->
        declined.reason().message();
    case Unavailable ignored ->
        "Payment service unavailable";
};
```

Python requires more discipline because static exhaustiveness is weaker:

```python
from typing import assert_never

def message_for(result: PaymentResult) -> str:
    match result:
        case Approved(receipt=receipt):
            return f"Receipt {receipt.id}"
        case Declined(reason=reason):
            return reason.message
        case Unavailable():
            return "Payment service unavailable"
        case _:
            assert_never(result)
```

For Python, `assert_never` should be mandatory in closed-union pattern matches.

## 5. Make illegal construction difficult

The rules should cover construction as well as consumption.

> ADT cases must be immutable, fully initialized, and independently valid.

TypeScript:

```typescript
type RegistrationResult =
  | {
      readonly kind: "registered";
      readonly customer: Customer;
    }
  | {
      readonly kind: "rejected";
      readonly reasons: readonly RegistrationError[];
    };
```

Java:

```java
sealed interface RegistrationResult
    permits Registered, Rejected {}

record Registered(Customer customer)
    implements RegistrationResult {}

record Rejected(List<RegistrationError> reasons)
    implements RegistrationResult {
    Rejected {
        reasons = List.copyOf(reasons);
        if (reasons.isEmpty()) {
            throw new IllegalArgumentException(
                "Rejected requires at least one reason"
            );
        }
    }
}
```

Python:

```python
from dataclasses import dataclass
from typing import TypeAlias

@dataclass(frozen=True)
class Registered:
    customer: Customer

@dataclass(frozen=True)
class Rejected:
    reasons: tuple[RegistrationError, ...]

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError("Rejected requires at least one reason")

RegistrationResult: TypeAlias = Registered | Rejected
```

## 6. Give Python stricter rules than the other languages

Python is the worst offender because `None`, dynamic dictionaries, partial initialization, and unchecked library boundaries interact badly.

I would explicitly require:

```text
Python:
- Enable strict Optional checking.
- Prohibit implicit Optional.
- Prohibit untyped decorators and untyped function bodies.
- Prohibit returning Any from typed functions.
- Prohibit plain dictionaries as domain records.
- Prohibit sentinel None when a dedicated ADT can express the state.
- Require assert_never for closed unions.
- Require boundary validation for external data.
```

For mypy, the policy should at least expect strict mode and prevent gradual-typing escape hatches. For pyright, use strict type-checking mode.

Also distinguish:

```python
# Legitimate absence
def find_customer(customer_id: CustomerId) -> Customer | None:
    ...

# Domain failure
def register_customer(
    command: RegisterCustomer,
) -> Registered | RegistrationRejected:
    ...
```

Do not use this:

```python
def register_customer(
    command: RegisterCustomer,
) -> Customer | None:
    ...
```

That signature destroys the reason registration failed.

## 7. Avoid library-specific monads in the core guideline

I would make the guideline semantic rather than prescribing one third-party `Either` implementation.

For example:

- TypeScript can use discriminated unions or a `Result` library.
- Java can use sealed interfaces, records, and optionally a library such as Vavr.
- Python can use tagged frozen dataclasses and unions, or a carefully selected `Result` library.

The standard should define the required properties:

1. Success and failure are distinct types.
2. Error variants are typed.
3. Matching is exhaustive.
4. Values are immutable.
5. Unwrapping is not used in domain logic.
6. Composition preserves the error type.

That avoids coupling the whole engineering organization to a particular library.

## 8. Define when exceptions remain appropriate

A blanket “never throw exceptions” rule becomes counterproductive.

Use typed return values for:

- Business rejection
- Expected lookup absence
- Validation failure
- Concurrency conflicts callers can retry
- External failures callers can meaningfully handle

Use exceptions for:

- Violated programmer invariants
- Corrupt internal state
- Misconfiguration during startup
- Resource exhaustion
- Framework-required propagation
- Failures that cannot be handled locally

The important distinction is:

> `Either` represents an outcome in the function’s contract. An exception represents failure to fulfil or execute that contract.

At infrastructure boundaries, catch external exceptions and translate them into a small typed error vocabulary:

```python
def load_customer(
    repository: CustomerRepository,
    customer_id: CustomerId,
) -> Customer | CustomerLoadError:
    try:
        customer = repository.get(customer_id)
    except DatabaseTimeout:
        return CustomerLoadUnavailable(customer_id)

    if customer is None:
        return CustomerNotFound(customer_id)

    return customer
```

Avoid leaking `SQLException`, `AxiosError`, or arbitrary Python exceptions into domain code.

## 9. Add an “optional field budget”

A useful opinionated rule is:

> Domain entities should normally contain zero optional fields. Every optional field requires justification.

This is deliberately stricter than normal style guidance. Optional fields often indicate:

- A missing subtype
- A state transition that has not been modelled
- An aggregate with mixed lifecycle stages
- A read model being confused with a domain model
- A database DTO leaking into the domain

Some optional fields are legitimate, such as a genuinely optional customer-provided note. But the burden should be on the model to demonstrate that absence has one clear meaning.

## 10. Encode this as a review decision tree

Your agentic skill will work better with a deterministic review flow:

```text
For every nullable or optional value:

1. Can the value be made mandatory by construction?
   - Yes: make it mandatory.
   - No: continue.

2. Is absence a normal, explanation-free outcome?
   - Yes: use Option.
   - No: continue.

3. Does the unsuccessful outcome have domain meaning?
   - Yes: use Either/Result with a closed error ADT.
   - No: continue.

4. Are several lifecycle states being represented?
   - Yes: replace the structure with an ADT.
   - No: continue.

5. Is the value nullable only because it came from an external system?
   - Yes: convert it at the boundary.
   - No: require explicit justification.
```

## Suggested core wording for the skill

A compact version could be:

> **Null is not a domain type.** Do not permit `null`, `None`, or `undefined` inside the typed application core. Nullable values may exist only in boundary representations and must be translated immediately into a mandatory value, `Option`, `Either`, or a domain ADT.
>
> Use `Option<A>` only for expected absence where the caller requires no explanation. Use `Either<E, A>` or `Result<A, E>` for expected failures that callers may inspect, report, recover from, or test. Use a sealed ADT when a value has multiple lifecycle or domain states.
>
> Make all variants immutable and valid by construction. Consume closed ADTs exhaustively. Do not use forced unwraps, unchecked casts, nullable assertions, default branches, or arbitrary fallback values to bypass the type model.
>
> Multiple optional fields in one domain type are a modelling warning. Replace conditionally related fields and status flags with a sum type so that invalid combinations are unrepresentable.
>
> Exceptions are reserved for broken invariants, defects, unrecoverable infrastructure conditions, and framework boundaries. Translate expected infrastructure failures into typed application errors before they enter domain logic.

I would put the language-independent rules in `SKILL.md`, then move language-specific enforcement into:

```text
references/
  total-types.md
  typescript.md
  java.md
  python.md
```

That keeps the main skill compact while allowing Python to carry substantially stricter guidance than Java or TypeScript.
