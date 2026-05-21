# IFDS Daily Review — 2026-03-25

## Pipeline
- [x] Pipeline futott — cron log létezik (1034 teszt passed)
- [x] Nincs ERROR/WARNING a pipeline logban
- [x] Telegram üzenet kiküldve
- VIX: 25.31 | BMI: 49.2% (YELLOW) | Stratégia: LONG

## Makró & Scoring
- [x] BMI rezsim ésszerű (GREEN/YELLOW/RED)
- [x] Circuit breaker NEM aktiválódott
- [!] EWMA simítás — MMS: undetermined=100
- [!] MMS multiplierek — MIND undetermined (100/100)
- [!] Crowdedness shadow — nem látható a logban
- Sector Leaders: XLE, XLF, XLI
- Sector Laggards: XLP, XLU, XLRE
- VETO: XLP, XLU, XLRE
- MMS eloszlás: Γ⁺:0 Γ⁻:0 DD:0 ABS:0 DIST:0 VOL:0 NEU:0 UND:100

## Pozíciók & Execution
- [x] Execution plan: 6 pozíció (cél: 5-8)
- [x] Szektor diverzifikáció OK — Energy: 3 (NFG, BP, BKR), Industrials: 3 (MTZ, HAFN, HWM)
- [x] EARN: nincs earnings 7 napon belül
- [x] Submit: 6 ticker (12 bracket) beküldve
- [x] Witching day check
- [x] monitor_positions.py (10:10 CET): OK — no leftover

## Paper Trading P&L
- Napi P&L: $-472.03
- Kumulatív P&L: $+307.75 (+0.31%) [Day 28/21]
- TP1 hit-ek: 0 db
- TP2 hit-ek: 0 db
- SL hit-ek: 0 db
- MOC exit-ek: 11 db
- Trail aktiválások: Scenario A: nincs | Scenario B: BKR nem aktiválódott (price $62.72 < profit threshold $63.81)

## Trades

| Ticker | Qty | Entry | Exit | Típus | P&L |
|--------|-----|-------|------|-------|-----|
| BKR | 73 | $63.40 | $62.59 | MOC | -$59.13 |
| HAFN (1) | 500 | $7.53 | $7.47 | MOC | -$28.99 |
| HAFN (2) | 54 | $7.53 | $7.47 | MOC | -$3.13 |
| MTZ (A) | 19 | $324.99 | $322.70 | MOC | -$43.57 |
| MTZ (B) | 38 | $324.99 | $322.70 | MOC | -$87.15 |
| NFG (1) | 111 | $94.91 | $94.35 | MOC | -$62.44 |
| NFG (2) | 89 | $94.91 | $94.35 | MOC | -$50.07 |
| NFG (3) | 100 | $94.91 | $94.36 | MOC | -$55.26 |
| NFG (4) | 33 | $94.91 | $94.36 | MOC | -$18.23 |
| HWM (A) | 35 | $242.39 | $241.47 | MOC | -$32.03 |
| HWM (B) | 35 | $242.39 | $241.47 | MOC | -$32.03 |
| **BP** | — | — | — | **UNFILLED** | $0.00 |

## Leftover & Anomáliák
- [x] Nincs leftover pozíció EOD-kor (AVDL.CVR ignored)
- [x] Nincs phantom trail
- [x] Nincs idempotency hiba
- [x] Nincs late fill probléma
- [!] BP UNFILLED — 6-ból csak 5 ticker kereskedett. Limit $44.79 nem teljesült, AVWAP sem triggerelt.
- [!] 100% vesztes nap — mind az 5 teljesült ticker MOC-on veszteséggel zárt. Sem TP1, sem trail nem aktiválódott.
- [!] NFG GEX regime: "negative" flag a pipeline-ban, mégis átment (GEX excluded 15 tickert, de NFG nem volt köztük).
- [!] HAFN split close: 500+54 share (2 leg) — MAX_ORDER_SIZE=500 limit miatt splittelve, működik rendben.
- [!] AVWAP fill árak: MTZ ($326.54/$325.79 vs plan $322.65 — rosszabb), NFG ($94.99/$94.94 vs plan $94.78 — kicsit rosszabb), HWM ($242.29 vs plan $239.51 — rosszabb), BKR ($63.40 vs plan $63.49 — kicsit jobb), HAFN ($7.53 vs plan $7.64 — kedvezőbb)

## Holnap Akciólista
1. BP unfill vizsgálat — AVWAP log, limit nem teljesült
2. MMS undetermined továbbra is 100%
3. Nuke NEM szükséges — minden pozíció zárva

## Megjegyzések
Első jelentős vesztes nap a paper trading periódusban (-$472.03). Mind az 5 teljesült ticker veszteséggel zárt MOC-on — a piac széles körben gyengült. NFG volt a legnagyobb vesztes (-$185.99 összesen), MTZ következett (-$130.72). A kumulatív P&L visszaesett +$307.75-re (+0.31%), Day 28. A tegnapi AAOI nyereség nagy részét visszaadta a piac. BMI továbbra is YELLOW (49.2%, -0.3), harmadik egymás utáni csökkenő nap.
