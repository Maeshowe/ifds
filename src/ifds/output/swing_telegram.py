"""Compact swing Telegram report formatter — Task #5 §3.

Renders the daily Telegram summary in the new swing format (< 800 chars,
mobile-friendly). Pure function — takes a metrics dict (the output of
``daily_metrics.build_daily_metrics``) and returns the rendered Telegram body.
"""

from __future__ import annotations

from typing import Any


def format_swing_compact_telegram(metrics: dict[str, Any]) -> str:
    """Render the compact swing-mode daily Telegram report.

    Expected ``metrics`` keys: ``date``, ``day_number``, ``pnl``, ``swing_state``,
    ``uw_shadow_summary``, ``market`` (vix/spy). Missing keys degrade gracefully.
    """
    date_str = metrics.get("date", "?")
    day_num = metrics.get("day_number", 0)

    pnl = metrics.get("pnl", {})
    net = float(pnl.get("net", pnl.get("gross", 0.0)))
    cum = float(pnl.get("cumulative", 0.0))

    swing = metrics.get("swing_state", {}) or {}
    open_n = int(swing.get("open_positions", 0))
    max_cap = int(swing.get("max_concurrent", 12))
    new_today = int(swing.get("new_entries_today", 0))
    exits_today = swing.get("exits_today", {}) or {}

    next_day = swing.get("next_day_planned", {}) or {}
    exits_at_1530 = next_day.get("exits_at_1530", [])
    time_stops_at_2140 = next_day.get("time_stops_at_2140", [])

    score_dist = swing.get("swing_score_distribution", {}) or {}
    top_scores = score_dist.get("top_3_scores") or score_dist.get("top_5_scores") or []

    # --- Build the body ---
    lines: list[str] = []
    lines.append(f"🌅 IFDS Swing — {date_str} (Day {day_num})")
    lines.append("─" * 37)
    lines.append(f"📊 Nettó P&L:       ${net:+,.2f}   (cum ${cum:+,.0f})")
    lines.append(f"📈 Pozíciók:        {open_n} nyitva / {max_cap} cap")

    if new_today > 0:
        tickers = swing.get("new_entries_tickers", [])
        if tickers:
            lines.append(f"🆕 Új entry today:  {new_today} ({', '.join(tickers)})")
        else:
            lines.append(f"🆕 Új entry today:  {new_today}")
    else:
        lines.append("🆕 Új entry today:  0")

    exit_strs = [f"{cnt} {kind}" for kind, cnt in sorted(exits_today.items()) if cnt > 0]
    if exit_strs:
        lines.append(f"📤 Exit today:      {', '.join(exit_strs)}")
    else:
        lines.append("📤 Exit today:      0")

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
        dp_avg = uw.get("dp_pct_avg")
        n_log = uw.get("tickers_logged", 0)
        if dp_avg is not None:
            lines.append(f"   {n_log} logged | dp_pct avg {dp_avg:.1f}%")

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

    lines.append("─" * 37)
    return "\n".join(lines)
