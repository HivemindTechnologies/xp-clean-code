---
name: revise
description: >-
  Audit existing prose against the prose-style rules and revise it in place: a rule-by-rule
  scorecard with verbatim excerpts, a confirmation, edits limited to the flagged passages, a
  re-audit, and a diff. Use when asked to revise, review, edit, tighten, copyedit, proofread,
  de-slop, or "fix the writing" of a file, a README, a draft, a commit message, or a pull request
  description. For writing new text, the prose-style skill applies on its own; this skill is the
  second pass over text that already exists.
---

# Revise

This is the second pass. The prose-style skill shapes text while it is being written; this skill
audits text that already exists, then rewrites only what the audit flags. The rule set,
identifiers, and examples are those of the **prose-style** skill: load it, and read its
`references/rules.md`, before auditing. The hard invariants for the rewrite are in
`references/revision-contract.md`; read that before the first edit.

## Targets

| Input | Result |
|---|---|
| One or more file paths | Audit each file; on confirmation, edit it in place and show the diff |
| No path, text pasted in the conversation | Audit the text; return the revised text in the reply |
| No path, no pasted text | Use the draft commit message or PR description under discussion. If there is none, ask what to revise |

The skill reads prose in Markdown, plain text, reStructuredText, and LaTeX. In other files, it
reads only comments and docstrings, and it never changes code.

## Workflow

### 1. Read and Map

Read the whole target. Mark the regions you will not audit or change: frontmatter, code fences,
inline code, URLs and link targets, HTML, quotations, command output, and generated sections.
Note the document's type (see "Text Types" in prose-style), because it changes which rules apply.

### 2. Audit

Check every rule, R1 to R21 and H1 to H5, against the prose regions. For each violation, record:

- the rule identifier,
- the line number,
- a **verbatim** excerpt of at most about 15 words, copied exactly from the source,
- a one-line suggested fix.

The audit is a judgement made by the model, so keep it honest:

- **Quote, do not paraphrase.** Before you report a finding, check that its excerpt appears in
  the source character for character. Drop any finding whose excerpt does not.
- **Count occurrences, not impressions.** Each instance is one finding. "Generally wordy" is not
  a finding.
- **Respect the text type.** A rule that does not apply to this kind of text is `n/a`, not
  clean. A commit subject has no stress position to check.
- **Respect the escape hatch.** If breaking a rule is the clearest option, do not flag it.
- **No new facts.** Flag an unsupported claim (R18, R19) so the author can support or soften
  it. Never propose support the source does not contain.

### 3. Report

Print a scorecard. List the rules with findings first, ordered by count, and show up to three
excerpts each. Then give one line listing the rules that are clean and the rules that are `n/a`.

```
prose-style audit: README.md (212 lines, 41 findings)

| Rule | Count | Examples |
|---|---|---|
| H4 Em dashes | 14 | L20 "**Test First** — the RED → GREEN" → use a colon after the label |
| H2 Title Case | 9 | L15 "## What this skill does" → "## What This Skill Does" |
| R16 Stock transitions | 3 | L88 "Additionally, the guard…" → merge with the previous sentence |

Clean: R1, R3, R9, R12, H3, H5. Not applicable: none.
```

If there are no findings, say so and stop.

### 4. Confirm

Ask: **"Apply these revisions to FILE in place?"** Offer all findings, selected rules, or none.
If the user has already asked for the revision to be applied ("revise the README", "fix it"),
that request is the confirmation. Go ahead, and say that you are going ahead.

Before editing, check the file's state with `git status --short -- FILE`. If the file is
untracked or has uncommitted changes, git cannot undo the edit cleanly. Copy the original to a
temporary snapshot first, and say where it is.

### 5. Revise in Place

Edit passage by passage with targeted replacements. Do not rewrite the whole file. Each edit
must resolve one or more listed findings and obey `references/revision-contract.md`: no new
facts, structure preserved, meaning preserved, no growth in length, and nothing outside the
flagged passages changed.

### 6. Re-audit

Audit the revised file again, using the same rules and the same standard. Print a before and
after table of counts per rule. For any finding that remains, say why: usually an unsupported
claim (R18, R19) that only the author can resolve, or a case where the escape hatch applies.
Flag any **new** finding your edits introduced, and fix it.

### 7. Diff

Show `git diff -- FILE`, or a `diff -u` against the snapshot when the file was not clean.
End with one line: the finding counts before and after, and any items left for the author.

## Hard Rules

- Never change code, identifiers, commands, URLs, quotations, or frontmatter values.
- Never add a fact, number, citation, link, or claim (R19 applies to the reviser too).
- Never change a passage the audit did not flag. The exception is a sentence that must change
  so that a flagged neighbour still reads correctly.
- Never write a file before the confirmation step.
- When the author's voice deliberately departs from a rule (marked with a comment, or
  explained when you ask), leave the passage alone.
