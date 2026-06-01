# Üzenet a következő CC sessionnek — Part A ledger forward-fix (P0 §0.11)

Másold be a friss `/continue` után, vagy nyisd meg ezt a fájlt és add hozzá kontextusként.

---

Szia. Egy P0 implementációt kell befejezni — **a teljes terv egy lemezen lévő locked spec-ben van**, a környezet tiszta és deploy-ready. Az előző session a túl hosszú futás + ismétlődő API 400 "thinking blocks" hibák miatt lezárult mielőtt élő trading scriptet módosított volna (helyes döntés volt — egy félbeszakadt edit egy SELL-t kockáztatott).

## 1) Olvasd be ELŐSZÖR a LOCKED specet

`docs/tasks/2026-05-29-part-a-ledger-forward-fix-spec.md`

Minden döntés benne FINAL. Ne kérdezz vissza tervkérdésekben — végrehajtás.

## 2) Kontextus, amit a spec NEM ismétel meg

- **Mai dátum: 2026-06-01 (szombat).** Élő trading nincs hétvégén — **ideális idő a deploy-ra**, mert a hétfői 21:40 close hozza az első éles próbát.
- **Részvénygazda**: Tamás. Ő pusholja a commitokat (`CC commitol, Tamás pusholja`), Mac Mini-re az `ssh ifds-mini` aliasszal jutsz.
- **Tesztbaseline**: utolsó verifikált 1828 passing (Part B után). A te változtatásaid + tesztjeid után 0 regresszió maradjon, full suite zöld.
- **Guard-fixek élnek**: `0b2ddaa` (days_held trading-day) + `4f2f8c0` (ATR band 0.5–5%). Day 9-en ST + ROIV ezen átment, tiszta belépés.
- **Canonical baseline**: `7f031e6` — `cumulative_pnl.json` cumulative = **-$651.10**, trading_days=8 (Day 1-8). Mac Mini-re alkalmazva. **Ezt NE bántsd, csak hozzáírj**.
- **Day 9 (5/28) AMH MOC** lezárt, de a cumulative 5/28 entry még pnl=0 — ezt a Part A első futása fogja befogni a spec 4. + Deploy step 4 szerint (AMH ledger seedelés + `--date 2026-05-28`).
- **Uncommitted, doc-only** (commitold a Part A commitsorozat előtt vagy után, ahogy passzol): `04-risks` §6.5 (SMA-inflexió exit-overlay, Chat által felvetett vizsgálat) + a `docs/tasks/2026-05-29-part-a-ledger-forward-fix-spec.md` maga.

## 3) Megerősítés Tamástól, mielőtt a Mac Mini-n élesítesz

Mac Mini-re NE pull-olj és deploy-olj jóváhagyás nélkül. A munkamenetben Tamás kifejezetten szólni fog: *"jóváhagyom a push + deploy-t"*. Addig: lokálisan írj, tesztelj, commitolj, pusholj jóváhagyással. A `git push origin master` egy explicit jóváhagyás-pont az auto-mode classifier miatt is.

## 4) Verifikációs lépések amiket a spec felsorol, de itt kiemelek

- **clientId=18 free**: `grep -rn "client_id\s*=\|clientId=" scripts/paper_trading/ | grep -oE "=\s*[0-9]+" | sort -u` — verifikáld, hogy 18 nem foglalt (a meglévők: submit=10, close=11, eod=12, nuke=13, monitor=14, trail=15, avwap=16, gateway=17).
- **`daily_metrics.main()` call order**: `record_pending_exits` ELŐBB fut, mint `build_daily_metrics`, hogy a build a frissített cumulative-t lássa.
- **`fetch_today_executions` backfill módban** — a meglévő helper (`lib/ibkr_reconciliation.py`) a `today: date` paramétert kapja, és post-filterel `exec_date != today` ellenőrzéssel. Verifikáld, hogy ez egy backfill-dátumra is jól szűr (`--date 2026-05-28` esetén). Ha nem: paraméterezhetővé tedd a target_date-et a hívási oldalon.
- **TP1 partial konvenció**: a ledger-write a SOLD qty-t rögzítse (50%-ot), `exit_type=TP1`. A maradék pozíció továbbra is nyitva van a state-ben.
- **try/except a ledger-write körül a close_positions-ban**: SOHA NEM blokkolhatja a SELL-t. Csak logger.warning + opcionális Telegram WARNING.

## 5) Commit szekvencia (a spec §8 sorrendje szerint)

1. `refactor(lib): move pure pnl helpers from retroactive_reconcile_w21 to lib/ibkr_reconciliation` (a "TIt ME_STOP" → "TIME_STOP" typo javítás is ide tartozik, ha találkozol vele)
2. `feat(pnl): pending-exits ledger module (lib/pending_exits.py)`
3. `feat(close_positions): write pending-exit ledger entries (try/except guarded)`
4. `feat(daily_metrics): record_pending_exits — sole cumulative_pnl writer + --date backfill`
5. `feat(eod_report): neutralize cumulative write + add silent-0-pnl Telegram WARNING`
6. `test(pnl): ledger + record_pending_exits + helpers (Part A regression suite)`
7. `data(reconcile): Day 9 AMH ledger seed + first ledger run (-651.10 → -???.??)`

Az utolsó (data) commit a live smoke utáni dokumentumolt állapot — a cumulative az AMH bevonásával frissül. A Day 9 AMH realized P&L pontos értékét a connector `get_account_trades` adja vissza (DAYS_30), AMH SELL fill 2026-05-28 dátummal.

## 6) Ha valami félresikerül a smoke-ban

- A `cumulative_pnl.json.bak.pre_canonical.*` backup ott van — Mac Mini-n `scripts/paper_trading/logs/` alatt.
- A `state/pending_exits/2026-05-28.json` ledger entry is törölhető, ha újra kell seedelni.
- A canonical reconstruction script továbbra is működik mint utolsó fallback — `python scripts/admin/canonical_pnl_reconstruction.py --apply` visszaállít a -$651.10 baseline-ra (DE ne fusson, ha már Part A is írt a fájlba, mert wholesale replace-eli a daily_history-t).

## 7) Munkamegosztás

Memóriában mentve: **Chat = stratégia + tervezés, CC = review + bugfix + automatizáció**. A Part A spec maga Chat-i terv (a session során finomítottam, Tamás jóváhagyta) — a te dolgod a **végrehajtás**.

Sok sikert. A spec-ben minden megvan ami kell.
