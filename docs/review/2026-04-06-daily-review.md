# IFDS Daily Review — 2026-04-06

## Pipeline
- [x] Pipeline futott — KÉTSZER: 14:00 CEST (FRED DOWN → HALT) + 22:00 CEST (OK)
- [x] 22:00 futás: 1291 teszt passed, Telegram kiküldve
- [!] 14:00 futás: FRED API timeout (7159ms) → HALT. Miért futott 14:00-kor? Crontab módosult?
- [!] 22:00 futás: "No actionable positions" — a pipeline holnapra méretezett, de ma is futott a submit!
- VIX: 24.38 | BMI: 46.8% (YELLOW, **+1.8** vs tegnap!) | Stratégia: LONG

## Makró & Scoring
- [x] BMI **fordult**: +1.8 — első emelkedés 9 nap után (45.0→46.8)!
- [x] VIX stabil: 24.38 (elevated)
- [!] **XLK visszatért Leader-be!** +5.28% momentum, UP trend. Drámai fordulat a korábbi VETO-ból.
- [!] **XLU most VETO** — az elmúlt hetekben Leader volt, most Laggard (+1.27%)
- [!] **XLE továbbra is VETO** (-4.60%, Laggard)
- Sector Leaders: XLK, XLC, XLRE
- VETO: XLE, XLP, XLU
- A szektorrotáció MEGFORDULT — tech/comm visszajön, utility/energy kiesik

## Crontab kérdés
- [!] **Két cron futás**: `cron_20260406_140001.log` (14:00) + `cron_20260406_220000.log` (22:00)
- A 14:00-ás futás FRED timeout-on HALT-olt
- A pipeline schedule megváltozott 10:00-ról? Vagy ez a BC20A Pipeline Split előkészítés (Phase 1-3 este, Phase 4-6 délután)?
- **Tisztázandó Tamással**: mi a szándékolt cron schedule?

## Fill Rate & Execution
- Execution plan (04-03): 8 ticker | Submit (04-06): 2 új (UNIT, SPHR) + 6 existing skip | Fill rate: ≈100%
- Existing skip: SKM, LIN, NEM, KGC, DBRG, BRX — ezek az 04-03-as plan-ből még nyitva
- [x] Monitor state: 2 ticker (UNIT, SPHR) írva

## Paper Trading P&L
- Napi P&L: **-$91.23**
- Kumulatív P&L: **-$1,497.00 (-1.50%) [Day 36/63]**
- TP1 hit-ek: 0
- SL hit-ek: 0
- Loss exit: 0
- MOC exit-ek: 8 (mind MOC)

## Trades (pt_events JSONL-ből)

| Ticker | Qty | Entry | Exit | Típus | P&L |
|--------|-----|-------|------|-------|-----|
| UNIT | 500+55 | $10.12 | $10.30 | MOC | **+$101.67** |
| BRX | 281 | $28.90 | $28.91 | MOC | +$2.81 |
| DBRG | 427 | $15.44 | $15.41 | MOC | -$12.81 |
| SPHR | 25 | $127.22 | $126.29 | MOC | -$23.25 |
| KGC | 185 | $31.51 | $31.35 | MOC | -$29.60 |
| LIN | 15 | $502.60 | $499.24 | MOC | -$50.40 |
| NEM | 59 | $114.05 | $112.70 | MOC | -$79.65 |

## Leftover & Anomáliák (IBKR screenshot megerősítve)
- [x] **EVRG 235sh NUKE OK** — IBKR trades tab: SLD 235sh @ $82.23, 15:30:26 ✅
- [x] **CRGY 672sh + AAPL 100sh — PHANTOM** — IBKR trades tab-ban NEM léteznek. A monitor_positions tévesen detektálta. Root cause: valószínűleg CC tesztelés teszt plan CSV-kből, vagy ib.positions() cache probléma a 14:00/22:00-ás többszörös futásnál.
- [!] **LION és SDRL trail/loss_exit event-ek** a pt_events-ben — NEM mai tickerek. A monitor régi state fájlból újra-detektálta. Dupla event-ek (12:00 és 20:00-kor is ugyanazok).
- [!] **monitor_positions 5× futott** — 14:00-kor és 22:00-kor is 5 párhuzamos futás. Crontab hiba — több entry van rá.
- [!] **pt_close_2026-04-06.log üres** — a close script a régi pt_close.log-ba írt, nem a napi fájlba.
- [x] UNIT +$101.67 — napi nyerő, XLRE Leader
- [x] **Nincs leftover az IBKR-ben** — minden pozíció rendben zárva 21:59-re

## Log Infrastruktúra ✅
- [x] **Napi log rotáció működik** — pt_*_2026-04-06.log fájlok léteznek
- [x] **pt_events JSONL működik** — teljes napi lifecycle egy fájlban
- [x] **1291 teszt** — a log modernizáció tesztjei beépültek (1077→1291)
- [!] pt_close napi log üres — a close script nem a napi fájlba ír?

## Holnap Akciólista
1. **Crontab ellenőrzés (Mac Mini)** — miért futott 14:00-kor is? Miért fut a monitor_positions 5×?
2. **pt_close napi log** — miért üres? CC ellenőrizze
3. **LION/SDRL phantom monitor state** — régi state fájlok törlése
4. **Telegram audit task CC-nek** (nyitva: `docs/tasks/2026-04-02-telegram-audit-timestamps.md`)
5. **NYSE calendar task CC-nek** (nyitva: `docs/tasks/2026-04-03-nyse-trading-calendar.md`)

## Megjegyzések

A piaci környezet **drámaian megváltozott**: BMI megfordult (+1.8, első emelkedés 9 nap után), XLK visszatért Leader-be (+5.28%), XLU/XLE VETO lett. A szektorrotáció az elmúlt 2 hét defenzív (utility/energy) fókuszáról visszaállt a growth/tech-re. A VIX 24.38 — stabil elevated, de nem panic.

A napi P&L -$91.23 — enyhe veszteség, 8/8 MOC. UNIT +$101 nyerő (XLRE Leader). NEM és LIN a legnagyobb vesztesek (Basic Materials).

**A log modernizáció működik!** A pt_events JSONL egy pillantásra megmutatja a nap teljes történetét. 1291 teszt (vs korábbi 1077).

**IBKR screenshot megerősíti:** EVRG nuke OK, CRGY/AAPL phantom (nem létezik az accountban), minden pozíció lezárva.
