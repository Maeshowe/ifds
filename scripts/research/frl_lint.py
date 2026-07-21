"""FRL — hypothesis registry lint: hypothesis-first, enforced by machine (spec §8).

The loop's first step is a *registered* hypothesis with a written mechanism. This
module makes that structural rather than aspirational: the batch calls
``assert_runnable()`` before an attempt, so a factor whose hypothesis is still a
DRAFT — or whose mechanism section is empty — cannot be tested at all.

Also enforced here (R1#6): a hypothesis may only reach REGISTERED if its factor
has a green ``sanity()`` pair.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import frl_config as cfg

HYPOTHESIS_DIR = cfg.PROJECT_ROOT / "docs" / "design" / "frl" / "hypotheses"

STATUSES = (
    "DRAFT",
    "REGISTERED",
    "TESTED",
    "KILLED",
    "PARKED",
    "PROMOTED",
    "HOLDOUT-PASS",
    "SHADOW",
    "DEPLOYED",
)

# Statuses an attempt may run against: the hypothesis is written down and either
# never tested or already tested (a re-test on fresh data is legitimate).
RUNNABLE_STATUSES = ("REGISTERED", "TESTED")

# Legal transitions. HOLDOUT-PASS only from PROMOTED; SHADOW only from
# HOLDOUT-PASS and only after the Day 63 gate.
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "DRAFT": ("REGISTERED",),
    "REGISTERED": ("TESTED", "KILLED", "PARKED"),
    "TESTED": ("KILLED", "PARKED", "PROMOTED"),
    "PARKED": ("TESTED", "KILLED", "PROMOTED"),
    "PROMOTED": ("HOLDOUT-PASS", "KILLED"),
    "HOLDOUT-PASS": ("SHADOW", "KILLED"),
    "SHADOW": ("DEPLOYED", "KILLED"),
    "DEPLOYED": (),
    "KILLED": (),
}

# SHADOW means live persistence in production — allowed only after the Day 63
# gate. The condition is the explicit `cfg.DAY63_GATE_PASSED` flag, NOT a computed
# date: the NYSE-calendar 63rd trading day (2026-08-17) is ~a month earlier than
# the working target (≈2026-09-15), because the gate counts actual edge-sample
# days and the outage days are excluded (04-risks §11.10). A date-derived guard
# would open early; a flag cannot.

REQUIRED_SECTIONS = (
    "Mechanizmus",
    "Várt előjel és horizont",
    "Ki a vesztes oldal",
    "Költségprofil",
    "Pre-reg metrika és kill-kritérium",
)

_HEADER_KEYS = ("Status", "Updated", "Data-lane")
_PLACEHOLDER = re.compile(r"^\s*(—|-|<.*>|TODO|TBD)\s*$", re.IGNORECASE)


@dataclass
class LintResult:
    """Findings for one hypothesis file."""

    path: Path
    hyp_id: str = ""
    status: str = ""
    data_lane: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def line(self) -> str:
        mark = "OK " if self.ok else "ERR"
        detail = "; ".join(self.errors) if self.errors else ""
        return f"{mark} {self.path.name} [{self.status or '?'}] {detail}".rstrip()


def _parse_header(text: str) -> dict[str, str]:
    header: dict[str, str] = {}
    for raw in text.splitlines()[:6]:
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        if key in ("Status", "Updated", "Data-lane", "Attempt-family", "Note"):
            header[key] = value.strip()
    return header


def _sections(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    current: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                out[current] = "\n".join(body).strip()
            current = line[3:].strip()
            body = []
        elif current is not None:
            body.append(line)
    if current is not None:
        out[current] = "\n".join(body).strip()
    return out


def _section_filled(sections: dict[str, str], prefix: str) -> bool:
    for name, body in sections.items():
        if not name.startswith(prefix):
            continue
        lines = [ln for ln in body.splitlines() if ln.strip() and not ln.startswith(">")]
        if not lines:
            return False
        return not all(_PLACEHOLDER.match(ln) for ln in lines)
    return False


def lint_file(path: Path, today: date | None = None) -> LintResult:
    """Lint a single hypothesis file."""
    today = today or date.today()
    result = LintResult(path=path)
    text = path.read_text()

    header = _parse_header(text)
    for key in _HEADER_KEYS:
        if key not in header:
            result.errors.append(f"missing header key: {key}")

    status = header.get("Status", "")
    result.status = status
    result.data_lane = header.get("Data-lane", "")

    if status and status not in STATUSES:
        result.errors.append(f"invalid Status: {status}")
    if result.data_lane and result.data_lane not in ("v1", "v2"):
        result.errors.append(f"invalid Data-lane: {result.data_lane}")

    match = re.search(r"^#\s+(HYP-[0-9]{3}[ab]?)", text, re.MULTILINE)
    if match:
        result.hyp_id = match.group(1)
    else:
        result.errors.append("no `# HYP-###` title found")

    sections = _sections(text)
    if status != "DRAFT":
        for required in REQUIRED_SECTIONS:
            if not _section_filled(sections, required):
                result.errors.append(f"section empty or placeholder: {required}")
    else:
        result.warnings.append("DRAFT — attempts are blocked until REGISTERED")

    if status == "SHADOW" and not cfg.DAY63_GATE_PASSED:
        result.errors.append(
            "SHADOW is not allowed before the Day 63 gate — set "
            "frl_config.DAY63_GATE_PASSED only after Tamás' gate decision "
            f"(NYSE-calendar estimate for reference: "
            f"{cfg.DAY63_NYSE_DATE_INFORMATIVE.isoformat()}, working target ≈2026-09-15)"
        )

    return result


def lint_dir(directory: Path | None = None, today: date | None = None) -> list[LintResult]:
    """Lint every hypothesis file (the template is skipped)."""
    base = Path(directory) if directory is not None else HYPOTHESIS_DIR
    if not base.exists():
        return []
    return [lint_file(path, today) for path in sorted(base.glob("HYP-*.md"))]


def check_transition(current: str, target: str) -> None:
    """Validate a status transition.

    Raises:
        ValueError: if the transition is not in the legal map.
    """
    if current not in TRANSITIONS:
        raise ValueError(f"unknown current status: {current}")
    if target not in TRANSITIONS[current]:
        allowed = TRANSITIONS[current] or ("(terminal)",)
        raise ValueError(f"illegal transition {current} -> {target}; allowed: {allowed}")


def load_status(hyp_id: str, directory: Path | None = None) -> str | None:
    """Status of ``hyp_id``, or None if no file exists."""
    for result in lint_dir(directory):
        if result.hyp_id == hyp_id:
            return result.status
    return None


class HypothesisNotRunnable(RuntimeError):
    """Raised when an attempt targets an unregistered or invalid hypothesis."""


def assert_runnable(hyp_id: str, directory: Path | None = None) -> None:
    """Gate an attempt on a registered, lint-clean hypothesis (hypothesis-first).

    Raises:
        HypothesisNotRunnable: if the hypothesis is missing, still DRAFT, or has
            lint errors.
    """
    for result in lint_dir(directory):
        if result.hyp_id != hyp_id:
            continue
        if not result.ok:
            raise HypothesisNotRunnable(f"{hyp_id} fails lint: {'; '.join(result.errors)}")
        if result.status not in RUNNABLE_STATUSES:
            raise HypothesisNotRunnable(
                f"{hyp_id} is {result.status} — attempts require one of "
                f"{RUNNABLE_STATUSES}. Write the mechanism first (spec §3/1)."
            )
        return
    raise HypothesisNotRunnable(f"{hyp_id} has no registered hypothesis file in {HYPOTHESIS_DIR}")


def assert_sanity_pair(factor, directory: Path | None = None) -> None:
    """A REGISTERED hypothesis requires a green ``sanity()`` pair (R1#6).

    Raises:
        HypothesisNotRunnable: if the factor's sanity check fails.
    """
    import factors.base as factor_base

    result = factor_base.run_sanity(factor)
    if not result.passed:
        raise HypothesisNotRunnable(f"{factor.name} has no green sanity() pair: {result.line()}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="FRL hypothesis registry lint")
    parser.add_argument("--dir", type=Path, default=None)
    args = parser.parse_args(argv)

    results = lint_dir(args.dir)
    for result in results:
        print(result.line())
    failed = [r for r in results if not r.ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} clean")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
