# Üzenet a következő CC sessionnek — IFDS folytatás (2026-06-08+)

Másold be a friss `/continue` után, vagy nyisd meg kontextusként. Az előző session (2026-06-06) token-limit miatt zárult; minden commitolva + pusholva + Mac Mini szinkronban.

---

## Élő státusz (2026-06-06 záró)

- **Cumulative realized: +$245.25** (broker-authoritatív, 6/4 + 6/5 restatement után). NetLiq $100,675.60.
- **Tesztek: 1898 passing**, 0 failure, 0 warning. Utolsó commit `9ec6ce5`.
- **Élő trading érintetlen.** 6 nyitott pozíció: AMH, BEN, FFIV, MSM, VNO, WST (state ≡ IBKR ✅).
- Mac Mini = MacBook = origin/master, mind szinkronban. `ssh ifds-mini`.

## Mit végeztünk az utóbbi sessionökben (kész + deployolva)

- **Part A ledger forward-fix** (P0 §0.11) — `record_pending_exits` az egyetlen cumulative writer, clientId=18, ledger `state/pending_exits/`.
- **Day 14 (A/B/C)**: (B) build_daily_metrics exits a cumulative counterekből, (C) re-runok. **(A.2) `ib.fills()`** — a recorder a settled realizedPNL-t olvassa (az A.1 sleep+re-request megbukott a 6/4 smoke-on). **DEPLOYED, hétfő 6/8 az élő smoke.**
- **§5.4** no-exit-nap zero-entry, **3b** Telegram BEST DAY címke, **Telegram EOD finomítás** (NYSE Day-N, top movers, day-change, exit-merge, S_j címkék, Day 21 chkpt, TRADING PLAN shadow-cleanup), **single-position cap** (0.12 resize).
- **Restatementek** (swing-attr → broker-authoritatív, connector `get_account_trades`): Day 9 AMH, Day 12 CDNS, Day 13 (6/3), **Day 14 (6/4) +225.34, Day 15 (6/5) +63.83**. Reusable tool: **`scripts/admin/restate_day_realized.py --date --realized --commission`**.
- **Autonóm review-pipeline**: **1a** `generate_review_data.py` (determinisztikus aggregátor + anomália-flagek), **1b/1c connector-független mag** `generate_review.py` (`build_cross_check_flags` + `render_review_markdown`). 1a→1c éles 6/4-en validálva.

## NYITOTT TASKOK (prioritás szerint)

### 1) `docs/tasks/2026-06-06-data-quality-fix-package.md` — ⭐ ÚJ, OPEN (Chat írta 6/6)
8 data-quality fix a Day 13-15 review-kból. **Ez a fő mai munka.** Deploy-sorrend a task §Deploy-sorrend szerint.
- **P1 (4, sürgős)**:
  - **#1 VIX → Polygon `I:VIX`** — a FRED 1 napos késéssel publikál; a 6/5 daily_metrics `vix_close: 15.78` TÉVES, a valódi 6/5 záró **21.50 (+39.7% risk-off)**. Endpoint `aggregates/v2/ticker/I:VIX/...`, fallback IBKR `get_price_snapshot(I:VIX)`. + Day 1-15 backfill. **KRITIKUS**: a 21.50 már átlépte a Strategic-review 18-as leállítási küszöbét!
  - **#2 EOD Telegram timing** — a 22:05 EOD a 22:10 recorder ELŐTT fut → tegnapi cumulative-t mutat. Tolás 22:11-re (vagy a render a már-frissített cumulative-ból).
  - **#3 `[Day N/63]` NYSE-count** — `pt_eod.py` a régi `trading_days`-t használja; állítsd `daily_metrics.day_number`-re (6/5 = D14 NYSE).
  - **#4 Commission rögzítés** — a `record_pending_exits` paralelben rögzítse a commission-t a ledgerbe + cumulative-ba (audit-trail; jelenleg csak a restatement-ek töltik).
- **P2 (2)**: #5 `weekly_metrics.py` slippage aggregálás (most csak az 1. entry-t veszi), #6 `portfolio_return_pct` definíció-audit.
- **P3 (2 backlog)**: #7 next-day MKT fill kockázat (TP1-limit opció), #8 major-bear TIME_STOP MOC statisztika.

