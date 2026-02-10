"""Tests for Phase 6: Position Sizing & Risk Management."""

import math
import pytest
from unittest.mock import MagicMock, patch

from ifds.config.loader import Config
from ifds.events.logger import EventLogger
from ifds.models.market import (
    FlowAnalysis,
    FundamentalScoring,
    GEXAnalysis,
    GEXRegime,
    MacroRegime,
    MarketVolatilityRegime,
    Phase6Result,
    PositionSizing,
    StockAnalysis,
    StrategyMode,
    TechnicalAnalysis,
)
from ifds.phases.phase6_sizing import (
    run_phase6,
    _join_stock_gex,
    _calculate_multiplier_total,
    _calculate_position,
    _apply_position_limits,
    _apply_freshness_alpha,
)


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    return Config()


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-phase6")


@pytest.fixture
def macro():
    return MacroRegime(
        vix_value=18.0, vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0, tnx_value=4.2, tnx_sma20=4.1,
        tnx_rate_sensitive=False,
    )


def _make_stock(ticker, sector="Technology", price=150.0, atr=3.0,
                combined_score=75.0, rvol_score=0, funda_score=15,
                insider_multiplier=1.0):
    """Create a StockAnalysis for Phase 6 input.

    Note: funda_score default=15 so base+score=50+15=65 >= threshold(60) → M_funda=1.0
    """
    return StockAnalysis(
        ticker=ticker, sector=sector,
        technical=TechnicalAnalysis(
            price=price, sma_200=140.0, sma_20=148.0,
            rsi_14=55.0, atr_14=atr, trend_pass=True,
        ),
        flow=FlowAnalysis(rvol_score=rvol_score),
        fundamental=FundamentalScoring(
            funda_score=funda_score,
            insider_multiplier=insider_multiplier,
        ),
        combined_score=combined_score,
    )


def _make_gex(ticker, regime=GEXRegime.POSITIVE, multiplier=1.0,
              call_wall=0.0, put_wall=0.0, price=150.0):
    """Create a GEXAnalysis for Phase 6 input."""
    return GEXAnalysis(
        ticker=ticker, net_gex=500.0, call_wall=call_wall,
        put_wall=put_wall, zero_gamma=140.0, current_price=price,
        gex_regime=regime, gex_multiplier=multiplier,
    )


# ============================================================================
# Stock-GEX Join Tests
# ============================================================================

class TestStockGexJoin:
    def test_inner_join_by_ticker(self):
        stocks = [_make_stock("AAPL"), _make_stock("MSFT")]
        gex = [_make_gex("AAPL"), _make_gex("MSFT")]
        result = _join_stock_gex(stocks, gex)
        assert len(result) == 2
        assert result[0][0].ticker == "AAPL"
        assert result[1][0].ticker == "MSFT"

    def test_missing_gex_excluded(self):
        stocks = [_make_stock("AAPL"), _make_stock("MSFT")]
        gex = [_make_gex("AAPL")]  # No MSFT
        result = _join_stock_gex(stocks, gex)
        assert len(result) == 1
        assert result[0][0].ticker == "AAPL"

    def test_missing_stock_excluded(self):
        stocks = [_make_stock("AAPL")]
        gex = [_make_gex("AAPL"), _make_gex("GOOG")]
        result = _join_stock_gex(stocks, gex)
        assert len(result) == 1

    def test_empty_inputs(self):
        assert _join_stock_gex([], []) == []
        assert _join_stock_gex([_make_stock("A")], []) == []
        assert _join_stock_gex([], [_make_gex("A")]) == []


# ============================================================================
# Multiplier Calculation Tests
# ============================================================================

