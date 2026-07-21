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

# --- Statistics -------------------------------------------------------------
HOLDOUT_WEEKS: Final[int] = 4  # D_B
HOLDOUT_PURGE_DAYS: Final[int] = 5  # h=5 forward-return overlap at the boundary
FDR_Q: Final[float] = 0.10  # D_C
IC_HORIZONS: Final[tuple[int, ...]] = (1, 3, 5, 7)
PRIMARY_HORIZON: Final[int] = 5
MIN_SECTOR_N: Final[int] = 5  # sectors with fewer names are dropped that day
ERA_BAR_FLOOR: Final[float] = 0.02  # era_bar = max(floor, 2 * SE(mean IC))

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

# --- Known coverage gaps (spec §4.5) ----------------------------------------
# Explicitly missing days — NEVER interpolated, always NaN in the IC series.
KNOWN_GAPS: Final[tuple[tuple[date, date], ...]] = (
    (date(2026, 6, 29), date(2026, 7, 6)),  # Mini SSH-orphan outage
    (date(2026, 7, 15), date(2026, 7, 16)),  # power outage
)


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
