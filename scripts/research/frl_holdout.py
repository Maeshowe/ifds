"""FRL — rolling embargoed holdout, PROMOTE criteria, PARK auto-retest (spec §5.4, §7).

The holdout is the loop's scarcest resource: one touch per hypothesis, forever
(G6). Everything here exists to make spending a touch deliberate and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Mapping

import frl_config as cfg


@dataclass(frozen=True)
class Windows:
    """The dev / purge / holdout split in effect for one batch run."""

    dev_start: date
    dev_end: date
    purge_start: date
    purge_end: date
    holdout_start: date
    holdout_end: date

    def describe(self) -> str:
        return (
            f"dev {self.dev_start}..{self.dev_end} | "
            f"purge {self.purge_start}..{self.purge_end} | "
            f"holdout {self.holdout_start}..{self.holdout_end}"
        )


def compute_windows(
    last_day: date,
    first_day: date = cfg.SWING_START,
    weeks: int = cfg.HOLDOUT_WEEKS,
    purge_days: int = cfg.HOLDOUT_PURGE_DAYS,
) -> Windows:
    """Split [first_day, last_day] into dev / purge / holdout.

    The holdout is the trailing ``weeks`` calendar weeks. Between dev and holdout
    sits a ``purge_days``-trading-day gap: with h=5 forward returns, factor days
    immediately before the boundary would otherwise carry returns realised inside
    the holdout.
    """
    from ifds.utils.trading_calendar import trading_days_between

    holdout_start = last_day - timedelta(weeks=weeks) + timedelta(days=1)
    days = trading_days_between(first_day, last_day)
    holdout_days = [d for d in days if d >= holdout_start]
    pre_holdout = [d for d in days if d < holdout_start]

    if not holdout_days:
        raise ValueError(f"no trading days in the holdout window ending {last_day}")

    purge = pre_holdout[-purge_days:] if pre_holdout else []
    dev = pre_holdout[:-purge_days] if len(pre_holdout) > purge_days else []

    return Windows(
        dev_start=dev[0] if dev else first_day,
        dev_end=dev[-1] if dev else first_day,
        purge_start=purge[0] if purge else holdout_days[0],
        purge_end=purge[-1] if purge else holdout_days[0],
        holdout_start=holdout_days[0],
        holdout_end=holdout_days[-1],
    )


class HoldoutTouchError(RuntimeError):
    """Raised when a hypothesis tries to touch the holdout a second time (G6)."""


def touches(hyp_id: str, entries: Iterable[dict]) -> int:
    """How many times ``hyp_id`` has already touched the holdout."""
    return sum(
        1 for entry in entries if entry.get("hyp_id") == hyp_id and entry.get("holdout_touched")
    )


def assert_untouched(hyp_id: str, entries: Iterable[dict]) -> None:
    """Hard-fail if the hypothesis already spent its single holdout touch."""
    used = touches(hyp_id, entries)
    if used:
        raise HoldoutTouchError(
            f"{hyp_id} already touched the holdout {used}x — one touch per "
            "hypothesis, forever (G6). Failure there means the hypothesis is dead."
        )


def holdout_congestion(entries: Iterable[dict], holdout_start: date) -> int:
    """Distinct hypotheses that have touched the *current* holdout window.

    At >= 3 the next PROMOTE waits for the window to roll (spec §7): a holdout
    touched by many candidates stops being out-of-sample.
    """
    seen = set()
    for entry in entries:
        if not entry.get("holdout_touched"):
            continue
        window = (entry.get("dev_window") or {}).get("holdout")
        if window and str(window[0]) >= holdout_start.isoformat():
            seen.add(entry.get("hyp_id"))
    return len(seen)


# ---------------------------------------------------------------------------
# PROMOTE / PARK decision (spec §5.4, R1#2 + R1#4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PromoteVerdict:
    decision: str  # PROMOTE | PARK_UNTIL_SWING_POWER | KILL
    reasons: tuple[str, ...]

    def line(self) -> str:
        return f"{self.decision}: " + "; ".join(self.reasons)


def _era_view(summary: Mapping | None) -> tuple[float, float, bool]:
    if not summary:
        return float("nan"), float("inf"), True
    mean_ic = float(summary.get("mean_ic", float("nan")))
    bar = float(summary.get("era_bar", float("inf")))
    inconclusive = bool(summary.get("inconclusive", True))
    return mean_ic, bar, inconclusive


def promote_verdict(
    era_summaries: Mapping[str, Mapping],
    expected_sign: int,
    bh_pass: bool,
) -> PromoteVerdict:
    """Apply the PROMOTE preconditions.

    All four must hold: BH-FDR passage, |mean IC| at or above the era-qualified
    bar, sign agreement with the registered hypothesis, and — the swing-era
    minimum condition — sign agreement in the swing era specifically.

    Legacy strength alone never promotes: the legacy era is a different strategy
    (6-hour bracket, 800-1370 names, different horizon), so it is a weak prior for
    swing behaviour. Legacy-positive with an underpowered swing view parks with an
    automatic retest trigger rather than dying.
    """
    reasons: list[str] = []

    swing_ic, swing_bar, swing_inconclusive = _era_view(era_summaries.get(cfg.ERA_SWING))
    legacy_ic, legacy_bar, legacy_inconclusive = _era_view(era_summaries.get(cfg.ERA_LEGACY))

    swing_sign_ok = swing_ic == swing_ic and (swing_ic > 0) == (expected_sign > 0)
    legacy_sign_ok = legacy_ic == legacy_ic and (legacy_ic > 0) == (expected_sign > 0)

    if not bh_pass:
        reasons.append("BH-FDR not passed at the ledger-deflated level")

    if swing_inconclusive:
        reasons.append(f"swing era inconclusive (|IC|={abs(swing_ic):.4f} < bar {swing_bar:.4f})")
    if not swing_sign_ok:
        reasons.append(
            f"swing sign does not match the hypothesis ({swing_ic:+.4f} vs {expected_sign:+d})"
        )

    if not reasons:
        reasons.append(
            f"swing |IC|={abs(swing_ic):.4f} >= bar {swing_bar:.4f}, sign matches, BH passed"
        )
        return PromoteVerdict("PROMOTE", tuple(reasons))

    legacy_supports = legacy_sign_ok and not legacy_inconclusive
    if legacy_supports and swing_sign_ok:
        reasons.append(
            f"legacy supports ({legacy_ic:+.4f} >= bar {legacy_bar:.4f}) but legacy-only "
            "PROMOTE is forbidden — parked until the swing sample carries the bar"
        )
        return PromoteVerdict("PARK_UNTIL_SWING_POWER", tuple(reasons))
    if legacy_supports and swing_inconclusive:
        reasons.append("legacy supports; swing underpowered, no sign contradiction yet")
        return PromoteVerdict("PARK_UNTIL_SWING_POWER", tuple(reasons))

    return PromoteVerdict("KILL", tuple(reasons))


def retest_due(parked_entry: Mapping, swing_summary: Mapping) -> bool:
    """Whether a PARKed family is worth retesting now (spec §5.4 auto-retest).

    The bar falls as the swing sample grows; a park becomes actionable once the
    current swing |IC| would clear the current bar. Evaluated on every batch run,
    so no park is forgotten.
    """
    if parked_entry.get("decision") != "PARK_UNTIL_SWING_POWER":
        return False
    mean_ic, bar, _ = _era_view(swing_summary)
    if mean_ic != mean_ic:
        return False
    return abs(mean_ic) >= bar


# ---------------------------------------------------------------------------
# Holdout transition criterion (spec §7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HoldoutVerdict:
    passed: bool
    reasons: tuple[str, ...]


def holdout_verdict(
    ic_dev: float,
    ic_holdout: float,
    family_p: float,
    expected_sign: int,
    alpha: float = 0.10,
) -> HoldoutVerdict:
    """Sign agreement AND |IC_holdout| >= 0.5*|IC_dev| AND family p < alpha."""
    reasons: list[str] = []

    if ic_holdout != ic_holdout or ic_dev != ic_dev:
        return HoldoutVerdict(False, ("holdout or dev IC undefined",))

    if (ic_holdout > 0) != (expected_sign > 0):
        reasons.append(f"holdout sign {ic_holdout:+.4f} contradicts {expected_sign:+d}")
    if abs(ic_holdout) < 0.5 * abs(ic_dev):
        reasons.append(f"|IC_holdout|={abs(ic_holdout):.4f} < 0.5*|IC_dev|={0.5 * abs(ic_dev):.4f}")
    if not (family_p < alpha):
        reasons.append(f"family p={family_p:.4f} >= {alpha:.2f}")

    if reasons:
        return HoldoutVerdict(False, tuple(reasons))
    return HoldoutVerdict(
        True,
        (
            f"sign matches, |IC_holdout|={abs(ic_holdout):.4f} >= "
            f"{0.5 * abs(ic_dev):.4f}, p={family_p:.4f}",
        ),
    )
