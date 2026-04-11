"""VWAP Module — Volume Weighted Average Price for entry quality filtering.

Calculates intraday VWAP from Polygon 5-minute bars and provides
an entry quality check against the planned limit price.

Entry quality levels:
- REJECT:  price > VWAP + 2%  — too far above fair value
- REDUCE:  price > VWAP + 1%  — slightly stretched
- NORMAL:  within ±1% of VWAP — acceptable
- BOOST:   price < VWAP - 1%  — discount entry
"""

from __future__ import annotations

from datetime import date


def calculate_vwap(bars_5min: list[dict]) -> float:
    """Calculate VWAP from intraday 5-minute bars.

    VWAP = Σ(typical_price × volume) / Σ(volume)
    typical_price = (high + low + close) / 3

    Parameters
    ----------
    bars_5min:
        List of bar dicts with keys ``h``, ``l``, ``c``, ``v``.
        Zero-volume bars are skipped.

    Returns
    -------
    float
        VWAP value, or 0.0 if no valid bars.
    """
    total_tp_vol = 0.0
    total_vol = 0.0

    for bar in bars_5min:
        vol = bar.get("v", 0)
        if vol <= 0:
            continue
        typical_price = (bar["h"] + bar["l"] + bar["c"]) / 3
        total_tp_vol += typical_price * vol
        total_vol += vol

    if total_vol <= 0:
        return 0.0

    return round(total_tp_vol / total_vol, 4)


def vwap_entry_check(
    current_price: float,
    vwap: float,
    reject_pct: float = 2.0,
    reduce_pct: float = 1.0,
    boost_pct: float = -1.0,
) -> str:
    """Check entry quality relative to VWAP.

    Parameters
    ----------
    current_price:
        Planned entry / current market price.
    vwap:
        Calculated VWAP for the day.
    reject_pct:
        Distance above VWAP (%) to reject entry.
    reduce_pct:
        Distance above VWAP (%) to reduce position.
    boost_pct:
        Distance below VWAP (%) to boost position (negative = below).

    Returns
    -------
    str
        ``"REJECT"`` | ``"REDUCE"`` | ``"BOOST"`` | ``"NORMAL"``
    """
    if vwap <= 0 or current_price <= 0:
        return "NORMAL"

    distance_pct = (current_price - vwap) / vwap * 100

    if distance_pct > reject_pct:
        return "REJECT"
    # BC23: REDUCE removed — binary decision (REJECT or PASS)
    if distance_pct < boost_pct:
        return "BOOST"
    return "NORMAL"


def vwap_distance_pct(current_price: float, vwap: float) -> float:
    """Calculate distance from VWAP as percentage."""
    if vwap <= 0:
        return 0.0
    return round((current_price - vwap) / vwap * 100, 2)


async def fetch_intraday_vwap(
    polygon_client: object,
    tickers: list[str],
    date_str: str | None = None,
) -> dict[str, float]:
    """Fetch 5-min bars and calculate VWAP for multiple tickers.

    Uses the existing Polygon ``get_aggregates`` method with
    ``timespan="minute"``, ``multiplier=5``.

    Parameters
    ----------
    polygon_client:
        AsyncPolygonClient (or sync PolygonClient with get_aggregates).
    tickers:
        List of ticker symbols.
    date_str:
        Date in ISO format (default: today).

    Returns
    -------
    dict[str, float]
        ``{ticker: vwap_value}`` for tickers with available data.
    """
    if date_str is None:
        date_str = date.today().isoformat()

    import asyncio

    results: dict[str, float] = {}

    async def _fetch_one(ticker: str) -> None:
        try:
            bars = await polygon_client.get_aggregates(
                ticker, date_str, date_str,
                timespan="minute", multiplier=5,
            )
            if bars:
                vwap = calculate_vwap(bars)
                if vwap > 0:
                    results[ticker] = vwap
        except Exception:
            pass  # Skip tickers with no intraday data

    await asyncio.gather(*[_fetch_one(t) for t in tickers])

    return results
