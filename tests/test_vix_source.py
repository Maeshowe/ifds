"""The VIX close: the defect was never the vendor, it was the clock.

Measured on production (2026-04-29 … 2026-10-22, n=113): the recorded ``vix_close``
matched the official CBOE close on **18 days — 15.9%**, with a maximum error of 1.10
(2026-07-09: 16.94 recorded against 15.84 official). Not noise, and not the provider.

The cause is the run time. ``daily_metrics`` fires at 22:10 Budapest = 16:10 ET, FIVE
MINUTES BEFORE the 16:15 ET VIX settlement, for roughly 50 weeks of the year. Whatever
source is asked at that instant answers with a value that is not yet the close.

Measured the same day across all three sources:

* on SETTLED days Polygon I:VIX, FMP ^VIX and FRED VIXCLS are identical to the cent
  (10-15 … 10-22, six sessions, zero difference);
* on the IN-PROGRESS day they disagree and keep moving — 2026-10-23 gave Polygon 20.51,
  FMP 20.10, then FMP 20.35 minutes later.

So switching Polygon → FMP does NOT fix anything on its own; the finality guard does.
FMP is chosen because the Indices line ($49/mo) is being cancelled and FMP ^VIX is
already paid for on the existing plan, while FRED — cent-exact but a day late — stays the
free backstop.

Hermetic: injected clients and an injected clock, no network, no production state.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "paper_trading"))
sys.path.insert(0, str(ROOT / "src"))

import daily_metrics as dm  # noqa: E402

ET = ZoneInfo("America/New_York")
TARGET = "2026-10-23"

#: Verbatim from /stable/historical-price-eod/full?symbol=^VIX, probed 2026-10-23.
EOD_ROWS = [
    {"date": "2026-10-23", "close": 20.35, "volume": 0},
    {"date": "2026-10-22", "close": 19.03, "volume": 0},
    {"date": "2026-10-21", "close": 16.68, "volume": 0},
    {"date": "2026-10-20", "close": 17.31, "volume": 0},
]


def _at(hour: int, minute: int) -> datetime:
    return datetime(2026, 10, 23, hour, minute, tzinfo=ET)


class TestTheFinalityGuard:
    def test_before_the_cutoff_the_days_close_is_refused(self) -> None:
        """16:10 ET is the CURRENT cron instant — five minutes before settlement."""
        close, _prev, reason = dm.vix_from_eod_rows(EOD_ROWS, TARGET, now_et=_at(16, 10))
        assert close is None
        assert reason == "before_settlement"

    def test_it_is_refused_even_though_a_bar_exists(self) -> None:
        """The whole point: the bar IS there, and it is not the close.

        Probed 2026-10-23 within one session: the same route returned 20.10 and then
        20.35. A guard that only checks presence would have taken either.
        """
        assert any(r["date"] == TARGET for r in EOD_ROWS)
        assert dm.vix_from_eod_rows(EOD_ROWS, TARGET, now_et=_at(14, 30))[0] is None

    def test_after_the_cutoff_it_is_accepted(self) -> None:
        close, prev, reason = dm.vix_from_eod_rows(EOD_ROWS, TARGET, now_et=_at(16, 40))
        assert reason is None
        assert close == pytest.approx(20.35)
        assert prev == pytest.approx(19.03), "previous session, for a self-consistent delta"

    @pytest.mark.parametrize("hour,minute,ok", [(16, 14, False), (16, 29, False), (16, 30, True), (17, 0, True)])
    def test_the_cutoff_boundary(self, hour, minute, ok) -> None:
        close, _p, _r = dm.vix_from_eod_rows(EOD_ROWS, TARGET, now_et=_at(hour, minute))
        assert (close is not None) is ok

    def test_the_cutoff_clears_the_settlement_with_margin(self) -> None:
        """VIX settles at 16:15 ET; the extra margin is feed latency, not superstition."""
        assert dm.VIX_FINALITY_CUTOFF_ET.hour == 16
        assert dm.VIX_FINALITY_CUTOFF_ET.minute >= 30

    def test_a_past_date_is_always_final(self) -> None:
        """Yesterday's close does not become more final by waiting."""
        close, _p, reason = dm.vix_from_eod_rows(EOD_ROWS, "2026-10-22", now_et=_at(9, 0))
        assert reason is None and close == pytest.approx(19.03)


class TestTheDateGuardSurvivesTheSourceChange:
    def test_a_missing_bar_is_never_filled_from_the_latest_row(self) -> None:
        rows = [r for r in EOD_ROWS if r["date"] != TARGET]
        close, _p, reason = dm.vix_from_eod_rows(rows, TARGET, now_et=_at(17, 0))
        assert close is None and reason == "no_bar_for_target_date"

    def test_an_empty_response_is_a_reason_not_a_crash(self) -> None:
        assert dm.vix_from_eod_rows([], TARGET, now_et=_at(17, 0))[2] == "no_bars"

    def test_a_missing_previous_bar_still_yields_the_close(self) -> None:
        """prev is for the delta only; its absence must not discard the close."""
        close, prev, reason = dm.vix_from_eod_rows(
            [EOD_ROWS[0]], TARGET, now_et=_at(17, 0)
        )
        assert close == pytest.approx(20.35) and prev is None and reason is None

    def test_index_bars_carry_no_volume_so_no_completeness_floor_applies(self) -> None:
        """Measured: every ^VIX EOD row has volume 0 — the SPY floor cannot be reused."""
        assert all(r["volume"] == 0 for r in EOD_ROWS)
        assert dm.vix_from_eod_rows(EOD_ROWS, TARGET, now_et=_at(17, 0))[0] is not None


