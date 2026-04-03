"""Phase 1-3 Context Persistence — save/load inter-phase state.

When the pipeline is split (Phase 1-3 at 22:00, Phase 4-6 at 15:45),
the Phase 1-3 output must be persisted so Phase 4-6 can resume.

State file: ``state/phase13_ctx.json.gz`` (gzipped JSON).
"""

from __future__ import annotations

import gzip
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from ifds.models.market import (
    BMIRegime,
    MacroRegime,
    MarketVolatilityRegime,
    SectorBMIRegime,
    SectorScore,
    StrategyMode,
    MomentumClassification,
    BreadthRegime,
    Ticker,
)

DEFAULT_PATH = "state/phase13_ctx.json.gz"


def save_phase13_context(ctx: object, path: str = DEFAULT_PATH) -> Path:
    """Save Phase 1-3 context fields to gzipped JSON.

    Extracts the fields needed by Phase 4-6 from PipelineContext.
    """
    data = {
        "macro": _macro_to_dict(ctx.macro) if ctx.macro else None,
        "strategy_mode": ctx.strategy_mode.value if ctx.strategy_mode else None,
        "bmi_regime": ctx.bmi_regime.value if ctx.bmi_regime else None,
        "bmi_value": ctx.bmi_value,
        "sector_bmi_values": ctx.sector_bmi_values or {},
        "universe": [_ticker_to_dict(t) for t in (ctx.universe or [])],
        "sector_scores": [_sector_score_to_dict(s) for s in (ctx.sector_scores or [])],
        "vetoed_sectors": list(ctx.vetoed_sectors or []),
        "agg_benchmark": _sector_score_to_dict(ctx.agg_benchmark) if ctx.agg_benchmark else None,
        "uw_available": ctx.uw_available,
    }

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(out.parent), suffix=".tmp")
    os.close(fd)
    try:
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, str(out))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return out


def load_phase13_context(ctx: object, path: str = DEFAULT_PATH) -> bool:
    """Load Phase 1-3 context from gzipped JSON into PipelineContext.

    Populates: macro, strategy_mode, bmi_regime, bmi_value,
    sector_bmi_values, universe, sector_scores, vetoed_sectors,
    agg_benchmark, uw_available.

    Returns True if loaded successfully, False otherwise.
    """
    p = Path(path)
    if not p.exists():
        return False

    try:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False

    ctx.macro = _dict_to_macro(data["macro"]) if data.get("macro") else None
    ctx.strategy_mode = StrategyMode(data["strategy_mode"]) if data.get("strategy_mode") else StrategyMode.LONG
    ctx.bmi_regime = BMIRegime(data["bmi_regime"]) if data.get("bmi_regime") else None
    ctx.bmi_value = data.get("bmi_value")
    ctx.sector_bmi_values = data.get("sector_bmi_values", {})
    ctx.universe = [_dict_to_ticker(d) for d in data.get("universe", [])]
    ctx.sector_scores = [_dict_to_sector_score(d) for d in data.get("sector_scores", [])]
    ctx.vetoed_sectors = data.get("vetoed_sectors", [])
    ctx.agg_benchmark = _dict_to_sector_score(data["agg_benchmark"]) if data.get("agg_benchmark") else None
    ctx.uw_available = data.get("uw_available", False)

    return True


# ------------------------------------------------------------------
# Serialization helpers
# ------------------------------------------------------------------

def _macro_to_dict(m: MacroRegime) -> dict:
    return {
        "vix_value": m.vix_value,
        "vix_regime": m.vix_regime.value,
        "vix_multiplier": m.vix_multiplier,
        "tnx_value": m.tnx_value,
        "tnx_sma20": m.tnx_sma20,
        "tnx_rate_sensitive": m.tnx_rate_sensitive,
        "yield_curve_2s10s": m.yield_curve_2s10s,
        "curve_status": m.curve_status,
        "cross_asset_regime": m.cross_asset_regime,
        "cross_asset_votes": m.cross_asset_votes,
        "vix_threshold_adjusted": m.vix_threshold_adjusted,
    }


def _dict_to_macro(d: dict) -> MacroRegime:
    return MacroRegime(
        vix_value=d["vix_value"],
        vix_regime=MarketVolatilityRegime(d["vix_regime"]),
        vix_multiplier=d["vix_multiplier"],
        tnx_value=d["tnx_value"],
        tnx_sma20=d["tnx_sma20"],
        tnx_rate_sensitive=d["tnx_rate_sensitive"],
        yield_curve_2s10s=d.get("yield_curve_2s10s"),
        curve_status=d.get("curve_status", "UNKNOWN"),
        cross_asset_regime=d.get("cross_asset_regime", "NORMAL"),
        cross_asset_votes=d.get("cross_asset_votes", 0.0),
        vix_threshold_adjusted=d.get("vix_threshold_adjusted", 20.0),
    )


def _ticker_to_dict(t: Ticker) -> dict:
    return {"symbol": t.symbol, "sector": t.sector}


def _dict_to_ticker(d: dict) -> Ticker:
    return Ticker(symbol=d["symbol"], sector=d["sector"])


def _sector_score_to_dict(s: SectorScore) -> dict:
    return {
        "sector_name": s.sector_name,
        "etf": s.etf,
        "momentum_5d": s.momentum_5d,
        "score_adjustment": s.score_adjustment,
        "classification": s.classification.value,
        "sector_bmi": s.sector_bmi,
        "sector_bmi_regime": s.sector_bmi_regime.value,
        "breadth_score_adj": getattr(s, "breadth_score_adj", 0),
    }


def _dict_to_sector_score(d: dict) -> SectorScore:
    return SectorScore(
        etf=d["etf"],
        sector_name=d.get("sector_name", ""),
        momentum_5d=d.get("momentum_5d", 0.0),
        score_adjustment=d.get("score_adjustment", 0),
        classification=MomentumClassification(d.get("classification", "neutral")),
        sector_bmi=d.get("sector_bmi"),
        sector_bmi_regime=SectorBMIRegime(d.get("sector_bmi_regime", "neutral")),
    )
