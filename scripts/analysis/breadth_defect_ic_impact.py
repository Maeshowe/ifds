"""Does the 2026-10-23 breadth defect move the FRL's IC? Measured, not argued.

The defect: `breadth_score_adj` was saved into the Phase 1-3 context and never restored on
the weekday reload, so BC14's deliberate exclusion (`score_adjustment - breadth_score_adj`)
subtracted zero and every ticker carried its sector's breadth term. 9 of 11 sectors, 828 of
1535 scored rows (53.9%).

The question that decides whether the 23 null verdicts survive: does that change the
cross-sectional IC the FRL measures? This script answers it three ways on the real panel.

* (A) injects the defect as a PER-SECTOR CONSTANT, which is its instantaneous shape;
* (B) is the CONTROL — the same offsets on a non-sector-neutral pooled IC. Without it a
  zero in (A) could just mean the injection did nothing;
* (C) bounds the one channel that is NOT a per-sector constant: the breadth term entered
  before the EWMA(5) smoothing, so a ticker's smoothed score carries a history-dependent
  fraction of it.

Measured 2026-10-23 on 84,832 rows / 86 days / 11 sectors / 2,019 tickers:
    (A) ΔIC = 0.000e+00 bit-exact at h = 1, 3, 5, 7, 10
    (B) Δ   = +0.0049 … +0.0069   (the injection does bite when ranks are not neutralised)
    (C) worst |ΔIC| = 9.49e-04 = 3.2% of the h=5 era bar

Read-only; writes nothing. Runs on the MacBook, where the research cache lives.
Recorded in docs/decisions/2026-10-23-signal-family-closure.md §3.1.
"""
import sys
import os
import datetime as dt
R = "/Users/safrtam/SSH-Services/ifds"
sys.path.insert(0, os.path.join(R, "scripts", "research"))
os.chdir(R)
import numpy as np
import pandas as pd
import frl_loader as loader
import frl_ic as ic
import frl_config as cfg
import frl_returns as fret

panel = loader.load_panel(cfg.SWING_START, dt.date(2026, 10, 2))
df = (panel.frame if hasattr(panel, "frame") else panel.panel).copy()
rets = fret.load_cached_returns()
if rets is None:
    print("!! no cached returns panel")
    raise SystemExit(1)
df = df.merge(rets, on=["date", "ticker"], how="left")
print(f"merged: {len(df)} rows; horizons available:",
      [c for c in df.columns if c.startswith("fwd_ret_")])

HOR = [h for h in (1, 3, 5, 7, 10) if f"fwd_ret_{h}" in df.columns]
sectors = sorted(df["sector"].dropna().unique())
rng = np.random.default_rng(20261023)

def ic_mean(frame, col, h):
    s = ic.daily_ic(frame, col, f"fwd_ret_{h}")
    return float(np.nanmean(s.values))

print("\n=== A) PURE PER-SECTOR CONSTANT (the defect's instantaneous shape) ===")
print(f"{'h':>3} {'IC base':>11} {'IC +breadth':>12} {'ΔIC':>14}")
base = {h: ic_mean(df, "score", h) for h in HOR}
# the real measured breadth values: -5..-15 on 9 of 11 sectors
offsets = {s: v for s, v in zip(sectors, [-15,-15,-15,-15,-15,-15,-15,-5,-5,0,0])}
d2 = df.copy()
d2["score_defect"] = d2["score"] + d2["sector"].map(offsets).fillna(0.0)
for h in HOR:
    v = ic_mean(d2, "score_defect", h)
    print(f"{h:>3} {base[h]:>11.8f} {v:>12.8f} {v-base[h]:>14.3e}")

print("\n=== B) CONTROL: the same offsets on a NON-sector-neutral pooled IC ===")
def pooled_ic(frame, col, h):
    out=[]
    for day, g in frame.dropna(subset=[col, f"fwd_ret_{h}"]).groupby("date"):
        if len(g) > 2:
            out.append(g[col].rank(pct=True).corr(g[f"fwd_ret_{h}"].rank(pct=True)))
    return float(np.nanmean(out))
for h in HOR:
    b, v = pooled_ic(df, "score", h), pooled_ic(d2, "score_defect", h)
    print(f"{h:>3} pooled base {b:>10.6f}  with defect {v:>10.6f}  Δ {v-b:>+10.6f}")

print("\n=== C) THE LEAK: per-ticker EWMA transient (sector adj changes weekly) ===")
# The breadth term enters BEFORE the EWMA(5) smoothing, so a ticker's smoothed score
# carries a history-dependent fraction of it. Emulate: resample the sector offset weekly
# and smooth per ticker with alpha=1/3, then difference against the unsmoothed constant.
alpha = 1/3
worst = 0.0
for trial in range(8):
    weekly = {s: rng.choice([-15.0, -10.0, -5.0, 0.0]) for s in sectors}
    d3 = df.copy()
    d3["_raw"] = d3["sector"].map(weekly).fillna(0.0)
    # week index -> a fresh draw each week, so the constant actually moves
    wk = pd.to_datetime(d3["date"]).dt.isocalendar().week.astype(int)
    jitter = {(s, w): rng.choice([-15.0,-10.0,-5.0,0.0]) for s in sectors for w in wk.unique()}
    d3["_raw"] = [jitter[(s, w)] if pd.notna(s) else 0.0 for s, w in zip(d3["sector"], wk)]
    d3 = d3.sort_values(["ticker", "date"])
    d3["_sm"] = d3.groupby("ticker")["_raw"].transform(lambda x: x.ewm(alpha=alpha).mean())
    d3["score_leak"] = d3["score"] + d3["_sm"]
    for h in HOR:
        delta = abs(ic_mean(d3, "score_leak", h) - base[h])
        worst = max(worst, delta)
print(f"worst |ΔIC| over 8 seeds x {len(HOR)} horizons: {worst:.3e}")
print(f"era_bar (h=5, from the ledger): ~0.0298  ->  leak is {worst/0.0298*100:.2f}% of it")
