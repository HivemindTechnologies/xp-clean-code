---
name: xp-clean-code
description: Apply Extreme Programming (XP) and Clean Code discipline to software development. Use this skill whenever writing, reviewing, or extending production code — especially when the task involves implementing new behaviour, refactoring, adding tests, or defining acceptance criteria. Triggers on phrases like "implement feature", "add tests", "refactor", "write a spec", "acceptance criteria", "Given/When/Then", "TDD", "BDD", or any request to build something non-trivial. Composes cleanly with Karpathy-style behavioural guidelines: where those address how an agent should reason, this skill addresses how code should be built.
---

# XP + Clean Code Skill

This skill enforces Extreme Programming discipline and Clean Code principles when building software. It governs **how** to build, complementing any guidelines that govern **how to reason** (e.g. don't assume, minimal footprint, surgical changes).

The rules here are non-negotiable defaults. Deviate only when the user explicitly asks and states a reason.

---

## The Five Principles

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

## Interaction with Other Guidelines

This skill is additive. When used alongside Karpathy-style behavioural rules:

| Karpathy Principle | XP Reinforcement |
|---|---|
| Clarify before acting | Write the BDD scenario first — it forces shared understanding before any code exists |
| Minimal footprint | TDD enforces this mechanically — you cannot write code without a test that demands it |
| Surgical changes | Refactor-as-separate-phase keeps structural improvements out of feature commits |
| Goal-driven execution | Given/When/Then *is* the success criterion, made verifiable |

---

## Quick Reference

```
Before any code:    Write scenario (Given/When/Then)
Before production:  Write failing test (RED)
To pass the test:   Minimum code only (GREEN)
After green:        Refactor separately (CLEAN)
Commit unit:        One scenario, green + clean
Names:              Reveal intent, no abbreviations
Functions:          One thing, no surprise side effects
Comments:           Why, never what
```

For language- or framework-specific testing patterns, see `references/testing-patterns.md`.
For worked examples of BDD scenarios across common problem types, see `references/scenario-examples.md`.
