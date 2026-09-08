---
description: Turn a confirmed brief into a roadmap of one-scenario iterations, ADRs with a pin gate, the lean operative context doc, and a walking skeleton
argument-hint: (none; reads docs/DESIGN.md)
---

You are running the **scaffolding** stage of the spec-driven plugin.

## Preconditions — check, do not assume

- `docs/DESIGN.md` exists and its status shows the customer confirmed it.
- Every blocking spike in it has a closed record under `docs/spikes/`.
- No production code exists — or a retrofit review has already run.

If any fails, say which and stop.

## Run

Load and apply the **scaffolding** skill exactly, in order: first small release and its
evidence-based exit gate → ADRs in `proposed` state with the pin-gate index → `docs/ROADMAP.md`
→ the domain table → `CLAUDE.md` (or `AGENTS.md`) within budget with its docs-current guard →
Iteration 0 walking skeleton, including `tests/test_specs_are_in_sync.py` copied from the spec
skill's `references/spec-sync-guard.py`.

Present the ADRs to the customer for acceptance before writing any iteration they block. Land
Iteration 0, confirm CI green, and stop: spec 001 is the next conversation.
