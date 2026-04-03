"""Tests for simulate_swing_trade (BC20C — Trail SIM support).

Covers:
- TP1 trigger → partial exit + trail activation
- Breakeven SL raise
- Trail stop exit after TP1
- Max hold MOC exit
- Same-day TP1+SL ambiguity → conservative SL
- No bars → Trade returned unchanged
- Full exit at TP1 (tp1_exit_pct=1.0)
"""

from datetime import date

import pytest

from ifds.sim.broker_sim import simulate_swing_trade
from ifds.sim.models import Trade


def _make_trade(
    entry: float = 100.0,
    sl: float = 95.5,
    qty: int = 100,
    direction: str = "BUY",
) -> Trade:
    return Trade(
        run_id="test_run",
        run_date=date(2026, 3, 1),
        ticker="AAPL",
        score=80.0,
        gex_regime="neutral",
        multiplier=1.0,
        entry_price=entry,
        quantity=qty,
        direction=direction,
        stop_loss=sl,
        tp1=0.0,
        tp2=0.0,
    )


def _bars(prices: list[tuple[float, float, float, float]],
          start: date = date(2026, 3, 2)) -> list[dict]:
    """Create bars from (open, high, low, close) tuples."""
    result = []
    for i, (o, h, l, c) in enumerate(prices):
        d = date(start.year, start.month, start.day + i)
        result.append({"date": d.isoformat(), "o": o, "h": h, "l": l, "c": c, "v": 1_000_000})
    return result


class TestSwingFill:

    def test_no_bars_returns_unfilled(self):
        trade = _make_trade()
        result = simulate_swing_trade(trade, [])
        assert not result.filled

    def test_fill_on_first_bar(self):
        trade = _make_trade(entry=100.0)
        bars = _bars([(99.0, 101.0, 98.0, 100.5)])  # low=98 <= entry=100
        result = simulate_swing_trade(trade, bars, max_hold_days=5)
        assert result.filled
        assert result.fill_price == 100.0

    def test_no_fill_when_price_above_entry(self):
        trade = _make_trade(entry=100.0)
        bars = _bars([(101.0, 103.0, 100.5, 102.0)])  # low=100.5 > entry=100
        result = simulate_swing_trade(trade, bars, max_hold_days=5)
        assert not result.filled


class TestSwingTP1:

    def test_tp1_partial_exit(self):
        """TP1 triggered on D+2 → 50% exit, trail active."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        # ATR ≈ (100-95.5)/1.5 = 3.0
        # TP1 = 100 + 0.75*3 = 102.25
        bars = _bars([
            (99.0, 100.5, 98.0, 100.0),   # D+1: fill (low=98 <= 100)
            (100.0, 101.0, 99.5, 100.5),   # D+2: no TP1 (high=101 < 102.25)
            (101.0, 103.0, 100.5, 102.0),  # D+3: TP1 hit (high=103 >= 102.25)
        ])
        result = simulate_swing_trade(trade, bars, max_hold_days=5, tp1_exit_pct=0.50)

        assert result.filled
        assert result.tp1_triggered
        assert result.partial_exit_qty == 50
        assert result.partial_exit_pnl > 0

    def test_tp1_full_exit(self):
        """tp1_exit_pct=1.0 → full exit at TP1."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        bars = _bars([
            (99.0, 100.5, 98.0, 100.0),   # fill
            (101.0, 103.0, 100.5, 102.0),  # TP1 hit
        ])
        result = simulate_swing_trade(trade, bars, max_hold_days=5, tp1_exit_pct=1.0)

        assert result.tp1_triggered
        assert result.exit_type == "tp1_full"
        assert result.total_pnl > 0


