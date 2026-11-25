// The opencode plugin for this repository. Install it with
//   opencode plugin -g 'git+https://github.com/HivemindTechnologies/xp-clean-code.git#main'
// It registers every plugin's skills and commands and, with pr-validation, the
// pull request preflight gate. Pass ["<spec>", {"plugins": ["pr-validation"]}]
// in the opencode config to register only some of the plugins.

import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  addCommands,
  addSkillPaths,
  commandsOf,
  gateReason,
  mayCreatePullRequest,
  pluginNames,
  selectPlugins,
  skillDirectories,
} from "./core.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const GATE = join(ROOT, "plugins", "pr-validation", "hooks", "pr_preflight_gate.py");

const server = async (input, options) => {
  const plugins = selectPlugins(pluginNames(ROOT), options);
  const hooks = {
    config: async (config) => {
      addSkillPaths(config, skillDirectories(ROOT, plugins));
      addCommands(config, Object.assign({}, ...plugins.map((plugin) => commandsOf(ROOT, plugin))));
    },
  };
  if (plugins.includes("pr-validation")) {
    hooks["tool.execute.before"] = async ({ tool }, output) => {
      if (!mayCreatePullRequest(tool, output.args)) return;
      const reason = gateReason(GATE, { tool, args: output.args ?? {}, directory: input.directory });
      if (reason) throw new Error(reason);
    };
  }
  return hooks;
};

export default { id: "xp-clean-code", server };
