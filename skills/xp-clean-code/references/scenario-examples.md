# BDD Scenario Examples

Worked examples of Given/When/Then across common problem types. Use these as templates when drafting scenarios from a vague requirement.

---

## How to use this file

1. Find the problem type closest to your task.
2. Use the scenario structure as a template.
3. Replace the domain terms with your own.
4. Confirm the scenarios with the requester before writing any tests.

---

## Data Pipeline / Streaming

**Requirement:** "Process Kafka events and write to Iceberg"

```
Scenario: Happy path ingestion
  Given a valid order event arrives on topic orders.raw
  When the pipeline processes the event
  Then a row is written to the orders Iceberg table
   And the row contains the correct order_id, status, and event_time
   And the event is committed to the consumer group offset

Scenario: Malformed event handling
  Given an event arrives with a payload that cannot be parsed as OrderEvent
  When the pipeline attempts to process it
  Then the event is written to the dead-letter topic orders.dlq
   And the pipeline continues processing subsequent events
   And no row is written to the Iceberg table

Scenario: Exactly-once under restart
  Given the pipeline has committed checkpoint N
   And events N+1 through N+5 have been written to Iceberg but not checkpointed
  When the pipeline restarts
  Then events N+1 through N+5 are not duplicated in the Iceberg table
   And the pipeline resumes from checkpoint N
```

---

## Authentication / Authorisation

**Requirement:** "Users should only access their own data"

```
Scenario: Authorised access
  Given a user with id "user-42" and a valid JWT
  When they request GET /api/orders?userId=user-42
  Then the response contains orders belonging to user-42
   And the status code is 200

Scenario: Cross-user access attempt
  Given a user with id "user-42" and a valid JWT
  When they request GET /api/orders?userId=user-99
  Then the response status is 403
   And the response body contains error code FORBIDDEN
   And no order data is returned

Scenario: Expired token
  Given a user with an expired JWT (expired 1 second ago)
  When they request any protected resource
  Then the response status is 401
   And the response body contains error code TOKEN_EXPIRED
```

---

## Payment Processing

**Requirement:** "Handle payment failures without losing orders"

```
Scenario: Successful payment
  Given an order in PENDING state
   And a customer with a valid, non-expired card
  When the payment is processed
  Then the order transitions to CONFIRMED
   And the customer receives a confirmation event on orders.confirmed

Scenario: Card declined
  Given an order in PENDING state
   And a customer whose card is declined by the gateway
  When the payment is processed
  Then the order remains in PENDING state
   And the customer receives error code CARD_DECLINED
   And no charge is applied to the card

Scenario: Gateway timeout
  Given an order in PENDING state
   And the payment gateway does not respond within 5 seconds
  When the payment is processed
  Then the order remains in PENDING state
   And a retry is scheduled for 60 seconds later
   And the retry count is incremented to 1

Scenario: Maximum retries exceeded
  Given an order in PENDING state with retry count 3
   And the payment gateway times out again
  When the payment is processed
  Then the order transitions to PAYMENT_FAILED
   And no further retries are scheduled
   And the customer is notified via the failure event topic
```

---

## REST API

**Requirement:** "Create a product endpoint"

```
Scenario: Create product — valid input
  Given a request body with name "Widget", price 9.99, and stock 100
  When POST /api/products is called with a valid auth token
  Then the response status is 201
   And the response body contains the created product with a server-assigned id
   And the product is retrievable via GET /api/products/{id}

Scenario: Create product — missing required field
  Given a request body with name "Widget" but no price
  When POST /api/products is called
  Then the response status is 400
   And the response body lists "price" as a missing field

Scenario: Create product — unauthenticated
  Given a request body with all required fields
  When POST /api/products is called without an auth token
  Then the response status is 401
```

---

## Background Jobs / Workers

**Requirement:** "Retry failed notifications"

```
Scenario: First retry succeeds
  Given a notification in FAILED state with retry count 0
   And the notification service is available
  When the retry worker runs
  Then the notification status transitions to SENT
   And the retry count remains 0 (not incremented on success)
   And the notification is not re-queued

Scenario: Retry fails, more attempts remaining
  Given a notification in FAILED state with retry count 1
   And the notification service is unavailable
  When the retry worker runs
  Then the notification status remains FAILED
   And the retry count is incremented to 2
   And the notification is re-queued with exponential backoff delay

Scenario: Max retries reached
  Given a notification in FAILED state with retry count 5 (the maximum)
   And the notification service is unavailable
  When the retry worker runs
  Then the notification status transitions to PERMANENTLY_FAILED
   And the notification is not re-queued
   And an alert is emitted to the ops monitoring topic
```

---

## Domain Logic / Business Rules

**Requirement:** "Discount logic for loyalty customers"

```
Scenario: Standard customer — no discount
  Given a customer with loyalty tier STANDARD
   And an order total of €100.00
  When the discount is calculated
  Then the discount amount is €0.00
   And the final price is €100.00

Scenario: Gold customer — 10% discount
  Given a customer with loyalty tier GOLD
   And an order total of €100.00
  When the discount is calculated
  Then the discount amount is €10.00
   And the final price is €90.00

Scenario: Discount does not apply to delivery fees
  Given a GOLD customer
   And an order total of €100.00 with a €5.00 delivery fee
  When the discount is calculated
  Then the discount applies to €100.00 only
   And the final price is €90.00 + €5.00 = €95.00
```

---

## Tips for Writing Good Scenarios

### Start with the unhappy paths
Engineers naturally think of the happy path first. Write at least one failure scenario for every success scenario — they often reveal missing requirements faster.

### One When per scenario
If you find yourself writing "When X happens and then Y happens", split into two scenarios or use a Background block for shared setup.

### Avoid UI details in scenarios
```
# Bad — too implementation-specific
When the user clicks the "Submit Order" button

# Good — describes intent
When the order is submitted
```

### Quantify Thens where precision matters
```
# Weak
Then the stock is reduced

# Strong
Then the stock level is decremented by the ordered quantity
```

### Scenarios as documentation
Well-named scenarios become living documentation. Name them so a product owner can read the scenario list and understand what the system does:
- "Placing an order decrements stock" ✓
- "Test order placement" ✗
