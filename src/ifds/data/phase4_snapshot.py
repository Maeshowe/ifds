"""Phase 4 Snapshot Persistence — Save daily ticker data for SIM-L2 re-score.

Saves Phase 4 "passed" ticker raw data daily as gzipped JSON.
BC20 (Mód 2 re-score) will consume these snapshots.
"""

import gzip
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path


def save_phase4_snapshot(passed_analyses: list,
                         snapshot_dir: str = "state/phase4_snapshots") -> Path:
    """Save Phase 4 passed ticker data as daily snapshot.

    Args:
        passed_analyses: list[StockAnalysis] from Phase 4.
        snapshot_dir: Directory for snapshots.

    Returns:
        Path to the saved snapshot file.
    """
    out_dir = Path(snapshot_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    file_path = out_dir / f"{today}.json.gz"

    records = []
    for stock in passed_analyses:
        record = _stock_to_dict(stock)
        records.append(record)

    with gzip.open(file_path, "wt", encoding="utf-8") as f:
        json.dump(records, f)

    return file_path


def load_phase4_snapshot(date_str: str,
                         snapshot_dir: str = "state/phase4_snapshots") -> list[dict]:
    """Load a single day's snapshot for re-scoring.

    Args:
        date_str: Date in ISO format (YYYY-MM-DD).
        snapshot_dir: Directory for snapshots.

    Returns:
        List of ticker dicts, or empty list if not found.
    """
    dir_path = Path(snapshot_dir)

    # Try gzipped JSON first
    gz_path = dir_path / f"{date_str}.json.gz"
    if gz_path.exists():
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            return json.load(f)

    # Try plain JSON fallback
    json_path = dir_path / f"{date_str}.json"
    if json_path.exists():
        with open(json_path) as f:
            return json.load(f)

    return []


def _stock_to_dict(stock) -> dict:
    """Convert StockAnalysis to a flat dict for persistence."""
    t = stock.technical
    fl = stock.flow
    fu = stock.fundamental

    return {
        "ticker": stock.ticker,
        "sector": stock.sector,
        "combined_score": stock.combined_score,
        "sector_adjustment": stock.sector_adjustment,
        "shark_detected": stock.shark_detected,
        # Technical
        "price": t.price,
        "sma_200": t.sma_200,
        "sma_50": t.sma_50,
        "sma_20": t.sma_20,
        "rsi_14": t.rsi_14,
        "atr_14": t.atr_14,
        "trend_pass": t.trend_pass,
        "rsi_score": t.rsi_score,
        "sma50_bonus": t.sma50_bonus,
        "rs_vs_spy": t.rs_vs_spy,
        "rs_spy_score": t.rs_spy_score,
        # Flow
        "rvol": fl.rvol,
        "rvol_score": fl.rvol_score,
        "dark_pool_pct": fl.dark_pool_pct,
        "dp_pct_score": fl.dp_pct_score,
        "pcr": fl.pcr,
        "pcr_score": fl.pcr_score,
        "otm_call_ratio": fl.otm_call_ratio,
        "otm_score": fl.otm_score,
        "block_trade_count": fl.block_trade_count,
        "block_trade_score": fl.block_trade_score,
        "buy_pressure_score": fl.buy_pressure_score,
        "squat_bar": fl.squat_bar,
        # Fundamental
        "revenue_growth_yoy": fu.revenue_growth_yoy,
        "eps_growth_yoy": fu.eps_growth_yoy,
        "net_margin": fu.net_margin,
        "roe": fu.roe,
        "debt_equity": fu.debt_equity,
        "insider_score": fu.insider_score,
        "insider_multiplier": fu.insider_multiplier,
        "funda_score": fu.funda_score,
        "shark_detected_funda": fu.shark_detected,
        "inst_ownership_trend": fu.inst_ownership_trend,
        "inst_ownership_score": fu.inst_ownership_score,
    }
