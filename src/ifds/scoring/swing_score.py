"""Swing scoring engine (Day 63 outcome §3.4, §3.5, §3.13 — 2026-05-18).

Replaces the 3-component (flow 0.40 + tech 0.30 + funda 0.30) weighted
scoring with a Bonferroni-minimum percentile formulation:

    S_j(t) = 100 × (PCR_percentile_j(t) − OTM_percentile_j(t)) + sector_adj_j(t)
    EWMA(5) smoothed per ticker, N=5 day history persisted to disk.

* PCR (put-call ratio): higher = more bearish hedging = bullish positioning
  → percentile rank, **positive sign** (high PCR → high score).
* OTM call ratio: higher = retail FOMO/short-term momentum chase → sign-
  flipped on the Bonferroni-significant audit → **negative sign** (high
  OTM → low score).
* Cross-sectional ranking is the Day-1-operational normalization. A rolling
  5-day cross-sectional percentile is a future-scope refinement
  (strategic-review §4 mentions but defers to Fázis 4+).

The threshold S_j > 50 is the Bonferroni-significant minimum from the
2026-05-08 strategic review §4 (the only two features that survived
Bonferroni correction on the 60-trade sample).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scipy import stats

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Percentile helpers
# ---------------------------------------------------------------------------


def compute_percentile_score(values: list[float], target: float) -> float:
    """Cross-sectional rank percentile of ``target`` within ``values``.

    Returns a value in [0.0, 1.0]:
        0.0 → target is the lowest in the universe
        1.0 → target is the highest in the universe

    Uses ``scipy.stats.percentileofscore(kind='rank')`` to handle ties as
    the average rank — the same convention used by pandas. If ``values`` is
    empty, returns 0.5 (neutral) so downstream code stays numerically stable.
    """
    if not values:
        return 0.5
    return float(stats.percentileofscore(values, target, kind="rank")) / 100.0


def compute_raw_swing_score(
    pcr: float,
    pcr_universe: list[float],
    otm_call_ratio: float,
    otm_universe: list[float],
    sector_adjustment: float,
) -> float:
    """Pure-function swing score from raw inputs.

    ``S = 100 × (PCR_pct − OTM_pct) + sector_adj``.
    Negative when the ticker is high-OTM/low-PCR; positive when high-PCR/
    low-OTM. Range typically -100 to +100 before sector_adj.
    """
    pcr_pct = compute_percentile_score(pcr_universe, pcr)
    otm_pct = compute_percentile_score(otm_universe, otm_call_ratio)
    return 100.0 * (pcr_pct - otm_pct) + float(sector_adjustment)


# ---------------------------------------------------------------------------
# EWMA(N) per-ticker state
# ---------------------------------------------------------------------------


@dataclass
class SwingEwmaState:
    """Per-ticker EWMA history persisted to ``state/swing_ewma_state.json``.

    Schema on disk:
        {
          "AAPL": {"history": [54.2, 56.8, 58.1], "ewma": 56.0},
          "MSFT": {"history": [...], "ewma": ...},
          ...
        }
    """

    path: Path
    span: int = 5
    _data: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def alpha(self) -> float:
        return 2.0 / (self.span + 1)

    # -- I/O ------------------------------------------------------------

    def load(self) -> None:
        if not self.path.exists():
            self._data = {}
            return
        try:
            self._data = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Swing EWMA state unreadable, starting fresh: %s", exc)
            self._data = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True))

    # -- per-ticker -----------------------------------------------------

    def update(self, ticker: str, raw_score: float) -> float:
        """Update the EWMA for one ticker, return the smoothed value.

        Day-1 semantics (no history): EWMA = raw_score.
        Subsequent days: ewma_new = α × raw + (1 − α) × ewma_prev.
        ``history`` keeps the last ``span`` raw scores for audit + future
        rolling-window experiments.
        """
        entry = self._data.get(ticker, {})
        history: list[float] = list(entry.get("history") or [])
        previous_ewma = entry.get("ewma")

        if previous_ewma is None:
            smoothed = float(raw_score)
        else:
            smoothed = self.alpha * float(raw_score) + (1.0 - self.alpha) * float(previous_ewma)

        history.append(float(raw_score))
        if len(history) > self.span:
            history = history[-self.span :]

        self._data[ticker] = {
            "history": history,
            "ewma": round(smoothed, 4),
        }
        return smoothed

    def get(self, ticker: str) -> dict[str, Any] | None:
        return self._data.get(ticker)

    # introspection for tests
    def as_dict(self) -> dict[str, dict[str, Any]]:
        return dict(self._data)


# ---------------------------------------------------------------------------
# Batch operation — called from Phase 4 post-processing
# ---------------------------------------------------------------------------


@dataclass
class SwingScoreResult:
    ticker: str
    raw_score: float
    ewma_score: float
    pcr_percentile: float
    otm_percentile: float
    sector_adjustment: float


def compute_swing_scores(
    tickers_data: list[dict[str, Any]],
    ewma_state: SwingEwmaState,
) -> list[SwingScoreResult]:
    """Compute swing scores for an entire universe pass.

    ``tickers_data`` items must have keys:
      - ``ticker``: str
      - ``pcr``: float | None (None → treated as median = neutral)
      - ``otm_call_ratio``: float | None (same)
      - ``sector_adjustment``: float

    The percentile distributions are built from non-None values only.
    Returns one :class:`SwingScoreResult` per input ticker in the same order.
    Mutates ``ewma_state`` (caller is responsible for ``.save()``).
    """
    pcr_universe = [
        t["pcr"] for t in tickers_data if t.get("pcr") is not None
    ]
    otm_universe = [
        t["otm_call_ratio"] for t in tickers_data if t.get("otm_call_ratio") is not None
    ]

    # Universe-median fallbacks for tickers missing one of the inputs — keeps
    # them numerically stable (they end up near 0 raw, with sector_adj only).
    pcr_median = float(sorted(pcr_universe)[len(pcr_universe) // 2]) if pcr_universe else 0.0
    otm_median = float(sorted(otm_universe)[len(otm_universe) // 2]) if otm_universe else 0.0

    results: list[SwingScoreResult] = []
    for entry in tickers_data:
        ticker = entry["ticker"]
        pcr_value = entry.get("pcr") if entry.get("pcr") is not None else pcr_median
        otm_value = entry.get("otm_call_ratio") if entry.get("otm_call_ratio") is not None else otm_median
        sector_adj = float(entry.get("sector_adjustment") or 0.0)

        pcr_pct = compute_percentile_score(pcr_universe, pcr_value)
        otm_pct = compute_percentile_score(otm_universe, otm_value)
        raw = 100.0 * (pcr_pct - otm_pct) + sector_adj
        smoothed = ewma_state.update(ticker, raw)

        results.append(
            SwingScoreResult(
                ticker=ticker,
                raw_score=raw,
                ewma_score=smoothed,
                pcr_percentile=pcr_pct,
                otm_percentile=otm_pct,
                sector_adjustment=sector_adj,
            )
        )
    return results
