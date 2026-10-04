"""FRL — rolling embargoed holdout, PROMOTE criteria, PARK auto-retest (spec §5.4, §7).

The holdout is the loop's scarcest resource: one touch per hypothesis, forever
(G6). Everything here exists to make spending a touch deliberate and auditable.
"""

from __future__ import annotations

import math
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


# ---------------------------------------------------------------------------
# (e) Economic significance gate
#
# Pre-registration: docs/planning/2026-10-04-economic-gate-preregistration.md
# (§3.1 the rule, §3.2 why p75, §3.3 the decision table, §4 PARK_UNECONOMIC).
#
# Why this exists: ``frl_ic.costed_view()`` already computes ``breakeven_ic`` and
# ``survives_cost``, and ``frl_report`` prints them — but ``promote_verdict`` took
# no cost input at all, so a factor could PROMOTE while losing money. Spec §5.3
# says in its own title "költség-kapu, NEM kill-kapu". The 2026-10-03 gate run
# measured the consequence: on the swing h=1 arm the statistical bar was 0.0311
# while the economic breakeven was 0.15-0.18 — the economic bar is 2.3-4.8x the
# harder one, so the statistical bar alone can wave through a money-loser.
#
# This gate intercepts ONLY the PROMOTE branch. Every KILL and PARK path below is
# untouched, so no previously confirmed verdict can move (regression-pinned in
# tests/test_frl_holdout.py::TestConfirmedVerdictsAreUnchanged).
# ---------------------------------------------------------------------------

ECONOMIC_OK = "ok"
ECONOMIC_INCONCLUSIVE = "inconclusive"
ECONOMIC_FAIL = "fail"
ECONOMIC_UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class EconomicView:
    """Breakeven IC for one era at the median and p75 per-side cost.

    Both come from ``frl_ic.costed_view()`` run against the two cost levels in
    ``research/cost_model.json``. The p75 is the binding threshold (pre-reg
    §3.2): it is calibrated from the slippage distribution's own dispersion
    (p75/median has run 1.41-1.63), not from a safety factor anyone chose, and
    being the conservative end it cannot flip toward a stricter cost.
    """

    breakeven_median: float
    breakeven_p75: float


def economic_status(mean_ic: float, view: EconomicView | None) -> str:
    """Classify a factor's |IC| against its cost thresholds (pre-reg §3.3).

    Fails CLOSED: a missing view, a non-finite bound, or an inverted band
    (p75 below median, which a well-formed cost model cannot produce) all
    return ``ECONOMIC_UNAVAILABLE`` rather than silently passing.
    """
    if view is None:
        return ECONOMIC_UNAVAILABLE
    if not math.isfinite(mean_ic):
        return ECONOMIC_UNAVAILABLE
    median, p75 = view.breakeven_median, view.breakeven_p75
    if not (math.isfinite(median) and math.isfinite(p75)):
        return ECONOMIC_UNAVAILABLE
    if p75 < median:
        return ECONOMIC_UNAVAILABLE

    magnitude = abs(mean_ic)
    if magnitude >= p75:
        return ECONOMIC_OK
    if magnitude >= median:
        return ECONOMIC_INCONCLUSIVE
    return ECONOMIC_FAIL


def _era_view(summary: Mapping | None) -> tuple[float, float, bool]:
    if not summary:
        return float("nan"), float("inf"), True
    mean_ic = float(summary.get("mean_ic", float("nan")))
    bar = float(summary.get("era_bar", float("inf")))
    inconclusive = bool(summary.get("inconclusive", True))
    return mean_ic, bar, inconclusive


