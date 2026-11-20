"""Scenarios for the pr-validation preflight tooling runner and its purity rules.

Run with: python3 -m unittest discover -s tests
Integration scenarios skip when the tool they need is not on PATH.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "plugins/pr-validation/skills/pr-validation"
RUNNER = SKILL / "scripts/preflight_tools.py"
_spec = importlib.util.spec_from_file_location("preflight_tools", RUNNER)
assert _spec is not None and _spec.loader is not None
tools = importlib.util.module_from_spec(_spec)
sys.modules["preflight_tools"] = tools
_spec.loader.exec_module(tools)

Directory, Snapshot, Config = tools.Directory, tools.Snapshot, tools.Config
ALL_TOOLS = frozenset({"gitleaks", "diff-cover", "lizard", "jscpd", "semgrep", "pre-commit", "ruff",
                       "mypy", "cargo", "sbt", "mvn", "gofmt", "go", "golangci-lint", "clang-format"})


def snapshot(changed: dict[str, set[int]], directories: dict[str, Directory] | None = None,
             tool_names: frozenset[str] = ALL_TOOLS, reports: tuple[str, ...] = ()) -> Snapshot:
    return Snapshot("m" * 40, {path: frozenset(lines) for path, lines in changed.items()},
                    directories or {"": Directory()}, tool_names, reports)


def by_id(checks: list[object]) -> dict[str, object]:
    return {check.id: check for check in checks}  # type: ignore[attr-defined]


class ParsesDiffs(unittest.TestCase):
    def test_hunks_and_files(self) -> None:
        diff = "\n".join([
            "diff --git a/a.py b/a.py", "--- a/a.py", "+++ b/a.py",
            "@@ -1,0 +2,3 @@", "+x", "+y", "+z",
            "@@ -10 +12 @@", "-old", "+new",
            "@@ -20,2 +23,0 @@", "-gone", "-gone",
            "diff --git a/dir/new file.rs b/dir/new file.rs", "--- /dev/null", "+++ b/dir/new file.rs",
            "@@ -0,0 +1,2 @@", "+fn a() {}", "+fn b() {}",
        ])
        self.assertEqual(tools.parse_changed_lines(diff), {
            "a.py": frozenset({2, 3, 4, 12}),
            "dir/new file.rs": frozenset({1, 2}),
        })

    def test_languages(self) -> None:
        groups = tools.group_by_language(["b.scala", "a.py", "c.tsx", "d.kt", "e.h", "README.md"])
        self.assertEqual(groups, {"scala": ["b.scala"], "python": ["a.py"], "typescript": ["c.tsx"],
                                  "kotlin": ["d.kt"], "cpp": ["e.h"]})


class ReadsConfiguration(unittest.TestCase):
    def test_defaults(self) -> None:
        self.assertEqual(tools.parse_config({}), (Config(), []))

    def test_values(self) -> None:
        config, warnings = tools.parse_config({
            "checks": {"required": ["secrets", "project"], "disabled": ["duplication"]},
            "coverage": {"reports": ["coverage.xml"], "fail_under": 80},
            "complexity": {"max_ccn": 12}, "duplication": {"min_tokens": 70},
            "purity": {"domain_paths": ["src/domain/"]},
        })
        self.assertEqual(warnings, [])
        self.assertEqual(config, Config(frozenset({"secrets", "project"}), frozenset({"duplication"}),
                                        ("coverage.xml",), 80, 12, 70, ("src/domain/",)))

    def test_purity_needs_domain_paths_to_be_required(self) -> None:
        config, warnings = tools.parse_config({"checks": {"required": ["purity"]}})
        self.assertNotIn("purity", config.required)
        self.assertTrue(any("domain_paths" in warning for warning in warnings))

    def test_bad_values_warn(self) -> None:
        config, warnings = tools.parse_config({"checks": {"required": "secrets"}, "extra": {}})
        self.assertEqual(config.required, frozenset())
        self.assertEqual(len(warnings), 2)


class PlansCoreChecks(unittest.TestCase):
    def test_everything_runs_when_installed(self) -> None:
        checks = by_id(tools.plan(snapshot({"src/a.py": {1}}, reports=("coverage.xml",)), Config()))
        for check_id in ("secrets", "coverage", "complexity", "duplication", "purity"):
            with self.subTest(check=check_id):
                self.assertIsInstance(checks[check_id], tools.Planned)

    def test_missing_tools_are_reported_not_hidden(self) -> None:
        checks = by_id(tools.plan(snapshot({"a.py": {1}}, tool_names=frozenset()), Config()))
        for check_id, tool in (("secrets", "gitleaks"), ("complexity", "lizard"),
                               ("duplication", "jscpd"), ("purity", "semgrep"), ("coverage", "diff-cover")):
            with self.subTest(check=check_id):
                self.assertIsInstance(checks[check_id], tools.Skipped)
                self.assertEqual(checks[check_id].reason, f"{tool} is not installed")

    def test_required_and_disabled(self) -> None:
        config = Config(required=frozenset({"secrets"}), disabled=frozenset({"duplication"}))
        checks = by_id(tools.plan(snapshot({"a.py": {1}}), config))
        self.assertTrue(checks["secrets"].required)
        self.assertEqual(checks["duplication"].reason, "disabled in .pr-preflight.toml")

    def test_coverage_reasons(self) -> None:
        unconfigured = by_id(tools.plan(snapshot({"a.py": {1}}), Config()))["coverage"]
        configured = by_id(tools.plan(snapshot({"a.py": {1}}), Config(coverage_reports=("x.xml",))))["coverage"]
        self.assertIn("no coverage report found", unconfigured.reason)
        self.assertIn("none of the reports", configured.reason)

    def test_purity_scans_first_class_languages_only(self) -> None:
        checks = by_id(tools.plan(snapshot({"a.py": {1}, "b.go": {1}, "c.scala": {1}}), Config()))
        argv = checks["purity"].argv
        self.assertIn("a.py", argv)
        self.assertIn("c.scala", argv)
        self.assertNotIn("b.go", argv)

    def test_purity_respects_domain_paths(self) -> None:
        config = Config(domain_paths=("src/domain/",))
        checks = by_id(tools.plan(snapshot({"src/domain/a.py": {1}, "src/http/b.py": {1}}), config))
        self.assertIn("src/domain/a.py", checks["purity"].argv)
        self.assertNotIn("src/http/b.py", checks["purity"].argv)

    def test_no_source_files(self) -> None:
        checks = by_id(tools.plan(snapshot({"README.md": {1}}), Config()))
        self.assertIsInstance(checks["secrets"], tools.Planned)
        self.assertEqual(checks["complexity"].reason, "no changed source files")

    def test_jscpd_formats_follow_changed_languages(self) -> None:
        argv = by_id(tools.plan(snapshot({"a.ts": {1}, "b.cpp": {1}}), Config()))["duplication"].argv
        self.assertEqual(argv[argv.index("--format") + 1], "c,cpp,tsx,typescript")

    def test_only(self) -> None:
        checks = tools.plan(snapshot({"a.py": {1}}), Config(), frozenset({"secrets"}))
        self.assertEqual([check.id for check in checks], ["secrets"])


class PlansProjectChecks(unittest.TestCase):
    def test_pre_commit_replaces_native_detection_and_runs_in_a_worktree(self) -> None:
        directories = {"": Directory(frozenset({".pre-commit-config.yaml", "pyproject.toml"}),
                                     {"pyproject.toml": "[tool.ruff]"})}
        checks = [check for check in tools.plan(snapshot({"a.py": {1}}, directories), Config())
                  if check.id.startswith("project:")]
        self.assertEqual([check.id for check in checks], ["project:pre-commit"])
        self.assertTrue(checks[0].in_worktree)
        self.assertEqual(checks[0].cost, "slow")

    def test_ruff_in_a_nested_project(self) -> None:
        directories = {"": Directory(), "svc": Directory(frozenset({"pyproject.toml"}),
                                                         {"pyproject.toml": "[tool.ruff]\nline-length = 100"}),
                       "svc/app": Directory()}
        checks = by_id(tools.plan(snapshot({"svc/app/a.py": {1}}, directories), Config()))
        check = checks["project:ruff-check@svc"]
        self.assertEqual(check.cwd, "svc")
        self.assertEqual(check.argv[-1], "app/a.py")
        self.assertNotIn("project:mypy@svc", checks)

    def test_unconfigured_tools_do_not_run(self) -> None:
        directories = {"": Directory(frozenset({"pyproject.toml"}), {"pyproject.toml": "[project]"})}
        checks = tools.plan(snapshot({"a.py": {1}}, directories), Config())
        self.assertFalse([check for check in checks if check.id.startswith("project:")])

    def test_node_tools_need_node_modules(self) -> None:
        bare = {"": Directory(frozenset({"package.json", "eslint.config.js", "tsconfig.json"}))}
        installed = {"": Directory(frozenset({"package.json", "eslint.config.js", "tsconfig.json",
                                              "node_modules/.bin/eslint", "node_modules/.bin/tsc"}))}
        self.assertFalse([c for c in tools.plan(snapshot({"a.ts": {1}}, bare), Config()) if c.id.startswith("project:")])
        checks = by_id(tools.plan(snapshot({"a.ts": {1}}, installed), Config()))
        self.assertEqual(checks["project:eslint"].cost, "fast")
        self.assertEqual(checks["project:tsc"].cost, "slow")

    def test_gradle_without_wrapper_is_reported(self) -> None:
        directories = {"": Directory(frozenset({"build.gradle.kts"}), {"build.gradle.kts": 'id("com.diffplug.spotless")'})}
        check = by_id(tools.plan(snapshot({"A.kt": {1}}, directories), Config()))["project:spotless-gradle"]
        self.assertIsInstance(check, tools.Skipped)
        self.assertEqual(check.reason, "no ./gradlew wrapper")

    def test_scala_formatting_config_found_in_a_parent(self) -> None:
        directories = {"": Directory(frozenset({".scalafmt.conf"})), "core": Directory(frozenset({"build.sbt"}))}
        checks = by_id(tools.plan(snapshot({"core/A.scala": {1}}, directories), Config()))
        self.assertEqual(checks["project:scalafmt@core"].argv, ("sbt", "-batch", "scalafmtCheckAll"))
        self.assertNotIn("project:scalafix@core", checks)

    def test_gofmt_lists_files(self) -> None:
        directories = {"": Directory(frozenset({"go.mod"}))}
        check = by_id(tools.plan(snapshot({"main.go": {1}}, directories), Config()))["project:gofmt"]
        self.assertEqual((check.kind, check.argv), ("listing", ("gofmt", "-l", "main.go")))

    def test_project_required_covers_every_project_check(self) -> None:
        directories = {"": Directory(frozenset({"go.mod"}))}
        checks = tools.plan(snapshot({"main.go": {1}}, directories), Config(required=frozenset({"project"})))
        self.assertTrue(all(check.required for check in checks if check.id.startswith("project:")))


class ParsesToolOutput(unittest.TestCase):
    changed = {"a.py": frozenset({5, 6}), "b.py": frozenset({40})}

    def test_lizard_keeps_complex_changed_functions(self) -> None:
        output = "\n".join([
            '10,12,40,2,10,"f@3-12@a.py","a.py","f","f( x , y )",3,12',
            '3,15,24,1,3,"g@20-30@a.py","a.py","g","g( )",20,30',
            '3,4,24,1,3,"h@38-45@b.py","b.py","h","h( )",38,45',
        ])
        findings = tools.parse_lizard(output, self.changed, 10)
        self.assertEqual([(f.file, f.line) for f in findings], [("a.py", 3)])

    def test_jscpd_reports_the_changed_fragment(self) -> None:
        report = json.dumps({"duplicates": [
            {"lines": 9, "firstFile": {"name": "./c.py", "start": 1, "end": 9},
             "secondFile": {"name": "b.py", "start": 35, "end": 43}},
            {"lines": 9, "firstFile": {"name": "c.py", "start": 1, "end": 9},
             "secondFile": {"name": "d.py", "start": 1, "end": 9}},
        ]})
        findings = tools.parse_jscpd(report, self.changed)
        self.assertEqual(len(findings), 1)
        self.assertEqual((findings[0].file, findings[0].line), ("b.py", 35))
        self.assertIn("c.py:1-9", findings[0].message)

    def test_semgrep_keeps_changed_lines(self) -> None:
        output = json.dumps({"results": [
            {"path": "a.py", "start": {"line": 5}, "end": {"line": 5},
             "check_id": "tmp.rules.purity.python-clock", "extra": {"message": "Clock read."}},
            {"path": "a.py", "start": {"line": 9}, "end": {"line": 9},
             "check_id": "python-random", "extra": {"message": "Random read."}},
        ], "errors": []})
        findings, errors = tools.parse_semgrep(output, self.changed)
        self.assertEqual([(f.line, f.rule) for f in findings], [(5, "python-clock")])
        self.assertEqual(errors, [])

    def test_gitleaks_never_copies_the_secret(self) -> None:
        report = json.dumps([{"File": "a.py", "StartLine": 3, "RuleID": "github-pat", "Description": "GitHub token",
                              "Commit": "0123456789abcdef", "Secret": "ghp_real", "Match": "token = ghp_real"}])
        findings = tools.parse_gitleaks(report)
        self.assertEqual(findings[0].rule, "github-pat")
        self.assertNotIn("ghp_real", json.dumps([f.__dict__ for f in findings]))

    def test_diff_cover(self) -> None:
        report = json.dumps({"src_stats": {"a.py": {"violation_lines": [5]}}, "total_percent_covered": 75})
        findings, total = tools.parse_diff_cover(report)
        self.assertEqual(([(f.file, f.line) for f in findings], total), ([("a.py", 5)], 75.0))


class Judges(unittest.TestCase):
    def planned(self, kind: str, tool: str = "t") -> object:
        return tools.Planned("x", tool, (tool,), "", "fast", kind, True)

    def test_exit_status(self) -> None:
        self.assertEqual(tools.judge(self.planned("exit"), 0, "", "", None, {}, Config()).status, "PASS")
        failed = tools.judge(self.planned("exit"), 1, "E1 bad", "", None, {}, Config())
        self.assertEqual((failed.status, failed.output_tail), ("FAIL", "E1 bad"))

    def test_listing(self) -> None:
        result = tools.judge(self.planned("listing", "gofmt"), 0, "main.go\n", "", None, {}, Config())
        self.assertEqual((result.status, result.findings[0].file), ("FAIL", "main.go"))

    def test_coverage_threshold(self) -> None:
        report = json.dumps({"src_stats": {"a.py": {"violation_lines": [5]}}, "total_percent_covered": 90})
        result = tools.judge(self.planned("diff-cover"), 0, "", "", report, {}, Config(fail_under=80))
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.total_findings, 1)
        result = tools.judge(self.planned("diff-cover"), 0, "", "", report, {}, Config(fail_under=95))
        self.assertEqual(result.status, "FAIL")

    def test_unreadable_output_is_an_error(self) -> None:
        result = tools.judge(self.planned("semgrep"), 0, "not json", "", None, {}, Config())
        self.assertEqual(result.status, "ERROR")

    def test_required_checks_that_did_not_pass(self) -> None:
        results = [
            tools.Result("a", "t", True, "fast", "PASS"),
            tools.Result("b", "t", True, "fast", "NOT_RUN"),
            tools.Result("c", "t", True, "slow", "SKIPPED_SLOW"),
            tools.Result("d", "t", False, "fast", "FAIL"),
        ]
        self.assertEqual(tools.summarise(results)["required_failed"], ["b", "c"])


def have(*names: str) -> bool:
    return all(shutil.which(name) for name in names)


def git(repo: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *arguments],
                          cwd=repo, check=True, capture_output=True, text=True).stdout


TOKEN = "ghp_" + "8fK2mQ9zR4tW7yX1cV5bN3jH6gL0pD2sA9eT"


class EndToEnd(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "base")
        git(self.repo, "switch", "-q", "-c", "feature")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def commit(self, files: dict[str, str]) -> None:
        for name, text in files.items():
            (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / name).write_text(text, encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "change")

    def run_tools(self, *arguments: str) -> tuple[int, dict[str, object]]:
        completed = subprocess.run([sys.executable, str(RUNNER), "--base", "main", *arguments],
                                   cwd=self.repo, capture_output=True, text=True, check=False)
        self.assertIn(completed.returncode, (0, 1), completed.stderr)
        return completed.returncode, json.loads(completed.stdout)

    @unittest.skipUnless(have("gitleaks"), "gitleaks not installed")
    def test_secrets_are_found_and_never_printed(self) -> None:
        self.commit({"settings.py": f'TOKEN = "{TOKEN}"\n'})
        (self.repo / ".pr-preflight.toml").write_text('[checks]\nrequired = ["secrets"]\n')
        code, report = self.run_tools("--only", "secrets")
        check = report["checks"][0]
        self.assertEqual((check["status"], code), ("FAIL", 1))
        self.assertEqual(report["summary"]["required_failed"], ["secrets"])
        self.assertNotIn(TOKEN, json.dumps(report))

    @unittest.skipUnless(have("semgrep"), "semgrep not installed")
    def test_purity_only_reports_changed_lines(self) -> None:
        self.commit({"domain.py": "import time\n\ndef old():\n    return time.time()\n"})
        git(self.repo, "branch", "-f", "main", "HEAD")
        self.commit({"domain.py": "import time\n\ndef old():\n    return time.time()\n\n"
                                  "def new():\n    return time.time()\n"})
        _, report = self.run_tools("--only", "purity")
        findings = report["checks"][0]["findings"]
        self.assertEqual([(f["file"], f["line"], f["rule"]) for f in findings], [("domain.py", 7, "python-clock")])

    @unittest.skipUnless(have("pre-commit"), "pre-commit not installed")
    def test_pre_commit_never_touches_the_working_tree(self) -> None:
        self.commit({
            ".pre-commit-config.yaml": (
                "repos:\n- repo: local\n  hooks:\n  - id: rewrite\n    name: rewrite\n"
                "    entry: sh -c 'for f in \"$@\"; do echo rewritten >> \"$f\"; done; exit 1' --\n"
                "    language: system\n    files: \\.py$\n"),
            "a.py": "x = 1\n",
        })
        before = (self.repo / "a.py").read_text()
        _, report = self.run_tools("--only", "project", "--include-slow")
        check = report["checks"][0]
        self.assertEqual((check["id"], check["status"]), ("project:pre-commit", "FAIL"))
        self.assertEqual((self.repo / "a.py").read_text(), before)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        self.assertEqual(len(git(self.repo, "worktree", "list").splitlines()), 1)

    def test_slow_checks_wait_for_permission(self) -> None:
        self.commit({".pre-commit-config.yaml": "repos: []\n", "a.py": "x = 1\n"})
        _, report = self.run_tools("--only", "project")
        check = report["checks"][0]
        self.assertIn(check["status"], ("SKIPPED_SLOW", "NOT_RUN"))

    def test_plan_runs_nothing(self) -> None:
        self.commit({"a.py": "x = 1\n"})
        code, report = self.run_tools("--plan")
        self.assertEqual(code, 0)
        self.assertNotIn("PASS", {check["status"] for check in report["checks"]})
        self.assertNotIn("FAIL", {check["status"] for check in report["checks"]})


@unittest.skipUnless(have("semgrep"), "semgrep not installed")
class PurityRules(unittest.TestCase):
    def test_rules_match_their_annotated_fixtures(self) -> None:
        completed = subprocess.run(
            ["semgrep", "--test", "--metrics=off", "--config", str(SKILL / "rules/purity"),
             str(ROOT / "tests/semgrep/purity")],
            capture_output=True, text=True, check=False, env={**os.environ, "SEMGREP_ENABLE_VERSION_CHECK": "0"})
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
