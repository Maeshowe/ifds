# IFDS Log Review — Handoff (2026-06-26 záró, W26 vége)

**Készült:** 2026-06-26 (péntek, Day 28 review után)
**Chat:** IFDS — Log Review & Ops
**Indok:** kontextus ~75%+, 12 napi review-sorozat (06-11 … 06-26) lezárva
**Következő session első napja:** 2026-06-29 (hétfő, Day 29, W27 D1)

---

## 1. Állapot egy pillantásra (Day 28, 2026-06-26 close)

- **Cumulative: +$540,05** (+0,54%) — `cumulative_pnl.json`, `trading_days=28=day_number` ✓
- **Net Liq (IBKR verifikált): $101 339,17** — +$1 339 a startvonal fölött
- **Nyitott könyv unrealized: +$418,68** (6/8 zöld)
- **Nyitott pozíciók: 8** — AXTA, IEX, NSA, R, PFGC, SLGN, RBC(qty 5, post-TP1 trail), TDG(qty 2, post-TP1 trail)
- **Csúcs: +$1 735,02 (06-11, Day 18)** → -$1 195 drawdown 7 trading napon át, az utolsó 3 nap (06-24/25/26) stabilizálódott (flat: -21/+2/+3)
- **Silent OK számláló: 23/23**

## 2. Trading-narratíva (W25–W26, a drawdown-ablak)

- 06-11 (Day 18): csúcs +$1 735,02 (NSA TP2 +$176, BEN TIME_STOP +$160)
- W25 (06-15…06-18): -$450,16, mind a 4 exit TIME_STOP (FFIV -152, TKR +134, ACHC -271, VNO -161)
- W26 (06-22…06-26): -$744,81 (a deploy legnagyobb heti vesztesége), de **+1,65% excess egy -2,39% SPY-héten** (long-only defenzíven viselkedett)
- **Take-profit aszály**: 06-11 NSA TP2 óta 10 trading nap 0 TP-hit; **06-26-án megtört, de árnyaltan** (RBC TP1 -$32,38 veszteséggel, TDG TP1 +$35,75 — lásd §3)

## 3. NYITOTT SZÁLAK (prioritás szerint)

### Day 63-input tételek (Dev-chat felé, `04-risks-and-open-questions.md`)
1. **🔴 scoring_validation.py legacy-swing pooling** — a `docs/analysis/scoring-validation.md` (06-26 futás) **458 trade / 70 trading napon** = legacy intraday + swing keverve (bizonyíték: LOSS_EXIT/NUKE/SL legacy exit-típusok, score range 0–142,5, fejléc „28 nap" vs summary „70 nap"). A „**Evidence of alpha**" felirat **félrevezető**: a score vs excess -0,151** **negatív** = a magas score rosszabb hozamot jelez (high-score paradoxon), NEM pozitív alpha. A Q5 a legrosszabb (-$566,81, 42,4% win). **Javasolt CC-task: swing-only szűrő** (entry_date ≥ 2026-05-18 ÉS exit_type ∈ {TIME_STOP, MENTAL_SL, TP1, TP2, TRAIL}, a legacy kizárva). Ne propagálódjon az „alpha"-felirat a Day 63 döntésbe. A `signal_attribution.py` a pre-regisztrált út; ez a leíró kiegészítő.
2. **🔴 TP1-mechanika flag→fill lag** (06-26-on derült ki) — a TP1 **partial exit** (fél pozíció elad, maradék trail), és a flag-nap **másnapján 15:30-kor** tölt, NEM a TP1-áron. RBC „TP1"-ként -$32,38-cal zárt (fill $635,45 a TP1 $667,07 ÉS az entry $643,55 alatt), mert a 06-25-i intraday-high flag után a 06-26 gap-down nyitón töltött. **A „TP1" címke nem garantál profitot.** Day 63 edge-audit input.
3. **tp1_hit → kimenet mintázat (ELLENPÉLDÁVAL)** — tp1_hit=false → 7 negatív / 1 pozitív (CORT 06-25 +$34,10 az első kivétel); tp1_hit=true → 2/2 pozitív (TKR, BEN). n=10 exit. A mintázat már nem tiszta bináris — a Day 63 attribution kvantitatívan dönti el. **Mind a 8 jelenleg nyitott pozíció tp1_hit=false volt belépéskor.**

