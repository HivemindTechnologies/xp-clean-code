# Spec template

Copy to `docs/specs/NNN-<slug>.md`. Keep every section; write "none" rather than deleting one, so
a reader can tell an empty section from a forgotten one. The header lines are machine-read by the
sync guard — keep their exact form.

```markdown
# Spec NNN · <Title — the story in five words>

**Status:** draft
**Milestone:** M1 — <milestone name from ROADMAP.md>
**Roadmap iterations:** 7, 8
**Feature files:** `tests/features/<name>.feature`
**Story:** <story id or title from DESIGN.md's backlog>
**Decisions relied on:** ADR-0003, ADR-0007

## 1. Purpose

One paragraph. Which story this increment delivers, which hypothesis in `DESIGN.md` it tests,
and what the customer will be able to observe when it ships. If this paragraph needs a second
one, the increment is two specs.

## 2. Scope fence

**In:** the scenarios in §3, and nothing that no scenario exercises.

**Out (this increment):**
- <a thing a reader might reasonably assume is included, and is not>
- <the obvious next step, named so nobody builds it early>
- <a configuration knob or abstraction that YAGNI forbids until a scenario demands it>

## 3. Scenarios

Verbatim mirror of the feature file(s) named above, from `building` onward. One `When` per
scenario. `Then` is an assertion a test can make. No class names, method names or SQL.

```gherkin
Feature: <Feature name>

  <One paragraph of intent, in the domain's language.>

  Scenario: <Behaviour, stated as an outcome>
    Given <a precondition that is true>
    When <the one action>
    Then <an observable outcome>
     And <a second observable outcome>

  Scenario: <Failure mode, stated as an outcome>
    Given <the precondition that makes it fail>
    When <the same one action>
    Then <the typed error the caller receives>

  Scenario: <Double application is a no-op>   # for every state transition
    Given <the state after one application>
    When <the same action again>
    Then <the state is unchanged>
     And <no duplicate event is emitted>
```

## 4. Design notes (minimum)

Only what the scenarios force. Typically:
- **Terms entering the ubiquitous language:** `<Name>` — one line each. Add them to the domain
  model table in the operative doc when they are built, not before.
- **Existing types consumed:** `<Name>` from `<module>`.
- **Effects at the boundary:** which I/O this increment touches and where it is injected.
- **Explicitly not designed here:** anything a reader might expect (a cache, a retry, a second
  adapter) that no scenario requires.

## 5. Exit evidence

What proves the increment did what §1 claims — beyond "tests green". Examples: a measured
value on real data, a log line observed in the deployed cycle, a manual check the customer
performs. If nothing beyond green tests is needed, say so.

## 6. Amendments

| Date | Scenario added / changed | Why it was not foreseen | Confirmed by |
|------|--------------------------|-------------------------|--------------|
| none | | | |

## 7. Reconciliation (as-built)

Filled when the spec moves to `reconciled`. Every deviation between §3/§4 as confirmed and what
shipped, with the reason. "None" is a legitimate entry and a rare one.
```

## Header field rules

| Field | Rule |
|---|---|
| `Status` | one of `draft` `confirmed` `building` `shipped` `reconciled` `withdrawn` `superseded` — lower case, nothing else on the line |
| `Feature files` | back-ticked paths relative to the repo root, comma-separated; may be empty in `draft` |
| `Roadmap iterations` | the iteration numbers this spec consumes; the roadmap links back |
| `Decisions relied on` | ADRs whose acceptance this spec assumes; an ADR still `proposed` blocks `confirmed` |
