# IFDS Daily Review — 2026-04-09

## Pipeline
- [x] Pipeline futott — cron_intraday_20260409_154500.log ✅
- [!] IBKR Error 163: TP orderek elutasítva (Precautionary Settings 3% limit) — **JAVÍTVA** 22:00 CEST
- [!] IBKR Error 383: SBRA Bracket B size >500 — **JAVÍTVA** 22:00 CEST
- [x] Telegram üzenet kiküldve
- VIX: 21.22 | BMI: n/a (Phase 1-3 este) | Stratégia: LONG

## Makró & Scoring
- [x] Circuit breaker NEM aktiválódott
- [x] BMI Momentum Guard — NEM aktív
- Phase 4: Analyzed 1540 | Passed 283 | Crowded: 1
- Phase 6: 8 pozíció | 4 sector limit excluded | 6 position limit excluded

## Fill Rate & Execution
- Execution plan: 8 ticker (friss CSV ✅) | Filled: 8 | Fill rate: 100%
- Existing skip: AVDL.CVR
- **Dupla submit**: 15:47 UTC (automata, IBKR connection error) + 17:44 UTC (manuális, sikeres)
- **Error 163** (TP price >3%): SNDK, RNG, TSM, VRT, BWXT, SBRA — TP orderek Cancelled
- **Error 383** (size >500): SBRA Bracket B (560 shares) — Cancelled

## Paper Trading P&L
- Napi P&L: **-$311.15**
- Kumulatív P&L: **-$1,928.32 (-1.93%)** [Day 39/63]
- TP1: 5 | SL: 0 | LOSS_EXIT: 1 | TRAIL: 0 | MOC: 6

## Trades

| Ticker | Qty | Entry | Exit | Típus | P&L |
|--------|-----|-------|------|-------|-----|
| SNDK | 1 | $839.40 | $850.00 | TP1 | +$10.60 |
| SNDK | 1 | $839.40 | $851.01 | MOC | +$11.61 |
| SBRA | 276 | $20.43 | $20.42 | TP1 | -$2.76 (4 részen) |
| RNG | 84 | $36.45 | $36.38 | LOSS_EXIT | -$5.88 |
| TSM | 24 | $365.83 | $365.27 | MOC | -$13.44 |
| LXP | 130 | $49.99 | $49.67 | MOC | -$42.03 |
| CXW | 402 | $20.35 | $20.24 | MOC | -$44.22 |
| VRT | 21 | $289.50 | $287.07 | MOC | -$51.03 |
| BWXT | 29 | $236.41 | $230.41 | MOC | -$174.00 |

## Leftover & Anomáliák
- [x] Nincs leftover EOD-kor
- [!] LION/SDRL/DELL/DOCN phantom — továbbra is aktív a 22:00 utáni monitor ciklusban
- [!] CRGY/AAPL phantom leftover — monitor_positions
- [!] SBRA TP1 instant fill negatív P&L (MKT fill $20.43 > TP1 $20.34) — ismert, Fix 2 taskban
- [!] BWXT -$174: legnagyobb napi vesztes, TP nélkül futott (Error 163 elutasította)
- [!] Error 163 az összes TP orderre 6/8 tickernél — **pozíciók TP védelem nélkül futottak**

## IBKR Config Változás (22:00 CEST)
- **Price (Percentage)**: 3% → 30% — TP orderek nem lesznek elutasítva
- **Size Limit**: 500 → 2000 — nagy pozíciók (SBRA 836 sh) nem lesznek splittelve

## Scoring Validáció
- Ma érkezett a scoring-validation.md report (CC)
- Kulcs eredmény: **a scoring NEM termel alpha-t** (r=+0.046, p=0.46)
- Q5 (legmagasabb score) a legrosszabbul teljesít — inverz quintilis minta
- Flow komponens gyengén szignifikáns (r=+0.136, p=0.039)
- Részletek: docs/analysis/scoring-validation.md

## Holnap Akciólista
1. IBKR config módosítás ellenőrzése — TP orderek átmennek-e (Precautionary 30%)
2. Stabilizációs fix deploy ellenőrzése (CC task: post-submit-stabilization.md)
3. Phantom state fájlok kezelése (LION/SDRL régi state-ek)

## Megjegyzések
Az első **teljes automatikus nap** az új rendszerrel (pipeline split + MKT entry). A pipeline mechanikailag működik: friss CSV, MKT fill, monitor trail, Scenario B, loss exit, MOC close. Az Error 163 a legnagyobb probléma — 6/8 ticker TP nélkül futott, ami a BWXT -$174 veszteséghez hozzájárult. Az IBKR config fix megtörtént, holnap validáljuk.

A scoring validáció eredménye stratégiai jelentőségű — a Day 63 kiértékelés alapja.
