# Total Types — Per-Language Idioms

Reference for Principle 8. Three idioms per language, in the order you need them:

1. **Boundary normalisation** — turning a nullable external representation into a domain type.
2. **ADT declaration** — making invalid combinations unrepresentable.
3. **Exhaustive elimination** — consuming the type without an escape hatch.

Plus two shared sections: the properties any hand-rolled result type must satisfy, and the Python rules that a type checker cannot enforce for you.

---

## Python

Python needs the most discipline: `None` is universal, dicts are structureless, and library boundaries are untyped.

**Boundary normalisation** — the row is not the domain type:

```python
from dataclasses import dataclass
from typing import Any, Mapping

@dataclass(frozen=True)
class CustomerRow:                      # boundary representation — nullable is legal here
    display_name: str | None

@dataclass(frozen=True)
class KnownName:
    value: str

@dataclass(frozen=True)
class Anonymous:
    pass

CustomerName = KnownName | Anonymous    # domain type — no None anywhere in it

def to_customer_name(row: CustomerRow) -> CustomerName:
    return Anonymous() if row.display_name is None else KnownName(row.display_name)
```

Untrusted external data gets a `Result`, not an `Optional` — the reason it was rejected is the point:

```python
def parse_close(row: Mapping[str, Any]) -> Result[DailyClose, RowError]:
    raw = row.get("close")
    if raw is None:
        return Err(RowError.MISSING_CLOSE)
    try:
        price = Decimal(str(raw))
    except InvalidOperation:
        return Err(RowError.UNPARSEABLE_CLOSE)
    if price <= 0:
        return Err(RowError.NON_POSITIVE_CLOSE)
    return Ok(DailyClose(price))
```

**ADT declaration** — frozen dataclasses under a union alias, each variant independently valid:

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
            raise ValueError("Rejected requires at least one reason")   # a defect, so raise

RegistrationResult: TypeAlias = Registered | Rejected
```

Note the tuple: a `list` field on a frozen dataclass is still mutable through its own methods, so `frozen=True` buys less than it appears to. Use `tuple[...]` or `Mapping[...]` for collection fields on value objects.

**Exhaustive elimination** — `match` with `assert_never`:

```python
from typing import assert_never

def message_for(result: RegistrationResult) -> str:
    match result:
        case Registered(customer=customer):
            return f"Welcome, {customer.name}"
        case Rejected(reasons=reasons):
            return "; ".join(r.value for r in reasons)
        case _:
            assert_never(result)
```

`assert_never` is what makes the check real: without it, adding a third variant leaves this function silently returning nothing on the new case. mypy reports an unreachable-code error the moment the union grows and the `case _` becomes reachable.

For two-case types, a `fold` on the type itself is better than a match at every call site — see the conformance section below.

---

## TypeScript

**Boundary normalisation:**

```typescript
type CustomerRow = { display_name: string | null };            // boundary

type CustomerName =                                            // domain
  | { readonly kind: "known"; readonly value: string }
  | { readonly kind: "anonymous" };

function toCustomerName(row: CustomerRow): CustomerName {
  return row.display_name === null
    ? { kind: "anonymous" }
    : { kind: "known", value: row.display_name };
}
```

Parse untrusted input into a `Result`, and keep the schema at the edge — a validator (zod, valibot, io-ts) belongs in the adapter, never imported by domain modules.

**ADT declaration** — a discriminated union with `readonly` on every field:

```typescript
type Payment =
  | { readonly kind: "pending" }
  | { readonly kind: "processing"; readonly startedAt: Instant }
  | { readonly kind: "succeeded"; readonly receipt: Receipt }
  | { readonly kind: "failed";    readonly error: PaymentError };
```

**Exhaustive elimination** — `assertNever` in the default branch:

```typescript
function assertNever(value: never): never {
  throw new Error(`Unhandled case: ${JSON.stringify(value)}`);
}

function messageFor(payment: Payment): string {
  switch (payment.kind) {
    case "pending":    return "Awaiting submission";
    case "processing": return `Started ${payment.startedAt.toISO()}`;
    case "succeeded":  return `Receipt ${payment.receipt.id}`;
    case "failed":     return payment.error.message;
    default:           return assertNever(payment);
  }
}
```

Required config, or none of the above holds: `strict: true` (which includes `strictNullChecks`), plus `noUncheckedIndexedAccess` — without it `array[0]` and `record[key]` are typed as present when they are not, which is null re-entering the core through the index operator.

Banned in domain code: the non-null assertion `!`, `as` casts that remove optionality, and `any`. `unknown` at the boundary is correct — it forces the parse.

---

## Java

**Boundary normalisation** — translate at the adapter, and never return `null` from a domain method:

```java
record CustomerRow(String displayName) {}                      // boundary; may be null

sealed interface CustomerName permits Known, Anonymous {}
record Known(String value) implements CustomerName {}
record Anonymous() implements CustomerName {}

static CustomerName toCustomerName(CustomerRow row) {
    return row.displayName() == null ? new Anonymous() : new Known(row.displayName());
}
```

`Optional` is a return type, not a field type and not a parameter type. An `Optional` field adds a second absent state (`null` Optional vs empty Optional) and is not serialisable in the way most frameworks expect.

**ADT declaration** — sealed interface plus records, validating in the compact constructor:

```java
sealed interface RegistrationResult permits Registered, Rejected {}

record Registered(Customer customer) implements RegistrationResult {}

