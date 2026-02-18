# Task: SimEngine L2 — Mód 1 (Parameter Sweep + Phase 4 Snapshot)

**Date:** 2026-02-18
**BC:** BC19
**Priority:** NORMAL
**Design doc:** `docs/planning/simengine-l2-design.md` (APPROVED)
**Builds on:** SIM-L1 (`src/ifds/sim/` — models, broker_sim, validator, report)

---

## Scope

Two deliverables:
1. **SIM-L2 Mód 1:** Multi-variant parameter sweep — run broker_sim with different TP/SL/hold configs on the same execution plan data, compare results with paired t-test.
2. **Phase 4 Snapshot Persistence:** Save Phase 4 "passed" ticker raw data daily for future Mód 2 re-score (BC20 will consume this).

---

## Deliverable 1: Parameter Sweep Engine

### New files

**`src/ifds/sim/replay.py`** — Multi-variant orchestrator

Core function:
```python
def run_comparison(
    variants: list[SimVariant],
    output_dir: str = "output",
    polygon_api_key: str | None = None,
    max_hold_days: int = 10,
    cache_dir: str | None = None,
) -> ComparisonReport:
```

Logic:
1. Load execution plan CSVs once (`load_execution_plans()` from validator.py)
2. Fetch Polygon bars once (reuse `_fetch_bars_for_trades()` from validator.py)
3. For each variant:
   - Deep copy base trades
   - Apply parameter overrides (recalculate TP/SL from implied ATR)
   - Run `simulate_bracket_order()` on each trade
   - Aggregate `ValidationSummary`
4. Return `ComparisonReport` with delta metrics + p-value

Parameter override logic — `recalculate_bracket()`:
```python
def recalculate_bracket(trade: Trade, overrides: dict,
                        original_sl_atr_mult: float = 1.5) -> Trade:
    """Recalculate TP/SL from implied ATR and new multipliers."""
    if trade.entry_price <= 0 or trade.stop_loss <= 0:
        return trade
    # Implied ATR
    atr = (trade.entry_price - trade.stop_loss) / original_sl_atr_mult
    if atr <= 0:
        return trade
    
    new_sl = overrides.get("stop_loss_atr_multiple", original_sl_atr_mult)
    new_tp1 = overrides.get("tp1_atr_multiple", 2.0)
    new_tp2 = overrides.get("tp2_atr_multiple", 3.0)
    
    trade.stop_loss = trade.entry_price - new_sl * atr
    trade.tp1 = trade.entry_price + new_tp1 * atr
    trade.tp2 = trade.entry_price + new_tp2 * atr
    return trade
```

YAML config loading:
```python
def load_variants_from_yaml(yaml_path: str) -> list[SimVariant]:
    """Load variant definitions from YAML config file."""
```

Format — see `docs/planning/simengine-l2-design.md` section 7.1.

---

**`src/ifds/sim/comparison.py`** — Statistical comparison

```python
from scipy.stats import ttest_rel

def compare_variants(variants: list[SimVariant]) -> ComparisonReport:
    """Compare first variant (baseline) against all others."""
```

Delta metrics per (baseline, challenger) pair:
- ΔP&L = challenger.total_pnl - baseline.total_pnl
- ΔWin Rate (leg1 + leg2)
- ΔAvg P&L per trade
- ΔAvg Holding Days
- ΔFill Rate

Statistical significance:
- `ttest_rel` on paired per-trade P&L (same ticker, same date → paired)
- `is_significant = p_value < 0.05`
- If fewer than 30 paired trades: set `insufficient_data = True` in report

scipy is **mandatory** — direct import, no try/except fallback.

---

### Model additions in `src/ifds/sim/models.py`

```python
@dataclass
class SimVariant:
    name: str
    description: str = ""
    overrides: dict = field(default_factory=dict)
    trades: list[Trade] = field(default_factory=list)
    summary: ValidationSummary = field(default_factory=ValidationSummary)

@dataclass
class VariantDelta:
    """Delta between baseline and one challenger."""
    challenger_name: str
    pnl_delta: float = 0.0
    win_rate_leg1_delta: float = 0.0
    win_rate_leg2_delta: float = 0.0
    avg_pnl_delta: float = 0.0
    avg_holding_days_delta: float = 0.0
    fill_rate_delta: float = 0.0
    p_value: float | None = None
    is_significant: bool = False
    insufficient_data: bool = False
    paired_trade_count: int = 0

@dataclass
class ComparisonReport:
    baseline: SimVariant = field(default_factory=SimVariant)
    challengers: list[SimVariant] = field(default_factory=list)
    deltas: list[VariantDelta] = field(default_factory=list)
```

---

### Report additions in `src/ifds/sim/report.py`

Add:
```python
def write_comparison_report(report: ComparisonReport, output_dir: str) -> Path:
    """Write comparison CSV + console summary."""
```

