# IFDS Daily Review — 2026-07-21 (kedd, Day 44/63 NYSE-count)

> Executor: **CC** (Fázis A, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett.
> Az IBKR MCP connector a review első írásakor lecsatlakozott volt; **Tamás újraindítása után a teljes
> v6 §3 kereszt-ellenőrzés lefutott** (`get_account_summary/positions/trades`) és a §4 mark/unrealized
> adatok pótolva. Day 63 előtt nincs jel-ítélet.

## 1. Fejléc
- **Day 44/63** (NYSE-count) — `daily_metrics::day_number=44`. ⚠️ `cumulative_trading_days=38` ≠ 44 (ismert gap, 07-07 §6.2).
- **Realized net: +$54,83** (1 exit, komm. $1,07) — `cumulative_pnl` 07-21 history-sor. **Cumulative: $107,62 (+0,108%)**.
- **Net Liq: $100 364,55** — IBKR `get_account_summary` **≡** `state/daily_equity.json["2026-07-21"]`, **penny-pontos egyezés ✓** (lásd §6: a 07-13 §6.1 forrás-konfliktus ma nem áll fenn); **napi Δ: +$463,24** (07-20: $99 901,31). Visszatért $100k fölé.
- **Excess: −0,78%** — `daily_metrics::excess_return` (portfolio +0,06% vs SPY **+0,83%**). Risk-on nap (VIX 16,91, −9,33%), a könyv gyakorlatilag oldalazott.
- **Nyitott pozíciók: 5** (`review_data` ≡ `pt_events` reconcile 5/5 ✓): USFD, GTES, JAZZ, PFGC, EQH.

## 2. Exits (1) — típus: `state/pending_exits/2026-07-21.json`; P&L: `daily_metrics::trades::details` (broker)
| Idő (CEST) | Ticker | Típus | Qty | Entry→Exit | Broker realized | 07-20 §8 várt | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59 | SLGN | TIME_STOP (MOC) | 60 | 44,73 → 45,64 | **+$54,83** (+2,04%) | ~+$82 | −$27,17 |

A maradó 60 SLGN (a 07-20-i TP1-részleges után) a day-6 max_hold-on zárt. Az eltérés oka: a 07-20-i mark
(46,07) fölött becsültünk, a keddi MOC 45,64-en teljesült.

## 3. Entries (2) — `pt_events` 15:31 + `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| PFGC | Consumer Defensive | 60 | 109,32 → **110,42** | **+1,01%** | 103,51 / 113,68 / 118,03 |
| EQH | Financial Services | 126 | 48,10 → **48,5579** | **+0,95%** | 45,33 / 50,18 / 52,25 |

Átlag fill-slippage **+0,97%**, komm. összesen $1,07. ⚠️ **A PFGC self-reentry** — lásd §6.

## 4. Nyitott pozíciók (5) — `swing_positions.json` (days/stop/next) + IBKR `get_account_positions` (mark/unrealized)
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| USFD | 5 | 94,75 | **−$439,48** | **−0,35%** (stop alatt) | **MENTAL_SL** (holnap 15:30) |
| GTES | 2 | 27,05 | +$70,78 | 7,02% | HOLD |
| JAZZ | 1 | 254,22 | +$96,06 | 8,40% | HOLD |
| PFGC | 0 | 110,34 | −$5,80 | 6,19% | HOLD (re-entry) |
| EQH | 0 | 49,13 | +$71,08 | 7,73% | HOLD |

**Total unrealized: −$207,36** (IBKR). Gross position value $29 130,21 (`get_account_summary`);
entry-bázisú notional **29,21% equity**; szektor-max Consumer Defensive $12 232,56 (USFD+PFGC) < cap 30%.
A GTES (+$261,90) és a JAZZ (+$247,25) napi mark-emelkedése vitte a NetLiq-et vissza $100k fölé.

## 5. Ops-checklist
- ✓ **Reconcile 5/5 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Teljes cron-lánc**: 15:31 submit (PFGC, EQH), 21:40 time_stop (SLGN MOC), 22:00 eod_eval (USFD MENTAL_SL), 22:10 metrics, 22:20 review_data.
- ✓ **Nincs ERROR**; a 20:11 `eod::leftover_warning` (5) normál.
- ✓ **IBKR MCP kereszt-ellenőrzés lefutott** (connector-újraindítás után, ugyanaznap este): NetLiq penny-egyezés a `daily_equity`-vel; pozíció-halmaz 5/5 egyezés; a 3 mai fill (SLGN 45,64 MOC / PFGC 110,42 / EQH 26@48,55 + 100@48,56) verifikálva.

## 6. Anomáliák (új/változott/lezárt)
- **✅ LEZÁRVA — USFD stop-breach (07-20 §6/P2).** Ma a 22:00 eod_eval **MENTAL_SL flaget adott** az USFD-re (`pt_events` 20:00 `swing_eod_action`), végrehajtás holnap 15:30. A számok a hipotézist **megerősítik**: 07-20-án a mark **95,03** volt a 95,08-as stop alatt (**−0,05%**, 5 centes határeset → nem flag-elt), ma **94,75** (**−0,35%**, 33 cent → flag-elt). Vagyis a nem-flagelés tegnap **határeset + forrás-timing** (Polygon napi close vs IBKR last) volt, nem logikai hiba — a mental-stop mechanizmus működik. **NEM emelendő P1-re**; megfigyelésként lezárva.
- **✅ LEZÁRVA — Net Liq forrás-konfliktus (07-13 §6.1).** Ma az IBKR `get_account_summary` ($100 364,55) és a `state/daily_equity.json` **penny-pontosan egyezik** — a korábbi eltérés nem áll fenn. Ha újra megjelenik, akkor nyitandó újra.
- **P2 (ÚJ) — PFGC self-reentry: a max_hold kényszerített round-tripje.** A PFGC-t a max_hold TIME_STOP 07-20-án **109,18-on kiléptette**, a jel ma **újra beengedte** → fill **110,42**. Round-trip költség: **+$1,24/részvény × 60 ≈ −$74** implicit, plusz 2 komisszió — *pusztán a max_hold=5 szabály miatt, változatlan jel mellett*. A pozícióméret is újraszámolódott (62 → 60). **Day 63-input**: a max_hold perzisztens jelnél kényszerű, ~1%/oldal csúszással terhelt round-tripeket generál. n=1 (első dokumentált eset a swing-érában). Forrás: `pending_exits` 07-20 + `daily_metrics::execution` 07-21.
- **P3 (carry) — entry-slippage ~1%/oldal, immár 4 print.** PFGC +1,01%, EQH +0,95% ma (előzmény: JAZZ +1,0% 07-20, GTES −1,0% 07-17). **4/4-ből 3 adverz.** Közvetlen input az FRL cost-modelljébe (§7) — a spec v2 **75 bp/oldal** induló értéke a mért ~100 bp mediánhoz képest **konzervatívnak tűnik**, felülvizsgálandó, ahogy n nő.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=4**: GTES −1,00% (07-17), JAZZ +1,00% (07-20), PFGC +1,01%, EQH +0,95% (07-21). **|slippage| medián ≈ 1,00% (≈100 bp)**, 3/4 adverz előjelű. *(Ez a sorozat az FRL `research/cost_model.json` bemenete — a torzítatlan cost-input az |slippage| medián/p75, nem az előjeles nyomatok.)*
- **Self-reentry** — **n=1 (ÚJ)**: PFGC (07-20 exit 109,18 → 07-21 entry 110,42), implicit round-trip ≈ −$74 + komisszió. ROI-zárás még nincs (a pozíció nyitva).
- **Major risk-off excess**: ma **nem** risk-off (SPY +0,83%) — nem adódik hozzá; megjegyzés: up-napon a könyv +0,06% (excess −0,78%).
- **TP-hit / pozitív-exit**: ma 1 exit, **1 pozitív** (SLGN +2,04%). Kumulatív a sorozat-vezetésből aktualizálandó.
- **Daily-eval fordulat**: USFD HOLD → MENTAL_SL (1 fordulat).

## 8. Holnap (szerda, 07-22) — várt + feltevés
- **USFD MENTAL_SL** 15:30 MKT (56 db) — `várt` ≈ **−$440** (feltevés: a holnapi fill ≈ a mai záró mark 94,75; IBKR-bázis 102,598 → a mai unrealized −$439,48 realizálódna). A ~1%-os belépő-slippage mintázat alapján a tényleges fill ettől ±$50-ban térhet el.
- **Fókuszlista**: (1) USFD MENTAL_SL végrehajtás + a várt-vs-tény; (2) PFGC self-reentry követése (day 1 — a round-trip megtérül-e; ma −$5,80 unrealized); (3) EQH első teljes napja (+$71,08 indulás); (4) slippage-sorozat n=4 → tovább (FRL cost-model input); (5) a szektor-koncentráció figyelése (Consumer Defensive 2 névvel, de USFD holnap távozik).

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** A mai commitok (`b659543`, `a7e186f`, `6457abe`) docs-only (review-k + FRL spec/task/handoff). Freeze él Day 63-ig.

## 10. A nap egy mondatban
Risk-on nap (SPY +0,83%) mellett a könyv oldalazott (+0,06%, excess −0,78%); az egyetlen exit a SLGN max_hold-ja (+$54,83), a PFGC-t a max_hold kiléptette majd a jel ~1% csúszással visszaengedte, és az USFD holnap mental-stopon távozik.
