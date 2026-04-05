# IFDS Daily Review — 2026-03-31

## Pipeline
- [x] Pipeline futott — cron log létezik (1075 teszt passed)
- [x] Nincs ERROR/WARNING a pipeline logban
- [x] Telegram üzenet kiküldve
- VIX: 29.18 | BMI: 46.2% (YELLOW) | Stratégia: LONG

## Makró & Scoring
- [x] BMI rezsim ésszerű — YELLOW, -0.1 vs tegnap (stabilizálódik?)
- [x] Circuit breaker NEM aktiválódott
- [x] EWMA simítás működik
- [x] MMS: distribution=4, gamma_negative=2, gamma_positive=1, neutral=27, undetermined=66
- [!] Crowdedness: 0 good / 100 neutral / 0 bad
- [!] BMI Momentum Guard AKTÍV (7. egymás utáni csökkenő nap, max 5)
- Sector Leaders: XLE, XLB, XLU
- Sector Laggards: XLY, XLC, XLK
- VETO: XLY, XLC, XLK
- MMS eloszlás: Γ⁺:1 Γ⁻:2 DD:0 DIST:4 VOL:0 NEU:27 UND:66

## Pozíciók & Execution
- [x] Execution plan: 5 pozíció (cél: max 5 BMI guard)
- [!] Szektor: Utilities 3 (EXC, SO, ED), Energy 1 (CNX), Basic Materials 1 (SQM)
- [x] Submit: 5 ticker (10 bracket) beküldve
- [x] monitor_positions.py: OK — no leftover (reggel)

## Fill Rate & Execution
- Execution plan: 5 ticker | Filled: 5 | Unfilled: 0 | Fill rate: 100%

## Paper Trading P&L
- Napi P&L: $-357.18
- Kumulatív P&L: $-1,104.20 (-1.10%) [Day 32/63]
- TP1 hit-ek: 0 db
- SL hit-ek: 3 db (CNX bracket SL)
- Loss exit hit-ek: 3 db (SQM, CNX×2)
- MOC exit-ek: 4 db (SO, EXC, ED, CNX maradék)
- Trail aktiválások: nincs

## Trades

| Ticker | Qty | Entry | Exit | Típus | P&L |
|--------|-----|-------|------|-------|-----|
| EXC | 142 | $48.87 | $49.03 | MOC | +$22.72 |
| SO | 87 | $96.55 | $96.55 | MOC | -$0.29 |
| ED | 52 | $113.39 | $113.06 | MOC | -$17.16 |
| SQM | 29 | $80.92 | $79.15 | Loss Exit | -$51.33 |
| CNX (SL×3) | 60+? | $40.12 | $39.78 | SL | -$61.61 |
| CNX (Loss×2) | — | $40.12 | $39.28 | Loss Exit | -$153.11 |
| CNX (MOC) | 60 | $40.12 | $38.51 | MOC | -$96.40 |

## Leftover & Anomáliák
- [!] **CNX 123 SHARE LEFTOVER** — EOD report: "Still 1 open positions! CNX: 123.0 shares". Close log: "qty adjusted 183 → 60 (intraday partial fill)". Holnap NUKE szükséges!
- [x] Nincs phantom trail
- [x] Nincs idempotency hiba
- [!] CNX volt a katasztrófa (-$311.12 összesen) — SL hit + Loss Exit + MOC, többszörös exit különböző árakon. A TP1 $45.00 (vs entry $40.12) túl messze volt — GEX call_wall override.
- [!] Utility tickerek (EXC/SO/ED) kicsi mozgással zártak — a szűk 0.75×ATR TP1 nem triggert (EXC TP1 $49.84 vs close $49.03 — közel volt!)
- [!] 0 TP1 hit — az új 0.75×ATR beállítás nem hozott TP1-et ezen a napon sem
- [!] VIX visszajött 30.77→29.18 de a piac továbbra is gyenge

## Holnap Akciólista
1. **NUKE: CNX 123 share** — holnap reggel, piaci nyitás előtt
2. MMS distribution=4 megjelent — figyelni a hatást
3. Nuke plan: `python scripts/paper_trading/nuke.py` → CNX 123sh SELL

## Megjegyzések
Ötödik egymás utáni vesztes nap (-$357.18). Kumulatív P&L átlépte a -1%-ot: -$1,104.20 (-1.10%), Day 32. CNX volt a legnagyobb vesztes (-$311, a napi veszteség 87%-a) — a GEX call_wall override miatt a TP1 $45.00 volt ($40.12 entry-nél), ami irreálisan messze van. A 3 utility ticker (EXC/SO/ED) stabilan tartotta magát (nettó +$5.27), ami a defenzív szektor erejét mutatja a bearish piacon. EXC közel volt a TP1-hez ($49.03 close vs $49.84 TP1). CNX leftover (123sh) holnap nuke-olandó.
