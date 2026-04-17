# IFDS Daily Review — 2026-04-17 (BC23 Day 5)

## Pipeline
- [x] Pipeline futott 16:15 CEST ✅
- [x] FRED OK (703ms — gyors) ✅
- [x] Nincs Error ✅
- VIX: 17.65 (normal, legalacsonyabb a BC23 óta) | TNX: 4.29% | Stratégia: LONG

## Paper Trading P&L
- Napi P&L: **-$36.90** (első negatív nap a BC23 óta)
- Kumulatív P&L: **-$694.53 (-0.69%)** [Day 45/63]
- 2/4 nyereséges | TP1: 0 | SL: 0 | LOSS_EXIT: 0 | TRAIL: 0 | MOC: 4

## BC23 Első Teljes Hét (ápr 13-17)
| Nap | P&L | Win rate | Pozíciók |
|-----|-----|----------|----------|
| ápr 13 (hétfő) | +$390.27 | 3/3 | 3 |
| ápr 14 (kedd) | +$190.81 | 2/3 | 3 |
| ápr 15 (szerda) | +$599.75 | 2/3 | 3 |
| ápr 16 (csütörtök) | +$576.77 | 4/4 | 4 |
| ápr 17 (péntek) | -$36.90 | 2/4 | 4 |
| **Heti összesen** | **+$1,720.70** | **13/17 (76%)** | **17** |

BC23 előtti 40 nap: -$2,415, átlag -$60/nap
BC23 első hete (5 nap): +$1,721, átlag **+$344/nap**
Kumulatív: -$2,415 → **-$695** (29% visszanyerés egy hét alatt)

## Trades

| Ticker | Score | Qty | Entry | Exit | Típus | P&L |
|--------|-------|-----|-------|------|-------|-----|
| META | 94.0 | 22 | $684.97 | $688.56 | MOC | +$78.98 |
| DELL | 94.5 | 50 | $196.51 | $196.55 | MOC | +$2.00 |
| AMD | 94.5 | 44 | $278.96 | $278.34 | MOC | -$27.28 |
| BALL | 95.0 | 302 | $64.78 | $64.48 | MOC | -$90.60 |

## Pipeline Szűrés
- Analyzed: 1285 → Passed: 211 → 4 pozíció
- Max 5 (dynamic threshold 85) → 4 ticker qualified
- Exposure: $56,732 (nagyobb mint az előző napok — magas árú tickerek: META $687, AMD $279, DELL $196)
- Freshness Alpha: 17 tickerre (köztük META FRESH)

## Kulcs megfigyelések
1. **BALL**: kétnapos szereplő (score 95.0 mindkét nap) — tegnap +$8.91, ma -$90.60. A magas score önmagában nem garantál nyereséget.
2. **AMD, META**: első BC23 megjelenés — nagy tech nevek
3. **DELL**: a korábbi phantom ma valódi pozíció, flat (+$2.00)

## Leftover & Anomáliák
- [x] Nincs leftover EOD-kor ✅
- [!] LION/SDRL phantom — továbbra is aktív (CC task nyitva)
- [!] CRGY/AAPL phantom leftover (nuke.py fix szükséges)

## Megjegyzések
Az első negatív nap kicsi veszteség (-$36.90) — közel flat. A BC23 első teljes hete +$1,720.70-nal zárult, ami 76% win rate-tel és $344/nap átlaggal sokkal jobb mint a BC23 előtti -$60/nap. Ez az első valódi bizonyíték hogy a redesign működik.

**Most futtatandó:** `weekly_metrics.py` — első heti metrika a BC23-ra.
