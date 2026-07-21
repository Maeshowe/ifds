# IFDS Daily Review — 2026-07-20 (hétfő, Day 43/63 NYSE-count)

> Executor: **CC** (Fázis A, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett; IBKR = végső igazságforrás. Day 63 előtt nincs jel-ítélet.

## 1. Fejléc
- **Day 43/63** (NYSE-count) — `daily_metrics::day_number=43`. ⚠️ `cumulative_trading_days=37` ≠ 43 — a gap az outage + korábbi eltérés (07-07 §6.2, nyitva).
- **Realized net: −$438,55** (3 exit, komm. $3,31) — `daily_metrics::pnl` + `cumulative_pnl` 07-20 history-sor. **Cumulative: $52,79 (+0,053%)** — a pivot (05-18) óta lényegében breakeven közelébe esett vissza (491,34 → 52,79).
- **Net Liq: $99 901,31** — IBKR `get_account_summary`; **napi Δ: −$816,15** (07-17 close $100 717,46 → ma). Először **$100k alatt** a pivot óta.
- **Excess: −0,27%** — `daily_metrics::excess_return` (portfolio −0,44% vs SPY −0,16%). ⚠️ szemantika: realized+mark-alapú napi hozam; **flat indexnapon** (SPY −0,16%) a könyv alulteljesített (idioszinkratikus, lásd §6).
- **Nyitott pozíciók: 4** (`swing_positions.json` ≡ IBKR 4 ✓): USFD, GTES, SLGN(60), JAZZ.

## 2. Exits (3) — típus forrása: `state/pending_exits/2026-07-20.json`; realized: IBKR `get_account_trades`
| Idő (CEST) | Ticker | Típus | Qty | Entry(IBKR)→Fill | Broker realized | 07-17 §8 várt | Eltérés |
|---|---|---|---|---|---|---|---|
| 15:30 | SLGN | TP1 (részleges) | 60 | 44,71 → 47,05 | **+$139,43** | ~+$150 | −$10,57 |
| 21:40 | PFGC | TIME_STOP (MOC) | 62 | 115,27 → 109,18 | **−$378,49** | ~−$217 | **−$161,49** |
| 21:40 | BIRK | TIME_STOP (MOC) | 84 | 45,14 → 42,78 | **−$199,49** | ~−$66 | **−$133,49** |

**Összeg: −$438,55** (= `cumulative` Δ ✓). Várt ~−$133 → tény −$438,55 (**Δ −$305**), döntően a PFGC/BIRK túllövés — lásd §6/P2.

## 3. Entries (1) — forrás: `pt_events` 15:31 + IBKR `get_account_trades`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| JAZZ | Healthcare | 23 | 247,53 → **250,00** (NASDAQ) | **+1,0%** (gap up) | 232,86 / 258,53 / 269,53 |

Komisszió $1,00. A stop/TP a *tervezett* 247,53-ból számítva (lásd §6/P3).

## 4. Nyitott pozíciók (4) — `swing_positions.json` + IBKR mark/unrealized
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| USFD | 4 | 95,03 | −$423,80 | **−0,05%** ⚠️ | HOLD (lásd §6/P2) |
| GTES | 1 | 25,70 | −$191,12 | 2,14% | HOLD |
| SLGN | 6 | 46,07 | +$81,70 | 10,77% | **TIME_STOP** (holnap 21:40; trail_sl 44,60) |
| JAZZ | 0 | 243,47 | −$151,19 | 4,36% | HOLD |

**Total unrealized: −$684,41** (IBKR). Gross position value $18 676,77 (`get_account_summary`).

## 5. Ops-checklist
- ✓ **Reconcile 4/4 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Teljes cron-lánc lefutott**: 15:30 close (SLGN TP1), 15:31 submit (JAZZ), 21:40 time_stop (PFGC/BIRK MOC), 22:00 eod_eval, 22:10 metrics, 22:20 review_data.
- ✓ **Nincs ERROR**; a 20:11 `eod::leftover_warning` (4) normál EOD-jelzés.
- ⚠️ **Telegram-render** nem verifikálva ebben a sessionben (nem forrás; v6 §5) — n/a.

## 6. Anomáliák (új/változott/lezárt)
- **P2 — USFD stop-breach vs HOLD (forrás-konfliktus, holnap ellenőrzendő).** IBKR mark **95,03** < stop **95,08** (buffer −0,05%), a `next_action` mégis **HOLD** — nincs MENTAL_SL flag (`swing_positions` + `review_data`). v6 §2 (forrás-ütközés → mindkettő + ⚠️): a 22:00 `eod_eval` a **Polygon napi close-t** használja (valószínűleg ≥95,08 az evalkor), az IBKR-last (22:36) 95,03. Hipotézis: adatforrás-timing eltérés, nem logikai hiba. **Ellenőrzés holnap**: ha USFD a 95,08 alatt marad az eval-időben, a MENTAL_SL-nek fire-olnia kell — ha nem, P1-re emelendő. Gazda: megfigyelés → holnapi watch.
- **P2 — outage-késleltetett exit ára (számszerűsítve).** PFGC/BIRK (day 7, max_hold=5; a 07-15/16 outage miatt 2 nap késés) ma **materiálisan rosszabbul** zárt, mint a 07-17-i mark: PFGC −$378,49 (várt −217, Δ −161), BIRK −$199,49 (várt −66, Δ −133); mindkettő tovább esett a késés alatt. A ~**−$295 többletveszteség** a 07-17-mark-várakozáshoz képest **outage-kontaminációs költség** (2 nap plusz piaci kitettség). Gazda: **Day 63-input** (kizárás az edge-mintából, §11.10). Nem jel a stratégiáról.
- **P3 (carry) — `entry_price` = tervezett, nem fill** (07-17 §6 folytatása): JAZZ planned 247,53 vs IBKR fill **250,00** (gap up); a stop/TP a tervezettből. Ugyanaz az osztály. Gazda: Day 63-input.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage**: ma JAZZ **+1,0%** (gap up); előző: GTES −1,0% (07-17). 2 adatpont, előjel-vegyes.
- **Self-reentry**: ma n=0.
- **Major risk-off excess**: ma **nem** risk-off nap (SPY −0,16% < küszöb) — nem adódik a sorozathoz; megjegyzés: a könyv flat indexnapon −0,27% excess (idioszinkratikus).
- **TP-hit / pozitív-exit**: ma 3 exit, **1 pozitív** (SLGN TP1 +$139,43); a részleges TP1 után a maradó 60 SLGN trailre váltott (trail_sl 44,60), majd TIME_STOP-flag holnapra.
- **Daily-eval fordulat**: SLGN TP1(flag 07-17)→végrehajtva→maradék TIME_STOP-flag (1 fordulat).

## 8. Holnap (kedd, 07-21) — várt + feltevés
- **SLGN TIME_STOP** 21:40 MOC (maradó 60) — `várt` ≈ **+$82** (feltevés: holnapi close ≈ mai mark 46,07; IBKR-bázis 44,71).
- **USFD watch** (§6/P2): ha az eval-időben < 95,08, MENTAL_SL várható; ha marad HOLD a stop alatt → P1.
- **Fókuszlista**: (1) USFD stop-breach feloldása; (2) SLGN végső exit; (3) GTES (−191) és JAZZ (−151) első teljes napja, mindkettő víz alatt; (4) cumulative $52,79 — breakeven-közel, a következő napok iránya érzékeny; (5) Mini-stabilitás (UPS megrendelve, még nem üzemel).

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** Freeze él Day 63-ig.

## 10. A nap egy mondatban
Flat indexnap (SPY −0,16%), de −$438,55 realizált, mert az outage-késleltetett PFGC/BIRK TIME_STOP a pénteki marknál mélyebben zárt; a cumulative 491→53-ra esett, a NetLiq először $100k alá.
