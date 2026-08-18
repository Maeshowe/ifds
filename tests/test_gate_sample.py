"""Tests for scripts/analysis/gate_sample.py — the §5 sample-definition wrapper.

The wrapper exists because the pinned attribution tool (c5e9ed0) implements only
data-availability exclusions, while gate-protocol §6/2 defines the sample as
"entry-based clean cut + the §5 exclusions". Decision (Tamás, 2026-08-18): wrapper,
not re-pinning — the pin's inviolability is the point of G1.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = _ROOT / "scripts" / "analysis" / "gate_sample.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sa = _load("signal_attribution", _ROOT / "scripts" / "analysis" / "signal_attribution.py")
gs = _load("gate_sample", _SCRIPT)


def _trade(ticker: str, entry_date: str, realized_r: float = 0.0) -> "sa.Trade":
    return sa.Trade(
        ticker=ticker,
        entry_date=entry_date,
        entry_price=100.0,
        entry_score=80.0,
        sector="Industrials",
        exit_type="TIME_STOP",
        realized_r=realized_r,
    )


def _loaded(ticker: str, entry_date: str, exit_date: str = "2026-08-01", day: int = 20):
    return sa.LoadedTrade(
        trade=_trade(ticker, entry_date),
        entry_day_number=day,
        exit_date=exit_date,
        exit_day_number=day + 6,
    )


# --- §5.2 outage-delayed exits -------------------------------------------------


def test_the_four_late_exits_are_dropped():
    loaded = [
        _loaded("PFGC", "2026-07-08"),
        _loaded("BIRK", "2026-07-08"),
        _loaded("USFD", "2026-07-14"),
        _loaded("DE", "2026-07-30"),
        _loaded("SAIC", "2026-07-31"),
    ]
    kept, dropped = gs.apply_s5_exclusions(loaded)
    assert [lt.trade.ticker for lt in kept] == ["SAIC"]
    assert {e.ticker for e in dropped} == {"PFGC", "BIRK", "USFD", "DE"}
    assert all(e.reason == gs.REASON_LATE_EXIT for e in dropped)


def test_exclusion_is_position_keyed_not_ticker_keyed():
    """The PRIMARY regression: only the 07-08 PFGC is late — the other two stay.

    A ticker-keyed filter would silently drop three PFGC positions instead of one,
    shrinking the gate sample without any report line saying so.
    """
    loaded = [
        _loaded("PFGC", "2026-06-25"),  # clean
        _loaded("PFGC", "2026-07-08"),  # §5 late exit
        _loaded("PFGC", "2026-07-21"),  # clean (self-reentry, NOT excluded per §5.5)
    ]
    kept, dropped = gs.apply_s5_exclusions(loaded)
    assert [lt.trade.entry_date for lt in kept] == ["2026-06-25", "2026-07-21"]
    assert len(dropped) == 1
    assert dropped[0].entry_date == "2026-07-08"


def test_self_reentry_positions_are_not_excluded():
    """§5.5: self-reentry is normal strategy behaviour, not an outage artifact."""
    loaded = [_loaded("PFGC", "2026-07-21"), _loaded("USFD", "2026-07-23")]
    kept, dropped = gs.apply_s5_exclusions(loaded)
    assert len(kept) == 2
    assert dropped == []


# --- §5.1 outage days ----------------------------------------------------------


def test_entry_on_an_outage_day_is_dropped():
    loaded = [_loaded("FOO", "2026-07-22"), _loaded("BAR", "2026-08-04")]
    kept, dropped = gs.apply_s5_exclusions(loaded)
    assert [lt.trade.ticker for lt in kept] == ["BAR"]
    assert dropped[0].reason == gs.REASON_ENTRY_ON_OUTAGE


def test_declared_outage_days_are_nine_trading_days_in_five_events():
    assert len(gs.OUTAGE_DAYS) == 9
    assert len(gs.OUTAGE_EVENTS) == 5
    assert sum(len(e.days) for e in gs.OUTAGE_EVENTS) == 9
    assert {d for e in gs.OUTAGE_EVENTS for d in e.days} == set(gs.OUTAGE_DAYS)


DAY63 = "2026-08-17"


def _write_era(metrics: Path, skip: set[str], end: str = DAY63) -> None:
    metrics.mkdir(exist_ok=True)
    for day in gs.era_trading_days(end=end):
        if day not in skip:
            (metrics / f"{day}.json").write_text("{}")


def test_verify_outage_days_accepts_a_matching_state(tmp_path):
    metrics = tmp_path / "daily_metrics"
    _write_era(metrics, skip=set(gs.OUTAGE_DAYS))
    gs.verify_outage_days(metrics)  # must not raise


def test_verify_outage_days_raises_when_a_new_outage_is_unlisted(tmp_path):
    """A new outage day that nobody added to §5 must fail LOUDLY, not pass silently."""
    metrics = tmp_path / "daily_metrics"
    _write_era(metrics, skip={*gs.OUTAGE_DAYS, "2026-08-12"})
    with pytest.raises(gs.SampleIntegrityError, match="2026-08-12"):
        gs.verify_outage_days(metrics)


def test_a_new_outage_AFTER_the_last_declared_one_is_still_caught(tmp_path):
    """The guard must range to the DATA FRONTIER, not to the last known outage.

    Ranging only to max(OUTAGE_DAYS) would make the guard blind to precisely the case
    it exists for: the next outage, which by definition comes after the last one.
    """
    metrics = tmp_path / "daily_metrics"
    _write_era(metrics, skip={*gs.OUTAGE_DAYS, "2026-08-14"})
    with pytest.raises(gs.SampleIntegrityError, match="2026-08-14"):
        gs.verify_outage_days(metrics)


def test_verify_outage_days_raises_when_a_listed_day_has_data(tmp_path):
    metrics = tmp_path / "daily_metrics"
    _write_era(metrics, skip=set(gs.OUTAGE_DAYS))
    (metrics / "2026-07-22.json").write_text("{}")  # a declared outage day WITH data
    with pytest.raises(gs.SampleIntegrityError, match="2026-07-22"):
        gs.verify_outage_days(metrics)


def test_verify_outage_days_passes_on_the_real_state():
    """The declared §5.1 list must match the actual production state, today."""
    gs.verify_outage_days(Path(__file__).resolve().parent.parent / "state" / "daily_metrics")


# --- equivalence with the pinned tool ------------------------------------------


def test_empty_exclusion_list_is_a_no_op(monkeypatch):
    """With §5 empty the wrapper must return exactly the pinned tool's sample."""
    monkeypatch.setattr(gs, "LATE_EXIT_POSITIONS", frozenset())
    monkeypatch.setattr(gs, "OUTAGE_DAYS", frozenset())
    loaded = [_loaded("PFGC", "2026-07-08"), _loaded("USFD", "2026-07-14")]
    kept, dropped = gs.apply_s5_exclusions(loaded)
    assert kept == loaded
    assert dropped == []


def test_exclusions_are_signal_attribution_Exclusion_objects():
    """The dropped rows must render in the pinned report's exclusion section."""
    kept, dropped = gs.apply_s5_exclusions([_loaded("DE", "2026-07-30")])
    assert isinstance(dropped[0], sa.Exclusion)


def test_wrapper_does_not_mutate_the_input_list():
    loaded = [_loaded("DE", "2026-07-30"), _loaded("SAIC", "2026-07-31")]
    before = list(loaded)
    gs.apply_s5_exclusions(loaded)
    assert loaded == before
