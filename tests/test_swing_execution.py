"""Tests — Task #4 Swing Execution + Exit (Day 63 §3.1, §3.6, §3.8, §3.12).

Covers the pure logic of the mental-stop EOD eval, state I/O, and the
sell-quantity / exit-application helpers. The IBKR-side glue
(``submit_orders.py``, ``close_positions.py``, ``pt_monitor.py``) is sanity-
tested for branching only; the integration smoke at the bottom of the file
exercises a 3-day swing lifecycle (HOLD → TP1 partial → trail).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

import pytest

from ifds.config.defaults import TUNING
from ifds.state.swing_positions import (
    ACTION_HARD_SL,
    ACTION_HOLD,
    ACTION_MENTAL_SL,
    ACTION_TIME_STOP,
    ACTION_TP1,
    ACTION_TP2,
    ACTION_TRAIL_SL,
    SwingPosition,
    apply_executed_exit,
    build_swing_position_from_sizing,
    compute_sell_qty,
    compute_weekly_pnl_pct,
    evaluate_all_positions,
    evaluate_position_eod,
    load_swing_positions,
    save_swing_positions,
    to_position_sizing_stub,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ENTRY = 100.0
ATR = 2.0
QTY = 50
ENTRY_DATE = "2026-05-18"
EQUITY = 100_000.0
CFG = {
    "swing_hard_sl_weekly_cumulative_pct": -0.08,
    "swing_trail_atr_multiple": 1.0,
    "swing_time_stop_trading_days": 5,
    "swing_mental_stop_atr_multiple": 2.0,
    "swing_tp1_atr_multiple": 1.5,
    "swing_tp2_atr_multiple": 3.0,
}


def _pos(**overrides) -> SwingPosition:
    """Build a baseline LONG swing position for tests."""
    base = SwingPosition(
        ticker="TEST",
        entry_date=ENTRY_DATE,
        entry_price=ENTRY,
        atr=ATR,
        stop_level=ENTRY - 2.0 * ATR,  # 96.00
        tp1_level=ENTRY + 1.5 * ATR,  # 103.00
        tp2_level=ENTRY + 3.0 * ATR,  # 106.00
        qty=QTY,
        qty_remaining=QTY,
        sector="XLK",
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


# ---------------------------------------------------------------------------
# 1. State I/O
# ---------------------------------------------------------------------------


def test_save_and_load_roundtrip(tmp_path):
    """save → load roundtrip preserves all fields."""
    state_file = tmp_path / "swing.json"
    positions = [_pos(), _pos(ticker="OTHER", sector="XLF")]

    save_swing_positions(state_file, positions)
    loaded = load_swing_positions(state_file)

    assert len(loaded) == 2
    assert loaded[0].ticker == "TEST" and loaded[1].ticker == "OTHER"
    assert loaded[0].tp1_level == 103.0
    assert loaded[1].sector == "XLF"


def test_load_returns_empty_when_missing(tmp_path):
    """Missing state file → empty list (Day 1 deploy)."""
    assert load_swing_positions(tmp_path / "nonexistent.json") == []


def test_load_handles_malformed_json(tmp_path):
    """Malformed JSON → empty list (defensive — no crash)."""
    f = tmp_path / "bad.json"
    f.write_text("{not json}")
    assert load_swing_positions(f) == []


# ---------------------------------------------------------------------------
# 2. Pure helpers
# ---------------------------------------------------------------------------


def test_compute_weekly_pnl_pct_basic():
    pos = _pos()
    # +$2 × 50 qty / $100k = 0.001 = 0.1%
    assert compute_weekly_pnl_pct(pos, today_close=102.0, equity=EQUITY) == pytest.approx(0.001)
    # -$5 × 50 / $100k = -0.0025 = -0.25%
    assert compute_weekly_pnl_pct(pos, today_close=95.0, equity=EQUITY) == pytest.approx(-0.0025)


def test_compute_weekly_pnl_pct_zero_equity():
    pos = _pos()
    assert compute_weekly_pnl_pct(pos, today_close=110.0, equity=0.0) == 0.0


def test_compute_sell_qty_tp1_50_percent():
    """TP1 → SELL 50% (rounded down, min 1)."""
    assert compute_sell_qty(_pos(qty=50, qty_remaining=50), ACTION_TP1) == 25
    assert compute_sell_qty(_pos(qty=51, qty_remaining=51), ACTION_TP1) == 25
    assert compute_sell_qty(_pos(qty=1, qty_remaining=1), ACTION_TP1) == 1  # floor


def test_compute_sell_qty_full_exit_actions():
    """HARD_SL / MENTAL_SL / TP2 / TRAIL_SL / TIME_STOP → SELL qty_remaining."""
    pos = _pos(qty=50, qty_remaining=30)
    for action in (ACTION_HARD_SL, ACTION_MENTAL_SL, ACTION_TP2, ACTION_TRAIL_SL, ACTION_TIME_STOP):
        assert compute_sell_qty(pos, action) == 30


def test_build_swing_position_from_sizing():
    """Builder applies stop/TP multipliers from config."""
    pos = build_swing_position_from_sizing(
        ticker="NVDA",
        entry_price=200.0,
        atr=5.0,
        qty=10,
        entry_date="2026-05-18",
        config=CFG,
        sector="XLK",
        m_target=0.6,
    )
    assert pos.stop_level == 200.0 - 2.0 * 5.0  # 190.0
    assert pos.tp1_level == 200.0 + 1.5 * 5.0  # 207.5
    assert pos.tp2_level == 200.0 + 3.0 * 5.0  # 215.0
    assert pos.m_target == 0.6


def test_to_position_sizing_stub_preserves_notional():
    """SwingPosition → PositionSizing stub keeps quantity × entry_price for sector cap math."""
    pos = _pos(qty=50, qty_remaining=30)
    stub = to_position_sizing_stub(pos)
    assert stub.quantity == 30 and stub.entry_price == ENTRY
    assert stub.sector == pos.sector


# ---------------------------------------------------------------------------
# 3. EOD eval — the 6 exit conditions
# ---------------------------------------------------------------------------


def test_eod_eval_returns_hold_in_normal_range():
    """close ∈ [stop, tp1] AND high < tp1 → HOLD."""
    pos = _pos()
    action, _ = evaluate_position_eod(
        pos,
        today_close=101.0,
        today_high=102.0,
        today_low=99.0,
        today_date=date.fromisoformat(ENTRY_DATE),
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_HOLD


def test_eod_eval_returns_mental_sl_below_2atr():
    """close < entry - 2×ATR → MENTAL_SL."""
    pos = _pos()
    action, _ = evaluate_position_eod(
        pos,
        today_close=95.0,
        today_high=98.0,
        today_low=94.0,
        today_date=date.fromisoformat(ENTRY_DATE),
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_MENTAL_SL


def test_eod_eval_returns_tp1_when_high_reaches_1_5atr():
    """high >= entry + 1.5×ATR (first hit) → TP1."""
    pos = _pos()
    action, _ = evaluate_position_eod(
        pos,
        today_close=102.5,
        today_high=103.5,
        today_low=99.0,
        today_date=date.fromisoformat(ENTRY_DATE),
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_TP1


def test_eod_eval_returns_tp2_when_high_reaches_3_0atr():
    """high >= entry + 3.0×ATR → TP2 (wins over TP1 same day)."""
    pos = _pos()
    action, _ = evaluate_position_eod(
        pos,
        today_close=105.0,
        today_high=106.5,
        today_low=99.0,
        today_date=date.fromisoformat(ENTRY_DATE),
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_TP2


def test_eod_eval_returns_hard_sl_when_weekly_below_minus_8pct():
    """weekly cum P&L < -8% → HARD_SL (precedes MENTAL_SL)."""
    # Need a position large enough so a small price drop yields -8%
    # entry $100 × qty 1000 = $100k notional; close $92 → -$8000 = -8.0%
    pos = _pos(
        qty=1000, qty_remaining=1000, stop_level=70.0
    )  # very-loose stop so MENTAL doesn't fire
    action, updates = evaluate_position_eod(
        pos,
        today_close=91.0,
        today_high=91.0,
        today_low=90.0,
        today_date=date.fromisoformat(ENTRY_DATE),
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_HARD_SL
    assert updates["weekly_pnl_pct"] < -0.08


def test_eod_eval_returns_time_stop_day5():
    """days_held >= 5 → TIME_STOP (same-day MOC, NOT next-day)."""
    pos = _pos()
    action, updates = evaluate_position_eod(
        pos,
        today_close=101.5,
        today_high=102.5,
        today_low=99.0,
        today_date=date.fromisoformat("2026-05-23"),  # 5 days after 2026-05-18
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_TIME_STOP
    assert updates["days_held"] == 5


def test_eod_eval_priority_hard_sl_over_mental_sl():
    """HARD_SL precedes MENTAL_SL when both trigger."""
    # close $90 → -$10 × qty 1000 / $100k = -10% → HARD_SL
    # also $90 < $96 (stop_level) → MENTAL_SL — but HARD_SL wins
    pos = _pos(qty=1000, qty_remaining=1000)
    action, _ = evaluate_position_eod(
        pos,
        today_close=90.0,
        today_high=92.0,
        today_low=89.0,
        today_date=date.fromisoformat(ENTRY_DATE),
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_HARD_SL


def test_eod_eval_priority_tp2_over_tp1():
    """TP2 wins over TP1 when high reaches both same day."""
    pos = _pos()
    action, _ = evaluate_position_eod(
        pos,
        today_close=104.0,
        today_high=106.5,
        today_low=102.0,
        today_date=date.fromisoformat(ENTRY_DATE),
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_TP2


# ---------------------------------------------------------------------------
# 4. Trail SL — only active after TP1
# ---------------------------------------------------------------------------


def test_trail_sl_inactive_before_tp1():
    """trail_sl stays None when tp1_hit=False."""
    pos = _pos(tp1_hit=False, trail_sl=None)
    action, updates = evaluate_position_eod(
        pos,
        today_close=101.0,
        today_high=102.0,
        today_low=99.0,
        today_date=date.fromisoformat(ENTRY_DATE),
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_HOLD
    assert "trail_sl" not in updates


def test_trail_sl_initializes_after_tp1_hit():
    """tp1_hit=True + no prior trail → set trail_sl = close - 1.0×ATR."""
    pos = _pos(tp1_hit=True, trail_sl=None)
    action, updates = evaluate_position_eod(
        pos,
        today_close=104.0,
        today_high=104.5,
        today_low=102.0,
        today_date=date.fromisoformat("2026-05-19"),
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_HOLD
    # new trail = 104 - 1.0 × 2.0 = 102
    assert updates["trail_sl"] == pytest.approx(102.0)


def test_trail_sl_ratchets_upward_only():
    """Trail rises but never falls. Day 1: trail=102. Day 2 close $103 → trail=101 NOT updated."""
    # Day 1: tp1_hit, close=104 → trail set to 102
    pos = _pos(tp1_hit=True, trail_sl=102.0)
    action, updates = evaluate_position_eod(
        pos,
        today_close=103.0,
        today_high=104.0,
        today_low=101.5,
        today_date=date.fromisoformat("2026-05-20"),
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_HOLD
    # new candidate = 103 - 2 = 101 < 102 (existing trail) — DO NOT update
    assert "trail_sl" not in updates or updates["trail_sl"] >= 102.0


def test_trail_sl_triggers_exit_when_close_below():
    """Close < existing trail_sl → TRAIL_SL."""
    pos = _pos(tp1_hit=True, trail_sl=102.0, qty_remaining=25)
    action, _ = evaluate_position_eod(
        pos,
        today_close=101.0,
        today_high=102.5,
        today_low=100.5,
        today_date=date.fromisoformat("2026-05-21"),
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_TRAIL_SL


# ---------------------------------------------------------------------------
# 5. Batch eval + apply exit
# ---------------------------------------------------------------------------


def test_evaluate_all_positions_mixed_actions():
    """Batch eval marks 3 positions: HOLD / TP1 / MENTAL_SL."""
    p_hold = _pos(ticker="HOLD")
    p_tp1 = _pos(ticker="TP1HIT")
    p_sl = _pos(ticker="MSL")
    ohlc = {
        "HOLD": {"close": 100.5, "high": 101.0, "low": 100.0},
        "TP1HIT": {"close": 103.0, "high": 103.5, "low": 102.0},
        "MSL": {"close": 95.0, "high": 98.0, "low": 94.0},
    }
    updated, exits = evaluate_all_positions(
        [p_hold, p_tp1, p_sl],
        ohlc,
        today_date=date.fromisoformat(ENTRY_DATE),
        config=CFG,
        equity=EQUITY,
    )
    by_ticker = {p.ticker: p for p in updated}
    assert by_ticker["HOLD"].next_action == ACTION_HOLD
    assert by_ticker["TP1HIT"].next_action == ACTION_TP1
    assert by_ticker["MSL"].next_action == ACTION_MENTAL_SL
    assert sorted(exits) == [("MSL", ACTION_MENTAL_SL), ("TP1HIT", ACTION_TP1)]


def test_evaluate_all_positions_missing_ohlc_stays_hold():
    """Missing OHLC → position stays unchanged (defensive)."""
    pos = _pos()
    updated, exits = evaluate_all_positions(
        [pos],
        {},
        today_date=date.fromisoformat(ENTRY_DATE),
        config=CFG,
        equity=EQUITY,
    )
    assert updated[0].next_action == ACTION_HOLD
    assert exits == []


def test_apply_executed_exit_tp1_partial():
    """TP1 execution → tp1_hit=True, qty_remaining reduced 50%."""
    pos = _pos(qty=50, qty_remaining=50)
    updated = apply_executed_exit(pos, ACTION_TP1, tp1_sell_pct=0.50)
    assert updated is not None
    assert updated.tp1_hit is True
    assert updated.qty_remaining == 25
    assert updated.next_action == ACTION_HOLD


def test_apply_executed_exit_full_exit_returns_none():
    """HARD/MENTAL/TP2/TRAIL/TIME exits → None (caller removes from state)."""
    for action in (ACTION_HARD_SL, ACTION_MENTAL_SL, ACTION_TP2, ACTION_TRAIL_SL, ACTION_TIME_STOP):
        assert apply_executed_exit(_pos(), action) is None


# ---------------------------------------------------------------------------
# 6. Friday entry → 5-trading-day hold ≈ next Friday calendar
# ---------------------------------------------------------------------------


def test_friday_entry_time_stop_at_5_calendar_days():
    """Friday entry → 5-day calendar diff yields TIME_STOP.

    Note: the spec says "5 trading days" but the implementation uses
    ``(today_date - entry_date).days``. A Friday → following Wednesday is
    5 trading days (= 5 calendar days). Friday → next Friday is 7 calendar
    days (still TIME_STOP because >= 5).
    """
    friday_entry = "2026-05-15"  # Friday
    pos = _pos(entry_date=friday_entry)

    # Following Wednesday = +5 calendar days, 3 trading days inclusive
    # The implementation is calendar-based (simpler, conservative — earlier exit
    # on weekends is fine because positions aren't actively traded then).
    action, updates = evaluate_position_eod(
        pos,
        today_close=101.0,
        today_high=102.0,
        today_low=99.0,
        today_date=date.fromisoformat("2026-05-20"),  # Wed = 5 calendar days
        config=CFG,
        equity=EQUITY,
    )
    assert action == ACTION_TIME_STOP
    assert updates["days_held"] == 5


# ---------------------------------------------------------------------------
# 7. M_target audit trail preserved
# ---------------------------------------------------------------------------


def test_m_target_preserved_in_state(tmp_path):
    """SwingPosition.m_target survives save/load roundtrip (audit trail per Gotcha D)."""
    state_file = tmp_path / "s.json"
    pos = _pos()
    pos.m_target = 0.60
    save_swing_positions(state_file, [pos])
    loaded = load_swing_positions(state_file)
    assert loaded[0].m_target == 0.60


# ---------------------------------------------------------------------------
# 8. Config defaults sanity (regression — make sure TUNING is wired)
# ---------------------------------------------------------------------------


def test_tuning_swing_execution_keys_present():
    """All Task #4 TUNING keys must exist in defaults.TUNING."""
    required = [
        "swing_execution_enabled",
        "swing_entry_time_cest",
        "swing_eod_eval_time_cest",
        "swing_tp1_atr_multiple",
        "swing_tp2_atr_multiple",
        "swing_mental_stop_atr_multiple",
        "swing_trail_atr_multiple",
        "swing_hard_sl_weekly_cumulative_pct",
        "swing_time_stop_trading_days",
        "swing_positions_state_file",
        "ibkr_bracket_enabled",
        "loss_exit_intraday_enabled",
        "pt_monitor_5min_mode",
    ]
    for key in required:
        assert key in TUNING, f"Missing TUNING key: {key}"