### CC-task tételek (implementáció, nem analízis)
4. **🔴 weekly_metrics TP1-statisztika korrupció** (§6.2, 06-26) — a `2026-W26.md` „TP1 avg profit -$109,18 / 3 hits"-et ír, broker-valóság 2 hit avg +$1,69. Gyökérok: az `exits_today` flag-számláló (lásd #5) szennyezi a weekly TP1-aggregátot. **Konkrét hibás riport-szám, nem elvi kockázat.** Fix: weekly TP1-forrás legyen `exits{}` v. broker-ledger, NE `exits_today`.
5. **exits_today flag-számláló bug** — a `daily_metrics::swing_state::exits_today` a **következő napra beállított flageket** számolja, nem a ma végrehajtott exiteket (06-22: MENTAL_SL:1 flag; 06-24: TIME_STOP:2 flag; 06-26: TIME_STOP:1 = hétfői AXTA flag). Az `exits{}` blokk helyes. Fix: csak lefutott exitek.
6. **exit_type-determináció bug** (P1, régi) — a `daily_metrics::trades::exit_type` fill-timestamp alapú, megbízhatatlan (06-23 SJM MENTAL_SL → „TP1" címke). A `03c77d8` az eod Trades-SZÁMOT javította, az exit_type-determinációt NEM. A `record_pending_exits` + `exits{}` aggregát helyes.

### Megfigyelések (nem akció, követés)
7. **Net Liq-reziduum** — stabil ~+$390±30 (06-16…06-26: 372/375/423/407/388/411/363/380). Fix számviteli offset, nem növekvő szivárgás. Valószínű összefüggés a planned-vs-broker entry-tárolással (§6.5). Ha kilép a sávból → CC-vizsgálat.
8. **Notional-pálya** — 29,72% (06-12) → csúcs 50,11% (06-23) → 43,14% (06-26). Az 50%-ot az Industrials-klaszter (magas-árú RBC/TDG/IEX/R) húzta; a TP1-partialök csökkentették. Day 63-input lehet explicit notional-cap.
9. **Szektor-rotáció koncentrációba** — korai Real Estate-klaszter (06-15/16, 22,79%) → Industrials-klaszter (06-24, 24,20%, 4 név). A top-3 score 4 napja tiszta Industrials. observed max mindig < 30% cap.
10. **`BEALLITASOK` legacy display** (P3) — a cron stale config-blokkot mutat (0,7%/$700, flow=0,60), miközben a futó swing 0,35%-ot használ. Display-only, CC-verifikáció.

### Dev-chat / stratégiai (Tamás viszi át)
11. **UW kivezetés** — verdikt: az UW élő hozzáadott értéke ≈ 0 (greek-exposure GATED OFF + Polygon-GEX fedi 100%; PCR/OTM Polygon-forrás; darkpool-shadow túl vékony, napi ingadozás 0↔13). Két lépés Dev-chatben: (1) greek-exposure-primary kikapcsolás verifikáció-feltételesen freeze-safe (regime-egyezés bizonyítása kell), (2) teljes UW-kivezetés a Day 126 data-cost tábla + Day 90 darkpool-audit életképesség függvénye. **NEM Log Review döntés.**

## 4. LEZÁRT tételek (ne nyisd újra)
- ✅ `trading_days` off-by-one — backfill `4f75455` élesítve, 06-01 zero-sor beillesztve, `trading_days=day_number` tartja
- ✅ eod „Trades: 0" undercount — `03c77d8`, a persisted cross-client MOC-számot mutatja
- ✅ §6.3 UW 429 trading-hatás — Polygon-GEX fedi, nulla trading-hatás, higiéniai csak (a darabszám ugrál: 2/4/3/12/29/4/0, nem flagelendő trading-kockázatként)
- ✅ §6.1 (06-12) reconcile/eod log hiány — a 22:16 előtti sync okozta, nem cron-kimaradás (folyamat-tanulság: sync csak 22:16 CEST után)

## 5. Folyamat-emlékeztetők (v6 + tanultak)
- **Sync csak 22:16 CEST után** (a reconcile/eod log 22:11/22:15-kor ír)
- **IBKR verifikáció időzítése**: a `get_account_positions`/`summary` a következő 15:30 nyitás UTÁN a mai intraday-t adja, nem az előző close-t. Tiszta ablak: close után, következő nyitás előtt. A Net Liq-snapshotot ebben az ablakban rögzítsd.
- **`get_account_summary` instabil lehet** — 06-12-n 5×, 06-13-n 7× hibázott; a `get_account_positions` közben ment. Ne püföld, jelöld nem-verifikáltként.
- **Cron intraday log suffix ingadozik**: `_143000` VAGY `_143001` (pl. 06-17, 06-22 `_143001`)
- **Várt-exit becslés**: tp1_hit=false TIME_STOP-okra **NE adj pont-becslést** statikus markból (06-17 ACHC alulbecslés -$47 vs -$271; 06-18 VNO túlbecslés -$370 vs -$161). Csak irányt, és jelezd a next-day MOC-mark bizonytalanságot.
- **`exit_type` forrása kizárólag `pending_exits/{date}.json`** (a daily_metrics::exit_type megbízhatatlan)
- **Day 63 előtt nincs jel-érvényességi ítélet**; statisztika csak n-nel, szuperlatívusz nélkül
- **Net Liq reziduum**: ne hajszold újra a summary-t, ha stabil a sávban

## 6. Hétfő (06-29, Day 29) várható
- **Várt exit: 1** — AXTA TIME_STOP (days_held=5, tp1_hit=false, +$111 unrealized 06-26-on). Figyelni: a CORT-ellenpélda után lesz-e 2. tp1_hit=false-pozitív idő-stop.
- RBC/TDG post-TP1 trailing-maradék (qty 5 / 2) sorsa
- Net Liq vs $101 339,17
- Esetleg §6.2 weekly TP1-fix és #1 scoring_validation swing-only státusz (ha CC közben dolgozott rajtuk)

## 7. Kulcs-útvonalak
- Reviews: `docs/review/YYYY-MM-DD-daily-review.md` (06-26-ig kész)
- Heti: `docs/analysis/weekly/2026-W26.md` (W21–W26 kész)
- scoring_validation: `docs/analysis/scoring-validation.md` (pooled, lásd #1)
- v6 prompt: `docs/ifds-log-review-prompt-v6.md`
- Edge audit (Day 63/126 ref): `docs/foundational/strategic-review/2026-06-10-edge-audit.md`
- Kétheti riport: **nincs külön fájl** — a „biweekly" = a `scoring_validation.py` kéthetes futása
