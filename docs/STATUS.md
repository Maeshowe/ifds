# IFDS — Current Status
<!-- Frissíti: CC (/wrap-up), Chat (session végén) -->
<!-- Utolsó frissítés: 2026-04-03 ~19:00 CET, CC -->

## Paper Trading
Day 33/63 | cum. PnL: −$1,113.16 (−1.11%) | IBKR DUH118657
Kiterjesztve 63 napra (~máj 14 kiértékelés)

## Aktív BC
BC20 ✅ DONE (20A + 20C + 20B) → **BC21 következő (Cross-Asset Regime)**
**SORREND: BC21 (előrehozva!) → BC20A**

## Élesben futó feature-ök
- EWMA simítás (span=10), MMS multiplierek (day 15/10, aktiválódott)
- TP1 0.75×ATR, VIX-adaptív SL cap (pt_avwap.py)
- M_target penalty: ×0.85 (>20% analyst target) / ×0.60 (>50%)
- BMI momentum guard: 3+ nap csökkenés + delta ≤−1.0 → max_positions 8→5
- close_positions.py: net BOT-SLD kalkuláció
- Log infra: daily rotation + unified JSONL events + SQLite query

## Shadow mode (adatgyűjtés, hatás nélkül)

| Feature | Shadow óta | Élesítés |
|---|---|---|
| Crowdedness composite | 2026-03-23 | ~ápr 7 (2 hét adat) |
| 2s10s Yield Curve | 2026-03-27 | BC21 Cross-Asset Regime |
| EWMA score delta log | 2026-03-27 | Már aktív (monitoring) |
| Skip Day Shadow Guard | 2026-04-02 | Kiértékelés ~máj 2 |

## BC20-22 Taskok

| BC | Phase | Task fájl | Státusz |
|---|---|---|---|
| BC20 | 20A Re-Score | `2026-04-02-bc20-phase20a-rescore-engine.md` | ✅ DONE `9cb823d` |
| BC20 | 20C Trail SIM | `2026-04-02-bc20-phase20c-trail-sim.md` | ✅ DONE `5b96270` |
| BC20 | 20B Freshness A/B | `2026-04-02-bc20-phase20b-freshness-ab-test.md` | ✅ DONE `037fe4c` |
| BC21 | 21B Cross-Asset | `2026-04-02-bc21-phase21b-cross-asset-regime.md` | **NEXT** |
| BC21 | 21A Corr Guard | `2026-04-02-bc21-phase21a-correlation-guard-var.md` | OPEN |
| BC20A | 20A_1 VWAP | `2026-04-02-bc20a-phase20a1-vwap-module.md` | OPEN |
| BC20A | 20A_2 PosTrk | `2026-04-02-bc20a-phase20a2-position-tracker.md` | OPEN |
| BC20A | 20A_3 Split | `2026-04-02-bc20a-phase20a3-pipeline-split-mkt.md` | OPEN |
| BC20A | 20A_4 Swing | `2026-04-02-bc20a-phase20a4-swing-close.md` | OPEN |
| BC20A | 20A_5 SimEng | `2026-04-02-bc20a-phase20a5-simengine-swing.md` | OPEN |

## Tesztek
1167 passing, 0 failure

## Blokkolók
nincs
