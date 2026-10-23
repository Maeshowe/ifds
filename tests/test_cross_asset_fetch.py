"""Cross-Asset Regime: the fetch that threw on every run for 6.5 months.

What happened. ``_fetch_cross_asset_ratios`` called ``polygon.get_daily_bars(etf, n)`` —
a method PolygonClient has never defined. The surrounding ``except Exception`` caught the
AttributeError, logged a WARNING and set that ETF's bars to ``[]``, so all three ratios
came back empty and the regime stayed NORMAL forever. 196 of 286 production run logs
carry the line, the first on 2026-04-06. CLAUDE.md advertises the layer as live.

Two defects, two guards:

1. The call itself. PolygonClient returns RAW Polygon aggregate rows — ``{"t": epoch_ms,
   "c": close, ...}`` — while ``_ratio`` indexes ``b["date"]``. Fixing the method name
   alone would have produced a second silent empty: KeyError inside the same bare except.
   So the shape conversion is part of the fix and is asserted here.

2. The gap. A bare ``except Exception`` around a client call turns a typo into six months
   of silence. ``TestTheClientContractHolds`` asserts every PolygonClient attribute the
   module reaches for actually exists, so the next rename fails in CI instead of in prod.

Hermetic: a fake client, no network, no production state.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ifds.phases import phase0_diagnostics as diag  # noqa: E402


def _epoch_ms(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1000)


class _FakePolygon:
    """Returns raw Polygon-shaped aggregate rows, exactly as the real client does."""

    def __init__(self, closes_by_etf: dict[str, list[float]], start: date) -> None:
        self._closes = closes_by_etf
        self._start = start
        self.calls: list[tuple] = []

    def get_aggregates(self, ticker, from_date, to_date, timespan="day", multiplier=1):
        self.calls.append((ticker, from_date, to_date, timespan, multiplier))
        closes = self._closes.get(ticker)
        if closes is None:
            return None
        return [
            {"t": _epoch_ms(self._start + timedelta(days=i)), "c": c, "o": c, "h": c, "l": c, "v": 1}
            for i, c in enumerate(closes)
        ]


class _SilentLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def log(self, *_args, **kwargs) -> None:
        self.messages.append(str(kwargs.get("message", "")))


START = date(2026, 10, 1)
CLOSES = {
    "HYG": [80.0, 81.0, 82.0],
    "IEF": [100.0, 100.0, 100.0],
    "RSP": [150.0, 153.0, 156.0],
    "SPY": [600.0, 600.0, 600.0],
    "IWM": [240.0, 240.0, 246.0],
}
ETFS = ["HYG", "IEF", "RSP", "SPY", "IWM"]


class TestTheRatiosAreActuallyComputed:
    def test_all_three_ratios_come_back_non_empty(self) -> None:
        logger = _SilentLogger()
        ratios = diag._fetch_cross_asset_ratios(_FakePolygon(CLOSES, START), ETFS, 30, logger)

        assert ratios["hyg_ief"] == [0.80, 0.81, 0.82]
        assert ratios["rsp_spy"] == [0.25, 0.255, 0.26]
        assert ratios["iwm_spy"] == [0.40, 0.40, 0.41]
        assert not any("failed to fetch" in m for m in logger.messages), (
            "the fetch logged a failure — this is the 6.5-month-old regression"
        )

    def test_it_asks_for_a_date_range_covering_the_lookback(self) -> None:
        """lookback_days is a window, and get_aggregates takes two dates, not a count."""
        client = _FakePolygon(CLOSES, START)
        diag._fetch_cross_asset_ratios(client, ETFS, 30, _SilentLogger())

        assert len(client.calls) == len(ETFS)
        for ticker, from_date, to_date, timespan, multiplier in client.calls:
            assert ticker in ETFS
            assert timespan == "day" and multiplier == 1
            span = (date.fromisoformat(to_date) - date.fromisoformat(from_date)).days
            assert span >= 30, f"asked for {span} days, lookback was 30"

    def test_a_missing_etf_degrades_to_an_empty_ratio_not_a_crash(self) -> None:
        partial = {k: v for k, v in CLOSES.items() if k != "IEF"}
        ratios = diag._fetch_cross_asset_ratios(
            _FakePolygon(partial, START), ETFS, 30, _SilentLogger()
        )
        assert ratios["hyg_ief"] == []
        assert ratios["rsp_spy"], "an unrelated ratio must still compute"

    def test_bars_are_aligned_by_date_not_by_position(self) -> None:
        """Different histories per ETF is the normal case, not the exception."""
        shifted = {
            "HYG": [80.0, 81.0, 82.0],
            "IEF": [100.0, 100.0],  # one session short — starts on the SAME day
            "RSP": [150.0],
            "SPY": [600.0],
            "IWM": [240.0],
        }
        ratios = diag._fetch_cross_asset_ratios(
            _FakePolygon(shifted, START), ETFS, 30, _SilentLogger()
        )
        assert ratios["hyg_ief"] == [0.80, 0.81], "the unmatched third HYG bar must be dropped"


class TestTheClientContractHolds:
    """Close the gap: a bare `except Exception` must not hide a renamed method again."""

    def test_every_polygon_method_the_module_calls_exists(self) -> None:
        import ast

        from ifds.data.polygon import PolygonClient

        source = Path(diag.__file__).read_text()
        called: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "polygon"
            ):
                called.add(node.func.attr)

        assert called, "the AST scan found no polygon.* calls — the guard would guard nothing"
        missing = sorted(m for m in called if not hasattr(PolygonClient, m))
        assert not missing, (
            f"phase0_diagnostics calls PolygonClient.{missing} which does not exist. "
            "A bare `except Exception` turns this into a silent empty result — that is "
            "how get_daily_bars went unnoticed from 2026-04-06 to 2026-10-23."
        )