def _t_eff(summary: Mapping | None) -> float:
    """Effective sample size for an era's IC series (0 if the era is absent)."""
    if not summary:
        return 0.0
    try:
        return float(summary.get("t_eff", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def promote_verdict(
    era_summaries: Mapping[str, Mapping],
    expected_sign: int,
    bh_pass: bool,
    economic_views: Mapping[str, EconomicView] | None = None,
) -> PromoteVerdict:
    """Apply the PROMOTE preconditions.

    All five must hold: BH-FDR passage, |mean IC| at or above the era-qualified
    bar, sign agreement with the registered hypothesis, the swing-era minimum
    condition (sign agreement in the swing era specifically), and — since the
    2026-10-04 pre-registration — **(e) economic significance**: the factor must
    clear its own trading cost. ``economic_views`` carries the per-era breakeven
    pair; omitting it cannot PROMOTE (fail closed).

    Legacy strength alone never promotes: the legacy era is a different strategy
    (6-hour bracket, 800-1370 names, different horizon), so it is a weak prior for
    swing behaviour. Legacy-positive with an underpowered swing view parks with an
    automatic retest trigger rather than dying.

    KILL vs PARK encodes pre-reg criteria (a)/(b)/(c): a terminal KILL requires
    either a sign contradiction (b) or a clean fail at **adequate** T_eff (a). If
    the sign is correct but every era with data is underpowered (T_eff below
    ``MIN_ADEQUATE_T_EFF``, spec §5.5), the fail is power-driven, not a null — it
    PARKs and retests as the swing sample grows (c). This holds for swing-only
    factors too, which have no legacy leg to lean on.
    """
    reasons: list[str] = []

    swing_ic, swing_bar, swing_inconclusive = _era_view(era_summaries.get(cfg.ERA_SWING))
    legacy_ic, legacy_bar, legacy_inconclusive = _era_view(era_summaries.get(cfg.ERA_LEGACY))
    swing_t_eff = _t_eff(era_summaries.get(cfg.ERA_SWING))
    legacy_t_eff = _t_eff(era_summaries.get(cfg.ERA_LEGACY))

    swing_present = swing_ic == swing_ic  # not NaN
    swing_sign_ok = swing_present and (swing_ic > 0) == (expected_sign > 0)
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
        # (a)-(d) are satisfied. The (e) economic gate decides from here, and
        # intercepts ONLY this branch — the KILL/PARK logic below is untouched.
        reasons.append(
            f"swing |IC|={abs(swing_ic):.4f} >= bar {swing_bar:.4f}, sign matches, BH passed"
        )
        view = (economic_views or {}).get(cfg.ERA_SWING)
        status = economic_status(swing_ic, view)

        if status == ECONOMIC_OK:
            reasons.append(
                f"(e) economic: |IC|={abs(swing_ic):.4f} >= breakeven(p75)="
                f"{view.breakeven_p75:.4f}"
            )
            return PromoteVerdict("PROMOTE", tuple(reasons))

        if status == ECONOMIC_FAIL:
            reasons.append(
                f"(e) economic FAIL: |IC|={abs(swing_ic):.4f} < breakeven(median)="
                f"{view.breakeven_median:.4f} — real signal, but this execution "
                "style cannot harvest it; the remedy is execution, not the factor"
            )
            return PromoteVerdict("PARK_UNECONOMIC", tuple(reasons))

        if status == ECONOMIC_INCONCLUSIVE:
            reasons.append(
                f"(e) economic INCONCLUSIVE: breakeven(median)="
                f"{view.breakeven_median:.4f} <= |IC|={abs(swing_ic):.4f} < "
                f"breakeven(p75)={view.breakeven_p75:.4f} — explicitly undecided, "
                "never rounded up to PROMOTE"
            )
            return PromoteVerdict("INCONCLUSIVE_ON_COST", tuple(reasons))

        reasons.append(
            "(e) economic unavailable — cost view missing or malformed, so (e) was "
            "not evaluated; PROMOTE requires it (fail closed)"
        )
        return PromoteVerdict("INCONCLUSIVE_ON_COST", tuple(reasons))

    # Criterion (b): a swing sign contradiction is always terminal — the
    # cross-sectional form of the mechanism is refuted, not underpowered.
    if swing_present and not swing_sign_ok:
        reasons.append("swing sign contradiction — terminal (pre-reg b)")
        return PromoteVerdict("KILL", tuple(reasons))

    # Legacy-positive + swing catching up: park with the auto-retest trigger.
    legacy_supports = legacy_sign_ok and not legacy_inconclusive
    if legacy_supports:
        reasons.append(
            f"legacy supports ({legacy_ic:+.4f}) but legacy-only PROMOTE is forbidden — "
            "parked until the swing sample carries the bar"
        )
        return PromoteVerdict("PARK_UNTIL_SWING_POWER", tuple(reasons))

    # Criterion (a) vs (c): is there any era with ADEQUATE power that cleanly
    # fails? If so the fail is a genuine null → KILL. Otherwise every leg is
    # underpowered and the sign is not contradicted → PARK and retest.
    legacy_adequate_fail = (
        legacy_t_eff >= cfg.MIN_ADEQUATE_T_EFF and legacy_ic == legacy_ic
    )  # legacy present here always means it failed to PROMOTE
    swing_adequate_fail = swing_present and swing_t_eff >= cfg.MIN_ADEQUATE_T_EFF

    if legacy_adequate_fail or swing_adequate_fail:
        reasons.append(
            f"adequate T_eff clean fail (swing T_eff={swing_t_eff:.1f}, "
            f"legacy T_eff={legacy_t_eff:.1f} vs floor {cfg.MIN_ADEQUATE_T_EFF:.0f}) — "
            "genuine null (pre-reg a)"
        )
        return PromoteVerdict("KILL", tuple(reasons))

    reasons.append(
        f"sign correct, all eras underpowered (swing T_eff={swing_t_eff:.1f} < "
        f"{cfg.MIN_ADEQUATE_T_EFF:.0f}) — power-driven fail, retest as sample grows (pre-reg c)"
    )
    return PromoteVerdict("PARK_UNTIL_SWING_POWER", tuple(reasons))


def retest_due(
    parked_entry: Mapping,
    swing_summary: Mapping,
    economic_view: EconomicView | None = None,
) -> bool:
    """Whether a PARKed family is worth retesting now (spec §5.4 auto-retest).

    The two park reasons have INDEPENDENT triggers:

    * ``PARK_UNTIL_SWING_POWER`` — the statistical bar falls as the swing sample
      grows; actionable once the current swing |IC| would clear the current bar.
    * ``PARK_UNECONOMIC`` — the signal was real but could not pay for its
      trading; actionable once the COST model improves enough that the breakeven
      drops below the measured |IC| (pre-reg §4). Without a view it stays parked.

    Evaluated on every batch run, so no park is forgotten.
    """
    decision = parked_entry.get("decision")
    if decision == "PARK_UNECONOMIC":
        mean_ic, _, _ = _era_view(swing_summary)
        return economic_status(mean_ic, economic_view) == ECONOMIC_OK
    if decision != "PARK_UNTIL_SWING_POWER":
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
