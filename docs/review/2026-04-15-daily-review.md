# IFDS Daily Review — 2026-04-15 (BC23 Day 3)

## Pipeline
- [x] Pipeline futott 16:15 CEST ✅
- [x] Nincs Error 163 / Error 383 ✅
- [x] POST-SUBMIT: all 3 accounted ✅
- [x] Daily metrics JSON generálódott ✅
- VIX: ~18 (normal) | Stratégia: LONG

## BC23 Validáció
- [x] 3 pozíció (dynamic threshold 85) ✅
- [x] Score range: 92.0–92.5 (nincs inflált 140+ score) ✅
- [x] 50/50 bracket split ✅
- [x] TP1 1.5×ATR ✅
- [x] Slippage átlag 0.06% — legjobb eddig ✅

## Paper Trading P&L
- Napi P&L: **+$599.75** (legjobb nap feb 24 óta)
- Commission: $13.14
- Kumulatív P&L: **-$1,234.40 (-1.23%)** [Day 43/63]
- TP1: 0 | SL: 0 | LOSS_EXIT: 0 | TRAIL: 0 | MOC: 4

## BC23 Összesítve (3 nap)
| Nap | P&L | Win rate | Pozíciók | Commission |
|-----|-----|----------|----------|------------|
| ápr 13 | +$390.27 | 3/3 | 3 | $9.42 |
| ápr 14 | +$190.81 | 2/3 | 3 | $9.46 |
| ápr 15 | +$599.75 | 2/3 | 3 | $13.14 |
| **Összesen** | **+$1,180.83** | **7/9 (78%)** | **9** | **$32.02** |

BC23 előtti 40 nap: -$2,415, átlag -$60/nap
BC23 óta 3 nap: +$1,181, átlag **+$394/nap**

## Trades

| Ticker | Score | Qty | Entry | Exit | Típus | P&L |
|--------|-------|-----|-------|------|-------|-----|
| ZM | 92.5 | 146 | $85.85 | $89.04 | MOC | +$465.01 |
| GME | 92.0 | 555 | $24.39 | $24.77 | MOC | +$209.43 |
| KSPI | 92.5 | 97 | $82.77 | $82.00 | MOC | -$74.69 |

## Daily Metrics Összefoglaló
- Slippage: átlag +0.06% (ZM +0.05%, KSPI +0.12%, GME 0.00%)
- Commission: $13.14
- Excess return: -0.19% (portfólió +0.60% vs SPY +0.79%)

## Leftover & Anomáliák
- [x] Nincs leftover EOD-kor ✅
- [!] LION/SDRL phantom — továbbra is aktív (CC task nyitva)
- [!] CRGY/AAPL phantom leftover (nuke.py fix szükséges)

## Megjegyzések
BC23 harmadik egymást követő pozitív nap. A rendszer konzisztensen 3 trade-et nyit, 78% win rate-tel, minimális slippage-dzsel. A kumulatív -$1,234 — a BC23 3 nap alatt $1,181-et hozott vissza a -$2,415-ből. Három nap nem bizonyíték, de a trend egyértelmű: kevesebb, jobb minőségű trade, alacsonyabb költség, jobb eredmény.
