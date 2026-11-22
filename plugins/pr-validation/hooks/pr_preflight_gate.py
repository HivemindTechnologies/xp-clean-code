#!/usr/bin/env python3
"""Gate pull request creation on a pr-validation preflight for the current HEAD.

The hook runs before a shell command or MCP tool call. When the call would open
a pull request and no preflight record exists for the commit at HEAD, the hook
denies it and tells the agent to run the pr-validation skill in preflight mode.
The skill writes the record once the report is in front of the user and the
user has confirmed; any new commit changes HEAD and requires a fresh preflight.

The repository is the one the command runs in: the session's directory,
followed through any `cd` or `pushd` earlier in the same command. A `cd` the
gate cannot resolve (a variable, a substitution, `cd -`) denies the call with a
request for a literal path.

Hosts:
  --host claude   Claude Code and Codex (PreToolUse, hookSpecificOutput)
  --host cursor   Cursor (beforeShellExecution, permission response)

The gate fails open: when the payload is unreadable, the directory is not a git
repository, or git is unavailable, the call proceeds. It is a guardrail, not an
enforcement boundary.
"""

from __future__ import annotations

import json
import posixpath
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Optional, Union

Host = Literal["claude", "cursor"]

MARKER_DIRECTORY = "pr-preflight"

# `gh pr create`, its alias `gh pr new`, and global flags between `gh` and `pr`
# (`gh -R owner/repo pr create`). Anchored to a command boundary so that
# `echo "gh pr create"` inside a longer word does not match by accident.
PR_CREATE_COMMAND = re.compile(
    r"(?:^|[\s;&|(`])gh(?:\s+(?:-R|--repo)\s+\S+|\s+--repo=\S+)*\s+pr\s+(?:create|new)(?=[\s;&|)]|$)"
)
PR_CREATE_MCP_TOOL = re.compile(r"(?:^|__)create_pull_request$")

# Where one shell command ends and the next begins, for following `cd` through
# a chain such as `cd ../other && git push && gh pr create`.
COMMAND_SEPARATOR = re.compile(r"&&|\|\||[;|\n(]")
DIRECTORY_CHANGES = ("cd", "pushd")

UNLOCATED_REASON = (
    "The pr-validation preflight gate cannot tell which repository this pull "
    "request comes from: the command changes directory with a path the gate "
    "cannot resolve, such as a variable, a command substitution or `cd -`. "
    "Change into the repository with a literal path (cd /path/to/repo && gh pr "
    "create ...), or run the command from the repository directory."
)

DENY_REASON = (
    "Pull request creation is gated on a pr-validation preflight, and none is "
    "recorded for the current HEAD ({head}). Load the pr-validation skill and "
    "follow references/preflight-workflow.md: validate this branch and the PR "
    "title and body you are about to submit, show the user the report, and ask "
    "whether to proceed. Record the preflight only after the user confirms, then "
    "retry this call."
)
USER_MESSAGE = "pr-validation: running the preflight check before opening the pull request."


# ---------------------------------------------------------------------------
# Pure core
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrCreation:
    """A tool call that would open a pull request, and where it runs."""

    cwd: str


@dataclass(frozen=True)
class Unlocated:
    """A pull request creation whose repository the gate cannot work out."""


@dataclass(frozen=True)
class Unrelated:
    """A tool call the gate has no opinion about."""


Intercepted = Union[PrCreation, Unlocated, Unrelated]


@dataclass(frozen=True)
class Allow:
    pass


@dataclass(frozen=True)
class Deny:
    reason: str


Decision = Union[Allow, Deny]


@dataclass(frozen=True)
class RepositoryState:
    """What the gate needs to know about the repository; read at the boundary."""

    head: str
    preflight_recorded: bool
    gate_disabled: bool


def is_pr_creation_command(command: str) -> bool:
    return PR_CREATE_COMMAND.search(command) is not None


def is_pr_creation_tool(tool_name: str) -> bool:
    return PR_CREATE_MCP_TOOL.search(tool_name) is not None


def command_text(raw: object) -> str:
    """Codex may pass a command as an argument vector; Claude and Cursor pass a string."""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        return " ".join(str(part) for part in raw)
    return ""


def first_workspace_root(payload: dict[str, object]) -> str:
    roots = payload.get("workspace_roots")
    if isinstance(roots, list) and roots and isinstance(roots[0], str):
        return roots[0]
    return ""


def first_operand(arguments: list[str]) -> str:
    """The directory argument of `cd`, skipping options such as `-P`; `~` when there is none."""
    operands = [argument for argument in arguments if argument == "-" or not argument.startswith("-")]
    return operands[0] if operands else "~"


def literal_target(arguments: list[str], home: str) -> Optional[str]:
    """The path `cd` is given, with `~` expanded; None when only the shell could resolve it."""
    target = first_operand(arguments)
    if target == "~" or target.startswith("~/"):
        return home + target[1:] if home else None
    if target == "-" or any(character in target for character in "$`~"):
        return None
    return target


