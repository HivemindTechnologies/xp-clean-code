# Design brief template (`docs/DESIGN.md`, draft state)

The brief is the *why*. It is allowed to run ahead of the code — that is its job — and the
precedence rule keeps it from becoming licence: anything here that is not in a confirmed spec
is intent, not work. Keep the brief in the domain's language; keep architecture out of it
until the scaffolding skill adds it.

```markdown
# <Product name> — Design Brief (DRAFT v0.1)

**Status:** draft — nothing here is confirmed for build. See the precedence rule.
**Customer:** <the person who decides>
**Precedence:** for anything being built now, `CLAUDE.md`, the current spec and the accepted
ADRs are authoritative; this document is authoritative for intent and future phases.

## 1. The problem

Who has it, what it costs them today, and why now. Three to six sentences. No solution yet.

## 2. Hypotheses

Each hypothesis states what we believe, **what observation would falsify it**, and where that
observation will come from. A hypothesis that cannot fail is a slogan.

| # | We believe that… | It is false if… | Evidence source | Tested by |
|---|------------------|-----------------|-----------------|-----------|
| H1 | | | | spike S1 / milestone M1 |
| H2 | | | | |

## 3. Non-goals

What this product will not do, stated so a later reader cannot mistake silence for permission.
Include the things that are tempting.

## 4. Stories

XP user stories, INVEST-shaped: Independent, Negotiable, Valuable, Estimable, Small, Testable.
A story is a *promise of a conversation*, not a specification — the spec skill will turn one
into scenarios when its turn comes.

| Id | As a… | I want… | so that… | Done when (one observable outcome) | Tests | Needs spike |
|----|-------|---------|----------|-------------------------------------|-------|-------------|
| U1 | | | | | H1 | S1 |
| U2 | | | | | H1 | — |

Order is by the customer's value, not by technical dependency. Dependencies are a scaffolding
concern.

## 5. Spikes

A spike answers **one question** whose answer changes which stories are possible or how they
are shaped. It is time-boxed, on a throwaway branch, and its only permitted outputs are a
decision record (ADR) or a scenario. Spike code is never merged.

| Id | Question | Time box | Ends when | Blocks |
|----|----------|----------|-----------|--------|
| S1 | | 1 day | an ADR proposing X or Y | U1, U3 |

## 6. Ubiquitous language (seed)

Ten to twenty terms the domain expert actually uses, one line each. These become type names
later; here they are just words with agreed meanings.

| Term | Meaning | Not to be confused with |
|------|---------|-------------------------|
| | | |

## 7. Constraints

Only genuine constraints: a regulator, an existing system the product must read from, a
budget, a deadline, a banned dependency. A preference is not a constraint.

## 8. Open questions

Things nobody can answer yet, each with who could answer it and by when.
```

## Spike record template (`docs/spikes/YYYY-MM-DD-<slug>.md`)

```markdown
# Spike S1 · <the question, as a question>

**Time box:** 1 day  **Started:** YYYY-MM-DD  **Closed:** YYYY-MM-DD
**Branch:** spike/<slug> (deleted after close)

## Question
One sentence.

## What was tried
Bullets. Enough that nobody repeats it.

## Finding
What was learned, with the measurement or the observation that supports it.

## Output
- ADR-000N proposed: <title>   — or —
- Scenario added to story U1's sketch: <title>
- No output: the question was the wrong question, because …

## Not carried forward
The code. State this explicitly so nobody goes looking for it.
```
