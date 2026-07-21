# `scripts/research/` — FRL tooling

Read-only analytical tooling (the `signal_attribution`-wiring precedent). Touches
no production code, cron, scoring or config. Runs on the **MacBook**.

Flat modules, no package — each entry point puts its own directory on `sys.path`
(the `scripts/paper_trading/` house pattern), which also avoids colliding with
the top-level `research/` data directory.

| Module | Role |
|---|---|
| `frl_config.py` | single source of truth: era boundaries, D_B=4 weeks, D_C=q0.10, horizons, paths |
| `frl_loader.py` | scan-matrix cross-section + panel + era guard + JSONL validation |
| `frl_returns.py` | forward-return matrix from Polygon grouped-daily bars |
| `frl_cost.py` | empirical per-side cost model from observed entry slippage |

## Verified data semantics (FRL-0 gate, 2026-07-21)

The gate report lives in `docs/tasks/2026-07-21-frl-scan-matrix-loader.md`
§Eredmény. Three findings are encoded in the loader and must not be undone:

1. **`Total_Score` is era-dependent in meaning.** Legacy (≤2026-05-15) = legacy
   composite, 0–108 on a .0/.5 grid. Swing (≥2026-05-18) = EWMA(5)-smoothed
   `S_j = 100·(PCR_pct − OTM_pct) + sector_adj`, −125…+107 continuous. The scales
   are incompatible → `require_single_era()` blocks pooled score factors (G5).
2. **Tech-filter rows are NaN, not 0.** They never reached scoring; their 0.0 is a
   dataclass default. On all four sampled days the zero-score set was *exactly*
   the tech-filter set. Loading them as 0 would repeat the dp_pct structural-zero
   error class on ~40% of a swing-day panel.
3. **The JSONL is not a score validator in the swing era.** `TICKER_SCORED` emits
   the *pre-rescore legacy composite* (70–95, .0/.5 grid) on a biased subset
   (legacy-passed names only). `validate_with_events()` compares scores in the
   legacy era and coverage only in the swing era.

Fourth, from V2: the Mini's `data/cache/polygon` is **empty**, so returns come
from the API via `get_grouped_daily` — one call per day for the whole market.

## Usage

```python
import sys; sys.path.insert(0, "scripts/research")
from datetime import date
import frl_loader, frl_cost

panel = frl_loader.load_panel(date(2026, 5, 18), date(2026, 7, 20))
print(len(panel.days), "days,", panel.missing_days, "missing")

model = frl_cost.build_cost_model()  # swing era by default
```
