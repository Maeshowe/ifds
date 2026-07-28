# IFDS Daily Review — 2026-07-27 (hétfő, Day 48/63 NYSE-count)

> Executor: **CC** (CC-only, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett;
> IBKR MCP kereszt-ellenőrzés lefutott. Day 63 előtt nincs jel-ítélet.

## 1. Fejléc
- **Day 48/63** (NYSE-count) — `daily_metrics::day_number=48`. ⚠️ `cumulative_trading_days=41` (gap: outage-napok).
- **Realized net: −$29,31** (1 exit, komm. $1,14) — `cumulative_pnl` 07-27 sor. **Cumulative: −$453,01 (−0,453%)**.
- **Net Liq: $100 609,10** — `state/daily_equity.json["2026-07-27"]`; **napi Δ: +$183,21** (07-24: $100 425,89).
  *(IBKR `get_account_summary` 07-28 pre-market: $100 625,32 — a hétvégi/overnight különbség, nem forrás-konfliktus.)*
- **Excess: −0,05%** — `daily_metrics::excess_return` (portfolio −0,03% vs SPY **+0,02%**). Gyakorlatilag flat nap (VIX 18,85, +1,45%).
- **Nyitott pozíciók: 7** (`swing_positions` ≡ IBKR 7 ✓) — 5-ről nőtt a 3 mai belépővel.

## 2. Exits (1) — típus: `pending_exits`; realized: IBKR `get_account_trades`
| Idő (CEST) | Ticker | Típus | Qty | Entry(IBKR)→Exit | Broker realized | 07-24 §8 várt | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59 | GTES | TIME_STOP (MOC) | 194 | 26,685 → 26,54 | **−$29,31** | ~+$40 | **−$69** |

A GTES a day-5 max_hold-on zárt. Az eltérés oka: a pénteki mark (26,89) fölött becsültünk, a hétfői
MOC 26,54-en teljesült (−1,3% a hétvége/hétfő során). **Ez tiszta, nem-outage-kontaminált exit** —
az első ilyen a 3 késett exit után.

## 3. Entries (3) — `pt_events` 15:31 + `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| ROIV | Healthcare | 152 | 35,01 → **35,50** | **+1,40%** | 32,71 / 36,74 / 38,46 |
| WAB | Industrials | 21 | 302,50 → **302,75** | **+0,08%** | 285,94 / 314,92 / 327,34 |
| MLI | Industrials | 92 | 63,91 → **64,45** | **+0,84%** | 60,14 / 66,73 / 69,56 |

Átlag fill-slippage **+1,10%**, komm. $1,14 összesen. A ROIV két lábon telt (115 IEX + 37 NASDAQ, azonos ár).
**A legaktívabb belépő-nap** a swing-érában (3 új tétel; a napi limit `max_allowed=5`).

## 4. Nyitott pozíciók (7) — `swing_positions` + IBKR `get_account_positions`
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| JAZZ | **5** | 255,43 | +$123,89 | 8,84% | **TIME_STOP** (holnap 21:40) |
| PFGC | 4 | 114,30 | +$231,80 | 9,44% | **TP1** (holnap 15:30, részleges) |
| EQH | 4 | 48,59 | +$3,04 | 6,71% | HOLD |
| USFD | 2 | 99,29 | +$281,80 | 9,50% | HOLD |
| ROIV | 0 | 34,72 | −$119,56 | 5,79% | HOLD |
| WAB | 0 | 300,90 | −$39,85 | 4,97% | HOLD |
| MLI | 0 | 64,17 | −$26,76 | 6,28% | HOLD |

**Total unrealized: +$454,36** (IBKR) — a legmagasabb a swing-érában. Gross position value $41 955,50.
**Notional 28,92% → 41,25% equity** (a 3 belépővel); szektor-eloszlás: Industrials $12 232 / Consumer Defensive
$11 939 / Healthcare $11 015 / Financial Services $6 061 — mindegyik a 30%-os cap alatt.

## 5. Ops-checklist
- ✓ **Reconcile 7/7 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Teljes cron-lánc**: 15:31 submit (3 belépő), 21:40 time_stop (GTES MOC), 22:00 eod_eval (JAZZ TIME_STOP + PFGC TP1 flag), 22:10 metrics, 22:20 review_data.
- ✓ **Nincs ERROR**; a 20:11 `eod::leftover_warning` (7) normál.
- ✓ **`pt_events` tiszta** (9 sor, nincs teszt-szennyezés) — a `db95c13` fix tartja.
- ✓ **STOP-triggerek: ✓ nincs breach** (mind a pre-reg ablak kiértékelve) — `stop_trigger_monitor.py`, v6 §5 kötelező sor. *(Ez az első nap, amikor a monitor élesben fut.)*

## 6. Anomáliák (új/változott/lezárt)
- **Nincs új anomália.** A nap tiszta: minden cron lefutott, a reconcile néma, a fillek verifikáltak.
- **Változott — pozíció-koncentráció.** A notional egy nap alatt **28,92% → 41,25%** equity (3 új tétel).
  Nincs limit-sértés (`max_concurrent=12`, napi `max_allowed=5`, szektor-cap 30%), **de három szektor
  pontosan a `max_positions_per_sector=2` cap-en áll** (Industrials WAB+MLI, Healthcare JAZZ+ROIV,
  Consumer Defensive PFGC+USFD). Megfigyelés, nem kifogás — a JAZZ holnapi TIME_STOP-ja oldja a Healthcare-t.
- **Változott — self-reentry sorozat (n=2) állása:** mindkét max_hold-kényszerű visszalépés **erősen profitban**:
  PFGC **+$231,80** (holnap TP1-et vesz), USFD **+$281,80**. A round-trip-súrlódás (~−$74 / ~−$64)
  bőven visszakeresődött. Day 63-input marad (a megfigyelés a szabályról szól, nem a kimenetről).
- **Ismert, nyitott** (nem ismételve): entry_price=planned (§11.10), FileVault-gyökérok (Tamás-döntés).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=8** (+3 ma): GTES −1,00 / JAZZ +1,00 / PFGC +1,01 / EQH +0,95 /
  USFD −1,89 / **ROIV +1,40 / WAB +0,08 / MLI +0,84**. **|slippage| medián = 1,00% (100 bp)** — n=5→8 mellett
  **változatlan**; előjeles átlag **+0,30%** (adverz); **6 adverz / 2 kedvező**.
  *(Az FRL `cost_model.json` inputja; a spec v2 75 bp/oldal induló értéke a mért 100 bp mediánhoz képest konzervatív.)*
- **Self-reentry** — n=2, mindkettő nyitva és profitban (lásd §6).
- **Major risk-off excess**: ma nem risk-off (SPY +0,02%).
- **TP-hit / pozitív-exit**: ma 1 exit, **0 pozitív** (GTES −$29,31). PFGC TP1 holnap.
- **Outage-késleltetett exit** — n=3, **ma nem nőtt** (a GTES tiszta, időben végrehajtott exit).

## 8. Holnap (kedd, 07-28) — várt + feltevés
- **PFGC TP1** 15:30 MKT, részleges (50% ≈ 30 db) — `várt` ≈ **+$116** (feltevés: keddi ár ≈ hétfői mark 114,30; IBKR-bázis 110,437).
- **JAZZ TIME_STOP** 21:40 MOC (23) — `várt` ≈ **+$124** (feltevés: keddi close ≈ hétfői mark 255,43; IBKR-bázis 250,043).
- **Fókuszlista**: (1) a két exit várt-vs-tény; (2) a 3 friss belépő (ROIV −$120 a legmélyebb) első teljes napja;
  (3) notional 41,25% — a két exit után csökken; (4) slippage-sorozat n=8 → 100 bp stabil; (5) kapu-döntések
  D1/D2/D3 (~15 trading nap a Day 63-ig).

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** A tegnapi `e155c53` (scoring_validation előjel-fix + G5 éra-bontás)
és `ad4b28b` (STOP-monitor) **read-only elemző-tooling**, production-útvonalat nem érint. Freeze él Day 63-ig.

## 10. A nap egy mondatban
Flat nap (SPY +0,02%) a swing-éra legaktívabb belépő-napjával (ROIV/WAB/MLI, +1,10% átlag-slippage); a GTES
max_hold-on −$29,31-gyel zárt (az első tiszta, nem-outage-késett exit), a nyitott könyv +$454 unrealizeddel a
legmagasabb, és holnap két exit esedékes (PFGC TP1, JAZZ TIME_STOP).
