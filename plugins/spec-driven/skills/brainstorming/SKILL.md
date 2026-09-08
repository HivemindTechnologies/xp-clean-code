---
name: brainstorming
description: >-
  Turn an idea into a design brief: the problem, falsifiable hypotheses, non-goals, INVEST user
  stories, the spikes needed to de-risk them, and a seed of the ubiquitous language — with no
  architecture, no file tree and no technology choices. Use this at the very start of a product
  or a major new capability: "brainstorm", "I have an idea for", "sketch out a product", "what
  should this do", "design brief", "scope this", "hypotheses", "user stories", "what to spike",
  "MVP scope", "non-goals", "is this worth building". This is XP's exploration phase, made
  explicit. It is the first stage of the spec-driven plugin; scaffolding follows once the
  customer has confirmed the brief.
---

# Brainstorming · From idea to a falsifiable brief

Brainstorming produces the **why**: a design brief with hypotheses that can fail, stories the
customer values, and the spikes that must be run before anything can be planned. It produces no
architecture. The strongest temptation at this stage is to start designing — to name the
modules, choose the database, sketch the pipeline — and every one of those moves is a decision
made before the evidence that should drive it exists.

XP calls this exploration: write stories, find the metaphor, spike what you do not understand.
The brief is XP's story cards, kept in one file so the agent can read them.

The template is `references/brief-template.md`; the checklists are
`references/story-checklist.md`. The rules here are non-negotiable defaults.

---

## Procedure

### Step 1 — Frame the problem, without a solution

Ask, and write down: **who** has the problem, **what it costs them** today, **why now**. Three to
six sentences. If the user's opening message already contains a solution ("I want to build a
Kafka pipeline that…"), extract the problem behind it and write that; the solution goes to a
parking list you show them at the end.

### Step 2 — Hypotheses, with their falsifiers

For each thing the product is betting on, write: *we believe that…* / *it is false if…* /
*the evidence would come from…*. Write the falsifier **before** the belief is polished. A row
without a falsifier is not a hypothesis; move it to non-goals or constraints.

Push for at least one hypothesis about the **edge or value** (why this works at all) and one
about the **user** (why anyone would use it). Products fail on both.

### Step 3 — Non-goals

List what the product will not do, including the tempting things. A reader must not be able to
mistake silence for permission. This list is the ancestor of every spec's *Out* list.

### Step 4 — Stories

Write XP user stories in INVEST form (see the checklist). Each has one *done when* that is an
observable outcome. Stories are promises of a conversation, not designs: an "I want" that names
a table, an endpoint or a class has skipped ahead. Order them by the **customer's value**, not by
technical dependency — dependency ordering is scaffolding's job.

Aim for 5–15 stories. Fewer and the product is a feature; more and the brief has become a
backlog for a year.

### Step 5 — Spikes

For every story whose size you cannot estimate, or whose feasibility rests on an unknown, name a
spike: **one question**, a time box, what output ends it, which stories it blocks. A spike's
only permitted outputs are a proposed ADR or a scenario sketch. Spike code is thrown away and the
record says so.

### Step 6 — Ubiquitous-language seed

Ten to twenty terms the domain expert actually uses, each with a one-line meaning and, where
useful, what it is *not*. These are words, not types. The scaffolding skill will promote some of
them to value objects when a scenario first consumes them.

### Step 7 — Constraints and open questions

Constraints are genuine externalities: a regulator, a system that must be read from, a banned
dependency, a budget. Preferences are not constraints. Open questions each name who could answer
them and by when.

### Step 8 — Hand to the customer

Write `docs/DESIGN.md` from the template with `Status: draft`, and the spike records under
`docs/spikes/`. Present the brief in full. The customer picks the stories and the hypotheses the
product will bet on, and confirms. The agent proposes; the customer decides. Only after
confirmation does scaffolding begin.

---

## Hard rules

- **No architecture.** No file tree, no module or class names beyond the language seed, no
  technology choice that is not a genuine constraint, no sequencing beyond value order.
- **Every hypothesis has a falsifier and an evidence source.** Otherwise it is not in the table.
- **Every story has exactly one *done when*.** Two means two stories.
- **Spikes answer one question each and produce no merged code.**
- **The brief runs ahead of the code on purpose,** and the precedence rule (written into it)
  says so: nothing in the brief is licence to build.
- **The customer confirms.** The skill does not move the brief out of `draft`.

## What this skill refuses

- To write `ROADMAP.md`, an ADR, a spec, or any code. Those belong to later stages and to the
  evidence spikes produce.
- To accept "make it scalable / flexible / robust" as a hypothesis, a story or a constraint.
- To carry a story whose *done when* cannot be observed.

## Interaction with the other skills

| Skill | Receives from brainstorming |
|---|---|
| scaffolding | the confirmed brief: stories, hypotheses, closed spikes, the language seed, constraints |
| spec | a story (via the roadmap) and the hypothesis it tests |
| review | the brief, to measure what the code actually does against what was believed |

## Quick reference

```
□ Problem framed: who, cost today, why now — no solution
□ Each hypothesis: belief / falsifier / evidence source / tested by
□ Non-goals include the tempting things
□ 5–15 INVEST stories, one "done when" each, ordered by customer value
□ A spike for every unknown; one question, time box, output = ADR or scenario
□ 10–20 language terms, words not types
□ Constraints are externalities; open questions have an owner
□ DESIGN.md written in draft; customer confirms; nothing else exists yet
```
