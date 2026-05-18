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
            '<tr><th>Symbol</th></tr>'
            '<tr><td>BRK.B</td></tr>'
            '<tr><td>BF-A</td></tr>'
            '</table>'
        )
        assert _parse_symbols(html) == ["BRK-B", "BF-A"]

    def test_filters_non_ticker_tokens(self):
        html = (
            '<table class="wikitable" id="constituents">'
            '<tr><th>Symbol</th></tr>'
            '<tr><td>AAPL</td></tr>'
            '<tr><td>Not-A-Ticker-1234</td></tr>'
            '<tr><td></td></tr>'
            '<tr><td>MSFT</td></tr>'
            '</table>'
        )
        assert _parse_symbols(html) == ["AAPL", "MSFT"]


# ---------------------------------------------------------------------------
# Cache lifecycle
# ---------------------------------------------------------------------------


class TestCacheLifecycle:
    def test_get_universe_writes_cache_on_first_call(self, tmp_path):
        source = SwingUniverseSource(cache_dir=tmp_path)
        with patch("ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                   return_value=[f"X{i:04d}" for i in range(500)]), \
             patch("ifds.data.swing_universe.fetch_russell1000_from_wikipedia",
                   return_value=[f"X{i:04d}" for i in range(1000)]):
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
        (tmp_path / "universe.json").write_text(json.dumps({
            "fetched_at": old_ts,
            "count": 1000,
            "symbols": [f"OLD{i:03d}" for i in range(1000)],
        }))
        source = SwingUniverseSource(cache_dir=tmp_path, cache_ttl_days=7)
        with patch("ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                   return_value=[f"NEW{i:04d}" for i in range(500)]), \
             patch("ifds.data.swing_universe.fetch_russell1000_from_wikipedia",
                   return_value=[f"NEW{i:04d}" for i in range(1000)]):
            symbols = source.get_universe()
        assert symbols[0].startswith("NEW")  # not OLD

    def test_corrupt_cache_falls_through_to_fetch(self, tmp_path):
        (tmp_path / "universe.json").write_text("{ not valid json")
        source = SwingUniverseSource(cache_dir=tmp_path)
        with patch("ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                   return_value=[f"X{i:04d}" for i in range(500)]), \
             patch("ifds.data.swing_universe.fetch_russell1000_from_wikipedia",
                   return_value=[f"X{i:04d}" for i in range(1000)]):
            symbols = source.get_universe()
        assert len(symbols) >= 950


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


class TestFailureModes:
    def test_wikipedia_fail_fmp_succeeds(self, tmp_path):
        source = SwingUniverseSource(cache_dir=tmp_path)
        fmp = MagicMock()
        fmp._api_key = "k"
        fmp._auth_headers = lambda: {}
        # Two endpoint calls — SP then R1000 (overlapping namespace like the
        # real indexes: S&P 500 is ~95% subset of Russell 1000)
        fmp._get.side_effect = [
            [{"symbol": f"X{i:04d}"} for i in range(500)],
            [{"symbol": f"X{i:04d}"} for i in range(1000)],
        ]
        with patch("ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                   side_effect=RuntimeError("wiki down")):
            symbols = source.get_universe(fmp_client=fmp)
        assert 950 <= len(symbols) <= 1100

    def test_wikipedia_fail_no_fmp_raises(self, tmp_path):
        source = SwingUniverseSource(cache_dir=tmp_path)
        with patch("ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                   side_effect=RuntimeError("wiki down")):
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
        (tmp_path / "swing_universe" / "universe.json").write_text(json.dumps({
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "count": 1000,
            "symbols": ["AAPL", "MSFT"] + [f"X{i:04d}" for i in range(998)],
        }))

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

    def test_swing_failure_falls_back_to_raw_screener(self, config, logger, tmp_path):
        # No cache → SwingUniverseSource fetches → patched Wikipedia raises →
        # patched FMP fallback returns None → _load_swing_membership returns
        # None → Phase 2 logs WARNING + uses raw screener.
        fmp = MagicMock()
        fmp.screener.return_value = [
            self._make_fmp_dict("AAPL"),
            self._make_fmp_dict("NOTINIDX"),
        ]
        with patch("ifds.data.swing_universe.fetch_sp500_from_wikipedia",
                   side_effect=RuntimeError("wiki down")), \
             patch("ifds.data.swing_universe.fetch_from_fmp_fallback",
                   return_value=None):
            result = _screen_long_universe(fmp, config, logger)
        # Fallback to raw screener — both tickers pass
        assert {t.symbol for t in result} == {"AAPL", "NOTINIDX"}

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