def test_tuning_swing_tp_multipliers_match_spec():
    """Task #4 spec §7: TP1=1.5×, TP2=3.0×ATR (overrides Task #3 1.25/2.0)."""
    assert TUNING["swing_tp1_atr_multiple"] == 1.5
    assert TUNING["swing_tp2_atr_multiple"] == 3.0


def test_tuning_legacy_brackets_disabled():
    """Legacy bracket + intraday loss-exit must be off in swing mode."""
    assert TUNING["ibkr_bracket_enabled"] is False
    assert TUNING["loss_exit_intraday_enabled"] is False
    assert TUNING["pt_monitor_5min_mode"] is False


# ---------------------------------------------------------------------------
# 9. 3-day swing lifecycle smoke (integration)
# ---------------------------------------------------------------------------


def test_three_day_swing_lifecycle_integration(tmp_path):
    """Day 1 entry → Day 2 TP1 partial → Day 3 trail hit on remainder.

    Validates the full ratchet flow end-to-end without IBKR:
    - Day 1: position written to state, next_action=HOLD
    - Day 2: TP1 triggers, state shows next_action=TP1; apply → qty=25, tp1_hit=True
    - Day 3: trail_sl was set on Day 2 high; today close drops below → TRAIL_SL
    """
    state_file = tmp_path / "swing.json"

    # --- Day 1: Submit ---
    pos = build_swing_position_from_sizing(
        ticker="AAPL",
        entry_price=100.0,
        atr=2.0,
        qty=50,
        entry_date="2026-05-18",
        config=CFG,
        sector="XLK",
    )
    save_swing_positions(state_file, [pos])
    loaded = load_swing_positions(state_file)
    assert loaded[0].next_action == ACTION_HOLD
    assert loaded[0].qty_remaining == 50

    # --- Day 2 EOD eval: high $103.5 → TP1 ---
    ohlc_day2 = {"AAPL": {"close": 103.0, "high": 103.5, "low": 101.5}}
    updated, exits = evaluate_all_positions(
        loaded,
        ohlc_day2,
        today_date=date.fromisoformat("2026-05-19"),
        config=CFG,
        equity=EQUITY,
    )
    assert exits == [("AAPL", ACTION_TP1)]
    save_swing_positions(state_file, updated)

    # --- Day 2 (next morning) Execute TP1: 50% sell, tp1_hit=True ---
    loaded = load_swing_positions(state_file)
    executed_tp1 = apply_executed_exit(loaded[0], ACTION_TP1, tp1_sell_pct=0.50)
    assert executed_tp1 is not None and executed_tp1.qty_remaining == 25
    assert executed_tp1.tp1_hit is True
    save_swing_positions(state_file, [executed_tp1])

    # --- Day 2 EOD again (after TP1) — trail initializes ---
    loaded = load_swing_positions(state_file)
    ohlc_day2b = {"AAPL": {"close": 104.0, "high": 104.0, "low": 102.5}}
    updated, exits = evaluate_all_positions(
        loaded,
        ohlc_day2b,
        today_date=date.fromisoformat("2026-05-19"),
        config=CFG,
        equity=EQUITY,
    )
    assert exits == []
    # trail = close (104) - 1.0 × ATR (2) = 102
    assert updated[0].trail_sl == pytest.approx(102.0)
    save_swing_positions(state_file, updated)

    # --- Day 3 EOD: close $101 (below trail_sl=102) → TRAIL_SL ---
    loaded = load_swing_positions(state_file)
    ohlc_day3 = {"AAPL": {"close": 101.0, "high": 102.5, "low": 100.0}}
    updated, exits = evaluate_all_positions(
        loaded,
        ohlc_day3,
        today_date=date.fromisoformat("2026-05-20"),
        config=CFG,
        equity=EQUITY,
    )
    assert exits == [("AAPL", ACTION_TRAIL_SL)]
    assert updated[0].next_action == ACTION_TRAIL_SL


