#!/usr/bin/env python3
"""Run deterministic tools against a branch's changes for the pr-validation preflight.

The runner gathers evidence for the five analyses; it does not replace them.
It never installs a tool, never runs a project's test suite, and never changes
the working tree. A tool that is missing is reported as NOT_RUN with the reason.

Checks:
  secrets      gitleaks over the commits on the branch
  coverage     diff-cover over coverage reports the project already produced
  complexity   lizard cyclomatic complexity of changed functions
  duplication  jscpd clones that touch changed lines
  purity       semgrep impurity signals (rules shipped with this skill)
  project:*    the project's own checks: pre-commit, or detected per language

Usage:
  preflight_tools.py [--base REF] [--repo DIR] [--plan] [--include-slow]
                     [--only ID[,ID...]] [--format json|markdown]

--plan prints what would run, and why anything would not, without running it.
Checks marked slow (builds, type checks, pre-commit) run only with
--include-slow; the skill asks the user before passing it.

Exit status: 0 when no required check failed, 1 when one did, 2 on a runner
error. Configuration lives in .pr-preflight.toml at the repository root.
"""

from __future__ import annotations

import csv
import fnmatch
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - depends on interpreter
    tomllib = None  # type: ignore[assignment]

CONFIG_FILE = ".pr-preflight.toml"
RULES_DIR = Path(__file__).resolve().parent.parent / "rules" / "purity"
MAX_FINDINGS = 50
OUTPUT_TAIL_LINES = 40
TIMEOUT_SECONDS = {"fast": 300, "slow": 1800}

LANGUAGE_EXTENSIONS: Mapping[str, str] = {
    ".py": "python", ".pyi": "python",
    ".scala": "scala", ".sc": "scala",
    ".rs": "rust",
    ".java": "java",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
    ".kt": "kotlin", ".kts": "kotlin",
    ".go": "go",
    ".c": "cpp", ".h": "cpp", ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp",
    ".hh": "cpp", ".hpp": "cpp", ".hxx": "cpp",
}
FIRST_CLASS = ("scala", "python", "rust", "java", "typescript")
JSCPD_FORMATS: Mapping[str, Sequence[str]] = {
    "python": ("python",), "scala": ("scala",), "rust": ("rust",), "java": ("java",),
    "typescript": ("typescript", "tsx"), "kotlin": ("kotlin",), "go": ("go",),
    "cpp": ("cpp", "c"),
}
SEARCH_EXCLUDES = ("**/node_modules/**", "**/target/**", "**/build/**", "**/dist/**",
                   "**/.git/**", "**/vendor/**", "**/.venv/**")
CORE_CHECKS = ("secrets", "coverage", "complexity", "duplication", "purity")
COVERAGE_CANDIDATES = (
    "coverage.xml", "cobertura.xml", "lcov.info", "coverage/lcov.info",
    "coverage/cobertura-coverage.xml", "target/site/jacoco/jacoco.xml",
    "build/reports/jacoco/test/jacocoTestReport.xml", "build/reports/kover/report.xml",
    "target/cobertura.xml",
)


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    required: frozenset[str] = frozenset()
    disabled: frozenset[str] = frozenset()
    coverage_reports: tuple[str, ...] = ()
    fail_under: Optional[float] = None
    max_ccn: int = 10
    min_tokens: int = 50
    domain_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Directory:
    """Marker files present in one directory, with the text of the build files."""

    files: frozenset[str] = frozenset()
    texts: Mapping[str, str] = field(default_factory=dict)

    def has(self, *names: str) -> bool:
        return any(name in self.files for name in names)

    def mentions(self, needle: str) -> bool:
        return any(needle in text for text in self.texts.values())


@dataclass(frozen=True)
class Snapshot:
    """Everything planning needs to know about the repository, read at the boundary."""

    merge_base: str
    changed: Mapping[str, frozenset[int]]
    directories: Mapping[str, Directory]  # "" is the repository root
    tools: frozenset[str]
    coverage_reports: tuple[str, ...]  # existing reports: configured ones, else well-known paths


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    rule: str
    message: str


@dataclass(frozen=True)
class Planned:
    id: str
    tool: str
    argv: tuple[str, ...]
    cwd: str  # relative to the repository root
    cost: str  # "fast" or "slow"
    kind: str  # selects the parser
    required: bool
    in_worktree: bool = False


@dataclass(frozen=True)
class Skipped:
    id: str
    tool: str
    required: bool
    reason: str
    cost: str = "fast"


@dataclass(frozen=True)
class Result:
    id: str
    tool: str
    required: bool
    cost: str
    status: str  # PASS | FAIL | NOT_RUN | SKIPPED_SLOW | ERROR
    reason: str = ""
    command: str = ""
    findings: tuple[Finding, ...] = ()
    total_findings: int = 0
    output_tail: str = ""


