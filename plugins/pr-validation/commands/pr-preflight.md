---
description: Validate the current branch and a draft pull request before opening it, then open it once you confirm
argument-hint: <base-branch> (optional; defaults to the repository's default branch)
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git fetch:*), Bash(git rev-parse:*), Bash(git worktree:*), Bash(gh repo view:*)
---

You are running the **pr-validation** check in **preflight mode**: the pull request does not exist yet.

## Target

Base branch: `$ARGUMENTS`

- If `$ARGUMENTS` is empty, use the repository's default branch.
- Validate the commits on the current branch that are not on the base.

Load and apply the **pr-validation** skill. Read and follow its `references/preflight-workflow.md`: assemble the draft title and body you would submit, run the deterministic tools (asking before any slow check), run the five analyses (Purity, Idempotency, BDD Coverage, Protection Claims, Spec Sync) against the local branch and that draft, and produce the PR Preflight Report with a final verdict.

Then ask whether to open the pull request. Record the preflight and open it only if the user confirms.
