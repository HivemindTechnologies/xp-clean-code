---
description: Validate a GitHub pull request for function purity, idempotency, BDD scenario coverage, protection claims, and spec sync
argument-hint: <pr-number | pr-url | branch> (optional; defaults to the PR for the current branch)
allowed-tools: Bash(gh pr view:*), Bash(gh pr diff:*), Bash(gh pr list:*), Bash(gh repo view:*), Bash(git worktree:*), Bash(git checkout --:*), Bash(git status:*), Bash(git diff:*)
---

You are running the **pr-validation** check against a GitHub pull request.

## Target PR

The user requested validation of: `$ARGUMENTS`

- If `$ARGUMENTS` is empty, resolve the PR associated with the current branch (`gh pr view`).
- If it is a number or URL, target that PR directly.

Load and apply the **pr-validation** skill. Because this command targets GitHub, read and follow the skill's `references/github-pr-workflow.md` procedure before running the five analyses (Purity, Idempotency, BDD Coverage, Protection Claims, Spec Sync). Produce the structured PR Validation Report with a final verdict.