def change_directory(current: str, arguments: list[str], home: str) -> Optional[str]:
    """Where `cd` or `pushd` with these arguments lands, or None when it cannot be known."""
    target = literal_target(arguments, home)
    if target is None or not (posixpath.isabs(target) or current):
        return None
    return posixpath.normpath(posixpath.join(current, target))


def directory_change(segment: str) -> Optional[list[str]]:
    """The arguments of a `cd` or `pushd` segment; None when the segment is something else."""
    words = segment.split()
    if not words or words[0] not in DIRECTORY_CHANGES:
        return None
    try:
        return shlex.split(segment)[1:]
    except ValueError:
        return ["$unparseable"]


def target_directory(command: str, cwd: str, home: str) -> Optional[str]:
    """The directory `gh pr create` runs in, following any `cd` before it in the same command."""
    match = PR_CREATE_COMMAND.search(command)
    directory: Optional[str] = cwd
    for segment in COMMAND_SEPARATOR.split(command[: match.start()] if match else ""):
        arguments = directory_change(segment)
        if arguments is not None and directory is not None:
            directory = change_directory(directory, arguments, home)
    return directory


def located(command: str, cwd: str, home: str) -> Intercepted:
    directory = target_directory(command, cwd, home)
    return Unlocated() if directory is None else PrCreation(directory)


def intercept_cursor(payload: dict[str, object], home: str) -> Intercepted:
    command = command_text(payload.get("command"))
    if payload.get("hook_event_name") != "beforeShellExecution" or not is_pr_creation_command(command):
        return Unrelated()
    return located(command, str(payload.get("cwd") or first_workspace_root(payload)), home)


def intercept_tool_call(payload: dict[str, object], home: str) -> Intercepted:
    cwd = str(payload.get("cwd") or "")
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input")
    command = command_text(tool_input.get("command")) if isinstance(tool_input, dict) else ""
    if tool_name == "Bash" and is_pr_creation_command(command):
        return located(command, cwd, home)
    if tool_name.startswith("mcp__") and is_pr_creation_tool(tool_name):
        return PrCreation(cwd)
    return Unrelated()


def intercept(host: Host, payload: dict[str, object], home: str = "") -> Intercepted:
    """Classify a hook payload as a pull request creation, and find the repository it runs in."""
    if host == "cursor":
        return intercept_cursor(payload, home)
    return intercept_tool_call(payload, home)


def decision_for(intercepted: Intercepted, read_state: Callable[[str], RepositoryState]) -> Decision:
    if isinstance(intercepted, Unlocated):
        return Deny(UNLOCATED_REASON)
    if isinstance(intercepted, Unrelated) or not intercepted.cwd:
        return Allow()
    return decide(read_state(intercepted.cwd))


def decide(state: RepositoryState) -> Decision:
    if state.gate_disabled or state.preflight_recorded:
        return Allow()
    return Deny(DENY_REASON.format(head=state.head[:12]))


def render(host: Host, decision: Decision) -> str:
    """The hook's stdout. Empty means no opinion: the host's normal flow applies."""
    if host == "cursor":
        if isinstance(decision, Deny):
            return json.dumps(
                {
                    "continue": True,
                    "permission": "deny",
                    "user_message": USER_MESSAGE,
                    "agent_message": decision.reason,
                }
            )
        return json.dumps({"continue": True, "permission": "allow"})

    if isinstance(decision, Deny):
        return json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": decision.reason,
                }
            }
        )
    return ""


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------


class GitUnavailable(Exception):
    pass


def git(cwd: str, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", cwd, *arguments],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise GitUnavailable(str(error)) from error
    if completed.returncode != 0:
        raise GitUnavailable(completed.stderr.strip())
    return completed.stdout.strip()


def marker_path(cwd: str, head: str) -> Path:
    directory = git(cwd, "rev-parse", "--path-format=absolute", "--git-path", MARKER_DIRECTORY)
    return Path(directory) / head


def gate_disabled(cwd: str) -> bool:
    try:
        return git(cwd, "config", "--type=bool", "--get", "pr-preflight.enabled") == "false"
    except GitUnavailable:
        return False  # unset


def read_repository_state(cwd: str) -> RepositoryState:
    head = git(cwd, "rev-parse", "HEAD")
    return RepositoryState(
        head=head,
        preflight_recorded=marker_path(cwd, head).is_file(),
        gate_disabled=gate_disabled(cwd),
    )


def parse_host(arguments: list[str]) -> Host:
    if "--host" in arguments:
        index = arguments.index("--host")
        if index + 1 < len(arguments) and arguments[index + 1] == "cursor":
            return "cursor"
    return "claude"


def main(arguments: list[str]) -> int:
    host = parse_host(arguments)
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        intercepted = intercept(host, payload, str(Path.home()))
        decision: Decision = decision_for(intercepted, read_repository_state)
    except (ValueError, GitUnavailable):
        decision = Allow()

    output = render(host, decision)
    if output:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