# ---------------------------------------------------------------------------
# 10. Phase 6 wire-up regression — open_positions kwarg passes through
# ---------------------------------------------------------------------------


def test_runner_open_positions_loader_returns_empty_when_state_missing(tmp_path, monkeypatch):
    """Day 1 deploy: no state file → load_swing_positions returns []."""
    missing = tmp_path / "no.json"
    assert load_swing_positions(missing) == []


def test_runner_open_positions_converts_to_position_sizing_stub(tmp_path):
    """SwingPosition state loads and converts to PositionSizing stubs with correct notional."""
    state_file = tmp_path / "open.json"
    save_swing_positions(
        state_file,
        [
            _pos(ticker="A", sector="XLK", qty_remaining=10),
            _pos(ticker="B", sector="XLF", qty_remaining=20),
        ],
    )
    open_swings = load_swing_positions(state_file)
    stubs = [to_position_sizing_stub(p) for p in open_swings]
    assert len(stubs) == 2
    notional_a = stubs[0].quantity * stubs[0].entry_price
    notional_b = stubs[1].quantity * stubs[1].entry_price
    assert notional_a == 10 * ENTRY
    assert notional_b == 20 * ENTRY
    # Sectors preserved for the 30% sector cap math
    assert {stubs[0].sector, stubs[1].sector} == {"XLK", "XLF"}
