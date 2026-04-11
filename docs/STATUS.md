# IFDS — Current Status
<!-- Frissíti: CC (/wrap-up), Chat (session végén) -->
<!-- Utolsó frissítés: 2026-04-11 Budapest, CC -->

## Paper Trading
Day 40/63 | cum. PnL: ~−$1,928 (~−1.93%) | IBKR DUH118657
**BC23 Scoring & Exit Redesign deployolva** — hétfőtől éles
**Mac Mini**: git pull OK, crontab frissítés szükséges (16:15 submit)

## BC23 — Scoring & Exit Redesign (2026-04-11)

| Változás | Régi | Új |
|---|---|---|
| Scoring súlyok | flow=0.40 funda=0.30 tech=0.30 | **flow=0.60** funda=0.10 tech=0.30 |
| Freshness bonus | 1.5× | **1.0** (kikapcsolva) |
| RS vs SPY bonus | +40 | **+15** |
| TP1 ATR multiple | 0.75 (0.5:1 R:R) | **1.5 (1:1 R:R)** |
| TP2 ATR multiple | 3.0 | **2.0** |
| Bracket split | 33/67 | **50/50** |
| Call wall TP1 | aktív | **kikapcsolva** |
| Max positions | 8 | **5** |
| Score threshold | nincs | **85** |
| Risk per trade | 0.5% | **0.7%** |
| Multiplier chain | 7 aktív | **3 aktív** (M_vix, M_gex, M_target) |
| MMS sizing | on | **off** |
| VWAP REDUCE | aktív | **eltávolítva** |
| Submit idő | 15:45 CEST | **16:15 CEST** |

## Élesben futó feature-ök
- Pipeline Split: Phase 1-3 (22:00) + Phase 4-6 (**16:15** Budapest)
- MKT entry + VWAP guard (csak REJECT >2%)
- Swing Management: 5 napos hold, TP1 50% partial, TRAIL, breakeven SL, D+5 MOC
- Dynamic positions: max 5, score threshold 85
- Cross-Asset Regime + Korrelációs Guard + Portfolio VaR 3%
- Company Intel: 16:15 submit után (friss tickerekre)
- EWMA simítás, M_target penalty, BMI momentum guard

## Shadow mode

| Feature | Shadow óta | Élesítés |
|---|---|---|
| Crowdedness composite | 2026-03-23 | ~ápr 7 |
| Skip Day Shadow Guard | 2026-04-02 | Kiértékelés ~máj 2 |

## Következő
- BC23 live monitoring (hétfőtől): dynamic threshold, TP1 hit rate, pozíciószám
- Day 63 kiértékelés (~máj 14): Paper→éles döntés

## Tesztek
1315 passing, 0 failure

## Blokkolók
nincs