# ---------------------------------------------------------------------------
# Pure core: diffs, languages, configuration
# ---------------------------------------------------------------------------

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def parse_changed_lines(diff: str) -> dict[str, frozenset[int]]:
    """Map each file in a `git diff --unified=0` to the line numbers it adds or changes."""
    changed: dict[str, set[int]] = {}
    current: Optional[str] = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            current = target[2:] if target.startswith("b/") else None
            if current is not None:
                changed.setdefault(current, set())
            continue
        match = HUNK.match(line)
        if match and current is not None:
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1
            changed[current].update(range(start, start + count))
    return {path: frozenset(lines) for path, lines in changed.items()}


def language_of(path: str) -> Optional[str]:
    return LANGUAGE_EXTENSIONS.get(Path(path).suffix.lower())


def group_by_language(paths: Iterable[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for path in sorted(paths):
        language = language_of(path)
        if language is not None:
            groups.setdefault(language, []).append(path)
    return groups


def parse_config(data: Mapping[str, object]) -> tuple[Config, list[str]]:
    warnings: list[str] = []
    known = {"checks", "coverage", "complexity", "duplication", "purity"}
    for key in data:
        if key not in known:
            warnings.append(f"unknown section [{key}] ignored")

    def section(name: str) -> Mapping[str, object]:
        value = data.get(name, {})
        if isinstance(value, dict):
            return value
        warnings.append(f"[{name}] must be a table; ignored")
        return {}

    def strings(table: Mapping[str, object], key: str) -> tuple[str, ...]:
        value = table.get(key, [])
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return tuple(value)
        warnings.append(f"{key} must be a list of strings; ignored")
        return ()

    def number(table: Mapping[str, object], key: str, default: Optional[float]) -> Optional[float]:
        value = table.get(key, default)
        if value is None or (isinstance(value, (int, float)) and not isinstance(value, bool)):
            return value
        warnings.append(f"{key} must be a number; ignored")
        return default

    checks, coverage = section("checks"), section("coverage")
    complexity, duplication, purity = section("complexity"), section("duplication"), section("purity")
    config = Config(
        required=frozenset(strings(checks, "required")),
        disabled=frozenset(strings(checks, "disabled")),
        coverage_reports=strings(coverage, "reports"),
        fail_under=number(coverage, "fail_under", None),
        max_ccn=int(number(complexity, "max_ccn", 10) or 10),
        min_tokens=int(number(duplication, "min_tokens", 50) or 50),
        domain_paths=strings(purity, "domain_paths"),
    )
    if "purity" in config.required and not config.domain_paths:
        warnings.append(
            "purity is required but purity.domain_paths is empty; impurity at the boundary "
            "is legitimate, so purity stays advisory until domain paths are named"
        )
        config = replace(config, required=config.required - {"purity"})
    return config, warnings


def is_required(check_id: str, config: Config) -> bool:
    return check_id in config.required or (
        check_id.startswith("project:") and "project" in config.required
    )


def is_disabled(check_id: str, config: Config) -> bool:
    return check_id in config.disabled or (
        check_id.startswith("project:") and "project" in config.disabled
    )


def touches(changed: Mapping[str, frozenset[int]], path: str, start: int, end: int) -> bool:
    lines = changed.get(path)
    return bool(lines) and any(start <= line <= end for line in lines)  # type: ignore[union-attr]


def in_domain(path: str, domain_paths: Sequence[str]) -> bool:
    return any(path.startswith(pattern) or fnmatch.fnmatch(path, pattern) for pattern in domain_paths)


def ancestors(path: str) -> list[str]:
    """Directories from the file's own up to the repository root (""), nearest first."""
    parts = Path(path).parent.parts
    return ["/".join(parts[:index]) for index in range(len(parts), -1, -1)]


def nearest_root(path: str, directories: Mapping[str, Directory], *markers: str) -> Optional[str]:
    for directory in ancestors(path):
        if directories.get(directory, Directory()).has(*markers):
            return directory
    return None


def relative_to(root: str, path: str) -> str:
    return path[len(root) + 1:] if root else path


# ---------------------------------------------------------------------------
# Pure core: planning
# ---------------------------------------------------------------------------


def plan_core(snapshot: Snapshot, config: Config) -> list[Planned | Skipped]:
    files = sorted(snapshot.changed)
    groups = group_by_language(files)
    plans: list[Planned | Skipped] = []

    def add(check: Planned | Skipped) -> None:
        if is_disabled(check.id, config):
            plans.append(Skipped(check.id, check.tool, False, "disabled in .pr-preflight.toml", check.cost))
        else:
            plans.append(check)

    def missing(check_id: str, tool: str) -> Skipped:
        return Skipped(check_id, tool, is_required(check_id, config), f"{tool} is not installed")

    # secrets
    if "gitleaks" not in snapshot.tools:
        add(missing("secrets", "gitleaks"))
    else:
        add(Planned("secrets", "gitleaks", (
            "gitleaks", "git", f"--log-opts={snapshot.merge_base}..HEAD", "--report-format", "json",
            "--report-path", "{report}", "--redact", "--no-banner", "--exit-code", "0", ".",
        ), "", "fast", "gitleaks", is_required("secrets", config)))

    # coverage
    reports = snapshot.coverage_reports
    if "diff-cover" not in snapshot.tools:
        add(missing("coverage", "diff-cover"))
    elif not reports:
        add(Skipped("coverage", "diff-cover", is_required("coverage", config),
                    "none of the reports under [coverage] reports exists"
                    if config.coverage_reports else
                    "no coverage report found; produce one with the project's coverage tool "
                    "or list it under [coverage] reports"))
    else:
        add(Planned("coverage", "diff-cover", (
            "diff-cover", *reports, f"--compare-branch={snapshot.merge_base}",
            "--ignore-staged", "--ignore-unstaged", "--format", "json:{report}", "-q",
        ), "", "fast", "diff-cover", is_required("coverage", config)))

    # complexity
    if not groups:
        add(Skipped("complexity", "lizard", is_required("complexity", config), "no changed source files"))
    elif "lizard" not in snapshot.tools:
        add(missing("complexity", "lizard"))
    else:
        sources = [path for language in sorted(groups) for path in groups[language]]
        add(Planned("complexity", "lizard", ("lizard", "--csv", *sources), "", "fast", "lizard",
                    is_required("complexity", config)))

    # duplication
    if not groups:
        add(Skipped("duplication", "jscpd", is_required("duplication", config), "no changed source files"))
    elif "jscpd" not in snapshot.tools:
        add(missing("duplication", "jscpd"))
    else:
        formats = ",".join(sorted({fmt for language in groups for fmt in JSCPD_FORMATS[language]}))
        add(Planned("duplication", "jscpd", (
            "jscpd", "--silent", "--gitignore", "--reporters", "json", "--output", "{report_dir}",
            "--min-tokens", str(config.min_tokens), "--format", formats,
            "--ignore", ",".join(SEARCH_EXCLUDES), ".",
        ), "", "fast", "jscpd", is_required("duplication", config)))

    # purity
    purity_files = [path for language in FIRST_CLASS for path in groups.get(language, [])]
    if config.domain_paths:
        purity_files = [path for path in purity_files if in_domain(path, config.domain_paths)]
    if not purity_files:
        add(Skipped("purity", "semgrep", is_required("purity", config),
                    "no changed files in Scala, Python, Rust, Java or TypeScript"
                    + (" under purity.domain_paths" if config.domain_paths else "")))
    elif "semgrep" not in snapshot.tools:
        add(missing("purity", "semgrep"))
    else:
        add(Planned("purity", "semgrep", (
            "semgrep", "scan", "--config", str(RULES_DIR), "--json", "--metrics=off",
            "--disable-version-check", "--quiet", *purity_files,
        ), "", "fast", "semgrep", is_required("purity", config)))

    return plans


@dataclass(frozen=True)
class NativeCheck:
    """A project check that runs only where the project has configured its tool."""

    id: str
    language: str
    tool: str
    cost: str
    markers: tuple[str, ...]  # build files that define the project root
    configured: Callable[[Directory, Mapping[str, Directory], str], bool]
    argv: Callable[[str, Sequence[str], str], tuple[str, ...]]  # (root, files, merge_base)
    kind: str = "exit"  # "exit": non-zero fails; "listing": any output fails


def directory_and_parents(directory: str) -> list[str]:
    return [""] if directory == "" else ancestors(directory + "/_")


def _has_up(names: Sequence[str]) -> Callable[[Directory, Mapping[str, Directory], str], bool]:
    """Configured when any of `names` exists in the project root or one of its parents."""

    def check(_: Directory, directories: Mapping[str, Directory], root: str) -> bool:
        return any(directories.get(directory, Directory()).has(*names)
                   for directory in directory_and_parents(root))

    return check


def _python_tool(tool: str, files: Sequence[str]) -> Callable[[Directory, Mapping[str, Directory], str], bool]:
    def check(directory: Directory, _: Mapping[str, Directory], __: str) -> bool:
        return directory.has(*files) or directory.mentions(f"[tool.{tool}")

    return check


def _node_bin(name: str, config_files: Sequence[str] = ()) -> Callable[[Directory, Mapping[str, Directory], str], bool]:
    def check(directory: Directory, _: Mapping[str, Directory], __: str) -> bool:
        has_config = not config_files or directory.has(*config_files)
        return has_config and directory.has(f"node_modules/.bin/{name}")

    return check


def _mentions(*needles: str) -> Callable[[Directory, Mapping[str, Directory], str], bool]:
    return lambda directory, _, __: any(directory.mentions(needle) for needle in needles)


ESLINT_CONFIGS = ("eslint.config.js", "eslint.config.mjs", "eslint.config.cjs", "eslint.config.ts",
                  ".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json", ".eslintrc.yml")
GRADLE_FILES = ("build.gradle", "build.gradle.kts")

NATIVE_CHECKS: tuple[NativeCheck, ...] = (
    NativeCheck("project:ruff-check", "python", "ruff", "fast", ("pyproject.toml", "ruff.toml", ".ruff.toml", "setup.cfg"),
                _python_tool("ruff", ("ruff.toml", ".ruff.toml")),
                lambda root, files, mb: ("ruff", "check", "--output-format=concise", *files)),
    NativeCheck("project:ruff-format", "python", "ruff", "fast", ("pyproject.toml", "ruff.toml", ".ruff.toml", "setup.cfg"),
                _python_tool("ruff", ("ruff.toml", ".ruff.toml")),
                lambda root, files, mb: ("ruff", "format", "--check", *files)),
    NativeCheck("project:mypy", "python", "mypy", "slow", ("pyproject.toml", "mypy.ini", ".mypy.ini", "setup.cfg"),
                _python_tool("mypy", ("mypy.ini", ".mypy.ini")),
                lambda root, files, mb: ("mypy", *files)),
    NativeCheck("project:pyright", "python", "pyright", "slow", ("pyproject.toml", "pyrightconfig.json"),
                _python_tool("pyright", ("pyrightconfig.json",)),
                lambda root, files, mb: ("pyright", *files)),
    NativeCheck("project:cargo-fmt", "rust", "cargo", "fast", ("Cargo.toml",),
                lambda directory, _, __: True,
                lambda root, files, mb: ("cargo", "fmt", "--check")),
    NativeCheck("project:cargo-clippy", "rust", "cargo", "slow", ("Cargo.toml",),
                lambda directory, _, __: True,
                lambda root, files, mb: ("cargo", "clippy", "--all-targets", "--quiet")),
    NativeCheck("project:scalafmt", "scala", "sbt", "slow", ("build.sbt",),
                _has_up((".scalafmt.conf",)),
                lambda root, files, mb: ("sbt", "-batch", "scalafmtCheckAll")),
    NativeCheck("project:scalafix", "scala", "sbt", "slow", ("build.sbt",),
                _has_up((".scalafix.conf",)),
                lambda root, files, mb: ("sbt", "-batch", "scalafixAll --check")),
    NativeCheck("project:spotless-gradle", "jvm", "gradle", "slow", GRADLE_FILES,
                _mentions("spotless"), lambda root, files, mb: ("./gradlew", "spotlessCheck", "--quiet")),
    NativeCheck("project:checkstyle-gradle", "jvm", "gradle", "slow", GRADLE_FILES,
                _mentions("checkstyle"), lambda root, files, mb: ("./gradlew", "checkstyleMain", "--quiet")),
    NativeCheck("project:detekt", "jvm", "gradle", "slow", GRADLE_FILES,
                _mentions("detekt"), lambda root, files, mb: ("./gradlew", "detekt", "--quiet")),
    NativeCheck("project:ktlint", "jvm", "gradle", "slow", GRADLE_FILES,
                _mentions("ktlint"), lambda root, files, mb: ("./gradlew", "ktlintCheck", "--quiet")),
    NativeCheck("project:spotless-maven", "jvm", "mvn", "slow", ("pom.xml",),
                _mentions("spotless-maven-plugin"), lambda root, files, mb: ("mvn", "-q", "spotless:check")),
    NativeCheck("project:checkstyle-maven", "jvm", "mvn", "slow", ("pom.xml",),
                _mentions("maven-checkstyle-plugin"), lambda root, files, mb: ("mvn", "-q", "checkstyle:check")),
    NativeCheck("project:eslint", "typescript", "eslint", "fast", ("package.json",),
                _node_bin("eslint", ESLINT_CONFIGS),
                lambda root, files, mb: ("node_modules/.bin/eslint", *files)),
    NativeCheck("project:biome", "typescript", "biome", "fast", ("package.json",),
                _node_bin("biome", ("biome.json", "biome.jsonc")),
                lambda root, files, mb: ("node_modules/.bin/biome", "ci", *files)),
    NativeCheck("project:tsc", "typescript", "tsc", "slow", ("package.json",),
                _node_bin("tsc", ("tsconfig.json",)),
                lambda root, files, mb: ("node_modules/.bin/tsc", "--noEmit")),
    NativeCheck("project:gofmt", "go", "gofmt", "fast", ("go.mod",),
                lambda directory, _, __: True,
                lambda root, files, mb: ("gofmt", "-l", *files), kind="listing"),
    NativeCheck("project:go-vet", "go", "go", "slow", ("go.mod",),
                lambda directory, _, __: True,
                lambda root, files, mb: ("go", "vet", "./...")),
    NativeCheck("project:golangci-lint", "go", "golangci-lint", "slow", ("go.mod",),
                _has_up((".golangci.yml", ".golangci.yaml", ".golangci.toml", ".golangci.json")),
                lambda root, files, mb: ("golangci-lint", "run", f"--new-from-rev={mb}")),
    NativeCheck("project:clang-format", "cpp", "clang-format", "fast", ("CMakeLists.txt", "Makefile", "meson.build", ".clang-format"),
                _has_up((".clang-format",)),
                lambda root, files, mb: ("clang-format", "--dry-run", "--Werror", *files)),
)

TOOLS_IN_PROJECT = {"eslint", "biome", "tsc", "gradle"}  # resolved inside the project, not on PATH


def plan_project(snapshot: Snapshot, config: Config) -> list[Planned | Skipped]:
    root_dir = snapshot.directories.get("", Directory())
    if root_dir.has(".pre-commit-config.yaml"):
        check_id = "project:pre-commit"
        if is_disabled(check_id, config):
            return [Skipped(check_id, "pre-commit", False, "disabled in .pr-preflight.toml", "slow")]
        if "pre-commit" not in snapshot.tools:
            return [Skipped(check_id, "pre-commit", is_required(check_id, config), "pre-commit is not installed", "slow")]
        # pre-commit hooks may rewrite files, so it runs in a disposable worktree at HEAD.
        return [Planned(check_id, "pre-commit", (
            "pre-commit", "run", "--from-ref", snapshot.merge_base, "--to-ref", "HEAD", "--show-diff-on-failure",
        ), "", "slow", "exit", is_required(check_id, config), in_worktree=True)]

    plans: list[Planned | Skipped] = []
    groups = group_by_language(snapshot.changed)
    for check in NATIVE_CHECKS:
        # sbt covers Scala; Gradle and Maven checks cover Java and Kotlin.
        languages = ("java", "kotlin") if check.language == "jvm" else (check.language,)
        files = [path for language in languages for path in groups.get(language, [])]
        by_root: dict[str, list[str]] = {}
        for path in files:
            root = nearest_root(path, snapshot.directories, *check.markers)
            if root is not None:
                by_root.setdefault(root, []).append(path)
        for root, root_files in sorted(by_root.items()):
            directory = snapshot.directories.get(root, Directory())
            if not check.configured(directory, snapshot.directories, root):
                continue
            check_id = check.id if root == "" else f"{check.id}@{root}"
            required = is_required(check.id, config)
            if is_disabled(check.id, config):
                plans.append(Skipped(check_id, check.tool, False, "disabled in .pr-preflight.toml", check.cost))
                continue
            available = (
                directory.has("gradlew") if check.tool == "gradle"
                else check.tool in TOOLS_IN_PROJECT or check.tool in snapshot.tools
            )
            if not available:
                reason = "no ./gradlew wrapper" if check.tool == "gradle" else f"{check.tool} is not installed"
                plans.append(Skipped(check_id, check.tool, required, reason, check.cost))
                continue
            relative_files = [relative_to(root, path) for path in root_files]
            plans.append(Planned(check_id, check.tool, check.argv(root, relative_files, snapshot.merge_base),
                                 root, check.cost, check.kind, required))
    return plans


def plan(snapshot: Snapshot, config: Config, only: frozenset[str] = frozenset()) -> list[Planned | Skipped]:
    checks = plan_core(snapshot, config) + plan_project(snapshot, config)
    if only:
        checks = [check for check in checks
                  if check.id in only or check.id.split("@")[0] in only
                  or (check.id.startswith("project:") and "project" in only)]
    return checks


# ---------------------------------------------------------------------------
# Pure core: parsing tool output
# ---------------------------------------------------------------------------


def parse_gitleaks(report: str) -> list[Finding]:
    leaks = json.loads(report or "[]") or []
    return [
        Finding(str(leak.get("File", "")), int(leak.get("StartLine", 0)), str(leak.get("RuleID", "")),
                f"{leak.get('Description', 'secret')} in commit {str(leak.get('Commit', ''))[:8]}")
        for leak in leaks
    ]


def parse_diff_cover(report: str) -> tuple[list[Finding], Optional[float]]:
    data = json.loads(report)
    findings = [
        Finding(path, line, "uncovered", "changed line not executed by any test")
        for path, stats in sorted(data.get("src_stats", {}).items())
        for line in stats.get("violation_lines", [])
    ]
    total = data.get("total_percent_covered")
    return findings, float(total) if isinstance(total, (int, float)) else None


def parse_lizard(output: str, changed: Mapping[str, frozenset[int]], max_ccn: int) -> list[Finding]:
    findings = []
    for row in csv.reader(io.StringIO(output)):
        if len(row) < 11 or not row[1].isdigit():
            continue
        ccn, path, function, start, end = int(row[1]), row[6], row[7], int(row[9]), int(row[10])
        path = os.path.normpath(path)
        if ccn > max_ccn and touches(changed, path, start, end):
            findings.append(Finding(path, start, "complexity",
                                    f"{function} has cyclomatic complexity {ccn} (limit {max_ccn})"))
    return findings


def parse_jscpd(report: str, changed: Mapping[str, frozenset[int]]) -> list[Finding]:
    findings = []
    for clone in json.loads(report).get("duplicates", []):
        first, second = clone.get("firstFile", {}), clone.get("secondFile", {})
        for this, other in ((first, second), (second, first)):
            path = os.path.normpath(str(this.get("name", "")))
            start, end = int(this.get("start", 0)), int(this.get("end", 0))
            if touches(changed, path, start, end):
                findings.append(Finding(
                    path, start, "duplication",
                    f"lines {start}-{end} duplicate {os.path.normpath(str(other.get('name', '')))}:"
                    f"{other.get('start')}-{other.get('end')} ({clone.get('lines')} lines)"))
                break
    return findings


def parse_semgrep(output: str, changed: Mapping[str, frozenset[int]]) -> tuple[list[Finding], list[str]]:
    data = json.loads(output)
    findings = []
    for result in data.get("results", []):
        path = os.path.normpath(str(result.get("path", "")))
        line = int(result.get("start", {}).get("line", 0))
        end = int(result.get("end", {}).get("line", line))
        if touches(changed, path, line, end):
            rule = str(result.get("check_id", "")).rsplit(".", 1)[-1]
            findings.append(Finding(path, line, rule, str(result.get("extra", {}).get("message", ""))))
    errors = [str(error.get("message", error)) for error in data.get("errors", [])]
    return findings, errors


def tail(text: str, lines: int = OUTPUT_TAIL_LINES) -> str:
    return "\n".join(text.rstrip().splitlines()[-lines:])


def judge(check: Planned, returncode: int, stdout: str, stderr: str, report: Optional[str],
          changed: Mapping[str, frozenset[int]], config: Config) -> Result:
    """Turn one tool run into a result. Pure: the run's outputs are its inputs."""
    base = Result(check.id, check.tool, check.required, check.cost, "PASS", command=" ".join(check.argv))
    combined = tail("\n".join(part for part in (stdout, stderr) if part))
    try:
        if check.kind == "gitleaks":
            if returncode != 0:
                return replace(base, status="ERROR", reason=f"gitleaks exited {returncode}", output_tail=combined)
            findings = parse_gitleaks(report or "[]")
            return with_findings(base, findings)
        if check.kind == "diff-cover":
            if returncode != 0 or report is None:
                return replace(base, status="ERROR", reason=f"diff-cover exited {returncode}", output_tail=combined)
            findings, total = parse_diff_cover(report)
            result = with_findings(base, findings)
            if config.fail_under is not None and total is not None:
                status = "FAIL" if total < config.fail_under else "PASS"
                return replace(result, status=status,
                               reason=f"{total:g}% of changed lines covered (fail_under {config.fail_under:g})")
            return replace(result, reason=f"{total:g}% of changed lines covered" if total is not None else "")
        if check.kind == "lizard":
            if returncode != 0:
                return replace(base, status="ERROR", reason=f"lizard exited {returncode}", output_tail=combined)
            return with_findings(base, parse_lizard(stdout, changed, config.max_ccn))
        if check.kind == "jscpd":
            if returncode != 0 or report is None:
                return replace(base, status="ERROR", reason=f"jscpd exited {returncode}", output_tail=combined)
            return with_findings(base, parse_jscpd(report, changed))
        if check.kind == "semgrep":
            if returncode not in (0, 1):
                return replace(base, status="ERROR", reason=f"semgrep exited {returncode}", output_tail=combined)
            findings, errors = parse_semgrep(stdout, changed)
            result = with_findings(base, findings)
            return replace(result, reason="; ".join(errors[:3])) if errors else result
        if check.kind == "listing":
            listed = [line for line in stdout.splitlines() if line.strip()]
            findings = [Finding(path, 0, check.tool, "not formatted") for path in listed]
            if returncode != 0 and not listed:
                return replace(base, status="ERROR", reason=f"{check.tool} exited {returncode}", output_tail=combined)
            return with_findings(base, findings)
        # "exit": the project's own check decides
        if returncode == 0:
            return base
        return replace(base, status="FAIL", reason=f"{check.tool} exited {returncode}", output_tail=combined)
    except (ValueError, KeyError, TypeError) as error:
        return replace(base, status="ERROR", reason=f"could not read {check.tool} output: {error}",
                       output_tail=combined)


def with_findings(result: Result, findings: Sequence[Finding]) -> Result:
    return replace(result, status="FAIL" if findings else "PASS",
                   findings=tuple(findings[:MAX_FINDINGS]), total_findings=len(findings))


def skipped_result(check: Skipped) -> Result:
    return Result(check.id, check.tool, check.required, check.cost, "NOT_RUN", reason=check.reason)


def slow_result(check: Planned) -> Result:
    return Result(check.id, check.tool, check.required, check.cost, "SKIPPED_SLOW",
                  reason="slow check; rerun with --include-slow once the user agrees",
                  command=" ".join(check.argv))


def summarise(results: Sequence[Result]) -> dict[str, object]:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    required_failed = [result.id for result in results
                       if result.required and result.status in ("FAIL", "ERROR", "NOT_RUN", "SKIPPED_SLOW")]
    return {"counts": counts, "required_failed": required_failed}


def render_markdown(report: Mapping[str, object]) -> str:
    lines = [
        f"**Commits:** `{str(report['merge_base'])[:8]}..{str(report['head'])[:8]}` "
        f"against `{report['base']}`",
        "",
        "| Check | Tool | Required | Status | Detail |",
        "|---|---|---|---|---|",
    ]
    results = report["checks"]
    assert isinstance(results, list)
    for result in results:
        detail = result["reason"] or (f"{result['total_findings']} finding(s)" if result["total_findings"] else "")
        lines.append(f"| {result['id']} | {result['tool']} | {'yes' if result['required'] else 'no'} "
                     f"| {result['status']} | {detail} |")
    for result in results:
        if result["findings"]:
            lines += ["", f"**{result['id']}** ({result['total_findings']} finding(s)"
                      + (f", first {len(result['findings'])} shown" if result['total_findings'] > len(result['findings']) else "")
                      + ")", ""]
            lines += [f"- `{finding['file']}:{finding['line']}` {finding['rule']}: {finding['message']}"
                      for finding in result["findings"]]
        elif result["status"] in ("FAIL", "ERROR") and result["output_tail"]:
            lines += ["", f"**{result['id']}** output (last lines):", "", "```", result["output_tail"], "```"]
    notes = report.get("notes")
    if isinstance(notes, list) and notes:
        lines += ["", "**Notes:**"] + [f"- {note}" for note in notes]
    summary = report["summary"]
    assert isinstance(summary, dict)
    failed = summary["required_failed"]
    lines += ["", f"**Required checks failed:** {', '.join(failed) if failed else 'none'}"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------


class RunnerError(Exception):
    pass


def git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(["git", "-C", str(repo), "-c", "core.quotePath=false", *arguments],
                               capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RunnerError(f"git {' '.join(arguments)}: {completed.stderr.strip()}")
    return completed.stdout


def resolve_base(repo: Path, base: Optional[str]) -> str:
    if base:
        for candidate in (f"origin/{base}", base):
            if subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", candidate + "^{commit}"],
                              capture_output=True, check=False).returncode == 0:
                return candidate
        raise RunnerError(f"base {base!r} is neither a local nor an origin branch or commit")
    try:
        return git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
    except RunnerError:
        for candidate in ("origin/main", "origin/master", "main", "master"):
            if subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", candidate],
                              capture_output=True, check=False).returncode == 0:
                return candidate
    raise RunnerError("cannot find the base branch; pass --base")


MARKER_FILES = (
    "pyproject.toml", "setup.cfg", "ruff.toml", ".ruff.toml", "mypy.ini", ".mypy.ini", "pyrightconfig.json",
    "Cargo.toml", "build.sbt", ".scalafmt.conf", ".scalafix.conf", "build.gradle", "build.gradle.kts",
    "gradlew", "pom.xml", "package.json", "tsconfig.json", "biome.json", "biome.jsonc", *ESLINT_CONFIGS,
    "node_modules/.bin/eslint", "node_modules/.bin/biome", "node_modules/.bin/tsc", "go.mod",
    ".golangci.yml", ".golangci.yaml", ".golangci.toml", ".golangci.json", ".clang-format",
    "CMakeLists.txt", "Makefile", "meson.build", ".pre-commit-config.yaml",
)
TEXT_MARKERS = ("pyproject.toml", "setup.cfg", "build.gradle", "build.gradle.kts", "pom.xml")


def read_directories(repo: Path, changed: Iterable[str]) -> dict[str, Directory]:
    directories: dict[str, Directory] = {}
    for path in changed:
        for directory in ancestors(path):
            if directory in directories:
                continue
            absolute = repo / directory
            present = frozenset(name for name in MARKER_FILES if (absolute / name).exists())
            texts = {name: (absolute / name).read_text(encoding="utf-8", errors="replace")
                     for name in TEXT_MARKERS if name in present}
            directories[directory] = Directory(present, texts)
    return directories


def available_tools() -> frozenset[str]:
    names = ("gitleaks", "diff-cover", "lizard", "jscpd", "semgrep", "pre-commit", "ruff", "mypy",
             "pyright", "cargo", "sbt", "mvn", "gofmt", "go", "golangci-lint", "clang-format")
    return frozenset(name for name in names if shutil.which(name))


def load_config(repo: Path) -> tuple[Config, list[str], Optional[str]]:
    path = repo / CONFIG_FILE
    if not path.is_file():
        return Config(), [], None
    if tomllib is None:
        return Config(), [f"{CONFIG_FILE} needs Python 3.11 or later to read; using defaults"], str(path)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return Config(), [f"{CONFIG_FILE} could not be read ({error}); using defaults"], str(path)
    config, warnings = parse_config(data)
    return config, warnings, str(path)


def take_snapshot(repo: Path, base_ref: str, config: Config) -> tuple[Snapshot, str]:
    merge_base = git(repo, "merge-base", base_ref, "HEAD").strip()
    head = git(repo, "rev-parse", "HEAD").strip()
    diff = git(repo, "diff", "--unified=0", "--no-color", "--no-ext-diff", "--diff-filter=ACMR", merge_base, "HEAD")
    changed = parse_changed_lines(diff)
    reports = tuple(report for report in (config.coverage_reports or COVERAGE_CANDIDATES)
                    if (repo / report).is_file())
    return Snapshot(merge_base, changed, read_directories(repo, changed), available_tools(), reports), head


def run_check(repo: Path, check: Planned, changed: Mapping[str, frozenset[int]], config: Config) -> Result:
    with tempfile.TemporaryDirectory(prefix="pr-preflight-") as scratch:
        report_path = Path(scratch) / "report.json"
        report_dir = Path(scratch) / "jscpd"
        argv = [part.replace("{report}", str(report_path)).replace("{report_dir}", str(report_dir))
                for part in check.argv]
        worktree = Path(scratch) / "worktree"
        cwd = repo / check.cwd
        if check.in_worktree:
            git(repo, "worktree", "add", "--quiet", "--detach", str(worktree), "HEAD")
            cwd = worktree / check.cwd
        try:
            completed = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                                       timeout=TIMEOUT_SECONDS[check.cost], check=False)
        except FileNotFoundError:
            return Result(check.id, check.tool, check.required, check.cost, "NOT_RUN",
                          reason=f"{argv[0]} is not installed", command=" ".join(argv))
        except subprocess.TimeoutExpired:
            return Result(check.id, check.tool, check.required, check.cost, "ERROR",
                          reason=f"timed out after {TIMEOUT_SECONDS[check.cost]}s", command=" ".join(argv))
        finally:
            if check.in_worktree:
                subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                               capture_output=True, check=False)
        report_file = report_dir / "jscpd-report.json" if check.kind == "jscpd" else report_path
        report = report_file.read_text(encoding="utf-8") if report_file.is_file() else None
        return judge(check, completed.returncode, completed.stdout, completed.stderr, report, changed, config)


