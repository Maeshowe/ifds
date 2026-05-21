"""Swing Position state — mental stop architecture (Task #4, Day 63 §3.1/3.6/3.8/3.12).

Source-of-truth for swing position exit levels. The IBKR side only holds the
open position; stop/TP1/TP2/trail are evaluated mental-only by ``pt_monitor.py``
at 22:00 CEST EOD, with next-day exits submitted by ``close_positions.py``
the following 15:30 CEST (and same-day 21:40 MOC for ``TIME_STOP``).

State file (default): ``state/swing_positions.json``.

The dataclass + load/save/eval helpers here are pure (no IBKR, no Telegram) so
they can be unit-tested in isolation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from ifds.utils.io import atomic_write_json

# ---------------------------------------------------------------------------
# Exit action enum (string-valued for JSON-friendliness)
# ---------------------------------------------------------------------------

# Possible values of ``SwingPosition.next_action`` produced by ``evaluate_position_eod``.
ACTION_HOLD = "HOLD"
ACTION_HARD_SL = "HARD_SL"  # next-day 15:30 MARKET SELL 100% (weekly cum < -8%)
ACTION_MENTAL_SL = "MENTAL_SL"  # next-day 15:30 MARKET SELL 100% (close < entry - 2*ATR)
ACTION_TP1 = "TP1"  # next-day 15:30 MARKET SELL 50% (high >= entry + 1.5*ATR)
ACTION_TP2 = "TP2"  # next-day 15:30 MARKET SELL remainder (high >= entry + 3.0*ATR)
ACTION_TRAIL_SL = "TRAIL_SL"  # next-day 15:30 MARKET SELL remainder (close < trail_sl)
ACTION_TIME_STOP = "TIME_STOP"  # SAME-day 21:40 MOC SELL remainder (days_held >= 5)

EOD_ACTIONS_NEXT_DAY = frozenset(
    {
        ACTION_HARD_SL,
        ACTION_MENTAL_SL,
        ACTION_TP1,
        ACTION_TP2,
        ACTION_TRAIL_SL,
    }
)
EOD_ACTIONS_SAME_DAY_MOC = frozenset({ACTION_TIME_STOP})


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class SwingPosition:
    """A single open swing position with mental stop/TP levels."""

    ticker: str
    entry_date: str  # ISO YYYY-MM-DD
    entry_price: float
    atr: float
    stop_level: float  # entry - 2.0 * ATR
    tp1_level: float  # entry + 1.5 * ATR
    tp2_level: float  # entry + 3.0 * ATR
    qty: int
    qty_remaining: int
    tp1_hit: bool = False
    trail_sl: float | None = None  # set after TP1 hit
    days_held: int = 0
    next_action: str = ACTION_HOLD
    next_action_at: str | None = None  # ISO datetime when next_action was set
    weekly_pnl_pct: float = 0.0
    sector: str = ""
    direction: str = "BUY"
    m_target: float = 1.0  # audit trail — Phase 6 captured at entry


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def load_swing_positions(state_file: str | Path) -> list[SwingPosition]:
    """Load swing positions from JSON state file.

    Returns an empty list if the file does not exist or is malformed.
    """
    path = Path(state_file)
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return [SwingPosition(**rec) for rec in data.get("positions", [])]
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


def save_swing_positions(
    state_file: str | Path,
    positions: list[SwingPosition],
) -> None:
    """Atomic write swing positions to JSON state file."""
    data = {
        "positions": [asdict(p) for p in positions],
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write_json(str(state_file), data)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def compute_weekly_pnl_pct(
    position: SwingPosition,
    today_close: float,
    equity: float,
) -> float:
    """Weekly cumulative unrealized P&L % relative to account equity.

    Dimensionless: ``(today_close - entry_price) * qty_remaining / equity``.
    Used for the HARD_SL gate (< -8% → trigger).
    """
    if equity <= 0:
        return 0.0
    unrealized = (today_close - position.entry_price) * position.qty_remaining
    return unrealized / equity


def compute_sell_qty(position: SwingPosition, action: str, tp1_sell_pct: float = 0.50) -> int:
    """Quantity to sell for a given EOD action.

    TP1: ``floor(qty * tp1_sell_pct)`` (at least 1). All other exits: ``qty_remaining``.
    """
    if action == ACTION_TP1:
        qty = int(position.qty * tp1_sell_pct)
        return max(1, qty)
    return position.qty_remaining


# ---------------------------------------------------------------------------
# Daily EOD eval — the core decision logic
# ---------------------------------------------------------------------------


def evaluate_position_eod(
    position: SwingPosition,
    today_close: float,
    today_high: float,
    today_low: float,
    today_date: date,
    config: dict[str, Any] | None = None,
    equity: float = 100_000.0,
) -> tuple[str, dict[str, Any]]:
    """Run the daily EOD eval for a single position.

    Parameters
    ----------
    position:
        The open ``SwingPosition`` (read-only — the caller applies returned updates).
    today_close, today_high, today_low:
        Today's OHLC values for the ticker.
    today_date:
        Reference date (used for ``days_held`` calculation).
    config:
        TUNING dict — recognized keys: ``swing_hard_sl_weekly_cumulative_pct``,
        ``swing_trail_atr_multiple``, ``swing_time_stop_trading_days``.
    equity:
        Account equity for weekly P&L calculation (default $100k).

    Returns
    -------
    tuple[str, dict[str, Any]]
        ``(action, state_updates)`` where ``action`` is one of:
          - ``HOLD``       — no exit triggered
          - ``HARD_SL``    — weekly cum P&L < -8% → next-day 15:30 100% SELL
          - ``MENTAL_SL``  — close < stop_level → next-day 15:30 100% SELL
          - ``TP1``        — high >= tp1_level (first hit) → next-day 15:30 50% SELL
          - ``TP2``        — high >= tp2_level → next-day 15:30 remainder SELL
          - ``TRAIL_SL``   — TP1 hit AND close < trail_sl → next-day 15:30 remainder
          - ``TIME_STOP``  — days_held >= 5 → SAME-day 21:40 MOC remainder

        Priority order (first match wins): HARD_SL → MENTAL_SL → TP2 → TP1
        → TRAIL_SL → TIME_STOP → HOLD.

        ``state_updates`` contains ``days_held``, ``weekly_pnl_pct``, and
        (when the trail ratchets upward) ``trail_sl``.
    """
    cfg = config or {}
    hard_sl_pct = cfg.get("swing_hard_sl_weekly_cumulative_pct", -0.08)
    trail_mult = cfg.get("swing_trail_atr_multiple", 1.0)
    time_stop_days = cfg.get("swing_time_stop_trading_days", 5)

    days_held = (today_date - date.fromisoformat(position.entry_date)).days
    weekly_pnl_pct = compute_weekly_pnl_pct(position, today_close, equity)

    updates: dict[str, Any] = {
        "days_held": days_held,
        "weekly_pnl_pct": weekly_pnl_pct,
    }

    # 1. Hard SL (weekly cumulative)
    if weekly_pnl_pct < hard_sl_pct:
        return ACTION_HARD_SL, updates

    # 2. Mental SL (today's close below stop_level)
    if today_close < position.stop_level:
        return ACTION_MENTAL_SL, updates

    # 3. TP2 (today's high reached TP2 — wins over TP1 in the same session)
    if today_high >= position.tp2_level:
        return ACTION_TP2, updates

    # 4. TP1 (today's high reached TP1, not yet partial-exited)
    if not position.tp1_hit and today_high >= position.tp1_level:
        return ACTION_TP1, updates

    # 5. Trail SL (only active AFTER tp1_hit)
    if position.tp1_hit:
        prev_trail = position.trail_sl
        new_candidate = today_close - trail_mult * position.atr
        # First check: did today's close trip the existing trail?
        if prev_trail is not None and today_close < prev_trail:
            return ACTION_TRAIL_SL, updates
        # Otherwise, ratchet upward (only)
        if prev_trail is None or new_candidate > prev_trail:
            updates["trail_sl"] = new_candidate

    # 6. Time stop (same-day 21:40 MOC)
    if days_held >= time_stop_days:
        return ACTION_TIME_STOP, updates

    return ACTION_HOLD, updates


def to_position_sizing_stub(position: SwingPosition) -> Any:
    """Convert a ``SwingPosition`` to a ``PositionSizing``-shaped stub.

    Phase 6's ``_select_swing_entries`` only reads ``ticker``, ``sector``,
    ``quantity``, ``entry_price``, and ``direction`` from the ``open_positions``
    list to compute current sector notionals. A minimal ``PositionSizing`` is
    sufficient for that math (the multipliers and contradiction flags are
    audit-trail fields that don't apply to already-open positions).

    Imported lazily inside callers to avoid pulling ``ifds.models.market``
    into this module's import graph.
    """
    from ifds.models.market import PositionSizing

    return PositionSizing(
        ticker=position.ticker,
        sector=position.sector,
        direction=position.direction,
        entry_price=position.entry_price,
        quantity=position.qty_remaining,
        stop_loss=position.stop_level,
        take_profit_1=position.tp1_level,
        take_profit_2=position.tp2_level,
        risk_usd=(position.entry_price - position.stop_level) * position.qty_remaining,
        combined_score=0.0,  # not used by sector-cap math
        gex_regime="",
        multiplier_total=1.0,
        m_target=position.m_target,
    )


def evaluate_all_positions(
    positions: list[SwingPosition],
    ohlc_map: dict[str, dict[str, float]],
    today_date: date,
    config: dict[str, Any] | None = None,
    equity: float = 100_000.0,
) -> tuple[list[SwingPosition], list[tuple[str, str]]]:
    """Run EOD eval for a batch of swing positions.

    Pure function (no IO). Returns updated copies of the positions plus a list
    of ``(ticker, action)`` tuples for the exits triggered today.

    Parameters
    ----------
    positions:
        Current open swing positions (from ``load_swing_positions``).
    ohlc_map:
        ``{ticker: {"close": float, "high": float, "low": float}}`` — today's
        daily bar per ticker. Missing tickers stay on HOLD (defensive).
    today_date:
        Reference date.
    config:
        TUNING dict.
    equity:
        Account equity for weekly P&L %.
    """
    cfg = config or {}
    eval_iso = datetime.now(timezone.utc).isoformat()
    updated: list[SwingPosition] = []
    exits: list[tuple[str, str]] = []

    for pos in positions:
        ohlc = ohlc_map.get(pos.ticker)
        if not ohlc:
            updated.append(pos)
            continue

        action, state_updates = evaluate_position_eod(
            pos,
            today_close=ohlc["close"],
            today_high=ohlc["high"],
            today_low=ohlc["low"],
            today_date=today_date,
            config=cfg,
            equity=equity,
        )

        new_pos = SwingPosition(**asdict(pos))
        for key, value in state_updates.items():
            setattr(new_pos, key, value)
        new_pos.next_action = action
        new_pos.next_action_at = eval_iso if action != ACTION_HOLD else None
        updated.append(new_pos)
        if action != ACTION_HOLD:
            exits.append((pos.ticker, action))

    return updated, exits


def apply_executed_exit(
    position: SwingPosition,
    action: str,
    tp1_sell_pct: float = 0.50,
) -> SwingPosition | None:
    """Apply an executed exit action to a position.

    Returns the updated position (TP1 partial → qty_remaining reduced, tp1_hit=True)
    or ``None`` when the position is fully closed (HARD_SL/MENTAL_SL/TP2/TRAIL_SL/TIME_STOP).
    """
    if action == ACTION_TP1:
        sold = compute_sell_qty(position, ACTION_TP1, tp1_sell_pct=tp1_sell_pct)
        new_pos = SwingPosition(**asdict(position))
        new_pos.qty_remaining = max(0, position.qty_remaining - sold)
        new_pos.tp1_hit = True
        new_pos.next_action = ACTION_HOLD
        new_pos.next_action_at = None
        return new_pos
    return None


def build_swing_position_from_sizing(
    ticker: str,
    entry_price: float,
    atr: float,
    qty: int,
    entry_date: str,
    config: dict[str, Any] | None = None,
    sector: str = "",
    direction: str = "BUY",
    m_target: float = 1.0,
) -> SwingPosition:
    """Construct a fresh ``SwingPosition`` from sizing output.

    Computes the mental stop/TP/TP2 levels from the swing TUNING multipliers.
    Used by ``submit_orders.py`` after the market BUY is placed.
    """
    cfg = config or {}
    stop_mult = cfg.get("swing_mental_stop_atr_multiple", 2.0)
    tp1_mult = cfg.get("swing_tp1_atr_multiple", 1.5)
    tp2_mult = cfg.get("swing_tp2_atr_multiple", 3.0)

    return SwingPosition(
        ticker=ticker,
        entry_date=entry_date,
        entry_price=entry_price,
        atr=atr,
        stop_level=entry_price - stop_mult * atr,
        tp1_level=entry_price + tp1_mult * atr,
        tp2_level=entry_price + tp2_mult * atr,
        qty=qty,
        qty_remaining=qty,
        sector=sector,
        direction=direction,
        m_target=m_target,
    )
