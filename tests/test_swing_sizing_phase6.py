"""Tests for Phase 6 swing sizing (Day 63 §3.7, §3.11 — Döntés 7, 11).

Covers:
- ``compute_swing_notional`` — 0.35% risk, ATR_pct denom, M_target penalty
- ``_calculate_swing_position`` — full PositionSizing build (only M_target active)
- ``_select_swing_entries`` — sector-balanced greedy fill, 12 cap, 30% sector cap
- ``run_phase6`` integration with ``swing_sizing_enabled=True``
"""

from __future__ import annotations

import math

import pytest

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
    _calculate_swing_position,
    _select_swing_entries,
    compute_swing_notional,
    run_phase6,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config(monkeypatch, tmp_path):
    monkeypatch.setenv("IFDS_POLYGON_API_KEY", "test_poly")
    monkeypatch.setenv("IFDS_FMP_API_KEY", "test_fmp")
    monkeypatch.setenv("IFDS_FRED_API_KEY", "test_fred")
    monkeypatch.setenv("IFDS_ASYNC_ENABLED", "false")
    c = Config()
    # Swing sizing path active by default in defaults.py — affirm here so the
    # test intent is explicit even if defaults change.
    c.tuning["swing_sizing_enabled"] = True
    c.tuning["swing_risk_per_trade_pct"] = 0.0035
    c.tuning["swing_max_concurrent"] = 12
    c.tuning["swing_max_daily_new"] = 3
    c.tuning["swing_sector_cap_pct"] = 0.30
    c.tuning["swing_stop_atr_multiple"] = 2.0
    c.tuning["swing_score_threshold"] = 50.0
    c.tuning["m_vix_enabled"] = False
    c.tuning["m_contradiction_enabled"] = False
    c.tuning["uw_gex_sizing_enabled"] = False
    c.tuning["portfolio_var_enabled"] = False  # avoid VaR trim noise here
    c.runtime["account_equity"] = 100_000
    c.runtime["max_positions"] = 12
    c.runtime["max_gross_exposure"] = 150_000
    c.runtime["max_single_ticker_exposure"] = 15_000
    c.runtime["daily_trades_file"] = str(tmp_path / "daily_trades.json")
    c.runtime["daily_notional_file"] = str(tmp_path / "daily_notional.json")
    return c


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_dir=str(tmp_path), run_id="test-swing-sizing")


@pytest.fixture
def macro():
    return MacroRegime(
        vix_value=18.0, vix_regime=MarketVolatilityRegime.NORMAL,
        vix_multiplier=1.0, tnx_value=4.2, tnx_sma20=4.1,
        tnx_rate_sensitive=False,
    )


def _make_stock(
    ticker: str,
    *,
    sector: str = "Technology",
    price: float = 150.0,
    atr: float = 3.0,
    combined_score: float = 80.0,
    analyst_target: float | None = None,
) -> StockAnalysis:
    return StockAnalysis(
        ticker=ticker,
        sector=sector,
        technical=TechnicalAnalysis(
            price=price, sma_200=140.0, sma_20=148.0,
            rsi_14=55.0, atr_14=atr, trend_pass=True,
        ),
        flow=FlowAnalysis(rvol_score=0),
        fundamental=FundamentalScoring(funda_score=15, insider_multiplier=1.0),
        combined_score=combined_score,
        analyst_target=analyst_target,
    )


def _make_gex(ticker: str, *, price: float = 150.0) -> GEXAnalysis:
    return GEXAnalysis(
        ticker=ticker, net_gex=500.0, call_wall=0.0, put_wall=0.0,
        zero_gamma=140.0, current_price=price,
        gex_regime=GEXRegime.POSITIVE, gex_multiplier=1.0,
    )


# ============================================================================
# compute_swing_notional
# ============================================================================


