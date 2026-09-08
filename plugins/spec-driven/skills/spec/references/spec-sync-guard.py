"""Spec ⇄ feature-file mirror guard (reference implementation, stdlib only).

Copy this file into the project's test suite (e.g. `tests/test_specs_are_in_sync.py`). It is the
executable form of §3 of `sync-contract.md`: every scenario a spec authorises exists verbatim in
one of the feature files the spec names, and every scenario in those files is authorised by
exactly one spec. Duplication of Gherkin between the spec and the feature file is acceptable only
because this test exists.

The comparison is textual — no Gherkin parser — so the same algorithm ports to any stack in a
few dozen lines. Whitespace is normalised; comments are dropped; titles and step lines must
otherwise match exactly.

Spec header contract (the first 40 lines of each `docs/specs/*.md`):

    **Status:** building
    **Feature files:** `tests/features/orders.feature`, `tests/features/refunds.feature`

Only specs in `building`, `shipped` or `reconciled` are checked: in `draft` and `confirmed` the
spec alone is authoritative and no feature file need exist yet.

The header is untrusted input — a spec arrives in a pull request like any other file — so a
feature-file path is accepted only when it is relative, resolves to a location inside the project
root, and ends in `.feature`. Anything else is reported as a malformed header and never opened:
the guard's job is to compare two files it owns, not to read what a spec tells it to.
"""

from __future__ import annotations

import difflib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# The project root: the directory holding `docs/` and `tests/`. As a test file under `tests/`
# that is one level up; when run as a script from elsewhere (a review over another checkout),
# pass the root as the first argument or set SPEC_SYNC_ROOT, so the guard never silently
# inspects the wrong tree and prints nothing.
_ROOT_OVERRIDE = sys.argv[1] if __name__ == "__main__" and len(sys.argv) > 1 else os.environ.get("SPEC_SYNC_ROOT")
ROOT = Path(_ROOT_OVERRIDE).resolve() if _ROOT_OVERRIDE else Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "docs" / "specs"

# The lifecycle from sync-contract.md §2. A status outside this set is a malformed header, not a
# spec in some other state: a typo such as `buidling` must fail the check, never opt out of it.
LIFECYCLE_STATES = {"draft", "confirmed", "building", "shipped", "reconciled", "withdrawn", "superseded"}
CHECKED_STATES = {"building", "shipped", "reconciled"}
_STATUS = re.compile(r"^\*\*Status:\*\*\s*`?([a-z]+)`?", re.MULTILINE)
_FEATURE_FILES = re.compile(r"^\*\*Feature files?:\*\*(.*)$", re.MULTILINE)
_BACKTICKED = re.compile(r"`([^`]+)`")
_GHERKIN_BLOCK = re.compile(r"```gherkin\n(.*?)```", re.DOTALL)
_SCENARIO_LINE = re.compile(r"^\s*(Scenario(?: Outline)?):\s*(.+?)\s*$")
_TERMINATOR = re.compile(r"^\s*(Feature|Background|Rule|Scenario(?: Outline)?):")


@dataclass(frozen=True)
class Scenario:
    title: str
    steps: tuple[str, ...]


def scenarios_in(text: str) -> dict[str, Scenario]:
    """Every `Scenario:`/`Scenario Outline:` block in `text`, keyed on its title.

    Steps are the following non-comment lines, trimmed and with internal whitespace collapsed,
    up to the next Gherkin keyword at block level. Examples tables are kept as steps so a changed
    example row is a changed scenario.
    """
    found: dict[str, Scenario] = {}
    current_title: str | None = None
    current_steps: list[str] = []

    def flush() -> None:
        if current_title is not None:
            if current_title in found:
                raise AssertionError(f"duplicate scenario title within one source: {current_title!r}")
            found[current_title] = Scenario(current_title, tuple(current_steps))

    for raw in text.splitlines():
        line = raw.strip()
        # Blank lines and comments carry no behaviour. Neither do tags (`@wip`, `@slow`): they are
        # how a build marks the scenarios it has not reached yet, and toggling them must not read
        # as drift between the spec and the feature file.
        if not line or line.startswith("#") or line.startswith("@"):
            continue
        header = _SCENARIO_LINE.match(raw)
        if header:
            flush()
            current_title = header.group(2)
            current_steps = []
            continue
        if _TERMINATOR.match(raw):
            flush()
            current_title = None
            current_steps = []
            continue
        if current_title is not None:
            current_steps.append(re.sub(r"\s+", " ", line))
    flush()
    return found


@dataclass(frozen=True)
class Spec:
    path: Path
    status: str
    feature_files: tuple[Path, ...]
    scenarios: dict[str, Scenario]


def feature_path_problem(declared: str) -> str | None:
    """Why a declared feature-file path may not be opened, or None when it may.

    The path comes from a document anyone who can open a pull request can write. It must stay
    inside the project root after resolution (so `../` and symlinks out of the tree are refused),
    must not be absolute, and must be a `.feature` file — the only kind of file the mirror has any
    business reading.
    """
    if Path(declared).is_absolute():
        return f"`{declared}` is absolute; feature-file paths are relative to the project root"
    resolved = (ROOT / declared).resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        return f"`{declared}` resolves outside the project root"
    if resolved.suffix != ".feature":
        return f"`{declared}` is not a `.feature` file"
    return None