record Rejected(List<RegistrationError> reasons) implements RegistrationResult {
    Rejected {
        reasons = List.copyOf(reasons);                        // defensive copy: records are shallow
        if (reasons.isEmpty()) {
            throw new IllegalArgumentException("Rejected requires at least one reason");
        }
    }
}
```

**Exhaustive elimination** — a switch expression over a sealed type needs no default, and the compiler enforces coverage:

```java
return switch (result) {
    case Registered r -> "Welcome, " + r.customer().name();
    case Rejected rej -> String.join("; ", rej.reasons().stream().map(RegistrationError::message).toList());
};
```

Adding a permitted subtype turns this into a compile error — which is the point. Writing `default -> …` throws that away.

---

## Scala

The idioms are the language: `Option`, `Either`, sealed traits, and exhaustive `match` need no ceremony.

```scala
// Boundary — the row type admits null from JDBC; the domain type does not
final case class CustomerRow(displayName: String | Null)

enum CustomerName:
  case Known(value: String)
  case Anonymous

def toCustomerName(row: CustomerRow): CustomerName =
  Option(row.displayName).fold(CustomerName.Anonymous)(CustomerName.Known(_))

// ADT — enum cases carry exactly the fields their state requires
enum Payment:
  case Pending
  case Processing(startedAt: Instant)
  case Succeeded(receipt: Receipt)
  case Failed(error: PaymentError)

// Elimination — no default case; -Wnonexhaustive-match makes a gap a warning, -Xfatal-warnings an error
def messageFor(payment: Payment): String = payment match
  case Payment.Pending             => "Awaiting submission"
  case Payment.Processing(startedAt) => s"Started $startedAt"
  case Payment.Succeeded(receipt)  => s"Receipt ${receipt.id}"
  case Payment.Failed(error)       => error.message
```

Turn the warning into an error in CI (`-Wnonexhaustive-match -Xfatal-warnings`); otherwise exhaustiveness is advice. Banned in domain code: `.get` on an `Option`, `.head` on a possibly-empty collection, and `asInstanceOf`.

---

## Rust

Rust is the easy case: `Option` and `Result` are the standard vocabulary, `match` is exhaustive by construction, and there is no null. The work is not adopting the types — it is refusing the escape hatches.

```rust
// Boundary — serde gives you the nullable shape; convert immediately
#[derive(serde::Deserialize)]
struct CustomerRow { display_name: Option<String> }

pub enum CustomerName { Known(String), Anonymous }

impl From<CustomerRow> for CustomerName {
    fn from(row: CustomerRow) -> Self {
        row.display_name.map(CustomerName::Known).unwrap_or(CustomerName::Anonymous)
    }
}

// ADT — each variant carries only what that state has, so impossible combinations cannot be built
pub enum Payment {
    Pending,
    Processing { started_at: DateTime<Utc> },
    Succeeded { receipt: Receipt },
    Failed { error: PaymentError },
}
```

Two Rust-specific notes:

- **`_ =>` on a domain enum is the escape hatch here.** It compiles today and silently absorbs every variant added tomorrow. Match every variant explicitly; if several share a body, list them with `|`.
- **`unwrap_or_default()` is a domain decision in disguise.** `Money::default()` is zero, and zero is a number the rest of the system will happily act on. Substituting it is a fallback that needs a scenario, not a convenience.

The banned-construct table in `SKILL.md` (Principle 7, *Rust: newtypes, ownership, and honest signatures*) covers `unwrap`/`expect`/`panic!` and the `[lints.clippy]` denials that enforce them — this section does not repeat it.

---

## Conformance properties for a hand-rolled result type

Do not couple a codebase to a third-party `Either` when a small local type will do, and do not prescribe one library across an organisation. Define the properties instead. Any implementation — hand-rolled, standard-library, or vendored — must satisfy all six:

```
□ 1. Success and failure are distinct types, not one type with a flag.
□ 2. Error variants are typed — an enum or sealed ADT, not a string or a bare Exception.
□ 3. Elimination is exhaustive — handling one case and forgetting the other is a type error.
□ 4. Values are immutable.
□ 5. Unwrapping does not occur in domain logic.
□ 6. Composition preserves the error type — mapping or chaining never widens E to Any.
```

A ~50-line Python implementation that satisfies all six: `Ok`/`Err` as frozen dataclasses under an abstract base (properties 1, 2, 4), with `map` and `flat_map` for composition (6) and a single `fold(on_ok, on_err)` as the **only** sanctioned unwrap (3, 5). `fold` is what makes property 3 hold without pattern matching: it takes one handler per case, so omitting a case will not type-check, and there is no `.value` for a caller to reach past it.

Judge a candidate library the same way. A `Result` whose `unwrap()` is idiomatic fails property 5 by design; one that erases the error type on `map` fails property 6 and will quietly become `Result[T, Any]` three calls into a pipeline.

---

## Python rules a type checker cannot enforce

Run `mypy --strict` (or pyright in strict mode) in CI, and treat an unannotated function as a build failure. Strict mode already covers implicit `Optional`, untyped definitions and decorators, returning `Any` from a typed function, and unparameterised generics — do not restate those as skill rules, or the skill drifts out of sync with the config that actually enforces them.

These four are not enforceable by configuration and are therefore review obligations:

```
□ No plain dict as a domain record. dict[str, Any] is a boundary type; the line after
  parsing it is where the frozen dataclass appears.
□ No sentinel None where an ADT expresses the state. If the docstring explains what None
  means, the meaning belongs in the type.
□ Closed unions are eliminated with assert_never or a total eliminator (fold) — an
  isinstance ladder with no final assert_never silently ignores new variants.
□ External data is validated at the boundary into a Result with a typed error. This
  includes LLM output, which is untrusted input like any other network response.
```

The second of those is the one that bites hardest in practice. A comment is the tell: the moment a field or return type needs prose to explain what its absence means, the prose is describing a type that has not been written yet.
