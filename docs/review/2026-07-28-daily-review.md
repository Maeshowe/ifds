# IFDS Daily Review — 2026-07-28 (kedd, Day 49/63 NYSE-count)

> Executor: **CC** (CC-only, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett.
> ⚠️ **IBKR MCP részleges**: a `get_account_positions` lefutott (pozíció-verifikáció ✓), de a
> `get_account_summary` és `get_account_trades` **hibázott** ("An error occurred", 2× újrapróbálva).
> A NetLiq a `daily_equity.json`-ból (Mini Gateway), a realized a `daily_metrics::trades::details`
> broker-láncból — mindkettő broker-eredetű. Day 63 előtt nincs jel-ítélet.

## 1. Fejléc
- **Day 49/63** (NYSE-count) — `daily_metrics::day_number`. ⚠️ `cumulative_trading_days=42` (gap: outage-napok).
- **Realized net: +$264,26** (2 exit, gross $266,47, komm. $2,21). **Cumulative: −$188,75 (−0,189%)** —
  a −$453,01-ról **javult**, a pivot óta a legkisebb negatív egyenleg a 07-21-i csúcs óta.
- **Net Liq: $101 051,75** — `daily_equity.json`; **napi Δ: +$442,65** (07-27: $100 609,10).
  **A swing-éra csúcsa** (marginálisan a 07-10-i $101 043,78 fölött).
- **Excess: +0,03%** — `daily_metrics::excess_return` (portfolio **+0,27%** vs SPY +0,24%). Enyhén emelkedő
  tape (VIX 18,11, −3,0%), a könyv **hajszállal felülteljesített**.
- **Nyitott pozíciók: 6** (`swing_positions` ≡ IBKR 6 ✓) — 7-ről csökkent a JAZZ teljes kiszállásával.

## 2. Exits (2) — típus: `pending_exits`; P&L: `daily_metrics::trades::details` (broker-lánc)
| Idő (CEST) | Ticker | Típus | Qty | Entry→Exit | Broker realized | 07-27 §8 várt | Eltérés |
|---|---|---|---|---|---|---|---|
| 15:30 | PFGC | TP1 (részleges) | 30 | 110,47 → 114,07 | **+$107,92** (+3,26%) | ~+$116 | −$8 |
| 21:59 | JAZZ | TIME_STOP (MOC) | 23 | 250,09 → 256,89 | **+$156,34** (+2,72%) | ~+$124 | **+$32** |

**Összeg +$264,26** (= a `cumulative` Δ ✓). **A várt-vs-tény eddigi legpontosabb napja**: várt ~+$240 →
tény +$264,26 (**+$24**, +10%). Mindkét exit pozitív — a JAZZ a day-5 max_hold-on, a PFGC a TP1-en.

## 3. Entries (0)
Nincs mai belépő (`new_entries=[]`; a submit `existing_skip`: ROIV/MLI/WAB). A slippage-sorozat n=8 marad.

## 4. Nyitott pozíciók (6) — `swing_positions` + IBKR `get_account_positions`
| Ticker | days_held | Mark | Unrealized | next_action (holnap) |
|---|---|---|---|---|
| USFD | 3 | 101,47 | **+$403,88** | **TP1** (15:30) |
| MLI | 1 | 66,50 | +$187,60 | **TP1** (15:30) |
| PFGC | 5 | 115,53 | +$152,80 | **TIME_STOP** (21:40, maradó 30) |
| EQH | 5 | 49,39 | +$103,84 | **TIME_STOP** (21:40) |
| WAB | 1 | 304,68 | +$39,59 | HOLD |
| ROIV | 1 | 33,84 | **−$253,32** | HOLD |

**Total unrealized: +$634,39** (IBKR) — **új swing-éra csúcs** (+$454,36 → +$634,39). Öt pozíció profitban,
egy (ROIV) mélyen víz alatt. Notional **41,25% → 32,27%** equity.

## 5. Ops-checklist
- ✓ **Reconcile 6/6 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Teljes cron-lánc**: 15:30 close (PFGC TP1), 15:31 submit (0 új), 21:40 time_stop (JAZZ MOC),
  22:00 eod_eval (**4 flag** holnapra), 22:10 metrics, 22:20 review_data.
- ✓ **Nincs ERROR**; a 20:11 `eod::leftover_warning` (6) normál.
- ✓ **`pt_events` tiszta** (12 sor, nincs teszt-szennyezés).
- ✓ **STOP-triggerek: ✓ nincs breach** (mind a pre-reg ablak kiértékelve) — `stop_trigger_monitor.py`.
- ✓ **v2 enrichment sink**: `n_rows=226 / n_scored=122` ≡ scan-matrix **226/122** — pontos egyezés.
  *(Az FRL-5 deploy-előfeltétel 2 szerinti napi ellenőrzés első éles futása.)*
- ⚠️ **IBKR MCP részleges kiesés** — `get_account_summary` és `get_account_trades` hibázott (lásd fejléc).
  Tényként rögzítve (v6 anti-halluc. #6); a pozíció-verifikáció és a broker-lánc lefedte a hiányt.

## 6. Anomáliák (új/változott/lezárt)
- **Nincs új anomália.** Tiszta nap: minden cron lefutott, reconcile néma, mindkét flag pontosan végrehajtva.
- **Változott — ROIV az egyetlen érdemi negatív.** −$253,32 unrealized (−4,7%) két nap alatt; a stop 32,71,
  a mark 33,84 → **stop-buffer 3,34%**, a könyv legszűkebbje. Megfigyelés, nem kifogás — a mental-stop eval
  (22:00) HOLD-ot adott, tehát a szint fölött van. **Holnapi watch.**
- **Változott — a PFGC self-reentry részben realizálódott.** A 07-21-i max_hold-kényszerű visszalépés ma
  **TP1-et vett +$107,92**-vel, és a maradó 30 db holnap TIME_STOP-on zár. **A round-trip ROI holnap lesz
  először teljesen mérhető** — a sorozat (n=2) első lezáruló esete.
- **Ismert, nyitott** (nem ismételve): entry_price=planned (§11.10), FileVault (Tamás-döntés).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=8, ma nem nőtt** (0 belépő). |medián| 100 bp, előjeles átlag +0,30%.
- **Self-reentry** — **n=2**: PFGC **részben realizált** (+$107,92 TP1; maradó 30 db holnap zár → ROI mérhető),
  USFD +$403,88 unrealized (holnap TP1). **Mindkettő holnap lép tovább.**
- **Major risk-off excess**: ma nem risk-off (SPY +0,24%).
- **TP-hit / pozitív-exit**: ma **2 exit, 2 pozitív** (100%) — PFGC TP1 +3,26%, JAZZ +2,72%.
  A TP1-sorozat bővül; holnap további 2 TP1 esedékes.
- **Outage-késleltetett exit** — n=3, változatlan (ma mindkét exit időben).
- **Várt-vs-tény pontosság** (a review-pipeline minőségmérője): ma **+$24 / +10%** — a sorozat eddigi legjobbja.

## 8. Holnap (szerda, 07-29) — várt + feltevés
**Négy exit-flag** (a swing-éra legsűrűbb exit-napja lenne):
- **USFD TP1** 15:30, részleges (~28 db) — `várt` ≈ **+$202** (feltevés: keddi mark 101,47; IBKR-bázis 94,258).
- **MLI TP1** 15:30, részleges (~46 db) — `várt` ≈ **+$94** (mark 66,50; bázis 64,461).
- **PFGC TIME_STOP** 21:40 MOC (maradó 30) — `várt` ≈ **+$153** (mark 115,53; bázis 110,437).
- **EQH TIME_STOP** 21:40 MOC (126) — `várt` ≈ **+$104** (mark 49,39; bázis 48,566).

Együtt `várt` ≈ **+$553** — ha teljesül, a **cumulative pozitívba fordulna** (−$188,75 → ~+$364).
⚠️ A becslés feltevése minden esetben „holnapi ár ≈ mai mark"; a TP1-eknél a részleges qty a `tp1_sell_pct=0.50`.

- **Fókuszlista**: (1) a négy exit várt-vs-tény; (2) **ROIV stop-buffer 3,34%** — a legszűkebb; (3) a PFGC
  self-reentry ROI-zárása; (4) a cumulative előjelváltása; (5) kapu-menetrend: Day 63 ~08-17 (freeze-feloldás).

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** A mai commitok (`98d5166`, `db64d46`) docs-only + task-archiválás;
az enrichment sink (§11.11) és a STOP-monitor read-only. Freeze él Day 63-ig.

## 10. A nap egy mondatban
Két pozitív exit (JAZZ max_hold +$156,34, PFGC TP1 +$107,92) a várt-vs-tény eddigi legpontosabb napján
(+10%); a NetLiq $101 051,75-tel swing-éra csúcsra, az unrealized +$634-re nőtt, és holnap négy exit-flag
áll — ha teljesülnek, a kumulatív pozitívba fordul.
