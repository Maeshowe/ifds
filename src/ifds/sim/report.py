"""Validation report generation.

Outputs:
- Console summary (colorama-enhanced)
- output/validation_trades.csv (per-trade details)
- output/validation_summary.json (aggregated metrics)
"""

import csv
import json
from datetime import date
from pathlib import Path

from ifds.sim.models import Trade, ValidationSummary


# ============================================================================
# Console Report
# ============================================================================

def print_validation_report(trades: list[Trade], summary: ValidationSummary) -> str:
    """Print formatted validation report to console.

    Returns:
        The formatted report string.
    """
    try:
        from colorama import Fore, Style
        G = Fore.GREEN
        R = Fore.RED
        Y = Fore.YELLOW
        C = Fore.CYAN
        W = Fore.WHITE
        RST = Style.RESET_ALL
    except ImportError:
        G = R = Y = C = W = RST = ""

    date_start = summary.date_range_start.isoformat() if summary.date_range_start else "N/A"
    date_end = summary.date_range_end.isoformat() if summary.date_range_end else "N/A"

    lines = []
    _box_top = f"{C}{'=' * 58}{RST}"
    _box_mid = f"{C}{'-' * 58}{RST}"

    lines.append("")
    lines.append(_box_top)
    lines.append(f"{C}{'IFDS Forward Validation Report':^58}{RST}")
    lines.append(_box_top)

    lines.append(f"  Period: {date_start} -> {date_end}")
    lines.append(f"  Execution Plans: {summary.plan_count}  |  Total Trades: {summary.total_trades}")
    lines.append(_box_mid)

    # Fill rate
    fill_pct = (summary.filled_trades / summary.total_trades * 100
                if summary.total_trades > 0 else 0)
    lines.append(f"  {W}FILL RATE{RST}")
    lines.append(f"    Filled: {summary.filled_trades}/{summary.total_trades} ({fill_pct:.1f}%)")
    lines.append(f"    Unfilled: {summary.unfilled_trades} (entry price not reached)")
    lines.append(_box_mid)

    # Leg 1
    wr1_color = G if summary.leg1_win_rate >= 50 else R
    lines.append(f"  {W}LEG 1 (33% -> TP1/SL){RST}          Win Rate: {wr1_color}{summary.leg1_win_rate:.1f}%{RST}")
    lines.append(f"    TP1 Hit: {summary.leg1_tp_hits}  |  Stop: {summary.leg1_stop_hits}  |  Expired: {summary.leg1_expired}")
    lines.append(_box_mid)

    # Leg 2
    wr2_color = G if summary.leg2_win_rate >= 50 else R
    lines.append(f"  {W}LEG 2 (66% -> TP2/SL){RST}          Win Rate: {wr2_color}{summary.leg2_win_rate:.1f}%{RST}")
    lines.append(f"    TP2 Hit: {summary.leg2_tp_hits}  |  Stop: {summary.leg2_stop_hits}  |  Expired: {summary.leg2_expired}")
    lines.append(_box_mid)

    # P&L
    pnl_color = G if summary.total_pnl >= 0 else R
    lines.append(f"  {W}P&L SUMMARY{RST}")
    lines.append(f"    Total: {pnl_color}${summary.total_pnl:+,.2f}{RST}  |  "
                 f"Avg/trade: ${summary.avg_pnl_per_trade:+,.2f}")
    lines.append(f"    Best: {G}+${summary.best_trade_pnl:,.2f}{RST} ({summary.best_trade_ticker})"
                 f"  |  Worst: {R}-${abs(summary.worst_trade_pnl):,.2f}{RST} ({summary.worst_trade_ticker})")
    lines.append(f"    Avg holding: {summary.avg_holding_days:.1f} days")
    lines.append(_box_mid)

    # GEX regime breakdown
    if summary.pnl_by_gex_regime:
        lines.append(f"  {W}BY GEX REGIME{RST}")
        for regime, data in sorted(summary.pnl_by_gex_regime.items()):
            pnl = data["pnl"]
            color = G if pnl >= 0 else R
            lines.append(
                f"    {regime}: {color}${pnl:+,.2f}{RST} "
                f"({data['trades']} trades, {data['win_rate']:.0f}% win)")
        lines.append(_box_mid)

    # Score bucket breakdown
    if summary.win_rate_by_score_bucket:
        lines.append(f"  {W}BY SCORE BUCKET{RST}")
        parts = []
        for bucket in ["90+", "80-90", "70-80"]:
            wr = summary.win_rate_by_score_bucket.get(bucket)
            if wr is not None:
                parts.append(f"{bucket}: {wr:.0f}% win")
        lines.append(f"    {'  |  '.join(parts)}")

    lines.append(_box_top)
    lines.append("")

    report = "\n".join(lines)
    print(report)
    return report


