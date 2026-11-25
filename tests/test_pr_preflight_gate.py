"""Scenarios for the pr-validation preflight gate hook.

Run with: python3 -m unittest discover -s tests
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "plugins/pr-validation/hooks/pr_preflight_gate.py"
)
_spec = importlib.util.spec_from_file_location("pr_preflight_gate", GATE_PATH)
assert _spec is not None and _spec.loader is not None
gate = importlib.util.module_from_spec(_spec)
sys.modules["pr_preflight_gate"] = gate
_spec.loader.exec_module(gate)


def bash_payload(command: object, cwd: str = "/repo") -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}


class RecognisesPullRequestCreation(unittest.TestCase):
    def test_plain_command(self) -> None:
        self.assertTrue(gate.is_pr_creation_command('gh pr create --title "x" --body "y"'))

    def test_alias_new(self) -> None:
        self.assertTrue(gate.is_pr_creation_command("gh pr new"))

    def test_repo_flag_between_gh_and_pr(self) -> None:
        self.assertTrue(gate.is_pr_creation_command("gh -R org/repo pr create --fill"))
        self.assertTrue(gate.is_pr_creation_command("gh --repo=org/repo pr create"))

    def test_chained_after_push(self) -> None:
        self.assertTrue(gate.is_pr_creation_command("git push -u origin feat && gh pr create --fill"))

    def test_inside_a_subshell_or_before_a_separator(self) -> None:
        for command in ("(cd ../other && gh pr create --fill)", "gh pr create;", "gh pr create|cat"):
            with self.subTest(command=command):
                self.assertTrue(gate.is_pr_creation_command(command))

    def test_heredoc_body(self) -> None:
        self.assertTrue(gate.is_pr_creation_command('gh pr create --body "$(cat <<EOF\nbody\nEOF\n)"'))

    def test_other_pr_subcommands_pass(self) -> None:
        for command in ("gh pr view", "gh pr diff 12", "gh pr list", "gh pr checks", "gh pr edit 3"):
            with self.subTest(command=command):
                self.assertFalse(gate.is_pr_creation_command(command))

    def test_lookalike_words_pass(self) -> None:
        self.assertFalse(gate.is_pr_creation_command("ngh pr create"))
        self.assertFalse(gate.is_pr_creation_command("gh pr created-at"))

    def test_mcp_tool_names(self) -> None:
        self.assertTrue(gate.is_pr_creation_tool("mcp__github__create_pull_request"))
        self.assertFalse(gate.is_pr_creation_tool("mcp__github__create_pull_request_review"))
        self.assertFalse(gate.is_pr_creation_tool("mcp__github__list_pull_requests"))


class FindsTheRepository(unittest.TestCase):
    """The gate checks the repository the command runs in, not the session's directory."""

    def target(self, command: str, cwd: str = "/session") -> object:
        return gate.target_directory(command, cwd, "/home/u")

    def test_without_cd_the_session_directory(self) -> None:
        self.assertEqual(self.target("gh pr create --fill"), "/session")

    def test_cd_before_the_command(self) -> None:
        self.assertEqual(self.target("cd /other && gh pr create"), "/other")
        self.assertEqual(self.target("cd /other; gh pr create"), "/other")
        self.assertEqual(self.target("(cd /other && gh pr create)"), "/other")
        self.assertEqual(self.target("pushd /other && gh pr create"), "/other")

    def test_paths_resolve_against_the_directory_so_far(self) -> None:
        self.assertEqual(self.target("cd sub && gh pr create"), "/session/sub")
        self.assertEqual(self.target("cd /a && cd ../b && git push && gh pr create"), "/b")
        self.assertEqual(self.target("cd ~/GitRoot/repo && gh pr create"), "/home/u/GitRoot/repo")
        self.assertEqual(self.target("cd && gh pr create"), "/home/u")
        self.assertEqual(self.target('cd "/with space" && gh pr create'), "/with space")

    def test_cd_after_the_command_does_not_count(self) -> None:
        self.assertEqual(self.target("gh pr create --fill && cd /other"), "/session")

    def test_paths_it_cannot_resolve(self) -> None:
        for command in ('cd "$REPO" && gh pr create', "cd - && gh pr create",
                        "cd `pwd` && gh pr create", "cd 'unterminated && gh pr create"):
            with self.subTest(command=command):
                self.assertIsNone(self.target(command))
        self.assertIsNone(gate.target_directory("cd sub && gh pr create", "", "/home/u"))