class TestMultiplierCalculation:
    def test_m_flow_above_threshold(self, config, macro):
        # rvol_score=35 → flow_score=50+35=85 > threshold(80) → 1.25
        stock = _make_stock("T", rvol_score=35)
        gex = _make_gex("T")
        m_total, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_flow"] == 1.25

    def test_m_flow_below_threshold(self, config, macro):
        # rvol_score=0 → flow_score=50 ≤ 80 → 1.0
        stock = _make_stock("T", rvol_score=0)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_flow"] == 1.0

    def test_m_insider_buy_multiplier(self, config, macro):
        stock = _make_stock("T", insider_multiplier=1.25)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_insider"] == 1.25

    def test_m_insider_sell_multiplier(self, config, macro):
        stock = _make_stock("T", insider_multiplier=0.75)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_insider"] == 0.75

    def test_m_insider_neutral(self, config, macro):
        stock = _make_stock("T", insider_multiplier=1.0)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_insider"] == 1.0

    def test_m_funda_below_threshold(self, config, macro):
        # funda_score=-5 → 50+(-5)=45 < threshold(60) → 0.50
        stock = _make_stock("T", funda_score=-5)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_funda"] == 0.50

    def test_m_funda_above_threshold(self, config, macro):
        # funda_score=15 → 50+15=65 ≥ 60 → 1.0
        stock = _make_stock("T", funda_score=15)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_funda"] == 1.0

    def test_m_gex_positive(self, config, macro):
        stock = _make_stock("T")
        gex = _make_gex("T", regime=GEXRegime.POSITIVE, multiplier=1.0)
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_gex"] == 1.0

    def test_m_gex_negative(self, config, macro):
        stock = _make_stock("T")
        gex = _make_gex("T", regime=GEXRegime.NEGATIVE, multiplier=0.5)
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_gex"] == 0.5

    def test_m_gex_high_vol(self, config, macro):
        stock = _make_stock("T")
        gex = _make_gex("T", regime=GEXRegime.HIGH_VOL, multiplier=0.6)
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_gex"] == 0.6

    def test_m_vix_normal(self, config, macro):
        # VIX=18, multiplier=1.0
        stock = _make_stock("T")
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_vix"] == 1.0

    def test_m_vix_elevated(self, config):
        # VIX=30 → multiplier = max(0.25, 1-(30-20)*0.02) = 0.80
        macro_high = MacroRegime(
            vix_value=30.0, vix_regime=MarketVolatilityRegime.ELEVATED,
            vix_multiplier=0.80, tnx_value=4.2, tnx_sma20=4.1,
            tnx_rate_sensitive=False,
        )
        stock = _make_stock("T")
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro_high, config)
        assert mults["m_vix"] == 0.80

    def test_m_utility_above_threshold(self, config, macro):
        # combined_score=90 > 85 → min(1.3, 1.0 + (90-85)/100) = 1.05
        stock = _make_stock("T", combined_score=90.0)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert abs(mults["m_utility"] - 1.05) < 0.001

    def test_m_utility_below_threshold(self, config, macro):
        stock = _make_stock("T", combined_score=80.0)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_utility"] == 1.0

    def test_m_total_clamped_min(self, config):
        """All multipliers penalizing — total should not go below 0.25."""
        macro_panic = MacroRegime(
            vix_value=50.0, vix_regime=MarketVolatilityRegime.PANIC,
            vix_multiplier=0.25, tnx_value=5.0, tnx_sma20=4.0,
            tnx_rate_sensitive=True,
        )
        stock = _make_stock("T", insider_multiplier=0.75, funda_score=-20)
        gex = _make_gex("T", multiplier=0.5)
        m_total, _ = _calculate_multiplier_total(stock, gex, macro_panic, config)
        assert m_total == 0.25

    def test_m_total_clamped_max(self, config, macro):
        """All multipliers boosting — total should not exceed 2.0."""
        stock = _make_stock("T", rvol_score=35, insider_multiplier=1.25,
                            funda_score=15, combined_score=90.0)
        gex = _make_gex("T", multiplier=1.0)
        m_total, _ = _calculate_multiplier_total(stock, gex, macro, config)
        assert m_total <= 2.0


# ============================================================================
# Position Sizing Tests
# ============================================================================

