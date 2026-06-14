# Purity Checklist — Language-Specific Detection Patterns

This reference lists language-specific signals that indicate impurity in changed functions. Use it during Analysis 1 of the PR Validation skill.

---

## Python

### Impurity signals

```python
# Clock reads
import datetime; datetime.datetime.now()
import time; time.time()

# Random reads
import random; random.random()
import uuid; uuid.uuid4()

# Environment reads
import os; os.environ["KEY"]
os.getenv("KEY")

# I/O — files
open("path", "r")
pathlib.Path("file").read_text()

# I/O — network / HTTP
import requests; requests.get(url)
import httpx; httpx.post(url)

# I/O — database (common ORMs)
session.query(Model)
Model.objects.get(id=...)
db.execute("SELECT ...")

# Logging (write-only side effect)
import logging; logger.info(...)  # acceptable at boundary, flag inside domain logic

# Argument mutation
def f(items: list[str]) -> None:
    items.append("x")  # mutates caller's list — impure

# Global state mutation
_cache: dict = {}
def f(key: str) -> str:
    _cache[key] = "value"  # impure
```

### Pure function markers (positive signals)

```python
# Frozen dataclasses — value produced, not mutated
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

# Returns a new value derived from input
def apply_discount(price: Money, discount: Discount) -> Money:
    return Money(price.amount * (1 - discount.rate), price.currency)

# Explicit failure in return type — not hidden in exceptions
def parse_age(raw: str) -> Either[ValidationError, Age]:
    ...
```

---

## Scala

### Impurity signals

```scala
// Side-effecting return types
def f(): Unit       // almost always impure
def f(): Future[_]  // async I/O; acceptable at boundary only

// Direct I/O
import scala.io.Source
Source.fromFile("path")

// Database / slick
db.run(query)

// HTTP
http.singleRequest(request)

// Mutability
var counter = 0
counter += 1

import scala.collection.mutable
val buf = mutable.ListBuffer[Int]()

// System reads
System.currentTimeMillis()
java.time.LocalDateTime.now()
scala.util.Random.nextInt()

// Logging inside domain logic
logger.info("...")  // side effect; flag if inside a domain function
```

### Pure function markers

```scala
// Immutable by default
val result = order.copy(status = Status.Confirmed)

// Algebraic effect types
def confirm(order: Order): Either[DomainError, Order]
def findByEmail(email: Email): Option[Customer]
def process(cmd: Command): IO[Event]

// For-comprehension chains pure effects
for {
  validated <- validate(input)
  enriched  <- enrich(validated)
} yield enriched
```

---

## Java (17+)

### Impurity signals

```java
// Date/time
LocalDateTime.now();
Instant.now();
new Date();
System.currentTimeMillis();

// Random
new Random().nextInt();
UUID.randomUUID();

// I/O
new FileReader("path");
HttpClient.newHttpClient().send(request, handler);

// Database
entityManager.persist(entity);
jdbcTemplate.update("INSERT ...");
repository.save(entity);

// Static mutable state
private static final Map<String, String> CACHE = new HashMap<>();

// Mutation of argument
void enrich(Order order) {
    order.setStatus(Status.CONFIRMED);  // mutates caller's object
}
```

### Pure function markers

```java
// Records — immutable value objects
record Money(BigDecimal amount, String currency) {}
record Discount(BigDecimal rate) {}

// Returns new value, does not mutate
Money applyDiscount(Money price, Discount discount) {
    return new Money(
        price.amount().multiply(BigDecimal.ONE.subtract(discount.rate())),
        price.currency()
    );
}

// Explicit failure — Optional or Result
Optional<Customer> findByEmail(Email email) { ... }
Either<ValidationError, Order> validate(OrderRequest request) { ... }
```

---

## TypeScript / JavaScript

### Impurity signals

```typescript
// Date/time
new Date();
Date.now();

// Random
Math.random();
crypto.randomUUID();

// Environment
process.env.API_KEY;

// I/O — fetch / axios
await fetch(url);
await axios.get(url);

// I/O — database
await prisma.order.findUnique({ where: { id } });
await db.query("SELECT ...");

// File system (Node)
fs.readFileSync("path");
await fs.promises.readFile("path");

// Mutation of argument
function enrich(order: Order): void {
    order.status = "CONFIRMED";  // mutates caller's object
}

// Global / module-level mutation
let requestCount = 0;
requestCount++;
```

### Pure function markers

```typescript
// Immutable update via spread
const confirmed = { ...order, status: "CONFIRMED" } as const;

// Readonly inputs signal intent
function applyDiscount(price: Money, discount: Discount): Money {
    return { amount: price.amount * (1 - discount.rate), currency: price.currency };
}

// Explicit failure via discriminated union
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };
function parseAge(raw: string): Result<Age, ValidationError> { ... }
```

---

## Boundary Layer Identification

A function is an acceptable I/O boundary if **all** of the following hold:

1. It lives in an infrastructure or adapter layer (not in `domain/`, `core/`, or `logic/`).
2. All domain logic it calls is pure — the I/O wraps pure functions, not the reverse.
3. Its tests isolate the I/O with test doubles (in-memory store, stub clock, fake HTTP server).
4. Its name or package makes the side effect obvious (`UserRepository`, `EmailSender`, `OrderController`).

If these conditions are not met, the function is an **Impure — violation**, even if it lives at the edge of the codebase.
