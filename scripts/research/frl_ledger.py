"""FRL — append-only attempt ledger with multiplicity deflation (spec §6, §5.4).

G4: every tested variant is written with ``decision: "PENDING"`` **before** the
test runs. Metrics and the decision are filled in afterwards on the same line.
This closes the "I tested it, didn't like it, didn't log it" loophole — the
significance threshold deflates from the ledger count, so a hidden attempt would
silently inflate everyone else's odds.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import frl_config as cfg

PENDING = "PENDING"
DECISIONS = ("PENDING", "KILL", "PARK", "PARK_UNTIL_SWING_POWER", "PROMOTE")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_ledger(path: Path | None = None) -> list[dict]:
    """Read every ledger entry, oldest first."""
    target = Path(path) if path is not None else cfg.LEDGER_PATH
    if not target.exists():
        return []
    entries = []
    for line in target.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def next_attempt_id(path: Path | None = None) -> str:
    """Next ``A-000N`` id, derived from the ledger itself (no separate counter)."""
    entries = read_ledger(path)
    highest = 0
    for entry in entries:
        raw = str(entry.get("attempt_id", ""))
        if raw.startswith("A-"):
            try:
                highest = max(highest, int(raw[2:]))
            except ValueError:
                continue
    return f"A-{highest + 1:04d}"


@dataclass(frozen=True)
class AttemptSpec:
    """Everything known about an attempt *before* it runs."""

    hyp_id: str
    variant: str
    data_lane: str
    dev_window: dict
    n_days_used: dict
    code_ref: str
    horizon: int | None = None


def open_attempt(spec: AttemptSpec, path: Path | None = None) -> str:
    """Write the PENDING ledger line and return the attempt id.

    Must be called before the test computes anything (G4).
    """
    target = Path(path) if path is not None else cfg.LEDGER_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    attempt_id = next_attempt_id(target)
    entry = {
        "attempt_id": attempt_id,
        "hyp_id": spec.hyp_id,
        "variant": spec.variant,
        "tested_at": _now_iso(),
        "data_lane": spec.data_lane,
        "horizon": spec.horizon,
        "dev_window": spec.dev_window,
        "n_days_used": spec.n_days_used,
        "metrics": {},
        "half_life_days": None,
        "implied_turnover_cost_bps": None,
        "decision": PENDING,
        "decision_note": "",
        "decision_source": None,
        "human_confirmed": False,
        "holdout_touched": False,
        "code_ref": spec.code_ref,
    }
    with open(target, "a") as fh:
        fh.write(json.dumps(entry) + "\n")
    return attempt_id


def close_attempt(
    attempt_id: str,
    metrics: dict,
    decision: str,
    decision_note: str = "",
    half_life_days: float | None = None,
    implied_turnover_cost_bps: float | None = None,
    holdout_touched: bool | None = None,
    path: Path | None = None,
) -> dict:
    """Fill in the results of a previously opened attempt (rewrite-on-close).

    The verdict written here is the *machine* verdict: it lands with
    ``decision_source: "auto"`` and ``human_confirmed: False``, because spec §10
    puts the decision with Tamás (Chat proposes). The auto verdict is a
    mechanically-triggered default on a pre-registered criterion, not the
    decision itself — ``confirm_decision()`` is what closes the audit chain.

    The whole file is rewritten through a temp file, with a ``.bak`` copy of the
    previous state kept — an append-only log that gets rewritten needs a
    recoverable prior version.

    Raises:
        ValueError: on unknown decision or unknown attempt id.
    """
    if decision not in DECISIONS:
        raise ValueError(f"unknown decision: {decision} (allowed: {DECISIONS})")

    target = Path(path) if path is not None else cfg.LEDGER_PATH
    entries = read_ledger(target)
    updated: dict | None = None

    for entry in entries:
        if entry.get("attempt_id") == attempt_id:
            entry["metrics"] = metrics
            entry["decision"] = decision
            entry["decision_note"] = decision_note
            entry["half_life_days"] = half_life_days
            entry["implied_turnover_cost_bps"] = implied_turnover_cost_bps
            entry["closed_at"] = _now_iso()
            entry["decision_source"] = "auto"
            entry["human_confirmed"] = False
            if holdout_touched is not None:
                entry["holdout_touched"] = bool(holdout_touched)
            updated = entry
            break

    if updated is None:
        raise ValueError(f"attempt not found in ledger: {attempt_id}")

    _write_ledger(entries, target)
    return updated


def _write_ledger(entries: list[dict], target: Path) -> None:
    """Rewrite the ledger atomically, keeping a ``.bak`` of the prior state."""
    if target.exists():
        shutil.copy2(target, target.with_suffix(target.suffix + ".bak"))
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(e) + "\n" for e in entries))
    tmp.replace(target)


def confirm_decision(
    attempt_id: str,
    by: str,
    decision: str | None = None,
    note: str = "",
    path: Path | None = None,
) -> dict:
    """Record the human decision on a closed attempt (spec §10).

    Pass ``decision`` to override the machine verdict — the override is the whole
    point of the confirmation step, and the original is preserved in
    ``auto_decision`` so the audit chain shows what the machine proposed and what
    the human decided.

    Raises:
        ValueError: if the attempt is unknown, still PENDING, or the override
            decision is not a legal one.
    """
    target = Path(path) if path is not None else cfg.LEDGER_PATH
    entries = read_ledger(target)

    for entry in entries:
        if entry.get("attempt_id") != attempt_id:
            continue
        if entry.get("decision") == PENDING:
            raise ValueError(
                f"{attempt_id} is still PENDING — a decision must be closed before "
                "it can be confirmed"
            )
        if decision is not None:
            if decision not in DECISIONS:
                raise ValueError(f"unknown decision: {decision} (allowed: {DECISIONS})")
            # Snapshot the machine verdict ONCE, on the first override. Re-confirming
            # must not overwrite auto_decision with the already-overridden value —
            # that would erase the fact that a human changed a KILL to a PARK.
            if "auto_decision" not in entry:
                entry["auto_decision"] = entry["decision"]
            entry["decision"] = decision

        entry["human_confirmed"] = True
        entry["decision_source"] = "human"
        entry["confirmed_by"] = by
        entry["confirmed_at"] = _now_iso()
        if note:
            existing = entry.get("decision_note") or ""
            entry["decision_note"] = f"{existing} | {note}".strip(" |")

        _write_ledger(entries, target)
        return entry

    raise ValueError(f"attempt not found in ledger: {attempt_id}")


def unconfirmed_decisions(path: Path | None = None) -> list[dict]:
    """Closed attempts still carrying only a machine verdict.

    Surfaced in every batch report so an auto verdict cannot quietly become the
    record of a decision nobody made.
    """
    return [
        e
        for e in read_ledger(path)
        if e.get("decision") != PENDING and not e.get("human_confirmed")
    ]


def pending_attempts(path: Path | None = None) -> list[dict]:
    """Attempts still open — a non-empty list after a batch means it crashed."""
    return [e for e in read_ledger(path) if e.get("decision") == PENDING]


# ---------------------------------------------------------------------------
# Multiplicity deflation (spec §5.4)
# ---------------------------------------------------------------------------


def sidak_family_p(p_values: Sequence[float]) -> float:
    """Šidák-corrected family p from the minimum of ``k`` within-family p-values.

    The h-variants of one hypothesis are a family: picking the best horizon after
    the fact is selection, and the family p prices that in.
    """
    clean = [float(p) for p in p_values if p is not None and 0.0 <= float(p) <= 1.0]
    if not clean:
        return float("nan")
    k = len(clean)
    p_min = min(clean)
    return 1.0 - (1.0 - p_min) ** k


def benjamini_hochberg(p_values: Sequence[float], q: float = cfg.FDR_Q) -> list[bool]:
    """BH-FDR decisions at level ``q``, returned in the input order."""
    indexed = [(i, float(p)) for i, p in enumerate(p_values) if p is not None and p == p]
    if not indexed:
        return [False] * len(p_values)

    indexed.sort(key=lambda pair: pair[1])
    m = len(indexed)
    cutoff_rank = 0
    for rank, (_, p) in enumerate(indexed, start=1):
        if p <= q * rank / m:
            cutoff_rank = rank

    passing = {idx for idx, _ in indexed[:cutoff_rank]}
    return [i in passing for i in range(len(p_values))]


def deflate(entries: Iterable[dict], q: float = cfg.FDR_Q) -> list[dict]:
    """Deflate the ledger's era-level results for multiplicity.

    One row per (hypothesis family, era): the family p is the Šidák-corrected
    minimum across the family's horizon variants; BH-FDR runs across all families
    in the ledger's entire history, with a Bonferroni second view.
    """
    by_family: dict[tuple[str, str, str], list[float]] = {}
    for entry in entries:
        if entry.get("decision") == PENDING:
            continue
        hyp = entry.get("hyp_id", "")
        lane = entry.get("data_lane", "")
        for era, metrics in (entry.get("metrics") or {}).items():
            p = (metrics or {}).get("p")
            if p is None:
                continue
            by_family.setdefault((hyp, lane, era), []).append(float(p))

    keys = sorted(by_family)
    family_ps = [sidak_family_p(by_family[k]) for k in keys]
    bh_flags = benjamini_hochberg(family_ps, q)
    m = max(1, len(family_ps))

    rows = []
    for (hyp, lane, era), p_family, bh in zip(keys, family_ps, bh_flags):
        rows.append(
            {
                "hyp_id": hyp,
                "data_lane": lane,
                "era": era,
                "n_variants": len(by_family[(hyp, lane, era)]),
                "p_family": p_family,
                "bh_pass": bool(bh),
                "bonferroni_alpha": q / m,
                "bonferroni_pass": bool(p_family <= q / m),
            }
        )
    return rows
