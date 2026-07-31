# IFDS Daily Review — 2026-07-31 (péntek, Day 52/63 NYSE-count)

> Executor: **CC** (CC-only, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett;
> IBKR MCP kereszt-ellenőrzés lefutott. Day 63 előtt nincs jel-ítélet.

## 1. Fejléc
- **Day 52/63** (NYSE-count). ⚠️ `cumulative_trading_days=45` (gap: outage-napok).
- **Realized net: +$176,52** (1 exit, komm. $1,06). **Cumulative: +$347,45 (+0,347%)** — pozitívban, a hét
  során **−$188,75 → +$347,45**.
- **Net Liq: $100 166,14** — `daily_equity.json` ≡ IBKR `get_account_summary` ✓; **napi Δ: −$293,78**
  (07-30: $100 459,92). ⚠️ **Másodszor a héten: pozitív realizált mellett csökkenő NetLiq** — a nyitott
  könyv romlása nagyobb (lásd §4).
- **Excess: −0,54%** — `daily_metrics::excess_return` (portfolio +0,18% vs SPY **+0,72%**). Emelkedő tape
  (VIX 15,85, −7,26% — a hét legalacsonyabb szintje).
- **Nyitott pozíciók: 7** (`swing_positions` ≡ IBKR 7 ✓).

## 2. Exits (1) — típus: `pending_exits`; realized: `daily_metrics::trades::details` (broker-lánc)
| Idő (CEST) | Ticker | Típus | Qty | Entry→Fill | Broker realized | 07-30 §8 várt | Eltérés |
|---|---|---|---|---|---|---|---|
| 21:59 | USFD | TIME_STOP (MOC) | 28 | 94,30 → 100,60 | **+$176,52** (+6,69%) | ~+$176 | **+$0,52** |

**A sorozat legpontosabb becslése** (0,3% eltérés). A day-5 max_hold zárta a maradék felet.

## 3. Entries (2) — `pt_events` 15:31 + `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| SAIC | Technology | 45 | 115,72 → **116,78** | **+0,92%** | 108,03 / 121,49 / 127,25 |
| TTWO | Communication Svcs | 28 | 247,43 → **245,41** | **−0,82%** | 234,99 / 256,76 / 266,09 |

Átlag +0,25% (a két print ellentétes irányú), komm. $1,06. **Két új szektor** a könyvben.

## 4. Nyitott pozíciók (7)
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| MLI | 4 | 66,41 | +$89,66 | 9,44% | HOLD |
| SAIC | 0 | 117,13 | +$14,75 | 7,77% | HOLD |
| DE | 1 | 593,06 | −$54,30 | 2,75% | HOLD |
| TTWO | 0 | 242,91 | −$71,00 | 3,26% | HOLD |
| ROIV | 4 | 33,91 | −$242,68 | 3,54% | HOLD |
| WAB | 4 | 290,86 | −$250,69 | 1,69% ⚠️ | HOLD |
| CTAS | 2 | 205,08 | **−$275,40** | **1,20%** ⚠️ | HOLD |

**Total unrealized: −$789,66** (−$380,29-ról) — **a swing-éra mélypontja**. **7-ből 5 negatív.**
Gross position value $38 072,27; notional **29,43% → 38,88%** equity. **Hétfőre nincs exit-flag.**

## 5. Ops-checklist
- ✓ **Reconcile 7/7 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Cron-lánc**: 15:31 submit (SAIC, TTWO), 21:40 time_stop (USFD MOC), 22:00 eod_eval (0 új flag),
  22:10 metrics, 22:20 review_data.
- ✓ **Nincs ERROR**; a 20:11 `eod::leftover_warning` (7) normál.
- ✓ **`pt_events` tiszta** (7 sor).
- ✓ **STOP-triggerek: ✓ nincs breach** (mind a pre-reg ablak kiértékelve).
- ✓ **v2 enrichment sink**: `226/123` ≡ scan-matrix **226/123** — pontos egyezés.

## 6. Anomáliák (új/változott/lezárt)
- **✅ LEZÁRVA — self-reentry sorozat (n=2), mindkettő teljesen mérhető.** Az USFD ma zárta a második lábat:
  a 07-23-i visszalépés (56 db @ 94,24) → TP1 07-29 (**+$169,24**) + TIME_STOP ma (**+$176,52**) =
  **+$345,76**; a kényszerű round-trip súrlódása ~**−$62** (exit 93,13 → re-entry 94,24).
  **Összesített kép (n=2, tényszerű, következtetés nélkül):**
  | Eset | Round-trip súrlódás | A visszalépett láb realizált eredménye |
  |---|---|---|
  | PFGC (07-20→07-21) | ~−$74 | **+$293,24** |
  | USFD (07-23) | ~−$62 | **+$345,76** |
  | **Σ** | **~−$136** | **+$639,00** |
  Mindkét esetben a visszalépett pozíció **nyereséges** lett. **n=2 — nem általánosítható**, Day 63-input.
- **⚠️ Változott — CTAS a legszűkebb (1,20%).** Második napja romlik (−$249,64 → −$275,40); a 07-30-i
  idioszinkratikus zuhanás nem fordult vissza. **WAB 1,69%** (−$250,69), szintén tartósan negatív.
  Mindkettő HOLD-on (a 22:00 eval a stop fölött látta). **Hétfői watch.**
- **⚠️ ÚJ megfigyelés — a könyv kettéválik.** A heti **+$771,15 realizált** a **régebbi** tételekből jött
  (PFGC/EQH/USFD/MLI/JAZZ, 07-20..07-27 belépők), miközben a **jelenlegi** könyv (CTAS/DE/ROIV/WAB/TTWO,
  07-27..07-31 belépők) **−$789,66 unrealizeddel** áll. Tényszerű rögzítés, **nem** ok-okozati állítás —
  a magyarázat lehet piaci timing, szelekció vagy zaj; Day 63 előtt nem ítélünk.
- **Ismert, nyitott** (nem ismételve): entry_price=planned (§11.10), FileVault (Tamás-döntés).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=12** (+SAIC +0,92%, TTWO −0,82%). **|medián| = 0,98%** (n=10-nél
  1,00% volt — a két mai print enyhén lehúzta). Előjeles átlag **+0,04%** (7 adverz / 5 kedvező).
  A kép stabil: **szórás ~100 bp, torzítás ~0**. *(FRL `cost_model.json` input.)*
- **Self-reentry** — **n=2, mindkettő ZÁRT** (lásd §6). A sorozat lezárható vagy folytatható új eset esetén.
- **Major risk-off excess** — ma nem risk-off (SPY +0,72%).
- **TP-hit / pozitív-exit**: ma 1 exit, **1 pozitív** (USFD +6,69%). Heti: 8 exit, **7 pozitív** (87,5%).
- **Outage-késleltetett exit** — n=3, változatlan.
- **Várt-vs-tény pontosság**: ma **+$0,52 / +0,3%** — **a sorozat legpontosabb napja**.

## 8. Hétfő (08-03) — várt + feltevés
- **Nincs ütemezett exit-flag.** A legrégebbi tételek: MLI és ROIV és WAB (day 4) → **kedden érik a day-5
  max_holdot**, tehát hétfőn eval-fordulat várható rajtuk.
- **Fókuszlista**: (1) **CTAS 1,20%** és **WAB 1,69%** — a két legszűkebb buffer, mindkettő tartósan negatív;
  (2) a −$790 unrealized alakulása (a könyv mélypontja); (3) MLI/ROIV/WAB day-5 flag-ek kedden;
  (4) notional 38,88% — a hét legmagasabbja; (5) **kapu: Day 63 ~08-17** (freeze-feloldás + első leíró futás)
  — **11 trading nap**.

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** Freeze él Day 63-ig.

## 10. A nap egy mondatban
Az USFD max_hold-ja +$176,52-vel zárt (a sorozat legpontosabb becslése, +$0,52 eltérés) és lezárta a második
self-reentryt; két új belépő (SAIC, TTWO) mellett a nyitott könyv −$790-re mélyült, a CTAS 1,20%-os
stop-bufferrel a legszűkebb.

---

## Heti zárás — W31 (2026-07-27 → 07-31) — forrás: `docs/analysis/weekly/2026-W31.md`
5 trading nap, **outage nélkül** (az első teljes, zavartalan hét 06-22 óta).

| Nap | Realized | Equity (EOD) | Esemény |
|---|---|---|---|
| 07-27 (H) | −$29,31 | $100 609,10 | GTES TIME_STOP; 3 belépő (ROIV/WAB/MLI) |
| 07-28 (K) | **+$264,26** | $101 051,75 | JAZZ TIME_STOP + PFGC TP1 |
| 07-29 (Sze) | **+$359,68** | $100 455,17 | 4 exit; CTAS belépő; **cum. pozitívba fordult** |
| 07-30 (Cs) | $0,00 | $100 459,92 | DE belépő |
| 07-31 (P) | **+$176,52** | $100 166,14 | USFD TIME_STOP; SAIC+TTWO belépő |

- **Heti net: +$771,15** (gross $779,92, komm. $8,77) — **a swing-éra legjobb hete**
  (W28 −$311,36, W29 +$262,65, W30 −$915,04). Cumulative: **−$423,70 → +$347,45**.
- **Excess vs SPY: −0,34%** (portfolio +0,78% vs SPY +1,12%) — a realizált erős volt, de a **könyv
  mark-to-market alulteljesített** egy emelkedő héten.
- **Exit-bontás**: 8 exit (3 TP1, 5 MOC), **7 pozitív** (87,5%). TP1 avg +$100,60.
- ⚠️ **A NetLiq a héten CSÖKKENT** ($100 425,89 → $100 166,14 = **−$259,75**) a **+$771,15 realizált
  mellett** — a nyitott könyv unrealizedje +$283-ról −$790-re fordult (~−$1 073 swing). Ez a hét
  legfontosabb ténye: **a realizált eredmény és az equity ellentétes irányba mozdult.**
- **Megfigyelés-sorozatok (heti)**: slippage n=8→12 (|medián| ~98 bp, torzítás ~0); self-reentry **n=2,
  mindkettő zárt** (+$639,00 a visszalépett lábakon, ~−$136 súrlódás mellett); risk-off excess +1 nap
  (07-29, +1,90%); outage-késett exit n=3 (változatlan).
