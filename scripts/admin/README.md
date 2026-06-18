# scripts/admin/

Administrative scripts for the live `cumulative_pnl.json` ledger. Two kinds:

## Reusable tools (safe to re-run)

| Script | Purpose |
|---|---|
| `restate_day_realized.py` | Restate a day's realized P&L from the broker-authoritative IBKR `get_account_trades` (DAYS_30). General-purpose. |
| `canonical_pnl_reconstruction.py` | Rebuild `cumulative_pnl.json` totals/`trading_days` from `daily_history`. |

## One-off historical scripts — DONE, do **not** re-run

Date-specific restatements / backfills / reconciliations run once against the live
ledger. Kept in place (they use repo-root-relative `lib` imports, so they are not
moved) and recorded here for the audit trail only.

| Script | What it did (one-off) |
|---|---|
| `backfill_2026-06-01_zero_row.py` | Inserted the missing 2026-06-01 zero `daily_history` row (`trading_days` 20→21, $0 impact). Applied on the Mini 2026-06-17. |
| `backfill_amh_day9_pnl.py` | Backfilled Day 9 (2026-05-28) AMH TIME_STOP realized −$57.48. |
| `restate_cdns_day12_pnl.py` | Restated Day 12 CDNS TP2 ($450.10 → $434.82). |
| `restate_20260603_exits_pnl.py` | Restated 2026-06-03 exit P&L after the reqExecutions `realizedPNL=0` incident. |
| `seed_amh_day9_ledger.py` | Seeded the AMH Day 9 pending-exit ledger entry (paired with the backfill). |
| `retroactive_reconcile_w21.py` | W21 retroactive state↔IBKR reconciliation (VLO Day 4 SL + ON Day 5 TP1). Has unit tests (`tests/test_retroactive_reconcile_w21.py`). |
