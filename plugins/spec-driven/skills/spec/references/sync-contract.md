# The Sync Contract · Spec ⇄ Feature File ⇄ Test ⇄ PR

This is the one rule set that makes spec-driven development compatible with XP: the spec is
**the acceptance-test set for one small release plus a scope fence**, not a requirements
document. Everything upstream of it (the brief, the design, the roadmap) is intent, and intent is
never licence to build. Everything downstream of it is the RED → GREEN → CLEAN loop the
xp-clean-code skill already governs.

Every skill in this plugin reads this file. The `spec` skill enforces it on the way in; the
`review` skill measures it after the fact; the pr-validation skill's Analysis 5 checks it on
every pull request.

---

## 1. Artefacts and where they live

| Artefact | Path | Owned by | Authoritative for |
|---|---|---|---|
| Design brief + vision | `docs/DESIGN.md` | brainstorming, extended by scaffolding | *why*, and future phases |
| Roadmap | `docs/ROADMAP.md` | scaffolding | the order of iterations and each milestone's exit gate |
| Decisions | `docs/decisions/NNNN-<slug>.md` + `docs/decisions/README.md` | scaffolding (any skill may propose) | anything that shapes every signature |
| Spikes | `docs/spikes/YYYY-MM-DD-<slug>.md` | brainstorming | a question, its time box, and the finding |
| Specs | `docs/specs/NNN-<slug>.md` | spec | the scope fence and authorised scenarios of one small release |
| Scenarios | `tests/features/*.feature` | spec (executable form) | what the code must do — the tests run from here |
| Review records | `docs/reviews/YYYY-MM-DD-<slug>.md` | review | measured drift, open questions, sequenced follow-ups |
| Operative context | `CLAUDE.md` (or `AGENTS.md`) | scaffolding writes, review polices | what holds on every commit, and the current iteration only |

**Precedence rule** (write it into the operative doc verbatim): *for anything being built now,
the operative doc, the current spec, and the accepted ADRs are authoritative. `DESIGN.md` is
authoritative for intent and future phases. If they conflict on a present-tense decision, the
present-tense documents win, and the conflict is fixed, not left standing.*

---

## 2. Spec lifecycle

```
draft ──▶ confirmed ──▶ building ──▶ shipped ──▶ reconciled
  │                                                   
  └──▶ withdrawn            any state ──▶ superseded by NNN
```

| State | Meaning | Who moves it | Where the Gherkin is authoritative |
|---|---|---|---|
| `draft` | Scenarios written in the spec; nothing else exists | author | **spec** |
| `confirmed` | The customer has accepted scope and scenarios | customer | **spec** |
| `building` | Scenarios copied verbatim into the named feature files; RED/GREEN/CLEAN under way | author, at the first RED commit | **feature file** |
| `shipped` | Every authorised scenario is green on the default branch | author | feature file |
| `reconciled` | The *Reconciliation* section records every as-built deviation; the spec now describes what exists | author, customer acknowledges | feature file |
| `withdrawn` / `superseded` | Never built, or replaced by a later spec | customer | — |

The state is one line in the spec header. It is the **only** status the spec carries — per-scenario
status is derived from the tests (present in the feature file and green means done), never
written by hand, because a hand-written checklist is the first thing to drift.

A retrofitted spec (see the `review` skill) is born `reconciled`: it describes what is already
built, and saying otherwise would be a lie about provenance.

---

## 3. Two copies, one checker

Scenarios exist twice on purpose:

1. **In the spec**, inside fenced ```` ```gherkin ```` blocks, so a human reviews the scope fence
   and the scenarios in one document, before any code exists.
2. **In the feature files** the spec header names, because that is what the test runner executes.

Duplication is acceptable exactly when it is mechanically checked. The check:

- For every spec in `building`, `shipped` or `reconciled`, every `Scenario` (or `Scenario Outline`
  with its `Examples`) in its Gherkin blocks exists in one of its named feature files with an
  identical title and identical steps, after whitespace normalisation.
- For every feature file named by a spec, every scenario in it appears in **exactly one** spec.
- A feature file no spec names is **unowned**. That is a review finding, not a test failure, so
  a retrofit can proceed one feature file at a time.

Direction of the fix when the check fails: copy in the direction the state dictates (§2). In
`draft`/`confirmed` the spec is right; from `building` onward the feature file is right, and the
spec's block is refreshed to match — then the *Amendments* log says why the behaviour moved.

The reference implementation is `references/spec-sync-guard.py` (Python, stdlib only). For other
stacks, reproduce the algorithm in §7 — it is a text comparison, so it needs no Gherkin parser.

---

## 4. The scope fence

Every spec names what is **in** and what is **out** for this small release. The scenarios *are*
the "in" list; the "out" list is written down so that a reader cannot mistake silence for
permission.

**The scope-creep rule.** A scenario discovered during the build that the spec does not
authorise **stops the work**. There are two permitted moves, and no third:

1. **Amend** — add the scenario to the spec's Gherkin block and an *Amendments* entry (date, the
   scenario, the reason it was not foreseen, who confirmed). The customer confirms before the RED
   test is written. The amendment lands in the same PR as the scenario it authorises.
2. **Defer** — write it to the roadmap backlog and carry on within the fence.

Silently adding a scenario, a helper "we'll need later", or a configuration knob no scenario
exercises is scope creep, and pr-validation reports it.

---

## 5. Scenario ⇄ test

- One scenario = one test (or one parameterised case). This is xp-clean-code Principle 2.
- Every scenario in an owned feature file is **bound** to a test: `pytest-bdd`'s
  `scenarios("x.feature")`, Cucumber glue, `cucumber-rs`, SpecFlow — whatever the stack uses.
- A test module that introduces new behaviour without a bound scenario is a finding, at repo scale
  in `review` and at diff scale in pr-validation Analysis 3.

---

## 6. PR ⇄ spec

- The PR body names the spec it builds: a line `Spec: NNN` or a link to `docs/specs/NNN-*.md`.
- pr-validation Analysis 5 checks: the spec exists and is in `confirmed` or `building`; every
  scenario added or changed in the diff is authorised by it (directly or by an amendment in the
  same PR); the mirror check of §3 passes on the PR head; and the production changes serve those
  scenarios and nothing else.
- A repository with a `docs/specs/` directory and a PR that names no spec is a finding. A
  repository without `docs/specs/` makes Analysis 5 not applicable — say so explicitly.

---

## 7. The mirror algorithm (stack-neutral)

```
for each spec file in docs/specs/:
    read header:  Status, Feature files (list of paths)
    skip unless Status in {building, shipped, reconciled}
    spec_scenarios = scenarios_in(all ```gherkin fenced blocks)
    file_scenarios = scenarios_in(each named feature file)
    compare as maps title → normalised step lines
      missing in file   → "spec authorises X; feature file lacks it"
      missing in spec   → "feature file has X; spec does not authorise it"
      steps differ      → unified diff of the two step lists

scenarios_in(text):
    split on lines starting with "Scenario:" or "Scenario Outline:"
    title = rest of that line, trimmed
    steps = following lines up to the next Scenario/Feature/Background/Rule/blank-then-keyword,
            each trimmed, with runs of internal whitespace collapsed; comments (#) and
            tag lines (@wip) dropped; Examples tables kept as steps
```

Owned feature files with a scenario in two specs, and feature files owned by no spec, are
reported separately (the first is an error, the second a finding).
