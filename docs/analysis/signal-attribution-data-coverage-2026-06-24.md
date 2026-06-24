# Signal-attribution data coverage — early-period gap (2026-06-24)

Companion to the `signal_attribution` data-loader wiring (spec §6.1). Records the
recovery investigation Chat mandated for the excluded trades, and the go-forward
gap status. Read-only analysis; no trading state was touched (freeze-safe).

## Sample after position-level aggregation

The loader aggregates ledger legs by `(ticker, entry_date)` into one position
(condition b), so a TP1+TP2/TIME_STOP position is a single data point, not two.

| | count |
|---|---|
| ledger leg-records (`state/pending_exits/*.json`) | 28 |
| unique positions `(ticker, entry_date)` | 20 |
| **included** (entry_score resolved + all legs' realized P&L present) | **12** |
| **excluded** | **8** |

All 12 included positions entered on Day ≥ 9, so for this n the entry-based
`clean` sample equals `full` (a data artifact, reported honestly — it is not a
claim that the early window is represented).

## The 8 exclusions — recovery attempted, NOT reliably recoverable

All 8 are excluded for `realized pnl unavailable (≥1 leg)`: their exits landed
**before the 2026-06-09 `_build_trades_details` fix**, when `daily_metrics.trades.details`
was not yet broker-authoritative per exit. Entries 2026-05-22 → 2026-05-29, exits
2026-05-28 → 2026-06-08.

Recovery sources checked:

1. **`daily_metrics/{exit_date}.json` → `trades.details`** — the file exists for
   every date, but `details` is empty or omits the ticker for the pre-fix days
   (e.g. 06-03 has 2 details, neither is EOG). This is the gap itself.
2. **`scripts/paper_trading/logs/trades_*.csv`** — sparse and inconsistent:
   `EOG`, `JHG`, `ROIV` appear in **no** CSV; `AMH`/`CDNS`/`AKAM`/`ST` rows carry
   mismatched entry dates, a different `exit_type` (MOC, not the ledger
   TP1/TIME_STOP), and `score = 0`. A superseded recording mechanism — not a
   sound per-trade realized-P&L source.
3. **`cumulative_pnl.json → daily_history`** — daily aggregate only; cannot be
   split back to per-trade on days with >1 exit.

**Verdict:** the per-trade realized P&L for these 8 early positions was never
recorded per-trade and is not reliably reconstructable. They remain excluded.
This is the §5 persistence-precondition residual gap, surfaced now (not at Day 63).

## Pre-registered hierarchy preserved (§4.2/2)

The `full` Day 1–63 sample stays the **official gate**; `clean` (entry Day 9+)
stays secondary. The early-window incompleteness (8 unrecoverable positions) is
documented here and does **not** promote `clean` over `full`. Moving the gate
because early data is thin is exactly the manoeuvre the audit was built against.

## Go-forward gap — CLOSED

Since the 2026-06-09 fix (CHANGELOG 2026-06-09, P1+P2), `_build_trades_details`
writes broker-authoritative per-exit detail from the SLD fills (realized_pnl NET
of commission, MOC exits included). New closures therefore reliably capture both
the predictor (`entry_score`, persisted in the ledger since 2026-06-10) and the
output (per-trade realized P&L). Verified on SJM (Day 25, 2026-06-23): ledger
`entry_score = 77.41`, `daily_metrics` detail `pnl = −330.91` (= daily net).
No further wiring needed for future trades.
