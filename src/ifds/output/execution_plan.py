"""Execution plan, full scan matrix, and trade plan CSV output generation.

Writes CSV files for:
- execution_plan: Position sizing details for order execution
- full_scan_matrix: Every analyzed ticker (ACCEPTED/REJECTED) with reasons
- trade_plan: Top 20 positions summary for daily review
"""

import csv
from datetime import date
from pathlib import Path

from ifds.events.logger import EventLogger
from ifds.events.types import EventType, Severity
from ifds.models.market import PositionSizing, SectorScore, StockAnalysis

COLUMNS = [
    "instrument_id", "direction", "order_type", "limit_price",
    "quantity", "stop_loss", "take_profit_1", "take_profit_2",
    "risk_usd", "score", "gex_regime", "sector", "multiplier_total",
    "mult_vix", "mult_utility", "sector_bmi", "sector_regime", "is_mean_reversion",
]

SCAN_COLUMNS = [
    "Ticker", "Status", "Reason", "Total_Score", "Flow_Score", "Funda_Score",
    "Tech_Score", "Strategy", "Sector_ETF", "Sector_BMI", "Sector_Regime",
    "Price", "ATR", "Sector_Name",
]

TRADE_PLAN_COLUMNS = [
    "Rank", "Ticker", "Score", "Flow", "Funda", "Tech", "Sector", "Flags",
]

_BASE_SCORE = 50  # Neutral starting point for sub-dimension scores

_REASON_MAP = {
    "tech_filter": "Tech Filter (Price < SMA200)",
    "min_score": "Score < 70",
    "clipping": "Crowded Trade (Score > 95)",
}


def write_execution_plan(positions: list[PositionSizing],
                         output_dir: str,
                         run_id: str,
                         logger: EventLogger) -> str:
    """Write execution plan CSV.

    Args:
        positions: Sized positions (already sorted by score desc).
        output_dir: Directory to write the CSV file.
        run_id: Pipeline run ID for filename.
        logger: Event logger.

    Returns:
        Absolute path to the generated CSV file.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    file_path = out_path / f"execution_plan_{run_id}.csv"

    with open(file_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()

        for pos in positions:
            writer.writerow({
                "instrument_id": pos.ticker,
                "direction": pos.direction,
                "order_type": "LIMIT",
                "limit_price": round(pos.entry_price, 2),
                "quantity": pos.quantity,
                "stop_loss": round(pos.stop_loss, 2),
                "take_profit_1": round(pos.take_profit_1, 2),
                "take_profit_2": round(pos.take_profit_2, 2),
                "risk_usd": round(pos.risk_usd, 2),
                "score": round(pos.combined_score, 2),
                "gex_regime": pos.gex_regime,
                "sector": pos.sector,
                "multiplier_total": round(pos.multiplier_total, 4),
                "mult_vix": round(pos.m_vix, 4),
                "mult_utility": round(pos.m_utility, 4),
                "sector_bmi": round(pos.sector_bmi, 2) if pos.sector_bmi is not None else "",
                "sector_regime": pos.sector_regime,
                "is_mean_reversion": pos.is_mean_reversion,
            })

    logger.log(EventType.EXECUTION_PLAN, Severity.INFO, phase=6,
               message=f"Execution plan written: {file_path}",
               data={"path": str(file_path), "positions": len(positions)})

    return str(file_path)


def write_full_scan_matrix(analyzed: list[StockAnalysis],
                           sector_scores: list[SectorScore],
                           strategy_mode: str,
                           output_dir: str,
                           run_id: str,
                           logger: EventLogger) -> str:
    """Write full scan matrix CSV — every analyzed ticker with status and reason.

    Args:
        analyzed: All tickers analyzed in Phase 4 (passed + excluded).
        sector_scores: Sector scores from Phase 3.
        strategy_mode: "LONG" or "SHORT".
        output_dir: Directory to write the CSV file.
        run_id: Pipeline run ID for filename.
        logger: Event logger.

    Returns:
        Absolute path to the generated CSV file.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    file_path = out_path / f"full_scan_matrix_{today}.csv"

    # Build sector lookup
    sector_map = {ss.sector_name: ss for ss in sector_scores}

    with open(file_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SCAN_COLUMNS)
        writer.writeheader()

        for stock in analyzed:
            ss = sector_map.get(stock.sector)

            # Determine status and reason
            if stock.excluded:
                status = "REJECTED"
                reason = _REASON_MAP.get(stock.exclusion_reason or "", stock.exclusion_reason or "")
                # Override with Sector VETO if sector is vetoed
                if ss and ss.vetoed:
                    reason = (
                        f"Sector VETO ({ss.sector_name}, "
                        f"{ss.classification.value}, "
                        f"{ss.sector_bmi_regime.value})"
                    )
            else:
                status = "ACCEPTED"
                reason = ""

            # Sub-scores: base + adjustment (flow capped to [0, 100])
            flow_score = min(100, max(0, _BASE_SCORE + stock.flow.rvol_score))
            funda_score = _BASE_SCORE + stock.fundamental.funda_score
            tech_score = stock.technical.rsi_score + stock.technical.sma50_bonus + stock.technical.rs_spy_score

            writer.writerow({
                "Ticker": stock.ticker,
                "Status": status,
                "Reason": reason,
                "Total_Score": round(stock.combined_score, 2),
                "Flow_Score": flow_score,
                "Funda_Score": funda_score,
                "Tech_Score": tech_score,
                "Strategy": strategy_mode,
                "Sector_ETF": ss.etf if ss else "",
                "Sector_BMI": round(ss.sector_bmi, 2) if ss and ss.sector_bmi is not None else "",
                "Sector_Regime": ss.sector_bmi_regime.value if ss else "",
                "Price": round(stock.technical.price, 2),
                "ATR": round(stock.technical.atr_14, 2),
                "Sector_Name": stock.sector,
            })

    accepted = sum(1 for s in analyzed if not s.excluded)
    rejected = sum(1 for s in analyzed if s.excluded)
    logger.log(EventType.EXECUTION_PLAN, Severity.INFO, phase=4,
               message=f"Full scan matrix written: {file_path}",
               data={"path": str(file_path), "accepted": accepted, "rejected": rejected})

    return str(file_path)