Output: `output/sim_comparison_YYYYMMDD_HHMMSS.csv` with columns:
variant, total_trades, filled, total_pnl, avg_pnl, leg1_wr, leg2_wr, avg_hold_days

Plus delta section at bottom.

---

### CLI in `src/ifds/__main__.py`

Add `compare` subcommand:
```bash
# CLI with overrides
python -m ifds compare \
  --baseline "default" \
  --challenger "wide_stops" \
  --override-sl-atr 2.0 \
  --override-tp1-atr 3.0 \
  --override-tp2-atr 4.0

# CLI with YAML config
python -m ifds compare --config sim_variants.yaml
```

Both modes should work. If `--config` is provided, ignore individual `--override-*` flags.

---

## Deliverable 2: Phase 4 Snapshot Persistence

### New file: `src/ifds/data/phase4_snapshot.py`

```python
def save_phase4_snapshot(passed_analyses: list[StockAnalysis],
                         snapshot_dir: str = "state/phase4_snapshots") -> Path:
    """Save Phase 4 passed ticker data as daily parquet snapshot."""

def load_phase4_snapshot(date_str: str,
                         snapshot_dir: str = "state/phase4_snapshots") -> list[dict]:
    """Load a single day's snapshot for re-scoring."""
```

**What to persist per ticker** (from StockAnalysis + raw API data):
- ticker, sector, combined_score, sector_adjustment
- TechnicalAnalysis fields (price, sma_200, sma_50, rsi_14, atr_14, rs_vs_spy, all scores)
- FlowAnalysis fields (rvol, dp_pct, pcr, otm_call_ratio, block_trade_count, buy_pressure_score, all scores)
- FundamentalScoring fields (rev_growth, eps_growth, margin, roe, d/e, insider_score, shark, all scores)

**Format:** Parquet (via pyarrow — already a transitive dependency from pandas if present, otherwise plain JSON).
- Check if pyarrow is available: if yes, use parquet. If no, fall back to gzipped JSON.
- File naming: `state/phase4_snapshots/{YYYY-MM-DD}.parquet` or `.json.gz`

### Integration point

In the main pipeline (`src/ifds/pipeline.py` or wherever Phase 6 completes), add:
```python
# After Phase 6, before Telegram report
if config.runtime.get("phase4_snapshot_enabled", True):
    from ifds.data.phase4_snapshot import save_phase4_snapshot
    save_phase4_snapshot(ctx.phase4.passed)
```

Add to `defaults.py` RUNTIME:
```python
"phase4_snapshot_enabled": True,
"phase4_snapshot_dir": "state/phase4_snapshots",
```

---

## Testing

### test_sim_replay.py (NEW — ~15-20 tests)

- `test_recalculate_bracket_basic` — ATR implied correctly, new TP/SL correct
- `test_recalculate_bracket_edge_cases` — zero entry, zero stop, negative ATR
- `test_run_comparison_two_variants` — baseline vs challenger, deltas computed
- `test_run_comparison_identical_variants` — delta should be ~0, p_value ~1.0
- `test_run_comparison_better_variant` — wider stops → more P&L (contrived bars)
- `test_paired_ttest_significance` — mock data with known p-value
- `test_paired_ttest_insufficient_data` — < 30 trades → insufficient_data=True
- `test_load_variants_from_yaml` — parse YAML correctly
- `test_load_variants_yaml_missing_file` — graceful error
- `test_comparison_report_output` — CSV written correctly
- `test_cli_compare_overrides` — argparse works
- `test_cli_compare_yaml` — argparse works

### test_phase4_snapshot.py (NEW — ~5-8 tests)

- `test_save_and_load_snapshot` — roundtrip
- `test_snapshot_content_completeness` — all fields present
- `test_snapshot_overwrite_same_day` — idempotent
- `test_load_nonexistent_date` — returns empty list
- `test_snapshot_dir_creation` — creates dir if missing

---

## Validation

- `pytest` — all existing 752+ tests pass + 20-28 new tests
- No breaking changes to existing sim/ module
- New dependencies: pyyaml (add to requirements if not present), scipy (already installed)
- Check if pyarrow is available for parquet; if not, use json.gz fallback

## Files to create
1. `src/ifds/sim/replay.py`
2. `src/ifds/sim/comparison.py`
3. `src/ifds/data/phase4_snapshot.py`
4. `tests/test_sim_replay.py`
5. `tests/test_phase4_snapshot.py`

## Files to modify
1. `src/ifds/sim/models.py` — add SimVariant, VariantDelta, ComparisonReport
2. `src/ifds/sim/report.py` — add comparison report writer
3. `src/ifds/__main__.py` — add `compare` subcommand
4. `src/ifds/config/defaults.py` — add phase4_snapshot_* runtime keys
5. `src/ifds/pipeline.py` — add snapshot save call after Phase 6 (check exact file name)

## Out of scope
- Mód 2 re-score (BC20)
- T10 Freshness vs WOW A/B test (BC20)
- OBSIDIAN regime multiplier in variants (BC20+)
