---
description: Validate a GitHub pull request for function purity, idempotency, and BDD scenario coverage
argument-hint: <pr-number | pr-url | branch> (optional; defaults to the PR for the current branch)
allowed-tools: Bash(gh pr view:*), Bash(gh pr diff:*), Bash(gh pr list:*), Bash(gh repo view:*)
---

You are running the **pr-validation** check against a GitHub pull request.

## Target PR

The user requested validation of: `$ARGUMENTS`

- If `$ARGUMENTS` is empty, resolve the PR associated with the current branch (`gh pr view`).
- If it is a number or URL, target that PR directly.

## Step 1 — Fetch the PR from GitHub

Run these and use their output as the source of truth (do not analyse the local working tree):

```
gh pr view $ARGUMENTS --json number,title,author,baseRefName,headRefName,files,url
gh pr diff $ARGUMENTS
```

If `gh` reports no PR or authentication fails, stop and tell the user (suggest `gh auth login`).

## Step 2 — Run the validation

Load and apply the **pr-validation** skill, using the diff from Step 1 as the PR diff.
Follow the skill exactly: run the three analyses (Purity, Idempotency, BDD Coverage)
and produce the structured PR Validation Report with a final verdict.

Work only from the diff obtained above — analyse changed functions, not unchanged code,
unless a changed function's call site requires it.
