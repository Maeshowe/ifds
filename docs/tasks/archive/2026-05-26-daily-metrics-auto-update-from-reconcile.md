# Task — Daily Metrics + Cumulative PnL auto-update from reconcile closures (Rész 3 follow-up)

Status: DONE (SUPERSEDED)
Updated: 2026-06-04
Note: A task lényegét (close-exit P&L + counters automatikus rögzítése a cumulative_pnl/daily_metrics-be) a **Part A** (P0 §0.11, commit 66faf29.., `record_pending_exits` az egyetlen cumulative writer + ledger) + a **Day 14 fix** (Option B broker-realized, build_daily_metrics exits-source a cumulative counterekből, no-exit-nap zero-entry §5.4) **teljesen megoldotta**. A retroactive operator-workaround (retroactive_reconcile_w21.py) helyett most a forward-fix ledger automatikusan rögzít. Ez a task ezzel obsolete.
Priority: P1 (NEM blokkoló a Day 7 deploy-ra — operator workaround a retroactive_reconcile_w21.py)
Created: 2026-05-25
Owner: Claude Code
Estimated effort: ~2-3h CC (logic + tests + integration)

**Source**:
- [`docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md`](2026-05-23-state-reconciliation-from-ibkr.md) Rész 3 (eredeti scope)
- 2026-05-25 deploy döntés: Rész 1 + 2 elég a Day 7 cron-ra, az auto-patch W22-re tolódik

---

## 1. Probléma

A `pt_monitor.py::_reconcile_state_from_ibkr` (deployed 2026-05-25 commit `5c8e79a`) detektálja az autonóm bracket trigger-eket (Day 4 VLO SL minta), tisztítja a state-et, és Telegram alert-et küld. **DE NEM frissíti automatikusan** a `daily_metrics/YYYY-MM-DD.json` és `cumulative_pnl.json` fájlokat. A jelenleg operatív workaround: Tamás manuálisan futtatja a `retroactive_reconcile_w21.py`-t (vagy egy paraméterezett successor-t) a closures-szal.

A Day 7+ trading napokon ez **operator burden** — minden bracket trigger után manual reconciliation needed.

## 2. Cél

A `pt_monitor._reconcile_state_from_ibkr` mostantól ne csak a state-et, hanem a `daily_metrics` + `cumulative_pnl` fájlokat is patch-elje automatikusan a detektált closures alapján.

## 3. Implementáció vázlat

### 3.1 Reusable helpers a lib/ibkr_reconciliation.py-ba

A `retroactive_reconcile_w21.py`-ben definiált helpers mozgatandó a `lib/ibkr_reconciliation.py`-be (DRY):

- `append_trade_to_daily_metrics(daily_metrics, trade, new_cumulative)` — pure
- `update_cumulative_history_entry(cum_data, date, **deltas)` — pure
- `recompute_cumulative_pnl(cum_data)` — pure

A `retroactive_reconcile_w21.py` átalakítható thin orchestrator-ré, ami csak a Day 2/4/5 konstansokat tartalmazza és az új közös helpereket hívja.

### 3.2 Új helper: apply_closures_to_metrics

```python
def apply_closures_to_metrics(
    closures: list[dict[str, Any]],
    *,
    daily_metrics_path: Path,
    cumulative_pnl_path: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Patch daily_metrics + cumulative_pnl from a ReconcileReport's closures.

    For each closure dict (with ticker, exit_type, fill_price, qty, gross,
    commission, entry_price):
    1. Build a TradeRecord (entry, exit, qty, exit_type, gross, commission, net)
    2. Append to daily_metrics.trades.details + bump exits.* counter
    3. Update cumulative_pnl.daily_history[today] with pnl/commission/counters
    4. Recompute cumulative_pnl.cumulative_pnl

    Returns a summary dict (for logging + Telegram).
    """
```

### 3.3 pt_monitor.py integráció

A `_reconcile_state_from_ibkr` végén:

```python
if report.detected_closures and not dry_run_mode:
    summary = apply_closures_to_metrics(
        report.detected_closures,
        daily_metrics_path=Path(f"state/daily_metrics/{date.today().isoformat()}.json"),
        cumulative_pnl_path=Path("scripts/paper_trading/logs/cumulative_pnl.json"),
    )
    logger.info(f"[SWING EOD] daily_metrics + cumulative_pnl auto-patched: {summary}")
```

### 3.4 Edge cases

- **Race condition with 22:10 daily_metrics cron**: a `daily_metrics.py` 22:10-kor építi újra a `daily_metrics/YYYY-MM-DD.json`-t a trades.csv-ből. Ha a pt_monitor 22:00-kor patch-elte, és aztán a 22:10 felülírja — **data loss**. Megoldás: vagy (a) a daily_metrics.py 22:10 előtt olvassa az IBKR closures-t és integrálja, vagy (b) a pt_monitor 22:00 patch-e egy külön mezőbe írjon (pl. `extra_closures: [...]`) amit a daily_metrics 22:10 figyelembe vesz.
- **Idempotency**: ha a reconcile kétszer fut (pl. ad-hoc smoke teszt), ne duplázza a closures-t. Sentinel-mintás védelem mint a retroactive script.

## 4. Acceptance criteria

- [ ] `lib/ibkr_reconciliation.py::apply_closures_to_metrics` implementálva + 5+ teszt
- [ ] Race condition pattern eldöntve + dokumentálva
- [ ] `retroactive_reconcile_w21.py` átalakítva thin orchestrator-ré (DRY refactor)
- [ ] `pt_monitor.py::_reconcile_state_from_ibkr` integráció
- [ ] Smoke test: egy mockolt bracket trigger end-to-end — state cleanup + daily_metrics patch + cumulative_pnl update mind egy reconcile futás során
- [ ] Backwards-compatibility: a retroactive_reconcile_w21.py még mindig fut és ugyanazt az eredményt adja

## 5. Notes

- A jelenlegi workaround (Tamás manual retroactive_reconcile run) **elég a Day 7-10 ablakra** — a Rész 3 nem kritikus.
- Ha bracket-trigger ritka (Day 4-5 W21 mintázat: 2/5 nap), a manual workflow elviselhető 1-2 hétig.
- A Day 21 (≈ 2026-06-08) checkpoint előtt érdemes deploy-olni, hogy a weekly_metrics.py automatikusan helyes adatot lásson.

## 6. Kapcsolódó

- `scripts/admin/retroactive_reconcile_w21.py` (forrás-helpers)
- `scripts/paper_trading/lib/ibkr_reconciliation.py` (cél-helper)
- `scripts/paper_trading/pt_monitor.py::_reconcile_state_from_ibkr` (integráció pont)
- `scripts/paper_trading/daily_metrics.py::build_daily_metrics` (race condition target)
