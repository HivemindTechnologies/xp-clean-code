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
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "docs" / "specs"

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


def read_spec(path: Path) -> Spec:
    text = path.read_text(encoding="utf-8")
    status = _STATUS.search(text)
    assert status is not None, f"{path.name}: no `**Status:**` line in the header"
    files_line = _FEATURE_FILES.search(text)
    files = tuple(ROOT / f for f in _BACKTICKED.findall(files_line.group(1))) if files_line else ()
    gherkin = "\n".join(block for block in _GHERKIN_BLOCK.findall(text))
    return Spec(path, status.group(1), files, scenarios_in(gherkin))


def checked_specs() -> list[Spec]:
    if not SPECS_DIR.exists():
        return []
    return [s for s in map(read_spec, sorted(SPECS_DIR.glob("*.md"))) if s.status in CHECKED_STATES]


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
        if not feature.exists():
            problems.append(f"{spec.path.name} names {feature.relative_to(ROOT)}, which does not exist")
            continue
        in_files.update(scenarios_in(feature.read_text(encoding="utf-8")))
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
    problems = [p for spec in checked_specs() for p in mirror_problems(spec)]
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


if __name__ == "__main__":  # `python spec-sync-guard.py` prints the review-mode summary
    for spec in checked_specs():
        for problem in mirror_problems(spec):
            print("DRIFT:", problem)
    for path in unowned_feature_files():
        print("UNOWNED:", path.relative_to(ROOT))
