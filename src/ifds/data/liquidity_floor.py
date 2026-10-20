"""Deterministic liquidity floor over index membership (D-U2 = (C), 2026-10-20).

The swing universe is index membership, narrowed by a liquidity floor computed HERE
rather than delegated to the FMP screener. Same thresholds, different mechanism, and
the difference is the whole point:

* the screener is a moving set — its raw result swung 2043 -> 1529 (-25%) week on week
  on identical parameters, and intersecting membership with it made the scored panel
  inherit BOTH sources' churn (measured: 226-1479 names week to week, with zero names
  present on every day of the regime);
* this floor is a pure function of bars we already hold, so the same inputs always
  give the same universe.

Why no market-cap floor. ``universe_min_market_cap`` is deliberately NOT applied: the
Russell 1000 is a market-capitalisation ranking by construction, so membership already
encodes it, and market cap is not derivable from OHLCV bars. Dropping it means this
floor is slightly WEAKER than the screener's, which is stated in the report rather
than hidden — a name can pass here and still have had no screener row.

Bars come from Phase 1, which already fetches ~38 sessions of Polygon grouped dailies
for the BMI SMA25. That makes the floor free in API terms. It also means the floor is
unavailable when ``breadth_enabled`` is off, and that must fail loudly, never silently
widen the universe (the failure mode that hid nine weeks of degradation).
"""

from __future__ import annotations

import logging
import statistics
import types
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

logger = logging.getLogger(__name__)

#: Sessions of history used for the average-volume test. Twenty trading days is the
#: conventional ADV window and sits well inside Phase 1's ~38-session fetch.
DEFAULT_LOOKBACK_SESSIONS = 20

#: Exclusion reasons, as stable labels so the report can count them by cause.
REASON_NO_BARS = "no_bars"
REASON_BELOW_PRICE = "below_price"
REASON_BELOW_VOLUME = "below_volume"


