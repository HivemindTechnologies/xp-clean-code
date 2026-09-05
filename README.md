# xp-clean-code

Plugins that bring Extreme Programming and Clean Code discipline to AI-assisted development: one for how code gets built, one for validating that a pull request lives up to it, and one for deciding *what* gets built — a spec-driven workflow grounded in XP rather than in big design up front. Works with **Cursor** (Team Marketplace) and **Claude Code**.

-----

## About Hivemind Technologies

At [Hivemind Technologies](https://hivemindtechnologies.com), we build scalabe data platforms and machine learning systems for finance, energy and mobility sectors. Our engineering culture is rooted in the belief that software quality is not a trade-off against delivery speed — it is what makes sustained delivery possible. We practice test-first development, design through small increments, and treat code clarity as a first-class concern. This skill is a direct expression of those values, made available for AI coding agents.

-----

## What this skill does

AI coding agents are remarkably capable, but left unconstrained they tend toward the same failure modes as a talented developer working without discipline: skipping tests, over-engineering, and conflating building with cleaning. This skill gives Claude Code a concrete methodology to follow — one that engineers have used to ship reliable software for decades.

It encodes eight principles:

1. **Test First** — the RED → GREEN → CLEAN cycle, enforced strictly. No production code without a failing test.
1. **BDD Scenarios as Success Criteria** — Given/When/Then scenarios are written before tests, making intent explicit and verifiable before a line of implementation exists.
1. **One Step at a Time** — one failing test at a time, one scenario per commit. No speculative work, no big-bang implementations.
1. **Clean Code Invariants** — names that reveal intent, functions that do one thing, comments that explain why rather than what, no surprise side effects.
1. **Refactor as a Separate Phase** — structural improvements are always made after green, never mixed with feature work.
1. **Domain-Driven Design** — code speaks the language of the domain. Bounded contexts enforce explicit boundaries. Value objects replace primitives. Domain events model facts as immutable values. Repositories abstract persistence from domain logic.
1. **Functional Core** — pure functions as the default, referential transparency as the goal. Side effects are pushed to the edges. Errors are modelled as `Either`/`Result` types, not exceptions. Absent values are `Option`, not null. State changes return new values; nothing mutates in place. Where the language supports it, function composition (including monadic chains) builds complex behaviour from simple, testable parts.
1. **Total Types and Explicit Outcomes** — the decision rule for *which* type carries an outcome. `Option` only where absence needs no explanation; `Either`/`Result` where the caller may need to distinguish, report, recover from, or test the failure. Null never enters the typed core — nullable values are normalised at the boundary. Optionals that depend on each other become a sum type, so invalid combinations cannot be constructed. Closed types are eliminated exhaustively, with no default branch and no forced unwrap. Exceptions keep a defined role: broken invariants and defects, not outcomes.

-----

## Installation

### Cursor (Team Marketplace)

Requires a Cursor Teams or Enterprise plan and admin access.

1. Push these changes so `main` includes `.cursor-plugin/marketplace.json`.
2. Open **Dashboard → Settings → Plugins**.
3. Under **Team Marketplaces**, choose **Import Marketplace** / **Import from Repo**.
4. Paste: `https://github.com/HivemindTechnologies/xp-clean-code`
5. Confirm the three plugins (`xp-clean-code`, `pr-validation`, `spec-driven`) are detected, then save.

For private repos, install the Cursor GitHub App on the org/repo first (**Dashboard → Integrations**). Enable **Auto Refresh** if you want pushes to re-index the marketplace.

**Personal / local (no Team Marketplace):** symlink skills into `~/.cursor/skills/`:

```bash
mkdir -p ~/.cursor/skills
ln -s "$(pwd)/plugins/xp-clean-code/skills/xp-clean-code" ~/.cursor/skills/xp-clean-code
ln -s "$(pwd)/plugins/pr-validation/skills/pr-validation" ~/.cursor/skills/pr-validation
for s in brainstorming scaffolding spec review; do
  ln -s "$(pwd)/plugins/spec-driven/skills/$s" ~/.cursor/skills/$s
done
```

Or load a plugin from `~/.cursor/plugins/local/` (symlink a plugin directory that contains `.cursor-plugin/plugin.json`).

### Claude Code

**As a plugin (recommended — applies across all projects):**

Add the repo as a plugin source in `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "xp-clean-code": {
      "source": {
        "source": "github",
        "repo": "HivemindTechnologies/xp-clean-code"
      }
    }
  }
}
```

Then open Claude Code and run `/plugin` to browse and install.

**Per-project (append to an existing CLAUDE.md):**

```bash
echo "" >> CLAUDE.md
curl https://raw.githubusercontent.com/HivemindTechnologies/xp-clean-code/main/plugins/xp-clean-code/skills/xp-clean-code/SKILL.md >> CLAUDE.md
```

-----

## What’s included

```
.cursor-plugin/
└── marketplace.json                      # Cursor Team Marketplace index
.claude-plugin/
└── marketplace.json                      # Claude Code marketplace index

plugins/xp-clean-code/                    # how to build
├── .cursor-plugin/
│   └── plugin.json                       # Cursor plugin manifest
├── .claude-plugin/
│   └── plugin.json                       # Claude Code plugin manifest
└── skills/
    └── xp-clean-code/
        ├── SKILL.md                      # Core principles — loaded on demand
        └── references/
            ├── testing-patterns.md       # Framework examples: Scala, Java, Python, PySpark,
            │                             #   TypeScript, Rust, Gherkin
            ├── total-types.md            # Option/Either/ADT idioms per language; result-type
            │                             #   conformance properties
            └── scenario-examples.md      # Worked BDD scenarios across common problem types

plugins/pr-validation/                    # verifying what was built
├── .cursor-plugin/
│   └── plugin.json
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   └── pr-validate.md                    # /pr-validate — runs the check against a GitHub PR
└── skills/
    └── pr-validation/
        ├── SKILL.md                      # The four analyses — loaded on demand
        └── references/
            ├── purity-checklist.md       # Impurity signals + absence-vs-failure signals:
            │                             #   Python, Scala, Java, TypeScript, Rust
            ├── gap-patterns.md           # Eleven coverage gap patterns, with before/after scenarios
            └── claim-verification.md     # Mutation catalogue for the removal check

plugins/spec-driven/                      # deciding what to build
├── .cursor-plugin/
│   └── plugin.json
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── brainstorm.md                     # /brainstorm  — idea → design brief
│   ├── scaffold.md                       # /scaffold    — brief → roadmap, ADRs, operative doc, skeleton
│   ├── spec.md                           # /spec        — one fenced increment, drafted → reconciled
│   └── reconcile.md                      # /reconcile   — review docs against code; --retrofit to bootstrap
└── skills/
    ├── brainstorming/
    │   ├── SKILL.md
    │   └── references/
    │       ├── brief-template.md         # DESIGN.md + spike record templates
    │       └── story-checklist.md        # INVEST, hypothesis checklist, "you are designing" smells
    ├── scaffolding/
    │   ├── SKILL.md
    │   └── references/
    │       ├── roadmap-template.md       # milestones with evidence gates; one scenario per row
    │       ├── adr-template.md           # Nygard ADRs + the pin-gate index
    │       └── operative-context.md      # CLAUDE.md / AGENTS.md budget and the docs-current guard
    ├── spec/
    │   ├── SKILL.md
    │   └── references/
    │       ├── sync-contract.md          # THE rule set: lifecycle, scope fence, spec ⇄ feature mirror
    │       ├── spec-template.md
    │       └── spec-sync-guard.py        # stdlib test: spec Gherkin == feature files, both ways
    └── review/
        ├── SKILL.md
        └── references/
            ├── drift-patterns.md         # what to measure, per document pair
            └── retrofit.md               # bringing an existing codebase under the shape
```

The reference files are loaded on demand. `SKILL.md` stays lean in context; the detail is there when the agent needs it.

### The pr-validation plugin

Where `xp-clean-code` governs how to build, `pr-validation` checks that what was built holds up. Run `/pr-validate` on a PR — or ask Claude to review one — and it produces a structured report across four analyses:

1. **Purity** — every changed function classified as Pure, Impure–boundary, or Impure–violation.
1. **Idempotency** — every state transition checked for `f(f(x)) = f(x)`, and for a double-application scenario.
1. **BDD coverage** — a coverage matrix mapping changed functions to scenarios: happy path, each failure mode, each branch, each boundary.
1. **Protection claims** — for every assertion the PR body makes about what a check protects against, the mapped test is run with that protection removed. If it still passes, the claim is unsubstantiated: the guard is untested, unreachable, or the test passes for an unrelated reason. A protection claim nobody can break is a promise the suite does not keep.

### The spec-driven plugin

`xp-clean-code` says how to build and `pr-validation` checks what was built. Neither says what to
build. `spec-driven` does, in four stages that map one-to-one onto XP practices rather than onto a
requirements → design → tasks pipeline:

| Stage | XP practice | Produces | Who decides |
|---|---|---|---|
| **brainstorming** (`/brainstorm`) | exploration, story writing, spikes | `docs/DESIGN.md`: problem, falsifiable hypotheses, non-goals, INVEST stories, spikes, a language seed — and no architecture | the customer picks the stories and the bets |
| **scaffolding** (`/scaffold`) | release planning, walking skeleton | `docs/ROADMAP.md` (one scenario per iteration, evidence-based exit gates), Nygard ADRs with a pin gate, a lean `CLAUDE.md`, Iteration 0 | the customer accepts each ADR |
| **spec** (`/spec`) | iteration planning, acceptance tests | `docs/specs/NNN-*.md`: a scope fence plus the Given/When/Then scenarios that *are* the acceptance tests for one small release | the customer confirms scope; the agent builds under xp-clean-code |
| **review** (`/reconcile`) | retrospective | `docs/reviews/DATE-*.md`: measured drift between documents and code, open questions, risks, follow-ups sized as iterations — and no code changed | the customer sequences the follow-ups |

The idea that makes the two traditions compatible: **the spec is the acceptance-test set for one
small release plus a scope fence, not a requirements document.** Everything upstream of it is
intent, and the precedence rule says intent is never licence to build. Scenarios live twice — in
the spec so a human can review scope and behaviour in one document, and in the feature file so
the runner can execute them — and `spec-sync-guard.py` holds the two copies equal, so duplication
is safe exactly because it is checked. A scenario discovered mid-build that the spec does not
authorise stops the work: amend (the customer confirms first) or defer, never sneak in.
`pr-validation`'s Analysis 5 checks the same fence on every pull request.

`/reconcile --retrofit` bootstraps the documents from an existing codebase — scenarios from tests,
specs born `reconciled`, ADRs from the decisions already living in code — without inventing intent
the code does not show.

-----

## Works well with

These skills focus on *how to build*, *how to check it*, and *what to build*. If you also want to constrain *how to reason* — surface assumptions, avoid over-complication, make surgical changes — it pairs naturally with [andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills). The two address different failure modes and do not overlap.

-----

## License

MIT