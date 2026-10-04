---
name: prose-style
description: >-
  Write English prose that people read (documentation, READMEs, ADRs, specs, commit messages,
  pull request descriptions, issues, code comments, error messages, UI text, reports) in a
  clear, concrete, calibrated house style: active voice, needless words cut, claims matched to
  evidence, none of the habits that mark text as machine-written, British spelling, Title Case
  headings, no contractions. Use whenever you write or edit sentences for a human reader. To
  audit or rewrite text that already exists, use the revise skill. Do not use for code,
  identifiers, logs, or quoted material.
---

# Prose Style

This skill governs **how text reads**. The xp-clean-code skill governs how code gets built.
Both work from the same idea: the reader's attention is the scarcest resource, and every word,
like every line of code, has to earn its place.

The rules draw on four sources: Strunk's *The Elements of Style* (1918), Orwell's "Politics and
the English Language" (1946), Pinker's *The Sense of Style* (2014), and Gopen and Swan's "The
Science of Scientific Writing" (1990). To these we add the habits that recur in text written by
language models, and the house conventions of Hivemind Technologies. Every rule has a bad and a
good example, with the reasoning, in `references/rules.md`. Read that file the first time
you write a substantial document in a session. `references/word-list.md` lists plain-English
swaps, inflated vocabulary, and commonly confused words.

## Scope

Apply the rules to any text written for a person to read: files, commit messages, pull request
and issue text, code comments, docstrings, error messages, and UI copy. In chat replies, apply
groups A to D. The house conventions (group E) are for artefacts that outlive the conversation.

Leave alone anything that is not your prose: code, identifiers, command output, quotations,
names, and text you were asked to reproduce verbatim.

## The Rules

### A. Reader and Purpose

- **R1 Name the reader.** Decide who reads this and what they already know. Define a term the
  first time you use it, or do not use it. Do not lean on context only you hold.
- **R2 Lead with the point.** Put the answer, decision, or change in the first sentence. Give the
  background afterwards, for those who want it.

### B. Sentences

- **R3 Active voice.** When the actor is known and matters, make it the subject: "the guard
  rejects the request", not "the request is rejected".
- **R4 Concrete words.** Name the thing. Avoid category words like "aspects", "factors",
  "various", and "considerations" when you can say which ones.
- **R5 Cut needless words.** "In order to" becomes "to", "due to the fact that" becomes
  "because", and "is able to" becomes "can". Drop intensifiers such as "very", "really",
  "simply", "just", and "basically".
- **R6 Positive form.** Say what is, not what is not: "forgot", not "did not remember". Do
  not stage contrasts for effect ("not just X, but Y"; "this is not a bug, it is a feature").
- **R7 Plain words.** "Use", not "leverage" or "utilise". "Method", not "methodology".
  "Feature", not "functionality".
- **R8 No dead metaphors.** Cut "paradigm shift", "game-changer", "deep dive", "cutting-edge",
  "seamless", and "unlock". If the plain statement sounds thin, the claim is thin.
- **R9 Keep related words together.** Keep the subject near its verb and the modifier next to
  what it modifies. Move a long parenthetical into its own sentence.
- **R10 Stress position.** End the sentence on the new or important information. Put familiar
  context at the start.
- **R11 Sentence length.** Split sentences longer than about 30 words. Mix long and short
  sentences within a paragraph.
- **R12 Parallel form.** Give items in a series the same grammatical shape.

### C. Paragraphs and Structure

- **R13 One topic per paragraph,** opened by a sentence that states it.
- **R14 Prose for reasoning, lists for items.** Connected argument belongs in paragraphs. Use
  bullets only for items that are truly separate. Do not force ideas into groups of three.
- **R15 No summary closers.** Do not end a paragraph or document by restating what it just
  said ("In short…", "Overall…", "This ensures that…").
- **R16 No stock transitions.** Do not open sentences with "Additionally", "Furthermore",
  "Moreover", "In addition", "It is worth noting that", or "Importantly". If the link
  between two sentences is not clear, rewrite the sentences.
- **R17 Vary openings.** Do not start consecutive sentences with the same word.

### D. Claims and Terms

- **R18 Calibrate claims.** Match the verb to the evidence: "shows" needs a demonstration,
  "suggests" is enough for a hint. Do not write "always", "never", "guarantees", or "ensures"
  unless that is literally true.
- **R19 No invented facts.** Never invent numbers, citations, links, quotations, or behaviour.
  If something is unknown, say so, or leave a visible `TODO`.
- **R20 One term per concept.** Once you name a thing, keep using that name. Switching between
  synonyms makes the reader wonder whether there are two things.
- **R21 No padding.** No throat-clearing ("Let me explain…", "It is important to understand
  that…"), no praise of the question, no offers to help further, and no stacked hedges ("may
  potentially", "could possibly").

### E. House Conventions

- **H1 British spelling:** behaviour, colour, organise, recognise, modelling, centre,
  catalogue. Practice and licence are nouns; practise and license are verbs. "Program" is
  software; "programme" is a plan.
- **H2 Title Case headings.** Capitalise the principal words. Keep articles, coordinating
  conjunctions, and prepositions of four letters or fewer in lower case, unless they come
  first or last. Code identifiers keep their own case: "The `prose-style` Plugin". Title Case
  applies to document headings, not to commit subjects, list items, or table cells.
- **H3 No contractions:** "it is", "does not", "cannot". Quoted text and UI strings that must
  match a product's voice are exempt.
- **H4 Em dashes, very sparingly.** Use a comma, colon, semicolon, parentheses, or a full stop
  instead. An em dash is allowed for one deliberate interruption, at most once in a paragraph
  and never in two paragraphs running. Never use a dash to join a bold label to its text in a
  list; use a colon.
- **H5 Serial comma** before the last item in a list of three or more: "Claude Code, Cursor,
  and Codex".

## Text Types

| Text | What changes |
|---|---|
| Commit subject | Imperative mood, at most 72 characters, no full stop, sentence case. R2 applies; R10 and H2 do not. |
| Commit or PR body | Say why first, then what. Wrap prose; use bullets only for separate changes. |
| ADR, spec, design brief | R18 and R19 are critical: a decision record that overstates its evidence misleads every later reader. |
| Error message | Say what happened, why, and what the reader can do, in that order. No apology, no blame. |
| Code comment | Explain why, not what (see xp-clean-code). Short sentences; fragments are fine. |
| README | R1 and R2 come first: who is this for, and what does it do, in the first paragraph. |

## Escape Hatch

> "Break any of these rules sooner than say anything outright barbarous."
> George Orwell, 1946, rule 6.

The rules serve clarity; they are not the goal. If following one makes a sentence worse, break
it, and be ready to say which rule you broke and why.

## Before You Hand Text Over

Read the draft once as its intended reader would. Then check:

1. Does the first sentence carry the point (R2)?
2. Is any word or sentence doing no work (R5, R15, R21)?
3. Is every claim backed by something on the page (R18, R19)?
4. Does it look machine-written: stock transitions, forced lists of three, staged contrasts,
   dashes everywhere (R6, R14, R16, H4)?
5. Do spelling, headings, and contractions follow the house conventions (H1 to H3)?

For a second pass over existing text, with a rule-by-rule audit and edits in place, use the
**revise** skill (`/revise` in Claude Code, `$revise` in Codex).
