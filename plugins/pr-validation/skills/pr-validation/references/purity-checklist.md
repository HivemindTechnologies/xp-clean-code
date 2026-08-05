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

## Rust

Rust's signatures carry more purity information than any other language on this list — read them first, then confirm against the body.

### Signature-level signals (check these before reading the body)

| Signature | Reading |
|---|---|
| `fn f(&self) -> T` | Likely pure — no mutation possible through `&self` alone |
| `fn f(self) -> Self` | Pure transformation — consumes and produces |
| `fn f(&mut self)` | Mutates the receiver; pure only in the "builder returning nothing" sense — check whether the caller observes an intermediate state |
| `fn f(x: &mut T)` | Mutates the caller's value — argument mutation |
| `fn f(...) -> ()` with a body that does work | Almost certainly a side effect; where did the result go? |
| `async fn` | I/O by construction — boundary only |
| `fn f(...) -> Result<T, E>` | Honest about failure — positive signal |
| `unsafe fn` | Cannot be reasoned about as pure; flag in domain code |

`&self` is not a purity *proof* — interior mutability (below) mutates through a shared reference. Check for it explicitly.

### Impurity signals

```rust
// Clock reads
std::time::SystemTime::now();
std::time::Instant::now();
chrono::Utc::now();

// Random reads
rand::random::<u64>();
rand::thread_rng().gen_range(0..10);
uuid::Uuid::new_v4();

// Environment / config reads
std::env::var("API_KEY");
std::env::args();

// I/O — files
std::fs::read_to_string("path");
tokio::fs::write("path", data).await;

// I/O — network / HTTP
reqwest::get(url).await;
client.post(url).send().await;

// I/O — database
sqlx::query!("SELECT ...").fetch_one(&pool).await;
diesel::insert_into(orders::table).values(&order).execute(conn);

// Logging / tracing (write-only side effect)
tracing::info!("...");       // acceptable at boundary, flag inside domain logic
println!("...");             // flag anywhere outside a binary's main or tests

// Argument mutation
fn enrich(order: &mut Order) {
    order.status = Status::Confirmed;   // mutates the caller's value
}

// Interior mutability — mutation through a shared reference; defeats &self
use std::cell::RefCell;
self.cache.borrow_mut().insert(key, value);
self.counter.fetch_add(1, Ordering::SeqCst);
self.lock.lock().unwrap().push(item);
static INIT: OnceCell<Config> = OnceCell::new();

// Global mutable state
static mut COUNTER: u64 = 0;
lazy_static! { static ref CACHE: Mutex<HashMap<String, String>> = ...; }

// Panic as control flow — a hidden effect the signature denies
let order = repo.find(id).unwrap();
let parsed: u32 = raw.parse().expect("must be numeric");
panic!("unreachable");   // on a reachable path
```

### Pure function markers

```rust
// Newtype value objects — structural equality, no identity
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Money { amount: i64, currency: Currency }

// Consumes and returns; no mutation observable by the caller
impl Order {
    pub fn confirm(self) -> Order {
        Order { status: Status::Confirmed, ..self }
    }
}

// Typed, exhaustive failure in the return type
fn validate(request: OrderRequest) -> Result<Order, ValidationError>;
fn find_by_email(email: &Email, index: &CustomerIndex) -> Option<&Customer>;

// Effects injected as traits — the function stays a function of its arguments
fn schedule_retry(order: &Order, clock: &impl Clock) -> RetryPlan;

// const fn is compiler-proven pure
const fn tax_rate_for(region: Region) -> Rate;

// #[must_use] proves the result is the point, not a side effect
#[must_use]
fn apply_discount(price: Money, discount: Discount) -> Money;

// Iterator pipeline instead of a mutable accumulator
let total: Money = lines.iter().filter(|l| l.is_taxable()).map(Line::subtotal).sum();
```

### Rust-specific verification questions

Add these to the Analysis 1 checklist for every changed Rust function:

```
□ Does it take &mut on self or any argument? Is that mutation the point of the function, or an accident?
□ Does it use RefCell / Cell / Mutex / RwLock / atomics / OnceCell — mutation hidden behind &self?
□ Does it call unwrap() / expect() / panic! on a path a caller can reach?
□ Is it async, or does it await? If so, is it in an adapter module rather than domain?
□ Does it read a clock, RNG, or env var directly instead of taking a trait?
□ Does it reach for unsafe?
□ Does the error type erase information (anyhow::Error / Box<dyn Error>) where the caller must branch on the failure?
```

A changed function that trades `Result<T, DomainError>` for `anyhow::Result<T>` inside the domain is a regression even though it still compiles — flag it as a violation of honest signatures.

---

## Boundary Layer Identification

A function is an acceptable I/O boundary if **all** of the following hold:

1. It lives in an infrastructure or adapter layer (not in `domain/`, `core/`, or `logic/`).
2. All domain logic it calls is pure — the I/O wraps pure functions, not the reverse.
3. Its tests isolate the I/O with test doubles (in-memory store, stub clock, fake HTTP server).
4. Its name or package makes the side effect obvious (`UserRepository`, `EmailSender`, `OrderController`).

In Rust the layer boundary is usually a module or crate split — `domain/` or a `-core` crate that
depends on neither `tokio` nor `sqlx` nor `reqwest`, with adapters in `infra/`, `adapters/`, or a
separate `-api` crate. A new I/O dependency appearing in the domain crate's `Cargo.toml` is itself a
finding: check the manifest diff, not just the source diff.

If these conditions are not met, the function is an **Impure — violation**, even if it lives at the edge of the codebase.
