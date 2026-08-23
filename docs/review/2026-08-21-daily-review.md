# IFDS Daily Review — 2026-08-21 (péntek, Day 67/63) + **W34 heti zárás**

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett; IBKR MCP kereszt-ellenőrzés lefutott.
> ⚠️ **Outage-nap** — a 3. FileVault-osztályú kiesés, ÚJ hibaalakkal
> (`docs/handoff/2026-08-21-outage-recovery.md`, 04-risks §11.16).

## 1. Fejléc
- **Realized net: −$794,39** (gross −$790,03, komm. $4,36) — **4 exit**.
- **Cumulative: −$1 532,57 (−1,53%)** — a swing-éra mélypontja, egy nap alatt **−$794**.
- **Net Liq: $98 974,06** — napi Δ **+$344,92**. ⚠️ **A NetLiq EMELKEDETT** egy −$794-es
  realizált napon: a veszteségek **már be voltak árazva** a nyitott könyvbe, az exit csak
  **realizálta** őket (§6).
- **Excess: −1,20%** (portfolio −0,79% vs SPY +0,41%). **MTM: −0,06%** →
  **1,14 pp rés, a swing-éra 2. legnagyobbja** (rekord: 1,20 pp, 06-10). Azonos előjel.
- **VIX 15,21 (−5,00%)**, SPY **+0,41%** — risk-on nap.
- **Nyitott pozíciók: 6** (`reconcile_state`: *„Reconciliation OK — state and IBKR match"* ✓).

## 2. Exits (4) — mind a négy végrehajtva
| Idő (UTC) | Ticker | Típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 15:51 | **DLB** | **TP1** (94→47) | 47 | 61,98 → **65,27** | **+$154,47** (+5,30%) | ≈ +$105 | **+$49** |
| 15:51 | **EQH** | **MENTAL_SL** | 102 | 53,04 → **49,40** | **−$371,36** (−6,86%) | ≈ −$481 | **+$110** |
| 19:59 | SN | TIME_STOP | 24 | 187,69 → 180,93 | −$162,17 (−3,60%) | ≈ −$184 | +$22 |
| 19:59 | **FBIN** | TIME_STOP | 75 | 50,09 → **44,55** | **−$415,33** (−11,06%) | ≈ −$380 | −$35 |
| **Σ** | | | | | **−$794,39** | ≈ −$940 | **+$146** |

- **Az FBIN −11,06% a swing-éra legnagyobb egy-tételes százalékos vesztesége.**
- A **DLB TP1** a self-reentry-ciklus **első pozitív realizálása** — a 08-19-i −$79,22 súrlódás
  után **+$154,47**. A maradék 47 db `trail_sl` 63,425-en fut (`tp1_hit: true`).
- A két 15:51-es exit **outage miatt 2h21m-mel késett** (a 15:30-as cron nem futott, kézzel
  pótolva). **Mindkét késés kedvezett** (+$110 / +$49) — de a §5 elv szerint ez **nem
  releváns**: a probléma a végrehajtás időpontja, nem az irány (§6).

**Bróker-verifikáció**: mind a 4 fill megerősítve (`get_account_trades`), a `pending_exits`
mind a 4 sora `processed: true`, `reconcile_state` silent OK.

## 3. Entries (0)
**Nem volt belépő** — a 14:30-as Phase 4-6 és a 15:31-es submit az outage miatt nem futott.
`qualified_above_threshold: 0`, `top_3_scores: []` — nincs mai jelölt-lista. **Tudatos döntés
volt nem pótolni**: a swing-architektúra következő-napi MKT-open belépőre épül, egy 4 órával
a nyitás utáni, elavult terv szerinti belépő spec-en kívüli lett volna.

## 4. Nyitott pozíciók (6) — 08-21 záró mark
| Ticker | Bázis | Záró | Unrealized |
|---|---|---|---|
| DLB (TP1 után) | 61,96 | 65,27 | **+$155,54** |
| PSO | 16,08 | 16,28 | **+$108,65** |
| IMAX | 52,76 | 52,74 | −$1,88 |
| FMS | 23,69 | 23,43 | −$73,44 |
| ZBRA | 379,73 | 368,51 | −$112,20 |
| BANC | 19,77 | 18,64 | −$302,63 |
| **Σ** | | | **−$225,96** |

A könyv **−$1 405,50 → −$225,96**. ⚠️ **Ez döntően NEM javulás, hanem átsorolás**: a négy
kilépett tétel unrealizedje (≈ −$950) **realizálttá** vált. A maradó 6-ból **2 pozitív**,
és a `total_notional` **48,32% → 31,93%** (a kitettség-ugrás lecsengett).

## 5. Ops-checklist
- 🔴 **Az outage miatt kiesett**: 10:10 monitor, **14:30 Phase 4-6**, 15:25 gateway-check,
  **15:30 eod_flags exit**, **15:31 submit**, 15:45 heartbeat. Részletek: §6 + a handoff.
- ✓ **Helyreállítva 17:35–17:51**: cron újraindult (konzol-login), Gateway feléledt
  (`Gateway OK`), a két elmaradt exit **kézzel pótolva** (Tamás engedélyével).
- ✓ **A 21:40-es lánc és a 22:00–22:45-ös eod-lánc normálisan lefutott** — van
  `daily_metrics/2026-08-21.json`, `pending_exits` feldolgozva, `review_data` generálva.
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó): `excess_10d_mean` **−0,05%** vs −1,0% →
  **nincs halt**. `excess_15d_mean` −0,29%. `excess_15d_sum` **−4,28%** (BREACH, megfigyelés).
