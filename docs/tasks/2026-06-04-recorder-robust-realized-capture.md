Status: OPEN
Updated: 2026-06-03
Note: Day 13 (2026-06-03) első multi-exit incidens — Option B reqExecutions.realizedPNL=0 élőben. Safety-fix + restatement már deploy-olva; ez a ROBUSZTUS fix + a kapcsolódó metadata-source fix.

# Recorder — robusztus broker-realized capture + daily_metrics exits-source fix (P1)

**Priority**: P1 — pénzügyi-rögzítési pontosság (a safety-fix már megakadályozza a néma $0-t, de a realized becsült, nem broker-pontos)
**Becsült**: ~2-3h CC + live smoke a következő exit-napon
**Érintett**: `scripts/paper_trading/lib/ibkr_reconciliation.py`, `scripts/paper_trading/daily_metrics.py`

## Háttér — Day 13 incidens (2026-06-03)

Az első éles multi-exit (AKAM TP1 8@156, ST TP1 47@52.51, EOG TIME_STOP 44@141.55) a recorderben (22:10) **mindhárom realized-et $0.00-nak rögzítette** — a `reqExecutions().commissionReport.realizedPNL` aszinkron populálódik, és 22:10-kor még 0 volt. Az `ib.fills()` (eod_report 22:05) és a connector `get_account_trades` viszont megadta a valódi értéket (Σ **+$229.84**).

**Már deploy-olva (2026-06-03 este, commit `ce3f129`)**:
- **Safety-fix**: `fetch_today_executions` a `realizedPNL == 0.0`-t UNAVAILABLE-ként kezeli → `None` → recorder fallback swing-attribúcióra + warning (nincs néma $0). DE a swing-attribúció a *tervezett* entry-ből számol → pontatlan (Day 13-on EOG: swing-attr ~$14.5 vs valós $48.46, mert a state entry $141.22 ≠ valós cost basis ~$140.45).
- **Restatement**: `restate_20260603_exits_pnl.py` → 6/3 +$229.84, cumulative **-43.92**.

## A) Robusztus realized capture (a fő feladat)

A cél: a recorder a **broker-authoritatív net realized**-et kapja meg megbízhatóan, ne 0-t és ne a pontatlan swing-attribúciót. Opciók (mérendő a következő exit-napon élőben):

1. **`ib.sleep()` a commissionReport event-ekre** — `reqExecutions` után várni (pl. 3-5s), hogy a `commissionReport` async event-ek megérkezzenek, majd újraolvasni. Legkisebb változás, de a timing törékeny lehet.
2. **`ib.fills()` használata `reqExecutions` helyett** — a `Fill` objektumok a `commissionReport`-tal együtt jönnek, miután az event-ek beérkeztek (connect + sleep után). Az eod_report ezt használja és **helyesen** kapta a +$181-et. Valószínűleg ez a legjobb.
3. **Connector `get_account_trades` reconciliation** — a 22:10 recorder után (vagy másnap) egy reconcile-lépés a connector realized_pnl-jével felülírja a fallback-becslést. Robusztus, de connector-függő (nem cron-natív).

**Javaslat (mérendő)**: (2) `ib.fills()` + connect-utáni `ib.sleep(2-3)`; ha a realized még így is hiányos, (1) explicit várakozás a `commissionReport` event-re. **KÖTELEZŐ live smoke** a következő exit-napon (lásd ifds-rules: rate-limit/élő-verifikáció szabály — itt a realized-timing élő verifikáció).

**Siker-kritérium**: a következő multi-exit napon a recorder a connector `get_account_trades`-szel **megegyező** realized-et rögzít (≤$1 eltérés/exit), 0 fallback-warning.

## B) daily_metrics exits-source fix (a Day 13 metadata-glitch)

A 6/3 `daily_metrics` `exits` blokkja `moc:2`-t mutat (helyesen **tp1:2 + moc:1**), mert az eod_report **létrehozott egy trades CSV-t** (AKAM+ST-t MOC-ként félrecímkézve + EOG-t kihagyva), és a `build_daily_metrics` a CSV-t részesíti előnyben. A #3b metadata-sync csak ÜRES CSV esetén aktivál — de a CSV jelenléte **nem determinisztikus** (attól függ, az `ib.fills()` lát-e exitet 22:05-kor).

**Fix**: a `build_daily_metrics` az **`exits` blokkot MINDIG a cumulative `daily_history` counterekből** vegye (tp1_hits/tp2_hits/sl_hits/loss_exit_hits/trail_hits/moc_exits) — a recorder ezek authoritatív forrása —, függetlenül a trades CSV jelenlététől. A CSV maradhat a `scoring`/`slippage` forrása (azt a recorder nem rögzíti), de az exit-típusok a ledger/cumulative-ból jöjjenek. Plusz: a P&L (gross/net/commission) is a cumulative-ból (a CSV `pnl` az eod portfolio-realized, ami szintén lehet hiányos).

**Teszt**: trades CSV JELEN van (eod MOC-labelekkel) DE a cumulative daily_history tp1_hits=2/moc_exits=1 → a `build_daily_metrics` exits blokkja tp1:2, moc:1 (NEM a CSV moc:2-je). Regresszió a 6/3 esetre.

## C) Day 13 daily_metrics korrekció

A B) fix landolása után re-run: `daily_metrics.py --date 2026-06-03` → az exits blokk javul tp1:2/moc:1-re (a cumulative már most helyes, csak a daily_metrics.json metadata-ja téves).

## Verifikáció / deploy

- Full suite zöld (baseline 1875).
- Live smoke a következő exit-napon (A pont siker-kritérium).
- Mac Mini deploy Tamás jóváhagyással.

## Kapcsolódó
- Incidens commit: `ce3f129` (safety-fix + restatement)
- Option B alap: `9b2a95a`
- A periodikus connector-realized reconciliation egyébként az autonóm review-pipeline (`2026-05-28-automated-daily-review-pipeline.md`) §5 cross-check-jének is része lehet.
