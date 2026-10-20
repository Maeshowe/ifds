"""FRL — central configuration constants (freeze-safe, read-only research tooling).

Single source of truth for the Factor Research Loop. Spec:
``docs/design/2026-07-21-factor-research-loop-spec.md``.

Decisions encoded here:
  * D_B = 4 weeks rolling holdout (spec §7, review consensus)
  * D_C = q 0.10 Benjamini-Hochberg FDR (spec §5.4, review consensus)

Era boundaries are empirically verified by the FRL-0 gate report
(``docs/tasks/2026-07-21-frl-scan-matrix-loader.md`` §Eredmény): 2026-05-15 is the
last legacy-composite scan day, 2026-05-18 the first swing S_j day. No mixed day
exists in the 102-day history.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

# --- Directories ------------------------------------------------------------
# `research/` is a NEW top-level dir deliberately OUTSIDE the sync_from_mini.sh
# --delete mirror set (spec §4.3) — otherwise the next Mini sync would delete it.
RESEARCH_DIR: Final[Path] = PROJECT_ROOT / "research"
CACHE_DIR: Final[Path] = RESEARCH_DIR / "cache"
RUNS_DIR: Final[Path] = RESEARCH_DIR / "runs"
LEDGER_PATH: Final[Path] = RESEARCH_DIR / "attempt_ledger.jsonl"
COST_MODEL_PATH: Final[Path] = RESEARCH_DIR / "cost_model.json"

SCAN_MATRIX_DIR: Final[Path] = PROJECT_ROOT / "output"
EVENT_LOG_DIR: Final[Path] = PROJECT_ROOT / "logs"
DAILY_METRICS_DIR: Final[Path] = PROJECT_ROOT / "state" / "daily_metrics"

# --- Eras (spec §5.2 G5) ----------------------------------------------------
LEGACY_START: Final[date] = date(2026, 2, 11)
LEGACY_END: Final[date] = date(2026, 5, 15)
SWING_START: Final[date] = date(2026, 5, 18)

ERA_LEGACY: Final[str] = "legacy"
ERA_SWING: Final[str] = "swing"

# --- Universe regimes (D-U3, approved 2026-10-20) ---------------------------
# The swing era ran on THREE different universe definitions. G5 forbids pooling
# across eras; this is the same hazard INSIDE one era, and nothing recorded it, so
# it went unnoticed for nine weeks.
#
# Measured panel sizes per regime (the scored panel, not the raw membership):
#   1. screener ∩ index-union : 226-1479 week to week, and ZERO names present on
#      every day of the regime — the intersection inherited both sources' churn.
#   2. screener only          : 1338-1824. A silent degradation: the membership
#      source died on 2026-08-12 and Phase 2 fell open, swapping 377 of 730 names
#      (52%) for non-members.
#   3. index-union ∩ floor    : 909, and DETERMINISTIC — a pure function of
#      completed daily bars, immune both to the screener's composition and to the
#      hour of day (the old `volumeMoreThan` filtered today's PARTIAL volume).
#
# Tamás's decision (2026-10-20), the strict option of two: a new attempt may use
# ONLY regime-3 data. The alternative was to permit mixtures with a declared
# blend ratio, which is weaker — regime 3 is the only one whose universe is
# reproducible, so an attempt spanning regimes is not comparable to one that does
# not, whatever ratio is reported.
#
# THE PRICE, measured, so it cannot surprise anyone later. T_eff = n_days/h must
# reach MIN_ADEQUATE_T_EFF (6.0), and the forward return consumes h more sessions:
#   h=1  -> 2026-10-28      h=5  -> 2026-12-08      h=10 -> 2027-01-29
#   h=3  -> 2026-11-17      h=7  -> 2026-12-29      h=20 -> 2027-05-11
# Until those dates a new attempt at that horizon PARKs on power, it does not KILL.
UNIVERSE_REGIME_INTERSECT: Final[str] = "screener_intersect_index"
UNIVERSE_REGIME_SCREENER: Final[str] = "screener_only_degraded"
UNIVERSE_REGIME_FLOOR: Final[str] = "index_union_plus_liquidity_floor"

#: (first day, regime label). Open-ended at the end; sorted by start date.
UNIVERSE_REGIMES: Final[tuple[tuple[date, str], ...]] = (
    (date(2026, 5, 18), UNIVERSE_REGIME_INTERSECT),
    (date(2026, 8, 16), UNIVERSE_REGIME_SCREENER),
    (date(2026, 10, 20), UNIVERSE_REGIME_FLOOR),
)

#: The only regime a new attempt may draw from (D-U3). Named, not computed, for the
#: same reason DAY63_GATE_PASSED is a flag: a derived "current" value would silently
#: follow a future regime change that nobody approved.
CURRENT_UNIVERSE_REGIME: Final[str] = UNIVERSE_REGIME_FLOOR


def universe_regime_of(day: date) -> str | None:
    """The universe definition in force on ``day``, or None before the swing era.

    Mirrors :func:`era_of`. Returns None rather than guessing for days before the
    first regime, so a caller cannot silently treat pre-era data as current.
    """
    label: str | None = None
    for start, name in UNIVERSE_REGIMES:
        if day >= start:
            label = name
        else:
            break
    return label


def regime_start(label: str) -> date | None:
    """The first day of a named universe regime, or None if the name is unknown."""
    for start, name in UNIVERSE_REGIMES:
        if name == label:
            return start
    return None


def regime_span(days: "list[date] | tuple[date, ...]") -> dict[str, int]:
    """``{regime: n_days}`` over ``days`` — the blend a panel actually contains.

    Reported even when a panel is single-regime, because "I checked and it was
    clean" and "nobody checked" must not look the same in the record.
    """
    out: dict[str, int] = {}
    for day in days:
        label = universe_regime_of(day) or "pre_era"
        out[label] = out.get(label, 0) + 1
    return dict(sorted(out.items()))


# --- Statistics -------------------------------------------------------------
HOLDOUT_WEEKS: Final[int] = 4  # D_B
HOLDOUT_PURGE_DAYS: Final[int] = 5  # h=5 forward-return overlap at the boundary
FDR_Q: Final[float] = 0.10  # D_C
IC_HORIZONS: Final[tuple[int, ...]] = (1, 3, 5, 7)

# Long horizons registered for SPECIFIC hypotheses by pre-registered amendment.
# Keyed by hyp_id so the engine cannot quietly run an unregistered horizon on a
# DIFFERENT hypothesis — the gap is closed, not the instance.
#
# HYP-007 (Funda block): measured half-life 799.8 days (rank autocorrelation
# rho = 0.999, independently verified), so h<=7 is 0.9% of the factor's own time
# scale. The half-life is the factor's autocorrelation — mathematically
# independent of returns — and was measured BEFORE any IC for this hypothesis,
# so fitting the grid to the measured time scale is pre-registration, not tuning.
# Source: docs/planning/2026-10-04-component-decomposition-preregistration.md
#         AMENDMENT-1 §A-1.2. Accepted by Tamás 2026-10-04.
LONG_HORIZONS_BY_HYPOTHESIS: Final[dict[str, tuple[int, ...]]] = {
    "HYP-007": (10, 20, 60),
}
PRIMARY_HORIZON: Final[int] = 5
MIN_SECTOR_N: Final[int] = 5  # sectors with fewer names are dropped that day
ERA_BAR_FLOOR: Final[float] = 0.02  # era_bar = max(floor, 2 * SE(mean IC))

# Effective-sample adequacy floor for a terminal KILL (spec §5.5). Below this
# T_eff the power analysis says even a moderate IC (~0.08) is undetectable, so a
# family-p fail there is "underpowered", not "no signal" — it PARKs and retests as
# the swing sample grows, rather than dying. At or above it, a clean fail is a
# genuine null and KILLs. This makes pre-reg criteria (a) vs (c) machine-enforced.
#
# Pinned at 6 = the §5.5 detectability threshold, NOT tuned to any result. On the
# HYP-005 batch the family verdict is stable for floor ∈ [5, 7] (h1/h3 KILL,
# h5/h7 PARK); it only flips at 4 (h5→KILL) or 8 (h3→PARK). 6 sits mid-band.
MIN_ADEQUATE_T_EFF: Final[float] = 6.0

# --- Day 63 gate ------------------------------------------------------------
# EXPLICIT FLAG, never a computed date. Only a Tamás decision flips this to True.
#
# Why not a date: the NYSE calendar puts the 63rd trading day after the swing
# pivot at 2026-08-17, but the pipeline's own day counter showed 37 on 2026-07-20
# against 43 NYSE days — the outage/orphan days are excluded from the edge sample
# (04-risks §11.10), and the gate is about 63 days of *actual edge sample*, not
# the 63rd calendar trading day. The working target is ≈2026-09-15 (W37). While
# the trading-days invariant is an open Dev item, every date derivation is
# ambivalent; a flag cannot err in the permissive direction.
DAY63_GATE_PASSED: Final[bool] = False
DAY63_NYSE_DATE_INFORMATIVE: Final[date] = date(2026, 8, 17)  # informational only

# --- Cost model (spec §5.3, R1#3) -------------------------------------------
# Fallback only — the real value comes from build_cost_model() over the observed
# |slippage| distribution. 3 bp-class assumptions are FORBIDDEN for this
# execution style (next-day MKT open).
FALLBACK_COST_BPS_PER_SIDE: Final[float] = 75.0
COST_MODEL_MIN_N: Final[int] = 30  # below this the model carries a small-n warning

# --- Two-sided signed cost estimator ----------------------------------------
# Pre-reg: docs/planning/2026-10-19-cost-estimator-amendment.md (D-C1..D-C4,
# approved 2026-10-19) as corrected by its own ERRATA (D-E1..D-E6, approved
# 2026-10-19). The estimator charges TRUE FRICTION ONLY — the fill against the
# price available at the moment of trading — and adds the two sides rather than
# doubling the entry. Every engine constant below is registered HERE, because
# the approved text left them unspecified (ERRATA §E-7) and an unregistered
# bootstrap parameter is a free parameter on the binding threshold.
PENDING_EXITS_DIR: Final[Path] = PROJECT_ROOT / "state" / "pending_exits"
BARS_DIR: Final[Path] = CACHE_DIR / "api" / "polygon" / "grouped_daily"
ENTRY_BACKFILL_PATH: Final[Path] = (
    PROJECT_ROOT / "scripts" / "maintenance" / "slippage_backfill_map.json"
)

# A fill outside its own session's range is a ticker/corporate-action mismatch or
# a mis-dated row, not an execution cost. Registered per ERRATA §E-5 (D-E3): it is
# a post-hoc exclusion moving the estimate in the PERMISSIVE direction, so it
# carries the full companion set and its sensitivity is published in the report.
FILL_IN_BAR_TOLERANCE: Final[float] = 0.005

# One-sided upper confidence bound on the MEAN (pre-reg §4: the uncertainty lives
# in the central value, not in a per-trade quantile). Day-clustered because fills
# cluster within a session; seeded because a persisted cost model must be
# reproducible bit-for-bit.
COST_UCB_CONFIDENCE: Final[float] = 0.95
COST_BOOTSTRAP_REPLICATES: Final[int] = 20_000
COST_BOOTSTRAP_SEED: Final[int] = 20_261_019

# Degeneracy floor for the round trip. The old median(|slippage|) estimator was
# non-negative by construction; a SIGNED mean is not, and a non-positive round
# trip would make breakeven_ic <= 0 and open the (e) gate for every factor.
# Tolerance-based per the house rule, never `== 0`.
MIN_ROUND_TRIP_BPS: Final[float] = 1.0

# --- Known coverage gaps (spec §4.5) ----------------------------------------
# Explicitly missing days — NEVER interpolated, always NaN in the IC series.
# Each entry names its source, because the batch report separates DOCUMENTED gaps
# from unexpected ones precisely so a GENUINE new gap stays visible. A stale list
# makes the report cry wolf on known outages, and a real gap then hides among
# them — the signal-to-noise of that warning is what this list protects.
# Coverage is regression-tested in tests/test_frl_loader.py::TestKnownGapsCoverage.
KNOWN_GAPS: Final[tuple[tuple[date, date], ...]] = (
    # pipeline down while the market traded — OHLCV backfill task §1.2
    (date(2026, 4, 6), date(2026, 4, 7)),
    (date(2026, 6, 29), date(2026, 7, 6)),  # Mini SSH-orphan outage
    (date(2026, 7, 15), date(2026, 7, 16)),  # power outage
    (date(2026, 7, 22), date(2026, 7, 22)),  # FileVault outage — 04-risks §11.16
    # FileVault outage — docs/review/2026-W32-weekly-close.md (Day 57)
    (date(2026, 8, 7), date(2026, 8, 7)),
    # booted machine, SSH green, but cron only started at console login — §11.16.
    # SSH reachability is NOT a health signal for the cron chain.
    (date(2026, 8, 21), date(2026, 8, 21)),
)


def allowed_horizons(hyp_id: str | None = None) -> tuple[int, ...]:
    """Horizons this hypothesis may be tested at (default grid + its amendments).

    An unnamed hypothesis gets the default pre-registered grid only, so a run
    that forgets ``--hyp`` cannot reach an amended horizon.
    """
    extra = LONG_HORIZONS_BY_HYPOTHESIS.get(hyp_id or "", ())
    return tuple(sorted(set(IC_HORIZONS) | set(extra)))


def era_of(day: date) -> str | None:
    """Return the era label for ``day``, or None outside both eras.

    The 05-16/05-17 weekend gap between the eras yields None, as does any date
    before LEGACY_START.
    """
    if LEGACY_START <= day <= LEGACY_END:
        return ERA_LEGACY
    if day >= SWING_START:
        return ERA_SWING
    return None


def is_known_gap(day: date) -> bool:
    """True if ``day`` falls inside a documented coverage gap (spec §4.5)."""
    return any(start <= day <= end for start, end in KNOWN_GAPS)
