# IFDS Daily Review — 2026-07-07 (kedd, Day 34/63 NYSE-count, outage-recovery nap)

> A CC 1c scaffold (`2026-07-07-daily-review.draft.md`) adatai beépítve; a végleges review a v6 szerkezetben. A draft fejléce „Day 37" — hibás, lásd §6.3.

## 1. Fejléc
- **Day 34/63** (NYSE-count) — forrás: `pt_eod` „[Day 34/63]" + `daily_metrics::day_number=34`. ⚠️ `cumulative_pnl::trading_days=29` ≠ 34 — 5 NYSE-nap (06-29…07-02, 07-06) outage miatt hiányzik a daily_history-ból (§6.2). A W27 heti review emiatt nem készült (0 kereskedett nap).
- **Realized net: +$75,25** (gross +$76,38; commission $1,13) — AXTA TIME_STOP MOC. Forrás: `daily_metrics`, broker-ledger (SELL 146 @ $34,26, 19:59:51 UTC, IBKR `get_account_trades` DAYS_7)
- **Cumulative: +$615,30 (+0,615%)** — `cumulative_pnl.json`
- **Net Liq (IBKR, tiszta 07-08 pre-open ablak): $101 431,63** ✓ — a 06-26 horgonyról (+$101 339,17) **+$92,46** a teljes outage-ablakra
- **Excess: +0,55 pp** (portfolio +0,08% vs SPY −0,48%, `daily_metrics` napi számítás)
- **Nyitott pozíciók: 9** (2 belépő ITT/XPO, 1 teljes kilépő AXTA; IBKR + `swing_positions` + reconcile egyező)

## 2. Exits (1) — forrás: `pending_exits/2026-07-07.json` + broker-ledger
| Idő (CEST) | Ticker | Típus | Qty | Entry→Fill | Broker realized | 06-26 `várt` | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59:51 | AXTA | TIME_STOP (MOC) | 146 | $33,74→$34,26 | **+$75,25** (+1,53%) | irány-hipotézis: pozitív lehetséges (nem volt pont-becslés) | irány ✓; 5 nappal késve (outage) |

- ⚠️ `pending_exits` entry_price=$34,00 (planned) vs broker $33,74 — ismert planned-vs-broker tárolási család (06-26 §4 reziduum-megjegyzés); a realized a broker-fillből számolt ✓
- **Kontamináció**: AXTA ténylegesen ~11 NYSE-napot volt tartva (terv: 5, entry 06-18) az outage miatt → a tp1_hit=false→kimenet sorozatban **nem tiszta adatpont** (a 07-08 re-plan §3 D2 kizárási jelölés érvényes rá)

## 3. Entries (2) — forrás: `pt_submit`, execution plan `run_20260707_123000_d9c20a.csv`, broker-ledger
| Ticker | Szektor | Qty | Planned→Fill | Slippage % | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| ITT | Industrials | 26 | $190,07→$183,93 | **−3,23%** | $176,90 / $199,94 / $209,82 |
| XPO | Industrials | 21 | $206,78→$203,07 | **−1,79%** | $190,63 / $218,89 / $231,00 |

