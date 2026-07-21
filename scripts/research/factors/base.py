"""FRL — factor contract and the mandatory per-factor sanity gate (spec §10, R1#6).

A factor is a pure function ``(panel) -> Series`` plus a **synthetic panel on
which the author knows the answer**. Before any attempt runs, the batch computes
the factor on that panel and checks the resulting IC has the declared sign and
enough magnitude.

Why the gate exists: the scarce resource in this loop is the holdout-touch budget
(one per hypothesis, forever — G6). Spending one on a sign-flipped implementation
is the most expensive mistake available, so a bugged factor must never reach the
attempt stage at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

import pandas as pd

MIN_SANITY_IC = 0.30  # the synthetic relation is strong by construction

DATA_LANES = ("v1", "v2")


@dataclass(frozen=True)
class SanityResult:
    """Outcome of a factor's synthetic-panel self-check."""

    factor: str
    passed: bool
    observed_ic: float
    expected_sign: int
    detail: str = ""

    def line(self) -> str:
        status = "PASS" if self.passed else "SANITY_FAIL"
        return (
            f"{status} {self.factor}: ic={self.observed_ic:+.3f} "
            f"expected_sign={self.expected_sign:+d} {self.detail}".rstrip()
        )


@dataclass(frozen=True)
class Factor:
    """A registered, sanity-checkable factor.

    Attributes:
        name: stable identifier, used in the ledger's ``variant`` field.
        hyp_id: the registered hypothesis this factor serves (hypothesis-first).
        data_lane: ``v1`` (historical, testable now) or ``v2`` (forward collection).
        expected_sign: +1 or -1, taken from the hypothesis — declared BEFORE testing.
        compute: ``(panel) -> Series`` aligned to the panel's index.
        sanity_panel: builds a synthetic panel carrying the expected relation,
            including a ``fwd_ret_5`` column.
        description: one line, quoted in the batch report.
    """

    name: str
    hyp_id: str
    data_lane: str
    expected_sign: int
    compute: Callable[[pd.DataFrame], pd.Series]
    sanity_panel: Callable[[], pd.DataFrame]
    description: str = ""

    def __post_init__(self) -> None:
        if self.data_lane not in DATA_LANES:
            raise ValueError(f"{self.name}: data_lane must be one of {DATA_LANES}")
        if self.expected_sign not in (-1, 1):
            raise ValueError(f"{self.name}: expected_sign must be +1 or -1")


def run_sanity(factor: Factor, min_ic: float = MIN_SANITY_IC) -> SanityResult:
    """Run the factor against its own synthetic panel.

    Fails closed: any exception inside ``compute`` is a SANITY_FAIL, not a crash
    that aborts the batch.
    """
    import frl_ic

    try:
        panel = factor.sanity_panel().copy()
        values = factor.compute(panel)
        panel["_factor"] = pd.Series(values).to_numpy()
        ic_series = frl_ic.daily_ic(panel, "_factor", "fwd_ret_5", min_sector_n=3)
        observed = float(ic_series.mean())
    except Exception as exc:  # noqa: BLE001 — the gate must never propagate
        return SanityResult(
            factor.name,
            False,
            float("nan"),
            factor.expected_sign,
            f"exception: {type(exc).__name__}: {exc}",
        )

    if pd.isna(observed):
        return SanityResult(
            factor.name,
            False,
            float("nan"),
            factor.expected_sign,
            "IC undefined on the synthetic panel",
        )

    sign_ok = (observed > 0) == (factor.expected_sign > 0)
    strong_enough = abs(observed) >= min_ic
    detail = ""
    if not sign_ok:
        detail = "sign mismatch — implementation likely inverted"
    elif not strong_enough:
        detail = f"|ic| below {min_ic:.2f} on a synthetic panel with a known relation"

    return SanityResult(
        factor=factor.name,
        passed=sign_ok and strong_enough,
        observed_ic=observed,
        expected_sign=factor.expected_sign,
        detail=detail,
    )


def linear_sanity_panel(
    column: str,
    sign: int,
    n_days: int = 6,
    n_per_sector: int = 8,
    sectors: tuple[str, ...] = ("Tech", "Health"),
    start: date = date(2026, 6, 1),
) -> Callable[[], pd.DataFrame]:
    """Build a sanity-panel factory where ``column`` drives the forward return.

    Useful for factors that are a monotone transform of a single panel column.
    Factors with richer inputs (multi-day OHLCV, cross-sectional context) must
    supply their own builder.
    """

    def build() -> pd.DataFrame:
        rows = []
        for d in range(n_days):
            day = start + timedelta(days=d)
            for sector in sectors:
                for i in range(n_per_sector):
                    level = float(i)
                    rows.append(
                        {
                            "date": day,
                            "ticker": f"{sector[:2]}{i}",
                            "sector": sector,
                            column: level,
                            "fwd_ret_5": sign * level * 0.01,
                        }
                    )
        return pd.DataFrame(rows)

    return build


_REGISTRY: dict[str, Factor] = {}


def register(factor: Factor) -> Factor:
    """Register a factor by name (duplicate names are a hard error)."""
    if factor.name in _REGISTRY:
        raise ValueError(f"duplicate factor name: {factor.name}")
    _REGISTRY[factor.name] = factor
    return factor


def get(name: str) -> Factor:
    if name not in _REGISTRY:
        raise KeyError(f"unknown factor: {name} (registered: {sorted(_REGISTRY)})")
    return _REGISTRY[name]


def all_factors() -> list[Factor]:
    return [_REGISTRY[k] for k in sorted(_REGISTRY)]


def for_hypothesis(hyp_id: str) -> list[Factor]:
    return [f for f in all_factors() if f.hyp_id == hyp_id]


def clear_registry() -> None:
    """Test helper — drop all registrations."""
    _REGISTRY.clear()