class TestTheClientRoutes:
    def test_the_fmp_client_exposes_both_index_routes(self) -> None:
        from ifds.data.fmp import FMPClient

        assert hasattr(FMPClient, "get_index_quote")
        assert hasattr(FMPClient, "get_index_eod")

    def test_the_routes_are_the_ones_measured_live(self) -> None:
        from ifds.data import fmp as fmp_mod

        source = Path(fmp_mod.__file__).read_text()
        assert "/stable/quote" in source
        assert "/stable/historical-price-eod/full" in source

    def test_the_vix_symbol_is_a_named_constant(self) -> None:
        from ifds.data.fmp import VIX_SYMBOL

        assert VIX_SYMBOL == "^VIX"


class TestTheFallbackChain:
    def test_fred_is_used_when_fmp_has_no_final_close(self, monkeypatch) -> None:
        """FRED is cent-exact but a day late — the right backstop, not the primary."""
        monkeypatch.setattr(dm, "_fetch_vix_eod_rows", lambda *_a, **_k: [])
        monkeypatch.setattr(dm, "_fetch_vix_from_fred", lambda d: 19.03)
        close, _prev, source = dm.resolve_vix_close(TARGET, now_et=_at(17, 0))
        assert close == pytest.approx(19.03)
        assert source == "fred"

    def test_no_source_means_no_value_never_a_default(self, monkeypatch) -> None:
        """The hardcoded 20.0 belongs to Phase 0's regime call, never to the research row.

        20.0 sits exactly at vix_penalty_start and below the skip-day threshold, so
        writing it would silently disarm two guards while looking like a measurement.
        """
        monkeypatch.setattr(dm, "_fetch_vix_eod_rows", lambda *_a, **_k: [])
        monkeypatch.setattr(dm, "_fetch_vix_from_fred", lambda d: None)
        close, _prev, source = dm.resolve_vix_close(TARGET, now_et=_at(17, 0))
        assert close is None
        assert source != "default"
        assert close != 20.0

    def test_fmp_wins_when_it_has_a_final_close(self, monkeypatch) -> None:
        monkeypatch.setattr(dm, "_fetch_vix_eod_rows", lambda *_a, **_k: EOD_ROWS)
        monkeypatch.setattr(
            dm, "_fetch_vix_from_fred", lambda d: pytest.fail("FRED must not be reached")
        )
        close, prev, source = dm.resolve_vix_close(TARGET, now_et=_at(17, 0))
        assert close == pytest.approx(20.35) and prev == pytest.approx(19.03)
        assert source == "fmp"


class TestTheDateArithmeticIsZoneAnchored:
    def test_the_cutoff_is_evaluated_in_eastern_time_not_locally(self) -> None:
        """22:40 Budapest is 16:40 ET in winter and 17:40 ET in the DST gap week — the
        guard must key off ET, or it would pass in one week and fail in the next."""
        budapest = ZoneInfo("Europe/Budapest")
        winter = datetime(2026, 11, 2, 22, 40, tzinfo=budapest).astimezone(ET)
        gap_week = datetime(2026, 10, 27, 22, 40, tzinfo=budapest).astimezone(ET)
        assert winter.hour == 16 and winter.minute == 40
        assert gap_week.hour == 17 and gap_week.minute == 40
        for moment in (winter, gap_week):
            assert dm.vix_from_eod_rows(EOD_ROWS, TARGET, now_et=moment)[0] is not None

    def test_the_target_date_is_parsed_not_inferred_from_the_clock(self) -> None:
        assert dm.vix_from_eod_rows(EOD_ROWS, "2026-10-21", now_et=_at(9, 0))[0] == pytest.approx(16.68)
        assert date.fromisoformat("2026-10-21") < date.fromisoformat(TARGET)


