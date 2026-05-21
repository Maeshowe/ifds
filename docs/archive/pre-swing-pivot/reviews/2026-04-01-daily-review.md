# IFDS Daily Review — 2026-04-01

## Pipeline
- [x] Pipeline futott — cron log létezik (1077 teszt passed)
- [x] Nincs ERROR/WARNING a pipeline logban
- [x] Telegram üzenet kiküldve
- VIX: 24.25 | BMI: 45.9% (YELLOW) | Stratégia: LONG

## Makró & Scoring
- [x] BMI rezsim ésszerű — YELLOW, -0.3 vs tegnap (8. egymás utáni csökkenő nap)
- [x] Circuit breaker NEM aktiválódott
- [x] VIX jelentősen csökkent: 29.18→24.25 (elevated)
- [!] MMS: neutral=5, undetermined=95 — visszaesett vs tegnap (neutral=27, undetermined=66)!
- [!] BMI Momentum Guard AKTÍV (max 5)
- [!] XLE visszaesett Leader-ből Neutral-ba (+0.69% momentum)
- Sector Leaders: XLB, XLU, XLRE
- Sector Laggards: XLY, XLI, XLK
- VETO: XLY, XLI, XLK

## Pozíciók & Execution
- [x] Execution plan: 5 pozíció (max 5 BMI guard)
- [x] Submit: 5 ticker (10 bracket) beküldve
- [!] DBRG: SL $15.34 vs entry $15.42 — mindössze $0.08 SL távolság (!!)
- [!] monitor_positions: CNX 123sh leftover (tegnapi) detektálva

## Fill Rate & Execution
- Execution plan: 5 ticker | Filled: 5 | Unfilled: 0 | Fill rate: 100%

## Paper Trading P&L
- Napi P&L: $-8.96
- Kumulatív P&L: $-1,113.16 (-1.11%) [Day 33/63]
- TP1 hit-ek: 1 db (CENX @ $62.41)
- SL hit-ek: 2 db (EMN bracket SL @ $76.12)
- Trail hit-ek: 1 db (CENX @ $62.36)
- MOC exit-ek: 7 db (PNW, EMN×2, TECK×4)

## Trades

| Ticker | Qty | Entry | Exit | Típus | P&L |
|--------|-----|-------|------|-------|-----|
| PNW | 80 | $100.75 | $101.58 | MOC | +$66.40 |
| CENX | 11 | $61.01 | $62.41 | TP1 | +$15.40 |
| CENX | 34 | $61.01 | $62.36 | TRAIL | +$45.90 |
| TECK | 258 | $53.23 | $53.23 | MOC | -$1.30 |
| EMN (SL) | 36+18 | $77.04 | $76.12 | SL | -$49.68 |
| EMN (MOC) | 36+18 | $77.04 | $75.85 | MOC | -$85.68 |

## 🔴 KRITIKUS: Leftover pozíciók
- **EMN 36 share NYITVA MARADT** — EOD: "Still 2 open positions! EMN: 36.0 shares"
- **CENX 23 share NYITVA MARADT** — EOD: "CENX: 23.0 shares" — de a close log "position fully closed intraday (TP/SL), skipping MOC" írja. Inkonzisztencia!
- **CNX 123 share** — tegnapi leftover, monitor_positions detektálta, de a nuke nem futott le?
- Holnap NUKE szükséges: EMN 36sh + CENX 23sh + CNX 123sh (ha még nyitva)

## Leftover & Anomáliák
- [!] **CENX leftover bug** — close_positions "fully closed" loggolt, de EOD 23 share-t mutat. A close_positions helytelenül kalkulálta az intraday zárt mennyiséget. Root cause vizsgálat szükséges.
- [!] **EMN leftover** — close_positions 108→72 adjusted, MOC 72, de 36 share mégis nyitva. Az SL 36 share-t zárt (2×18), a MOC 72-t próbált zárni, de úgy tűnik csak 36+18=54 zárt MOC-on az EOD reportban. 
- [x] CENX TP1 + TRAIL! Az első igazi TP1→trail siker. Entry $61.01 → TP1 $62.41 (+$15.40) → Trail $62.36 (+$45.90). Összesen +$61.30.
- [!] PNW is nyerő (+$66.40) — utility defenzív stratégia továbbra is működik
- [!] DBRG nem jelenik meg az EOD-ban — valószínűleg unfilled? SL $15.34 vs entry $15.42, $0.08 távolság

## Holnap Akciólista
1. **NUKE: CNX 123sh + EMN 36sh + CENX 23sh** — piaci nyitás előtt
2. **Close_positions qty kalkuláció bug** — CENX "fully closed" de 23sh leftover, EMN is hibásan adjusztálva. CC task szükséges.
3. **DBRG vizsgálat** — unfilled? SL $0.08 távolság potenciálisan probléma

## Megjegyzések
Végre szinte breakeven nap (-$8.96)! A hatnapos nagy veszteségsorozat megtört. **CENX TP1→Trail az első igazi siker az új 0.75×ATR TP1-gyel:** entry $61.01, TP1 hit $62.41, trail exit $62.36, összesen +$61.30. PNW utility is nyerő (+$66.40). VIX jelentősen csökkent (29.18→24.25), a piac enyhül. De a leftover probléma aggasztó: EMN 36sh + CENX 23sh nyitva maradt a close_positions hibás qty kalkulációja miatt. A close_positions.py `get_net_open_qty` logikáját felül kell vizsgálni — ez ismétlődő probléma.
