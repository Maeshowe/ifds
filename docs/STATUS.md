# IFDS — Current Status
<!-- Frissíti: CC (/wrap-up), Chat (session végén) -->
<!-- Utolsó frissítés: 2026-03-29 ~16:00 CET, CC -->

## Paper Trading
Day 30/63 | cum. PnL: −$572.41 (−0.57%) | IBKR DUH118657

## Aktív BC
BC18 DONE → BC20 következő (~ápr első fele)
Scope: SIM-L2 Mód 2 Re-Score (20A) → Freshness A/B (20B) → Trail Sim (20C)
**SORREND: BC20 ELŐBB mint BC20A** — baseline megőrzés az összehasonlításhoz

## Élesben futó feature-ök
- EWMA simítás (span=10), MMS multiplierek (51 ticker, min_periods=10)
- TP1 0.75×ATR, VIX-adaptív SL cap (pt_avwap.py)
- M_target penalty: ×0.85 (>20% analyst target) / ×0.60 (>50%)
- BMI momentum guard: 3+ nap csökkenés + delta ≤−1.0 → max_positions 8→5

## Shadow mode (adatgyűjtés, hatás nélkül)

| Feature | Shadow óta | Élesítés |
|---|---|---|
| Crowdedness composite | 2026-03-23 | ~ápr 7 (2 hét adat), BC20 ELŐTT is jöhet |
| 2s10s Yield Curve | 2026-03-27 | ~ápr 10 (2 hét), élesítés BC21-ben (~máj) |
| EWMA score delta log | 2026-03-27 | Már aktív (monitoring) |

## Nyitott taskok
(nincs — 8/8 DONE)

## Nyitott design döntések

| # | Kérdés | Mikor |
|---|---|---|
| 1 | Crowdedness élesítés (B+C+C döntés kész?) | ~ápr 7 |
| 2 | 2s10s Szint 2 küszöbök | ~ápr 10 |
| 3 | Paper→éles váltás kiértékelés | Day 63 (~máj 14) |
| 4 | Pozíciószám 8→15 | BC22 scope |

## Következő BC-k (részletek)
→ `docs/planning/backlog.md`

## Config állapot
- `mms_enabled: True`, `factor_volatility_enabled: True`, `mms_min_periods: 10`
- `ewma_enabled: True` (éles), `crowdedness_shadow_enabled: True` (shadow)
- `yield_curve_shadow_enabled: True` (shadow), `tp1_atr_multiple: 0.75`
- PT clientId-k: submit=10, close=11, eod=12, nuke=13, monitor=14, trail=15, avwap=16, gateway=17

## Tesztek
1075 passing, 0 failure

## Utolsó commit
e2b299d — chore: remove unused asdict import from phase4_snapshot

## Blokkolók
nincs
