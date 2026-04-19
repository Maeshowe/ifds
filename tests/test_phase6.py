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
    _replace_quantity,
)


@pytest.fixture
def config(monkeypatch, tmp_path):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    c = Config()
    c.runtime["daily_trades_file"] = str(tmp_path / "daily_trades.json")
    c.runtime["daily_notional_file"] = str(tmp_path / "daily_notional.json")
    return c


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
                combined_score=90.0, rvol_score=0, funda_score=15,
                insider_multiplier=1.0):
    """Create a StockAnalysis for Phase 6 input.

    Note: funda_score default=15 so base+score=50+15=65 >= threshold(60) → M_funda=1.0
    BC23: combined_score default=90 (was 75) to pass dynamic_position_score_threshold=85
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
    def test_m_flow_always_one(self, config, macro):
        # BC23: M_flow fixed at 1.0 regardless of flow score
        stock = _make_stock("T", rvol_score=35)
        gex = _make_gex("T")
        m_total, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_flow"] == 1.0

    def test_m_flow_below_threshold(self, config, macro):
        # rvol_score=0 → flow_score=50 ≤ 80 → 1.0
        stock = _make_stock("T", rvol_score=0)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_flow"] == 1.0

    def test_m_insider_always_one_buy(self, config, macro):
        # BC23: M_insider fixed at 1.0 regardless of insider activity
        stock = _make_stock("T", insider_multiplier=1.25)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_insider"] == 1.0

    def test_m_insider_always_one_sell(self, config, macro):
        # BC23: M_insider fixed at 1.0 regardless of insider activity
        stock = _make_stock("T", insider_multiplier=0.75)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_insider"] == 1.0

    def test_m_insider_neutral(self, config, macro):
        stock = _make_stock("T", insider_multiplier=1.0)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_insider"] == 1.0

    def test_m_funda_always_one(self, config, macro):
        # BC23: M_funda fixed at 1.0 regardless of fundamental score
        stock = _make_stock("T", funda_score=-5)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_funda"] == 1.0

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

    def test_m_utility_always_one(self, config, macro):
        # BC23: M_utility fixed at 1.0 regardless of combined score
        stock = _make_stock("T", combined_score=90.0)
        gex = _make_gex("T")
        _, mults = _calculate_multiplier_total(stock, gex, macro, config)
        assert mults["m_utility"] == 1.0

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
        stock = _make_stock("AAPL", price=150.0, atr=3.0)
        gex = _make_gex("AAPL")
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)

        assert pos is not None
        assert pos.ticker == "AAPL"
        assert pos.direction == "BUY"
        # BC23: BaseRisk = 100000 * 0.7 / 100 = $700
        # M_utility = min(1.3, 1.0 + (90-85)/100) = 1.05 (combined_score=90)
        # AdjustedRisk = 700 * 1.05 = 735
        # StopDistance = 1.5 * 3.0 = 4.5
        # Quantity = floor(735 / 4.5) = 163
        # Fat finger: 163 * 150 = $24,450 > $20K → floor(20000/150) = 133
        assert pos.quantity == 133
        # StopLoss = 150 - 4.5 = 145.5
        assert pos.stop_loss == 145.5
        # W16 follow-up: TP1 = 150 + 1.25*3 = 153.75 (tightened from 1.5)
        assert pos.take_profit_1 == 153.75
        # BC23: TP2 = 150 + 2.0*3 = 156.0
        assert pos.take_profit_2 == 156.0

    def test_basic_short_position(self, config, macro):
        stock = _make_stock("TSLA", price=200.0, atr=5.0)
        gex = _make_gex("TSLA", price=200.0)
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.SHORT)

        assert pos.direction == "SELL_SHORT"
        # SL = 200 + 1.5*5 = 207.5
        assert pos.stop_loss == 207.5
        # W16 follow-up: TP1 = 200 - 1.25*5 = 193.75 (tightened from 1.5)
        assert pos.take_profit_1 == 193.75
        # BC23: TP2 = 200 - 2.0*5 = 190.0
        assert pos.take_profit_2 == 190.0

    def test_tp1_always_atr_ignores_call_wall(self, config, macro):
        """BC23: call_wall is ignored — TP1 always ATR-based."""
        stock = _make_stock("AAPL", price=150.0, atr=3.0)
        gex = _make_gex("AAPL", call_wall=165.0)  # > entry, but irrelevant
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        # W16 follow-up: 150 + 1.25*3 = 153.75 (NOT call_wall)
        assert pos.take_profit_1 == 153.75

    def test_tp1_always_atr_ignores_put_wall(self, config, macro):
        """BC23: put_wall is ignored — TP1 always ATR-based."""
        stock = _make_stock("TSLA", price=200.0, atr=5.0)
        gex = _make_gex("TSLA", put_wall=180.0, price=200.0)
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.SHORT)
        # W16 follow-up: 200 - 1.25*5 = 193.75 (NOT put_wall)
        assert pos.take_profit_1 == 193.75

    def test_tp2_always_above_tp1_long(self, config, macro):
        """W16: TP2 = entry + 2.0*ATR > TP1 = entry + 1.25*ATR (guaranteed)."""
        stock = _make_stock("T", price=150.0, atr=3.0)
        gex = _make_gex("T")
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        assert pos.take_profit_2 == 156.0    # 150 + 2.0*3
        assert pos.take_profit_1 == 153.75   # 150 + 1.25*3
        assert pos.take_profit_2 > pos.take_profit_1

    def test_tp2_always_below_tp1_short(self, config, macro):
        """W16: TP2 = entry - 2.0*ATR < TP1 = entry - 1.25*ATR (guaranteed)."""
        stock = _make_stock("TSLA", price=200.0, atr=5.0)
        gex = _make_gex("TSLA", price=200.0)
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.SHORT)
        assert pos.take_profit_2 == 190.0    # 200 - 2.0*5
        assert pos.take_profit_1 == 193.75   # 200 - 1.25*5
        assert pos.take_profit_2 < pos.take_profit_1

    def test_tp1_ratio_to_sl(self, config, macro):
        """W16: TP1 (1.25*ATR) / SL (1.5*ATR) = 0.833:1 R:R."""
        stock = _make_stock("T", price=100.0, atr=4.0)
        gex = _make_gex("T")
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        tp1_distance = pos.take_profit_1 - 100.0
        sl_distance = 100.0 - pos.stop_loss
        ratio = tp1_distance / sl_distance
        assert ratio == pytest.approx(1.25 / 1.5, rel=1e-6)

    def test_quantity_rounded_down(self, config, macro):
        # BC23: BaseRisk=700, M_total=1.0 (all fixed), AdjustedRisk=700
        # ATR=3.33 → stop_dist=4.995 → 700/4.995=140.14 → 140
        stock = _make_stock("T", price=100.0, atr=3.33)
        gex = _make_gex("T")
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        assert pos.quantity == math.floor(700 / (1.5 * 3.33))

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
        assert pos.scale_out_pct == 0.50  # BC23: equal bracket split

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
    def _make_positions(self, n, sector="Technology", price=100.0, score=95.0):
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
                risk_usd=400.0, combined_score=95.0 - i,
                gex_regime="POSITIVE", multiplier_total=1.0,
            ))
        accepted, counts = _apply_position_limits(positions, config, logger)
        assert len(accepted) == 5  # BC23: max_positions=5
        # 12 positions: scores 95..84. Threshold=85 filters 1 (score=84) → 11 remain.
        # max_positions=5 → 6 excluded by position limit.
        assert counts["position"] == 6

    def test_sector_diversification(self, config, logger):
        # 5 Tech stocks → only 2 pass (BC23: max_positions_per_sector=2)
        positions = self._make_positions(5, sector="Technology")
        accepted, counts = _apply_position_limits(positions, config, logger)
        assert len(accepted) == 2  # BC23: max_positions_per_sector=2
        assert counts["sector"] == 3

    def test_sector_limit_keeps_highest_score(self, config, logger):
        positions = self._make_positions(4, sector="Energy", score=92.0)
        accepted, _ = _apply_position_limits(positions, config, logger)
        # BC23: max_positions_per_sector=2 → top 2 kept
        assert len(accepted) == 2
        assert accepted[0].combined_score == 92.0
        assert accepted[1].combined_score == 91.0

    def test_mixed_sectors_pass(self, config, logger):
        """Different sectors can fill up to max_positions."""
        tech = self._make_positions(3, sector="Technology", score=96.0)
        fin = self._make_positions(3, sector="Financials", score=93.0)
        health = self._make_positions(3, sector="Healthcare", score=90.0)
        positions = tech + fin + health
        # Sort by score descending (simulating what run_phase6 does)
        positions.sort(key=lambda p: p.combined_score, reverse=True)
        accepted, _ = _apply_position_limits(positions, config, logger)
        # BC23: max_per_sector=2, max_positions=5
        # Tech: 2 pass (sector limit), Fin: 2 pass, Health: 1 pass (position limit=5)
        assert len(accepted) == 5

    def test_max_single_position_risk(self, config, logger):
        # risk_usd=2000 > max (100000 * 1.5% = 1500)
        positions = [
            PositionSizing(
                ticker="BIG", sector="Technology", direction="BUY",
                entry_price=100.0, quantity=50, stop_loss=95.0,
                take_profit_1=106.0, take_profit_2=109.0,
                risk_usd=2000.0, combined_score=90.0,
                gex_regime="POSITIVE", multiplier_total=1.0,
            )
        ]
        accepted, counts = _apply_position_limits(positions, config, logger)
        assert len(accepted) == 0
        assert counts["risk"] == 1

    def test_max_gross_exposure(self, config, logger):
        # Each position: 50 * 2100 = $105K → exceeds max_gross($80K BC23)
        positions = [
            PositionSizing(
                ticker="EXP", sector="Technology", direction="BUY",
                entry_price=2100.0, quantity=50, stop_loss=2095.0,
                take_profit_1=2106.0, take_profit_2=2109.0,
                risk_usd=400.0, combined_score=90.0,
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
                risk_usd=400.0, combined_score=90.0,
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
        # BC23: freshness_bonus=1.0 → score unchanged (90 * 1.0 = 90)
        assert candidates[0][0].combined_score == 90.0
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
        assert candidates[0][0].combined_score == 90.0  # Unchanged
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
        assert candidates[0][0].combined_score == 90.0       # AAPL unchanged (stale)
        assert candidates[1][0].combined_score == 90.0   # BC23: MSFT unchanged (bonus=1.0)
        assert "AAPL" not in fresh_info
        assert "MSFT" in fresh_info


# ============================================================================
# Phase 6 Integration Tests
# ============================================================================

class TestPhase6Integration:
    def test_full_flow_long(self, config, logger, macro):
        stocks = [
            _make_stock("AAPL", price=150.0, atr=3.0, combined_score=92.0),
            _make_stock("MSFT", price=400.0, atr=8.0, combined_score=88.0),
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
                              atr=0.5, combined_score=95 - i)
                  for i in range(12)]
        gex = [_make_gex(f"T{i:02d}", price=10.0) for i in range(12)]

        result = run_phase6(config, logger, stocks, gex, macro,
                            StrategyMode.LONG, signal_history_path=None)

        assert len(result.positions) <= 5  # BC23: max_positions=5
        # Some exclusion must have occurred
        total_excluded = (result.excluded_position_limit +
                          result.excluded_exposure_limit +
                          result.excluded_sector_limit)
        assert total_excluded > 0

    def test_sector_limit_applied(self, config, logger, macro):
        """3+ stocks in same sector → sector limit kicks in (BC23: max=2)."""
        stocks = [_make_stock(f"T{i}", sector="Technology",
                              combined_score=95 - i)
                  for i in range(5)]
        gex = [_make_gex(f"T{i}") for i in range(5)]

        result = run_phase6(config, logger, stocks, gex, macro,
                            StrategyMode.LONG, signal_history_path=None)

        assert len(result.positions) == 2  # BC23: max_positions_per_sector=2
        assert result.excluded_sector_limit == 3

    def test_result_totals(self, config, logger, macro):
        stocks = [_make_stock("A", price=100.0, atr=2.0, combined_score=90)]
        gex = [_make_gex("A")]

        result = run_phase6(config, logger, stocks, gex, macro,
                            StrategyMode.LONG, signal_history_path=None)

        assert result.total_risk_usd == result.positions[0].risk_usd
        exposure = result.positions[0].quantity * result.positions[0].entry_price
        assert abs(result.total_exposure_usd - exposure) < 0.01

    def test_known_values(self, config, logger, macro):
        """Verify exact sizing for known input (NVDA-like scenario).

        BC23 simplified multiplier chain:
        - Price=875, ATR=14.5, CombinedScore=88
        - M_flow=1.0, M_insider=1.0, M_funda=1.0, M_utility=1.0 (all fixed)
        - M_gex=1.0, M_vix=1.0, M_target=1.0 (no analyst_target)
        - M_total = 1.0, BaseRisk=700
        """
        stock = _make_stock("NVDA", price=875.0, atr=14.5,
                            combined_score=88.0, rvol_score=35)
        gex = _make_gex("NVDA")

        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)

        # BC23: M_total = M_gex(1.0) * M_vix(1.0) * M_target(1.0) = 1.0
        # AdjustedRisk = 700 * 1.0 = 700
        # StopDist = 1.5 * 14.5 = 21.75
        # Quantity = floor(700 / 21.75) = 32
        # Fat finger cap (BC12): max_single_ticker_exposure/entry = 20000/875 = 22
        assert pos is not None
        assert pos.quantity == 22
        assert abs(pos.risk_usd - 700.0) < 0.01
        assert abs(pos.multiplier_total - 1.0) < 0.001
        # No freshness → original_score == combined_score, is_fresh == False
        assert pos.is_fresh is False
        assert pos.original_score == 88.0

    def test_freshness_audit_trail(self, config, logger, macro):
        """is_fresh and original_score correctly set when freshness applied."""
        original_scores = {"AAPL": 75.0}  # captured BEFORE freshness
        fresh_tickers = {"AAPL"}  # AAPL received freshness bonus
        stock = _make_stock("AAPL", combined_score=112.5)  # post-bonus: 75 * 1.5
        gex = _make_gex("AAPL")
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG,
                                  original_scores, fresh_tickers)
        assert pos is not None
        assert pos.is_fresh is True
        assert pos.original_score == 75.0
        assert pos.combined_score == 112.5  # 75 * 1.5

    def test_freshness_preserves_ranking(self, config, logger, macro):
        """Freshness bonus=1.0 (BC23) → scores unchanged, ranking preserved.

        3 tickers with scores [95, 90, 87] — bonus=1.0 means no change.
        All above dynamic_position_score_threshold=85.
        """
        stocks = [
            _make_stock("A", sector="Technology", combined_score=95.0),
            _make_stock("B", sector="Healthcare", combined_score=90.0),
            _make_stock("C", sector="Energy", combined_score=87.0),
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
        assert result.positions[0].original_score == 95.0
        assert result.positions[1].original_score == 90.0
        assert result.positions[2].original_score == 87.0
        # BC23: freshness_bonus=1.0 → combined_score unchanged
        assert result.positions[0].combined_score == 95.0
        assert result.positions[1].combined_score == 90.0
        assert result.positions[2].combined_score == 87.0


# ============================================================================
# dataclasses.replace() — mm_regime preservation (F2 fix)
# ============================================================================


class TestDataclassesReplace:
    """Verify _replace_quantity and _apply_position_limits preserve all fields."""

    def test_replace_quantity_preserves_mm_regime(self):
        """_replace_quantity must not drop mm_regime or unusualness_score."""
        pos = PositionSizing(
            ticker="AAPL", sector="Technology", direction="BUY",
            entry_price=150.0, quantity=100, stop_loss=145.0,
            take_profit_1=158.0, take_profit_2=163.0,
            risk_usd=500.0, combined_score=80.0,
            gex_regime="POSITIVE", multiplier_total=1.2,
            mm_regime="gamma_positive", unusualness_score=0.75,
        )
        updated = _replace_quantity(pos, new_qty=10)
        assert updated.quantity == 10
        assert updated.mm_regime == "gamma_positive"
        assert updated.unusualness_score == 0.75
        # Other fields unchanged
        assert updated.ticker == "AAPL"
        assert updated.entry_price == 150.0
        assert updated.combined_score == 80.0

    def test_apply_position_limits_preserves_mm_regime(self, config, logger):
        """Exposure reduction in _apply_position_limits must not drop mm_regime."""
        # Single position with notional > max_single_ticker_exposure ($20K)
        # but within risk_usd and gross exposure limits
        pos = PositionSizing(
            ticker="NVDA", sector="Technology", direction="BUY",
            entry_price=150.0, quantity=200, stop_loss=145.0,
            take_profit_1=158.0, take_profit_2=163.0,
            risk_usd=500.0, combined_score=90.0,
            gex_regime="POSITIVE", multiplier_total=1.5,
            mm_regime="dark_dominant", unusualness_score=0.62,
        )
        # 200 * 150 = $30K > max_single_ticker_exposure ($20K) → reduced
        accepted, _ = _apply_position_limits([pos], config, logger)
        assert len(accepted) == 1
        assert accepted[0].mm_regime == "dark_dominant"
        assert accepted[0].unusualness_score == 0.62
        assert accepted[0].quantity < 200  # reduced


class TestMTargetLoggerFix:
    """Regression test: _calculate_position must not crash when M_target logs."""

    def test_m_target_penalty_logs_with_logger(self, config, logger, macro):
        """When M_target < 1.0 and logger is passed, logger.log is called."""
        stock = _make_stock("OVER", price=155.0, atr=3.0, combined_score=75.0)
        stock.analyst_target = 100.0  # 55% overshoot → severe penalty
        gex = _make_gex("OVER")
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG,
                                  logger=logger)
        assert pos is not None
        assert pos.m_target == pytest.approx(0.60)

    def test_m_target_penalty_no_crash_without_logger(self, config, macro):
        """_calculate_position works without logger (default None)."""
        stock = _make_stock("OVER", price=155.0, atr=3.0, combined_score=75.0)
        stock.analyst_target = 100.0
        gex = _make_gex("OVER")
        pos = _calculate_position(stock, gex, macro, config, StrategyMode.LONG)
        assert pos is not None
        assert pos.m_target == pytest.approx(0.60)
