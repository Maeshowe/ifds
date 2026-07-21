"""FRL — IC engine: daily sector-neutral Spearman IC, HAC aggregation, half-life.

Spec §5. Every number here is **descriptive** (G1/G3): no signal-validity claim
is made or implied by this module.

Newey-West is implemented in-house on purpose: ``statsmodels`` is not a project
dependency and the Day 63 freeze forbids adding one to production requirements.
The implementation is validated against statsmodels in ``tests/test_frl_ic.py``
(skipped when the dev-only package is absent).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Sequence

import pandas as pd

import frl_config as cfg

# Ranks that vary by less than this are treated as constant (see daily_ic).
_RANK_STD_EPS = 1e-12


# ---------------------------------------------------------------------------
# Daily cross-sectional IC
# ---------------------------------------------------------------------------


def _within_sector_ranks(frame: pd.DataFrame, col: str) -> pd.Series:
    """Normalized (0..1) ranks of ``col`` computed inside each sector."""
    return frame.groupby("sector")[col].rank(pct=True)


def daily_ic(
    panel: pd.DataFrame,
    factor_col: str,
    return_col: str,
    min_sector_n: int = cfg.MIN_SECTOR_N,
) -> pd.Series:
    """Daily sector-neutral rank IC.

    Within each sector the factor and the forward return are converted to
    normalized ranks; ranking inside the sector *is* the sector-relative
    transform (a monotone shift by the sector mean cannot change within-sector
    ranks). The day's IC is the correlation of the pooled within-sector ranks,
    so every sector contributes on a common scale.

    Sectors with fewer than ``min_sector_n`` usable names that day are dropped;
    days left with fewer than two sectors or two names yield NaN — never 0.0.

    Returns:
        Series indexed by date (ascending), NaN on days without enough data.
    """
    needed = {"date", "sector", factor_col, return_col}
    missing = needed - set(panel.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")

    usable = panel.dropna(subset=[factor_col, return_col, "sector"])
    out: dict = {}

    for day, day_frame in usable.groupby("date", sort=True):
        counts = day_frame.groupby("sector")[factor_col].transform("size")
        kept = day_frame[counts >= min_sector_n]
        if len(kept) < 2 or kept["sector"].nunique() < 1:
            out[day] = float("nan")
            continue
        fr = _within_sector_ranks(kept, factor_col)
        rr = _within_sector_ranks(kept, return_col)
        # Degenerate-rank guard with a tolerance, not `== 0`: a factor that is
        # constant *inside* every sector yields identical pct-ranks whose std is
        # ~1e-16 rather than exactly 0, and pandas' corr on two such series
        # returns a spurious 1.0. That would score a pure sector bet as a
        # perfect sector-neutral signal.
        if fr.std(ddof=0) < _RANK_STD_EPS or rr.std(ddof=0) < _RANK_STD_EPS:
            out[day] = float("nan")
            continue
        out[day] = float(fr.corr(rr))

    return pd.Series(out, name=f"ic_{factor_col}").sort_index()


def dropped_sector_report(
    panel: pd.DataFrame,
    factor_col: str,
    return_col: str,
    min_sector_n: int = cfg.MIN_SECTOR_N,
) -> pd.DataFrame:
    """Per-day count of sectors dropped for thin coverage (reported, not hidden)."""
    usable = panel.dropna(subset=[factor_col, return_col, "sector"])
    rows = []
    for day, day_frame in usable.groupby("date", sort=True):
        sizes = day_frame.groupby("sector").size()
        rows.append(
            {
                "date": day,
                "sectors_total": int(len(sizes)),
                "sectors_dropped": int((sizes < min_sector_n).sum()),
                "names_dropped": int(sizes[sizes < min_sector_n].sum()),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Newey-West HAC standard error of the mean
# ---------------------------------------------------------------------------


def newey_west_se(values: Sequence[float] | pd.Series, lag: int) -> float:
    """HAC (Newey-West, Bartlett kernel) standard error of the sample mean.

    ``lag`` should be h-1 for an h-day overlapping forward return: consecutive
    IC observations share h-1 days of return, so the autocorrelation runs that
    far by construction.
    """
    series = pd.Series(values, dtype="float64").dropna()
    n = len(series)
    if n < 2:
        return float("nan")

    centered = (series - series.mean()).to_numpy()
    lag = max(0, min(int(lag), n - 1))

    gamma0 = float((centered * centered).sum() / n)
    total = gamma0
    for j in range(1, lag + 1):
        weight = 1.0 - j / (lag + 1.0)
        gamma_j = float((centered[j:] * centered[:-j]).sum() / n)
        total += 2.0 * weight * gamma_j

    if total <= 0:  # HAC estimate can go non-positive on tiny samples
        return float("nan")
    return math.sqrt(total / n)


def _two_sided_p(t_stat: float, df: int) -> float:
    if not math.isfinite(t_stat) or df < 1:
        return float("nan")
    from scipy import stats

    return float(2.0 * stats.t.sf(abs(t_stat), df))


@dataclass(frozen=True)
class ICSummary:
    """Aggregated IC statistics for one factor / horizon / era."""

    era: str
    horizon: int
    n_days: int
    t_eff: float
    mean_ic: float
    std_ic: float
    icir: float
    nw_se: float
    nw_t: float
    p_value: float
    era_bar: float
    nonoverlap_mean_ic: float
    nonoverlap_n: int
    inconclusive: bool

    def to_dict(self) -> dict:
        return asdict(self)


def era_bar(ic_series: pd.Series, horizon: int) -> float:
    """Era-qualified detectability bar: ``max(0.02, 2 * SE(mean IC))`` (R1#2).

    Computed from the run-time effective sample, so it loosens automatically as
    the swing sample grows — no manual re-tuning, and no fixed threshold that
    silently contradicts the power analysis.
    """
    se = newey_west_se(ic_series, lag=horizon - 1)
    if not math.isfinite(se):
        return float("inf")
    return max(cfg.ERA_BAR_FLOOR, 2.0 * se)


def aggregate(ic_series: pd.Series, horizon: int, era: str) -> ICSummary:
    """Aggregate a daily IC series into the reported statistics (spec §5.2)."""
    clean = pd.Series(ic_series, dtype="float64").dropna().sort_index()
    n = len(clean)
    if n == 0:
        return ICSummary(
            era=era,
            horizon=horizon,
            n_days=0,
            t_eff=0.0,
            mean_ic=float("nan"),
            std_ic=float("nan"),
            icir=float("nan"),
            nw_se=float("nan"),
            nw_t=float("nan"),
            p_value=float("nan"),
            era_bar=float("inf"),
            nonoverlap_mean_ic=float("nan"),
            nonoverlap_n=0,
            inconclusive=True,
        )

    mean_ic = float(clean.mean())
    std_ic = float(clean.std(ddof=1)) if n > 1 else float("nan")
    icir = mean_ic / std_ic if std_ic and math.isfinite(std_ic) and std_ic > 0 else float("nan")

    se = newey_west_se(clean, lag=horizon - 1)
    t_stat = mean_ic / se if se and math.isfinite(se) and se > 0 else float("nan")
    # Effective sample size under h-day overlap (spec §5.5).
    t_eff = n / horizon if horizon > 0 else float(n)
    p = _two_sided_p(t_stat, df=max(1, int(round(t_eff)) - 1))

    nonoverlap = clean.iloc[::horizon] if horizon > 0 else clean
    bar = era_bar(clean, horizon)

    return ICSummary(
        era=era,
        horizon=horizon,
        n_days=n,
        t_eff=round(t_eff, 2),
        mean_ic=mean_ic,
        std_ic=std_ic,
        icir=icir,
        nw_se=se,
        nw_t=t_stat,
        p_value=p,
        era_bar=bar,
        nonoverlap_mean_ic=float(nonoverlap.mean()),
        nonoverlap_n=int(len(nonoverlap)),
        inconclusive=abs(mean_ic) < bar,
    )


# ---------------------------------------------------------------------------
# Persistence / turnover (cost gate, NOT a kill gate — spec §5.3)
# ---------------------------------------------------------------------------


def rank_autocorrelation(panel: pd.DataFrame, factor_col: str) -> float:
    """Mean day-over-day cross-sectional rank autocorrelation of the factor."""
    per_day = {
        day: frame.set_index("ticker")[factor_col].dropna()
        for day, frame in panel.groupby("date", sort=True)
    }
    days = sorted(per_day)
    values: list[float] = []
    for prev, curr in zip(days, days[1:]):
        joined = pd.concat(
            [per_day[prev].rename("prev"), per_day[curr].rename("curr")],
            axis=1,
            join="inner",
        )
        if len(joined) < 3:
            continue
        rho = joined["prev"].rank().corr(joined["curr"].rank())
        if pd.notna(rho):
            values.append(float(rho))
    return float(sum(values) / len(values)) if values else float("nan")


def half_life(panel: pd.DataFrame, factor_col: str) -> float:
    """AR(1) half-life in trading days from the mean rank autocorrelation.

    Note (FRL-0 finding #5): the swing score column is already EWMA(5)-smoothed,
    so its half-life measures the smoothing as much as the underlying signal's
    persistence. The batch report must say so.
    """
    rho = rank_autocorrelation(panel, factor_col)
    if not math.isfinite(rho) or rho <= 0 or rho >= 1:
        return float("inf") if rho >= 1 else float("nan")
    return -math.log(2) / math.log(rho)


def cross_sectional_sigma(panel: pd.DataFrame, return_col: str) -> float:
    """Mean daily cross-sectional standard deviation of the forward return."""
    per_day = panel.groupby("date")[return_col].std(ddof=1)
    value = float(per_day.mean())
    return value if math.isfinite(value) else float("nan")


@dataclass(frozen=True)
class CostedView:
    """Gross vs cost-charged view of a factor (spec §5.3).

    Deliberately explicit about its one modelling assumption: a dollar-neutral
    portfolio weighted by the normalized factor score earns approximately
    ``IC × σ_cs`` per horizon (the standard Grinold approximation). Everything
    else — the per-side cost and the turnover — is empirical.

    ``breakeven_ic`` is the honest headline: the |IC| this factor would need
    before it pays for its own trading at the observed slippage.
    """

    horizon: int
    mean_ic: float
    sigma_cs: float
    periods_per_year: float
    gross_annual_bps: float
    cost_annual_bps: float
    net_annual_bps: float
    breakeven_ic: float

    @property
    def survives_cost(self) -> bool:
        return math.isfinite(self.net_annual_bps) and self.net_annual_bps > 0

    def to_dict(self) -> dict:
        return asdict(self) | {"survives_cost": self.survives_cost}


def costed_view(
    mean_ic: float,
    sigma_cs: float,
    horizon: int,
    cost_annual_bps: float,
    trading_days_per_year: int = 252,
) -> CostedView:
    """Charge the empirical trading cost against the factor's gross IC."""
    periods = trading_days_per_year / horizon if horizon > 0 else float("nan")
    gross = abs(mean_ic) * sigma_cs * periods * 10_000.0
    net = gross - cost_annual_bps
    denominator = sigma_cs * periods * 10_000.0
    breakeven = cost_annual_bps / denominator if denominator else float("inf")
    return CostedView(
        horizon=horizon,
        mean_ic=mean_ic,
        sigma_cs=sigma_cs,
        periods_per_year=periods,
        gross_annual_bps=gross,
        cost_annual_bps=cost_annual_bps,
        net_annual_bps=net,
        breakeven_ic=breakeven,
    )


def implied_turnover_cost_bps(
    half_life_days: float,
    cost_bps_per_side: float,
    trading_days_per_year: int = 252,
) -> float:
    """Annual cost drag implied by the factor's turnover and the empirical cost.

    One full round trip is assumed per half-life (the horizon over which the
    cross-sectional ranking substantially re-orders).
    """
    if not math.isfinite(half_life_days) or half_life_days <= 0:
        return float("nan")
    round_trips = trading_days_per_year / half_life_days
    return round_trips * 2.0 * cost_bps_per_side