def notes_for(repo: Path, snapshot: Snapshot, config: Config, head_time: int) -> list[str]:
    notes = []
    status = git(repo, "status", "--porcelain", "--untracked-files=no").strip()
    if status:
        notes.append("the working tree has uncommitted changes; checks that read files saw them, "
                     "but the pull request will not contain them")
    for report in snapshot.coverage_reports:
        path = repo / report
        if path.is_file() and path.stat().st_mtime < head_time:
            notes.append(f"coverage report {report} is older than HEAD; regenerate it for an accurate result")
    if snapshot.changed and not group_by_language(snapshot.changed):
        notes.append("no changed files in a supported language; only the secrets check applies")
    return notes


def build_report(repo: Path, base: Optional[str], only: frozenset[str], include_slow: bool,
                 dry_run: bool) -> dict[str, object]:
    toplevel = Path(git(repo, "rev-parse", "--show-toplevel").strip())
    config, warnings, config_path = load_config(toplevel)
    base_ref = resolve_base(toplevel, base)
    snapshot, head = take_snapshot(toplevel, base_ref, config)
    checks = plan(snapshot, config, only)

    results: list[Result] = []
    for check in checks:
        if isinstance(check, Skipped):
            results.append(skipped_result(check))
        elif dry_run:
            results.append(Result(check.id, check.tool, check.required, check.cost, "PLANNED",
                                  command=" ".join(check.argv)))
        elif check.cost == "slow" and not include_slow:
            results.append(slow_result(check))
        else:
            results.append(run_check(toplevel, check, snapshot.changed, config))

    head_time = int(git(toplevel, "show", "-s", "--format=%ct", "HEAD").strip())
    return {
        "base": base_ref,
        "merge_base": snapshot.merge_base,
        "head": head,
        "config": {"path": config_path, "warnings": warnings},
        "languages": group_by_language(snapshot.changed),
        "notes": notes_for(toplevel, snapshot, config, head_time),
        "checks": [result_dict(result) for result in results],
        "summary": summarise(results),
    }


