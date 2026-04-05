# IFDS Daily Review — 2026-03-27

## Pipeline
- [x] Pipeline futott — cron log létezik (1034 teszt passed)
- [x] Nincs ERROR/WARNING a pipeline logban
- [x] Telegram üzenet kiküldve
- VIX: 28.32 | BMI: 47.6% (YELLOW) | Stratégia: LONG

## Makró & Scoring
- [x] BMI rezsim ésszerű (GREEN/YELLOW/RED)
- [x] Circuit breaker NEM aktiválódott
- [!] EWMA simítás — MMS: undetermined=100
- [!] MMS multiplierek — MIND undetermined (100/100)
- [!] Crowdedness shadow — nem látható a logban
- Sector Leaders: XLE, XLB, XLF
- Sector Laggards: XLC, XLRE, XLK
- VETO: XLC, XLRE, XLK (XLK új VETO — Technology most Laggard!)
- MMS eloszlás: Γ⁺:0 Γ⁻:0 DD:0 ABS:0 DIST:0 VOL:0 NEU:0 UND:100

## Pozíciók & Execution
- [!] Execution plan: 4 pozíció (cél: 5-8) — alacsony
- [x] Szektor diverzifikáció — Energy: 3 (MPLX, NOV, PBF), Basic Materials: 1 (ARMN)
- [x] EARN: nincs earnings 7 napon belül
- [x] Submit: 3 ticker (6 bracket) — ARMN nem beküldve
- [x] Witching day check
- [x] monitor_positions.py (10:10 CET): OK — no leftover

## Fill Rate & Execution
- Execution plan: 4 ticker | Filled: 3 | Unfilled: 1 | Fill rate: 75%
- Unfilled tickerek: ARMN
- Unfill oka: nem beküldve a submit logban (valószínűleg existing skip vagy limit issue)

## Paper Trading P&L
- Napi P&L: $-421.13
- Kumulatív P&L: $-572.41 (-0.57%) [Day 30/21]
- TP1 hit-ek: 0 db
- TP2 hit-ek: 0 db
- SL hit-ek: 0 db
- Loss exit hit-ek: 0 db
- MOC exit-ek: 6 db
- Trail aktiválások: nincs

## Trades

| Ticker | Qty | Entry | Exit | Típus | P&L |
|--------|-----|-------|------|-------|-----|
| PBF | 45 | $50.37 | $51.24 | MOC | +$39.15 |
| NOV (1) | — | $19.99 | $19.88 | MOC | -$49.89 |
| NOV (2) | — | $19.99 | $19.88 | MOC | -$5.30 |
| NOV (3) | — | $19.99 | $19.88 | MOC | -$19.65 |
| MPLX (1) | — | $59.10 | $58.13 | MOC | -$256.96 |
| MPLX (2) | — | $59.10 | $58.13 | MOC | -$128.48 |
| **ARMN** | — | — | — | **UNFILLED** | $0.00 |

## Leftover & Anomáliák
- [x] Nincs leftover pozíció EOD-kor (AVDL.CVR ignored)
- [x] Nincs phantom trail
- [x] Nincs idempotency hiba
- [x] Nincs late fill probléma
- [!] ARMN UNFILLED — submit log "Submitted: 3 tickers", ARMN nem került be. Vizsgálni: existing skip? limit issue?
- [!] MPLX legnagyobb vesztes (-$385.44 összesen) — $59.10 entry vs $58.13 MOC, masszív drawdown. TP1 $60.00 közel volt de nem érte el.
- [!] BMI **-1.2 esés** (48.8→47.6), eddigi legnagyobb napi BMI drop. 5. egymás utáni csökkenő nap.
- [!] XLK (Technology) most LAGGARD és VETO — momentum -4.28%, lefelé tendál.
- [!] VIX tovább emelkedett: 27.36→28.32
- [!] Csak 4 pozíció a planben, 3 kereskedett — alacsony diverzifikáció
- [!] 3. egymás utáni vesztes nap: -$472, -$459, -$421 = -$1,352 három nap alatt

## Holnap Akciólista
1. ARMN unfill — submit log részletesebb vizsgálat
2. MMS undetermined továbbra is 100%
3. BMI trend kritikus — 5 napja csökken, -1.2 napi drop
4. Nuke NEM szükséges — minden pozíció zárva
5. Hétvége — nincs kereskedés hétfőig

## Megjegyzések
Harmadik egymás utáni nagy vesztes nap (-$421.13). A kumulatív P&L -$572.41 (-0.57%), Day 30. MPLX volt a legnagyobb vesztes (-$385.44), közel járt a TP1-hez ($60.00) de nem érte el. PBF volt az egyetlen nyerő (+$39.15). BMI rekord esése (-1.2) aggasztó — 5 napja csökken folyamatosan (49.9→47.6). VIX 28.32, emelkedő trend. XLK most VETO — a Technology szektor Laggard lett. A háromnapos veszteségsorozat (-$1,352) a korábbi nyereséget teljesen erodálta és mélyen negatívba vitte a kumulatív P&L-t.
