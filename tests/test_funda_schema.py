"""The two FMP schema defects that made the fundamental block score on 2 of 6 inputs.

Both were silent for the life of the swing era, and both are the same shape: the code
asked a real endpoint for fields that endpoint has never carried, got HTTP 200, and read
``None``. Nothing failed. Measured over 149 production snapshots / 16,425 ticker-days:
``roe``, ``debt_equity`` and ``net_margin`` non-null in 0, ``interest_coverage`` absent
from the schema entirely, ``inst_ownership_score`` == 0 in all 16,425.

1. KEY METRICS. ``/stable/key-metrics`` carries ``returnOnEquity``; the scorer read
   ``roeTTM``/``debtToEquityTTM``/``interestCoverageTTM``/``netIncomePerShareTTM`` — the
   legacy v3 ``key-metrics-ttm`` schema. Live probe 2026-10-23: the four the scorer needs
   live on ``/stable/ratios-ttm`` (``netProfitMarginTTM``, ``debtToEquityRatioTTM``,
   ``interestCoverageRatioTTM``, and ``netIncomePerShareTTM`` ÷
   ``shareholdersEquityPerShareTTM`` for ROE). One call replaces one call, so the Phase 4
   request rate is unchanged — which matters, because production already draws 276 HTTP
   429s a day at ~2,600 calls/min.

2. INSTITUTIONAL OWNERSHIP. ``/stable/institutional-ownership/latest?symbol=AAPL``
   silently IGNORES ``symbol`` and returns the market-wide filing feed. Live probe
   2026-10-23 for AAPL returned "RUBICON ADVISORS, GP" and "AMANAH HOLDINGS TRUST", with
   no ``totalInvested`` field at all. The per-symbol route is
   ``symbol-positions-summary``, and it carries current AND previous quarter in ONE row.

The live probe also found a trap that is NOT in either bug report, and the thresholds
below encode it: see TestTheQuarterMustBeComplete and TestAStructuralZeroIsNotBadNews.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ifds.config.loader import Config  # noqa: E402
from ifds.data import fmp as fmp_mod  # noqa: E402
from ifds.phases.phase4_stocks import _analyze_fundamental_from_data  # noqa: E402

# Verbatim from /stable/ratios-ttm?symbol=MSFT, probed 2026-10-23.
MSFT_RATIOS = {
    "netProfitMarginTTM": 0.4031,
    "netIncomePerShareTTM": 13.64,
    "shareholdersEquityPerShareTTM": 45.12,
    "debtToEquityRatioTTM": 0.2912,
    "interestCoverageRatioTTM": 50.8807,
    "revenuePerShareTTM": 33.84,
}
# Verbatim from /stable/ratios-ttm?symbol=AAPL. interestCoverageRatioTTM is 0.0 because
# Apple's interest expense is ~0 — that is the BEST possible coverage, not the worst.
AAPL_RATIOS = {
    "netProfitMarginTTM": 0.2762,
    "netIncomePerShareTTM": 7.52,
    "shareholdersEquityPerShareTTM": 6.27,
    "debtToEquityRatioTTM": 0.7841,
    "interestCoverageRatioTTM": 0.0,
}
GROWTH = {"revenueGrowth": 0.05, "epsgrowth": 0.05}  # neutral: isolates the metrics block


@pytest.fixture(autouse=True)
def _fake_keys(monkeypatch):
    """Config validates credentials at construction; the scorer makes no calls.

    Hermetic per .claude/rules/ifds-rules.md — injected, never read from the real .env,
    so the suite is green on a fresh clone and on the Mini alike.
    """
    for var in ("IFDS_POLYGON_API_KEY", "IFDS_FMP_API_KEY", "IFDS_FRED_API_KEY"):
        monkeypatch.setenv(var, "test-key-not-real")
    monkeypatch.delenv("IFDS_UW_API_KEY", raising=False)
    monkeypatch.delenv("IFDS_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("IFDS_TELEGRAM_CHAT_ID", raising=False)


def _score(metrics, growth=GROWTH, inst=None):
    return _analyze_fundamental_from_data(
        "TEST", growth, metrics, [], Config(), inst_data=inst
    )


class TestTheScorerReadsFieldsThatExist:
    def test_all_four_metrics_are_populated_from_a_real_payload(self) -> None:
        """The headline regression: 0 of 4 non-null across 16,425 rows, before this."""
        s = _score(MSFT_RATIOS)
        assert s.net_margin == pytest.approx(0.4031)
        assert s.debt_equity == pytest.approx(0.2912)
        assert s.interest_coverage == pytest.approx(50.8807)
        assert s.roe is not None and s.roe == pytest.approx(13.64 / 45.12, rel=1e-6)

    def test_roe_matches_the_vendor_s_own_figure_closely(self) -> None:
        """ROE is derived, so it must be checked against the vendor's direct number.

        Live cross-check 2026-10-23 (ratios-ttm derivation vs key-metrics-ttm
        returnOnEquityTTM): MSFT .3023/.3322, JPM .1772/.1791, XOM .1263/.1268,
        TSLA .0362/.0378. The spread is an averaging convention (period-end vs average
        equity) and never crosses a scoring threshold in the sample.
        """
        s = _score({"netIncomePerShareTTM": 13.64, "shareholdersEquityPerShareTTM": 45.12})
        assert s.roe == pytest.approx(0.3023, abs=0.02)

    def test_the_old_legacy_field_names_no_longer_decide_anything(self) -> None:
        """A v3-shaped payload must score as ABSENT data, not silently as zero."""
        legacy = {"roeTTM": 0.30, "debtToEquityTTM": 0.29, "interestCoverageTTM": 50.0}
        s = _score(legacy)
        assert s.roe is None and s.debt_equity is None and s.interest_coverage is None

    def test_six_branches_can_fire_not_two(self) -> None:
        """Before the fix funda_score could only ever be in {-10,-5,0,5,10}."""
        strong = dict(MSFT_RATIOS)
        rich = _score(strong, growth={"revenueGrowth": 0.5, "epsgrowth": 0.5})
        assert rich.funda_score > 10, (
            "revenue + EPS alone cap at 10; a score above it proves the metric branches "
            f"are live (got {rich.funda_score})"
        )


class TestAStructuralZeroIsNotBadNews:
    """interestCoverageRatioTTM == 0 means "no interest expense", i.e. excellent.

    Reading it as "below funda_interest_coverage_bad" would hand a -10 debt penalty to
    exactly the debt-free companies. Same error class as the dp_pct structural zero
    (.claude/rules/ifds-rules.md, 2026-05-10), and the house rule says the guard must be
    tolerance-based, never `== 0`.
    """

    def test_apple_s_zero_coverage_is_treated_as_missing(self) -> None:
        s = _score(AAPL_RATIOS)
        assert s.interest_coverage is None, "0.0 coverage must not read as catastrophic"

    def test_and_it_costs_no_penalty(self) -> None:
        with_zero = _score(AAPL_RATIOS).funda_score
        without = _score({k: v for k, v in AAPL_RATIOS.items() if k != "interestCoverageRatioTTM"})
        assert with_zero == without.funda_score

    @pytest.mark.parametrize("value", [0.0, -0.0, 1e-15, -1e-13])
    def test_the_guard_is_tolerance_based(self, value: float) -> None:
        s = _score({**MSFT_RATIOS, "interestCoverageRatioTTM": value})
        assert s.interest_coverage is None

    def test_a_genuinely_thin_coverage_still_penalises(self) -> None:
        """The guard must not swallow the real signal it sits next to."""
        thin = _score({**MSFT_RATIOS, "interestCoverageRatioTTM": 0.9})
        healthy = _score(MSFT_RATIOS)
        assert thin.interest_coverage == pytest.approx(0.9)
        assert thin.funda_score < healthy.funda_score


class TestTheQuarterMustBeComplete:
    """The trap the live probe found, which neither bug report predicted.

    13F filings are due 45 days after quarter end, so the newest quarter is a PARTIAL
    tally for weeks. Probed 2026-10-23 on the 2026-Q3 (Sep-30) summary: AAPL -96.78%,
    MSFT -96.06%, NVDA -97.20% QoQ. Taking "the latest quarter" would have stamped
    `decreasing` on essentially the whole universe — a far worse failure than the measured
    zero it replaces. 2026-Q2 on the same day: AAPL +18.85%, MSFT +4.69%, NVDA +20.10%.
    """

    @pytest.mark.parametrize(
        "today,expected",
        [
            (date(2026, 10, 23), (2026, 2)),  # Q3 ended 23 days ago — far too new
            (date(2026, 11, 13), (2026, 2)),  # the day before the Q3 deadline
            (date(2026, 12, 20), (2026, 3)),  # deadline + settling margin passed
            (date(2027, 1, 5), (2026, 3)),    # Q4 ended 5 days ago
            (date(2026, 5, 1), (2025, 4)),
        ],
    )
    def test_it_picks_the_latest_quarter_whose_filings_are_in(self, today, expected) -> None:
        assert fmp_mod.latest_complete_13f_quarter(today) == expected

    def test_the_lag_exceeds_the_statutory_deadline(self) -> None:
        """45 days is when filings START being complete, not when they are."""
        assert fmp_mod.FILING_LAG_DAYS >= 45 + 21

    def test_a_partial_quarter_is_rejected_even_if_the_date_rule_let_it_through(self) -> None:
        """Belt and braces: the filer count itself betrays an incomplete tally."""
        partial = {
            "totalInvested": 90_946_419_196,
            "lastTotalInvested": 2_825_792_540_134,
            "investorsHolding": 210,
            "lastInvestorsHolding": 6_423,
        }
        assert fmp_mod.is_complete_13f_row(partial) is False

    def test_a_complete_quarter_passes(self) -> None:
        complete = {
            "totalInvested": 2_825_792_540_134,
            "lastTotalInvested": 2_377_611_298_039,
            "investorsHolding": 6_481,
            "lastInvestorsHolding": 6_423,
        }
        assert fmp_mod.is_complete_13f_row(complete) is True


class TestTheOwnershipTrendIsComputedFromOneRow:
    """symbol-positions-summary carries this quarter AND last quarter in the same row."""

    ROW = {
        "totalInvested": 2_825_792_540_134,
        "lastTotalInvested": 2_377_611_298_039,
        "investorsHolding": 6_481,
        "lastInvestorsHolding": 6_423,
    }

    def test_increasing(self) -> None:
        s = _score(MSFT_RATIOS, inst=[self.ROW])
        assert s.inst_ownership_trend == "increasing"
        assert s.inst_ownership_score == 10

    def test_decreasing(self) -> None:
        row = {**self.ROW, "totalInvested": 2_000_000_000_000}
        s = _score(MSFT_RATIOS, inst=[row])
        assert s.inst_ownership_trend == "decreasing"

    def test_flat_is_stable_and_scores_nothing(self) -> None:
        row = {**self.ROW, "totalInvested": int(self.ROW["lastTotalInvested"] * 1.005)}
        s = _score(MSFT_RATIOS, inst=[row])
        assert s.inst_ownership_trend == "stable"
        assert s.inst_ownership_score == 0

    def test_the_old_two_row_feed_shape_yields_unknown_not_a_false_trend(self) -> None:
        """What production actually received for 16,425 ticker-days."""
        feed = [
            {"cik": "0002114679", "name": "RUBICON ADVISORS, GP", "formType": "13F-HR"},
            {"cik": "0002076121", "name": "AMANAH HOLDINGS TRUST", "formType": "13F-HR"},
        ]
        s = _score(MSFT_RATIOS, inst=feed)
        assert s.inst_ownership_trend == "unknown"
        assert s.inst_ownership_score == 0


class TestTheClientAsksTheRightEndpoints:
    def test_key_metrics_targets_the_ttm_ratios_route(self) -> None:
        source = Path(fmp_mod.__file__).read_text()
        assert "/stable/ratios-ttm" in source
        assert '"/stable/key-metrics"' not in source, (
            "that route carries returnOnEquity, not the TTM names the scorer reads"
        )

    def test_institutional_ownership_targets_the_per_symbol_route(self) -> None:
        source = Path(fmp_mod.__file__).read_text()
        assert "symbol-positions-summary" in source
        assert '"/stable/institutional-ownership/latest"' not in source, (
            "that route ignores ?symbol= and returns the market-wide filing feed"
        )

    def test_the_async_client_asks_for_exactly_the_same_routes(self) -> None:
        """The production path is async (IFDS_ASYNC_ENABLED=true); a one-sided fix is no fix."""
        sync = Path(fmp_mod.__file__).read_text()
        from ifds.data import async_clients

        asyn = Path(async_clients.__file__).read_text()
        for route in ("/stable/ratios-ttm", "symbol-positions-summary"):
            assert route in sync and route in asyn, f"{route} missing from one of the clients"
        assert '"/stable/institutional-ownership/latest"' not in asyn
        assert '"/stable/key-metrics"' not in asyn
