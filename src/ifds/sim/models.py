"""SimEngine data models.

Level 1: Forward validation from execution plan CSVs.
Designed for Level 2 (replay) and Level 3 (full backtest) extension.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Trade:
    """Egy execution plan entry -> bracket order -> outcome."""

    run_id: str                      # Pipeline run ID
    run_date: date                   # Pipeline run date (parsed from CSV filename)
    ticker: str
    score: float                     # Combined score (freshness-adjusted)
    gex_regime: str                  # positive/negative/high_vol
    multiplier: float                # M_total

    # Entry
    entry_price: float               # Limit order price
    quantity: int                    # Total quantity
    direction: str = "BUY"           # BUY or SELL_SHORT

    # Bracket targets
    stop_loss: float = 0.0
    tp1: float = 0.0
    tp2: float = 0.0

    # Bracket split (IBKR logic)
    qty_tp1: int = 0                 # 33% of quantity -> TP1/SL bracket
    qty_tp2: int = 0                 # 66% of quantity -> TP2/SL bracket

    # Execution results (validator fills these)
    filled: bool = False             # BUY limit filled?
    fill_date: date | None = None
    fill_price: float = 0.0          # Simulated: if low <= entry -> fill @ entry

    # Leg 1 (33% -> TP1/SL)
    leg1_exit_price: float = 0.0
    leg1_exit_date: date | None = None
    leg1_exit_reason: str = ""       # "tp1" / "stop" / "expired" / "open"
    leg1_pnl: float = 0.0

    # Leg 2 (66% -> TP2/SL)
    leg2_exit_price: float = 0.0
    leg2_exit_date: date | None = None
    leg2_exit_reason: str = ""       # "tp2" / "stop" / "expired" / "open"
    leg2_pnl: float = 0.0

    # Summary
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    holding_days: int = 0

    # Sector (for reporting)
    sector: str = ""


@dataclass
class ValidationSummary:
    """Aggregated results across all validated trades."""

    total_trades: int = 0
    filled_trades: int = 0           # BUY limit filled
    unfilled_trades: int = 0         # BUY limit NOT filled (price didn't reach entry)

    # Leg 1 (TP1 bracket)
    leg1_tp_hits: int = 0
    leg1_stop_hits: int = 0
    leg1_expired: int = 0            # Neither TP nor Stop within max_hold_days
    leg1_win_rate: float = 0.0

    # Leg 2 (TP2 bracket)
    leg2_tp_hits: int = 0
    leg2_stop_hits: int = 0
    leg2_expired: int = 0
    leg2_win_rate: float = 0.0

    # P&L
    total_pnl: float = 0.0
    avg_pnl_per_trade: float = 0.0
    avg_pnl_pct: float = 0.0
    best_trade_pnl: float = 0.0
    best_trade_ticker: str = ""
    worst_trade_pnl: float = 0.0
    worst_trade_ticker: str = ""

    # Timing
    avg_holding_days: float = 0.0

    # Breakdowns
    pnl_by_gex_regime: dict = field(default_factory=dict)
    win_rate_by_score_bucket: dict = field(default_factory=dict)  # 70-80, 80-90, 90+

    # Metadata
    plan_count: int = 0              # Number of execution plan CSVs processed
    date_range_start: date | None = None
    date_range_end: date | None = None
