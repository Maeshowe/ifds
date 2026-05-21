"""UW Dark Pool / GEX Shadow Logger (Day 63 outcome §3.2).

Day 63 decision [2]: the UW dark pool / GEX scoring is deactivated, but the
underlying data continues to be collected as a daily shadow snapshot through
Day 90 (~2026-08-26, W34). At Day 90 the 90-day shadow record allows
retroactive Bayesian recalibration analysis (e.g. regime-conditional dp_pct
sign-flip robustness, M_GEX impact under different VIX quintiles) without
the scoring pipeline depending on the unstable UW signal in the meantime.

Module surface:

* `_recompute_dp_pct_score`: reproduces the inclusive-boundary dp_pct
  scoring used in `phase4_stocks.py` — kept here so the shadow snapshot
  can capture the "would have been" dp_pct bonus even when scoring is
  disabled.
* `_gex_multiplier_for_regime`: reproduces the GEX multiplier mapping
  used in `phase5_gex.py` — kept here so the shadow snapshot can capture
  the "would have been" M_GEX even when sizing is disabled.
* `build_shadow_snapshot`: builds the daily snapshot payload from the
  Phase 4 / Phase 5 / Phase 6 pipeline outputs.
* `write_shadow_snapshot`: serializes a snapshot to
  `state/uw_shadow/YYYY-MM-DD.json`.
* `load_shadow_snapshot`: reads a snapshot back (used by daily_metrics
  and for Day 90 retrospective audit scripts).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Pure helpers — duplicate the active scoring rules so the shadow snapshot
# can record "what would have been" values without touching live scoring.
# ---------------------------------------------------------------------------


def _recompute_dp_pct_score(dp_pct: float, tuning: dict[str, Any]) -> int:
    """Reproduce inclusive-boundary dp_pct scoring (phase4_stocks.py:579-583).

    Always returns the score that would have been added to the flow component
    if `uw_dark_pool_scoring_enabled=True`, regardless of the current flag.
    """
    base_threshold = tuning["dark_pool_volume_threshold_pct"]
    high_threshold = tuning["dp_pct_high_threshold"]
    if dp_pct >= high_threshold:
        return int(tuning["dp_pct_high_bonus"])
    if dp_pct >= base_threshold:
        return int(tuning["dp_pct_bonus"])
    return 0


def _gex_multiplier_for_regime(gex_regime: str, tuning: dict[str, Any]) -> float:
    """Reproduce the GEX → multiplier mapping used in Phase 5/6 for shadow.

    GEXRegime values are strings (POSITIVE/NEGATIVE/HIGH_VOL → 'positive' etc.).
    The active multipliers live in TUNING (defaults: positive 1.0, negative 0.5,
    high_vol 0.6).
    """
    regime = (gex_regime or "").lower()
    if regime == "negative":
        return float(tuning.get("gex_negative_multiplier", 0.5))
    if regime == "high_vol":
        return float(tuning.get("gex_high_vol_multiplier", 0.6))
    return float(tuning.get("gex_positive_multiplier", 1.0))


# ---------------------------------------------------------------------------
# Snapshot builder
# ---------------------------------------------------------------------------


def build_shadow_snapshot(
    trading_date: str,
    stock_analyses: list,
    gex_analyses: list,
    positions: list,
    tuning: dict[str, Any],
) -> dict[str, Any]:
    """Build the daily UW shadow snapshot from pipeline outputs.

    Captures, per Phase 4 passed ticker:

    * raw dp_pct + would-have-been dp_pct_score (if scoring re-enabled)
    * raw gex_regime + gex_value + would-have-been M_GEX
    * the live combined_score (shadow-mode value — does NOT include the
      gated dp_pct bonus when the flag is False)
    * whether the ticker survived Phase 4 (passed) and made it to Phase 6

    The returned dict is JSON-serializable; `write_shadow_snapshot` adds
    `captured_at` and persists it.
    """
    gex_by_ticker = {g.ticker: g for g in gex_analyses or []}
    pos_tickers = {p.ticker for p in positions or []}

    tickers: dict[str, dict[str, Any]] = {}
    for stock in stock_analyses or []:
        ticker = stock.ticker
        flow = stock.flow

        dp_pct = float(flow.dark_pool_pct or 0.0)
        dp_score_would_have_been = _recompute_dp_pct_score(dp_pct, tuning)

        gex = gex_by_ticker.get(ticker)
        if gex is not None:
            gex_regime = getattr(gex.gex_regime, "value", str(gex.gex_regime))
            gex_value = float(gex.net_gex or 0.0)
            m_gex_would_have_been = float(gex.gex_multiplier)
        else:
            gex_regime = None
            gex_value = None
            m_gex_would_have_been = _gex_multiplier_for_regime("", tuning)

        tickers[ticker] = {
            "dp_pct": round(dp_pct, 2),
            "dp_score_would_have_been": dp_score_would_have_been,
            "gex_regime": gex_regime,
            "gex_value": gex_value,
            "m_gex_would_have_been": round(m_gex_would_have_been, 4),
            "phase4_passed": True,
            "phase6_sized": ticker in pos_tickers,
            "combined_score": round(float(stock.combined_score or 0.0), 2),
        }

    return {
        "date": trading_date,
        "tickers": tickers,
    }


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def write_shadow_snapshot(
    shadow_dir: Path,
    trading_date: str,
    snapshot: dict[str, Any],
) -> Path:
    """Persist a snapshot to ``{shadow_dir}/{trading_date}.json``.

    Adds ``captured_at`` (ISO-8601 UTC) at write time. Returns the path.
    """
    shadow_dir = Path(shadow_dir)
    shadow_dir.mkdir(parents=True, exist_ok=True)
    path = shadow_dir / f"{trading_date}.json"

    payload = dict(snapshot)
    payload["captured_at"] = datetime.now(timezone.utc).isoformat()

    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path


def load_shadow_snapshot(
    shadow_dir: Path,
    trading_date: str,
) -> dict[str, Any] | None:
    """Read back a snapshot. Returns ``None`` if the file does not exist."""
    path = Path(shadow_dir) / f"{trading_date}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Summary helper for daily_metrics integration
# ---------------------------------------------------------------------------


def summarize_shadow_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Aggregate one daily snapshot into the daily_metrics ``uw_shadow_summary``.

    Returns:
        ``tickers_logged``, ``avg_dp_pct``, ``would_have_been_penalty_count``,
        ``gex_regime_distribution``, ``m_gex_avg_would_have_been``.
    """
    tickers = (snapshot or {}).get("tickers", {})
    if not tickers:
        return {
            "tickers_logged": 0,
            "avg_dp_pct": 0.0,
            "would_have_been_penalty_count": 0,
            "gex_regime_distribution": {},
            "m_gex_avg_would_have_been": 1.0,
        }

    dp_pcts = [t.get("dp_pct", 0.0) for t in tickers.values()]
    penalty_count = sum(1 for t in tickers.values() if (t.get("dp_score_would_have_been") or 0) < 0)

    regime_dist: dict[str, int] = {}
    for t in tickers.values():
        regime = t.get("gex_regime") or "unknown"
        regime_dist[regime] = regime_dist.get(regime, 0) + 1

    m_gex_values = [t.get("m_gex_would_have_been", 1.0) for t in tickers.values()]
    m_gex_avg = sum(m_gex_values) / len(m_gex_values) if m_gex_values else 1.0

    return {
        "tickers_logged": len(tickers),
        "avg_dp_pct": round(sum(dp_pcts) / len(dp_pcts), 2) if dp_pcts else 0.0,
        "would_have_been_penalty_count": penalty_count,
        "gex_regime_distribution": regime_dist,
        "m_gex_avg_would_have_been": round(m_gex_avg, 4),
    }
