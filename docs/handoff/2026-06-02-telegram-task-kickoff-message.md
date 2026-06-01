# Üzenet a következő CC sessionnek — Telegram EOD finomítás + TRADING PLAN cleanup (phase 2)

Másold be a friss `/continue` után, vagy nyisd meg ezt a fájlt kontextusként.

---

Szia. Egy **display-only Telegram finomítás** vár implementációra — a teljes terv egy lemezen lévő, döntés-zárt task fájlban van. Tiszta, deploy-ready környezet.

## 1) Olvasd be ELŐSZÖR a task fájlt

`docs/tasks/2026-06-01-telegram-eod-finomitas.md` (Status: OPEN)

**Minden döntés FINAL** (Chat + előző CC review + Tamás sign-off egyesítve). Ne kérdezz vissza tervkérdésekben — végrehajtás. A §7 opció már eldöntve: **Option A** (1-soros shadow-jelzés).

## 2) Mi ez, dióhéjban

A swing pivot EOD Telegram (`swing_telegram.format_swing_compact_telegram`) 6 kisebb finomítása + a TRADING PLAN (`telegram._format_phases_5_to_6`) legacy GEX/MMS/breadth/crowd mezőinek swing-era takarítása. **Nincs trading-logika érintés** — render + 1 kis adatmentés (`total_equity`). Scope ~2-3 óra.

A 6+1 pont (részletek a taskban):
1. **Day-N** → NYSE trading-nap count (`ifds.utils.trading_calendar`, `start_date=2026-05-18`), NEM `cumulative_pnl.trading_days`. 6/1 = **Day 10**. `daily_metrics.day_number` + `eod_report` override + header mind ezt használja.
2. **Top movers** 3-3, csak |upnl| ≥ $50. Plumbing: `eod_report` a már lekért `ib.portfolio()` per-pozíció `unrealizedPNL`-ből építsen `metrics["pnl"]["per_position_unrealized"]` dict-et.
3a. **Day change** — új `state/daily_equity.json` store (eod_report írja `ib.accountSummary()` NetLiquidation-ből 22:05-kor). **NE** a `cumulative_pnl.json`-ba (Part A single-writer invariáns!). Backward-compat: hiányzó equity → "n/a". (3b BEST DAY = külön későbbi task, NE most.)
4. **Exit-merge** — a duplikált triggered/holnap sorokat egy gazdag sorba (entry→mark, +%, várt fill).
5. **Top S_j címke** — `[holding]`/`[selected]`/`[skipped]` (`swing_positions` + `new_entries_tickers`).
6. **Day 21 checkpoint** — `📍 Day 21 chkpt: $cum / $-1,500 (X% buffer, N days left)`.
7. **TRADING PLAN (Option A)** — a teljes `[5/6] GEX Analysis` blokk → `[5/6] Shadow signals\nGEX / MMS / breadth / crowd: collected (shadow — nem dönt)`. A `[6/6] Position Sizing` változatlan. SUBMIT/CLOSE: nincs változás (auditálva, tiszták).

## 3) Kontextus, amit a task nem ismétel

- **Mai dátum a session-indításkor: 2026-06-02 (kedd) körül.** A 6/1 (hétfő) volt Day 10; a Telegram most tévesen "Day 9"-et mutat (ezt javítja §1).
- **Tesztbaseline: 1862 passing** (Part A deploy után). A te változtatásaid + tesztek után 0 regresszió, full suite zöld.
- **Részvénygazda: Tamás** — ő hagyja jóvá a push + deploy-t (`CC commitol, Tamás pusholja`). Mac Mini: `ssh ifds-mini`.
- **Smoke higiénia (KRITIKUS)**: minden `eod_report.py --dry-run` smoke-ot `IFDS_TELEGRAM_BOT_TOKEN= IFDS_TELEGRAM_CHAT_ID= python ...` env-clear prefixszel futtass — különben a `load_dotenv()` ÉLES Telegram üzenetet küld Tamásnak (memóriában: smoke-no-external-send-with-dotenv). Mac Mini-n a `source .env`-vel betöltött tokenek is ezt okozzák.
- **Mac Mini Python**: a `source .env` NEM exportálja a kulcsokat a Python subprocessbe (dotenv-stílus) → a scriptekben `load_dotenv()` kell, vagy `python-dotenv`-es entrypoint.

## 4) Élő státusz a session végén (2026-06-01)

- **Part A (P0 §0.11) DEPLOYED** — pending-exit ledger forward-fix él. `record_pending_exits` az egyetlen cumulative writer (clientId=18), `close_positions` guarded ledger-write, `eod_report` cumulative-write OFF. **Cumulative: -$708.58** (Day 9 AMH backfill -$57.48 broker-authoritatív). Backup: `cumulative_pnl.json.bak.pre_partA.20260601_140510`.
- **Day 11 (6/1)**: 0 exit, 1 új entry (WST 18@324.33), **CDNS TP2 flag Day 12-re** (entry $373.85 → mark $414.33, várt realized ~+$506). **Ez lesz a Part A első éles same-day rögzítési próbája** a 6/2 22:10 cron-on — érdemes ránézni: `state/pending_exits/2026-06-02.json` + a 22:10 `daily_metrics` log + cumulative mozgás.
- **WST execution-finding**: a 6/1 WST fill $324.33 vs valós nyitás $321.65 = +$2.68 paper-fill anomália (~$48 fantom). NEM szisztematikus (14/15 belépő realisztikus). Rögzítve: `docs/review/2026-06-01-daily-review.md` §2 + `learnings-archive`.

## 5) Commit szekvencia (a task §"Commit szekvencia" szerint)

1. `feat(telegram): NYSE trading-day count for swing EOD Day-N` (§1)
2. `feat(telegram): top movers + day-change in swing EOD (total_equity store)` (§2 + §3a)
3. `feat(telegram): exit-merge detail + Top S_j status labels + Day 21 checkpoint` (§4-6)
4. `refactor(telegram): swing-era TRADING PLAN cleanup — demote shadow GEX/MMS/breadth/crowd` (§7)
5. `test(telegram): swing EOD render regression (day-N, movers, day-change, labels)`

## 6) Munkamegosztás

Chat = stratégia + tervezés, CC = review + bugfix + automatizáció. Ez a task Chat-terv + CC-review egyesítése, Tamás jóváhagyta — a te dolgod a **végrehajtás**. TDD (tesztek a render-logikára), full suite zöld, lokális commit, push/deploy Tamás jóváhagyással.

Sok sikert. A taskban minden megvan.
