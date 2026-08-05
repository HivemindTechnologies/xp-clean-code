---
description: Validate a GitHub pull request for function purity, idempotency, BDD scenario coverage, and protection claims
argument-hint: <pr-number | pr-url | branch> (optional; defaults to the PR for the current branch)
allowed-tools: Bash(gh pr view:*), Bash(gh pr diff:*), Bash(gh pr list:*), Bash(gh repo view:*), Bash(git worktree:*), Bash(git checkout --:*), Bash(git status:*), Bash(git diff:*)
---

You are running the **pr-validation** check against a GitHub pull request.

## Target PR

The user requested validation of: `$ARGUMENTS`

- If `$ARGUMENTS` is empty, resolve the PR associated with the current branch (`gh pr view`).
- If it is a number or URL, target that PR directly.

## Step 1 — Fetch the PR from GitHub

Run these and use their output as the source of truth (do not analyse the local working tree):

```
gh pr view $ARGUMENTS --json number,title,body,author,baseRefName,headRefName,files,url
gh pr diff $ARGUMENTS
gh pr view $ARGUMENTS --json commits --jq '.commits[].messageHeadline'
```

The `body`, `title`, and commit messages are required input for Analysis 4 — the protection claims are
extracted from them, not from the diff. If `gh` reports no PR or authentication fails, stop and tell the
user (suggest `gh auth login`).

## Step 2 — Run the validation

Load and apply the **pr-validation** skill, using the diff from Step 1 as the PR diff.
Follow the skill exactly: run the four analyses (Purity, Idempotency, BDD Coverage, Protection Claims)
and produce the structured PR Validation Report with a final verdict.

Work only from the diff obtained above — analyse changed functions, not unchanged code,
unless a changed function's call site requires it.

## Step 3 — Run the removal checks for Analysis 4

Analysis 4 requires actually running tests, not reading them. For each protection claim in the PR body:

1. Create a disposable worktree at the PR head (`git worktree add`) — never mutate the branch under review.
2. Confirm the mapped test passes as a baseline.
3. Remove or invert the protection, one mutation at a time, and re-run only the mapped test.
4. Record whether it failed, and whether the failure was about the claim.
5. Restore the file and confirm the baseline again before moving to the next claim.
6. Remove the worktree when finished.

Ask before running the project's test command if it is unknown or expensive; use the project's own
runner (`pytest`, `cargo test`, `sbt test`, `npm test`, …). If tests cannot be run here — no toolchain,
missing services, required secrets — report the affected claims as **UNVERIFIABLE** with the reason.
Never report a claim as VERIFIED from a static reading of the test.
