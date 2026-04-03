# IFDS — Current Status
<!-- Frissíti: CC (/wrap-up), Chat (session végén) -->
<!-- Utolsó frissítés: 2026-04-03 ~15:30 CET, CC -->

## Paper Trading
Day 33/63 | cum. PnL: −$1,113.16 (−1.11%) | IBKR DUH118657
Kiterjesztve 63 napra (~máj 14 kiértékelés)

## Aktív BC
BC20 indítás — Phase_20A (Re-Score Engine) következő
**SORREND: BC20 → BC21 (előrehozva!) → BC20A**
BC21 előrehozva a bearish piac miatt (CRISIS mód kell)

## Élesben futó feature-ök
- EWMA simítás (span=10), MMS multiplierek (day 15/10, aktiválódott)
- TP1 0.75×ATR, VIX-adaptív SL cap (pt_avwap.py)
- M_target penalty: ×0.85 (>20% analyst target) / ×0.60 (>50%)
- BMI momentum guard: 3+ nap csökkenés + delta ≤−1.0 → max_positions 8→5
- close_positions.py: net BOT-SLD kalkuláció (fix: suffix matching → net qty)
- Log infra: daily rotation + unified JSONL events + SQLite query

## Shadow mode (adatgyűjtés, hatás nélkül)

| Feature | Shadow óta | Élesítés |
|---|---|---|
| Crowdedness composite | 2026-03-23 | ~ápr 7 (2 hét adat), BC20 ELŐTT is jöhet |
| 2s10s Yield Curve | 2026-03-27 | ~ápr 10 (2 hét), élesítés BC21-ben |
| EWMA score delta log | 2026-03-27 | Már aktív (monitoring) |
| Skip Day Shadow Guard | 2026-04-02 | Kiértékelés 30 nap múlva (~máj 2) |

## Kész taskok (nem BC)
| Task | Commit | Dátum |
|---|---|---|
| Log Infra Modernizáció (F1-F4) | `364e53e`..`42e78e3` | 2026-04-03 |

## BC20-22 Taskok (10 task, kidolgozva)

| BC | Phase | Task fájl | Státusz |
|---|---|---|---|
| BC20 | 20A Re-Score | `2026-04-02-bc20-phase20a-rescore-engine.md` | **NEXT** |
| BC20 | 20C Trail SIM | `2026-04-02-bc20-phase20c-trail-sim.md` | OPEN |
| BC20 | 20B Freshness A/B | `2026-04-02-bc20-phase20b-freshness-ab-test.md` | OPEN |
| BC21 | 21B Cross-Asset | `2026-04-02-bc21-phase21b-cross-asset-regime.md` | OPEN |
| BC21 | 21A Corr Guard | `2026-04-02-bc21-phase21a-correlation-guard-var.md` | OPEN |
| BC20A | 20A_1 VWAP | `2026-04-02-bc20a-phase20a1-vwap-module.md` | OPEN |
| BC20A | 20A_2 PosTrk | `2026-04-02-bc20a-phase20a2-position-tracker.md` | OPEN |
| BC20A | 20A_3 Split | `2026-04-02-bc20a-phase20a3-pipeline-split-mkt.md` | OPEN |
| BC20A | 20A_4 Swing | `2026-04-02-bc20a-phase20a4-swing-close.md` | OPEN |
| BC20A | 20A_5 SimEng | `2026-04-02-bc20a-phase20a5-simengine-swing.md` | OPEN |

## Nyitott design döntések

| # | Kérdés | Mikor |
|---|---|---|
| 1 | Crowdedness élesítés (B+C+C döntés kész?) | ~ápr 7 |
| 2 | 2s10s Szint 2 küszöbök | ~ápr 10 |
| 3 | Paper→éles váltás kiértékelés | Day 63 (~máj 14) |
| 4 | Pozíciószám 8→15 | BC22 scope |
| 5 | Skip Day Guard élesítés | ~máj 2 (30 nap shadow adat után) |

## Piaci kontextus (2026-04-01)
- Iráni háború + Hormuzi-szoros lezárás → olaj $112+, stagflációs félelmek
- S&P 500 öt egymás utáni vesztes hét, Nasdaq korrekcióban (-13%)
- BMI 8 napja csökken (49.9→45.9), VIX 24-30 tartomány
- XLK (Technology) Laggard + VETO, XLE/XLB/XLU Leader

## Következő BC-k (részletek)
→ `docs/planning/backlog.md`

## Config állapot
- `mms_enabled: True`, `factor_volatility_enabled: True`, `mms_min_periods: 10`
- `ewma_enabled: True` (éles), `crowdedness_shadow_enabled: True` (shadow)
- `yield_curve_shadow_enabled: True` (shadow), `tp1_atr_multiple: 0.75`
- `skip_day_shadow_enabled: True` (shadow)
- PT clientId-k: submit=10, close=11, eod=12, nuke=13, monitor=14, trail=15, avwap=16, gateway=17

## Tesztek
1109 passing, 0 failure

## Blokkolók
nincs
