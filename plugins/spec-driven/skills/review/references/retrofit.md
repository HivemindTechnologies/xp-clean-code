# Retrofit · Bringing an existing codebase under the spec-driven shape

Retrofit is the review skill's second entry mode. It has two parts, and they are not done in
one sitting:

1. **The retrofit review** — the ordinary review procedure over what exists, whose record
   carries a *sequenced retrofit plan*: one row per step below, each sized as one iteration.
   The review writes nothing but the record.
2. **The retrofit itself** — the steps below, landed one per commit in the order the customer
   sequenced, each reviewable on its own. Most of the documents do not exist yet and must be
   **derived from what is there** — tests, code, commit history, README — never written from
   intent. The cardinal rule: **a retrofitted document describes what is built. It never
   invents intent the code does not show.**

## Order of work

Each later step reads the earlier ones. One step is rarely one iteration; the plan splits it
(step 1 is one row **per test module**, hard-rule and risk-invariant modules first).

### 1. Scenarios from tests

For each test module without a feature file:

- Group tests by the behaviour they exercise (usually one module under test = one `Feature:`).
- For each test, derive a scenario: the title from the test name stated as an outcome; `Given`
  from the arrange section; `When` from the single act; `Then` from the assertions. If a test has
  two acts, it is two scenarios (and a finding: *bundled When*).
- Write the feature file. Bind the existing tests to it where the stack allows (pytest-bdd:
  `scenarios()` plus step functions that call the existing helpers); where it does not, leave
  the binding as a follow-up row and record the scenario anyway — the record is the point.
  **One module per iteration**, hard-rule and risk-invariant modules first: binding hundreds of
  tests in one commit is exactly the large step XP forbids.
- Behaviour the tests do not cover is **not** given a scenario. It is a finding under
  *behaviour without a scenario*, and writing the scenario is a future spec's job, under TDD.

### 2. Specs from feature files

Group feature files into the small releases they evidently were (the git log's clusters usually
show them). For each, write a spec born **`reconciled`**: purpose in one paragraph derived from
what the scenarios do; scope fence from what neighbouring code does *not* do; the Gherkin block
copied verbatim from the feature file; design notes naming the types that exist; exit evidence
as "retrofitted — see review YYYY-MM-DD"; Amendments "none (retrofit)"; Reconciliation stating
the retrofit date and the commit reviewed.

Run `spec-sync-guard.py`. Every retrofitted spec should pass immediately, because it was copied
from the file. A failure here is a defect in the retrofit, not in the code.

### 3. ADRs from code

Search for decisions living in code: named constants with rationale comments, sign conventions,
day-count functions, tolerances, thresholds, accepted schema versions, boundary contracts. Each
becomes an ADR born `accepted`, with `Confirmed by` = the commit that introduced it and its date —
or, where history is truncated or the decision predates the repository, the document and date
that first recorded it, marked *no commit* — `Context` from the comment or the issue it cites,
and `Consequences` naming the test that guards it — or a finding that none does.

Decisions found only in prose (a doc says "we decided X") with no code location get an ADR in
`proposed` state and a finding: the code does not show the decision was made.

### 4. Brief from the codebase

Write `docs/DESIGN.md` in **reconciled** form: the problem the code evidently solves, the
hypotheses it evidently tests (a calibration gate, a cross-check, a Go/No-Go rule are
hypotheses in code), non-goals the code enforces (a banned import, a disabled path), stories as
the shipped small releases, and the ubiquitous language from the type names that exist. Mark
anything you had to infer as *inferred* — the customer corrects it.

If a design document already exists, do not rewrite it. Reconcile it: a table of *documented vs
built*, and move history out of it into ADRs and review records.

### 5. Roadmap from history

The shipped milestones from the git log, each with the specs it produced and whether its exit
gate was ever measured. The **next** milestone is left empty for the customer — the retrofit
does not plan forward.

### 6. Operative context document

Bring the existing `CLAUDE.md` / `AGENTS.md` under `operative-context.md`'s budget: move every
dated sentence to the ADR, spec or review it belongs to, leaving a link; keep invariants and the
current status only; add the precedence rule and the docs-current guard for each checkable
claim.

### 7. The closing review

When the plan's rows have landed, run the review skill again in what should now be **sync**
mode. Its record closes the retrofit, and its follow-ups are the first real backlog. (The
*opening* record — the retrofit review that produced the plan — is already under
`docs/reviews/`.)

## What retrofit refuses

- To write a scenario for behaviour no test exercises (that is spec work, under TDD).
- To describe intent the code does not evidence, without marking it *inferred*.
- To change production code. A retrofit is documents and test bindings only; every finding
  about the code becomes a sequenced follow-up.
- To plan the next milestone. That is the customer's, with the scaffolding skill.
