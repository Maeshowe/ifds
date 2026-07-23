# IFDS Daily Review — 2026-07-08 (szerda, Day 35/63 NYSE-count — 7-exites könyv-reset nap)

> Megjegyzés: a kérésben „2026-07-09" szerepelt, de a fájlrendszeren a legutolsó zárt nap 2026-07-08 (07-09-es log/metrics még nincs) — a review erre a napra készült. Az 1a/1c CC-scaffold ma nem generálódott (§6.6), a review közvetlenül a kanonikus forrásokból készült.

## 1. Fejléc
- **Day 35/63** (NYSE-count) — forrás: `pt_eod` „[Day 35/63]" + `daily_metrics::day_number=35`. ⚠️ `trading_days=30` ≠ 35 — az 5 outage-nap gap változatlan (07-07 §6.2, döntés nyitva)
- **Realized net: −$257,46** (gross −$249,77; commission $7,69 — 7 exit + 2 entry) — forrás: `daily_metrics`, broker-ledger tételesen egyező (IBKR `get_account_trades` DAYS_7)
- **Cumulative: +$357,84 (+0,358%)** — `cumulative_pnl.json`
- **Net Liq (IBKR, 07-09 pre-open snapshot): $100 434,82** — a 07-07 horgonyról (−$101 431,63) **−$996,81**. ⚠️ Az ITT pozíció daily_pnl=+$56,42 a snapshotban (07-09-i komponens), a többi pozíció daily_pnl≈0
- **Excess: +0,06 pp** (portfolio −0,25% vs SPY −0,31%, `daily_metrics`)
- **Nyitott pozíciók: 6** (7 exit — 2 partial-forrású maradék-zárás nélkül —, 2 belépő; IBKR + `swing_positions` + reconcile egyező)

## 2. Exits (7 — a 07-07-en flagelt mind lefutott) — típus: `pending_exits/2026-07-08.json`; fill: broker-ledger
| Idő (CEST) | Ticker | Típus | Qty | Entry(broker)→Fill | Realized | 07-07 ref-mark unrealized | Megjegyzés |
|---|---|---|---|---|---|---|---|
| 15:30:26 | PFGC | **TP2** | 63 | $106,50→$112,38 | **+$370,17** | +$567,89 | fill 2,7%-kal a 07-07 close ($115,50) alatt |
| 15:30:21 | NSA | TP1 (partial) | 75/150 | $45,22→$45,38 | +$11,91 | +$110,00 (teljes poz.) | maradék 75 trail ($43,83) |
| 21:59:30 | R | TIME_STOP (MOC) | 22 | $265,10→$265,23 | +$2,94 | +$19,68 | |
| 21:59:42 | TDG | TIME_STOP (MOC) | 2 | $1305,78→$1296,14 | −$19,27 | +$49,50 | irányfordulás a next-day fillen |
| 15:30:25 | SLGN | TP1 (partial) | 64/128 | $45,30→$44,32 | **−$63,01** | −$13,80 (teljes poz.) | **2. veszteséges „TP1"** (RBC 06-26 után); maradék 64 trail ($42,68) |
| 15:30:26 | RBC | **MENTAL_SL** | 5 | $643,49→$589,04 | **−$272,27** | −$215,11 | RBC teljes életút: −$304,65 (TP1 −32,38 + SL −272,27) |
| 21:59:30 | IEX | TIME_STOP (MOC) | 33 | $226,80→$218,07 | **−$287,93** | −$187,78 | |

- Várt-vs-tény: mind a 7 a tervezett típussal futott ✓; pont-becslés nem volt (szabály szerint), a ref-mark oszlop a 07-07 close-referencia. A 4 db 15:30-as MKT fill **1,2–2,7%-kal a 07-07 close alatt** printelt (§6.5)
- **Mind a 7 exit outage-kontaminált** (re-plan §3 D2) — a signal_attribution tiszta mintából kizárva, leíró jelöléssel

## 3. Entries (2) — forrás: `pt_submit` 15:31 ✓ (normál időzítés visszaállt), plan `run_20260708_123000_17ccd1.csv`, broker-ledger
| Ticker | Szektor | Qty | Planned→Fill | Slippage % | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| PFGC | Consumer Defensive | 62 | $115,50→$115,25 | −0,22% | $109,94 / $119,67 / $123,83 |
| BIRK | Consumer Cyclical | 84 | $45,56→$45,13 | −0,94% | $41,40 / $48,68 / $51,80 |