class InterceptsPayloads(unittest.TestCase):
    def test_claude_bash(self) -> None:
        self.assertEqual(gate.intercept("claude", bash_payload("gh pr create")), gate.PrCreation("/repo"))

    def test_codex_argument_vector(self) -> None:
        payload = bash_payload(["bash", "-lc", "gh pr create --fill"])
        self.assertEqual(gate.intercept("claude", payload), gate.PrCreation("/repo"))

    def test_claude_mcp(self) -> None:
        payload = {"tool_name": "mcp__github__create_pull_request", "tool_input": {}, "cwd": "/repo"}
        self.assertEqual(gate.intercept("claude", payload), gate.PrCreation("/repo"))

    def test_claude_unrelated_bash(self) -> None:
        self.assertEqual(gate.intercept("claude", bash_payload("ls")), gate.Unrelated())

    def test_cursor_shell(self) -> None:
        payload = {"hook_event_name": "beforeShellExecution", "command": "gh pr create", "cwd": "/repo"}
        self.assertEqual(gate.intercept("cursor", payload), gate.PrCreation("/repo"))

    def test_cursor_falls_back_to_workspace_root(self) -> None:
        payload = {
            "hook_event_name": "beforeShellExecution",
            "command": "gh pr create",
            "workspace_roots": ["/workspace"],
        }
        self.assertEqual(gate.intercept("cursor", payload), gate.PrCreation("/workspace"))

    def test_follows_cd_on_every_host(self) -> None:
        command = "cd /other && gh pr create"
        cursor = {"hook_event_name": "beforeShellExecution", "command": command, "cwd": "/repo"}
        self.assertEqual(gate.intercept("claude", bash_payload(command)), gate.PrCreation("/other"))
        self.assertEqual(gate.intercept("cursor", cursor), gate.PrCreation("/other"))

    def test_an_unresolvable_cd_is_unlocated(self) -> None:
        payload = bash_payload('cd "$REPO" && gh pr create')
        self.assertEqual(gate.intercept("claude", payload), gate.Unlocated())


def opencode_payload(tool: str, args: dict[str, object], directory: str = "/repo") -> dict[str, object]:
    """What the opencode plugin sends: the tool name, its arguments, and the session's directory."""
    return {"tool": tool, "args": args, "directory": directory}


class InterceptsOpencode(unittest.TestCase):
    def test_bash_runs_in_the_session_directory(self) -> None:
        payload = opencode_payload("bash", {"command": "gh pr create --fill"})
        self.assertEqual(gate.intercept("opencode", payload), gate.PrCreation("/repo"))

    def test_bash_runs_in_its_workdir(self) -> None:
        absolute = opencode_payload("bash", {"command": "gh pr create", "workdir": "/other"})
        relative = opencode_payload("bash", {"command": "gh pr create", "workdir": "sub"})
        self.assertEqual(gate.intercept("opencode", absolute), gate.PrCreation("/other"))
        self.assertEqual(gate.intercept("opencode", relative), gate.PrCreation("/repo/sub"))

    def test_bash_follows_cd_from_its_workdir(self) -> None:
        payload = opencode_payload("bash", {"command": "cd ../other && gh pr create", "workdir": "/work/repo"})
        self.assertEqual(gate.intercept("opencode", payload), gate.PrCreation("/work/other"))
        unresolvable = opencode_payload("bash", {"command": 'cd "$REPO" && gh pr create'})
        self.assertEqual(gate.intercept("opencode", unresolvable), gate.Unlocated())

    def test_mcp_tools_join_server_and_tool_with_one_underscore(self) -> None:
        payload = opencode_payload("github_create_pull_request", {"title": "x"})
        self.assertEqual(gate.intercept("opencode", payload), gate.PrCreation("/repo"))
        for tool in ("github_create_pull_request_review", "github_list_pull_requests", "read"):
            with self.subTest(tool=tool):
                self.assertEqual(gate.intercept("opencode", opencode_payload(tool, {})), gate.Unrelated())

    def test_unrelated_bash(self) -> None:
        self.assertEqual(gate.intercept("opencode", opencode_payload("bash", {"command": "ls"})), gate.Unrelated())

    def test_renders_a_deny_as_json_and_an_allow_as_nothing(self) -> None:
        self.assertEqual(json.loads(gate.render("opencode", gate.Deny("why"))), {"permission": "deny", "reason": "why"})
        self.assertEqual(gate.render("opencode", gate.Allow()), "")


class Decides(unittest.TestCase):
    def test_denies_without_record(self) -> None:
        decision = gate.decide(gate.RepositoryState("a" * 40, preflight_recorded=False, gate_disabled=False))
        self.assertIsInstance(decision, gate.Deny)
        self.assertIn("aaaaaaaaaaaa", decision.reason)
        self.assertIn("preflight-workflow.md", decision.reason)

    def test_allows_with_record(self) -> None:
        state = gate.RepositoryState("a" * 40, preflight_recorded=True, gate_disabled=False)
        self.assertEqual(gate.decide(state), gate.Allow())

    def test_allows_when_disabled(self) -> None:
        state = gate.RepositoryState("a" * 40, preflight_recorded=False, gate_disabled=True)
        self.assertEqual(gate.decide(state), gate.Allow())

    def test_denies_when_the_repository_is_unknown(self) -> None:
        decision = gate.decision_for(gate.Unlocated(), lambda cwd: self.fail("must not read git"))
        self.assertIsInstance(decision, gate.Deny)
        self.assertIn("cannot tell which repository", decision.reason)

    def test_claude_allow_is_silent(self) -> None:
        self.assertEqual(gate.render("claude", gate.Allow()), "")

    def test_cursor_always_answers_with_valid_json(self) -> None:
        for decision in (gate.Allow(), gate.Deny("why")):
            with self.subTest(decision=decision):
                self.assertIn(json.loads(gate.render("cursor", decision))["permission"], ("allow", "deny"))


