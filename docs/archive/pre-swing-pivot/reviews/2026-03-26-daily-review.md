# IFDS Daily Review — 2026-03-26

## Pipeline
- [x] Pipeline futott — cron log létezik (1034 teszt passed)
- [x] Nincs ERROR/WARNING a pipeline logban
- [x] Telegram üzenet kiküldve
- VIX: 27.36 | BMI: 48.8% (YELLOW) | Stratégia: LONG

## Makró & Scoring
- [x] BMI rezsim ésszerű (GREEN/YELLOW/RED)
- [x] Circuit breaker NEM aktiválódott
- [!] EWMA simítás — MMS: undetermined=100
- [!] MMS multiplierek — MIND undetermined (100/100)
- [!] Crowdedness shadow — nem látható a logban
- Sector Leaders: XLE, XLB, XLF
- Sector Laggards: XLC, XLU, XLRE
- VETO: XLC, XLU, XLRE
- MMS eloszlás: Γ⁺:0 Γ⁻:0 DD:0 ABS:0 DIST:0 VOL:0 NEU:0 UND:100

## Pozíciók & Execution
- [x] Execution plan: 6 pozíció (cél: 5-8)
- [x] Szektor diverzifikáció OK — Energy: 3 (SEDG, NOG, EQT), Basic Materials: 3 (OLN, LIN, SQM)
- [x] EARN: nincs earnings 7 napon belül
- [x] Submit: 6 ticker (12 bracket) beküldve
- [x] Witching day check
- [x] monitor_positions.py (10:10 CET): OK — no leftover

## Fill Rate & Execution
- Execution plan: 6 ticker | Filled: 6 | Unfilled: 0 | Fill rate: 100%
- Unfilled tickerek: nincs
- Unfill oka: N/A

## Paper Trading P&L
- Napi P&L: $-459.03
- Kumulatív P&L: $-151.28 (-0.15%) [Day 29/21]
- TP1 hit-ek: 1 db (NOG)
- TP2 hit-ek: 0 db
- SL hit-ek: 0 db
- Loss exit hit-ek: 2 db (SQM, SEDG)
- MOC exit-ek: 9 db
- Trail aktiválások: Scenario A: nincs | Scenario B: SQM és SEDG LOSS_EXIT

## Trades

| Ticker | Qty | Entry | Exit | Típus | P&L |
|--------|-----|-------|------|-------|-----|
| NOG (A) | — | $30.24 | $30.64 | TP1 | +$17.49 |
| NOG (B1) | — | $30.24 | $30.39 | MOC | +$19.76 |
| NOG (B2) | — | $30.24 | $30.39 | MOC | +$13.27 |
| LIN (1) | — | $494.15 | $495.34 | MOC | +$16.71 |
| LIN (2) | — | $494.15 | $495.34 | MOC | +$31.03 |
| LIN (3) | — | $494.15 | $495.28 | MOC | +$2.27 |
| OLN (1) | — | $28.90 | $28.55 | MOC | -$29.67 |
| OLN (2) | — | $28.90 | $28.55 | MOC | -$29.67 |
| EQT | — | $67.61 | $66.87 | MOC | -$93.24 |
| SQM | 41 | $78.49 | $77.35 | Loss Exit | -$46.74 |
| SEDG (A) | — | $51.89 | $50.80 | Loss Exit | -$86.37 |
| SEDG (B) | — | $51.89 | $50.16 | MOC | -$273.87 |

## Leftover & Anomáliák
- [x] Nincs leftover pozíció EOD-kor (AVDL.CVR ignored)
- [x] Nincs phantom trail
- [x] Nincs idempotency hiba
- [x] Nincs late fill probléma
- [!] SEDG legnagyobb vesztes (-$360.24 összesen) — stock 50% felett az analyst target, Company Intel contradiction, Scenario B loss exit + MOC loss
- [!] Kumulatív P&L negatívba fordult: -$151.28 (-0.15%). Két egymás utáni nagy vesztes nap (-$472 + -$459 = -$931 két nap alatt)
- [!] BMI 4. egymás utáni csökkenő nap (49.9→49.4→49.2→48.8)
- [!] Company Intel contradictions: OLN (25% felett analyst high target), SEDG (50% felett consensus), EQT (23.5% felett high target), SQM (0/4 earnings beat). Ma 4/6 tickernél volt contradiction.
- [!] VIX visszaemelkedett 27.36-ra (tegnap 25.31)

## Holnap Akciólista
1. MMS undetermined továbbra is 100%
2. BMI trend figyelés — 4 napja csökken, közelít a küszöbhöz
3. Nuke NEM szükséges — minden pozíció zárva

## Megjegyzések
Második egymás utáni nagy vesztes nap (-$459.03). A kumulatív P&L negatívba fordult: -$151.28 (-0.15%), Day 29. SEDG volt a legnagyobb vesztes (-$360.24), 50%-kal az analyst target felett kereskedett. Az egyetlen fénypont NOG (+$50.52, TP1 hit + MOC profit) és LIN (+$50.01). A fill rate viszont 100% volt, ami javulás az előző napokhoz képest. BMI 4. egymás utáni csökkenő nap, VIX visszaemelkedett — a piac gyengül.
