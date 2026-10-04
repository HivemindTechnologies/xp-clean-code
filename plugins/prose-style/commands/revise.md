---
description: Audit prose against the prose-style rules and revise it in place, with a scorecard, a confirmation, a re-audit, and a diff
argument-hint: <file …> (optional; defaults to pasted text, then the draft commit message or PR description under discussion)
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(diff:*), Bash(cp:*), Bash(mktemp:*)
---

You are running the **revise** pass of the prose-style plugin.

## Target

The user asked to revise: `$ARGUMENTS`

- One or more paths: audit each file in turn.
- Empty: revise the text pasted in the conversation, or else the draft commit message or pull
  request description under discussion. If there is none, ask what to revise.

## Run

Load the **prose-style** skill and read its `references/rules.md`, then load and apply the
**revise** skill exactly, with `references/revision-contract.md` as the binding invariants.
Print the scorecard, then confirm before editing. Edit files in place, passage by passage; never
rewrite a file wholesale. Re-audit, then show the diff.
