# IFDS Daily Review — 2026-04-10

## Pipeline
- [x] Pipeline futott — cron_intraday_20260410_154501.log ✅
- [x] Nincs Error 163 (IBKR Precautionary fix működik) ✅
- [x] POST-SUBMIT VERIFICATION: all 8 accounted for ✅
- [x] Company Intel futott 15:50-kor (deploy_intraday.sh-ban) ✅
- [x] Telegram üzenetek kiküldve (3 db)
- VIX: 19.06 (normal) | TNX: 4.29% | Stratégia: LONG

## Makró & Scoring
- [x] Circuit breaker NEM aktiválódott
- [x] BMI Momentum Guard — NEM aktív
- Phase 4: Analyzed 1444 | Passed 210 | Crowded: 5
- Phase 6: 8 pozíció | 3 sector limit | 7 position limit excluded
- Freshness Alpha: 8 tickerre alkalmazva

## Fill Rate & Execution
- Execution plan: 8 ticker (friss CSV ✅) | Filled: 8 | Fill rate: 100%
- Existing skip: AVDL.CVR
- Nincs Error 163 / Error 383 ✅
- MKT entry fill-ek rendben

## Paper Trading P&L
- Napi P&L: **-$486.91**
- Kumulatív P&L: **-$2,415.23 (-2.42%)** [Day 40/63]
- TP1: 1 | TRAIL: 1 | LOSS_EXIT: 3 | MOC: 7

## Trades

| Ticker | Qty | Entry | Exit | Típus | P&L |
|--------|-----|-------|------|-------|-----|
| SBRA | 925 | $20.38 | $20.46 | MOC | +$74.00 |
| LUNR | 53 | $22.90 | $23.58 | MOC | +$35.85 |
| GFS (A) | 24 | $49.72 | $50.00 | TP1 | +$6.72 |
| ADC | 105 | $78.16 | $78.21 | MOC | +$5.25 |
| GFS (B) | 48 | $49.72 | $49.28 | TRAIL | -$21.12 |
| VTR | 234 | $85.29 | $84.94 | MOC | -$81.90 |
| DOCN | 32 | $82.92 | $78.36 | LOSS_EXIT | -$145.92 |
| HLIO | 64 | $73.27 | $70.90 | LOSS_EXIT | -$151.89 |
| ARM | 30 | $158.04 | $151.11 | LOSS_EXIT | -$207.90 |

## Leftover & Anomáliák
- [x] Nincs leftover EOD-kor
- [!] "No orders found for cancellation" — szisztematikus minden Scenario B loss exit-nél (ARM, DOCN, LUNR, HLIO). Valószínű ok: clientId mismatch (submit=10, monitor=15). Az openOrders() csak a saját clientId ordereit adja vissza.
- [!] LION/SDRL phantom — továbbra is aktív 22:00 utáni ciklusban
- [x] GFS Scenario A trail működött (TP1 fill → trail → trail hit breakeven-nél)

## Scoring Validáció — Élő Megerősítés
- ARM (142.5 score, FRESH) → -$207.90 (legnagyobb vesztes)
- HLIO (139.5 score, FRESH) → -$151.89 (második legnagyobb vesztes)
- DOCN (95.0 score) → -$145.92
- LUNR (93.5 score) → +$35.85 (nyereséges)
- ADC (91.5 score) → +$5.25 (nyereséges)
- **Az inverz quintilis minta ma is érvényesült** — a magas score-ok veszítenek, az alacsonyak nyernek.

## Holnap Akciólista
1. ClientId mismatch vizsgálat — CC task: monitor (clientId=15) nem látja a submit (clientId=10) ordereit
2. Phantom LION/SDRL — CC task prioritás emelése
3. Az első teljes automatikus hibamentes nap ✅ — a pipeline mechanikailag stabil

## Megjegyzések
Pipeline mechanikailag hibamentes — az első ilyen nap ápr 3 óta. A P&L negatív, de az okok nem mechanikai: a scoring inverz mintája (magas score = rossz teljesítmény) a fő driver, amit a scoring validáció report alátámaszt. A Scenario A trail (GFS) és a Scenario B loss exit (ARM, DOCN, HLIO) helyesen működtek.