def write_trade_plan(positions: list[PositionSizing],
                     stock_analyses: list[StockAnalysis],
                     output_dir: str,
                     run_id: str,
                     logger: EventLogger) -> str:
    """Write trade plan CSV — top 20 positions summary.

    Args:
        positions: Sized positions (already sorted by score desc).
        stock_analyses: All passed stocks from Phase 4 (for sub-scores).
        output_dir: Directory to write the CSV file.
        run_id: Pipeline run ID for filename.
        logger: Event logger.

    Returns:
        Absolute path to the generated CSV file.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    file_path = out_path / f"trade_plan_{today}.csv"

    # Build stock lookup for sub-scores
    stock_map = {s.ticker: s for s in stock_analyses}

    top_20 = positions[:20]

    with open(file_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRADE_PLAN_COLUMNS)
        writer.writeheader()

        for rank, pos in enumerate(top_20, 1):
            stock = stock_map.get(pos.ticker)
            if stock:
                flow = min(100, max(0, _BASE_SCORE + stock.flow.rvol_score))
                funda = _BASE_SCORE + stock.fundamental.funda_score
                tech = stock.technical.rsi_score + stock.technical.sma50_bonus + stock.technical.rs_spy_score
            else:
                flow = funda = tech = _BASE_SCORE

            flags = []
            if pos.is_fresh:
                flags.append("FRESH")
            if pos.shark_detected:
                flags.append("SHARK")

            writer.writerow({
                "Rank": rank,
                "Ticker": pos.ticker,
                "Score": round(pos.combined_score, 2),
                "Flow": flow,
                "Funda": funda,
                "Tech": tech,
                "Sector": pos.sector,
                "Flags": ",".join(flags),
            })

    logger.log(EventType.EXECUTION_PLAN, Severity.INFO, phase=6,
               message=f"Trade plan written: {file_path}",
               data={"path": str(file_path), "positions": len(top_20)})

    return str(file_path)
