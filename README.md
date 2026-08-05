# xp-clean-code

Claude Code plugins that bring Extreme Programming and Clean Code discipline to AI-assisted development: one for how code gets built, one for validating that a pull request lives up to it.

-----

## About Hivemind Technologies

At [Hivemind Technologies](https://hivemindtechnologies.com), we build scalabe data platforms and machine learning systems for finance, energy and mobility sectors. Our engineering culture is rooted in the belief that software quality is not a trade-off against delivery speed — it is what makes sustained delivery possible. We practice test-first development, design through small increments, and treat code clarity as a first-class concern. This skill is a direct expression of those values, made available for AI coding agents.

-----

## What this skill does

AI coding agents are remarkably capable, but left unconstrained they tend toward the same failure modes as a talented developer working without discipline: skipping tests, over-engineering, and conflating building with cleaning. This skill gives Claude Code a concrete methodology to follow — one that engineers have used to ship reliable software for decades.

It encodes seven principles:

1. **Test First** — the RED → GREEN → CLEAN cycle, enforced strictly. No production code without a failing test.
1. **BDD Scenarios as Success Criteria** — Given/When/Then scenarios are written before tests, making intent explicit and verifiable before a line of implementation exists.
1. **One Step at a Time** — one failing test at a time, one scenario per commit. No speculative work, no big-bang implementations.
1. **Clean Code Invariants** — names that reveal intent, functions that do one thing, comments that explain why rather than what, no surprise side effects.
1. **Refactor as a Separate Phase** — structural improvements are always made after green, never mixed with feature work.
1. **Domain-Driven Design** — code speaks the language of the domain. Bounded contexts enforce explicit boundaries. Value objects replace primitives. Domain events model facts as immutable values. Repositories abstract persistence from domain logic.
1. **Functional Core** — pure functions as the default, referential transparency as the goal. Side effects are pushed to the edges. Errors are modelled as `Either`/`Result` types, not exceptions. Absent values are `Option`, not null. State changes return new values; nothing mutates in place. Where the language supports it, function composition (including monadic chains) builds complex behaviour from simple, testable parts.

-----

## Installation

**As a Claude Code plugin (recommended — applies across all projects):**

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
plugins/xp-clean-code/                    # how to build
├── .claude-plugin/
│   └── plugin.json                       # Plugin manifest
└── skills/
    └── xp-clean-code/
        ├── SKILL.md                      # Core principles — loaded by Claude Code
        └── references/
            ├── testing-patterns.md       # Framework examples: Scala, Java, Python, PySpark,
            │                             #   TypeScript, Rust, Gherkin
            └── scenario-examples.md      # Worked BDD scenarios across common problem types

plugins/pr-validation/                    # verifying what was built
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   └── pr-validate.md                    # /pr-validate — runs the check against a GitHub PR
└── skills/
    └── pr-validation/
        ├── SKILL.md                      # The four analyses — loaded by Claude Code
        └── references/
            ├── purity-checklist.md       # Impurity signals: Python, Scala, Java, TypeScript, Rust
            ├── gap-patterns.md           # Ten coverage gap patterns, with before/after scenarios
            └── claim-verification.md     # Mutation catalogue for the removal check
```

The reference files are loaded on demand. `SKILL.md` stays lean in context; the detail is there when Claude needs it.

### The pr-validation plugin

Where `xp-clean-code` governs how to build, `pr-validation` checks that what was built holds up. Run `/pr-validate` on a PR — or ask Claude to review one — and it produces a structured report across four analyses:

1. **Purity** — every changed function classified as Pure, Impure–boundary, or Impure–violation.
1. **Idempotency** — every state transition checked for `f(f(x)) = f(x)`, and for a double-application scenario.
1. **BDD coverage** — a coverage matrix mapping changed functions to scenarios: happy path, each failure mode, each branch, each boundary.
1. **Protection claims** — for every assertion the PR body makes about what a check protects against, the mapped test is run with that protection removed. If it still passes, the claim is unsubstantiated: the guard is untested, unreachable, or the test passes for an unrelated reason. A protection claim nobody can break is a promise the suite does not keep.

-----

## Works well with

This skill focuses on *how to build*. If you also want to constrain *how to reason* — surface assumptions, avoid over-complication, make surgical changes — it pairs naturally with [andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills). The two address different failure modes and do not overlap.

-----

## License

MIT