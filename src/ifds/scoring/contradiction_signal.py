"""Contradiction Signal — structured FMP-based outlier protection.

Computes a CONTRADICTION flag from structured FMP fundamentals data.
Pure function, deterministic, no LLM call. Used by Phase 4 to enrich
snapshots, and by Phase 6 sizing as ``M_contradiction`` multiplier.

Conditions evaluated (any one triggers the flag):

    1. Earnings beat ratio < 50% over last 4 quarters
    2. Price > consensus target by 2%+
    3. Price > analyst HIGH target
    4. 2+ recent analyst downgrades (last 30 days)

Defensive: missing data ⇒ no flag (`is_contradicted=False`, `reasons=[]`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta


# Thresholds — also exported in ContradictionResult.detail['thresholds'] for audit
CONSENSUS_OVERSHOOT_THRESHOLD = 0.02   # 2% above consensus target
EARNINGS_BEAT_RATIO_THRESHOLD = 0.5    # <50% beats (e.g. 0/4 or 1/4)
RECENT_DOWNGRADES_THRESHOLD = 2        # 2+ downgrades inside the window
RECENT_DOWNGRADES_WINDOW_DAYS = 30


@dataclass(frozen=True)
class ContradictionResult:
    """Structured result of a contradiction-signal evaluation.

    Frozen for immutability — callers should never mutate the underlying data.
    """

    is_contradicted: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    detail: dict[str, object] = field(default_factory=dict)


def _count_earnings_beats(history: list[dict] | None) -> tuple[int, int]:
    """Return (beats, n_actual). Only quarters with both eps fields present."""
    if not history:
        return 0, 0
    beats = 0
    n = 0
    for entry in history:
        actual = entry.get("epsActual")
        estimated = entry.get("epsEstimated")
        if not isinstance(actual, (int, float)) or not isinstance(estimated, (int, float)):
            continue
        n += 1
        if actual >= estimated:
            beats += 1
    return beats, n


def _count_recent_downgrades(
    grades: list[dict] | None,
    *,
    today: date | None = None,
    window_days: int = RECENT_DOWNGRADES_WINDOW_DAYS,
) -> int:
    """Count grades whose ``action`` indicates a downgrade inside the window."""
    if not grades:
        return 0
    today = today or date.today()
    cutoff = today - timedelta(days=window_days)
    count = 0
    for grade in grades:
        action = str(grade.get("action", "")).lower()
        if action not in ("downgraded", "downgrade", "down"):
            continue
        date_str = str(grade.get("date", ""))[:10]
        try:
            grade_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if grade_date >= cutoff:
            count += 1
    return count


def compute_contradiction_signal(
    *,
    price: float,
    target_consensus: float | None = None,
    target_high: float | None = None,
    earnings_history: list[dict] | None = None,
    analyst_grades_recent: list[dict] | None = None,
    today: date | None = None,
) -> ContradictionResult:
    """Evaluate the four CONTRADICTION conditions on structured FMP data.

    Args:
        price: Current ticker price (from execution plan / Phase 4 technical).
        target_consensus: FMP ``price-target-consensus.targetConsensus``.
        target_high: FMP ``price-target-consensus.targetHigh``.
        earnings_history: FMP ``earnings`` (last N quarters with actuals);
            each item: ``{"date": str, "epsActual": float, "epsEstimated": float}``.
        analyst_grades_recent: FMP ``grades`` (recent N changes); each item:
            ``{"date": str, "action": str, ...}``.
        today: Date used for downgrade window comparisons. Default
            ``date.today()`` — explicit override allows deterministic tests.

    Returns:
        :class:`ContradictionResult` with flag, ordered reasons, and detail dict.
    """
    flags: list[str] = []
    detail: dict[str, object] = {
        "thresholds": {
            "consensus_overshoot": CONSENSUS_OVERSHOOT_THRESHOLD,
            "earnings_beat_ratio": EARNINGS_BEAT_RATIO_THRESHOLD,
            "recent_downgrades": RECENT_DOWNGRADES_THRESHOLD,
            "downgrades_window_days": RECENT_DOWNGRADES_WINDOW_DAYS,
        }
    }

    # 1: Earnings beat ratio
    beats, n = _count_earnings_beats(earnings_history)
    if n > 0:
        ratio = beats / n
        detail["earnings_beats"] = f"{beats}/{n}"
        detail["earnings_beat_ratio"] = round(ratio, 3)
        if ratio < EARNINGS_BEAT_RATIO_THRESHOLD:
            flags.append(f"earnings_beats_below_half ({beats}/{n})")

    # 2: Price vs consensus target overshoot
    if isinstance(target_consensus, (int, float)) and target_consensus > 0:
        overshoot = (price - target_consensus) / target_consensus
        detail["consensus_overshoot_pct"] = round(overshoot * 100, 2)
        if overshoot > CONSENSUS_OVERSHOOT_THRESHOLD:
            flags.append(f"price_above_consensus_{round(overshoot * 100, 1)}pct")

    # 3: Price vs analyst HIGH target
    if isinstance(target_high, (int, float)) and price > target_high:
        flags.append("price_above_analyst_high")
        detail["target_high"] = target_high

    # 4: Recent analyst downgrades
    if analyst_grades_recent:
        downgrade_count = _count_recent_downgrades(analyst_grades_recent, today=today)
        detail[f"recent_downgrades_{RECENT_DOWNGRADES_WINDOW_DAYS}d"] = downgrade_count
        if downgrade_count >= RECENT_DOWNGRADES_THRESHOLD:
            flags.append(f"recent_downgrades_{downgrade_count}")

    return ContradictionResult(
        is_contradicted=len(flags) > 0,
        reasons=tuple(flags),
        detail=detail,
    )
