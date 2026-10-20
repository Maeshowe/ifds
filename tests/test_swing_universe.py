"""Swing universe source tests (Day 63 §3.9 Döntés 9, 2026-05-18).

Covers:
  * The :class:`_FirstColumnSymbolParser` HTML parser against fixture HTML
    that mirrors both the S&P 500 layout (Symbol = first td) and the
    Russell 1000 layout (Symbol = second td).
  * The :class:`SwingUniverseSource` cache lifecycle (write, read, expiry).
  * Wikipedia fetch failure → FMP fallback → final failure raising.
  * Phase 2 integration: legacy fmp_screener path unchanged, swing path
    intersects the screener result with the union membership set, swing
    fetch failure falls back to the raw screener.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ifds.config.loader import Config
from ifds.data.swing_universe import (
    SwingUniverseSource,
    _parse_symbols,
    fetch_from_fmp_fallback,
)
from ifds.events.logger import EventLogger
from ifds.phases.phase2_universe import _screen_long_universe

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config(monkeypatch, tmp_path):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    monkeypatch.setenv("IFDS_ASYNC_ENABLED", "false")
    cfg = Config()
    cfg.tuning["swing_universe_cache_dir"] = str(tmp_path / "swing_universe")
    return cfg


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-swing-universe")


SP500_LIKE_HTML = """
<html><body>
<table class="wikitable sortable" id="constituents">
<tbody>
<tr><th>Symbol</th><th>Security</th><th>Sector</th></tr>
<tr><td><a href="...">MMM</a></td><td>3M</td><td>Industrials</td></tr>
<tr><td><a href="...">AAPL</a></td><td>Apple</td><td>Technology</td></tr>
<tr><td><a href="...">BRK.B</a></td><td>Berkshire</td><td>Financials</td></tr>
</tbody>
</table>
</body></html>
"""

R1000_LIKE_HTML = """
<html><body>
<table class="wikitable">
<tr><td>noise</td></tr>
</table>
<table class="wikitable sortable" id="constituents">
<tbody>
<tr><th>Company</th><th>Symbol</th><th>Sector</th></tr>
<tr><td><a href="...">3M</a></td><td>MMM</td><td>Industrials</td></tr>
<tr><td><a href="...">A. O. Smith</a></td><td>AOS</td><td>Industrials</td></tr>
<tr><td><a href="...">Apple</a></td><td>AAPL</td><td>Technology</td></tr>
</tbody>
</table>
</body></html>
"""


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestParser:
    def test_sp500_layout_first_column(self):
        symbols = _parse_symbols(SP500_LIKE_HTML)
        assert symbols == ["MMM", "AAPL", "BRK-B"]

    def test_russell_layout_second_column(self):
        symbols = _parse_symbols(R1000_LIKE_HTML)
        # The first "noise" wikitable has no `id="constituents"` so it is skipped;
        # the second is the components table, Symbol is the SECOND column.
        assert symbols == ["MMM", "AOS", "AAPL"]

    def test_class_share_normalization(self):
        # BRK.B / BRK-B both normalized to hyphen form
        html = (
            '<table class="wikitable" id="constituents">'
            "<tr><th>Symbol</th></tr>"
            "<tr><td>BRK.B</td></tr>"
            "<tr><td>BF-A</td></tr>"
            "</table>"
        )
        assert _parse_symbols(html) == ["BRK-B", "BF-A"]

    def test_filters_non_ticker_tokens(self):
        html = (
            '<table class="wikitable" id="constituents">'
            "<tr><th>Symbol</th></tr>"
            "<tr><td>AAPL</td></tr>"
            "<tr><td>Not-A-Ticker-1234</td></tr>"
            "<tr><td></td></tr>"
            "<tr><td>MSFT</td></tr>"
            "</table>"
        )
        assert _parse_symbols(html) == ["AAPL", "MSFT"]


# ---------------------------------------------------------------------------
# Cache lifecycle
# ---------------------------------------------------------------------------


class TestCacheLifecycle:
    def test_get_universe_writes_cache_on_first_call(self, tmp_path):
        source = SwingUniverseSource(cache_dir=tmp_path)
        with (
            patch(
                "ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                return_value=[f"X{i:04d}" for i in range(500)],
            ),
            patch(
                "ifds.data.swing_universe.fetch_russell1000_from_wikipedia",
                return_value=[f"X{i:04d}" for i in range(1000)],
            ),
        ):
            symbols = source.get_universe()
        assert 950 <= len(symbols) <= 1100
        cache = json.loads((tmp_path / "universe.json").read_text())
        assert cache["count"] == len(symbols)
        assert "fetched_at" in cache

    def test_fresh_cache_skips_fetch(self, tmp_path):
        cache_payload = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "count": 1000,
            "symbols": [f"X{i:04d}" for i in range(1000)],
        }
        (tmp_path / "universe.json").write_text(json.dumps(cache_payload))

        source = SwingUniverseSource(cache_dir=tmp_path)
        with patch("ifds.data.swing_universe.fetch_sp500_from_wikipedia") as mock_sp:
            symbols = source.get_universe()
            mock_sp.assert_not_called()
        assert len(symbols) == 1000

    def test_expired_cache_triggers_refetch(self, tmp_path):
        old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        (tmp_path / "universe.json").write_text(
            json.dumps(
                {
                    "fetched_at": old_ts,
                    "count": 1000,
                    "symbols": [f"OLD{i:03d}" for i in range(1000)],
                }
            )
        )
        source = SwingUniverseSource(cache_dir=tmp_path, cache_ttl_days=7)
        with (
            patch(
                "ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                return_value=[f"NEW{i:04d}" for i in range(500)],
            ),
            patch(
                "ifds.data.swing_universe.fetch_russell1000_from_wikipedia",
                return_value=[f"NEW{i:04d}" for i in range(1000)],
            ),
        ):
            result = source.get_universe()
        assert result.symbols[0].startswith("NEW")  # not OLD
        assert result.degraded_stale is False
        assert result.source == "wikipedia"

    def test_expired_cache_is_SERVED_when_the_refetch_fails(self, tmp_path):
        """The TTL inversion (D-U1/F-1a): stale membership beats a swapped population.

        The old code returned None from an expired cache, which sent the caller down
        the screener fallback — a DIFFERENT population. Nine consecutive weekly runs
        (2026-08-16 .. 10-19) degraded that way in silence. Measured afterwards: a
        77-day-old list differs from today's by Jaccard 0.927 (a few percent), while
        the substitution swapped 377 of 730 names (52%) for non-members.
        """
        old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        (tmp_path / "universe.json").write_text(
            json.dumps(
                {
                    "fetched_at": old_ts,
                    "count": 1000,
                    "symbols": [f"OLD{i:03d}" for i in range(1000)],
                }
            )
        )
        source = SwingUniverseSource(cache_dir=tmp_path, cache_ttl_days=7)
        with (
            patch(
                "ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                side_effect=RuntimeError("page moved"),
            ),
            patch("ifds.data.swing_universe.fetch_from_fmp_fallback", return_value=None),
        ):
            result = source.get_universe()
        assert result.symbols[0].startswith("OLD"), "the stale list must be served"
        assert result.degraded_stale is True
        assert result.source == "cache"
        assert 9.0 < result.age_days < 11.0

    def test_no_cache_and_failed_fetch_RAISES_rather_than_substituting(self, tmp_path):
        """F-1c: the absence of any membership must stop the pipeline, not degrade it."""
        source = SwingUniverseSource(cache_dir=tmp_path, cache_ttl_days=7)
        with (
            patch(
                "ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                side_effect=RuntimeError("page moved"),
            ),
            patch("ifds.data.swing_universe.fetch_from_fmp_fallback", return_value=None),
            pytest.raises(RuntimeError, match="no usable"),
        ):
            source.get_universe()

    def test_the_staleness_alarm_escalates(self, tmp_path, caplog):
        """F-1b: WARNING past the TTL, ERROR past 45 days."""
        import logging

        from ifds.data import swing_universe as su

        def _serve_stale(age_days: int):
            ts = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat()
            (tmp_path / "universe.json").write_text(
                json.dumps(
                    {
                        "fetched_at": ts,
                        "count": 1000,
                        "symbols": [f"OLD{i:03d}" for i in range(1000)],
                    }
                )
            )
            src = SwingUniverseSource(cache_dir=tmp_path, cache_ttl_days=7)
            with (
                patch(
                    "ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                    side_effect=RuntimeError("page moved"),
                ),
                patch("ifds.data.swing_universe.fetch_from_fmp_fallback", return_value=None),
                caplog.at_level(logging.INFO, logger=su.logger.name),
            ):
                caplog.clear()
                src.get_universe()
            return {r.levelno for r in caplog.records}

        assert logging.WARNING in _serve_stale(10), "past the TTL must WARN"
        assert logging.ERROR not in _serve_stale(10)
        assert logging.ERROR in _serve_stale(su.STALE_ERROR_DAYS + 5), "past 45d must ERROR"

    def test_provenance_is_recorded_for_the_context(self, tmp_path):
        """F-2: every downstream artifact must be able to say what it ran on."""
        source = SwingUniverseSource(cache_dir=tmp_path, cache_ttl_days=7)
        with (
            patch(
                "ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                return_value=[f"X{i:04d}" for i in range(503)],
            ),
            patch(
                "ifds.data.swing_universe.fetch_russell1000_from_wikipedia",
                return_value=[f"X{i:04d}" for i in range(1021)],
            ),
        ):
            prov = source.get_universe().provenance()
        assert set(prov) == {"source", "fetched_at", "count", "age_days", "degraded_stale"}
        assert prov["source"] == "wikipedia"
        assert prov["count"] == 1021
        assert prov["degraded_stale"] is False

    def test_corrupt_cache_falls_through_to_fetch(self, tmp_path):
        (tmp_path / "universe.json").write_text("{ not valid json")
        source = SwingUniverseSource(cache_dir=tmp_path)
        with (
            patch(
                "ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                return_value=[f"X{i:04d}" for i in range(500)],
            ),
            patch(
                "ifds.data.swing_universe.fetch_russell1000_from_wikipedia",
                return_value=[f"X{i:04d}" for i in range(1000)],
            ),
        ):
            symbols = source.get_universe()
        assert len(symbols) >= 950


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


class TestFailureModes:
    def test_wikipedia_fail_fmp_succeeds(self, tmp_path):
        """The FMP fallback, with fixtures shaped like the LIVE payloads.

        The previous version of this test fed ``{"symbol": "X0000"}`` rows to both
        legs. Production never returns that for the Russell leg: an ETF-holdings row
        carries the ETF in ``symbol`` and the constituent in ``asset``. The test was
        therefore green against a payload shape that could not occur, which is how a
        fallback that had been structurally dead since 2026-05-18 kept a passing test.

        Schemas captured live on 2026-10-19 with the production key:
          /stable/sp500-constituent  -> 503 rows, keys include symbol, name, sector, cik
          /stable/etf/holdings?symbol=IWB -> 1026 rows, 1021 distinct `asset`,
            exactly 1 distinct `symbol` ("IWB" — the fund itself),
            keys: asset, isin, marketValue, name, securityCusip, sharesNumber,
                  symbol, updatedAt, weightPercentage
        """
        source = SwingUniverseSource(cache_dir=tmp_path)
        fmp = MagicMock()
        fmp._api_key = "k"
        fmp._auth_headers = lambda: {}
        # S&P 500 leg: constituent rows keyed by `symbol`.
        sp500_rows = [
            {"symbol": f"X{i:04d}", "name": f"Co {i}", "sector": "Technology"}
            for i in range(503)
        ]
        # Russell leg: ETF-holdings rows. `symbol` is the FUND on every row; the
        # constituent is `asset`. The overlap mirrors reality (S&P 500 is almost a
        # subset of the Russell 1000).
        iwb_rows = [
            {
                "symbol": "IWB",
                "asset": f"X{i:04d}",
                "name": f"Co {i}",
                "weightPercentage": 0.1,
                "updatedAt": "2026-10-19 13:45:55",
            }
            for i in range(1021)
        ]
        fmp._get.side_effect = [sp500_rows, iwb_rows]
        with patch(
            "ifds.data.swing_universe.fetch_sp500_from_wikipedia",
            side_effect=RuntimeError("wiki down"),
        ):
            symbols = source.get_universe(fmp_client=fmp)
        assert 950 <= len(symbols) <= 1100
        assert "IWB" not in symbols, "the fund itself must never enter the universe"

    def test_the_etf_leg_reads_asset_not_symbol(self, tmp_path):
        """Guard the trap directly: reading `symbol` collapses the union to 504.

        Measured live: `symbol` has exactly 1 distinct value across all 1026 IWB rows.
        If a refactor reverts the field, the union falls to ~504, the 950-1100 guard
        rejects it and the system falls open to the legacy screener — silently, which
        is exactly how this went unnoticed for nine weeks.
        """
        from ifds.data import swing_universe as su

        fmp = MagicMock()
        fmp._api_key = "k"
        fmp._auth_headers = lambda: {}
        fmp._get.side_effect = [
            [{"symbol": f"X{i:04d}"} for i in range(503)],
            [{"symbol": su.R1000_ETF, "asset": f"X{i:04d}"} for i in range(1021)],
        ]
        union = su.fetch_from_fmp_fallback(fmp)
        assert union is not None, "the live-shaped payload must satisfy the guard"
        assert len(union) == 1021
        assert su.R1000_ETF not in union

    def test_the_etf_leg_requests_iwb_holdings_not_the_dead_endpoint(self, tmp_path):
        """`/stable/russell1000-constituent` never existed — it must not be called.

        Probed 2026-10-19 on the production key: 404 with a body byte-identical to a
        fabricated route, while sp500/nasdaq/dowjones return 200 on the same key.
        """
        from ifds.data import swing_universe as su

        fmp = MagicMock()
        fmp._api_key = "k"
        fmp._auth_headers = lambda: {}
        fmp._get.side_effect = [
            [{"symbol": f"X{i:04d}"} for i in range(503)],
            [{"symbol": su.R1000_ETF, "asset": f"X{i:04d}"} for i in range(1021)],
        ]
        su.fetch_from_fmp_fallback(fmp)
        paths = [c.args[0] if c.args else c.kwargs.get("path") for c in fmp._get.call_args_list]
        assert "/stable/russell1000-constituent" not in paths
        assert "/stable/etf/holdings" in paths
        holdings_call = fmp._get.call_args_list[1]
        assert holdings_call.kwargs["params"]["symbol"] == su.R1000_ETF

    def test_wikipedia_fail_no_fmp_raises(self, tmp_path):
        source = SwingUniverseSource(cache_dir=tmp_path)
        with patch(
            "ifds.data.swing_universe.fetch_sp500_from_wikipedia",
            side_effect=RuntimeError("wiki down"),
        ):
            with pytest.raises(RuntimeError, match="Wikipedia parse failed"):
                source.get_universe(fmp_client=None)

    def test_fmp_fallback_out_of_window_returns_none(self):
        fmp = MagicMock()
        fmp._api_key = "k"
        fmp._auth_headers = lambda: {}
        fmp._get.return_value = [{"symbol": "ONLY"}]  # 1 ticker → out of window
        result = fetch_from_fmp_fallback(fmp)
        assert result is None


# ---------------------------------------------------------------------------
# Phase 2 integration
# ---------------------------------------------------------------------------


class TestPhase2SwingIntegration:
    def _make_fmp_dict(self, symbol):
        return {
            "symbol": symbol,
            "companyName": f"{symbol} Inc",
            "sector": "Technology",
            "marketCap": 5_000_000_000,
            "price": 100.0,
            "volume": 1_000_000,
            "isActivelyTrading": True,
        }

    def test_swing_filter_intersects_screener_result(self, config, logger, tmp_path):
        # Default `universe_source = "swing_sp500_r1000"` from defaults.py
        # Pre-warm a cache so the test does not hit the network.
        (tmp_path / "swing_universe").mkdir()
        (tmp_path / "swing_universe" / "universe.json").write_text(
            json.dumps(
                {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "count": 1000,
                    "symbols": ["AAPL", "MSFT"] + [f"X{i:04d}" for i in range(998)],
                }
            )
        )

        fmp = MagicMock()
        # FMP returns AAPL, MSFT (in universe) + NOTINIDX (not in universe)
        fmp.screener.return_value = [
            self._make_fmp_dict("AAPL"),
            self._make_fmp_dict("MSFT"),
            self._make_fmp_dict("NOTINIDX"),
        ]
        result = _screen_long_universe(fmp, config, logger)
        symbols = {t.symbol for t in result}
        assert symbols == {"AAPL", "MSFT"}

    def test_swing_failure_REFUSES_the_raw_screener(self, config, logger, tmp_path):
        """INVERTED 2026-10-20 (D-U1/F-1d, approved).

        This test used to assert the opposite: that a membership failure falls back
        to the raw screener. That fallback is what hid nine consecutive weekly runs
        of degradation (2026-08-16 .. 10-19). The screener is not a staler membership
        list, it is a DIFFERENT population — measured, it swapped 377 of 730 names
        (52%) for non-members, and the resulting mixture inflated sigma_cs enough to
        understate the project's central number by ~4%.

        Since the staleness ladder now serves an EXPIRED cache rather than giving up,
        reaching this path means there is no usable membership at all, which must stop
        the phase so no context is written.
        """
        fmp = MagicMock()
        fmp.screener.return_value = [
            self._make_fmp_dict("AAPL"),
            self._make_fmp_dict("NOTINIDX"),
        ]
        with (
            patch(
                "ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                side_effect=RuntimeError("wiki down"),
            ),
            patch("ifds.data.swing_universe.fetch_from_fmp_fallback", return_value=None),
            pytest.raises(RuntimeError, match="REFUSING|Substituting|unavailable"),
        ):
            _screen_long_universe(fmp, config, logger)

    def test_an_expired_cache_still_yields_a_universe(self, config, logger, tmp_path):
        """The ladder's point: stale membership keeps the pipeline running (F-1a)."""
        import json
        from datetime import datetime, timedelta, timezone

        cache_dir = tmp_path / "swing_universe"
        cache_dir.mkdir()
        stale = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        (cache_dir / "universe.json").write_text(
            json.dumps(
                {
                    "fetched_at": stale,
                    "count": 1000,
                    "symbols": ["AAPL"] + [f"OLD{i:03d}" for i in range(999)],
                }
            )
        )
        config.tuning["swing_universe_cache_dir"] = str(cache_dir)
        fmp = MagicMock()
        fmp.screener.return_value = [
            self._make_fmp_dict("AAPL"),
            self._make_fmp_dict("NOTINIDX"),
        ]
        with (
            patch(
                "ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                side_effect=RuntimeError("wiki down"),
            ),
            patch("ifds.data.swing_universe.fetch_from_fmp_fallback", return_value=None),
        ):
            result = _screen_long_universe(fmp, config, logger)
        # The stale membership is honoured: AAPL is in it, NOTINIDX is not.
        assert {t.symbol for t in result} == {"AAPL"}

    def test_legacy_fmp_source_skips_swing_filter(self, config, logger):
        config.tuning["universe_source"] = "fmp_screener"
        fmp = MagicMock()
        fmp.screener.return_value = [
            self._make_fmp_dict("WHATEVER"),
            self._make_fmp_dict("ANYTHING"),
        ]
        result = _screen_long_universe(fmp, config, logger)
        # Both pass — no swing membership filter applied
        assert {t.symbol for t in result} == {"WHATEVER", "ANYTHING"}
