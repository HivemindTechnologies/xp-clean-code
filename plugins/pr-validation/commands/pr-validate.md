---
description: Validate a GitHub pull request for function purity, idempotency, BDD scenario coverage, and protection claims
argument-hint: <pr-number | pr-url | branch> (optional; defaults to the PR for the current branch)
allowed-tools: Bash(gh pr view:*), Bash(gh pr diff:*), Bash(gh pr list:*), Bash(gh repo view:*), Bash(git worktree:*), Bash(git checkout --:*), Bash(git status:*), Bash(git diff:*)
---

You are running the **pr-validation** check against a GitHub pull request.

The user requested validation of: `$ARGUMENTS`

Load and apply the **pr-validation** skill. Because this command targets GitHub, read and follow the skill's `references/github-pr-workflow.md` procedure before running the four analyses.

If `$ARGUMENTS` is empty, validate the pull request associated with the current branch. Otherwise use it as the PR number, URL, or branch. Produce the structured PR Validation Report with a final verdict.