# ============================================================================
# CSV Output
# ============================================================================

TRADE_COLUMNS = [
    "run_id", "run_date", "ticker", "direction", "score", "gex_regime",
    "multiplier", "entry_price", "quantity", "stop_loss", "tp1", "tp2",
    "qty_tp1", "qty_tp2", "filled", "fill_date", "fill_price",
    "leg1_exit_price", "leg1_exit_date", "leg1_exit_reason", "leg1_pnl",
    "leg2_exit_price", "leg2_exit_date", "leg2_exit_reason", "leg2_pnl",
    "total_pnl", "total_pnl_pct", "holding_days", "sector",
]


def write_validation_trades(trades: list[Trade],
                            output_dir: str = "output") -> str:
    """Write per-trade validation results to CSV.

    Returns:
        Path to the written CSV file.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    file_path = out_path / "validation_trades.csv"

    with open(file_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRADE_COLUMNS)
        writer.writeheader()

        for t in trades:
            writer.writerow({
                "run_id": t.run_id,
                "run_date": t.run_date.isoformat() if t.run_date else "",
                "ticker": t.ticker,
                "direction": t.direction,
                "score": round(t.score, 2),
                "gex_regime": t.gex_regime,
                "multiplier": round(t.multiplier, 4),
                "entry_price": round(t.entry_price, 2),
                "quantity": t.quantity,
                "stop_loss": round(t.stop_loss, 2),
                "tp1": round(t.tp1, 2),
                "tp2": round(t.tp2, 2),
                "qty_tp1": t.qty_tp1,
                "qty_tp2": t.qty_tp2,
                "filled": t.filled,
                "fill_date": t.fill_date.isoformat() if t.fill_date else "",
                "fill_price": round(t.fill_price, 2),
                "leg1_exit_price": round(t.leg1_exit_price, 2),
                "leg1_exit_date": t.leg1_exit_date.isoformat() if t.leg1_exit_date else "",
                "leg1_exit_reason": t.leg1_exit_reason,
                "leg1_pnl": round(t.leg1_pnl, 2),
                "leg2_exit_price": round(t.leg2_exit_price, 2),
                "leg2_exit_date": t.leg2_exit_date.isoformat() if t.leg2_exit_date else "",
                "leg2_exit_reason": t.leg2_exit_reason,
                "leg2_pnl": round(t.leg2_pnl, 2),
                "total_pnl": round(t.total_pnl, 2),
                "total_pnl_pct": round(t.total_pnl_pct, 4),
                "holding_days": t.holding_days,
                "sector": t.sector,
            })

    return str(file_path)


# ============================================================================
# JSON Summary Output
# ============================================================================

def write_validation_summary(summary: ValidationSummary,
                             output_dir: str = "output") -> str:
    """Write aggregated validation summary to JSON.

    Returns:
        Path to the written JSON file.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    file_path = out_path / "validation_summary.json"

    data = {
        "total_trades": summary.total_trades,
        "filled_trades": summary.filled_trades,
        "unfilled_trades": summary.unfilled_trades,
        "leg1": {
            "tp_hits": summary.leg1_tp_hits,
            "stop_hits": summary.leg1_stop_hits,
            "expired": summary.leg1_expired,
            "win_rate": round(summary.leg1_win_rate, 2),
        },
        "leg2": {
            "tp_hits": summary.leg2_tp_hits,
            "stop_hits": summary.leg2_stop_hits,
            "expired": summary.leg2_expired,
            "win_rate": round(summary.leg2_win_rate, 2),
        },
        "pnl": {
            "total": round(summary.total_pnl, 2),
            "avg_per_trade": round(summary.avg_pnl_per_trade, 2),
            "avg_pct": round(summary.avg_pnl_pct, 4),
            "best": {"pnl": round(summary.best_trade_pnl, 2),
                     "ticker": summary.best_trade_ticker},
            "worst": {"pnl": round(summary.worst_trade_pnl, 2),
                      "ticker": summary.worst_trade_ticker},
        },
        "avg_holding_days": round(summary.avg_holding_days, 1),
        "pnl_by_gex_regime": summary.pnl_by_gex_regime,
        "win_rate_by_score_bucket": summary.win_rate_by_score_bucket,
        "plan_count": summary.plan_count,
        "date_range_start": summary.date_range_start.isoformat() if summary.date_range_start else None,
        "date_range_end": summary.date_range_end.isoformat() if summary.date_range_end else None,
    }

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

    return str(file_path)