def read_spec(path: Path) -> Spec | str:
    """The spec, or a one-line problem when its header does not follow the template.

    A malformed header is reported beside the other drift rather than raised: one badly-headed
    file must not stop the other specs from being checked. A spec naming a path the guard may
    not open is malformed as a whole — none of its paths are read.
    """
    text = path.read_text(encoding="utf-8")
    status = _STATUS.search(text)
    if status is None:
        return f"{path.name}: no parseable `**Status:** <state>` line (see spec-template.md)"
    if status.group(1) not in LIFECYCLE_STATES:
        return (
            f"{path.name}: `**Status:** {status.group(1)}` is not a lifecycle state "
            f"({', '.join(sorted(LIFECYCLE_STATES))}); a spec in an unknown state is not checked, "
            "so it is refused rather than skipped"
        )
    files_line = _FEATURE_FILES.search(text)
    declared = _BACKTICKED.findall(files_line.group(1)) if files_line else []
    refused = [p for p in (feature_path_problem(d) for d in declared) if p is not None]
    if refused:
        return f"{path.name}: feature-file path refused — " + "; ".join(refused)
    files = tuple(ROOT / d for d in declared)
    gherkin = "\n".join(block for block in _GHERKIN_BLOCK.findall(text))
    return Spec(path, status.group(1), files, scenarios_in(gherkin))


def load_specs() -> tuple[list[Spec], list[str]]:
    """Every spec under docs/specs/ that the mirror applies to, and the header problems found."""
    if not SPECS_DIR.exists():
        return [], []
    specs: list[Spec] = []
    problems: list[str] = []
    for loaded in map(read_spec, sorted(SPECS_DIR.glob("*.md"))):
        if isinstance(loaded, str):
            problems.append(loaded)
        elif loaded.status in CHECKED_STATES:
            specs.append(loaded)
    return specs, problems


def checked_specs() -> list[Spec]:
    return load_specs()[0]


def _step_diff(spec_side: Scenario, file_side: Scenario) -> str:
    return "\n".join(
        difflib.unified_diff(
            list(spec_side.steps), list(file_side.steps), "spec", "feature file", lineterm="", n=1
        )
    )


def mirror_problems(spec: Spec) -> list[str]:
    """Human-readable drift between one spec's Gherkin blocks and its feature files."""
    problems: list[str] = []
    if not spec.feature_files:
        return [f"{spec.path.name} is `{spec.status}` but names no feature file"]
    in_files: dict[str, Scenario] = {}
    for feature in spec.feature_files:
        if not feature.is_file():
            problems.append(f"{spec.path.name} names {feature.relative_to(ROOT)}, which is not a file")
            continue
        try:
            text = feature.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as unreadable:
            problems.append(f"{feature.relative_to(ROOT)} could not be read as a feature file: {unreadable}")
            continue
        try:
            found = scenarios_in(text)
        except AssertionError as duplicate:
            problems.append(f"{feature.relative_to(ROOT)}: {duplicate}")
            continue
        # A title already seen in an earlier owned file must not be overwritten: the later copy
        # could match the spec while the earlier one carries steps the spec never authorised.
        for title in sorted(found.keys() & in_files.keys()):
            problems.append(
                f"{title!r} is defined in more than one feature file {spec.path.name} owns "
                f"(again in {feature.relative_to(ROOT)}); one scenario, one definition"
            )
            del found[title]
        in_files.update(found)
    for title, authorised in spec.scenarios.items():
        built = in_files.get(title)
        if built is None:
            problems.append(f"{spec.path.name} authorises {title!r}; no named feature file has it")
        elif built.steps != authorised.steps:
            problems.append(f"{title!r} differs in steps:\n{_step_diff(authorised, built)}")
    for title in in_files.keys() - spec.scenarios.keys():
        problems.append(
            f"{title!r} is in a feature file {spec.path.name} owns, but the spec does not authorise it"
        )
    return problems


def test_every_checked_spec_mirrors_its_feature_files() -> None:
    specs, header_problems = load_specs()
    problems = header_problems + [p for spec in specs for p in mirror_problems(spec)]
    assert not problems, "spec ⇄ feature-file drift:\n\n" + "\n\n".join(problems)


def test_no_scenario_is_authorised_by_two_specs() -> None:
    owners: dict[str, list[str]] = {}
    for spec in checked_specs():
        for title in spec.scenarios:
            owners.setdefault(title, []).append(spec.path.name)
    shared = {t: o for t, o in owners.items() if len(o) > 1}
    assert not shared, f"scenarios owned by more than one spec: {shared}"


def unowned_feature_files() -> list[Path]:
    """Feature files no spec names — a review finding, deliberately not a test failure."""
    features_dir = ROOT / "tests" / "features"
    if not features_dir.exists():
        return []
    owned = {f for spec in checked_specs() for f in spec.feature_files}
    return sorted(f for f in features_dir.glob("*.feature") if f not in owned)


if __name__ == "__main__":
    # `python spec-sync-guard.py [project-root]` — the review skill's summary: counts first, so a
    # tree with no specs says so instead of printing nothing; exit 1 on any drift.
    specs, header_problems = load_specs()
    drift = header_problems + [p for spec in specs for p in mirror_problems(spec)]
    unowned = unowned_feature_files()
    owned = {f for spec in specs for f in spec.feature_files}
    print(f"root: {ROOT}")
    print(f"specs dir: {'present' if SPECS_DIR.exists() else 'ABSENT'}; "
          f"{len(specs)} spec(s) in a checked state; {len(header_problems)} malformed header(s)")
    print(f"feature files: {len(owned)} owned, {len(unowned)} unowned")
    for problem in drift:
        print("DRIFT:", problem)
    for path in unowned:
        print("UNOWNED:", path.relative_to(ROOT))
    sys.exit(1 if drift else 0)