class TestPositionSizing:
    def test_basic_long_position(self, config, macro):
        stock = _make_stock("AAPL", price=150.0, atr=3.0, combined_score=75.0)
        gex = _make_gex("AAPL")
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)

        assert pos is not None
        assert pos.ticker == "AAPL"
        assert pos.direction == "BUY"
        # BaseRisk = 100000 * 0.5 / 100 = $500
        # M_total = 1.0 (all neutral)
        # StopDistance = 1.5 * 3.0 = 4.5
        # Quantity = floor(500 / 4.5) = 111
        assert pos.quantity == 111
        # StopLoss = 150 - 4.5 = 145.5
        assert pos.stop_loss == 145.5
        # TP1 (no call_wall) = 150 + 2.0*3 = 156
        assert pos.take_profit_1 == 156.0
        # TP2 = 150 + 3.0*3 = 159
        assert pos.take_profit_2 == 159.0

    def test_basic_short_position(self, config, macro):
        stock = _make_stock("TSLA", price=200.0, atr=5.0)
        gex = _make_gex("TSLA", price=200.0)
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.SHORT)

        assert pos.direction == "SELL_SHORT"
        # SL = 200 + 1.5*5 = 207.5
        assert pos.stop_loss == 207.5
        # TP1 = 200 - 2.0*5 = 190
        assert pos.take_profit_1 == 190.0
        # TP2 = 200 - 3.0*5 = 185
        assert pos.take_profit_2 == 185.0

    def test_tp1_uses_call_wall_when_valid(self, config, macro):
        stock = _make_stock("AAPL", price=150.0, atr=3.0)
        gex = _make_gex("AAPL", call_wall=165.0)  # > entry
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        assert pos.take_profit_1 == 165.0

    def test_tp1_ignores_call_wall_below_entry(self, config, macro):
        stock = _make_stock("AAPL", price=150.0, atr=3.0)
        gex = _make_gex("AAPL", call_wall=140.0)  # < entry
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        # Falls back to ATR: 150 + 2*3 = 156
        assert pos.take_profit_1 == 156.0

    def test_short_tp1_uses_put_wall(self, config, macro):
        stock = _make_stock("TSLA", price=200.0, atr=5.0)
        gex = _make_gex("TSLA", put_wall=180.0, price=200.0)
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.SHORT)
        assert pos.take_profit_1 == 180.0

    def test_tp2_adjusted_when_call_wall_exceeds_tp2_long(self, config, macro):
        """LONG: call_wall=170 > entry+3*ATR=159 → TP1=170, TP2 must be > TP1."""
        stock = _make_stock("MPLX", price=150.0, atr=3.0)
        gex = _make_gex("MPLX", call_wall=170.0)  # Higher than entry + 3*ATR = 159
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        assert pos.take_profit_1 == 170.0
        # TP2 would be 150+3*3=159 < TP1=170, so TP2 = TP1 + ATR = 173
        assert pos.take_profit_2 == 173.0
        assert pos.take_profit_2 > pos.take_profit_1

    def test_tp2_not_adjusted_when_call_wall_below_tp2_long(self, config, macro):
        """LONG: call_wall=155 < entry+3*ATR=159 → TP1=155, TP2=159 (no fix needed)."""
        stock = _make_stock("T", price=150.0, atr=3.0)
        gex = _make_gex("T", call_wall=155.0)
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        assert pos.take_profit_1 == 155.0
        assert pos.take_profit_2 == 159.0
        assert pos.take_profit_2 > pos.take_profit_1

    def test_tp2_adjusted_when_put_wall_below_tp2_short(self, config, macro):
        """SHORT: put_wall=175 < entry=200, TP2=200-3*5=185 > TP1=175, so fix needed."""
        stock = _make_stock("TSLA", price=200.0, atr=5.0)
        gex = _make_gex("TSLA", put_wall=175.0, price=200.0)
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.SHORT)
        assert pos.take_profit_1 == 175.0
        # TP2 would be 200-3*5=185 > TP1=175, so TP2 = TP1 - ATR = 170
        assert pos.take_profit_2 == 170.0
        assert pos.take_profit_2 < pos.take_profit_1

    def test_quantity_rounded_down(self, config, macro):
        # BaseRisk=500, ATR=3.33 → stop_dist=4.995 → 500/4.995=100.1 → 100
        stock = _make_stock("T", price=100.0, atr=3.33)
        gex = _make_gex("T")
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        assert pos.quantity == math.floor(500 / (1.5 * 3.33))

    def test_zero_atr_returns_none(self, config, macro):
        stock = _make_stock("T", atr=0.0)
        gex = _make_gex("T")
        assert _calculate_position(stock, gex, macro, config, StrategyMode.LONG) is None

    def test_scale_out_price(self, config, macro):
        stock = _make_stock("T", price=100.0, atr=2.0)
        gex = _make_gex("T")
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        # scale_out = 100 + 2.0*2 = 104
        assert pos.scale_out_price == 104.0
        assert pos.scale_out_pct == 0.33

    def test_multiplier_affects_quantity(self, config, macro):
        """Higher multiplier → higher adjusted risk → more shares."""
        stock = _make_stock("T", price=100.0, atr=2.0, rvol_score=35,
                            insider_multiplier=1.25)
        gex = _make_gex("T")
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        # M_flow=1.25, M_insider=1.25 → M_total = 1.5625
        # AdjustedRisk = 500 * 1.5625 = 781.25
        # Quantity = floor(781.25 / 3.0) = 260
        assert pos.quantity > 111  # More than neutral case