class TestComputeSwingNotional:
    def test_basic_formula(self, config):
        """notional = (equity × 0.0035) / (ATR_pct × 2.0) × M_target.

        equity=100k, risk=0.35%, ATR=$3, entry=$150 → ATR_pct=0.02
        → notional = 350 / 0.04 = $8,750
        """
        stock = _make_stock("AAPL", price=150.0, atr=3.0)
        notional, m_target, _ = compute_swing_notional(stock, config)
        assert m_target == 1.0
        assert notional == pytest.approx(8_750.0, rel=1e-6)

    def test_m_target_moderate_overshoot_penalty(self, config):
        """20-50% overshoot → ×0.85 notional."""
        # Price 150, analyst target 110 → overshoot = (150-110)/110 ≈ 36% (in 20-50% band)
        stock = _make_stock("AAPL", price=150.0, atr=3.0, analyst_target=110.0)
        notional, m_target, _ = compute_swing_notional(stock, config)
        assert m_target == 0.85
        assert notional == pytest.approx(8_750.0 * 0.85, rel=1e-6)

    def test_m_target_severe_overshoot_penalty(self, config):
        """>50% overshoot → ×0.60 notional."""
        # Price 150, analyst target 80 → overshoot = (150-80)/80 = 87.5% (> 50%)
        stock = _make_stock("AAPL", price=150.0, atr=3.0, analyst_target=80.0)
        notional, m_target, _ = compute_swing_notional(stock, config)
        assert m_target == 0.60
        assert notional == pytest.approx(8_750.0 * 0.60, rel=1e-6)

    def test_zero_atr_returns_zero(self, config):
        stock = _make_stock("AAPL", price=150.0, atr=0.0)
        notional, _, diag = compute_swing_notional(stock, config)
        assert notional == 0.0
        assert diag["reason"] == "invalid_atr_or_price"


# ============================================================================
# _calculate_swing_position
# ============================================================================


class TestCalculateSwingPosition:
    def test_basic_long_position(self, config):
        stock = _make_stock("AAPL", price=150.0, atr=3.0)
        gex = _make_gex("AAPL")
        pos = _calculate_swing_position(
            stock, gex, config, StrategyMode.LONG,
        )
        assert pos is not None
        assert pos.ticker == "AAPL"
        assert pos.direction == "BUY"
        # notional ≈ $8,750 → 58 shares × $150 = $8,700
        assert pos.quantity == 58
        # Stop = entry - 2.0 × ATR = 150 - 6 = 144
        assert pos.stop_loss == 144.0
        # Multipliers — only M_target active, rest forced to 1.0
        assert pos.m_vix == 1.0
        assert pos.m_gex == 1.0
        assert pos.m_contradiction == 1.0
        assert pos.m_flow == 1.0
        assert pos.multiplier_total == pos.m_target == 1.0

    def test_zero_atr_returns_none(self, config):
        stock = _make_stock("AAPL", atr=0.0)
        gex = _make_gex("AAPL")
        assert _calculate_swing_position(
            stock, gex, config, StrategyMode.LONG,
        ) is None

    def test_below_min_notional_returns_none(self, config):
        # Force the min_notional floor by raising it past computed notional
        config.tuning["swing_min_notional"] = 100_000
        stock = _make_stock("AAPL", price=150.0, atr=3.0)
        gex = _make_gex("AAPL")
        assert _calculate_swing_position(
            stock, gex, config, StrategyMode.LONG,
        ) is None


# ============================================================================
# _select_swing_entries
# ============================================================================