### 2) `docs/tasks/2026-06-04-recorder-robust-realized-capture.md` — WIP
A.2 (`ib.fills()`) deployolva. **HÁTRA: a hétfői (6/8) 22:10 cron az élő smoke** — a recorder végre a broker realized-et kapja-e (recorder realized == connector `get_account_trades`, ≤$1/exit, **0 fallback-warning**)? Ha még mindig fallback → opció-3 (connector-reconciliation admin lépés). Ellenőrzés: `logs/pt_daily_metrics_2026-06-08.log` (`broker_realized_pnl` vs `state_attribution_fallback`).

### 3) `docs/tasks/2026-05-28-automated-daily-review-pipeline.md` — WIP
1a + 1b/1c connector-független mag KÉSZ. **HÁTRA: az 1c LLM review-skill** — a teljes autonóm review-generálás formalizálása (CC-eljárás: 1a → IBKR snapshot MCP-ből → `build_cross_check_flags` → `render_review_markdown` → LLM-narratíva → `docs/review/{date}.md`). A determinisztikus mag tesztelt; ez a "kapcsold ki a Chat-manualitást" cél.

## A három rögzített KÖVETKEZŐ LÉPÉS (Tamás kérése szerint)

1. **~$218 cumulative_drift kivizsgálása** — a 6/6-i ELSŐ éles cross-check P0-t flagelt: cumulative +245.25 + unrealized +211.92 = +457.17, de NetLiq +675.60 → **~$218 reziduum**. Vizsgálat: connector `get_account_trades(DAYS_30)` TELJES realized összege vs a `cumulative_pnl.daily_history` pnl-összeg. Lehetséges ok: Part B canonical Day 1-8 baseline alulbecslés, halmozott commission (lásd #4!), pre-pivot reset reziduum. (Rögzítve a pipeline task §"1b cross-check ELSŐ ÉLES FUTÁS"-ban.)
2. **(A.2) hétfői élő smoke** — lásd fent (2. task).
3. **1c LLM review-skill** — lásd fent (3. task).

## Kritikus kontextus / gotchák

- **IBKR `reqExecutions.realizedPNL` aszinkron** → 0-t ad a recorder-időben; `ib.fills()` (A.2) a megoldás (az eod_report így kapja helyesen). Live verifikáció KÖTELEZŐ (learnings-archive).
- **Swing-attr ≠ broker realized** — a recorder fallback-je a *tervezett* entry-vel számol → nagyot tévedhet (6/5 BEN: +47.50 vs valós +123.27). A `restate_day_realized.py` a connector-értékre javít.
- **Smoke higiénia**: minden ad-hoc smoke `IFDS_TELEGRAM_BOT_TOKEN= IFDS_TELEGRAM_CHAT_ID= python ...` prefixszel (különben élő Telegram megy Tamásnak). Mac Mini cron-futtatás `--date`-tel: `IFDS_SKIP_TRADING_DAY_GUARD=1` (ha nem trading nap).
- **Connector**: az IBKR MCP CC-ből működik (`get_account_trades/summary/positions`), de a CRON-ból NEM (az a Mac Mini ib_insync). A restatement/cross-check CC-oldali manuális lépés.
- **Munkamegosztás**: CC commitol, Tamás pusholja (push explicit jóváhagyással); a Mac Mini deploy Tamás "jóváhagyom" után. Chat írja a napi review-kat (`docs/review/`), CC az automatizációt.

## Files / parancsok
- Restatement: `python scripts/admin/restate_day_realized.py --date YYYY-MM-DD --realized X --commission Y --apply`
- 1a: `python scripts/paper_trading/generate_review_data.py --date YYYY-MM-DD`
- 1c scaffold: `python scripts/paper_trading/generate_review.py --date YYYY-MM-DD`
- Tesztek: `IFDS_TELEGRAM_BOT_TOKEN= IFDS_TELEGRAM_CHAT_ID= python -m pytest tests/ -q` (baseline 1898)

Sok sikert. A financial-kritikus rész broker-pontos, minden tesztelt és deployolt; a fő mai munka a data-quality fix-package P1-je (VIX először).
