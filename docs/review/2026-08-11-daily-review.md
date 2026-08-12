# IFDS Daily Review — 2026-08-11 (kedd, Day 59/63 NYSE-count)

> Executor: **CC** (CC-only, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett;
> IBKR MCP kereszt-ellenőrzés lefutott. Day 63 előtt nincs jel-ítélet.

## 1. Fejléc
- **Day 59/63** (NYSE-count). ⚠️ `cumulative_trading_days=51`.
- **Realized net: +$164,95** (1 exit, komm. $1,06). **Cumulative: +$195,74 (+0,196%)** — két nyereséges
  nap egymás után (08-10: +$110,77).
- **Net Liq: $100 163,53** — `daily_equity.json`; **napi Δ: −$259,61** (08-10: $100 423,14).
  ⚠️ **Ismét: pozitív realizált mellett csökkenő NetLiq** — a nyitott könyv romlása nagyobb (§4).
- **Excess: +0,49%** — `daily_metrics::excess_return` (portfolio **+0,17%** vs SPY **−0,32%**).
  Eső tape (VIX 15,32), a könyv **felülteljesített**.
- **Nyitott pozíciók: 7** (`swing_positions` ≡ IBKR 7 ✓, `reconcile::no_divergence`).

## 2. Exits (1) — típus: `state/pending_exits/` (KANONIKUS); realized: `daily_metrics::trades::details`
| Idő (CEST) | Ticker | Típus | Qty | Entry→Exit | Broker realized | 08-10 §8 várt | Eltérés |
|---|---|---|---|---|---|---|---|
| 15:30 | SAIC | **TP2** | 23 | 116,85 → 124,02 | **+$164,95** (+6,14%) | ~+$150…200 | **sávon belül ✓** |

> ⚠️ **Az ismert `exit_type` defekt ismét**: a `daily_metrics::trades::details` **`TP1`-et** ír, a
> `pending_exits` (kanonikus) **`TP2`**-t. Második élő megerősítés a 08-06-i után.

### 📌 A SAIC teljes ciklust zárt — a swing-architektúra mintapéldája
| Lépés | Dátum | Qty | Ár | Realizált |
|---|---|---|---|---|
| Belépő | 07-31 | 45 | 116,78 | — |
| **TP1** | 08-05 | 22 | 121,00 | **+$91,29** |
| **TP2** | 08-11 | 23 | 124,02 | **+$164,95** |
| **Σ** | 8 trading nap | **45** | | **+$256,24** |

**Ez a swing-éra 5. TP2-je** (39 TIME_STOP / 17 TP1 / 5 MENTAL_SL mellett) — és a pozíció **100%-ban,
kizárólag profit-célokon** zárult, max_hold vagy stop nélkül. **Az architektúra szándéka szerinti
kimenetel**; tényszerű rögzítés, n=1.

## 3. Entries (1) — `pt_events` 15:31 + `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| ADT | Industrials | **803** | 7,51 → **7,50** | **−0,13%** | 7,07 / 7,84 / 8,16 |

⚠️ **A 803 darabos méret NEM anomália**: notional **$6 026**, ami a szokásos sávban van
(DLB $5 805, STE $5 712, JAZZ $5 808, SSNC $5 363). A nagy darabszám az **alacsony árfolyamból**
($7,50) adódik — a sizing notional-alapú, nem darabszám-alapú. Ellenőrizve.

## 4. Nyitott pozíciók (7) — `swing_positions` + IBKR `get_account_positions`
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| VLTO | 4 | 97,97 | +$53,32 | 7,84% | HOLD |
| STE | 1 | 238,23 | +$4,52 | 6,25% | HOLD |
| DLB | 1 | 61,36 | −$37,66 | 5,36% | HOLD |
| ADT | 0 | 7,45 | −$44,17 | 5,10% | HOLD |
| GTES | 3 | 28,44 | −$147,06 | 6,15% | HOLD |
| SSNC | 4 | 79,85 | −$173,25 | 5,21% | HOLD |
| **JAZZ** | 4 | 247,98 | **−$353,44** | **0,74%** ⚠️ | HOLD |

**Total unrealized: −$697,74** (−$273,24-ról **jelentősen romlott**). Notional **34,52% → 37,89%**.
**Holnapra nincs exit-flag.**

## 5. Ops-checklist
- ✓ **Reconcile 7/7 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Teljes cron-lánc**: 10:10 monitor (tiszta), 15:30 close (SAIC TP2), 15:31 submit (ADT),
  **21:40 time_stop lefutott üresen** (`pt_close` log: *„No TIME_STOP flags — nothing to do"*),
  22:00 eod_eval (0 új flag), 22:10 metrics, 22:20 review_data.
- ✓ **Nincs ERROR**; a 20:11 `eod::leftover_warning` (7) normál.
- ✓ **`pt_events` tiszta** (7 sor).
- ⚠️ **STOP-triggerek** (D4: `mean` az irányadó): `excess_10d_mean` **−0,29%** vs −1,0% → **✓ nincs halt**
  (**javult** a −0,35%-ról). `sum` −2,94% (megfigyelés). **`cum_30d` −1,52%** — másodszor javult (−1,81% → −1,55% → −1,52%).
- ✓ **v2 enrichment sink**: `765/516` ≡ scan-matrix **765/516** — pontos egyezés.

## 6. Anomáliák (új/változott/lezárt)
- **⚠️ P2 (ÚJ) — JAZZ stop-buffer 0,74%, a könyv legmélyebb tétele.** A mark 247,98 a 246,15-ös stop
  fölött **1,83 dollárral**; az unrealized **−$353,44** (−6,1%), egy nap alatt **−$188** romlás
  (−$165,56 → −$353,44; a mark 256,52 → 247,98, **−3,3%**). A 22:00 eval **HOLD**-ot adott (a Polygon-close
  a szint fölött). **Holnapi watch**: ha a stop alá zár, MENTAL_SL várható. Ez a 4. „stop-közeli" eset
  (USFD 07-20 → visszapattant, ROIV 07-29 → visszapattant, CTAS 08-03 → visszapattant, majd 08-05 valódi).
  📌 **Kontextus**: a JAZZ **08-05-i belépő** (264,00) — a 07-28-i TIME_STOP-os kiszállás (+$156,34) után
  6 nap réssel visszavett tétel; jelenleg **−6,1%**-on áll.
- **📌 A SAIC teljes TP1→TP2 ciklusa** (§2) — az architektúra szándéka szerinti kimenetel, n=1.
- **📌 ADT méret ellenőrizve** (§3) — nem anomália, notional-alapú sizing alacsony árfolyamon.
- **Ismert, nyitott** (nem ismételve): `exit_type` mező hibás (2. élő megerősítés, §2),
  entry_price=planned (§11.10), **FileVault** (Tamás-döntés).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=19** (+ADT −0,13%, kedvező). **|medián| 0,91%**; előjeles átlag
  **+0,24%** (12 adverz / 7 kedvező). *(FRL `cost_model.json` input.)*
- **Self-reentry** — n=2, változatlan.
- **Outage-késleltetett exit** — n=4, változatlan.
- **Rally/risk-off aszimmetria** — ma eső nap (SPY −0,32%), a könyv **+0,17%** → excess **+0,49%**.
  A sorozat: **4 rally-lemaradás vs 5 risk-off/eső-napi felülteljesítés** (07-17, 07-23, 07-29, 08-05, ma).
  **Az aszimmetria konzisztens marad** — Day 63 előtt következtetés nincs.
- **TP-hit / pozitív-exit**: ma 1 exit, **1 pozitív** (SAIC TP2 +6,14%). A TP2-sorozat **n=5**.
- **Várt-vs-tény pontosság**: ma **sávon belül** (+$164,95 a becsült +$150…200-ban) — a becslés
  ezúttal sávot adott, nem pontértéket, és talált.

## 8. Holnap (szerda, 08-12) — várt + feltevés
- **Nincs ütemezett exit-flag** — hacsak a szerdai eval újat nem tesz.
- **Legvalószínűbb új flag**: a **JAZZ** (0,74% buffer) — ha a stop alá zár, MENTAL_SL.
  A `várt` ekkor ≈ **−$400** (a stop-szint közelében; a 08-06-i tapasztalat szerint a fill a stop
  fölött is telhet).
- **Fókuszlista**: (1) **JAZZ** — a nap egyetlen éles tétele; (2) az unrealized −$698 alakulása;
  (3) a `cum_30d` (−1,52%) javuló trendje; (4) a friss belépők (ADT, DLB, STE) beérése;
  (5) **kapu: Day 63 ~08-17 — 4 trading nap**.

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** Freeze él Day 63-ig.

## 10. A nap egy mondatban
A SAIC teljes TP1→TP2 ciklust zárt (+$256,24 a 45 darabos pozíción, az 5. TP2 a swing-érában), a
kumulatív +$195,74-re nőtt, de a nyitott könyv −$698-ra mélyült — döntően a JAZZ egynapos −$188-as
esése miatt, ami 0,74%-os stop-bufferrel a holnapi fő figyelnivaló.
