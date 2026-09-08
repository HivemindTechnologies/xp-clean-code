---
description: Draft, confirm, build and reconcile one spec — a fenced small release with its Given/When/Then scenarios — under XP discipline
argument-hint: <story id | roadmap iteration(s) | spec id to continue> (optional; defaults to the spec in `building`, else the next roadmap iteration)
---

You are running the **spec** stage of the spec-driven plugin.

## Target

`$ARGUMENTS` names a story, roadmap iteration(s), or an existing spec id.

- Empty → continue the spec whose `Status` is `building`; if none, draft the spec for the next
  ⏳ roadmap iteration.
- An existing spec id → resume from its current state (draft → present for confirmation;
  confirmed → open the build; building → next unbuilt scenario; shipped → reconcile).

## Run

Load and apply the **spec** skill exactly, with `references/sync-contract.md` as the rule set.
Before drafting, check the pin gate in `docs/decisions/README.md`: an ADR the spec relies on
that is still `proposed` blocks confirmation.

During the build, run each scenario through the xp-clean-code skill (RED → GREEN → CLEAN, one
commit per scenario), keep `tests/test_specs_are_in_sync.py` green, and stop on any behaviour the
spec does not authorise — amend (customer confirms first) or defer to the roadmap backlog.

Put `Spec: NNN` in every PR body so pr-validation's Analysis 5 can check the diff against it.
Never move a spec to `confirmed` yourself.