@dataclass(frozen=True)
class FloorResult:
    """Which members cleared the floor, and precisely why the rest did not."""

    passed: frozenset[str]
    excluded: tuple[tuple[str, str], ...]
    sessions_used: int
    lookback_requested: int
    #: {ticker: (latest close, median volume)} for the names that passed. Already
    #: computed here, so a caller that must build a record for a name the screener
    #: never returned does not have to re-derive it from the bars.
    metrics: Mapping[str, tuple[float, float]] = types.MappingProxyType({})

    def counts_by_reason(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for _, reason in self.excluded:
            out[reason] = out.get(reason, 0) + 1
        return dict(sorted(out.items()))

    def provenance(self) -> dict:
        """Recorded alongside the membership provenance (D-U1/F-2)."""
        return {
            "definition": "index_union_plus_liquidity_floor",
            "volume_statistic": "median",
            "passed": len(self.passed),
            "excluded": len(self.excluded),
            "excluded_by_reason": self.counts_by_reason(),
            "sessions_used": self.sessions_used,
            "lookback_requested": self.lookback_requested,
        }


def ticker_variants(ticker: str) -> tuple[str, ...]:
    """Every spelling a share-class ticker might carry across providers.

    Polygon writes class shares with a DOT (``BRK.B``); this repo normalises to a
    HYPHEN (``BRK-B``). Measured 2026-10-20: six membership names (BF-A, BF-B, BRK-B,
    HEI-A, LEN-B, UHAL-B) were absent from the bar cache under the hyphen spelling and
    present under the dot. Looking up only one form silently drops them.
    """
    upper = ticker.strip().upper()
    return tuple(dict.fromkeys((upper, upper.replace("-", "."), upper.replace(".", "-"))))


def _session_key(session: Mapping) -> str:
    return str(session.get("date") or "")


def _collect(
    membership: Iterable[str],
    grouped_daily_bars: Sequence[Mapping],
    lookback: int,
) -> tuple[dict[str, list[float]], dict[str, float], int]:
    """Gather per-member volumes and the latest close from the newest sessions."""
    wanted: dict[str, str] = {}
    for ticker in membership:
        for variant in ticker_variants(ticker):
            wanted[variant] = ticker.strip().upper()

    sessions = sorted(
        (s for s in grouped_daily_bars if s.get("bars")), key=_session_key
    )[-lookback:]

    volumes: dict[str, list[float]] = {}
    closes: dict[str, float] = {}
    for index, session in enumerate(sessions):
        is_latest = index == len(sessions) - 1
        for row in session.get("bars") or []:
            raw = str(row.get("T") or "").upper()
            canonical = wanted.get(raw)
            if canonical is None:
                continue
            volume = row.get("v")
            if volume is not None:
                try:
                    volumes.setdefault(canonical, []).append(float(volume))
                except (TypeError, ValueError):
                    pass
            if is_latest and row.get("c") is not None:
                try:
                    closes[canonical] = float(row["c"])
                except (TypeError, ValueError):
                    pass
    return volumes, closes, len(sessions)


def compute_floor(
    membership: Iterable[str],
    grouped_daily_bars: Sequence[Mapping] | None,
    min_price: float,
    min_avg_volume: float,
    lookback: int = DEFAULT_LOOKBACK_SESSIONS,
) -> FloorResult:
    """Narrow ``membership`` to the names clearing the price and ADV thresholds.

    Raises when there are no bars at all: an empty floor would either empty the
    universe or, worse, invite a caller to skip it and widen the universe instead.
    Phase 1 supplies the bars only while ``breadth_enabled`` is on, so this is a real
    configuration path and not a theoretical one.
    """
    members = {t.strip().upper() for t in membership if t and t.strip()}
    if not grouped_daily_bars:
        raise ValueError(
            "Liquidity floor needs Phase 1's grouped daily bars and received none. "
            "Check `breadth_enabled`. Skipping the floor would widen the universe, "
            "which is the failure mode this design exists to prevent."
        )

    volumes, closes, sessions_used = _collect(members, grouped_daily_bars, lookback)

    passed: set[str] = set()
    metrics: dict[str, tuple[float, float]] = {}
    excluded: list[tuple[str, str]] = []
    for ticker in sorted(members):
        series = volumes.get(ticker)
        price = closes.get(ticker)
        if not series or price is None:
            excluded.append((ticker, REASON_NO_BARS))
            continue
        if price < min_price:
            excluded.append((ticker, REASON_BELOW_PRICE))
            continue
        # MEDIAN, not mean. A mean can be carried over the threshold by a single
        # event day — 19 sessions at 1k shares plus one at 100M averages above
        # 500k — and a liquidity floor is supposed to describe typical
        # tradability, not an episode. The median cannot be carried that way by
        # construction. Measured on 2026-10-20 over 1011 members with bars: the
        # mean passes 913 and the median 900, and all 13 of the difference are
        # marginal (medians 444k-483k against the 500k threshold), so the choice
        # costs 1.4% of the universe and buys a structural guarantee.
        #
        # The threshold VALUE is `universe_min_avg_volume` — the same production
        # number — but the statistic is the median, which is why the provenance
        # names it explicitly instead of leaving "avg" to be assumed.
        median_volume = statistics.median(series)
        if median_volume < min_avg_volume:
            excluded.append((ticker, REASON_BELOW_VOLUME))
            continue
        passed.add(ticker)
        metrics[ticker] = (price, median_volume)

    result = FloorResult(
        passed=frozenset(passed),
        excluded=tuple(excluded),
        sessions_used=sessions_used,
        lookback_requested=lookback,
        metrics=types.MappingProxyType(metrics),
    )
    logger.info(
        "Liquidity floor: %d of %d members pass (price >= %.2f, MEDIAN volume >= %.0f "
        "over %d sessions); excluded %s",
        len(passed),
        len(members),
        min_price,
        min_avg_volume,
        sessions_used,
        result.counts_by_reason(),
    )
    return result
