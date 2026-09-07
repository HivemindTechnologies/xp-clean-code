#!/usr/bin/env python3
"""Check cross-host plugin manifest names and versions for drift."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_NAMES = ("xp-clean-code", "pr-validation")
MANIFESTS = {
    "Claude Code": ".claude-plugin/plugin.json",
    "Cursor": ".cursor-plugin/plugin.json",
    "Codex": ".codex-plugin/plugin.json",
}


def load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as manifest_file:
        return json.load(manifest_file)


def validate_plugin(plugin_name: str) -> list[str]:
    errors: list[str] = []
    versions: dict[str, object] = {}
    plugin_root = REPOSITORY_ROOT / "plugins" / plugin_name

    for host, relative_path in MANIFESTS.items():
        manifest_path = plugin_root / relative_path
        try:
            manifest = load_json(manifest_path)
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{manifest_path}: {error}")
            continue

        if manifest.get("name") != plugin_name:
            errors.append(
                f"{manifest_path}: name must be {plugin_name!r}, "
                f"found {manifest.get('name')!r}"
            )
        versions[host] = manifest.get("version")

    if len(set(versions.values())) > 1:
        rendered_versions = ", ".join(
            f"{host}={version!r}" for host, version in versions.items()
        )
        errors.append(f"{plugin_name}: manifest versions differ: {rendered_versions}")

    return errors


def validate_codex_marketplace() -> list[str]:
    marketplace_path = REPOSITORY_ROOT / ".agents/plugins/marketplace.json"
    try:
        marketplace = load_json(marketplace_path)
    except (OSError, json.JSONDecodeError) as error:
        return [f"{marketplace_path}: {error}"]

    entries = marketplace.get("plugins")
    if not isinstance(entries, list):
        return [f"{marketplace_path}: plugins must be an array"]

    errors: list[str] = []
    entries_by_name = {
        entry.get("name"): entry for entry in entries if isinstance(entry, dict)
    }
    for plugin_name in PLUGIN_NAMES:
        entry = entries_by_name.get(plugin_name)
        if entry is None:
            errors.append(f"{marketplace_path}: missing plugin {plugin_name!r}")
            continue

        expected_path = f"./plugins/{plugin_name}"
        source = entry.get("source")
        actual_path = source.get("path") if isinstance(source, dict) else None
        if actual_path != expected_path:
            errors.append(
                f"{marketplace_path}: {plugin_name!r} must use source path "
                f"{expected_path!r}, found {actual_path!r}"
            )

    return errors


def main() -> int:
    errors = [
        error
        for plugin_name in PLUGIN_NAMES
        for error in validate_plugin(plugin_name)
    ]
    errors.extend(validate_codex_marketplace())

    if errors:
        print("Manifest validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Manifest validation passed for Claude Code, Cursor, and Codex.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
