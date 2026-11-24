"""Tests for the opencode plugin in opencode/.

The Node tests cover the plugin's logic. The tests here hold its quick check in
agreement with the gate, and load the plugin into a real opencode when one is
installed. Each class skips when the tool it needs is missing.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE_PATH = ROOT / "plugins/pr-validation/hooks/pr_preflight_gate.py"
_spec = importlib.util.spec_from_file_location("pr_preflight_gate_for_opencode", GATE_PATH)
assert _spec is not None and _spec.loader is not None
gate = importlib.util.module_from_spec(_spec)
sys.modules["pr_preflight_gate_for_opencode"] = gate
_spec.loader.exec_module(gate)

SKILLS = {
    "brainstorming", "pr-validation", "prose-style", "review", "revise", "scaffolding", "spec", "xp-clean-code",
}
COMMANDS = {"brainstorm", "pr-preflight", "pr-validate", "reconcile", "revise", "scaffold", "spec"}


def node(script: str) -> str:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return completed.stdout


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class PluginLogic(unittest.TestCase):
    def test_node_tests_pass(self) -> None:
        completed = subprocess.run(
            ["node", "--test", "tests/opencode"], cwd=ROOT, capture_output=True, text=True
        )
        self.assertEqual(completed.returncode, 0, completed.stdout[-2000:] + completed.stderr[-2000:])

    def test_the_quick_check_lets_through_every_command_the_gate_would_check(self) -> None:
        commands = [
            "gh pr create",
            "gh pr new",
            "gh -R org/repo pr create --fill",
            "git push && gh pr create --fill",
            "(cd ../other && gh pr create)",
            "cd /x; gh pr create;",
            'gh pr create --body "$(cat <<EOF\nbody\nEOF\n)"',
        ]
        script = (
            "import { mayCreatePullRequest } from './opencode/core.js';"
            f"const commands = {json.dumps(commands)};"
            "console.log(JSON.stringify(commands.map((command) => mayCreatePullRequest('bash', { command }))));"
        )
        for command, passes in zip(commands, json.loads(node(script))):
            with self.subTest(command=command):
                self.assertTrue(gate.is_pr_creation_command(command))
                self.assertTrue(passes)


@unittest.skipUnless(shutil.which("opencode"), "opencode is not installed")
class LoadsIntoOpencode(unittest.TestCase):
    """Loads the repository as a local plugin into a throwaway project; no model is called."""

    def opencode(self, plugin_entry: object, *arguments: str) -> object:
        with tempfile.TemporaryDirectory() as project:
            config = {"$schema": "https://opencode.ai/config.json", "plugin": [plugin_entry]}
            (Path(project) / "opencode.json").write_text(json.dumps(config), encoding="utf-8")
            # opencode cuts long output short when it writes to a pipe, so it writes to a file.
            output = Path(project) / "output.json"
            with output.open("w", encoding="utf-8") as stdout:
                completed = subprocess.run(
                    ["opencode", "debug", *arguments], cwd=project, stdout=stdout,
                    stderr=subprocess.PIPE, text=True, timeout=120,
                )
            self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
            return json.loads(output.read_text(encoding="utf-8"))

    def ours(self, skills: object) -> set[str]:
        assert isinstance(skills, list)
        return {
            skill["name"] for skill in skills if str(ROOT / "plugins") in str(skill.get("location", ""))
        }

    def test_registers_every_skill(self) -> None:
        self.assertEqual(self.ours(self.opencode(str(ROOT), "skill")), SKILLS)

    def test_registers_every_command(self) -> None:
        config = self.opencode(str(ROOT), "config")
        assert isinstance(config, dict)
        self.assertLessEqual(COMMANDS, set(config.get("command") or {}))

    def test_registers_only_the_plugins_named(self) -> None:
        entry = [str(ROOT), {"plugins": ["prose-style"]}]
        self.assertEqual(self.ours(self.opencode(entry, "skill")), {"prose-style", "revise"})
        config = self.opencode(entry, "config")
        assert isinstance(config, dict)
        self.assertEqual(COMMANDS & set(config.get("command") or {}), {"revise"})


if __name__ == "__main__":
    unittest.main()
