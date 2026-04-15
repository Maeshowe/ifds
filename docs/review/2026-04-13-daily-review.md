# IFDS Daily Review — 2026-04-13 (BC23 Day 1)

## Pipeline
- [x] Pipeline futott 16:15 CEST — cron_intraday_20260413_161500.log ✅
- [x] BC23 minden változás aktív ✅
- [x] Nincs Error 163 / Error 383 ✅
- [x] POST-SUBMIT: all 3 accounted ✅
- [x] Daily metrics JSON generálva ✅
- VIX: 20.16 (elevated) | TNX: 4.29% | Stratégia: LONG

## BC23 Validáció
- [x] Submit 16:15 CEST (10:15 EDT) — opening range után ✅
- [x] Flow-first scoring (60/10/30) ✅
- [x] Dynamic positions: 3/5 (score threshold 85) ✅
- [x] Risk 0.7%/trade ✅
- [x] TP1 1.5×ATR (nem instant fill) ✅
- [x] 50/50 bracket split ✅
- [x] MMS collect-only (nem sizing) ✅
- [x] 3 aktív multiplier (M_vix, M_gex, M_target) ✅

## Fill Rate & Execution
- Execution plan: 3 ticker (friss CSV ✅) | Filled: 3 | Fill rate: 100%
- Existing skip: AVDL.CVR
- Avg slippage: +0.23% (legjobb: ALAB -0.02%, legrosszabb: YOU +0.46%)

## Paper Trading P&L
- Napi P&L: **+$390.27**
- Commission: **$9.42** (65% csökkenés vs BC23 előtti ~$27)
- Kumulatív P&L: **-$2,024.96 (-2.02%)** [Day 41/63]
- TP1: 0 | SL: 0 | LOSS_EXIT: 0 | TRAIL: 0 | MOC: 3
- **Mind a 3 trade nyereséges**

## Trades

| Ticker | Score | Qty | Entry | Exit | Típus | P&L |
|--------|-------|-----|-------|------|-------|-----|
| ALAB | 94.5 | 47 | $161.79 | $166.70 | MOC | +$230.77 |
| VIK | 92.5 | 77 | $76.83 | $78.13 | MOC | +$100.10 |
| YOU | 95.0 | 90 | $47.85 | $48.51 | MOC | +$59.40 |

## Excess Return
- Portfólió: +0.39% | SPY: +0.98% | Excess: -0.59%
- Megjegyzés: $17.8K exposure / $100K account — a cash arány torzít

## Leftover & Anomáliák
- [x] Nincs leftover EOD-kor ✅
- [!] LION/SDRL/DELL/DOCN phantom — továbbra is aktív (P3)
- [!] CRGY/AAPL phantom leftover (P3)
- **Nincs egyéb anomália — első tiszta nap ápr 3 óta**

## Megjegyzések
BC23 első nap: +$390.27, 3 trade, mind nyereséges, $9.42 commission. A rendszer pontosan azt csinálja amit terveztünk: kevesebb, jobb minőségű trade, alacsonyabb költség. Egy nap nem bizonyít semmit — de a mechanika hibátlan.
