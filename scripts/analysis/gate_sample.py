#!/usr/bin/env python3
"""§5 sample-definition wrapper for the pinned attribution tool.

Gate-protocol §6/2 defines the gate sample as "entry-based clean cut + the §5
exclusions". The pinned tool (``signal_attribution.py`` @ **c5e9ed0**) implements
only the DATA-AVAILABILITY exclusions — the §5 SAMPLE-INTEGRITY exclusions (outage
days, outage-delayed exits) are not in it. The pre-registration is the canon, so the
tool is what deviates.

Decision (Tamás, 2026-08-18, protocol §5.6): **wrapper, not re-pinning.** The pin's
inviolability is the point of G1, and §6/2 puts the SAMPLE in the protocol's remit,
not the tool's. Consequently this module:

  * imports the pinned analysis functions — never copies or edits them,
  * verifies at run time that the pin is unchanged (§6/1, enforced mechanically),
  * carries the §5 list as FROZEN data with its protocol source,
  * self-checks the declared outage days against the actual state (a new outage that
    nobody added to §5 fails LOUDLY rather than passing silently).

Read-only: writes nothing to the trading state.

    python scripts/analysis/gate_sample.py --as-of 2026-09-22
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent
_PINNED_SCRIPT = _HERE / "signal_attribution.py"

#: The pin the gate run is contracted to (§6/1). Changing it requires the new pin and
#: the reason to be written into 04-risks BEFORE the run.
PINNED_COMMIT = "c5e9ed0"


def _load_pinned():
    # Reuse an existing import so there is exactly ONE Exclusion/Trade class in the
    # process — a second module instance would make isinstance() checks fail and let
    # subtly different dataclasses flow into the same report.
    existing = sys.modules.get("signal_attribution")
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location("signal_attribution", _PINNED_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sa = _load_pinned()


class SampleIntegrityError(RuntimeError):
    """The declared §5 sample does not match reality — refuse to produce a sample."""


# ---------------------------------------------------------------------------
# §5.1 — outage days (9 trading days, 5 events). Source: gate-protocol §5.1.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutageEvent:
    """One outage, with the trading days it swallowed."""

    name: str
    days: tuple[str, ...]
    cause: str


OUTAGE_EVENTS: tuple[OutageEvent, ...] = (
    OutageEvent(
        "Mini SSH-orphan",
        ("2026-06-29", "2026-06-30", "2026-07-01", "2026-07-02", "2026-07-06"),
        "orphan prod-process (07-03 holiday)",
    ),
    OutageEvent("Áramszünet I", ("2026-07-15",), "power outage"),
    OutageEvent("Áramszünet II", ("2026-07-16",), "power outage"),
    OutageEvent("FileVault I", ("2026-07-22",), "unlock screen, ~26h"),
    OutageEvent("FileVault II", ("2026-08-07",), "unlock screen, ~13h"),
)

OUTAGE_DAYS: frozenset[str] = frozenset(d for e in OUTAGE_EVENTS for d in e.days)

# ---------------------------------------------------------------------------
# §5.2 — outage-delayed exits (6 positions, 4 events). Source: gate-protocol §5.2.
#
# POSITION-keyed (ticker, entry_date), never ticker-keyed: PFGC and USFD each hold
# several positions in the era and only ONE of each is outage-delayed. A ticker-keyed
# filter would silently shrink the sample.
#
# ITT/XPO are listed for completeness — they already fall out upstream on
# data-availability grounds (manual reconcile, no per-leg P&L).
# ---------------------------------------------------------------------------

LATE_EXIT_POSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("ITT", "2026-07-07"),
        ("XPO", "2026-07-07"),
        ("PFGC", "2026-07-08"),
        ("BIRK", "2026-07-08"),
        ("USFD", "2026-07-14"),
        ("DE", "2026-07-30"),
    }
)

REASON_LATE_EXIT = "gate-protokoll §5.2 — outage-késleltetett exit"
REASON_ENTRY_ON_OUTAGE = "gate-protokoll §5.1 — belépés outage-napon"

SWING_ERA_START = "2026-05-18"


# ---------------------------------------------------------------------------
# Integrity self-check
# ---------------------------------------------------------------------------


def era_trading_days(start: str = SWING_ERA_START, end: str | None = None) -> tuple[str, ...]:
    """NYSE sessions of the swing era, ascending. ``end`` defaults to the last outage."""
    import exchange_calendars as xcals

    last = end or max(OUTAGE_DAYS)
    sessions = xcals.get_calendar("XNYS").sessions_in_range(start, last)
    return tuple(d.date().isoformat() for d in sessions)


def verify_outage_days(metrics_dir: Path, end: str | None = None) -> None:
    """Assert the declared §5.1 list == the trading days actually missing from state.

    Raises ``SampleIntegrityError`` on either mismatch direction:
      * a trading day with no ``daily_metrics`` that §5.1 does not list (a NEW outage
        nobody recorded — the case this guard exists for), or
      * a declared outage day that does have data (the list is stale).

    ``end`` defaults to the **data frontier** (the latest day present in the state),
    NOT to the last known outage: a new outage after the last declared one has to fall
    inside the checked range, or the guard would be blind to exactly what it is for.
    """
    present = {p.stem[:10] for p in Path(metrics_dir).glob("*.json")}
    era_present = {d for d in present if d >= SWING_ERA_START}
    frontier = end or (max(era_present) if era_present else max(OUTAGE_DAYS))
    days = era_trading_days(end=frontier)
    missing = {d for d in days if d not in present}
    declared = {d for d in OUTAGE_DAYS if d in days}

    unlisted = sorted(missing - declared)
    if unlisted:
        raise SampleIntegrityError(
            f"Trading nap adat nélkül, de a §5.1 nem sorolja: {', '.join(unlisted)}. "
            "Új outage → a gate-protokoll §5.1 frissítendő a kapu-futás ELŐTT."
        )
    spurious = sorted(declared - missing)
    if spurious:
        raise SampleIntegrityError(
            f"A §5.1 outage-napként sorolja, de van adata: {', '.join(spurious)}. "
            "A lista elavult — a kapu-futás ELŐTT tisztázandó."
        )


def verify_pin(commit: str = PINNED_COMMIT) -> None:
    """§6/1 mechanically: refuse to run if the pinned tool has drifted off its pin."""
    result = subprocess.run(
        ["git", "diff", "--quiet", commit, "--", str(_PINNED_SCRIPT)],
        cwd=_REPO,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SampleIntegrityError(
            f"A pinelt eszköz eltér a {commit} pintől. A §6/1 szerint a pin nem "
            "változhat a futás előtt; ha mégis, az új pin és az ok a 04-risks-be kerül ELŐTTE."
        )


# ---------------------------------------------------------------------------
# The §5 filter
# ---------------------------------------------------------------------------


def apply_s5_exclusions(
    loaded: list["sa.LoadedTrade"],
) -> tuple[list["sa.LoadedTrade"], list["sa.Exclusion"]]:
    """Split the loaded trades into (kept, §5-excluded).

    Two categories, reported separately so the report shows WHY each row left:
      * ``REASON_ENTRY_ON_OUTAGE`` — entry on an outage day. Expected to be a no-op
        (no pipeline events on those days); a defensive guard, and a finding if it
        ever fires.
      * ``REASON_LATE_EXIT`` — the §5.2 position list.

    Does not mutate ``loaded``.
    """
    kept: list["sa.LoadedTrade"] = []
    dropped: list["sa.Exclusion"] = []
    for lt in loaded:
        trade = lt.trade
        if trade.entry_date in OUTAGE_DAYS:
            reason = REASON_ENTRY_ON_OUTAGE
        elif (trade.ticker, trade.entry_date) in LATE_EXIT_POSITIONS:
            reason = REASON_LATE_EXIT
        else:
            kept.append(lt)
            continue
        dropped.append(sa.Exclusion(trade.ticker, trade.entry_date, lt.exit_date, reason))
    return kept, dropped


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover — I/O orchestration, runs at the gate
    import os

    parser = argparse.ArgumentParser(description="Gate sample (§5) + pinned attribution")
    parser.add_argument("--as-of", default="today", help="evaluation date label")
    parser.add_argument("--state-dir", default="state", help="trading state root (read-only)")
    parser.add_argument("--out-dir", default="docs/analysis", help="report output directory")
    parser.add_argument(
        "--skip-pin-check", action="store_true", help="diagnostics only — never at the gate"
    )
    args = parser.parse_args()

    if not args.skip_pin_check:
        verify_pin()
    state = Path(args.state_dir)
    verify_outage_days(state / "daily_metrics")

    loaded, data_exclusions = sa.load_closed_trades(
        state / "pending_exits", state / "daily_metrics", state / "phase4_snapshots"
    )
    kept, s5_exclusions = apply_s5_exclusions(loaded)
    exclusions = list(data_exclusions) + s5_exclusions
    print(
        f"betöltve {len(loaded)} | adat-kizárás {len(data_exclusions)} | "
        f"§5-kizárás {len(s5_exclusions)} → minta n={len(kept)}"
    )

    api_key = os.environ.get("IFDS_POLYGON_API_KEY")
    if not api_key:
        raise SystemExit("Set IFDS_POLYGON_API_KEY to fetch forward returns.")

    from ifds.data.cache import FileCache
    from ifds.data.polygon import PolygonClient

    fetcher = sa.polygon_bar_fetcher(PolygonClient(api_key=api_key, cache=FileCache()))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for label, trades in sa.split_samples(kept).items():
        fwd = sa.fetch_forward_returns(trades, fetcher)
        report = sa.run_attribution(trades, fwd)
        md = sa.render_report(report, f"{args.as_of} (§5-minta, {label})", False, exclusions)
        path = out_dir / f"gate-sample-attribution-{args.as_of}-{label}.md"
        path.write_text(md)
        print(f"[{label}] n={len(trades)} → {path}")


if __name__ == "__main__":
    main()