class TestSelectSwingEntries:
    def test_respects_max_daily_new(self, config, logger):
        """5 ranked candidates, max_daily_new=3 → only 3 selected."""
        candidates = [
            (_make_stock(f"T{i}", sector=f"S{i}", combined_score=90 - i, price=50.0, atr=1.0),
             _make_gex(f"T{i}"))
            for i in range(5)
        ]
        selected, counts = _select_swing_entries(
            candidates, open_positions=[], config=config,
            strategy_mode=StrategyMode.LONG, logger=logger,
        )
        assert len(selected) == 3
        assert [p.ticker for p in selected] == ["T0", "T1", "T2"]
        assert counts["daily_cap"] == 2

    def test_respects_max_concurrent_cap(self, config, logger):
        """open=10, max_daily_new=3, max_concurrent=12 → only 2 new fit."""
        open_positions = [
            PositionSizing(
                ticker=f"O{i}", sector=f"OS{i}", direction="BUY",
                entry_price=100.0, quantity=10,
                stop_loss=98.0, take_profit_1=102.0, take_profit_2=104.0,
                risk_usd=20.0, combined_score=70.0, gex_regime="positive",
                multiplier_total=1.0,
            )
            for i in range(10)
        ]
        candidates = [
            (_make_stock(f"N{i}", sector=f"NS{i}", combined_score=90 - i, price=50.0, atr=1.0),
             _make_gex(f"N{i}"))
            for i in range(5)
        ]
        selected, _ = _select_swing_entries(
            candidates, open_positions=open_positions, config=config,
            strategy_mode=StrategyMode.LONG, logger=logger,
        )
        assert len(selected) == 2  # 12 cap - 10 open = 2 headroom (< daily_new=3)

    def test_zero_new_when_at_concurrent_cap(self, config, logger):
        """open=12 → 0 daily new entry."""
        open_positions = [
            PositionSizing(
                ticker=f"O{i}", sector=f"S{i}", direction="BUY",
                entry_price=100.0, quantity=10,
                stop_loss=98.0, take_profit_1=102.0, take_profit_2=104.0,
                risk_usd=20.0, combined_score=70.0, gex_regime="positive",
                multiplier_total=1.0,
            )
            for i in range(12)
        ]
        candidates = [
            (_make_stock("N1", combined_score=99.0), _make_gex("N1")),
        ]
        selected, counts = _select_swing_entries(
            candidates, open_positions=open_positions, config=config,
            strategy_mode=StrategyMode.LONG, logger=logger,
        )
        assert selected == []
        assert counts["concurrent_cap"] == 1

    def test_sector_cap_blocks_third_tech(self, config, logger):
        """Three TECH tickers, each ~$8,700 notional, sector cap 30% of $100k = $30k.
        Greedy fill: ticker 1 + 2 = $17,400 (under cap). Ticker 3 would push
        to $26,100 (still under). So at $30k cap with 3 ticks at ~$8,700 each
        all 3 fit. Use a slightly higher equity-scaled ATR pattern that lets
        2 fit but blocks the 3rd."""
        # Force: 4 high-priced tickers, each notional ~$20k → 2 fit (40k > 30k cap on 3rd)
        # Use entry=200, atr=1.5 → ATR_pct=0.0075 → notional=350/(0.0075*2)=$23,333
        config.tuning["swing_max_daily_new"] = 5
        candidates = [
            (_make_stock(f"T{i}", sector="Technology", combined_score=90 - i,
                         price=200.0, atr=1.5),
             _make_gex(f"T{i}"))
            for i in range(4)
        ]
        selected, counts = _select_swing_entries(
            candidates, open_positions=[], config=config,
            strategy_mode=StrategyMode.LONG, logger=logger,
        )
        # Each notional capped to max_single_ticker_exposure=$15k (15000/200=75 shares),
        # so per-position notional = 75*200 = $15,000.
        # Sector cap 30% × $100k = $30k → exactly 2 fit.
        assert len(selected) == 2
        assert counts["sector_cap"] == 2

    def test_sector_balanced_greedy_picks_lower_score_other_sector(self, config, logger):
        """High-S tech tickers fill sector cap → next-ranked OTHER sector picked even with lower score."""
        config.tuning["swing_max_daily_new"] = 4
        candidates = [
            # Tech tickers (high score) — will fill tech sector cap quickly
            (_make_stock("T1", sector="Technology", combined_score=95,
                         price=200.0, atr=1.5), _make_gex("T1")),
            (_make_stock("T2", sector="Technology", combined_score=92,
                         price=200.0, atr=1.5), _make_gex("T2")),
            (_make_stock("T3", sector="Technology", combined_score=88,
                         price=200.0, atr=1.5), _make_gex("T3")),
            # Lower-score healthcare → should still get picked when tech is capped
            (_make_stock("H1", sector="Healthcare", combined_score=70,
                         price=200.0, atr=1.5), _make_gex("H1")),
        ]
        selected, _ = _select_swing_entries(
            candidates, open_positions=[], config=config,
            strategy_mode=StrategyMode.LONG, logger=logger,
        )
        tickers = [p.ticker for p in selected]
        # T1 + T2 fit in Tech ($15k each, total $30k = cap), T3 blocked, H1 fits
        assert "T1" in tickers and "T2" in tickers
        assert "T3" not in tickers
        assert "H1" in tickers

    def test_zero_new_when_no_qualified(self, config, logger):
        """No candidates → empty selection."""
        selected, counts = _select_swing_entries(
            [], open_positions=[], config=config,
            strategy_mode=StrategyMode.LONG, logger=logger,
        )
        assert selected == []
        assert all(v == 0 for v in counts.values())

    def test_sector_notional_accounts_for_open_positions(self, config, logger):
        """An existing $20k Tech open position → new Tech entry can only add $10k more."""
        open_positions = [
            PositionSizing(
                ticker="OLD", sector="Technology", direction="BUY",
                entry_price=200.0, quantity=100,  # $20k notional
                stop_loss=196.0, take_profit_1=204.0, take_profit_2=208.0,
                risk_usd=40.0, combined_score=80.0, gex_regime="positive",
                multiplier_total=1.0,
            ),
        ]
        # Candidate: $15k tech (would push sector to $35k > $30k cap) → blocked
        candidates = [
            (_make_stock("NEW", sector="Technology", combined_score=90,
                         price=200.0, atr=1.5), _make_gex("NEW")),
        ]
        selected, counts = _select_swing_entries(
            candidates, open_positions=open_positions, config=config,
            strategy_mode=StrategyMode.LONG, logger=logger,
        )
        assert selected == []
        assert counts["sector_cap"] == 1


