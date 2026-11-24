// The opencode plugin's logic, kept apart from index.js so that it can be tested
// without opencode, and so that opencode sees only one exported plugin.
//
// The plugin reads the repository in place: each plugin directory's skills/ and
// commands/ are registered from where they are, and the pull request gate is the
// same Python script that Claude Code, Codex and Cursor run.

import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { basename, join } from "node:path";

// A cheap test that runs before the gate, so that ordinary bash calls do not
// start Python. It must accept every command the gate treats as pull request
// creation; tests/test_opencode_plugin.py holds the two in agreement.
const MAY_CREATE_PULL_REQUEST = /\bgh\b[\s\S]*\bpr\s+(?:create|new)\b/;
const PULL_REQUEST_TOOL = /create_pull_request$/;

export function pluginNames(root) {
  const plugins = join(root, "plugins");
  return readdirSync(plugins)
    .filter((name) => statSync(join(plugins, name)).isDirectory())
    .sort();
}

/** All plugins, or the ones named in the `plugins` option, in repository order. */
export function selectPlugins(available, options) {
  const wanted = options?.plugins;
  if (!Array.isArray(wanted)) return available;
  return available.filter((name) => wanted.includes(name));
}

/** A Claude Code command file as an opencode command: its description and its body. */
export function parseCommand(text) {
  const normalised = text.replace(/\r\n/g, "\n");
  const match = /^---\n([\s\S]*?)\n---\n?([\s\S]*)$/.exec(normalised);
  if (!match) return { description: "", template: normalised.trim() };
  const description = /^description:\s*(.*)$/m.exec(match[1])?.[1].trim() ?? "";
  return { description, template: match[2].trim() };
}

export function commandsOf(root, plugin) {
  const directory = join(root, "plugins", plugin, "commands");
  if (!existsSync(directory)) return {};
  return Object.fromEntries(
    readdirSync(directory)
      .filter((file) => file.endsWith(".md"))
      .sort()
      .map((file) => [basename(file, ".md"), parseCommand(readFileSync(join(directory, file), "utf8"))]),
  );
}

export function skillDirectories(root, plugins) {
  return plugins.map((plugin) => join(root, "plugins", plugin, "skills")).filter((path) => existsSync(path));
}

/**
 * Adds skill directories to the config. opencode 1.19 reads `skills.paths`; its
 * documentation describes a list, so a list already in the config is extended.
 */
export function addSkillPaths(config, paths) {
  if (Array.isArray(config.skills)) {
    config.skills = [...config.skills, ...paths];
    return;
  }
  const existing = config.skills ?? {};
  config.skills = { ...existing, paths: [...(existing.paths ?? []), ...paths] };
}

/** Registers the commands, leaving any command the user defined under the same name alone. */
export function addCommands(config, commands) {
  config.command = { ...commands, ...(config.command ?? {}) };
}

export function mayCreatePullRequest(tool, args) {
  if (tool === "bash") return MAY_CREATE_PULL_REQUEST.test(String(args?.command ?? ""));
  return PULL_REQUEST_TOOL.test(tool);
}

/**
 * Asks the gate about a tool call. Returns the reason to deny it, or null to let
 * it proceed. Like the gate itself, this fails open: without Python, or when the
 * gate errors, the call proceeds.
 */
export function gateReason(gate, payload, run = spawnSync) {
  const result = run("python3", [gate, "--host", "opencode"], {
    input: JSON.stringify(payload),
    encoding: "utf8",
    timeout: 15000,
  });
  if (result.error || result.status !== 0 || !result.stdout?.trim()) return null;
  try {
    const answer = JSON.parse(result.stdout);
    return answer.permission === "deny" ? String(answer.reason) : null;
  } catch {
    return null;
  }
}
