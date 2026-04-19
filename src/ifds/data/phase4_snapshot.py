"""Phase 4 Snapshot Persistence — Save daily ticker data for SIM-L2 re-score.

Saves Phase 4 "passed" ticker raw data daily as gzipped JSON.
BC20 (Mód 2 re-score) will consume these snapshots.
"""

import gzip
import json
import os
import tempfile
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

    # Atomic write: temp file + os.replace
    fd, tmp = tempfile.mkstemp(dir=str(out_dir), suffix=".tmp")
    os.close(fd)
    try:
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(records, f)
        os.replace(tmp, str(file_path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

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


def snapshot_to_stock_analysis(record: dict) -> "StockAnalysis":
    """Reconstruct StockAnalysis from a Phase 4 snapshot dict.

    Inverse of ``_stock_to_dict``.  Fields not persisted in snapshots
    (e.g. ``excluded``, ``volume_today``) get their dataclass defaults.
    """
    from ifds.models.market import (
        FlowAnalysis,
        FundamentalScoring,
        StockAnalysis,
        TechnicalAnalysis,
    )

    technical = TechnicalAnalysis(
        price=record["price"],
        sma_200=record["sma_200"],
        sma_20=record["sma_20"],
        rsi_14=record["rsi_14"],
        atr_14=record["atr_14"],
        trend_pass=record["trend_pass"],
        rsi_score=record.get("rsi_score", 0),
        sma_50=record.get("sma_50", 0.0),
        sma50_bonus=record.get("sma50_bonus", 0),
        rs_vs_spy=record.get("rs_vs_spy"),
        rs_spy_score=record.get("rs_spy_score", 0),
    )

    flow = FlowAnalysis(
        rvol=record.get("rvol", 1.0),
        rvol_score=record.get("rvol_score", 0),
        dark_pool_pct=record.get("dark_pool_pct", 0.0),
        dp_pct_score=record.get("dp_pct_score", 0),
        pcr=record.get("pcr"),
        pcr_score=record.get("pcr_score", 0),
        otm_call_ratio=record.get("otm_call_ratio"),
        otm_score=record.get("otm_score", 0),
        block_trade_count=record.get("block_trade_count", 0),
        block_trade_score=record.get("block_trade_score", 0),
        buy_pressure_score=record.get("buy_pressure_score", 0),
        squat_bar=record.get("squat_bar", False),
        # Dollar-weighted metrics (2026-04-17, default 0/0.0 for legacy snapshots)
        dp_volume_shares=record.get("dp_volume_shares", 0),
        total_volume=record.get("total_volume", 0),
        dp_volume_dollars=record.get("dp_volume_dollars", 0.0),
        block_trade_dollars=record.get("block_trade_dollars", 0.0),
        venue_entropy=record.get("venue_entropy", 0.0),
    )

    fundamental = FundamentalScoring(
        revenue_growth_yoy=record.get("revenue_growth_yoy"),
        eps_growth_yoy=record.get("eps_growth_yoy"),
        net_margin=record.get("net_margin"),
        roe=record.get("roe"),
        debt_equity=record.get("debt_equity"),
        insider_score=record.get("insider_score", 0),
        insider_multiplier=record.get("insider_multiplier", 1.0),
        funda_score=record.get("funda_score", 0),
        shark_detected=record.get("shark_detected_funda", False),
        inst_ownership_trend=record.get("inst_ownership_trend", "unknown"),
        inst_ownership_score=record.get("inst_ownership_score", 0),
    )

    return StockAnalysis(
        ticker=record["ticker"],
        sector=record["sector"],
        technical=technical,
        flow=flow,
        fundamental=fundamental,
        combined_score=record.get("combined_score", 0.0),
        sector_adjustment=record.get("sector_adjustment", 0),
        shark_detected=record.get("shark_detected", False),
        # Phase 5 GEX fields (None for legacy snapshots)
        net_gex=record.get("net_gex"),
        call_wall=record.get("call_wall"),
        put_wall=record.get("put_wall"),
        zero_gamma=record.get("zero_gamma"),
    )


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
        # Dollar-weighted flow metrics (2026-04-17)
        "dp_volume_shares": fl.dp_volume_shares,
        "total_volume": fl.total_volume,
        "dp_volume_dollars": fl.dp_volume_dollars,
        "block_trade_dollars": fl.block_trade_dollars,
        "venue_entropy": fl.venue_entropy,
        # Phase 5 GEX structural fields (None when options data unavailable)
        "net_gex": getattr(stock, "net_gex", None),
        "call_wall": getattr(stock, "call_wall", None),
        "put_wall": getattr(stock, "put_wall", None),
        "zero_gamma": getattr(stock, "zero_gamma", None),
    }
