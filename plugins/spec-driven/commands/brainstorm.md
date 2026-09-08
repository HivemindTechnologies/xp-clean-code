---
description: Turn an idea into a design brief — problem, falsifiable hypotheses, non-goals, INVEST stories, spikes, language seed — with no architecture
argument-hint: <one-paragraph idea, or a path to notes> (optional; the skill will ask if empty)
---

You are running the **brainstorming** stage of the spec-driven plugin.

## Input

The user's idea: `$ARGUMENTS`

If empty, ask for the idea in one paragraph before doing anything else. If it is a path, read
the file and treat its contents as the idea.

## Run

Load and apply the **brainstorming** skill exactly. Produce `docs/DESIGN.md` in `draft` state
from `references/brief-template.md`, and one record under `docs/spikes/` per spike named.

Refuse to write architecture, a roadmap, an ADR, a spec or code. If the idea arrives as a
solution, extract the problem behind it and park the solution in a list you show at the end.

Finish by presenting the brief in full and asking the customer to confirm the stories and
hypotheses the product will bet on. Do not move the brief out of `draft` yourself.