# ============================================================================
# Position Limits Tests
# ============================================================================

class TestPositionLimits:
    def _make_positions(self, n, sector="Technology", price=100.0, score=75.0):
        return [
            PositionSizing(
                ticker=f"T{i:02d}", sector=sector, direction="BUY",
                entry_price=price, quantity=50, stop_loss=95.0,
                take_profit_1=106.0, take_profit_2=109.0,
                risk_usd=400.0, combined_score=score - i,
                gex_regime="POSITIVE", multiplier_total=1.0,
            )
            for i in range(n)
        ]

    def test_max_positions_limit(self, config, logger):
        # Use different sectors to avoid sector limit triggering first
        sectors = ["S0", "S1", "S2", "S3", "S4", "S5"]
        positions = []
        for i in range(12):
            positions.append(PositionSizing(
                ticker=f"T{i:02d}", sector=sectors[i % len(sectors)],
                direction="BUY", entry_price=100.0, quantity=50,
                stop_loss=95.0, take_profit_1=106.0, take_profit_2=109.0,
                risk_usd=400.0, combined_score=75.0 - i,
                gex_regime="POSITIVE", multiplier_total=1.0,
            ))
        accepted, counts = _apply_position_limits(positions, config, logger)
        assert len(accepted) == 8  # max_positions=8
        assert counts["position"] == 4

    def test_sector_diversification(self, config, logger):
        # 5 Tech stocks → only 3 pass
        positions = self._make_positions(5, sector="Technology")
        accepted, counts = _apply_position_limits(positions, config, logger)
        assert len(accepted) == 3  # max_positions_per_sector=3
        assert counts["sector"] == 2

    def test_sector_limit_keeps_highest_score(self, config, logger):
        positions = self._make_positions(4, sector="Energy", score=80.0)
        accepted, _ = _apply_position_limits(positions, config, logger)
        # First three (highest scores) should be kept
        assert len(accepted) == 3
        assert accepted[0].combined_score == 80.0
        assert accepted[1].combined_score == 79.0
        assert accepted[2].combined_score == 78.0

    def test_mixed_sectors_pass(self, config, logger):
        """Different sectors can fill up to max_positions."""
        tech = self._make_positions(3, sector="Technology", score=80.0)
        fin = self._make_positions(3, sector="Financials", score=70.0)
        health = self._make_positions(3, sector="Healthcare", score=60.0)
        positions = tech + fin + health
        # Sort by score descending (simulating what run_phase6 does)
        positions.sort(key=lambda p: p.combined_score, reverse=True)
        accepted, _ = _apply_position_limits(positions, config, logger)
        # 3 Tech + 3 Fin + 2 Health = 8, all within max_positions(8)
        assert len(accepted) == 8

    def test_max_single_position_risk(self, config, logger):
        # risk_usd=2000 > max (100000 * 1.5% = 1500)
        positions = [
            PositionSizing(
                ticker="BIG", sector="Technology", direction="BUY",
                entry_price=100.0, quantity=50, stop_loss=95.0,
                take_profit_1=106.0, take_profit_2=109.0,
                risk_usd=2000.0, combined_score=80.0,
                gex_regime="POSITIVE", multiplier_total=1.0,
            )
        ]
        accepted, counts = _apply_position_limits(positions, config, logger)
        assert len(accepted) == 0
        assert counts["risk"] == 1

    def test_max_gross_exposure(self, config, logger):
        # Each position: 50 * 2100 = $105K → exceeds max_gross($100K)
        positions = [
            PositionSizing(
                ticker="EXP", sector="Technology", direction="BUY",
                entry_price=2100.0, quantity=50, stop_loss=2095.0,
                take_profit_1=2106.0, take_profit_2=2109.0,
                risk_usd=400.0, combined_score=80.0,
                gex_regime="POSITIVE", multiplier_total=1.0,
            )
        ]
        accepted, counts = _apply_position_limits(positions, config, logger)
        assert len(accepted) == 0
        assert counts["exposure"] == 1

    def test_max_single_ticker_exposure(self, config, logger):
        # 200 * 150 = $30K > max_single_ticker($20K) → reduce to 133
        positions = [
            PositionSizing(
                ticker="RED", sector="Technology", direction="BUY",
                entry_price=150.0, quantity=200, stop_loss=145.0,
                take_profit_1=156.0, take_profit_2=159.0,
                risk_usd=400.0, combined_score=80.0,
                gex_regime="POSITIVE", multiplier_total=1.0,
            )
        ]
        accepted, counts = _apply_position_limits(positions, config, logger)
        assert len(accepted) == 1
        # floor(20000 / 150) = 133
        assert accepted[0].quantity == 133

    def test_empty_input(self, config, logger):
        accepted, counts = _apply_position_limits([], config, logger)
        assert len(accepted) == 0
        assert all(v == 0 for v in counts.values())

    def test_single_position_passes(self, config, logger):
        positions = self._make_positions(1, price=100.0)
        accepted, counts = _apply_position_limits(positions, config, logger)
        assert len(accepted) == 1
        assert all(v == 0 for v in counts.values())