- ⚠️ **`cum_30d` −2,15%** vs a **−3,0%**-os leállítási küszöb — **ez a legközelebbi állás,
  amit bármely trigger valaha elért** (a távolság 0,85 pp). Múlt héten −1,28% volt.
  **Nem trigger, de a jövő heti fókusz első pontja.**

## 6. Anomáliák (új/változott/lezárt)
- **🔴 P1 (ÚJ, KAPU-RELEVÁNS) — a §5.1 outage-detektálás nem tudja kifejezni a RÉSZLEGES kiesést.**
  A `gate_sample.verify_outage_days()` kritériuma: *hiányzó `daily_metrics` fájl*. **Ma van
  ilyen fájl** (a helyreállt cron lefuttatta az eod-láncot), tehát a guard **némán átengedi** —
  holott a nap **érdemben csonka volt**: nem futott a Phase 4-6, **nincs jelölt-lista**
  (`qualified_above_threshold: 0`), **0 belépő**, és két exit **2h21m-et késett**.
  → **A binárisan „van/nincs adat" kritérium elégtelen.** Ez **Tamás-döntést** kíván
  (mi számít outage-napnak?), és a döntés `gate_sample.py`-módosítást + **ÚJ PINT** von maga
  után a §5.6 szabálya szerint (jelenlegi pin: **`68fc00e`**).
- **🔴 P1 (ÚJ, KAPU-RELEVÁNS) — §5.2 jelöltek: EQH + DLB.** Mindkettő **outage okozta
  késéssel** (2h21m) hajtódott végre. Az eddigi §5.2 esetek **nap-léptékű** csúszások voltak;
  ez **napon belüli**. **Beletartozik-e?** Az elv szerint igen (a végrehajtás nem a stratégia
  szándéka szerinti időpontban történt), de a küszöb sosem lett definiálva.
  ⚠️ **A DLB még nem zárt pozíció** (47 db nyitva) — pozíció-szinten csak a teljes lezárás után
  kerül a mintába. **Az EQH viszont lezárt** → a döntés azonnal hat a kapu-mintára.
- **🟡 P2 (ÚJ, MÉRT KÖVETKEZMÉNY) — az ismert `exit_type` defekt elrontja a heti TP1-metrikát.**
  A `trades.details.exit_type` a DLB TP1-et **„MOC"**-ként, az EQH MENTAL_SL-t szintén
  **„MOC"**-ként rögzítette. Következmény a W34 riportban: **„TP1 hits: 0/6 (0%)", „TP1 avg
  profit: $+0.00", „R:R realized: 1:0.00"** — miközben a kanonikus `pending_exits` szerint
  **volt** TP1, **+$154,47**-tel. A riport **önmagával is ellentmond** (az „Exit Breakdown"
  szekció `TP1 | N=1`-et ír, mert az a `daily_metrics::exits` blokkból jön — az helyes).
  ✅ **A kaput NEM érinti**: a `signal_attribution` 2. invariánsa szerint az `exit_type`
  **kizárólag** a `pending_exits`-ből jön.
- **🟡 P2 (ÚJ) — a `reconcile_state.py` csak TICKER-HALMAZT hasonlít, mennyiséget nem.**
  A log: *„State tickers: [...] / IBKR tickers: [...] / Reconciliation OK"*. Egy **darabszám-eltérés
  (pl. részleges TP1 után) így észrevétlen maradna.** Ma nem volt eltérés, de a DLB épp ilyen
  részleges tétel. Javaslat: a reconcile hasonlítson `qty_remaining`-et is.
- **✅ KORREKCIÓ a péntek esti jelzésemhez.** Pénteken jeleztem, hogy a DLB a state-ben 94-en
  áll, míg a bróker 47-et tart. **Ez az én olvasási hibám volt**: a rekordban `qty: 94`
  (eredeti méret) **és** `qty_remaining: 47` (helyes) szerepel, `tp1_hit: true` — rossz
  mezőneveket kérdeztem le. **Nem volt divergencia**, a reconcile is OK-t adott.
- **📌 Error 10349 a végrehajtáskor.** Mindkét 15:51-es rendelés **első kísérlete visszavonódott**
  (`Order TIF was set to DAY based on order preset`), a **második kísérlet kitelt**. Nagy
  valószínűséggel a **frissen indított Gateway** artefaktja (order-preset / API-precaution
  visszaállás). Ma a retry megmentette; **a 21:40-es MOC-oknál nem ismétlődött**.
