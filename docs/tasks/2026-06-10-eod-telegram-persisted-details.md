Status: OPEN
Updated: 2026-06-09
Note: A 2026-06-09-daily-metrics-execution-fix Day 17 verifikáció másodlagos finding-je. Az eod_report 22:11 Telegram `Trades:` száma a clientId-12 saját fill-jeiből épül, ami NEM látja a cross-client MOC fill-eket (Day 17: `Trades: 1` vs valós 2). A persisted daily_metrics helyes — az eod onnan olvasson.

# eod_report Telegram: trades.details a persisted daily_metrics-ből (P2)

**Priority**: P2 (másodlagos display-konzisztencia, NEM P&L-kritikus)
**Becsült CC effort**: ~1h
**Érintett**: `scripts/paper_trading/eod_report.py`

## Háttér

A 2026-06-09 (Day 17) esti EOD-on a `daily-metrics-execution-fix` #1+#2 **éles
verifikációja zöld** lett a persisted `daily_metrics/2026-06-09.json`-ban
(slippage IBKR fill-ból, trades.details=2: VNO TP1 + WST TIME_STOP_MOC). DE az
**eod_report 22:11 Telegram `Trades: 1`-et mutatott** (nem 2-t).

**Gyökérok**: az `eod_report.py:665` `logger.info(f"Trades: {len(trades)}")` és a
Telegram `closed_trades_today` a clientId-12 saját `ib.fills()`-éből / a
`trades_*.csv`-ből épül, ami:
- nem látja a **cross-client MOC fill-eket** (a WST 22:00 MOC-ot a
  `close_positions.py` clientId-11 adta be) — pontosan az a cross-client
  láthatósági korlát, amit a Part A a daily_metrics-nél (clientId-18 +
  pending_exits ledger) megoldott.

A **persisted `daily_metrics/{date}.json` viszont helyes** (a 22:10 cron a
clientId-18 `fetch_today_executions_safe`-fel mind a 2 exitet látta, `matched=2`).
Az eod_report **22:11-kor fut, a 22:10 daily_metrics UTÁN** — tehát a fájl már
kész és autoritatív, amikor az eod a Telegramot rendereli.

## Scope

- Az `eod_report` a Telegram `trades.details` + `closed_trades_today` mezőhöz a
  **már megírt `state/daily_metrics/{date}.json` `trades.details`-ét** olvassa
  (autoritatív), NE a saját clientId-12 fill-jeiből / CSV-ből rebuild-elje.
- Megközelítés: a `build_daily_metrics` hívás UTÁN, ha létezik a persisted
  `daily_metrics/{date}.json` (a 22:10 cron írta), annak `trades.details`-ét
  preferálja a `metrics["trades"]`-be + a `closed_trades_today`-t
  `len(persisted details)`-re állítsa. Fallback: a jelenlegi clientId-12
  rebuild (ha a fájl még nincs meg — pl. manuális/korai futás).
- A 665-ös `logger.info(f"Trades: {len(trades)}")` log-sor is a persisted
  details-számot mutassa (vagy egészüljön ki: `Trades(eod-fills): N | persisted: M`).

## Acceptance

- Egy cross-client MOC napon (mint Day 17) a 22:11 Telegram `Trades:` ==
  a persisted `daily_metrics::trades::details` count (Day 17: 2, NEM 1).
- A `P&L today` és a `Trades:` konzisztens (mindkettő a Part A / persisted
  autoritatív adatból).
- Unit-teszt: eod a persisted daily_metrics details-t preferálja, ha létezik;
  fallback a saját fills-re, ha nem.
- Regresszió: a meglévő eod_report tesztek zöldek maradnak.

## Verifikáció

- Day 18+ (következő cross-client MOC nap) esti EOD: a Telegram `Trades:` ==
  persisted details count.

## Kapcsolódó

- `2026-06-09-daily-metrics-execution-fix.md` (DONE) — ennek a Day 17
  verifikációja tárta fel a finding-et. A #1/#2 mag (persisted daily_metrics)
  helyes; ez csak az eod-Telegram display-réteg.
- `2026-06-04-recorder-robust-realized-capture.md` (DONE, Part A) — a
  cross-client fill-láthatóság gyökér-megoldása (clientId-18 + ledger); az eod
  most ehhez igazodik (a persisted adatot olvassa).
