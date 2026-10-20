#!/usr/bin/env python3
"""D-U4 — what the silent universe substitution did to the closed swing era.

From 2026-08-16 the index-membership source was dead and Phase 2 fell open to the
legacy FMP screener (see docs/CHANGELOG.md 2026-10-19 §8-9). The swing era therefore
ran on TWO populations: index members until 2026-08-14, screener names after. This
script measures what the era would have looked like had the source not broken, by
restricting the post-break days to the membership the system WOULD have used.

Three questions, in order of importance:

  1. sigma_cs — does restoring the design universe RAISE or LOWER the wall? Two
     sources disagree: the 2026-10-19 review panel said restoring it lowers sigma_cs
     and so RAISES the wall; a direct split-half measurement said the opposite
     (index half 0.0609 vs screener half 0.0564 at h=5). The wall is the project's
     central number, so the disagreement has to be settled empirically.
  2. IC — would the closed null results have differed on a clean universe?
  3. Rank displacement — how far do percentile ranks move for the names that survive?

NOT VERDICT GENERATION. This is a sensitivity analysis over already-closed attempts.
It writes nothing to research/attempt_ledger.jsonl and changes no decision; the
house rule forbids re-running the ledger for verdicts (companion #4).

MEMBERSHIP APPROXIMATION, stated up front: per-week historical membership was never
archived, so the post-break days are restricted to the 2026-08-04 snapshot (1018
names) — the last list the live source produced before it broke, i.e. exactly the one
the system would have carried into 08-16 under its 7-day cache. Membership drifts
slowly: 2026-08-04 vs 2026-10-20 is +43/-34, Jaccard 0.927 over 77 days, so the
approximation costs a few percent at the far end of the window and is reported.

Read-only. Companion: docs/tasks/2026-10-20-universe-fail-open-decision.md D-U4.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "research"))
sys.path.insert(0, str(ROOT / "src"))

import frl_config as cfg  # noqa: E402
import frl_ic  # noqa: E402
import frl_loader as loader  # noqa: E402

#: First session on the degraded (screener) universe — the Sunday rebuild after the
#: 7-day cache expired. Measured: 2026-08-09 was the last run on index membership.
REGIME_BREAK = date(2026, 8, 16)
ERA_LAST = date(2026, 10, 2)

#: The binding round trip from the 2026-10-19 cost model, so the wall here is
#: directly comparable with docs/review/2026-10-19-execution-wall-by-horizon.md.
ROUND_TRIP_BOUND_BPS = 84.73

MEMBERSHIP_PATH = ROOT / "research" / "cache" / "membership" / "universe_2026-08-04.json"


def load_membership(path: Path = MEMBERSHIP_PATH) -> set[str]:
    payload = json.loads(path.read_text())
    return {s.strip().upper() for s in payload["symbols"]}


def build_panels(membership: set[str]):
    """Return (as_run, counterfactual) frames merged with forward returns."""
    import pandas as pd

    panel = loader.load_panel(cfg.SWING_START, ERA_LAST).frame
    panel["date"] = pd.to_datetime(panel["date"]).dt.date
    panel["ticker"] = panel["ticker"].astype(str).str.upper()

    returns = pd.read_parquet(cfg.CACHE_DIR / "returns.parquet")
    returns["date"] = pd.to_datetime(returns["date"]).dt.date
    returns["ticker"] = returns["ticker"].astype(str).str.upper()

    as_run = panel.merge(returns, on=["date", "ticker"], how="left")
    # Only the post-break days are restricted: before the break the live pipeline
    # already applied membership, so those rows are their own counterfactual.
    keep = (as_run["date"] < REGIME_BREAK) | (as_run["ticker"].isin(membership))
    return as_run, as_run[keep].copy()


def _sigma_and_wall(frame, horizon: int) -> tuple[float, float, int, int]:
    column = f"fwd_ret_{horizon}"
    sub = frame[frame[column].notna()]
    sigma = frl_ic.cross_sectional_sigma(sub, column)
    wall = ROUND_TRIP_BOUND_BPS / (sigma * 1e4) if sigma and sigma == sigma else float("nan")
    return sigma, wall, sub["date"].nunique(), len(sub)


def main() -> int:
    membership = load_membership()
    as_run, counter = build_panels(membership)

    print("=" * 100)
    print("D-U4 — THE UNIVERSE COUNTERFACTUAL (sensitivity analysis, NOT verdict generation)")
    print("=" * 100)
    print(f"membership snapshot : {MEMBERSHIP_PATH.name}, {len(membership)} names")
    print(f"regime break        : {REGIME_BREAK} (first session on the screener)")
    print(f"round trip charged  : {ROUND_TRIP_BOUND_BPS} bp (the binding bound)")

    print("\n" + "-" * 100)
    print("1. PANEL SIZE — what the restriction removes")
    print("-" * 100)
    for label, days in (
        ("pre-break  (already membership-filtered)", as_run[as_run["date"] < REGIME_BREAK]),
        ("post-break (as run, screener)", as_run[as_run["date"] >= REGIME_BREAK]),
        ("post-break (counterfactual)", counter[counter["date"] >= REGIME_BREAK]),
    ):
        per_day = days.groupby("date")["ticker"].nunique()
        if per_day.empty:
            continue
        print(
            f"  {label:<42} days={per_day.size:>3}  mean={per_day.mean():>7.0f}  "
            f"min={per_day.min():>5}  max={per_day.max():>5}"
        )
    post = as_run[as_run["date"] >= REGIME_BREAK]
    off = post[~post["ticker"].isin(membership)]
    print(
        f"\n  off-membership rows removed post-break: {len(off):,} of {len(post):,} "
        f"({len(off) / max(len(post), 1) * 100:.0f}%)"
    )

    print("\n" + "-" * 100)
    print("2. SIGMA_CS AND THE WALL — the question the two sources disagreed on")
    print("-" * 100)
    print(
        f"{'h':>3}{'sigma as-run':>14}{'sigma counter':>15}{'delta':>9}"
        f"{'wall as-run':>13}{'wall counter':>14}{'delta':>9}"
    )
    for h in (1, 3, 5, 7, 10):
        s_a, w_a, _, _ = _sigma_and_wall(as_run, h)
        s_c, w_c, _, _ = _sigma_and_wall(counter, h)
        print(
            f"{h:>3}{s_a:>14.4f}{s_c:>15.4f}{(s_c - s_a):>+9.4f}"
            f"{w_a:>13.4f}{w_c:>14.4f}{(w_c - w_a):>+9.4f}"
        )

    print("\n" + "-" * 100)
    print("3. IC OF THE SCORE FAMILY — would the closed null have differed?")
    print("-" * 100)
    print(f"{'h':>3}{'mean IC as-run':>16}{'mean IC counter':>17}{'delta':>9}{'n days':>9}")
    for h in (1, 3, 5, 7, 10):
        column = f"fwd_ret_{h}"
        rows = []
        for frame in (as_run, counter):
            sub = frame[frame[column].notna() & frame["score"].notna()]
            series = frl_ic.daily_ic(sub, "score", column)
            summary = frl_ic.aggregate(series, h, cfg.ERA_SWING)
            rows.append(summary)
        print(
            f"{h:>3}{rows[0].mean_ic:>+16.4f}{rows[1].mean_ic:>+17.4f}"
            f"{(rows[1].mean_ic - rows[0].mean_ic):>+9.4f}{rows[1].n_days:>9}"
        )
    print("\n  The score family is a confirmed cross-sectional null (23 attempts).")
    print("  This row asks only whether a clean universe would have changed that.")

    print("\n" + "-" * 100)
    print("4. RANK DISPLACEMENT — how far the surviving names move")
    print("-" * 100)
    import pandas as pd

    moves = []
    for day, group in as_run[as_run["date"] >= REGIME_BREAK].groupby("date"):
        scored = group[group["score"].notna()]
        if len(scored) < 20:
            continue
        full = scored["score"].rank(pct=True)
        inside = scored["ticker"].isin(membership)
        if inside.sum() < 20:
            continue
        restricted = scored.loc[inside, "score"].rank(pct=True)
        delta = (restricted - full[inside]).abs()
        moves.append(delta.mean())
    if moves:
        series = pd.Series(moves)
        print(
            f"  mean |percentile shift| per day: mean={series.mean():.3f}  "
            f"median={series.median():.3f}  max={series.max():.3f}   (days={len(series)})"
        )
        print("  A shift of 0.10 means a name typically moves 10 percentile points.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
