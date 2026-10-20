"""The deterministic liquidity floor (D-U2 = (C), approved 2026-10-20).

Hermetic: every case builds its own bar sessions. No network, no production state, no
clock dependence — the floor is a pure function and these tests treat it as one.

Validated against real data on 2026-10-20 before these tests were written: membership
1018, 25 cached sessions, 20-session lookback -> 913 pass, 105 excluded
(below_volume 90, below_price 8, no_bars 7). The seven no_bars names are genuinely
absent from the Polygon grouped file (AVB, EA, EQR, LBRDA, LBRDK, MASI, WBS); the six
share-class names that USED to land there resolve once both spellings are tried.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ifds.data.liquidity_floor import (  # noqa: E402
    REASON_BELOW_PRICE,
    REASON_BELOW_VOLUME,
    REASON_NO_BARS,
    compute_floor,
    ticker_variants,
)


def _session(day: str, rows: dict[str, tuple[float, float]]) -> dict:
    """One session: {ticker: (close, volume)}."""
    return {
        "date": day,
        "bars": [{"T": t, "c": close, "v": volume} for t, (close, volume) in rows.items()],
    }


def _sessions(n: int, rows: dict[str, tuple[float, float]]) -> list[dict]:
    return [_session(f"2026-09-{i + 1:02d}", rows) for i in range(n)]


class TestTickerVariants:
    def test_a_hyphen_class_share_also_tries_the_dot_form(self):
        """Polygon writes BRK.B; this repo normalises to BRK-B. Measured: six
        membership names were invisible under one spelling only."""
        assert ticker_variants("BRK-B") == ("BRK-B", "BRK.B")

    def test_a_dot_class_share_also_tries_the_hyphen_form(self):
        assert ticker_variants("BRK.B") == ("BRK.B", "BRK-B")

    def test_a_plain_ticker_yields_itself_once(self):
        assert ticker_variants("AAPL") == ("AAPL",)

    def test_whitespace_and_case_are_normalised(self):
        assert ticker_variants("  aapl ") == ("AAPL",)


class TestTheFloor:
    def test_a_liquid_member_passes(self):
        bars = _sessions(20, {"AAPL": (200.0, 50_000_000)})
        result = compute_floor(["AAPL"], bars, min_price=5.0, min_avg_volume=500_000)
        assert result.passed == frozenset({"AAPL"})
        assert result.excluded == ()

    def test_a_cheap_member_is_excluded_on_price(self):
        bars = _sessions(20, {"PENNY": (2.5, 50_000_000)})
        result = compute_floor(["PENNY"], bars, min_price=5.0, min_avg_volume=500_000)
        assert result.passed == frozenset()
        assert result.excluded == (("PENNY", REASON_BELOW_PRICE),)

    def test_a_thin_member_is_excluded_on_volume(self):
        bars = _sessions(20, {"THIN": (50.0, 1_000)})
        result = compute_floor(["THIN"], bars, min_price=5.0, min_avg_volume=500_000)
        assert result.excluded == (("THIN", REASON_BELOW_VOLUME),)

    def test_one_event_day_cannot_carry_an_illiquid_name(self):
        """Why the statistic is the MEDIAN and not the mean.

        19 sessions at 1k shares plus one at 100M has a MEAN of 5.0M — above a
        500k floor — while its median is 1k. A liquidity floor must describe
        typical tradability, not an episode. Measured cost of choosing the median
        on real data (2026-10-20, 1011 members with bars): 913 pass on the mean,
        900 on the median, and all 13 of the difference are marginal names with
        medians of 444k-483k against the 500k threshold.
        """
        quiet = _sessions(19, {"SPIKE": (50.0, 1_000)})
        busy = [_session("2026-09-20", {"SPIKE": (50.0, 100_000_000)})]
        result = compute_floor(["SPIKE"], quiet + busy, min_price=5.0, min_avg_volume=500_000)
        assert result.excluded == (("SPIKE", REASON_BELOW_VOLUME),), "median, not mean"
        assert result.passed == frozenset()

    def test_a_steadily_liquid_name_passes_on_the_median(self):
        bars = _sessions(20, {"STEADY": (50.0, 600_000)})
        result = compute_floor(["STEADY"], bars, min_price=5.0, min_avg_volume=500_000)
        assert result.passed == frozenset({"STEADY"})

    def test_price_is_the_LATEST_close(self):
        """A name that fell below the floor must not be rescued by its history."""
        early = _sessions(19, {"FALLEN": (50.0, 50_000_000)})
        last = [_session("2026-09-20", {"FALLEN": (2.0, 50_000_000)})]
        result = compute_floor(["FALLEN"], early + last, min_price=5.0, min_avg_volume=500_000)
        assert result.excluded == (("FALLEN", REASON_BELOW_PRICE),)

    def test_a_member_absent_from_every_session_is_reported_not_silently_dropped(self):
        bars = _sessions(20, {"AAPL": (200.0, 50_000_000)})
        result = compute_floor(["AAPL", "GONE"], bars, min_price=5.0, min_avg_volume=500_000)
        assert result.passed == frozenset({"AAPL"})
        assert result.excluded == (("GONE", REASON_NO_BARS),)
        assert result.counts_by_reason() == {REASON_NO_BARS: 1}

    def test_a_class_share_is_found_under_the_providers_dot_spelling(self):
        """The measured trap: membership says BRK-B, Polygon says BRK.B."""
        bars = _sessions(20, {"BRK.B": (400.0, 5_000_000)})
        result = compute_floor(["BRK-B"], bars, min_price=5.0, min_avg_volume=500_000)
        assert result.passed == frozenset({"BRK-B"}), "the canonical spelling is kept"
        assert result.excluded == ()

    def test_only_the_newest_sessions_inside_the_lookback_count(self):
        old = [_session(f"2026-08-{i + 1:02d}", {"X": (50.0, 1_000)}) for i in range(10)]
        new = [_session(f"2026-09-{i + 1:02d}", {"X": (50.0, 50_000_000)}) for i in range(5)]
        result = compute_floor(["X"], old + new, min_price=5.0, min_avg_volume=500_000, lookback=5)
        assert result.passed == frozenset({"X"})
        assert result.sessions_used == 5
        assert result.lookback_requested == 5


class TestItFailsLoudly:
    def test_no_bars_at_all_RAISES_rather_than_emptying_or_skipping(self):
        """`breadth_enabled: False` is a real config path, not a theoretical one.

        Skipping the floor would WIDEN the universe — the failure mode that hid nine
        weeks of silent degradation (2026-08-16 .. 10-19).
        """
        for empty in ([], None):
            with pytest.raises(ValueError, match="breadth_enabled"):
                compute_floor(["AAPL"], empty, min_price=5.0, min_avg_volume=500_000)

    def test_sessions_without_bars_do_not_count_as_history(self):
        bars = _sessions(20, {"AAPL": (200.0, 50_000_000)}) + [{"date": "2026-09-21", "bars": []}]
        result = compute_floor(["AAPL"], bars, min_price=5.0, min_avg_volume=500_000)
        assert result.sessions_used == 20


class TestItIsDeterministicAndPure:
    def test_the_same_inputs_give_the_same_universe(self):
        """The whole reason for (C): the screener's raw result swung -25% week on
        week on identical parameters. A pure function cannot do that."""
        bars = _sessions(20, {"A": (50.0, 1_000_000), "B": (1.0, 1_000_000)})
        first = compute_floor(["A", "B"], bars, min_price=5.0, min_avg_volume=500_000)
        second = compute_floor(["B", "A"], bars, min_price=5.0, min_avg_volume=500_000)
        assert first.passed == second.passed
        assert first.excluded == second.excluded

    def test_the_inputs_are_not_mutated(self):
        bars = _sessions(3, {"A": (50.0, 1_000_000)})
        membership = ["A", "B"]
        snapshot = [dict(s, bars=[dict(r) for r in s["bars"]]) for s in bars]
        compute_floor(membership, bars, min_price=5.0, min_avg_volume=500_000)
        assert membership == ["A", "B"]
        assert bars == snapshot

    def test_provenance_names_the_definition_and_the_causes(self):
        bars = _sessions(20, {"A": (50.0, 1_000_000), "B": (1.0, 1_000_000)})
        prov = compute_floor(["A", "B", "C"], bars, min_price=5.0, min_avg_volume=500_000).provenance()
        assert prov["definition"] == "index_union_plus_liquidity_floor"
        assert prov["volume_statistic"] == "median", "the statistic must not be assumed"
        assert prov["passed"] == 1
        assert prov["excluded_by_reason"] == {REASON_BELOW_PRICE: 1, REASON_NO_BARS: 1}
