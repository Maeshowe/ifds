"""WOW Signals — U-shaped freshness scoring for A/B testing.

Instead of a flat ×1.5 bonus for "new" signals (linear mode), the WOW
model assigns differentiated multipliers based on a ticker's appearance
pattern in recent signal history:

- **New Kid** (0 appearances):          ×1.15  — moderate bonus
- **WOW** (3+ appearances, ≤5 days):   ×1.10  — recurring winner
- **Stale** (1+ appearances, >30 days): ×0.80  — penalty for returning after long absence
- **Persistent** (5+ appearances):       ×1.05  — small bonus for consistency
- **Neutral** (everything else):          ×1.00  — no adjustment
"""

from __future__ import annotations

from datetime import date, timedelta


def count_appearances(
    ticker: str,
    signal_history: list[dict],
    lookback_days: int = 90,
    reference_date: date | None = None,
) -> int:
    """Count how many times *ticker* appeared in signal history within lookback.

    Parameters
    ----------
    ticker:
        Ticker symbol to search for.
    signal_history:
        List of ``{"date": "YYYY-MM-DD", "ticker": "SYM"}`` records.
    lookback_days:
        Window size in calendar days.
    reference_date:
        "Today" for the lookback calculation (default: ``date.today()``).
    """
    ref = reference_date or date.today()
    cutoff = ref - timedelta(days=lookback_days)
    return sum(
        1 for r in signal_history
        if r["ticker"] == ticker and _parse_date(r["date"]) >= cutoff
    )


def days_since_last_appearance(
    ticker: str,
    signal_history: list[dict],
    reference_date: date | None = None,
) -> int | None:
    """Days since the most recent appearance of *ticker*.

    Returns ``None`` if the ticker never appeared.
    """
    ref = reference_date or date.today()
    dates = [
        _parse_date(r["date"])
        for r in signal_history
        if r["ticker"] == ticker
    ]
    if not dates:
        return None
    return (ref - max(dates)).days


def wow_multiplier(
    ticker: str,
    signal_history: list[dict],
    lookback_days: int = 90,
    reference_date: date | None = None,
) -> float:
    """Compute U-shaped WOW freshness multiplier.

    Decision tree (first match wins):
    1. New Kid:    appearances == 0                      → 1.15
    2. WOW:        appearances >= 3 AND last ≤ 5 days    → 1.10
    3. Stale:      appearances >= 1 AND last > 30 days   → 0.80
    4. Persistent: appearances >= 5                       → 1.05
    5. Neutral:    everything else                        → 1.00
    """
    appearances = count_appearances(ticker, signal_history, lookback_days, reference_date)
    last = days_since_last_appearance(ticker, signal_history, reference_date)

    if appearances == 0:
        return 1.15  # New Kid

    if appearances >= 3 and last is not None and last <= 5:
        return 1.10  # WOW — recurring winner, fresh

    if appearances >= 1 and last is not None and last > 30:
        return 0.80  # Stale — returning after long absence

    if appearances >= 5:
        return 1.05  # Persistent — consistent performer

    return 1.00  # Neutral


def _parse_date(d: str | date) -> date:
    if isinstance(d, date):
        return d
    return date.fromisoformat(d)