- **✅ VÁLTOZATLAN**: `entry_price=planned`, `uw_shadow` üresen ír (ma: `snapshot_path: null`,
  mert a pipeline nem futott), **FileVault** (a 3. előfordulás — most már csomagban sürgős),
  **`docs/analysis/` sync-rés** (kapu előtt zárandó).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **„Rés utáni visszalépés" — a sorozat LEZÁRULT: n=3, mind a három negatív.**
  JAZZ −$251,02 | GTES −$265,91 | **EQH −$371,36**. **3/3**, és a veszteség **monoton nő**.
  ⚠️ **n=3 — nem általánosítható** (G3). Kapu-input **nem** (G1); a **D6 SIM-napirend** viszont
  ezt is vizsgálhatja.
- **Self-reentry** — n=3. A **DLB** az első, amelynek **mindkét oldala mérve van**:
  −$79,22 súrlódás (08-19) → **+$154,47 TP1** (08-21), maradék 47 db nyitva.
- **Next-day MKT fill slippage** — CC-éra **n=28** változatlan (ma 0 belépő).
- **Outage-késleltetett exit** — **n=4 → 5** (esemény-szinten), ha az EQH/DLB beszámít (§6, döntés alatt).
- **„Stop-közeli"** — n=5, változatlan.
- **Rally/risk-off aszimmetria** — ma emelkedő nap, realized szerint **−1,20% lemaradás**.
  Sorozat: **8** rally-lemaradás vs 8 eső-napi felülteljesítés.
- **TP-hit / pozitív-exit**: **1/4** (DLB TP1). **Várt-vs-tény**: **+$146 kedvezőbb** Σ-ban —
  a hét **harmadik** napja, amikor a mark-alapú becslés $100+-t tévedett.

---

# W34 heti zárás (2026-08-17 – 08-21)

## Számok
| Mérőszám | Érték |
|---|---|
| **Net P&L** | **−$1 082,69** (gross −$1 071,77, komm. −$10,92) |
| Cumulative | **−$1 532,57 (−1,53%)** |
| Portfolio heti | −1,07% | 
| SPY heti | **−1,37%** |
| **Excess vs SPY** | **+0,30%** |
| **Nyerő napok** | **0 / 5** |
| Nyitott pozíciók (hét)| 6 (1,2/nap) |
| Zero-pozíciós nap | 1/5 | Low (<3) | 4/5 |
| Legrosszabb slippage | +1,39% (DLB, 08-19) |

## A hét karaktere (tényszerű)
- **Nulla nyerő nap öt közül** — a swing-éra egyik leggyengébb hete abszolút értékben
  (−$1 082,69), **miközben az excess POZITÍV (+0,30%)**, mert az SPY heti −1,37%-ot esett.
  ⚠️ **A két állítás nem mond ellent egymásnak**, de külön kell olvasni őket: a hét
  **abszolút** rossz volt és **relatíve** enyhén jobb az indexnél.
- **A veszteséget négy tétel vitte**: FBIN −$415, EQH −$371, JAZZ-utód SN −$162, valamint a
  hét eleji könyv-leértékelődés. Az **egyetlen pozitív realizálás a DLB TP1** (+$154,47).
- **Az outage a hét végét csonkolta**: pénteken 0 belépő, 2 késett exit. A heti
  „6 nyitott pozíció / 1,2 nap" szám tehát **lefelé torzított**.
- **A `cum_30d` −1,28% → −2,15%-ra romlott** — a leállítási küszöbtől (−3,0%) mért távolság
  **0,85 pp**, a valaha volt legkisebb. **Ez a jövő hét első számú megfigyelési tétele.**
- ⚠️ **A heti TP1-metrika HIBÁS** (0/6, $0,00, R:R 1:0.00) — lásd §6; a valóság 1 TP1, +$154,47.

## Következő hét
1. **`cum_30d`** alakulása (−2,15% vs −3,0%) — **D4 szerint a `mean`/`cum` az irányadó**, ez valódi trigger.
2. **Tamás-döntés × 2** (§6): a §5.1 részleges-outage kritérium és a §5.2 EQH/DLB besorolás.
   Mindkettő `gate_sample.py`-t és **új pint** érinthet a kapu (2026-09-22) előtt.
3. **FileVault** — 3. előfordulás; a `LaunchDaemon` + auto-login csomag most már a
   legnagyobb üzemviteli kockázat.
4. A **D6 SIM-napirend** indítása (prod fagyva; a revíziók SIM-ben).

## 9. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás;
a kézi exit-pótlás a meglévő `close_positions.py`-vel, Tamás explicit engedélyével történt.

## 10. A nap egy mondatban
Egy outage-tól megcsonkított napon mind a négy exit lefutott (kettő kézi pótlással, 2h21m
késéssel), **−$794,39-cel a swing-éra mélypontjára** víve a kumulatívat — miközben a **NetLiq
emelkedett** (+$345), mert a veszteségek már be voltak árazva —, a **„rés utáni visszalépés"
sorozat 3/3 negatívval lezárult**, és a `cum_30d` **−2,15%-ra** csúszott, minden eddiginél
közelebb a −3,0%-os leállítási küszöbhöz.
