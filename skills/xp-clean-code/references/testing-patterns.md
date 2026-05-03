# Testing Patterns Reference

Framework-specific patterns for the RED → GREEN → CLEAN cycle.

---

## Java (JUnit 5 + AssertJ)

```java
// Scenario: Given a valid order, When it is placed, Then stock is decremented
@Test
void placingValidOrderDecrementsStock() {
    // Given
    var product = new Product("SKU-001", 10);
    var order = new Order(product, quantity(3));

    // When
    order.place();

    // Then
    assertThat(product.stockLevel()).isEqualTo(7);
}
```

**BDD-style with AssertJ's BDDAssertions:**
```java
import static org.assertj.core.api.BDDAssertions.then;

@Test
void expiredCardProducesCorrectError() {
    given(gateway.charge(expiredCard())).willThrow(CardExpiredException.class);

    var result = paymentService.process(orderWith(expiredCard()));

    then(result.status()).isEqualTo(CARD_EXPIRED);
    then(result.orderState()).isEqualTo(PENDING);
}
```

**Java 21 patterns:**
```java
// Use records for test data builders — immutable, no boilerplate
record TestOrder(String sku, int quantity, PaymentMethod payment) {
    static TestOrder defaults() {
        return new TestOrder("SKU-001", 1, validCard());
    }
    TestOrder withQuantity(int q) { return new TestOrder(sku, q, payment); }
}
```

**Parameterised tests:**
```java
@ParameterizedTest
@MethodSource("invalidQuantities")
void orderRejectedForInvalidQuantity(int quantity, String reason) {
    var order = TestOrder.defaults().withQuantity(quantity);
    assertThatThrownBy(() -> order.place())
        .isInstanceOf(InvalidOrderException.class)
        .hasMessageContaining(reason);
}

static Stream<Arguments> invalidQuantities() {
    return Stream.of(
        Arguments.of(0, "quantity must be positive"),
        Arguments.of(-1, "quantity must be positive"),
        Arguments.of(1000, "exceeds maximum order size")
    );
}
```

---

## Python (pytest)

```python
# Scenario: Given a stream processor, When a malformed message arrives, Then it is sent to dead-letter
def test_malformed_message_goes_to_dead_letter(processor, dead_letter_queue):
    # Given
    message = Message(payload=b"not-valid-json", topic="orders")

    # When
    processor.handle(message)

    # Then
    assert dead_letter_queue.size() == 1
    assert dead_letter_queue.peek().original == message
```

**Fixtures as Given:**
```python
@pytest.fixture
def running_pipeline(spark_session):
    """A pipeline that has processed one checkpoint."""
    pipeline = SparkStreamingPipeline(spark_session)
    pipeline.start()
    pipeline.await_checkpoint(1)
    return pipeline

def test_pipeline_recovers_from_restart(running_pipeline):
    # Given: running_pipeline fixture (already at checkpoint 1)
    # When
    running_pipeline.stop()
    running_pipeline.start()

    # Then
    assert running_pipeline.checkpoint() == 1  # resumes, not restarts
```

**Parametrize for scenario tables:**
```python
@pytest.mark.parametrize("status,expected_topic", [
    ("APPROVED", "orders.approved"),
    ("REJECTED", "orders.rejected"),
    ("PENDING",  "orders.pending"),
])
def test_order_routed_to_correct_topic(order_router, status, expected_topic):
    order = Order(id="O-1", status=status)
    order_router.route(order)
    assert order_router.last_topic == expected_topic
```

---

## PySpark / Structured Streaming

Test Spark logic against small in-memory DataFrames. Never test against a real cluster in unit tests.

```python
def test_deduplication_removes_duplicate_event_ids(spark):
    # Given
    raw = spark.createDataFrame([
        ("evt-1", "order.created", "2024-01-01T10:00:00"),
        ("evt-1", "order.created", "2024-01-01T10:00:00"),  # duplicate
        ("evt-2", "order.shipped", "2024-01-01T11:00:00"),
    ], ["event_id", "event_type", "timestamp"])

    # When
    result = deduplicate(raw, key_col="event_id")

    # Then
    assert result.count() == 2
    assert result.filter(col("event_id") == "evt-1").count() == 1
```

**Testing watermark + windowing logic:**
```python
def test_late_events_outside_watermark_are_dropped(spark):
    # Given — events with a 10-minute watermark, late event at -15min
    events = spark.createDataFrame([
        ("e1", timestamp("10:00")),
        ("e2", timestamp("10:05")),
        ("e3", timestamp("09:45")),  # 15 min late — outside 10-min watermark
    ], ["id", "event_time"])

    # When
    result = apply_watermark_and_window(events, watermark_minutes=10, window_minutes=5)

    # Then — late event not included in any window
    event_ids = {row.id for row in result.collect()}
    assert "e3" not in event_ids
```

---

## TypeScript (Vitest / Jest)

```typescript
// Scenario: Given an unauthenticated request, When a protected resource is accessed, Then 401 is returned
describe('AuthMiddleware', () => {
  it('returns 401 for requests without a bearer token', async () => {
    // Given
    const req = mockRequest({ headers: {} });
    const res = mockResponse();

    // When
    await authMiddleware(req, res, jest.fn());

    // Then
    expect(res.status).toHaveBeenCalledWith(401);
    expect(res.json).toHaveBeenCalledWith({ error: 'UNAUTHORIZED' });
  });
});
```

**Nested describe as scenario grouping:**
```typescript
describe('PaymentProcessor', () => {
  describe('given an expired card', () => {
    it('keeps order in PENDING state', async () => { ... });
    it('returns CARD_EXPIRED error code', async () => { ... });
  });

  describe('given a gateway timeout', () => {
    it('schedules a retry after 60 seconds', async () => { ... });
  });
});
```

---

## Cucumber / Gherkin (for cross-cutting acceptance tests)

When acceptance tests need to be readable by non-engineers (product owners, QA), use Gherkin `.feature` files.

```gherkin
Feature: Order placement

  Scenario: Placing an order decrements stock
    Given a product "Widget A" with 10 units in stock
    And a customer with a valid payment method
    When the customer places an order for 3 units
    Then the stock level for "Widget A" is 7
    And the order status is CONFIRMED

  Scenario Outline: Orders rejected below minimum quantity
    Given a product with sufficient stock
    When a customer attempts to order <quantity> units
    Then the order is rejected with "<reason>"

    Examples:
      | quantity | reason                    |
      | 0        | quantity must be positive |
      | -1       | quantity must be positive |
```

Map Gherkin steps to JUnit 5 (via Cucumber-JVM) or pytest-bdd as appropriate.

---

## General Patterns

### Test naming convention
`[unit under test]_[condition]_[expected outcome]`

```
orderService_givenExpiredCard_returnsCardExpiredError
pipeline_givenLateEvent_dropsItFromWindow
authMiddleware_givenMissingToken_returns401
```

### Arrange–Act–Assert vs Given–When–Then
They are the same structure with different vocabulary:

| BDD | AAA |
|-----|-----|
| Given | Arrange |
| When | Act |
| Then | Assert |

Use Given/When/Then in comments for readability. Use Arrange/Act/Assert when working in a codebase that already uses that convention.

### Test doubles
- **Stub**: returns a fixed value (use when you only care about the output, not how it was reached)
- **Mock**: verifies interactions (use when the key behaviour is a side effect, e.g. a message was published)
- **Fake**: lightweight working implementation (use for repositories, message queues in integration tests)

Prefer fakes and stubs. Overuse of mocks leads to tests that verify implementation rather than behaviour.