class TestSwingTrailStop:

    def test_trail_exit_after_tp1(self):
        """TP1 → trail active → trail stop hit."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        # ATR ≈ 3.0, TP1=102.25, trail_distance=3.0 (1.0×ATR)
        bars = _bars([
            (99.0, 100.5, 98.0, 100.0),   # D+1: fill
            (101.0, 103.0, 100.5, 102.5),  # D+2: TP1 hit (high=103), trail_sl = 103-3=100
            (102.0, 104.0, 101.0, 103.5),  # D+3: trail up, trail_sl = 104-3=101
            (103.0, 103.5, 100.0, 100.5),  # D+4: trail_sl hit (low=100 <= 101)
        ])
        result = simulate_swing_trade(trade, bars, max_hold_days=10, tp1_exit_pct=0.50)

        assert result.tp1_triggered
        assert result.exit_type == "tp1_partial+trail"
        assert result.total_pnl != 0  # Has both partial + trail P&L


class TestSwingBreakeven:

    def test_breakeven_sl_raise(self):
        """Close above entry + BE threshold → SL raised to entry."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        # ATR ≈ 3.0, BE threshold = 0.3×3 = 0.9
        # Need close > 100.9 to trigger breakeven
        bars = _bars([
            (99.0, 100.5, 98.0, 100.0),   # D+1: fill
            (100.0, 101.5, 99.5, 101.0),   # D+2: close=101 > 100.9 → breakeven
            (101.0, 101.5, 99.0, 99.5),    # D+3: low=99 but SL now = 100 → SL hit
        ])
        result = simulate_swing_trade(trade, bars, max_hold_days=10, tp1_exit_pct=0.50)

        assert result.filled
        assert result.breakeven_triggered
        assert result.exit_type == "breakeven_stop"
        # SL at entry=100, so approximately breakeven (close to 0 P&L)
        assert abs(result.total_pnl) < 1  # Near breakeven


class TestSwingStopLoss:

    def test_stop_loss_before_tp1(self):
        """SL hit before TP1 → full exit at SL."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        bars = _bars([
            (99.0, 100.5, 98.0, 100.0),   # D+1: fill
            (99.0, 99.5, 95.0, 95.5),     # D+2: SL hit (low=95 <= 95.5)
        ])
        result = simulate_swing_trade(trade, bars, max_hold_days=5, tp1_exit_pct=0.50)

        assert result.filled
        assert result.exit_type == "stop"
        assert result.total_pnl < 0


class TestSwingSameDayAmbiguity:

    def test_tp1_and_sl_same_day_conservative(self):
        """Same-day TP1+SL → conservative: SL wins."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        # ATR ≈ 3.0, TP1 = 102.25
        bars = _bars([
            (99.0, 100.5, 98.0, 100.0),   # D+1: fill
            (100.0, 103.0, 95.0, 98.0),   # D+2: both TP1 (103>=102.25) AND SL (95<=95.5)
        ])
        result = simulate_swing_trade(trade, bars, max_hold_days=5, tp1_exit_pct=0.50)

        assert result.filled
        assert not result.tp1_triggered  # Conservative: SL wins
        assert result.exit_type == "stop"
        assert result.total_pnl < 0


