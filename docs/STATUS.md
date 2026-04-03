# IFDS — Current Status
<!-- Frissíti: CC (/wrap-up), Chat (session végén) -->
<!-- Utolsó frissítés: 2026-04-03 ~23:00 CET, CC -->

## Paper Trading
Day 33/63 | cum. PnL: −$1,113.16 (−1.11%) | IBKR DUH118657
**Hétfőtől (ápr 6): Swing Hybrid Exit éles — 5 napos holding**

## Lezárt BC-k (2026-04-03)

| BC | Fázisok | Commitok | Tesztek |
|---|---|---|---|
| BC20 SIM-L2 Mód 2 | 20A Re-Score, 20C Trail SIM, 20B Freshness A/B | `9cb823d` `5b96270` `037fe4c` | +75 |
| BC21 Risk Layer | 21B Cross-Asset Regime, 21A Corr Guard + VaR | `69bec6a` `c63ee67` | +34 |
| BC20A Swing Hybrid Exit | 20A_1 VWAP, 20A_2 PosTrk, 20A_3 Split, 20A_4 Swing, 20A_5 SimEng | `db524c8` `edc10d6` `c90e634` `b848854` `49f5539` | +68 |
| NYSE Calendar | is_trading_day, early close, holiday guard | `e9d617a` | +22 |
| Log Infra | F1-F4 (rotation, JSONL, SQLite) | `364e53e`..`42e78e3` | +17 |
| **Összesen** | **15 fázis** | **18 commit** | **+199** |

## Élesben futó feature-ök
- EWMA simítás (span=10), MMS multiplierek (aktiválódott)
- TP1 0.75×ATR, VIX-adaptív SL cap
- M_target penalty: ×0.85 / ×0.60
- BMI momentum guard: max_positions 8→5
- close_positions.py: net BOT-SLD kalkuláció
- Cross-Asset Regime: NORMAL→CAUTIOUS→RISK_OFF→CRISIS (VIX küszöb-tolás)
- Korrelációs Guard: szektorcsoport-limitek (cyclical 5, defensive 4, financial 3, commodity 3)
- Portfolio VaR cap: 3%
- **ÚJ: Pipeline Split — Phase 1-3 (22:00) + Phase 4-6 (15:45)**
- **ÚJ: MKT entry (garantált fill) + VWAP guard (REJECT >2%, REDUCE >1%)**
- **ÚJ: Swing Management — 5 napos hold, TP1 50% partial, TRAIL, breakeven SL**
- **ÚJ: PositionTracker — state/open_positions.json**

## Shadow mode

| Feature | Shadow óta | Élesítés |
|---|---|---|
| Crowdedness composite | 2026-03-23 | ~ápr 7 |
| Skip Day Shadow Guard | 2026-04-02 | Kiértékelés ~máj 2 |

## Deployment (Mac Mini — 2026-04-06 hétfő reggel)
→ `docs/tasks/2026-04-03-monday-deployment-checklist.md`

## Következő BC-k
- BC22 (~máj): HRP Allokáció + pozíciószám 8→15
- Day 63 kiértékelés (~máj 14): Paper→éles döntés

## Tesztek
1291 passing, 0 failure

## Blokkolók
nincs