class TestPhase0UsesTheSameSourceSwap:
    """Phase 0 is the biggest I:VIX caller — 237 of 287 production runs — so the Indices
    line cannot be cancelled while it still asks Polygon for the index.

    The swap is deliberately SEMANTICS-PRESERVING. Phase 0 runs at 08:30 ET (pre-market)
    and at 22:00 Sunday; at both instants Polygon's `get_vix` returns the last settled
    daily close. FMP's `previousClose` is that same number, officially final — probed
    2026-10-23: previousClose 19.03, which is exactly the official 10-22 CBOE close. So
    this changes where the number comes from, not what it means.
    """

    def test_it_reads_the_official_previous_close(self) -> None:
        from ifds.phases.phase0_diagnostics import _vix_from_fmp_quote

        assert _vix_from_fmp_quote({"price": 20.24, "previousClose": 19.03}) == pytest.approx(19.03)

    def test_it_does_not_take_the_live_intraday_price(self) -> None:
        """`price` moves all session — the same trap the daily_metrics guard exists for."""
        from ifds.phases.phase0_diagnostics import _vix_from_fmp_quote

        assert _vix_from_fmp_quote({"price": 99.0, "previousClose": 19.03}) == pytest.approx(19.03)

    @pytest.mark.parametrize("quote", [None, {}, {"previousClose": None}, {"previousClose": "n/a"}])
    def test_an_unusable_quote_yields_none_so_the_chain_falls_through(self, quote) -> None:
        from ifds.phases.phase0_diagnostics import _vix_from_fmp_quote

        assert _vix_from_fmp_quote(quote) is None

    def test_the_module_no_longer_asks_polygon_for_the_index(self) -> None:
        from ifds.phases import phase0_diagnostics as diag

        source = Path(diag.__file__).read_text()
        assert "polygon.get_vix" not in source, (
            "Phase 0 still calls Polygon for I:VIX; the Indices subscription cannot be "
            "cancelled while this path is live (237 of 287 production runs used it)"
        )


class TestPtMonitorAlsoLeavesThePolygonIndex:
    """The last live Polygon I:VIX caller, so the Indices line can go without a stub left.

    `pt_monitor --mode=eod_eval` is trading-guarded and dormant today, which is exactly
    why it is the right moment to move it: a dormant path that breaks on a cancelled
    entitlement is a landmine for the restart, not a problem for today.

    It uses the SAME clock-guarded resolver as daily_metrics rather than a second
    hand-rolled fetch — the whole point of the 2026-10-23 work is that presence of a bar
    is not evidence that it is the close, and that lesson should not need re-learning per
    call site.
    """

    def test_the_module_no_longer_asks_polygon_for_the_index(self) -> None:
        source = (ROOT / "scripts" / "paper_trading" / "pt_monitor.py").read_text()
        assert '"I:VIX"' not in source, (
            "pt_monitor still fetches Polygon I:VIX; cancelling the Indices product "
            "would silently leave vix_close and vix_delta_pct empty on the restart"
        )

    def test_it_reuses_the_guarded_resolver(self) -> None:
        source = (ROOT / "scripts" / "paper_trading" / "pt_monitor.py").read_text()
        assert "resolve_vix_close" in source, (
            "a second, unguarded VIX fetch would reintroduce the pre-settlement defect "
            "that cost the daily_metrics field 84% of its accuracy"
        )

    def test_the_delta_is_computed_from_the_resolver_s_own_previous_close(self) -> None:
        """A self-consistent pair, like the daily_metrics path — never today's close
        against a previous close pulled from a different request."""
        import importlib

        spec = importlib.util.spec_from_file_location(
            "_ptm", ROOT / "scripts" / "paper_trading" / "pt_monitor.py"
        )
        assert spec is not None
        source = (ROOT / "scripts" / "paper_trading" / "pt_monitor.py").read_text()
        assert "vix_prev" in source and "vix_delta_pct" in source
        assert source.count("resolve_vix_close(") == 1, "one call, one consistent pair"


class TestNoPolygonIndexEntitlementIsNeededAnywhere:
    """From 2026-10-26 the Polygon/Massive Indices product is cancelled and I:VIX 403s.

    A dead function that still names the endpoint is this repo's recurring trap: the
    Cross-Asset layer threw for 6.5 months behind a bare `except`, and the FMP schema
    defects read None for eight. So the guard is not "the live path works" — that was
    proven on production with the Polygon client sabotaged — it is that NO call site
    exists at all, including in code nobody runs.
    """

    def _sources(self):
        import subprocess

        out = subprocess.run(
            ["git", "ls-files", "-z", "src", "scripts"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout
        return [ROOT / n for n in out.split("\0") if n.endswith(".py")]

    def test_no_file_requests_the_index_ticker(self) -> None:
        offenders: list[str] = []
        for path in self._sources():
            for i, line in enumerate(path.read_text().splitlines(), 1):
                if '"I:VIX"' in line or "'I:VIX'" in line:
                    offenders.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()[:70]}")
        assert not offenders, (
            "a Polygon Indices call site survives; it will return 403 from 2026-10-26:\n"
            + "\n".join(offenders)
        )

    def test_the_sweep_actually_reads_files(self) -> None:
        """A guard whose file list is empty passes while guarding nothing."""
        paths = self._sources()
        assert len(paths) > 50, f"git ls-files returned only {len(paths)} python files"

    def test_the_polygon_client_has_no_index_method_left(self) -> None:
        from ifds.data.polygon import PolygonClient

        assert not hasattr(PolygonClient, "get_vix"), (
            "PolygonClient.get_vix reads the Indices product; it has no production "
            "callers and must not be left as a loaded gun"
        )
