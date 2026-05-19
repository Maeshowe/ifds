"""Compact swing Telegram report formatters — Task #5 + Task #T §3.

Pure formatters for the swing pivot Telegram messages:

- ``format_swing_compact_telegram(metrics)`` — 22:05 EOD report (§3.4)
- ``format_pt_monitor_eod_telegram(positions, ohlc, exits, ...)`` — 22:00 pt_monitor (§3.3)
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable


def format_swing_compact_telegram(metrics: dict[str, Any]) -> str:
    """Render the compact swing-mode daily Telegram report.

    Expected ``metrics`` keys: ``date``, ``day_number``, ``pnl``, ``swing_state``,
    ``uw_shadow_summary``, ``market`` (vix/spy). Missing keys degrade gracefully.
    """
    date_str = metrics.get("date", "?")
    day_num = metrics.get("day_number", 0)

    pnl = metrics.get("pnl", {})
    realized = float(pnl.get("net", pnl.get("gross", 0.0)))
    unrealized = pnl.get("unrealized")          # eod_report may inject
    cum = float(pnl.get("cumulative", 0.0))
    closed_count = int(pnl.get("closed_trades_today", 0))
    cb_threshold = float(pnl.get("circuit_breaker_threshold", -5000.0))

    swing = metrics.get("swing_state", {}) or {}
    open_n = int(swing.get("open_positions", 0))
    max_cap = int(swing.get("max_concurrent", 12))
    new_today = int(swing.get("new_entries_today", 0))
    new_tickers = swing.get("new_entries_tickers", [])
    exits_today = swing.get("exits_today", {}) or {}
    total_notional = float(swing.get("total_notional", 0.0))
    notional_pct = float(swing.get("total_notional_pct_equity", 0.0))
    sector_dist = swing.get("sector_distribution", {}) or {}

    next_day = swing.get("next_day_planned", {}) or {}
    exits_at_1530 = next_day.get("exits_at_1530", [])
    time_stops_at_2140 = next_day.get("time_stops_at_2140", [])

    score_dist = swing.get("swing_score_distribution", {}) or {}
    top_scores = score_dist.get("top_3_scores") or score_dist.get("top_5_scores") or []

    equity = float(metrics.get("initial_capital", 100_000.0))

    # --- Build the body ---
    lines: list[str] = []
    lines.append(f"🌅 IFDS Swing — {date_str} (Day {day_num})")
    lines.append("─" * 37)
    # P&L block: realized + unrealized + cumulative
    lines.append(f"💰 Realized today:   ${realized:+,.2f}  ({closed_count} closed)")
    if unrealized is not None:
        lines.append(f"📊 Unrealized:       ${float(unrealized):+,.2f}  ({open_n} open)")
    lines.append(f"📈 Cumulative:       ${cum:+,.0f}  (real-mark)")
    lines.append("")
    lines.append(f"📂 Pozíciók:        {open_n} nyitva / {max_cap} cap")

    if new_today > 0:
        if new_tickers:
            lines.append(f"🆕 Új entry today:  {new_today} ({', '.join(new_tickers)})")
        else:
            lines.append(f"🆕 Új entry today:  {new_today}")
    else:
        lines.append("🆕 Új entry today:  0")

    exit_strs = [f"{cnt} {kind}" for kind, cnt in sorted(exits_today.items()) if cnt > 0]
    if exit_strs:
        lines.append(f"📤 Triggered exits: {', '.join(exit_strs)} → holnap 15:30")
    else:
        lines.append("📤 Triggered exits: 0")

    # --- Open swing book + sectors ---
    if open_n > 0:
        lines.append("")
        lines.append(
            f"📒 Open book:       ${total_notional:,.0f}  ({notional_pct:.1f}%)"
        )
        if sector_dist:
            sector_bits = []
            for sector, notional in sorted(sector_dist.items(), key=lambda kv: -kv[1]):
                if equity > 0:
                    sector_bits.append(f"{sector} {notional / equity * 100:.1f}%")
            if sector_bits:
                lines.append(f"🏷 Sectors:          {' | '.join(sector_bits)}")

    if top_scores:
        lines.append("")
        lines.append("🎯 Top S_j today:")
        for entry in top_scores[:3]:
            ticker = entry.get("ticker", "?")
            score = float(entry.get("S_j", entry.get("score", 0.0)))
            sector = entry.get("sector", "")
            atr = entry.get("atr_move", "")
            sector_str = f" | {sector}" if sector else ""
            atr_str = f" | {atr}" if atr else ""
            lines.append(f"   {ticker}  {score:.1f}{sector_str}{atr_str}")

    if exits_at_1530 or time_stops_at_2140:
        lines.append("")
        lines.append("⚡ Holnap exit-tervek:")
        if exits_at_1530:
            lines.append(f"   15:30: {', '.join(exits_at_1530)}")
        if time_stops_at_2140:
            lines.append(f"   21:40: {', '.join(time_stops_at_2140)}")

    uw = metrics.get("uw_shadow_summary", {}) or {}
    if uw and uw.get("tickers_logged", 0):
        lines.append("")
        lines.append("🔬 UW shadow:")
        # daily_metrics.py uses ``avg_dp_pct``; accept ``dp_pct_avg`` for back-compat.
        dp_avg = uw.get("avg_dp_pct", uw.get("dp_pct_avg"))
        n_log = uw.get("tickers_logged", 0)
        m_gex = uw.get("m_gex_avg_would_have_been")
        if dp_avg is not None:
            line = f"   {n_log} logged | dp_pct avg {dp_avg:.2f}%"
            if m_gex is not None:
                line += f" | M_GEX avg {m_gex:.2f}"
            lines.append(line)
        else:
            lines.append(f"   {n_log} logged")

    mkt = metrics.get("market", {}) or {}
    vix = mkt.get("vix_close")
    vix_d = mkt.get("vix_delta_pct")
    spy_r = mkt.get("spy_return_pct")
    if vix is not None or spy_r is not None:
        lines.append("")
        bits = []
        if vix is not None:
            d_str = f" (Δ {vix_d:+.1f}%)" if vix_d is not None else ""
            bits.append(f"VIX: {vix:.1f}{d_str}")
        if spy_r is not None:
            bits.append(f"SPY: {spy_r:+.2f}%")
        lines.append(" | ".join(bits))

    # --- Circuit breaker buffer ---
    if cb_threshold < 0:
        # cum is signed; CB triggered when cum <= cb_threshold (a negative number).
        # Buffer = how much further cum can fall before CB fires.
        buffer_usd = cum - cb_threshold       # positive if still safe
        buffer_pct = (buffer_usd / abs(cb_threshold)) * 100 if cb_threshold != 0 else 0.0
        if cum <= cb_threshold:
            lines.append("")
            lines.append(
                f"🛑 CIRCUIT BREAKER:  ${cum:+,.0f} / ${cb_threshold:,.0f}  TRIGGERED"
            )
        else:
            lines.append("")
            lines.append(
                f"🟢 CB buffer:        ${cum:+,.0f} / ${cb_threshold:,.0f}  ({buffer_pct:.1f}%)"
            )

    lines.append("─" * 37)
    return "\n".join(lines)


def format_pt_monitor_eod_telegram(
    positions: list[Any],
    ohlc_map: dict[str, dict[str, float]],
    exits: list[tuple[str, str]],
    today_date: date,
    day_number: int = 0,
    total_days: int = 63,
    equity: float = 100_000.0,
    max_hold_days: int = 5,
    market: dict[str, float] | None = None,
) -> str:
    """Render the 22:00 pt_monitor EOD Telegram (Task #T §3.3).

    Pure function — takes the post-eval SwingPosition list + today's OHLC bars
    + the triggered exits + market context, returns the Telegram body string.

    Action icons: ✅ TP1/TP2, 🛑 HARD_SL/MENTAL_SL/TRAIL_SL, ⏰ TIME_STOP, ⏸ HOLD.
    """
    today_iso = today_date.isoformat()
    exits_map = {ticker: action for ticker, action in exits}

    icon_map = {
        "TP1": "✅", "TP2": "✅",
        "HARD_SL": "🛑", "MENTAL_SL": "🛑", "TRAIL_SL": "🛑",
        "TIME_STOP": "⏰",
        "HOLD": "⏸",
    }

    lines: list[str] = []
    if day_number:
        lines.append(f"🌙 IFDS Swing EOD — Day {day_number}/{total_days} ({today_iso})")
    else:
        lines.append(f"🌙 IFDS Swing EOD — {today_iso}")

    if not positions:
        lines.append("(no open positions)")
        return "\n".join(lines)

    # --- Open book + sectors ---
    total_notional = sum(p.entry_price * p.qty_remaining for p in positions)
    notional_pct = (total_notional / equity * 100) if equity > 0 else 0.0
    lines.append("")
    lines.append(
        f"Open: {len(positions)} | Notional: ${total_notional:,.0f} ({notional_pct:.1f}%)"
    )
    sector_totals: dict[str, float] = {}
    for p in positions:
        s = p.sector or "?"
        sector_totals[s] = sector_totals.get(s, 0.0) + p.entry_price * p.qty_remaining
    if sector_totals:
        sector_bits = [
            f"{s} {v / equity * 100:.1f}%"
            for s, v in sorted(sector_totals.items(), key=lambda kv: -kv[1])
        ]
        lines.append(f"Sectors: {' | '.join(sector_bits)}")

    # --- Per-ticker EOD eval lines ---
    lines.append("")
    lines.append("EOD eval:")
    for p in positions:
        bar = ohlc_map.get(p.ticker, {})
        close = bar.get("close")
        pct = (
            (close - p.entry_price) / p.entry_price * 100
            if close is not None and p.entry_price > 0
            else None
        )
        action = exits_map.get(p.ticker, "HOLD")
        icon = icon_map.get(action, "⏸")
        close_str = f"${close:.2f}" if close is not None else "n/a"
        pct_str = f"({pct:+.2f}%)" if pct is not None else ""
        lines.append(f"  {p.ticker:<5} {close_str:>10}  {icon} {action} {pct_str}")

    # --- Time-stops countdown ---
    has_time_stops = any(
        max_hold_days - p.days_held <= 2 for p in positions
    )
    if has_time_stops:
        lines.append("")
        lines.append("Time-stops:")
        for p in positions:
            days_left = max_hold_days - p.days_held
            if days_left <= 2:
                lines.append(
                    f"  {p.ticker}: {days_left} day{'s' if days_left != 1 else ''} left "
                    f"(qty {p.qty_remaining})"
                )

    # --- Market context ---
    if market:
        vix = market.get("vix_close")
        vix_d = market.get("vix_delta_pct")
        spy_r = market.get("spy_return_pct")
        if vix is not None or spy_r is not None:
            lines.append("")
            bits = []
            if vix is not None:
                d_str = f" ({vix_d:+.1f}%)" if vix_d is not None else ""
                bits.append(f"VIX {vix:.1f}{d_str}")
            if spy_r is not None:
                bits.append(f"SPY {spy_r:+.2f}%")
            lines.append(" | ".join(bits))

    return "\n".join(lines)
