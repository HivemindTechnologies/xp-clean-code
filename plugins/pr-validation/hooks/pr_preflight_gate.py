#!/usr/bin/env python3
"""Gate pull request creation on a pr-validation preflight for the current HEAD.

The hook runs before a shell command or MCP tool call. When the call would open
a pull request and no preflight record exists for the commit at HEAD, the hook
denies it and tells the agent to run the pr-validation skill in preflight mode.
The skill writes the record once the report is in front of the user and the
user has confirmed; any new commit changes HEAD and requires a fresh preflight.

Hosts:
  --host claude   Claude Code and Codex (PreToolUse, hookSpecificOutput)
  --host cursor   Cursor (beforeShellExecution, permission response)

The gate fails open: when the payload is unreadable, the directory is not a git
repository, or git is unavailable, the call proceeds. It is a guardrail, not an
enforcement boundary.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Union

Host = Literal["claude", "cursor"]

MARKER_DIRECTORY = "pr-preflight"

# `gh pr create`, its alias `gh pr new`, and global flags between `gh` and `pr`
# (`gh -R owner/repo pr create`). Anchored to a command boundary so that
# `echo "gh pr create"` inside a longer word does not match by accident.
PR_CREATE_COMMAND = re.compile(
    r"(?:^|[\s;&|(`])gh(?:\s+(?:-R|--repo)\s+\S+|\s+--repo=\S+)*\s+pr\s+(?:create|new)(?:\s|$)"
)
PR_CREATE_MCP_TOOL = re.compile(r"(?:^|__)create_pull_request$")

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
class Unrelated:
    """A tool call the gate has no opinion about."""


Intercepted = Union[PrCreation, Unrelated]


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


def intercept(host: Host, payload: dict[str, object]) -> Intercepted:
    """Classify a hook payload as a pull request creation or something else."""
    if host == "cursor":
        cwd = str(payload.get("cwd") or first_workspace_root(payload))
        if payload.get("hook_event_name") == "beforeShellExecution":
            if is_pr_creation_command(command_text(payload.get("command"))):
                return PrCreation(cwd)
        return Unrelated()

    cwd = str(payload.get("cwd") or "")
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input")
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    if tool_name == "Bash" and is_pr_creation_command(command_text(tool_input.get("command"))):
        return PrCreation(cwd)
    if tool_name.startswith("mcp__") and is_pr_creation_tool(tool_name):
        return PrCreation(cwd)
    return Unrelated()


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
        intercepted = intercept(host, payload)
        if isinstance(intercepted, Unrelated) or not intercepted.cwd:
            decision: Decision = Allow()
        else:
            decision = decide(read_repository_state(intercepted.cwd))
    except (ValueError, GitUnavailable):
        decision = Allow()

    output = render(host, decision)
    if output:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
