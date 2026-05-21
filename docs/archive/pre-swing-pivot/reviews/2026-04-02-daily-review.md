# IFDS Daily Review — 2026-04-02

## Pipeline
- [x] Pipeline futott — cron log létezik (1077 teszt passed)
- [x] Nincs ERROR/WARNING a pipeline logban
- [x] Telegram üzenet kiküldve
- VIX: 26.53 | BMI: 45.8% (YELLOW) | Stratégia: LONG

## Makró & Scoring
- [x] BMI rezsim ésszerű — YELLOW, -0.0 vs tegnap (stabilizálódik)
- [x] Circuit breaker NEM aktiválódott
- [!] BMI Momentum Guard: Telegram küldött "max 8→5"-öt, de Phase 6 mégis 8 pozíciót méretezett! Guard valójában NEM aktiválódott (delta -0.51 > -1.0 küszöb). A Telegram üzenet félrevezető — korábbi futásból vagy regresszióból.
- [!] MMS: distribution=4, gamma_negative=2, neutral=9, undetermined=85
- [!] XLE VETO lett (Laggard, -2.64%) — első alkalom a PT periódusban!
- Sector Leaders: XLB, XLU, XLRE
- VETO: XLK, XLE, XLY

## Pozíciók & Execution
- [!] Execution plan: 8 pozíció (kellene max 5 BMI guard, de a guard nem aktiválódott → 8)
- [x] Szektor: Utilities 3 (EXC, DUK, EVRG), Basic Materials 3 (DOW, ERO, CF), Real Estate 2 (DBRG, MAC)
- [x] Submit: 8 ticker beküldve
- [!] monitor_positions: EMN 36sh + CENX 23sh leftover (tegnapról)

## Fill Rate & Execution
- Execution plan: 8 ticker | Filled: 8 | Unfilled: 0 | Fill rate: 100%

## Paper Trading P&L
- Napi P&L: $-292.61
- Kumulatív P&L: $-1,405.77 (-1.41%) [Day 34/63]
- TP1 hit-ek: 2 db (EVRG @ $82.84, EXC @ $49.37) ✅
- SL hit-ek: 4 db (DOW×2, CF×2)
- Loss exit hit-ek: 1 db (CF)
- MOC exit-ek: 7 db
- Trail: nincs

## Trades

| Ticker | Qty | Entry | Exit | Típus | P&L |
|--------|-----|-------|------|-------|-----|
| MAC | 188 | $19.06 | $19.54 | MOC | +$90.24 |
| EVRG | — | $82.60 | $82.84 | TP1 | +$11.36 |
| EXC (TP1) | — | $49.25 | $49.37 | TP1 | +$6.00 |
| EXC (MOC) | — | $49.25 | $49.31 | MOC | +$15.24 |
| DBRG | 427 | $15.44 | $15.43 | MOC | -$4.27 |
| DUK | 178 | $132.55 | $132.26 | MOC | -$51.62 |
| DOW | 80 | $41.87 | $41.06-41.29 | SL+MOC | -$110.68 |
| CF | 34 | $134.46 | $130.44-131.16 | SL+LOSS_EXIT | -$248.88 |

## 🔴 KRITIKUS: EVRG 235sh Leftover
- EOD: "Still 1 open positions! EVRG: 235.0 shares"
- Close log: "EVRG: MOC SELL 235 shares" — elküldve, de nem teljesült?
- **A close_positions fix deployolódott?** Ha igen, ez új bug; ha nem, a régi suffix probléma.
- Holnap NUKE: EVRG 235sh (+ EMN 36sh + CENX 23sh ha nem nuke-olódtak)

## Leftover & Anomáliák
- [!] **EVRG 235sh leftover** — close MOC-olt de EOD mégis nyitva mutatja
- [!] **EMN 36sh + CENX 23sh** — tegnapról, monitor_positions detektálta. Nuke megtörtént?
- [!] **CF -$248.88** — AVWAP entry $134.46, TP1 $151.48 (call_wall override + AVWAP eltolás). Irreális target. A napi veszteség 85%-a.
- [x] **2 TP1 hit!** — EVRG + EXC, mindkettő utility, szűk 0.75×ATR TP1. A rendszer működik defenzív szektorokban.
- [x] MAC +$90.24 — XLRE Leader, jó pick

## Holnap Akciólista
1. **NUKE: EVRG 235sh** (+ EMN/CENX ha még nyitva)
2. **Close_positions fix ellenőrzés** — deployolódott-e a net BOT-SLD fix?
3. **Telegram audit task CC-nek** — `docs/tasks/2026-04-02-telegram-audit-timestamps.md`

## Megjegyzések
Hatodik egymás utáni vesztes nap (-$292.61), kumulatív -$1,405.77 (-1.41%), Day 34. CF volt a katasztrófa (-$248.88, call_wall AVWAP TP1 $151.48 irreális). De **2 TP1 hit** (EVRG + EXC)! Az 0.75×ATR TP1 a utility tickereknél működik. MAC is nyerő (+$90.24). A rendszer a defenzív szektorokban (Utilities, Real Estate) konzisztensen jobb mint az Energy/Materials-ban. Az EVRG leftover aggasztó — ha a close_positions fix nem deployolódott, az a régi suffix bug; ha deployolódott, új probléma van.
