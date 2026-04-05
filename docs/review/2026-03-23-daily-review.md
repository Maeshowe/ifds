# IFDS Daily Review — 2026-03-23

## Pipeline
- [x] Pipeline futott — cron log létezik
- [x] Nincs ERROR/WARNING a pipeline logban
- [x] Telegram üzenet kiküldve
- VIX: 29.95 | BMI: 49.9% (YELLOW) | Stratégia: LONG

## Makró & Scoring
- [x] BMI rezsim ésszerű (GREEN/YELLOW/RED)
- [x] Circuit breaker NEM aktiválódott
- [!] EWMA simítás működik (2. naptól) — MMS: undetermined=100, EWMA hatás nem látszik a logban
- [!] MMS multiplierek ésszerűek — MIND undetermined (100/100), nincs MMS hatás
- [!] Crowdedness shadow logolódik (ha deployolva) — nem látható a logban
- Sector Leaders: XLE, XLF, XLK
- Sector Laggards: XLP, XLB, XLU
- VETO: XLP, XLB, XLU
- MMS eloszlás: Γ⁺:0 Γ⁻:0 DD:0 ABS:0 DIST:0 VOL:0 NEU:0 UND:100

## Pozíciók & Execution
- [x] Execution plan: 6 pozíció (cél: 5-8)
- [x] Szektor diverzifikáció OK (max 3/szektor) — Energy: 3 (COP, LB, BTU), Tech: 3 (CRUS, CSGS, MRVL)
- [x] EARN: nincs earnings 7 napon belül
- [x] Submit: orderek beküldve IBKR-be (6 ticker, 12 bracket)
- [x] Witching day check
- [!] monitor_positions.py (10:10 CET): IBKR Gateway NEM futott — ConnectionRefusedError 3/3

## Paper Trading P&L
- Napi P&L: $+312.17
- Kumulatív P&L: $+332.54 (+0.33%) [Day 26/21]
- TP1 hit-ek: 0 db (EOD report szerint)
- TP2 hit-ek: 0 db
- SL hit-ek: 0 db
- MOC exit-ek: 13 db
- Trail aktiválások: Scenario A: nincs | Scenario B: BTU LOSS_EXIT (18:00 UTC, -$33.04)

## Trades

| Ticker | Qty | Entry | Exit | Típus | P&L |
|--------|-----|-------|------|-------|-----|
| COP | 44 | $125.29 | $127.18 | MOC | +$83.15 |
| BTU | 59 | $36.27 | $35.71 | Scenario B Loss Exit | -$33.04 |
| MRVL (A) | 13 | $90.14 | $91.25 | AVWAP_A_TP | +$14.43 |
| MRVL (B1) | 40 | $90.14 | $90.16 | MOC | +$0.80 |
| MRVL (B2) | 27 | $90.14 | $90.16 | MOC | +$0.54 |
| CRUS (A) | 29 | $137.15 | $137.00 | MOC | -$4.35 |
| CRUS (B) | 58 | $137.15 | $137.00 | MOC | -$8.70 |
| LB (1) | 64 | $71.31 | $72.06 | MOC | +$47.79 |
| LB (2) | 36 | $71.31 | $72.06 | MOC | +$26.88 |
| LB (3) | 92 | $71.31 | $72.06 | MOC | +$68.69 |
| CSGS (A_TP) | 82 | $80.16 | $80.29 | AVWAP_A_TP | +$10.79 |
| CSGS (B1) | 250 | $80.16 | $80.41 | MOC | +$62.91 |
| CSGS (B2) | 168 | $80.16 | $80.41 | MOC | +$42.28 |

## Leftover & Anomáliák
- [x] Nincs leftover pozíció EOD-kor (AVDL.CVR ignored, mint mindig)
- [x] Nincs phantom trail (unfilled tickeren)
- [x] Nincs idempotency hiba (dupla futás)
- [x] Nincs late fill probléma
- [!] monitor_positions.py 10:10 CET — IBKR Gateway offline volt, leftover check nem futott le. Tegnapi (03-20) leftovers a tegnapi napra nem lettek detektálva itt.
- [!] AVWAP fill árak: COP ($125.29 vs plan $126.92 — kedvezőbb), BTU ($36.27 vs $37.31 — kedvezőbb), MRVL ($90.14 vs $87.91 — rosszabb, AVWAP MKT), CRUS ($137.15 vs $136.07 — rosszabb, AVWAP MKT), LB ($71.31 vs $70.95 — kicsit rosszabb, AVWAP MKT), CSGS ($80.16 vs $79.87 — kicsit rosszabb, AVWAP MKT). A limit orderek COP és BTU-nál kedvezőbben teljesültek; a többi tickernél a limit nem teljesült és az AVWAP MKT fallback adott rosszabb entry-t.
- [!] EOD cumulative_pnl.json: tp1_hits=0, sl_hits=0 — de valójában MRVL AVWAP_A_TP és CSGS AVWAP_A_TP fill-ek voltak, valamint BTU LOSS_EXIT. Ezek nem a bracket TP1/SL-ek, hanem az AVWAP és monitor script exit-jei, ezért az EOD report nem számolja TP1/SL-ként. Ez helyes viselkedés, de a P&L tracking szempontjából érdemes figyelni.
- [!] Nagyon magas VIX (29.95) → VIX multiplier floor (0.25) aktív, kicsi pozícióméretek

## Holnap Akciólista
1. IBKR Gateway ellenőrzés — 10:10-kor miért nem futott? Restart szükséges?
2. MMS undetermined 100% — az MMS aktiválás (≥21 entry) még nem érte el egyik tickert sem? Ellenőrizni kell a state/mms/ fájlokat.
3. Nuke NEM szükséges — minden pozíció zárva EOD-kor.

## Megjegyzések
Jó nap (+$312.17), főleg LB (+$143.36 összesen) és COP (+$83.15) hozta. BTU Scenario B loss exit (-$33.04) a legnagyobb vesztes — a szén szektorra jellemző volatilitás. A CSGS magas score (141.8) és FRESH flag szűk TP range-el (entry $79.87, TP1 $80.00) működött az AVWAP TP-vel. Day 26/21 — paper trading fázis túlnyúlt az eredeti 21 napon, kumulatív +0.33%.
