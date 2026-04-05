# IFDS Daily Review — 2026-03-24

## Pipeline
- [x] Pipeline futott — cron log létezik
- [x] Nincs ERROR/WARNING a pipeline logban
- [x] Telegram üzenet kiküldve
- VIX: 26.54 | BMI: 49.4% (YELLOW) | Stratégia: LONG

## Makró & Scoring
- [x] BMI rezsim ésszerű (GREEN/YELLOW/RED)
- [x] Circuit breaker NEM aktiválódott
- [!] EWMA simítás — MMS: undetermined=100, nincs MMS hatás
- [!] MMS multiplierek — MIND undetermined (100/100)
- [!] Crowdedness shadow — nem látható a logban
- Sector Leaders: XLE, XLF, XLK
- Sector Laggards: XLP, XLRE, XLU
- VETO: XLP, XLRE, XLU
- MMS eloszlás: Γ⁺:0 Γ⁻:0 DD:0 ABS:0 DIST:0 VOL:0 NEU:0 UND:100

## Pozíciók & Execution
- [!] Execution plan: 4 pozíció (cél: 5-8) — alacsony, csak 2 teljesült
- [x] Szektor diverzifikáció OK — Energy: 3 (RRC, NOG, EFXT), Tech: 1 (AAOI)
- [x] EARN: nincs earnings 7 napon belül
- [x] Submit: orderek beküldve IBKR-be (4 ticker, 8 bracket)
- [x] Witching day check
- [x] monitor_positions.py (10:10 CET): OK — no leftover, IBKR Gateway futott (tegnapi hiba megoldva)

## Paper Trading P&L
- Napi P&L: $+447.24
- Kumulatív P&L: $+779.78 (+0.78%) [Day 27/21]
- TP1 hit-ek: 1 db (AAOI AVWAP_A_TP)
- TP2 hit-ek: 0 db
- SL hit-ek: 0 db
- MOC exit-ek: 4 db
- Trail aktiválások: Scenario A: nincs | Scenario B: nem aktiválódott (RRC threshold nem teljesült)

## Trades

| Ticker | Qty | Entry | Exit | Típus | P&L |
|--------|-----|-------|------|-------|-----|
| AAOI (A) | 7 | $101.76 | $106.24 | AVWAP_A_TP | +$30.52 |
| AAOI (B+AVWAP) | 33 | $101.88 | $113.92 | MOC | +$397.32 |
| RRC (A+B) | 388 | $45.89 | $45.94 | MOC | +$19.40 |
| NOG | — | — | — | UNFILLED | $0.00 |
| EFXT | — | — | — | UNFILLED | $0.00 |

## Leftover & Anomáliák
- [x] Nincs leftover pozíció EOD-kor (AVDL.CVR ignored)
- [x] Nincs phantom trail
- [x] Nincs idempotency hiba
- [x] Nincs late fill probléma
- [x] monitor_positions.py 10:10 CET — OK, no leftover
- [!] NOG és EFXT NEM TELJESÜLTEK — limit orderek nem filleltek, AVWAP sem. 4-ből csak 2 ticker kereskedett. Az EFXT limit $21.05 és NOG limit $28.60 valószínűleg nem érte el a piacot. Az AVWAP sem triggerelte? Ellenőrizni kell az AVWAP logot.
- [!] AAOI entry: AVWAP MKT $102.00 / $101.76 vs plan $95.76 — jelentős slippage (+6.5%), de a nap végén $113.92 MOC exit-tel mégis $397.32 profit a B bracket + AVWAP-on.
- [!] RRC entry: AVWAP MKT $45.89 vs plan $44.70 — +2.7% rosszabb entry, de azért MOC-on kicsit profitot hozott.
- [!] AAOI Company Intel contradiction: stock 108% felett az analyst target ($50 vs $95.76), mégis 93.0 score — és ma igazolta a momentum-ot ($113.92 close).
- [!] Rate-sensitive=True — TNX 4.39%, figyelni a rate-érzékeny szektorokat

## Holnap Akciólista
1. NOG/EFXT unfill vizsgálat — AVWAP log ellenőrzés, miért nem triggerelt
2. MMS undetermined továbbra is 100% — state/mms/ fájlok állapota
3. Nuke NEM szükséges — minden pozíció zárva

## Megjegyzések
Kiváló nap (+$447.24), az AAOI rakéta volt: $101.88 entry → $113.92 MOC, a B bracket önmagában +$397.32. A Company Intel ellentmondás (108% analyst target felett) ellenére a momentum igazolta a scoring-ot. RRC kis profitot hozott ($19.40), de az entry slippage ($45.89 vs $44.70) nagy volt. NOG és EFXT kiestek — csak 2/4 ticker kereskedett ténylegesen, ami csökkenti a diverzifikációt. Kumulatív P&L átlépte a +0.75%-ot: $+779.78 (+0.78%), Day 27.
