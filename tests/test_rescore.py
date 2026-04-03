"""Tests for SIM-L2 Mode 2 Re-Score Engine.

Covers:
- snapshot_to_stock_analysis round-trip
- Combined score re-calculation with weight overrides
- EWMA score smoothing
- Sizing multipliers (M_target, M_flow, M_funda, M_gex, M_vix)
- rescore_snapshot end-to-end
- Edge cases (None fields, empty snapshots)
"""

import math

import pytest

from ifds.data.phase4_snapshot import (
    _stock_to_dict,
    snapshot_to_stock_analysis,
)
from ifds.models.market import (
    FlowAnalysis,
    FundamentalScoring,
    StockAnalysis,
    TechnicalAnalysis,
)
from ifds.sim.rescore import (
    RescoredPosition,
    _build_config,
    _calculate_m_target,
    _calculate_m_vix,
    _calculate_sizing,
    _ewma_score,
    _rescore_combined_score,
    rescore_snapshot,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_stock(
    ticker: str = "AAPL",
    price: float = 150.0,
    atr: float = 3.0,
    combined_score: float = 80.0,
    sector_adjustment: int = 0,
    rvol_score: int = 10,
    funda_score: int = 15,
    rsi_score: int = 30,
    sma50_bonus: int = 30,
    rs_spy_score: int = 40,
    insider_multiplier: float = 1.0,
    insider_score: int = 0,
    analyst_target: float | None = None,
) -> StockAnalysis:
    return StockAnalysis(
        ticker=ticker,
        sector="Technology",
        technical=TechnicalAnalysis(
            price=price,
            sma_200=140.0,
            sma_20=148.0,
            rsi_14=55.0,
            atr_14=atr,
            trend_pass=True,
            rsi_score=rsi_score,
            sma_50=145.0,
            sma50_bonus=sma50_bonus,
            rs_vs_spy=0.05,
            rs_spy_score=rs_spy_score,
        ),
        flow=FlowAnalysis(
            rvol=1.5,
            rvol_score=rvol_score,
        ),
        fundamental=FundamentalScoring(
            funda_score=funda_score,
            insider_score=insider_score,
            insider_multiplier=insider_multiplier,
        ),
        combined_score=combined_score,
        sector_adjustment=sector_adjustment,
        analyst_target=analyst_target,
    )


def _make_snapshot_record(**overrides) -> dict:
    """Create a minimal snapshot dict."""
    base = {
        "ticker": "AAPL",
        "sector": "Technology",
        "combined_score": 80.0,
        "sector_adjustment": 0,
        "shark_detected": False,
        "price": 150.0,
        "sma_200": 140.0,
        "sma_50": 145.0,
        "sma_20": 148.0,
        "rsi_14": 55.0,
        "atr_14": 3.0,
        "trend_pass": True,
        "rsi_score": 30,
        "sma50_bonus": 30,
        "rs_vs_spy": 0.05,
        "rs_spy_score": 40,
        "rvol": 1.5,
        "rvol_score": 10,
        "dark_pool_pct": 0.0,
        "dp_pct_score": 0,
        "pcr": 0.5,
        "pcr_score": 15,
        "otm_call_ratio": 0.6,
        "otm_score": 10,
        "block_trade_count": 2,
        "block_trade_score": 10,
        "buy_pressure_score": 5,
        "squat_bar": False,
        "revenue_growth_yoy": 0.15,
        "eps_growth_yoy": 0.20,
        "net_margin": 0.25,
        "roe": 0.30,
        "debt_equity": 0.5,
        "insider_score": 0,
        "insider_multiplier": 1.0,
        "funda_score": 15,
        "shark_detected_funda": False,
        "inst_ownership_trend": "stable",
        "inst_ownership_score": 0,
    }
    return {**base, **overrides}


# ============================================================================
# Round-trip: StockAnalysis → dict → StockAnalysis
# ============================================================================

class TestSnapshotRoundTrip:

    def test_round_trip_preserves_fields(self):
        stock = _make_stock()
        d = _stock_to_dict(stock)
        restored = snapshot_to_stock_analysis(d)

        assert restored.ticker == stock.ticker
        assert restored.sector == stock.sector
        assert restored.combined_score == stock.combined_score
        assert restored.sector_adjustment == stock.sector_adjustment
        assert restored.shark_detected == stock.shark_detected

        # Technical
        assert restored.technical.price == stock.technical.price
        assert restored.technical.atr_14 == stock.technical.atr_14
        assert restored.technical.rsi_score == stock.technical.rsi_score
        assert restored.technical.sma50_bonus == stock.technical.sma50_bonus
        assert restored.technical.rs_spy_score == stock.technical.rs_spy_score

        # Flow
        assert restored.flow.rvol_score == stock.flow.rvol_score
        assert restored.flow.squat_bar == stock.flow.squat_bar

        # Fundamental
        assert restored.fundamental.funda_score == stock.fundamental.funda_score
        assert restored.fundamental.insider_multiplier == stock.fundamental.insider_multiplier

    def test_round_trip_shark_detected_rename(self):
        """shark_detected_funda in dict → shark_detected in FundamentalScoring."""
        stock = _make_stock()
        stock.fundamental.shark_detected = True
        d = _stock_to_dict(stock)
        assert "shark_detected_funda" in d
        assert d["shark_detected_funda"] is True

        restored = snapshot_to_stock_analysis(d)
        assert restored.fundamental.shark_detected is True

    def test_round_trip_none_fields(self):
        stock = _make_stock()
        stock.fundamental.net_margin = None
        stock.fundamental.roe = None
        stock.technical.rs_vs_spy = None
        d = _stock_to_dict(stock)
        restored = snapshot_to_stock_analysis(d)

        assert restored.fundamental.net_margin is None
        assert restored.fundamental.roe is None
        assert restored.technical.rs_vs_spy is None


# ============================================================================
# Combined score re-calculation
# ============================================================================

class TestRescoreCombinedScore:

    def test_default_weights(self):
        stock = _make_stock(rvol_score=10, funda_score=15, rsi_score=30,
                            sma50_bonus=30, rs_spy_score=40, sector_adjustment=0)
        cfg = _build_config({})

        score = _rescore_combined_score(stock, cfg)

        # flow = min(100, max(0, 50+10)) = 60
        # funda = 50 + 15 = 65
        # tech = 30 + 30 + 40 = 100
        # combined = (0.4*60 + 0.3*65 + 0.3*100 + 0) * 1.0 = 24 + 19.5 + 30 = 73.5
        assert score == 73.5

    def test_custom_weights(self):
        stock = _make_stock(rvol_score=10, funda_score=15, rsi_score=30,
                            sma50_bonus=30, rs_spy_score=40)
        cfg = _build_config({
            "weight_flow": 0.50,
            "weight_fundamental": 0.25,
            "weight_technical": 0.25,
        })

        score = _rescore_combined_score(stock, cfg)
        # flow=60, funda=65, tech=100
        # 0.5*60 + 0.25*65 + 0.25*100 = 30 + 16.25 + 25 = 71.25
        assert score == 71.25

    def test_sector_adjustment_applied(self):
        stock = _make_stock(sector_adjustment=15)
        cfg = _build_config({})
        score_with = _rescore_combined_score(stock, cfg)

        stock_no_adj = _make_stock(sector_adjustment=0)
        score_without = _rescore_combined_score(stock_no_adj, cfg)

        assert score_with == score_without + 15

    def test_insider_multiplier_applied(self):
        stock = _make_stock(insider_multiplier=1.25)
        cfg = _build_config({})
        score = _rescore_combined_score(stock, cfg)

        stock_neutral = _make_stock(insider_multiplier=1.0)
        score_neutral = _rescore_combined_score(stock_neutral, cfg)

        assert score == round(score_neutral * 1.25, 2)


# ============================================================================
# EWMA
# ============================================================================

class TestEWMA:

    def test_first_day_returns_current(self):
        assert _ewma_score(80.0, None) == 80.0

    def test_smoothing_pulls_toward_current(self):
        prev = 70.0
        current = 80.0
        result = _ewma_score(current, prev, span=10)
        # alpha = 2/11 ≈ 0.1818
        # result = 0.1818 * 80 + 0.8182 * 70 = 14.545 + 57.273 = 71.82
        assert result == 71.82

    def test_span_1_is_identity(self):
        # alpha = 2/2 = 1.0 → result = current
        assert _ewma_score(90.0, 70.0, span=1) == 90.0


# ============================================================================
# Sizing multipliers
# ============================================================================

class TestMTarget:

    def test_no_target_returns_1(self):
        cfg = _build_config({})
        assert _calculate_m_target(150.0, None, cfg) == 1.0

    def test_below_threshold(self):
        cfg = _build_config({})
        # target = 150, price = 160 → overshoot = 6.7% < 20%
        assert _calculate_m_target(160.0, 150.0, cfg) == 1.0

    def test_moderate_overshoot(self):
        cfg = _build_config({})
        # target = 100, price = 125 → overshoot = 25% > 20%
        assert _calculate_m_target(125.0, 100.0, cfg) == 0.85

    def test_severe_overshoot(self):
        cfg = _build_config({})
        # target = 100, price = 160 → overshoot = 60% > 50%
        assert _calculate_m_target(160.0, 100.0, cfg) == 0.60

    def test_disabled(self):
        cfg = _build_config({"target_overshoot_enabled": False})
        assert _calculate_m_target(200.0, 100.0, cfg) == 1.0


class TestMVix:

    def test_low_vix(self):
        cfg = _build_config({})
        assert _calculate_m_vix(15.0, cfg) == 1.0

    def test_elevated_vix(self):
        cfg = _build_config({})
        # VIX=25, start=20, rate=0.02 → 1.0 - 5*0.02 = 0.90
        assert _calculate_m_vix(25.0, cfg) == 0.90

    def test_extreme_vix_floors_at_0_5(self):
        cfg = _build_config({})
        # VIX=50, 1.0 - 30*0.02 = 0.40 → floor 0.5
        assert _calculate_m_vix(50.0, cfg) == 0.5


# ============================================================================
# Sizing
# ============================================================================

class TestCalculateSizing:

    def test_basic_sizing(self):
        stock = _make_stock(price=150.0, atr=3.0)
        cfg = _build_config({})
        pos = _calculate_sizing(stock, 80.0, cfg)

        assert pos is not None
        assert pos.ticker == "AAPL"
        assert pos.quantity > 0
        assert pos.stop_loss < pos.entry_price
        assert pos.tp1 > pos.entry_price
        assert pos.tp2 > pos.tp1

    def test_gex_multiplier_reduces_size(self):
        stock = _make_stock(price=150.0, atr=3.0)
        cfg = _build_config({})

        pos_neutral = _calculate_sizing(stock, 80.0, cfg, gex_multiplier=1.0)
        pos_reduced = _calculate_sizing(stock, 80.0, cfg, gex_multiplier=0.5)

        assert pos_neutral is not None and pos_reduced is not None
        assert pos_reduced.quantity < pos_neutral.quantity

    def test_zero_atr_returns_none(self):
        stock = _make_stock(atr=0.0)
        cfg = _build_config({})
        assert _calculate_sizing(stock, 80.0, cfg) is None


# ============================================================================
# rescore_snapshot — end-to-end
# ============================================================================

class TestRescoreSnapshot:

    def test_basic_rescore(self):
        records = [
            _make_snapshot_record(ticker="AAPL", combined_score=80.0),
            _make_snapshot_record(ticker="MSFT", combined_score=75.0),
        ]
        positions = rescore_snapshot(records)
        assert len(positions) > 0
        assert all(isinstance(p, RescoredPosition) for p in positions)

    def test_sorted_by_score_descending(self):
        records = [
            _make_snapshot_record(ticker="LOW", rvol_score=-5, funda_score=5,
                                  rsi_score=10, sma50_bonus=0, rs_spy_score=0),
            _make_snapshot_record(ticker="HIGH", rvol_score=20, funda_score=15,
                                  rsi_score=30, sma50_bonus=30, rs_spy_score=40),
        ]
        positions = rescore_snapshot(records)
        if len(positions) >= 2:
            assert positions[0].combined_score >= positions[1].combined_score

    def test_ewma_changes_scores(self):
        records = [_make_snapshot_record(ticker="AAPL")]

        pos_no_ewma = rescore_snapshot(records, {"ewma_enabled": False})
        ewma_state = {"AAPL": 60.0}  # Deliberately low previous
        pos_with_ewma = rescore_snapshot(
            records, {"ewma_enabled": True, "ewma_span": 10},
            ewma_state=ewma_state,
        )

        # EWMA should pull the score down toward the 60.0 previous
        if pos_no_ewma and pos_with_ewma:
            assert pos_with_ewma[0].combined_score < pos_no_ewma[0].combined_score

    def test_max_positions_cap(self):
        records = [_make_snapshot_record(ticker=f"T{i}") for i in range(20)]
        positions = rescore_snapshot(records, {"max_positions": 3})
        assert len(positions) <= 3

    def test_empty_snapshot(self):
        assert rescore_snapshot([]) == []

    def test_below_min_score_filtered(self):
        records = [_make_snapshot_record(
            ticker="WEAK", rvol_score=-20, funda_score=-10,
            rsi_score=0, sma50_bonus=0, rs_spy_score=0,
        )]
        positions = rescore_snapshot(records)
        # Score too low → no positions
        assert len(positions) == 0

    def test_config_override_weight_changes_ranking(self):
        """Different weights can change which ticker gets selected."""
        high_flow = _make_snapshot_record(
            ticker="FLOW", rvol_score=30, funda_score=0,
            rsi_score=15, sma50_bonus=15, rs_spy_score=20,
        )
        high_funda = _make_snapshot_record(
            ticker="FUNDA", rvol_score=0, funda_score=25,
            rsi_score=15, sma50_bonus=15, rs_spy_score=20,
        )
        records = [high_flow, high_funda]

        # Flow-heavy weighting
        pos_flow = rescore_snapshot(records, {"weight_flow": 0.60, "weight_fundamental": 0.20, "weight_technical": 0.20})
        # Funda-heavy weighting
        pos_funda = rescore_snapshot(records, {"weight_flow": 0.20, "weight_fundamental": 0.60, "weight_technical": 0.20})

        if pos_flow and pos_funda:
            assert pos_flow[0].ticker == "FLOW"
            assert pos_funda[0].ticker == "FUNDA"
