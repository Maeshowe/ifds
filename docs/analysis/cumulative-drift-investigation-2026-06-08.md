# Cumulative Drift Investigation — DAYS_30 Reconciliation (2026-06-08)

**Trigger**: the 2026-06-06 first live cross-check (`build_cross_check_flags`)
flagged a P0 `cumulative_drift` of **−$218.43**: tracked cumulative (+245.25)
+ unrealized (+211.92) = +457.17 vs NetLiq-implied +675.60.

**Verdict**: ✅ **Fully explained. Zero post-pivot tracking error.** The drift is
entirely a **baseline-reset artifact** (the IBKR paper account was reset to
~$100,208, not $100,000.00, at the 5/18 pivot) plus accrued credit interest.
The daily P&L tracking matches broker realized **to the penny**.

---

## Method

Connector `get_account_trades(DAYS_30)` (172 trades, 2026-05-07 → 2026-06-05),
`get_account_summary` (NetLiq), `get_account_positions` (unrealized). Reset
timestamp from `cumulative_pnl.json`: `reset_at = 2026-05-18T10:05:00Z`.

## Ground-truth figures (2026-06-08)

| Quantity | Value |
|---|---|
| NetLiq | $100,678.44 |
| Cash | $72,480.83 |
| Gross position value | $28,184.72 |
| Unrealized (6 positions) | +$212.30 |
| Tracked cumulative (production) | +$245.25 |

## Decisive checks

### 1. Post-reset broker realized == tracked cumulative, to the penny

Summing `realized_pnl` over all trades **strictly after** the reset timestamp
(`trade_time > 2026-05-18T10:05:00Z`):

> **POST-reset broker realized = +$245.25** = tracked production cumulative (+$245.25). ✅

Every post-pivot day matches the restated `daily_history` exactly (5/19 +112.63,
5/21 −220.69, 5/27 −695.79, 6/2 +434.82, 6/3 +229.84, 6/4 +225.34, 6/5 +63.83, …).

The Day-1 (5/18) **−$47.92 AVDL.CVR** loss (a pre-pivot contingent-value-right
settling to $0) is timestamped **04:00:00Z — before the 10:05Z reset** — and is
therefore correctly **excluded** from tracking. (A naive date-bucket sum wrongly
folds it into 5/18; the timestamp split is what makes tracking reconcile.)

### 2. The account was reset to ~$100,208, not $100,000.00 flat

Reconstructing cash from post-reset trade legs
(`cash = 100000 + Σ(SELL net) − Σ(BUY net) − Σ comm`):

| | Value |
|---|---|
| Implied cash if reset-to-$100k-flat | $72,272.46 |
| Actual IBKR cash | $72,480.83 |
| **Pre-pivot cash carry** | **+$208.37** |

The `cumulative_pnl.json` reset set `initial_capital = 100000` and cumulative = 0,
but the **live IBKR account retained ~+$208.37 of pre-pivot residual cash** at the
pivot instant. (The old pre-swing tracking file recorded −$1,204.48 over 65 days,
which evidently never matched IBKR reality — one of the reasons the pivot reset
was done. The live account's effective baseline at 5/18 was ~$100,208.)

### 3. Penny-level reconciliation

```
100000 + carry(208.37) + tracked(245.25) + unrealized(212.30) + accrued(12.89)
       = 100,678.81   vs   NetLiq 100,678.44   (Δ $0.37, commission gross/net rounding)

cross-check drift = NetLiq − 100000 − tracked − unrealized = 220.89
                  = carry(208.37) + accrued(12.89) = 221.26   ✓
```

`accrued = NetLiq − cash − pos_mkt = $12.89` = credit interest on the cash
balance (not realized P&L; `dividends = 0` in the summary).

## Conclusion

The ~$218 drift = **pre-pivot cash carry (+$208.37) + accrued interest (+$12.89)**.
There is **no post-pivot daily-tracking bug** — `record_pending_exits` /
`restate_day_realized` have kept tracked cumulative broker-accurate to the penny.

## Recommended resolution (human-in-the-loop — baseline decision)

The cross-check `cumulative_drift` flag compares against a hard $100,000 baseline.
To stop it false-flagging the known carry, pick one:

- **A — Baseline offset constant**: add `baseline_offset_usd: 208.37` (+ an
  `accrued_tolerance`) to `cumulative_pnl.json` / the cross-check, so
  `expected_netliq = 100000 + baseline_offset + tracked + unrealized`. Drift → ~$0.
  Keeps `initial_capital = 100000` honest (the swing strategy's own P&L is still
  measured from 0). **Recommended.**
- **B — Document-only**: leave the flag, annotate the known ~$221 carry+accrued in
  the review template so it's not re-investigated each run.
- **C — Re-baseline**: set `initial_capital = 100208.37`. Simplest arithmetic but
  conflates the pre-pivot carry into the swing baseline (muddies "swing P&L from 0").

All three are reconciliation-bookkeeping; none change live trading or the
broker-authoritative realized figures.