def result_dict(result: Result) -> dict[str, object]:
    return {
        "id": result.id, "tool": result.tool, "required": result.required, "cost": result.cost,
        "status": result.status, "reason": result.reason, "command": result.command,
        "findings": [finding.__dict__ for finding in result.findings],
        "total_findings": result.total_findings, "output_tail": result.output_tail,
    }


def parse_arguments(argv: Sequence[str]) -> dict[str, object]:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base", help="base branch or commit (default: origin's default branch)")
    parser.add_argument("--repo", default=".", help="repository directory (default: .)")
    parser.add_argument("--plan", action="store_true", help="show what would run without running it")
    parser.add_argument("--include-slow", action="store_true", help="also run slow checks")
    parser.add_argument("--only", default="", help="comma-separated check ids, e.g. secrets,purity,project")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return vars(parser.parse_args(argv))


def main(argv: Sequence[str]) -> int:
    arguments = parse_arguments(argv)
    only = frozenset(item.strip() for item in str(arguments["only"]).split(",") if item.strip())
    try:
        report = build_report(Path(str(arguments["repo"])), arguments["base"], only,  # type: ignore[arg-type]
                              bool(arguments["include_slow"]), bool(arguments["plan"]))
    except RunnerError as error:
        print(f"preflight_tools: {error}", file=sys.stderr)
        return 2
    print(render_markdown(report) if arguments["format"] == "markdown" else json.dumps(report, indent=2))
    summary = report["summary"]
    assert isinstance(summary, dict)
    return 1 if summary["required_failed"] and not arguments["plan"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