- **PFGC self-reentry**: TP2 exit 15:30:26 ($112,38) → re-entry 15:31:08 ($115,25), +2,55% 42 mp alatt (§6.5). A plan 3. sora (SLGN, 123 db új) helyesen skippelve („already has position") ✓

## 4. Nyitott pozíciók (6) — forrás: IBKR `get_account_positions` (07-09 pre-open; ⚠️ ITT mark 07-09-i komponenssel)
| Ticker | days_held (T) | Mark | Unrealized (IBKR) | Stop-buffer % | next_action |
|---|---|---|---|---|---|
| ITT | 1 | $187,50 ⚠️ | +$91,82 ⚠️ | +5,7% | HOLD |
| XPO | 1 | $204,59 | +$30,92 | +6,8% | HOLD |
| NSA | 10 | $44,80 | −$30,50 | +2,2% (trail $43,83) | **TIME_STOP** (07-09 21:40) |
| SLGN | 8 | $44,01 | −$81,28 | +3,0% (trail $42,68) | **TIME_STOP** (07-09 21:40) |
| PFGC | 0 | $111,53 | **−$231,64** | **+1,4%** | HOLD |
| BIRK | 0 | $44,24 | −$75,76 | +6,4% | HOLD |
| **Total unrealized** | | | **−$296,44** | | |

- days_held + trail-szintek: `swing_positions.json`. **PFGC stop-buffer +1,4%** — a self-reentry után azonnal MENTAL_SL-közelben
- Notional 26,49% equity; szektor-max **9,28%** (Industrials) — a koncentráció a 7 exittel kiürült (07-07: 28,33%)
- Net Liq-identitás: $100k + 357,84 − 296,44 = $100 061,40 vs tény $100 434,82 → **reziduum +$373,42** (sorozat: +380 → +476 → **+373**) — lásd §6.1

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:16:04 „Reconciliation OK", 6 ticker state≡IBKR — **25/25 silent OK**
- ✓ Cron-időzítések normalizálódtak: intraday pipeline 14:30 (`cron_intraday_20260708_143000.log`, „3 positions sized"), exits 15:30:05–10, submit 15:31, MOC 21:45, monitor 22:00 (2 flag), eod 22:11, reconcile 22:15
- ⚠️ `pt_eod` render hibás: „Trades(eod-fills): 3" NSA/SLGN/PFGC-t listáz „MOC"-ként — a valós eod-fillek IEX/R/TDG; a PFGC-sor az **új** entryvel ($115,25) párosítja a **régi** pozíció exitjét ($112,38) → −$180,81 (broker: +$370,17). Az ismert self-reentry render-bug (v6 ismert-hibák) első éles megjelenése a swing-runban → §6.2
- ✓ UW: 0 db 429; shadow 31 ticker, 0 penalty
- ⚠️ `BEALLITASOK` display: weights-sor továbbra is legacy (07-07 §5 pontosítás érvényes)

## 6. Anomáliák (új/változott)
- **6.1 P1 VÁLTOZOTT — cumulative_drift −$165,05** (volt −$267,52): implied $522,89 (NetLiq−100k−offset$208,37−unrealized) vs tracked $357,84. A reziduum-sorozat **nem monoton** (+$380 → +$476 → +$373): a −$102,47 lépés a 7-exites napon történt → `hipotézis:` a reziduum egy komponense a nyitott pozíciók planned-vs-broker basis-eltérése, amely **exitkor kollabál** (a kamat/osztalék-accrual hipotézis mellett, nem helyett). Ellenőrzés változatlanul: IBKR statement cash-tranzakciók 06-27→07-08 (Tamás) + per-pozíció basis-mismatch tábla és `baseline_offset` rekalibráció (CC)
- **6.2 P1 ÚJ — `trades_2026-07-08.csv` korrupt**: a PFGC-sor entry $115,25 / qty 63 / exit $112,38 / −$180,81 (broker-valóság: basis $106,49, +$370,17); az SLGN-sor „MOC" címkét + a **mai plan-score-t** (84,3) hordozza a belépéskori 77,48 helyett; és a CSV csak 3/7 exitet tartalmaz. A CSV a forrás-hierarchia alja, de fizikailag korrupt artefakt — downstream fogyasztás tilos, a attribution a broker P&L-t használja ✓. Gazda: **CC-task** (eod CSV-writer: self-reentry párosítás + teljes napi exit-lista)
- **6.3 ismert P1, új konkrét esetek — exit_type**: `daily_metrics::details` RBC=„TP1" (valós: MENTAL_SL), PFGC=„TP1" (valós: TP2); a `pending_exits` ✓ a kanonikus forrás (első előfordulás-család: 06-23 SJM)
- **6.4 ismert — `exits_today`={TIME_STOP:2}** = a holnapi flagek, ma 7 exit futott (első előfordulás 06-22)
- **6.5 P2 ÚJ — 15:30 open-print anomália**: mind a 4 db 15:30-as MKT exit-fill 1,2–2,7%-kal a 07-07 close alatt (SPY −0,31% napon); PFGC exit $112,38 → 42 mp múlva re-entry $115,25 (+2,55%). `hipotézis:` opening auction print / gap-down spike; ellenőrzés: PFGC 1-perces bar 15:30–15:32 CEST (Polygon). **Day 63-input** a flag→fill lag dossziéba (a TP-realizáció a nyitó printen múlik)
- **6.6 P3 ÚJ — 1a/1c nem futott**: nincs `state/review_data/2026-07-08.json` és draft. `hipotézis:` a CC review-mechanika cron-integrációja hiányzik/kihagyott. Gazda: CC-verifikáció. (A 07-07 §6.3 day-count-bug státusza emiatt ma nem mérhető)

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **TP-hit ráta: 17/39 exit (43,6%); pozitív-exit 23/39 (59,0%)** — a mai 7 exit D2-kontaminált jelöléssel számolva
- **Veszteséges „TP1": 2. eset** (SLGN −$63,01; RBC 06-26 −$32,38) — a flag→fill lag családja; **TP2 lag-költség**: PFGC +$370,17 realizált vs +$567,89 07-07 ref (leíró)
- **Self-reentry: +1 eset** (PFGC, entry-slippage −0,22%, ROI nyitott) — az első a swing-runban
- **tp1_hit=false→kimenet tiszta számláló változatlan** (7 neg / 1 poz) — a mai exitek kontamináltak
- **Szektor-koncentráció**: Industrials 28,33% → **9,28%** (reset a 7 exittel)
- **VIX**: 16,65 (+3,22%); nyitott könyv −$296,44, 2/6 zöld

## 8. Holnap (2026-07-09, Day 36)
- **2 tervezett exit, mindkettő 21:40 MOC**: NSA TIME_STOP (75 db, trail $43,83) és SLGN TIME_STOP (64 db, trail $42,68) — post-TP1 maradékok, outage-kontaminált jelöléssel; 15:30-as exit nincs. Pont-becslés nincs (next-day MOC bizonytalanság)
- Fókusz: (1) NSA/SLGN MOC fillek; (2) **PFGC +1,4% stop-buffer** — MENTAL_SL-flag valószínű, ha a mark a $109,94 alá csúszik; (3) §6.1 statement-ellenőrzés státusz; (4) 1a/1c generálás visszaáll-e; (5) Net Liq horgony $100 434,82 (⚠️ ITT-komponenssel)

## 9. Freeze-sor
Paraméter-érintő változás ma: **nincs**.

## 10. A nap egy mondatban
A 7-exites reset-nap −$257,46-tal kiürítette az outage-kontaminált könyvet (a 15:30-as MKT fillek 1,2–2,7%-kal a előző close alatt printeltek, a PFGC TP2 után 42 másodperccel +2,55%-on lépett vissza), a lánc időzítése normalizálódott (25/25 silent OK) — de a self-reentry az eod-rendert ÉS a trades CSV-t is hibás párosítással korrupttá tette, a NetLiq-reziduum pedig −$102-t lépett, ami a basis-kollapszus hipotézist hozta be a drift-diagnózisba.
