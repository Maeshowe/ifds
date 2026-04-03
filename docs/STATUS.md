# IFDS — Current Status
<!-- Frissíti: CC (/wrap-up), Chat (session végén) -->
<!-- Utolsó frissítés: 2026-04-03 ~23:30 Budapest, Chat -->

## Paper Trading
Day 33/63 | cum. PnL: −$1,113.16 (−1.11%) | IBKR DUH118657
**Hétfőtől (ápr 6): Swing Hybrid Exit éles — 5 napos holding**
Deployment checklist: `docs/tasks/2026-04-03-monday-deployment-checklist.md`

## Lezárt BC-k (2026-04-03 — egy nap alatt)

| BC | Commitok | Tesztek |
|---|---|---|
| BC20 SIM-L2 Mód 2 (20A+20C+20B) | `9cb823d` `5b96270` `037fe4c` | +75 |
| BC21 Risk Layer (21B+21A) | `69bec6a` `c63ee67` | +34 |
| BC20A Swing Hybrid Exit (20A_1–5) | `db524c8` `edc10d6` `c90e634` `b848854` `49f5539` | +68 |
| Log Infra F1-F4 | 6 commit | +17 |
| NYSE Calendar | `6c10be5` | +5 |
| Telegram Split | `8c0bd30` | — |
| Leftover fix + Skip day | 2 commit | — |
| **Összesen: 20 commit** | | **+199 teszt** |

Teszt baseline: **1092 → 1291**

## Élesben futó feature-ök (hétfőtől)
- Pipeline Split: Phase 1-3 (22:00) + Phase 4-6 (15:45 Budapest)
- MKT entry + VWAP guard (REJECT >2%, REDUCE >1%)
- Swing Management: 5 napos hold, TP1 50% partial, TRAIL, breakeven SL, D+5 MOC
- PositionTracker: state/open_positions.json
- Cross-Asset Regime: NORMAL→CAUTIOUS→RISK_OFF→CRISIS (VIX küszöb-tolás)
- Korrelációs Guard: szektorcsoport-limitek + Portfolio VaR cap 3%
- NYSE trading calendar: holiday skip + early close handling
- Telegram: MACRO SNAPSHOT (22:00) + TRADING PLAN (15:45)
- EWMA simítás, MMS multiplierek, M_target penalty, BMI momentum guard

## Shadow mode

| Feature | Shadow óta | Élesítés |
|---|---|---|
| Crowdedness composite | 2026-03-23 | ~ápr 7 |
| Skip Day Shadow Guard | 2026-04-02 | Kiértékelés ~máj 2 |

## Következő
- BC22 (~máj): HRP Allokáció + pozíciószám 8→15
- Day 63 kiértékelés (~máj 14): Paper→éles döntés

## Tesztek
1291 passing, 0 failure

## Blokkolók
nincs
