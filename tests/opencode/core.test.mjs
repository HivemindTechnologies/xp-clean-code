// Run with: node --test tests/opencode
// tests/test_opencode_plugin.py runs these as part of the Python suite when Node is installed.

import assert from "node:assert/strict";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import {
  addCommands,
  addSkillPaths,
  commandsOf,
  gateReason,
  mayCreatePullRequest,
  parseCommand,
  pluginNames,
  selectPlugins,
  skillDirectories,
} from "../../opencode/core.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

test("a command keeps its description and drops the Claude Code front matter", () => {
  const text = "---\ndescription: Do the thing\nargument-hint: <x>\nallowed-tools: Bash(git status:*)\n---\n\nBody with $ARGUMENTS\n";
  assert.deepEqual(parseCommand(text), { description: "Do the thing", template: "Body with $ARGUMENTS" });
});

test("a command without front matter is all template", () => {
  assert.deepEqual(parseCommand("Just a body\n"), { description: "", template: "Just a body" });
});

test("every command in the repository has a description and a body", () => {
  const commands = Object.assign({}, ...pluginNames(ROOT).map((plugin) => commandsOf(ROOT, plugin)));
  assert.deepEqual(Object.keys(commands).sort(), [
    "brainstorm", "pr-preflight", "pr-validate", "reconcile", "revise", "scaffold", "spec",
  ]);
  for (const [name, command] of Object.entries(commands)) {
    assert.ok(command.description, `${name} has no description`);
    assert.ok(command.template.length > 100, `${name} has no body`);
    assert.ok(!command.template.includes("allowed-tools:"), `${name} kept its front matter`);
  }
});

test("all plugins by default, or only the ones named", () => {
  const all = pluginNames(ROOT);
  assert.deepEqual(all, ["pr-validation", "prose-style", "spec-driven", "xp-clean-code"]);
  assert.deepEqual(selectPlugins(all, undefined), all);
  assert.deepEqual(selectPlugins(all, { plugins: ["xp-clean-code", "prose-style", "unknown"] }), ["prose-style", "xp-clean-code"]);
});

test("every plugin has a skills directory", () => {
  assert.equal(skillDirectories(ROOT, pluginNames(ROOT)).length, 4);
});

test("skill paths are added in the shape the config already uses", () => {
  const empty = {};
  addSkillPaths(empty, ["/a"]);
  assert.deepEqual(empty.skills, { paths: ["/a"] });

  const object = { skills: { paths: ["/user"], urls: ["https://x"] } };
  addSkillPaths(object, ["/a"]);
  assert.deepEqual(object.skills, { paths: ["/user", "/a"], urls: ["https://x"] });

  const list = { skills: ["/user"] };
  addSkillPaths(list, ["/a"]);
  assert.deepEqual(list.skills, ["/user", "/a"]);
});

test("a command the user defined keeps its definition", () => {
  const config = { command: { revise: { template: "mine" } } };
  addCommands(config, { revise: { template: "ours" }, spec: { template: "ours" } });
  assert.deepEqual(config.command, { revise: { template: "mine" }, spec: { template: "ours" } });
});

test("only calls that might open a pull request reach the gate", () => {
  assert.equal(mayCreatePullRequest("bash", { command: "cd ../x && gh pr create --fill" }), true);
  assert.equal(mayCreatePullRequest("bash", { command: "ls -la" }), false);
  assert.equal(mayCreatePullRequest("bash", {}), false);
  assert.equal(mayCreatePullRequest("github_create_pull_request", {}), true);
  assert.equal(mayCreatePullRequest("read", { filePath: "x" }), false);
});

test("the gate is asked as the opencode host, with the call as JSON", () => {
  let seen;
  const run = (program, args, options) => {
    seen = { program, args, input: JSON.parse(options.input) };
    return { status: 0, stdout: "" };
  };
  assert.equal(gateReason("/gate.py", { tool: "bash", args: { command: "gh pr create" }, directory: "/repo" }, run), null);
  assert.deepEqual(seen, {
    program: "python3",
    args: ["/gate.py", "--host", "opencode"],
    input: { tool: "bash", args: { command: "gh pr create" }, directory: "/repo" },
  });
});

test("a deny becomes the reason; anything else lets the call proceed", () => {
  const answer = (result) => gateReason("/gate.py", {}, () => result);
  assert.equal(answer({ status: 0, stdout: '{"permission": "deny", "reason": "run the preflight"}' }), "run the preflight");
  assert.equal(answer({ status: 0, stdout: "" }), null);
  assert.equal(answer({ status: 0, stdout: "not json" }), null);
  assert.equal(answer({ status: 1, stdout: '{"permission": "deny", "reason": "x"}' }), null);
  assert.equal(answer({ error: new Error("python3 not found") }), null);
});
