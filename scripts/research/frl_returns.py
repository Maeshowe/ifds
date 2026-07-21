"""FRL — forward return matrix from Polygon grouped-daily bars.

Source decision (FRL-0 V2): the Mini's ``data/cache/polygon`` is empty, so the
return matrix comes from the API. ``get_grouped_daily(date)`` returns the whole
US market for one date in a single cached call, so a ~110-day history costs
~110 calls instead of ~1500 per-ticker aggregate calls.

Returns are close-to-close over *NYSE trading days*: the horizon shift operates
on the ordered trading-day index, so a Friday h=1 return correctly spans the
weekend. Tail days where the horizon runs past the data are NaN, never dropped.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd

import frl_config as cfg

RETURNS_CACHE = cfg.CACHE_DIR / "returns.parquet"
API_CACHE_DIR = cfg.CACHE_DIR / "api"


def research_cache():
    """FileCache rooted under ``research/cache/api``.

    Deliberately NOT the production ``data/cache`` — that directory is inside the
    ``sync_from_mini.sh --delete`` mirror set and a Mini sync would wipe anything
    the research tooling cached there (spec §4.3).
    """
    from ifds.data.cache import FileCache

    API_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return FileCache(cache_dir=str(API_CACHE_DIR))


def closes_from_grouped(
    rows_by_day: Mapping[date, Sequence[Mapping]],
    tickers: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Build a wide close matrix (index=date, columns=ticker) from grouped bars.

    A ticker with no bar on a day stays NaN — never forward-filled, because a
    missing bar means the name did not trade, not that the price held.
    """
    wanted = set(tickers) if tickers is not None else None
    records: dict[date, dict[str, float]] = {}
    for day, rows in rows_by_day.items():
        day_map: dict[str, float] = {}
        for row in rows or ():
            symbol = row.get("T")
            close = row.get("c")
            if symbol is None or close is None:
                continue
            if wanted is not None and symbol not in wanted:
                continue
            day_map[symbol] = float(close)
        records[day] = day_map

    columns = (
        sorted(wanted)
        if wanted is not None
        else sorted({t for day_map in records.values() for t in day_map})
    )
    frame = pd.DataFrame(
        [[records[day].get(col) for col in columns] for day in sorted(records)],
        index=sorted(records),
        columns=columns,
        dtype="float64",
    )
    return frame


def forward_returns(
    closes: pd.DataFrame,
    horizons: Sequence[int] = cfg.IC_HORIZONS,
) -> pd.DataFrame:
    """Long-format forward returns for each horizon.

    Args:
        closes: wide close matrix, index = ordered trading days.
        horizons: forward horizons in trading days.

    Returns:
        Frame with columns ``date``, ``ticker`` and one ``fwd_ret_<h>`` per horizon.
    """
    ordered = closes.sort_index()
    out = (
        ordered.stack(future_stack=True)
        .rename("close")
        .reset_index()
        .rename(columns={"level_0": "date", "level_1": "ticker"})
    )
    out.columns = ["date", "ticker", "close"]

    for h in horizons:
        fwd = ordered.shift(-h) / ordered - 1.0
        melted = fwd.stack(future_stack=True).rename(f"fwd_ret_{h}").reset_index()
        melted.columns = ["date", "ticker", f"fwd_ret_{h}"]
        out = out.merge(melted, on=["date", "ticker"], how="left")

    return out.drop(columns=["close"])


def trailing_returns(
    closes: pd.DataFrame,
    lookbacks: Sequence[int] = (1, 5),
) -> pd.DataFrame:
    """Long-format *trailing* returns — the input side of reversal/momentum factors.

    ``past_ret_k`` at day t is the return over the k trading days ENDING at t, so
    it uses only information available at t. Keeping it in the same matrix as the
    forward returns makes the look-ahead boundary explicit: ``past_*`` may be a
    factor input, ``fwd_*`` may only ever be the target.
    """
    ordered = closes.sort_index()
    frames = []
    for k in lookbacks:
        past = ordered / ordered.shift(k) - 1.0
        melted = past.stack(future_stack=True).rename(f"past_ret_{k}").reset_index()
        melted.columns = ["date", "ticker", f"past_ret_{k}"]
        frames.append(melted.set_index(["date", "ticker"]))
    return pd.concat(frames, axis=1).reset_index()


def fetch_grouped_daily(
    days: Sequence[date],
    client,
) -> dict[date, list[dict]]:
    """Fetch grouped daily bars for ``days`` (one cached API call per day).

    Days the API has no data for (holidays, not-yet-settled sessions) map to an
    empty list, so the caller can tell "no data" from "not requested".
    """
    out: dict[date, list[dict]] = {}
    for day in days:
        rows = client.get_grouped_daily(day.isoformat())
        out[day] = list(rows) if rows else []
    return out


def build_return_matrix(
    start: date,
    end: date,
    client,
    tickers: Iterable[str] | None = None,
    horizons: Sequence[int] = cfg.IC_HORIZONS,
    lookbacks: Sequence[int] = (1, 5),
    cache_path: Path | None = RETURNS_CACHE,
) -> pd.DataFrame:
    """Build (and cache) the forward-return panel for [start, end].

    ``end`` should extend max(horizons) trading days past the last factor day,
    otherwise the final rows carry NaN forward returns by construction.
    """
    from ifds.utils.trading_calendar import trading_days_between

    days = trading_days_between(start, end)
    grouped = fetch_grouped_daily(days, client)
    closes = closes_from_grouped(grouped, tickers)
    frame = forward_returns(closes, horizons).merge(
        trailing_returns(closes, lookbacks), on=["date", "ticker"], how="left"
    )

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(cache_path, index=False)
    return frame


def load_cached_returns(cache_path: Path = RETURNS_CACHE) -> pd.DataFrame | None:
    """Return the cached forward-return panel, or None if absent."""
    if not cache_path.exists():
        return None
    return pd.read_parquet(cache_path)