class EndToEnd(unittest.TestCase):
    """Runs the script as each host would, against a throwaway repository."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        for command in (
            ["git", "init", "-q"],
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
             "commit", "-q", "--allow-empty", "-m", "first"],
        ):
            subprocess.run(command, cwd=self.repo, check=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_gate(self, host: str, payload: dict[str, object]) -> str:
        completed = subprocess.run(
            [sys.executable, str(GATE_PATH), "--host", host],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout.strip()

    def record_preflight(self, repo: str = "") -> None:
        # The one-liner documented in references/preflight-workflow.md.
        subprocess.run(
            'marker="$(git rev-parse --path-format=absolute --git-path pr-preflight)/$(git rev-parse HEAD)"'
            ' && mkdir -p "$(dirname "$marker")" && printf "verdict=PASS\\n" > "$marker"',
            shell=True,
            cwd=repo or self.repo,
            check=True,
        )

    def test_claude_denies_then_allows_after_record(self) -> None:
        payload = bash_payload("gh pr create --fill", cwd=self.repo)
        denied = json.loads(self.run_gate("claude", payload))
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")

        self.record_preflight()
        self.assertEqual(self.run_gate("claude", payload), "")

    def test_new_commit_invalidates_record(self) -> None:
        self.record_preflight()
        self.assertEqual(self.run_gate("claude", bash_payload("gh pr create", cwd=self.repo)), "")
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
             "commit", "-q", "--allow-empty", "-m", "second"],
            cwd=self.repo,
            check=True,
        )
        output = self.run_gate("claude", bash_payload("gh pr create", cwd=self.repo))
        self.assertEqual(json.loads(output)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_cursor_denies_then_allows_after_record(self) -> None:
        payload = {"hook_event_name": "beforeShellExecution", "command": "gh pr create", "cwd": self.repo}
        self.assertEqual(json.loads(self.run_gate("cursor", payload))["permission"], "deny")
        self.record_preflight()
        self.assertEqual(json.loads(self.run_gate("cursor", payload))["permission"], "allow")

    def test_opencode_denies_then_allows_after_record(self) -> None:
        payload = opencode_payload("bash", {"command": "gh pr create --fill"}, directory=self.repo)
        denied = json.loads(self.run_gate("opencode", payload))
        self.assertEqual(denied["permission"], "deny")
        self.assertIn("preflight-workflow.md", denied["reason"])
        self.record_preflight()
        self.assertEqual(self.run_gate("opencode", payload), "")

    def test_checks_the_repository_the_command_changes_into(self) -> None:
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        for command in (
            ["git", "init", "-q"],
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
             "commit", "-q", "--allow-empty", "-m", "other"],
        ):
            subprocess.run(command, cwd=other.name, check=True)
        payload = bash_payload(f"cd {other.name} && gh pr create --fill", cwd=self.repo)

        self.record_preflight()  # in the session's repository only
        denied = json.loads(self.run_gate("claude", payload))
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")

        self.record_preflight(other.name)
        self.assertEqual(self.run_gate("claude", payload), "")

    def test_repository_opt_out(self) -> None:
        subprocess.run(["git", "config", "pr-preflight.enabled", "false"], cwd=self.repo, check=True)
        self.assertEqual(self.run_gate("claude", bash_payload("gh pr create", cwd=self.repo)), "")

    def test_fails_open_outside_a_repository(self) -> None:
        with tempfile.TemporaryDirectory() as elsewhere:
            self.assertEqual(self.run_gate("claude", bash_payload("gh pr create", cwd=elsewhere)), "")

    def test_fails_open_on_garbage_input(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(GATE_PATH), "--host", "cursor"],
            input="not json",
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(json.loads(completed.stdout)["permission"], "allow")

    def test_unrelated_commands_never_touch_git(self) -> None:
        self.assertEqual(self.run_gate("claude", bash_payload("gh pr view", cwd="/nonexistent")), "")


class CursorMatcherAgreesWithGate(unittest.TestCase):
    """The Cursor matcher must let through every command the gate would deny."""

    def test_matcher(self) -> None:
        import re

        config = json.loads((GATE_PATH.parent / "hooks-cursor.json").read_text(encoding="utf-8"))
        matcher = re.compile(config["hooks"]["beforeShellExecution"][0]["matcher"])
        for command in (
            "gh pr create",
            "gh pr new",
            "gh -R org/repo pr create --fill",
            "git push && gh pr create --fill",
            "(cd ../other && gh pr create)",
        ):
            with self.subTest(command=command):
                self.assertTrue(gate.is_pr_creation_command(command))
                self.assertIsNotNone(matcher.search(command))


if __name__ == "__main__":
    unittest.main()
