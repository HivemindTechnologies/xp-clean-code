# Testing Patterns Reference

Framework-specific patterns for the RED → GREEN → CLEAN cycle.

---

## Scala (ScalaTest + GivenWhenThen)

ScalaTest's `GivenWhenThen` trait adds `given`, `when`, `andWhen`, `then`, and `and` methods that print labelled steps to the test report, keeping the prose scenario and the executable assertion in the same place.

**FeatureSpec — acceptance-level scenarios:**
```scala
import org.scalatest.featurespec.AnyFeatureSpec
import org.scalatest.GivenWhenThen
import org.scalatest.matchers.should.Matchers

class OrderPlacementSpec extends AnyFeatureSpec with GivenWhenThen with Matchers {

  Feature("Order placement") {

    Scenario("Placing a valid order decrements stock") {
      given("a product with 10 units in stock")
      val product = Product(sku = "SKU-001", stock = 10)

      and("an order for 3 units")
      val order = Order(product, quantity = 3)

      when("the order is placed")
      order.place()

      then("the stock level is 7")
      product.stockLevel shouldBe 7
    }

    Scenario("Placing an order with insufficient stock is rejected") {
      given("a product with 2 units in stock")
      val product = Product(sku = "SKU-001", stock = 2)

      and("an order for 5 units")
      val order = Order(product, quantity = 5)

      when("the order is placed")
      then("an InsufficientStockException is raised")
      an[InsufficientStockException] should be thrownBy order.place()

      and("the stock level is unchanged")
      product.stockLevel shouldBe 2
    }
  }
}
```

**FlatSpec — unit-level, one scenario per `it` block:**
```scala
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.GivenWhenThen
import org.scalatest.matchers.should.Matchers

class PaymentServiceSpec extends AnyFlatSpec with GivenWhenThen with Matchers {

  "PaymentService" should "keep order PENDING when the card is expired" in {
    given("an order in PENDING state with an expired card")
    val order   = Order(id = "O-1", status = Pending)
    val payment = Payment(card = expiredCard())

    when("the payment is processed")
    val result = PaymentService.process(order, payment)

    then("the order remains PENDING")
    result.orderStatus shouldBe Pending

    and("the error code is CARD_EXPIRED")
    result.errorCode shouldBe Some(CardExpired)
  }

  it should "schedule a retry when the gateway times out" in {
    given("an order in PENDING state")
    val order = Order(id = "O-2", status = Pending)

    and("a gateway that times out after 5 seconds")
    val gateway = TimingOutGateway(timeoutSeconds = 5)

    when("the payment is processed")
    val result = PaymentService.process(order, Payment(validCard()), gateway)

    then("the order remains PENDING")
    result.orderStatus shouldBe Pending

    and("a retry is scheduled for 60 seconds later")
    result.scheduledRetry shouldBe Some(RetryAfter(seconds = 60))
  }
}
```

**Table-driven / parameterised with TableDrivenPropertyChecks:**
```scala
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.GivenWhenThen
import org.scalatest.matchers.should.Matchers
import org.scalatest.prop.TableDrivenPropertyChecks.*

class DiscountSpec extends AnyFlatSpec with GivenWhenThen with Matchers {

  private val loyaltyTiers = Table(
    ("tier",     "orderTotal", "expectedDiscount"),
    (Standard,   BigDecimal(100), BigDecimal(0)),
    (Gold,       BigDecimal(100), BigDecimal(10)),
    (Platinum,   BigDecimal(100), BigDecimal(20)),
  )

  "DiscountCalculator" should "apply the correct discount per loyalty tier" in {
    forAll(loyaltyTiers) { (tier, orderTotal, expectedDiscount) =>
      given(s"a $tier customer with an order total of €$orderTotal")
      val customer = Customer(loyaltyTier = tier)

      when("the discount is calculated")
      val discount = DiscountCalculator.calculate(customer, orderTotal)

      then(s"the discount is €$expectedDiscount")
      discount shouldBe expectedDiscount
    }
  }
}
```

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