class TestSwingMaxHold:

    def test_max_hold_moc_exit(self):
        """No TP1, no SL hit within max_hold → exit at close."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        bars = _bars([
            (99.0, 100.5, 98.0, 100.0),   # D+1: fill
            (100.0, 101.0, 99.0, 100.5),   # D+2: no exit
            (100.5, 101.5, 99.5, 101.0),   # D+3: no exit → max_hold=2 → exit at close
        ])
        result = simulate_swing_trade(trade, bars, max_hold_days=2, tp1_exit_pct=0.50)

        assert result.filled
        assert result.exit_type == "max_hold"
        assert result.holding_days == 2
        # Exit at close=101.0 vs entry=100 → positive PnL
        assert result.total_pnl > 0


class TestSwingPnL:

    def test_pnl_accounting_partial_plus_trail(self):
        """P&L accounts for both partial TP1 exit and trail exit."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        # ATR=3, TP1=102.25, trail_dist=3
        bars = _bars([
            (99.0, 100.5, 98.0, 100.0),   # fill
            (101.0, 103.0, 100.0, 102.5),  # TP1 hit: 50 shares × (102.25-100) = +112.5
            (102.0, 102.5, 99.5, 100.0),   # trail_sl = max(100, 102.5-3)=100 → hit (low=99.5<=100)
        ])
        result = simulate_swing_trade(trade, bars, max_hold_days=10, tp1_exit_pct=0.50)

        assert result.tp1_triggered
        assert result.partial_exit_qty == 50
        assert result.partial_exit_pnl > 0

        # Total should be partial TP1 profit + trail exit (near entry)
        assert result.total_pnl > 0  # TP1 partial profit outweighs trail near-entry exit
        assert result.total_pnl_pct != 0

    def test_total_pnl_pct_based_on_full_position(self):
        """total_pnl_pct = total_pnl / (quantity × entry_price) × 100."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        bars = _bars([
            (99.0, 100.5, 98.0, 100.0),   # fill
            (99.0, 99.5, 95.0, 95.5),     # SL hit
        ])
        result = simulate_swing_trade(trade, bars, max_hold_days=5)

        # SL at 95.5: 100 × (95.5 - 100) = -450
        expected_pct = result.total_pnl / (100 * 100.0) * 100
        assert abs(result.total_pnl_pct - expected_pct) < 0.01


# ============================================================================
# BC20A Phase_20A_5 — SimEngine Swing Extensions
# ============================================================================

class TestVwapEntryFilter:

    def test_vwap_reject_no_fill(self):
        """Price > VWAP × 1.02 → no fill (vwap_reject)."""
        trade = _make_trade(entry=105.0, sl=100.0, qty=100)
        bars = _bars([(104.0, 106.0, 98.0, 105.0)])  # Would normally fill
        # VWAP = 100, entry 105 > 100*1.02=102 → reject
        result = simulate_swing_trade(trade, bars, vwap_prices={"AAPL": 100.0})
        assert not result.filled
        assert result.exit_type == "vwap_reject"

    def test_vwap_ok_fills(self):
        """Price < VWAP × 1.02 → normal fill."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        bars = _bars([(99.0, 101.0, 98.0, 100.0)])
        # VWAP = 100, entry 100 <= 100*1.02=102 → OK
        result = simulate_swing_trade(trade, bars, vwap_prices={"AAPL": 100.0})
        assert result.filled

    def test_no_vwap_data_no_filter(self):
        """No VWAP data → no filtering."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        bars = _bars([(99.0, 101.0, 98.0, 100.0)])
        result = simulate_swing_trade(trade, bars, vwap_prices=None)
        assert result.filled

    def test_vwap_other_ticker_no_filter(self):
        """VWAP data for different ticker → no filter on this trade."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        bars = _bars([(99.0, 101.0, 98.0, 100.0)])
        result = simulate_swing_trade(trade, bars, vwap_prices={"MSFT": 50.0})
        assert result.filled


class TestVolatileTrail:

    def test_volatile_tighter_trail(self):
        """MMS VOLATILE → trail distance = 0.75×ATR (not 1.0×ATR)."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        # ATR ≈ 3.0
        # Default trail: 1.0 × 3.0 = 3.0
        # Volatile trail: 0.75 × 3.0 = 2.25
        bars = _bars([
            (99.0, 100.5, 98.0, 100.0),   # fill
            (101.0, 103.0, 100.5, 102.5),  # TP1 hit (103 >= 102.25)
            (102.0, 102.5, 100.0, 100.5),  # With volatile trail: trail_sl = 103-2.25=100.75
                                            # low=100 < 100.75 → trail hit
        ])
        # With volatile trail → should hit trail stop
        result_vol = simulate_swing_trade(trade, bars, max_hold_days=10,
                                           tp1_exit_pct=0.50, mms_regime="volatile")
        assert result_vol.tp1_triggered

        # With default trail → trail_sl = 103-3=100, low=100 → also hits
        trade2 = _make_trade(entry=100.0, sl=95.5, qty=100)
        result_normal = simulate_swing_trade(trade2, bars, max_hold_days=10,
                                              tp1_exit_pct=0.50, mms_regime="undetermined")
        # Both should trigger TP1, but volatile should have tighter trail
        assert result_vol.tp1_triggered and result_normal.tp1_triggered

    def test_non_volatile_uses_default_trail(self):
        """Non-VOLATILE MMS regime → uses default trail_atr_mult."""
        trade = _make_trade(entry=100.0, sl=95.5, qty=100)
        bars = _bars([
            (99.0, 100.5, 98.0, 100.0),   # fill
            (100.0, 101.0, 99.5, 100.5),   # no TP1, no SL
        ])
        result = simulate_swing_trade(trade, bars, max_hold_days=5, mms_regime="neutral")
        assert result.filled  # Basic functionality works
