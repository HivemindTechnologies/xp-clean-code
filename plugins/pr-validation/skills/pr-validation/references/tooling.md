# Deterministic Tooling

`scripts/preflight_tools.py` runs tools against the commits on a branch and reports what they found on the changed lines. Its findings are evidence for the five analyses, not a replacement for them: a semgrep clock read is an impurity signal that Analysis 1 still classifies as Boundary or Violation, and an uncovered changed line is a gap that Analysis 3 still traces to a missing scenario.

The runner never installs a tool, never runs the project's test suite, and never changes the working tree. A missing tool is reported as **NOT_RUN** with the reason, never left out.

## Running It

Run from the repository, with the base branch the pull request will target:

```bash
python3 <skill-dir>/scripts/preflight_tools.py --base <base> --plan               # what would run, and why not
python3 <skill-dir>/scripts/preflight_tools.py --base <base> --format markdown    # run the fast checks
python3 <skill-dir>/scripts/preflight_tools.py --base <base> --include-slow --format markdown
```

`<skill-dir>` is the directory that holds this skill's `SKILL.md`. Use `--format json` when you need the findings as data. `--only secrets,purity,project` limits the run.

Slow checks (builds, type checks, pre-commit) report **SKIPPED_SLOW** until you pass `--include-slow`. Show the user the plan and ask before passing it, as with any test command of unknown cost.

Exit status: 0 when no required check failed, 1 when one did, 2 when the runner itself could not run (not a git repository, unknown base). Exit 1 is a finding, not a crash.

## Checks

| Check | Tool | Evidence for | Scope |
|---|---|---|---|
| `secrets` | gitleaks | Publishing safely | Every commit on the branch, including secrets added and later removed. Output is redacted; the secret never appears in the report. |
| `coverage` | diff-cover | Analysis 3 | Changed lines that no test executed, from a coverage report the project already produced. |
| `complexity` | lizard | Clean Code | Changed functions above the cyclomatic complexity limit (default 10). |
| `duplication` | jscpd | Clean Code | Clones of at least 50 tokens where one side touches a changed line. The whole repository is searched for the other side. |
| `purity` | semgrep | Analysis 1 | Impurity signals on changed lines in Scala, Python, Rust, Java and TypeScript, from the rules in `rules/purity/`. |
| `project:*` | the project's own | Avoiding a failed CI run | `pre-commit run` over the branch when `.pre-commit-config.yaml` exists, in a disposable worktree because hooks may rewrite files. Otherwise the checks below, each only where the project configures its tool. |

Project checks detected without pre-commit:

| Language | Fast | Slow | Detected by |
|---|---|---|---|
| Python | `ruff check`, `ruff format --check` | `mypy`, `pyright` | `[tool.ruff]` / `ruff.toml`; `[tool.mypy]` / `mypy.ini`; `[tool.pyright]` / `pyrightconfig.json` |
| Rust | `cargo fmt --check` | `cargo clippy --all-targets` | `Cargo.toml` |
| Scala | | `sbt scalafmtCheckAll`, `sbt "scalafixAll --check"` | `build.sbt` with `.scalafmt.conf` / `.scalafix.conf` |
| Java, Kotlin (Gradle) | | `spotlessCheck`, `checkstyleMain`, `detekt`, `ktlintCheck` | the plugin named in `build.gradle(.kts)`, and a `./gradlew` wrapper |
| Java (Maven) | | `spotless:check`, `checkstyle:check` | the plugin named in `pom.xml` |
| TypeScript | `eslint`, `biome ci` | `tsc --noEmit` | the tool's config file and its binary in `node_modules/.bin` |
| Go | `gofmt -l` | `go vet ./...`, `golangci-lint run --new-from-rev` | `go.mod`; `.golangci.*` |
| C++ | `clang-format --dry-run --Werror` | | `.clang-format` |

Each check runs from the nearest directory with the language's build file, so monorepos with several projects get one check per project (`project:ruff-check@services/api`).

The runner does not compile code to run compiler-integrated checks such as Error Prone or WartRemover. They run in the project's build; include them in CI.

## Statuses

| Status | Meaning |
|---|---|
| PASS | The tool ran and found nothing on the changed lines. |
| FAIL | The tool found something; findings or output follow. |
| NOT_RUN | The check could not run. The reason says why: a missing tool, no coverage report, no changed files in a supported language, or disabled in the configuration. |
| SKIPPED_SLOW | A slow check waiting for `--include-slow`. |
| ERROR | The tool crashed, timed out, or wrote output the runner could not read. |

A **required** check fails the preflight on FAIL, ERROR, NOT_RUN and SKIPPED_SLOW alike. A required check that did not run has not passed.

## Configuration

`.pr-preflight.toml` at the repository root. Without it every check is advisory.

```toml
[checks]
required = ["secrets", "project"]   # check ids; "project" covers every project:* check
disabled = ["duplication"]
exclude = ["tests/fixtures/**", "src/generated/**"]   # prefixes or globs; every check except secrets

[coverage]
reports = ["target/scala-2.13/coverage-report/cobertura.xml"]
fail_under = 80                     # percent of changed lines; without it, any uncovered changed line is a finding

[complexity]
max_ccn = 10

[duplication]
min_tokens = 50

[purity]
domain_paths = ["src/main/scala/com/example/domain/", "src/domain/**"]   # prefixes or globs
```

`exclude` removes paths from every check that reads files: fixtures that are impure on purpose, generated code, vendored code. Secrets are still checked everywhere.

`purity` can be required only when `domain_paths` names the domain code: impurity at the boundary is legitimate, so without domain paths the findings stay advisory. With domain paths, only files under them are scanned.

Reading the configuration needs Python 3.11 or later. On older interpreters the runner warns and uses the defaults.

## Coverage Reports

The runner never produces coverage. It reads a report the project already made, from `[coverage] reports` or a well-known path (`coverage.xml`, `lcov.info`, `coverage/lcov.info`, `target/site/jacoco/jacoco.xml`, `build/reports/jacoco/test/jacocoTestReport.xml`, `build/reports/kover/report.xml`). A report older than `HEAD` is flagged in the notes.

| Language | Producing a report diff-cover reads |
|---|---|
| Scala | `sbt coverage test coverageReport` (sbt-scoverage, Cobertura XML) |
| Python | `coverage run -m pytest && coverage xml` |
| Rust | `cargo llvm-cov --cobertura --output-path coverage.xml` |
| Java, Kotlin | JaCoCo XML (`jacocoTestReport`), or Kover XML |
| TypeScript | `vitest --coverage` or `c8` with the `lcov` reporter |
| Go | `go test -coverprofile=c.out ./...`, converted with `gocover-cobertura` |
| C++ | `gcovr --cobertura coverage.xml` |

Producing a report runs the test suite: ask the user first.

## Installing the Tools

The runner uses whatever is on `PATH`. Suggest these to the user; never install them yourself.

```bash
brew install gitleaks semgrep            # or the vendors' release binaries
pipx install diff-cover && pipx install lizard && pipx install pre-commit
npm install -g jscpd
```

## Reporting

Add a **0 · Tooling** section before the five analyses, using the runner's markdown output, and cite its findings in the analyses they inform. State every NOT_RUN and SKIPPED_SLOW check with its reason: silence on a check reads as a pass it did not earn.