# ============================================================================
# Freshness Alpha Tests
# ============================================================================

_has_pandas = pytest.importorskip("pandas", reason="pandas required for freshness tests") if False else None
try:
    import pandas as _pd
    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False

_skip_no_pandas = pytest.mark.skipif(not _PANDAS_AVAILABLE, reason="pandas not installed")


class TestFreshnessAlpha:
    @_skip_no_pandas
    def test_all_fresh_when_no_history(self, config, logger, tmp_path):
        """All signals fresh when no history file exists."""
        candidates = [(_make_stock("AAPL"), _make_gex("AAPL"))]
        history_path = str(tmp_path / "nonexistent.parquet")
        count, fresh_info = _apply_freshness_alpha(candidates, config, history_path, logger)
        assert count == 1
        # Score should be multiplied by freshness_bonus (1.5), capped to 100
        assert candidates[0][0].combined_score == 100.0  # min(100, 75 * 1.5)
        # fresh_info is now a set of fresh ticker symbols
        assert "AAPL" in fresh_info

    @_skip_no_pandas
    def test_stale_ticker_no_bonus(self, config, logger, tmp_path):
        """Ticker seen recently should NOT get bonus."""
        import pandas as pd
        from datetime import date

        history_path = str(tmp_path / "history.parquet")
        df = pd.DataFrame({"ticker": ["AAPL"], "date": [date.today()]})
        df.to_parquet(history_path, index=False)

        candidates = [(_make_stock("AAPL"), _make_gex("AAPL"))]
        count, fresh_info = _apply_freshness_alpha(candidates, config, history_path, logger)
        assert count == 0
        assert candidates[0][0].combined_score == 75.0  # Unchanged
        assert "AAPL" not in fresh_info

    @_skip_no_pandas
    def test_old_ticker_is_fresh(self, config, logger, tmp_path):
        """Ticker seen >90 days ago should be fresh."""
        import pandas as pd
        from datetime import date, timedelta

        history_path = str(tmp_path / "history.parquet")
        old_date = date.today() - timedelta(days=91)
        df = pd.DataFrame({"ticker": ["AAPL"], "date": [old_date]})
        df.to_parquet(history_path, index=False)

        candidates = [(_make_stock("AAPL"), _make_gex("AAPL"))]
        count, fresh_info = _apply_freshness_alpha(candidates, config, history_path, logger)
        assert count == 1
        assert "AAPL" in fresh_info

    @_skip_no_pandas
    def test_history_appended(self, config, logger, tmp_path):
        """Current run signals appended to history."""
        import pandas as pd

        history_path = str(tmp_path / "history.parquet")
        candidates = [
            (_make_stock("AAPL"), _make_gex("AAPL")),
            (_make_stock("MSFT"), _make_gex("MSFT")),
        ]
        _count, _info = _apply_freshness_alpha(candidates, config, history_path, logger)

        df = pd.read_parquet(history_path)
        assert len(df) == 2
        assert set(df["ticker"]) == {"AAPL", "MSFT"}

    def test_no_pandas_returns_zero(self, config, logger):
        """Without pandas, freshness alpha returns 0 (graceful skip)."""
        candidates = [(_make_stock("T"), _make_gex("T"))]
        count, fresh_info = _apply_freshness_alpha(candidates, config, None, logger)
        if _PANDAS_AVAILABLE:
            assert count == 1
            assert "T" in fresh_info
        else:
            assert count == 0
            assert fresh_info == set()

    @_skip_no_pandas
    def test_lookback_boundary_exact(self, config, logger, tmp_path):
        """Ticker seen exactly 90 days ago should be stale (within lookback)."""
        import pandas as pd
        from datetime import date, timedelta

        history_path = str(tmp_path / "history.parquet")
        boundary_date = date.today() - timedelta(days=90)
        df = pd.DataFrame({"ticker": ["AAPL"], "date": [boundary_date]})
        df.to_parquet(history_path, index=False)

        candidates = [(_make_stock("AAPL"), _make_gex("AAPL"))]
        count, fresh_info = _apply_freshness_alpha(candidates, config, history_path, logger)
        assert count == 0  # 90 days = within lookback → stale
        assert "AAPL" not in fresh_info

    @_skip_no_pandas
    def test_mixed_fresh_and_stale(self, config, logger, tmp_path):
        """Mix of fresh and stale signals."""
        import pandas as pd
        from datetime import date

        history_path = str(tmp_path / "history.parquet")
        df = pd.DataFrame({"ticker": ["AAPL"], "date": [date.today()]})
        df.to_parquet(history_path, index=False)

        candidates = [
            (_make_stock("AAPL"), _make_gex("AAPL")),   # stale
            (_make_stock("MSFT"), _make_gex("MSFT")),    # fresh
        ]
        count, fresh_info = _apply_freshness_alpha(candidates, config, history_path, logger)
        assert count == 1
        assert candidates[0][0].combined_score == 75.0       # AAPL unchanged
        assert candidates[1][0].combined_score == 100.0  # MSFT boosted: min(100, 75 * 1.5)
        assert "AAPL" not in fresh_info
        assert "MSFT" in fresh_info


