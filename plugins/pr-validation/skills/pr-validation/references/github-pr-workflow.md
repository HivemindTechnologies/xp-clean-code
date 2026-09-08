# GitHub Pull Request Workflow

Use this workflow when the validation target is a GitHub pull request. It supplies the PR inputs required by the main skill and isolates mutation checks from the branch under review.

## Resolve and fetch the target

Use the PR number, URL, or branch supplied by the user. If no target was supplied, resolve the pull request associated with the current branch.

Fetch the pull request metadata, diff, and commit messages with GitHub CLI:

```bash
gh pr view <target> --json number,title,body,author,baseRefName,headRefName,files,url
gh pr diff <target>
gh pr view <target> --json commits --jq '.commits[].messageHeadline'
```

Omit `<target>` when resolving the pull request for the current branch. Treat this output, rather than the local working tree, as the source of truth for the analysis. The title, body, and commit messages are required for extracting protection claims (Analysis 4) and for reading the named spec (Analysis 5).

If GitHub CLI cannot resolve the pull request or authentication fails, stop and report the problem. Suggest `gh auth login` when authentication is missing.

## Isolate removal checks

Analysis 4 requires executable removal checks. Never mutate the user's current working tree or the branch under review.

For each protection claim:

1. Create a disposable worktree at the pull request head.
2. Confirm the mapped test passes before changing the protection.
3. Remove or invert one protection at a time.
4. Run only the mapped test and record whether it failed for the claimed reason.
5. Restore the mutation and confirm the mapped test passes again.
6. Remove the disposable worktree when validation finishes, including after a failed check.

Ask before running a project test command when its cost or required environment is unknown. Use the project's existing test runner. If the toolchain, services, or secrets needed to execute a test are unavailable, report the affected claim as **UNVERIFIABLE** and give the reason. Never mark a claim **VERIFIED** from static inspection alone.

## Spec sync check

Analysis 5 applies when the repository keeps specs under `docs/specs/`. After fetching the PR:

1. Read the spec named in the PR body (`Spec: NNN` or a link to `docs/specs/NNN-*.md`).
2. List every scenario the diff adds or changes in feature files.
3. Run the mirror guard on the PR head — prefer the project's `tests/test_specs_are_in_sync.py` if present; otherwise use the reference guard from the spec-driven plugin (`plugins/spec-driven/skills/spec/references/spec-sync-guard.py`) copied beside the worktree. Quote its output.
4. If `docs/specs/` does not exist, report **Analysis 5: NOT APPLICABLE**.
