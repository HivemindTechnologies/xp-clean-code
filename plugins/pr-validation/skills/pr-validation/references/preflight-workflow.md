# Preflight Workflow

Use this workflow before a pull request exists: when the user asks you to open one, when `/pr-preflight` runs, or when the preflight gate hook denies a `gh pr create` call or a `create_pull_request` tool call. It supplies the same inputs as `github-pr-workflow.md`, taken from the local branch and the draft you are about to submit, so that findings are fixed before anyone else reads the pull request.

The five analyses, the report format and the verdict rules are unchanged. Only the inputs differ.

## Assemble the Draft

Before validating, have the pull request you intend to open written down:

- **Title** and **body**, exactly as you would submit them. Analysis 4 extracts protection claims from the body, and Analysis 5 reads the spec it names (`Spec: NNN`). Validating a placeholder body proves nothing.
- **Base branch**: the `--base` you would pass, or the repository's default branch (`gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`).

## Obtain the Inputs

Work from committed history only. Uncommitted changes are not part of the pull request, so say so in the report if `git status --porcelain` is not empty.

```bash
git fetch origin <base>
git diff origin/<base>...HEAD
git log --format='%h %s' origin/<base>..HEAD
```

If the remote base cannot be fetched, fall back to the local `<base>` branch and state that in the report.

## Run the Deterministic Tools

Run `scripts/preflight_tools.py` from this skill's directory, as `references/tooling.md` describes:

1. Run it with `--plan` and the base branch. Show the user which checks would run, which are slow, and which cannot run and why.
2. Run the fast checks. If the plan has slow checks, ask the user whether to run them too, and pass `--include-slow` only if they agree.
3. Keep the markdown output for the **0 · Tooling** section of the report, and use the findings as evidence in the analyses: impurity signals in Analysis 1, uncovered changed lines in Analysis 3.

A required check that failed, errored, or did not run makes the verdict FAIL. Never install a missing tool; report it and suggest the install command from `references/tooling.md`.

## Run the Analyses

Run all five analyses as `SKILL.md` describes, with these substitutions:

| Input | Invoked mode | Preflight mode |
|---|---|---|
| Diff | `gh pr diff` | `git diff origin/<base>...HEAD` |
| Title and body | the pull request on GitHub | the draft above |
| Commit messages | `gh pr view --json commits` | `git log origin/<base>..HEAD` |
| Removal checks | disposable worktree at the PR head | disposable worktree at `HEAD` |
| Spec mirror guard | run on the PR head | run in the worktree at `HEAD` |

The isolation rules in `github-pr-workflow.md` apply unchanged: never mutate the user's working tree, restore every mutation, remove the worktree afterwards, and ask before running a test command of unknown cost.

Title the report **PR Preflight Report** instead of PR Validation Report, name the commit it covers (`HEAD` short hash), and put the **0 · Tooling** section before the five analyses.

## Decide with the User

Show the report, then ask the user whether to open the pull request. Do not decide for them, whatever the verdict:

- **PASS**: ask whether to proceed.
- **FAIL**: list what you recommend fixing first (often the body: an unsupported claim is cheaper to remove now than after review). Offer to fix, to proceed anyway, or to stop.

If you change code to address findings, commit, and run the preflight again: the record is tied to `HEAD`.

If you change only the title or body, re-run Analyses 4 and 5 against the new text before recording.

## Record the Preflight

Only after the user confirms that the pull request should be opened, record the preflight for the current `HEAD`:

```bash
marker="$(git rev-parse --path-format=absolute --git-path pr-preflight)/$(git rev-parse HEAD)" \
  && mkdir -p "$(dirname "$marker")" \
  && printf 'verdict=%s\nconfirmed=%s\n' "<PASS|FAIL>" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$marker"
```

Run it in the repository the pull request comes from. The record lives under `.git/`, so it is never committed, and it is per worktree. Then create the pull request with the exact title and body you validated, in a separate command: the hook checks before any part of a command runs, so a record written earlier in the same command is not yet there.

Never record a preflight you did not run, and never write the record to get past the gate without the user's confirmation. Never set `pr-preflight.enabled` yourself: turning the gate off is the user's decision.

## The Gate

The plugin ships a hook for Claude Code, Codex and Cursor that intercepts pull request creation:

- Claude Code and Codex: `PreToolUse` on `Bash` commands running `gh pr create` or `gh pr new`, and on MCP tools named `*create_pull_request`.
- Cursor: `beforeShellExecution` on the same `gh` commands. Cursor MCP tool calls are not gated.
- opencode: `tool.execute.before` in the repository's opencode plugin, on `bash` calls running the same `gh` commands (from the call's `workdir`), and on MCP tools named `*_create_pull_request`. The denial reaches the agent as the tool's error.

When no record exists for `HEAD`, the hook denies the call and points here.

The hook checks the repository the command runs in: the session's directory, followed through any `cd` or `pushd` earlier in the same command, so `cd ../other && gh pr create` is checked against `../other`. When a `cd` takes a path the hook cannot resolve (a variable, a command substitution, `cd -`), it denies the call and asks for a literal path. An MCP tool call is checked against the session's directory, and `gh -R owner/repo` is not compared with the local clone.

The hook fails open (no repository, no git, unreadable input), and it cannot see pull requests opened in a browser or by other tools. It is a reminder with teeth, not an enforcement boundary.

A user can turn the gate off for one repository with `git config pr-preflight.enabled false`.