# ============================================================================
# Phase 6 Integration Tests
# ============================================================================

class TestPhase6Integration:
    def test_full_flow_long(self, config, logger, macro):
        stocks = [
            _make_stock("AAPL", price=150.0, atr=3.0, combined_score=80.0),
            _make_stock("MSFT", price=400.0, atr=8.0, combined_score=75.0),
        ]
        gex = [
            _make_gex("AAPL", call_wall=165.0),
            _make_gex("MSFT"),
        ]

        result = run_phase6(config, logger, stocks, gex, macro,
                            StrategyMode.LONG, signal_history_path=None)

        assert isinstance(result, Phase6Result)
        assert len(result.positions) == 2
        assert result.positions[0].ticker == "AAPL"  # Higher score first
        assert result.positions[0].direction == "BUY"
        assert result.total_risk_usd > 0
        assert result.total_exposure_usd > 0

    def test_full_flow_short(self, config, logger, macro):
        stocks = [_make_stock("TSLA", price=200.0, atr=5.0)]
        gex = [_make_gex("TSLA", put_wall=180.0, price=200.0)]

        result = run_phase6(config, logger, stocks, gex, macro,
                            StrategyMode.SHORT, signal_history_path=None)

        assert len(result.positions) == 1
        assert result.positions[0].direction == "SELL_SHORT"
        assert result.positions[0].stop_loss > 200.0  # Above entry for SHORT

    def test_empty_input(self, config, logger, macro):
        result = run_phase6(config, logger, [], [], macro,
                            StrategyMode.LONG, signal_history_path=None)
        assert len(result.positions) == 0

    def test_no_matching_gex(self, config, logger, macro):
        stocks = [_make_stock("AAPL")]
        gex = [_make_gex("MSFT")]  # Different ticker
        result = run_phase6(config, logger, stocks, gex, macro,
                            StrategyMode.LONG, signal_history_path=None)
        assert len(result.positions) == 0

    def test_position_limit_applied(self, config, logger, macro):
        """More than max_positions → limited by some limit (position or exposure)."""
        # Use low price so exposure doesn't hit limit first
        stocks = [_make_stock(f"T{i:02d}", sector=f"S{i}", price=10.0,
                              atr=0.5, combined_score=80 - i)
                  for i in range(12)]
        gex = [_make_gex(f"T{i:02d}", price=10.0) for i in range(12)]

        result = run_phase6(config, logger, stocks, gex, macro,
                            StrategyMode.LONG, signal_history_path=None)

        assert len(result.positions) <= 8
        # Some exclusion must have occurred
        total_excluded = (result.excluded_position_limit +
                          result.excluded_exposure_limit +
                          result.excluded_sector_limit)
        assert total_excluded > 0

    def test_sector_limit_applied(self, config, logger, macro):
        """3+ stocks in same sector → sector limit kicks in."""
        stocks = [_make_stock(f"T{i}", sector="Technology",
                              combined_score=80 - i)
                  for i in range(5)]
        gex = [_make_gex(f"T{i}") for i in range(5)]

        result = run_phase6(config, logger, stocks, gex, macro,
                            StrategyMode.LONG, signal_history_path=None)

        assert len(result.positions) == 3
        assert result.excluded_sector_limit == 2

    def test_result_totals(self, config, logger, macro):
        stocks = [_make_stock("A", price=100.0, atr=2.0, combined_score=78)]
        gex = [_make_gex("A")]

        result = run_phase6(config, logger, stocks, gex, macro,
                            StrategyMode.LONG, signal_history_path=None)

        assert result.total_risk_usd == result.positions[0].risk_usd
        exposure = result.positions[0].quantity * result.positions[0].entry_price
        assert abs(result.total_exposure_usd - exposure) < 0.01

    def test_known_values(self, config, logger, macro):
        """Verify exact sizing for known input (IDEA.md §5.6.4 NVDA example).

        Adapted: NVDA-like scenario
        - Price=875, ATR=14.5, CombinedScore=88 (>85 → M_utility)
        - M_flow=1.25 (flow_score>80), rest=1.0
        - BaseRisk=$500, StopDist=21.75
        """
        stock = _make_stock("NVDA", price=875.0, atr=14.5,
                            combined_score=88.0, rvol_score=35)
        gex = _make_gex("NVDA")

        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)

        # M_flow = 1.25 (50+35=85>80)
        # M_utility = min(1.3, 1.0 + (88-85)/100) = 1.03
        # M_total = 1.25 * 1.03 = 1.2875
        # AdjustedRisk = 500 * 1.2875 = 643.75
        # StopDist = 1.5 * 14.5 = 21.75
        # Quantity = floor(643.75 / 21.75) = 29
        # Fat finger cap (BC12): max_single_ticker_exposure/entry = 20000/875 = 22
        assert pos is not None
        assert pos.quantity == 22
        assert abs(pos.risk_usd - 643.75) < 0.01
        assert abs(pos.multiplier_total - 1.2875) < 0.001
        # No freshness → original_score == combined_score, is_fresh == False
        assert pos.is_fresh is False
        assert pos.original_score == 88.0

    def test_freshness_audit_trail(self, config, logger, macro):
        """is_fresh and original_score correctly set when freshness applied."""
        original_scores = {"AAPL": 75.0}  # captured BEFORE freshness
        fresh_tickers = {"AAPL"}  # AAPL received freshness bonus
        stock = _make_stock("AAPL", combined_score=100.0)  # post-bonus: min(100, 75 * 1.5)
        gex = _make_gex("AAPL")
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG,
                                  original_scores, fresh_tickers)
        assert pos is not None
        assert pos.is_fresh is True
        assert pos.original_score == 75.0
        assert pos.combined_score == 100.0  # min(100, 75 * 1.5)

    def test_freshness_preserves_ranking(self, config, logger, macro):
        """Freshness bonus should not destroy ranking differentiation.

        3 tickers with scores [85, 78, 72] — after freshness × 1.5,
        combined_score caps at 100.0 for all three.
        Sort by original_score preserves the ranking [85, 78, 72].
        """
        stocks = [
            _make_stock("A", sector="Technology", combined_score=85.0),
            _make_stock("B", sector="Healthcare", combined_score=78.0),
            _make_stock("C", sector="Energy", combined_score=72.0),
        ]
        gex = [_make_gex("A"), _make_gex("B"), _make_gex("C")]

        result = run_phase6(config, logger, stocks, gex, macro,
                            StrategyMode.LONG, signal_history_path=None)

        # All should be fresh (no history file → all are fresh)
        assert result.freshness_applied_count == 3
        # Positions should be sorted by original score (descending)
        assert len(result.positions) >= 3
        assert result.positions[0].ticker == "A"
        assert result.positions[1].ticker == "B"
        assert result.positions[2].ticker == "C"
        # Original scores preserved — this is the ranking key
        assert result.positions[0].original_score == 85.0
        assert result.positions[1].original_score == 78.0
        assert result.positions[2].original_score == 72.0
        # combined_score capped at 100 for all (freshness doesn't break the cap)
        for pos in result.positions[:3]:
            assert pos.combined_score == 100.0
