# IFDS Daily Review — 2026-04-14 (BC23 Day 2)

## Pipeline
- [x] Pipeline futott 16:15 CEST ✅
- [x] Friss Phase 1-3 ctx (manuális futtatás 16:04 — FRED tegnap HALT-olt) ✅
- [x] Nincs Error 163 / Error 383 ✅
- [x] POST-SUBMIT: all 3 accounted ✅
- VIX: 18.14 (normal) | TNX: 4.31% | BMI: 48.2% (YELLOW) | Stratégia: LONG

## BC23 Validáció
- [x] 3 pozíció (dynamic threshold 85) ✅
- [x] Flow-first scoring (60/10/30) ✅
- [x] 50/50 bracket split ✅
- [x] TP1 1.5×ATR (nincs instant fill) ✅
- [x] 3 aktív multiplier ✅

## Fill Rate & Execution
- Execution plan: 3 ticker (friss CSV ✅) | Filled: 3 | Fill rate: 100%
- Existing skip: AVDL.CVR

## Paper Trading P&L
- Napi P&L: **+$190.81**
- Kumulatív P&L: **-$1,834.15 (-1.83%)** [Day 42/63]
- TP1: 0 | SL: 0 | LOSS_EXIT: 0 | TRAIL: 0 | MOC: 3
- BC23 összesítve (2 nap): **+$581.08**, 5/6 trade nyereséges

## Trades

| Ticker | Score | Qty | Entry | Exit | Típus | P&L |
|--------|-------|-----|-------|------|-------|-----|
| BE | 95.0 | 17 | $211.85 | $218.74 | MOC | +$117.05 |
| DAL | 94.0 | 163 | $71.13 | $71.75 | MOC | +$101.06 |
| VIAV | 94.0 | 105 | $41.05 | $40.79 | MOC | -$27.30 |

## Leftover & Anomáliák
- [x] Nincs leftover EOD-kor ✅
- [!] LION/SDRL phantom — archiválás nem oldotta meg, mélyebb ok (P3)
- [!] CRGY/AAPL phantom leftover — nuke szükséges piaci órákban (nuke.py bug: _log_path)
- [x] Daily metrics JSON generálódott ✅ (22:10 cron)

## Daily Metrics Összefoglaló
- Slippage: átlag +0.16% (BE -0.16%, DAL +0.30%, VIAV +0.34%)
- Commission: $9.46
- Excess return: -1.03% (portfólió +0.19% vs SPY +1.22%)
- Megjegyzés: $19.5K exposure / $100K account → az exposure-adjusted return +0.98%, közelebb a SPY-hoz

## Holnap Akciólista
1. nuke.py fix (CC) → CRGY/AAPL cleanup
2. FRED CRITICAL→OPTIONAL átminősítés mérlegelése (tegnap HALT-olta a 22:00 futást)

## Megjegyzések
BC23 második pozitív nap. A rendszer konzisztensen 3 trade-et nyit, alacsony commission-nel ($9.46/nap vs régi ~$27), és 2 napból 5/6 trade nyereséges. Korai, de az irány helyes. A VIX normálra csökkent (18.14) — ez az első normális VIX piaci környezet hetek óta. A teljes mérési lánc működik: pipeline → submit → monitor → close → EOD → daily metrics.
