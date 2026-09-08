---
description: Review the codebase against its documents — drift, unowned scenarios, unrecorded decisions, open questions, risks — and write a dated review record with sequenced follow-ups; add --retrofit to bootstrap the documents from an existing codebase
argument-hint: [--retrofit] [path] (optional; defaults to sync mode over the current repository)
---

You are running the **review** stage of the spec-driven plugin.

## Mode

`$ARGUMENTS`:
- contains `--retrofit` → retrofit mode: follow `references/retrofit.md` steps 1–6 first, then
  the ordinary procedure.
- otherwise → sync mode. If `docs/specs/` does not exist, say so and recommend `--retrofit`
  rather than guessing.

## Run

Load and apply the **review** skill exactly. Run the mechanical checks first — the project's
`tests/test_specs_are_in_sync.py` (or `python spec-sync-guard.py` from the spec skill's
references, copied into the repo root context), the docs-current guard, the type checker and
the suite — then walk every pattern in `references/drift-patterns.md` and record a finding or
"none found" for each.

Write `docs/reviews/YYYY-MM-DD-<slug>.md`. **Change no code.** Present the record and let the
customer sequence the follow-ups; only docs-only and test-only follow-ups may then be landed
without a spec.