# ============================================================================
# run_phase6 integration
# ============================================================================


class TestPhase6SwingIntegration:
    def test_m_vix_disabled_no_size_effect(self, config, logger):
        """VIX 30 produces the SAME notional as VIX 15 (M_VIX forced to 1.0)."""
        stocks = [_make_stock("AAPL", combined_score=90, price=150.0, atr=3.0)]
        gex = [_make_gex("AAPL")]

        macro_low = MacroRegime(
            vix_value=15.0, vix_regime=MarketVolatilityRegime.LOW,
            vix_multiplier=1.0, tnx_value=4.2, tnx_sma20=4.1,
            tnx_rate_sensitive=False,
        )
        macro_high = MacroRegime(
            vix_value=30.0, vix_regime=MarketVolatilityRegime.ELEVATED,
            vix_multiplier=0.50,
            tnx_value=4.2, tnx_sma20=4.1, tnx_rate_sensitive=False,
        )

        res_low = run_phase6(config, logger, stocks, gex, macro_low, StrategyMode.LONG)
        res_high = run_phase6(config, logger, stocks, gex, macro_high, StrategyMode.LONG)
        assert res_low.positions[0].quantity == res_high.positions[0].quantity
        assert res_low.positions[0].m_vix == 1.0
        assert res_high.positions[0].m_vix == 1.0

    def test_end_to_end_swing_path(self, config, logger, macro):
        """End-to-end: scored candidates → sector-balanced greedy → Phase6Result.

        4 candidates across 3 sectors with mixed scores. Verifies:
        - Swing path used (M_VIX/M_GEX/M_contradiction = 1.0 in output)
        - Ranking respected
        - Sector cap enforced
        - Phase6Result populated correctly
        """
        config.tuning["swing_max_daily_new"] = 4
        stocks = [
            _make_stock("AAA", sector="Technology", combined_score=95,
                        price=200.0, atr=1.5),
            _make_stock("BBB", sector="Technology", combined_score=92,
                        price=200.0, atr=1.5),
            _make_stock("CCC", sector="Technology", combined_score=88,
                        price=200.0, atr=1.5),  # blocked: sector cap
            _make_stock("DDD", sector="Healthcare", combined_score=85,
                        price=150.0, atr=3.0),
        ]
        gex = [_make_gex(s.ticker, price=s.technical.price) for s in stocks]

        result = run_phase6(config, logger, stocks, gex, macro, StrategyMode.LONG)

        assert isinstance(result, Phase6Result)
        tickers = [p.ticker for p in result.positions]
        # AAA + BBB fit in Tech (2 × $15k = $30k cap), CCC blocked, DDD fits
        assert "AAA" in tickers and "BBB" in tickers
        assert "CCC" not in tickers
        assert "DDD" in tickers
        assert result.excluded_sector_limit == 1
        # Each sized position should reflect the swing multiplier chain
        for pos in result.positions:
            assert pos.m_vix == 1.0
            assert pos.m_gex == 1.0
            assert pos.m_contradiction == 1.0
            assert pos.multiplier_total == pos.m_target
        assert result.total_risk_usd > 0
        assert result.total_exposure_usd > 0
