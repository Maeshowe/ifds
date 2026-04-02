# IFDS — Current Status
<!-- Frissíti: CC (/wrap-up), Chat (session végén) -->
<!-- Utolsó frissítés: 2026-04-02 ~10:00 CET, Chat -->

## Paper Trading
Day 33/63 | cum. PnL: −$1,113.16 (−1.11%) | IBKR DUH118657
Kiterjesztve 63 napra (~máj 14 kiértékelés)

## Aktív BC
BC18 DONE → BC20 következő (~ápr első fele)
Scope: SIM-L2 Mód 2 Re-Score (20A) → Freshness A/B (20B) → Trail Sim (20C)
**SORREND: BC20 ELŐBB mint BC20A** — baseline megőrzés az összehasonlításhoz

## Élesben futó feature-ök
- EWMA simítás (span=10), MMS multiplierek (day 15/10, aktiválódott)
- TP1 0.75×ATR, VIX-adaptív SL cap (pt_avwap.py)
- M_target penalty: ×0.85 (>20% analyst target) / ×0.60 (>50%)
- BMI momentum guard: 3+ nap csökkenés + delta ≤−1.0 → max_positions 8→5
- close_positions.py: net BOT-SLD kalkuláció (fix: suffix matching → net qty)

## Shadow mode (adatgyűjtés, hatás nélkül)

| Feature | Shadow óta | Élesítés |
|---|---|---|
| Crowdedness composite | 2026-03-23 | ~ápr 7 (2 hét adat), BC20 ELŐTT is jöhet |
| 2s10s Yield Curve | 2026-03-27 | ~ápr 10 (2 hét), élesítés BC21-ben (~máj) |
| EWMA score delta log | 2026-03-27 | Már aktív (monitoring) |
| **Skip Day Shadow Guard** | **2026-04-02** | **Kiértékelés 30 nap múlva (~máj 2)** |

## Nyitott taskok
(nincs — mind DONE)

## Backlog (parkolt)
- GEX call_wall TP1 override felülvizsgálat — `min(call_wall, entry + 0.75×ATR)` vs jelenlegi override. Mikor: ha VIX ~15 körül lesz.

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
1077+ passing, 0 failure

## Blokkolók
nincs