- Avg slippage −2,59% (qty-súlyozott, `daily_metrics`). ⚠️ **Fill 21:02 CEST** (terv: 15:30) — outage-recovery késés (§6.4); a plan a 12:30 UTC futásból, a fill 15:02 ET délutáni áron → a két entry **outage-kontaminált** adatpont
- PFGC a plan 3. sora volt, submit helyesen skippelte („already has position") ✓

## 4. Nyitott pozíciók (9) — forrás: IBKR `get_account_positions` (07-08 pre-open, daily_pnl≈0 → 07-07 close markok)
| Ticker | days_held (T) | Mark | Unrealized (IBKR) | Stop-buffer % | next_action |
|---|---|---|---|---|---|
| PFGC | 7 | $115,50 | **+$567,89** | +12,6% | **TP2** |
| NSA | 9 | $45,94 | +$110,00 | +6,9% | **TP1** |
| TDG | 8 | $1330,00 | +$49,50 | +8,4% | **TIME_STOP** |
| R | 9 | $265,94 | +$19,68 | +6,1% | **TIME_STOP** |
| ITT | 0 | $184,62 | +$16,94 | +4,2% | HOLD |
| XPO | 0 | $202,79 | −$6,88 | +6,0% | HOLD |
| SLGN | 7 | $45,18 | −$13,80 | +7,2% | **TP1** |
| IEX | 10 | $221,07 | −$187,78 | +3,0% | **TIME_STOP** |
| RBC | 10 | $600,26 | **−$215,11** | **−0,3% (mark a stop alatt)** | **MENTAL_SL** |
| **Total unrealized** | | | **+$340,44** | | |

- days_held a `review_data`-ból (trading-nap); a 7 exit-flag (monitor 22:00) konzisztens a szintekkel (RBC mark $600,26 < trail-stop $601,99 → MENTAL_SL ✓)
- Notional 47,46% equity; **Industrials 28,33%** — új megfigyelt maximum (korábbi csúcs 24,20%, 06-24), cap 30% alatt, 6/9 pozíció Industrials
- Net Liq-identitás: $100k + 615,30 + 340,44 = $100 955,74 vs tény $101 431,63 → **reziduum +$475,89** (06-26: +$380,44) — lásd §6.1

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:15:05 „Reconciliation OK", 9 ticker state≡IBKR — **24/24 silent OK**
- ✓ `pt_eod` 22:11: Trades(eod-fills) 0 / persisted 1; P&L +$75,25; „[Day 34/63]" helyes
- ✓ monitor 22:00:09 — 9 pozíció kiértékelve, 7 exit-flag
- ⚠️ Cron-időzítés: submit **21:02 CEST** (terv 15:30), close 21:41 ✓ — outage-recovery nap (§6.4); 3 pipeline-futás 14:03/14:06/14:13 CEST („No actionable positions", pre-flight pytest **1981 passed** mindháromban), a plan-termelő 12:30 UTC futásnak jsonl-je + plan CSV-je van, cron stdout-log nincs (§6.6)
- ✓ UW: diagnostics SKIP (kivezetve), 0 db 429
- ⚠️ `BEALLITASOK` display: risk-mezők már helyesek (0,35%/$350, max 12), de a Weights sor (flow=0,60…) és „Max per sector 2" továbbra is legacy — a 06-26 #10 P3 pontosítva

## 6. Anomáliák (új/változott)
- **6.1 P1 ÚJ (P0 auto-flagből átminősítve) — cumulative_drift −$267,52**: tracked $615,30 vs implied $882,82 (NetLiq−100k−offset$208,37−unrealized$340,44; IBKR-ből verifikálva). Kulcs-diagnosztika: a reziduum a 06-26→07-07 outage-ablakban **+$95,45-öt nőtt nulla trade mellett** → nem trade-tracking hiba (a realized-ledger tételesen broker-egyeztetett). `hipotézis:` cash-accrual — (a) IBKR havi kamat-jóváírás (~$53,6k cash, július eleji posting) és/vagy (b) osztalék-jóváírás az ablakban (NSA REIT 150 db, SLGN 128 db — negyedéves kifizetők). Ellenőrzés: IBKR statement cash-tranzakciók 06-27→07-07 (interest+dividend sorok) → `baseline_offset` rekalibráció. Csak ha a tételek NEM fedik a rést → tracking-vizsgálat. Gazda: Tamás (statement) + CC (rekalibráció)
- **6.2 P1 ÚJ — trading_days(29) ≠ day_number(34)**: az outage 5 NYSE-napja nincs a `daily_history`-ban; a 06-26-ig tartott `trading_days=day_number` invariáns megszakadt. Döntés kell: zero-row backfill outage-jelöléssel VAGY dokumentált kivétel (a Day 63-kapu óra a NYSE-count=34). Gazda: Dev-chat/CC. **Day 63-input**: a kiértékelési ablak nevezőjének definíciója
- **6.3 P2 ÚJ — generate_review day-count bug**: `review_data::nyse_trading=37` = weekday-count (ünnepek nélkül nem szűrt), helyes NYSE-érték 34; a draft „Day 37" fejlécet termelt. Gazda: CC-task
- **6.4 P2 ÚJ — entry-timing deviáció**: ITT/XPO fill 21:02 CEST (terv 15:30), outage-recovery. A két entry a signal_attribution mintában kontaminált-jelölés jelölt (a gap-en át tartott 7 pozícióval azonos D2-kategória). Gazda: Day 63-input (leíró jelölés, Dev-chat)
- **6.5 P3 ÚJ — uw tickers_logged eltérés**: `review_data` 3 vs `daily_metrics::uw_shadow_summary` 31. Display/aggregációs szintkülönbség gyanú. Gazda: CC-task (generate_review)
- **6.6 P3 ÚJ — 12:30 UTC run cron stdout-log hiányzik** (`ifds_run_20260707_123000.jsonl` + plan megvan). `hipotézis:` kézi/recovery indítás cron-tee nélkül. Gazda: megfigyelés
- Ismert, változatlan: `exits_today` flag-számláló (ma 7 flag jelenik meg exitként; első előfordulás 06-22); exit_type-determináció P1 (ma a `pending_exits`=TIME_STOP ✓)

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **TP-hit ráta**: 14/32 exit (43,8%); **pozitív-exit 20/32 (62,5%)** — AXTA a 32. exit, outage-kontaminált jelöléssel
- **tp1_hit=false → kimenet**: formálisan 2. pozitív eset (AXTA +$75,25, CORT után), DE ~11 napos kényszertartás → **kontaminált, a tiszta mintázat-számlálóba nem kerül be** (7 neg / 1 poz tiszta állás változatlan)
- **Next-day MKT fill eltérés**: +2 adatpont (ITT −3,23%, XPO −1,79%) — mindkettő outage-kontaminált (21:02 fill), a sorozat tiszta átlagába nem számolandó; elkülönítve rögzítve
- **Szektor-koncentráció**: Industrials 28,33% — új observed max (sorozat: 22,79% RE 06-15 → 24,20% 06-24 → 28,33% ma), cap alatt
- **VIX**: 16,08 (+3,28%); nyitott könyv +$340,44, 5/9 zöld

## 8. Holnap (2026-07-08, Day 35)
- **7 tervezett exit** (`next_day_planned`): 15:30 — NSA TP1, PFGC TP2, SLGN TP1, RBC MENTAL_SL; 21:40 — IEX/R/TDG TIME_STOP. Pont-becslés nincs (next-day fill bizonytalanság + flag→fill lag); referencia-markok a §4-ben. PFGC-nél a +$568 unrealized realizálása a holnapi 15:30 fillen múlik, nem a TP2-áron
- Mind a 7 outage-kontaminált (re-plan §3 D2) — a review holnap ennek megfelelően jelöli; 7 exit után a könyv ITT/XPO-ra + új belépőkre szűkül
- Fókusz: (1) 7-exit végrehajtás + fill-szintek; (2) submit-időzítés visszaáll-e 15:30-ra; (3) §6.1 statement-ellenőrzés státusz; (4) Net Liq vs $101 431,63 horgony; (5) §6.2 day-count döntés

## 9. Freeze-sor
Paraméter-érintő változás ma: **nincs**.

## 10. A nap egy mondatban
Outage-recovery nap: az AXTA TIME_STOP +$75,25-tel zárt (11 napos kényszertartás után, kontaminált adatpont), ITT/XPO 21:02-kor lépett be a 15:30 helyett, a lánc (monitor/eod/reconcile, 24/24 silent OK) hibátlanul állt vissza — a NetLiq-identitás rése viszont nulla trade mellett +$95-tel nőtt, ami accrual-hipotézist erősít és statement-ellenőrzést igényel.
