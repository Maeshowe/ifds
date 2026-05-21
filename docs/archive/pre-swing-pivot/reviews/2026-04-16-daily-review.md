# IFDS Daily Review — 2026-04-16 (BC23 Day 4)

## Pipeline
- [x] Pipeline futott 16:15 CEST ✅
- [x] Nincs Error ✅
- [x] Daily metrics JSON ✅
- VIX: ~18 (normal) | Stratégia: LONG

## Paper Trading P&L
- Napi P&L: **+$576.77** (4/4 nyereséges — 100%)
- Commission: $13.76
- Kumulatív P&L: **-$657.63 (-0.66%)** [Day 44/63]
- **Excess return: +0.33%** (portfólió +0.58% vs SPY +0.25%) — első pozitív excess!

## BC23 Összesítve (4 nap)
| Nap | P&L | Win rate | Excess vs SPY |
|-----|-----|----------|---------------|
| ápr 13 | +$390 | 3/3 | -0.59% |
| ápr 14 | +$191 | 2/3 | -1.03% |
| ápr 15 | +$600 | 2/3 | -0.19% |
| ápr 16 | +$577 | 4/4 | **+0.33%** |
| **Összesen** | **+$1,758** | **11/13 (85%)** | |

BC23 előtti 40 nap: -$2,415, átlag -$60/nap
BC23 óta 4 nap: +$1,758, átlag **+$439/nap**
Kumulatív: -$2,415 → **-$658**

## Trades

| Ticker | Score | Qty | Entry | Exit | Típus | P&L |
|--------|-------|-----|-------|------|-------|-----|
| TIGO | 91.0 | 144 | $78.98 | $81.84 | MOC | +$411.84 |
| NVDA | 94.5 | 93 | $196.95 | $198.41 | MOC | +$135.78 |
| MU | 94.5 | 17 | $456.11 | $457.30 | MOC | +$20.24 |
| BALL | 92.0 | 297 | $63.28 | $63.31 | MOC | +$8.91 |

## Daily Metrics
- Slippage: **-0.13%** (negatív = kedvezőbb fill! NVDA -0.23%, MU -0.47%)
- Excess return: +0.33% — első pozitív excess a BC23 óta
- TIGO (legalacsonyabb score 91.0) → legnagyobb nyerő — az inverz quintilis minta megfordult

## Leftover & Anomáliák
- [x] Nincs leftover EOD-kor ✅
- [!] LION/SDRL/DELL/DOCN phantom (P3, CC task nyitva)
- [!] CRGY/AAPL phantom leftover (nuke.py fix szükséges)
- [!] qualified_above_threshold: 1 vs 4 pozíció nyitva — metrika script bug (P3)

## Megjegyzések
BC23 negyedik egymást követő pozitív nap, 4/4 nyereséges. A kumulatív -$2,415-ből 4 nap alatt -$658-ra javult (+$1,758). A rendszer stabilan 3-4 trade-et nyit, 85% win rate-tel, $11-14 commission-nel. Az excess return ma először pozitív. Holnap ápr 17 — ha pozitív, pénteken (ápr 18) az első heti metrika nagyon erős lesz.
