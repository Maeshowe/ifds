# IFDS Daily Review — 2026-09-10 (csütörtök, Day 80/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ Az IBKR MCP connector ebben a sessionben nem érhető el — bróker-kereszt-ellenőrzés **kimaradt**.
> Helyette: Mini `reconcile_state` **silent OK**, kanonikus `pending_exits`, Polygon záró markok.

## 1. 🔴 ELSŐ HELYEN: a `cum_30d` holnap a leállítási küszöb ALÁ kerülhet — az aritmetika

**A `cum_30d` a pre-reg §3 EGYIK LEÁLLÍTÁSI FELTÉTELE** („30 napi kumulatív < −3,0%", bármelyik
trigger elég). **Ma −2,67%** (a küszöbtől 0,33 pp = **$329,55**) — a valaha volt **második
legszorosabb** állás (a legszorosabb: 09-01, 0,23 pp).

**A holnapi ablak-gördülés MECHANIKUSAN KEDVEZŐTLEN:**

| Lépés | Összeg |
|---|---|
| Jelenlegi 30-napos ablak (07-29 → 09-10) | **−$2 670,45** |
| **Holnap kigördül a 2026-07-29-i nap** | **+$359,68** *(pozitív nap távozik)* |
| Új bázis a mai nap nélkül | **−$3 030,13** |
| **A −3,0% küszöb** | −$3 000,00 |

➡️ **A küszöb akkor NEM sérül, ha a mai (09-11) realizált X > +$30,13.**

**A mai flagelt exitek implikált várakozása a 09-10-i markokon:**

| Idő | Ticker | Típus | `várt` |
|---|---|---|---|
| 15:30 | YPF | TP1 (102→51) | **+$95,88** |
| 21:40 | **NWS** | TIME_STOP | **−$381,50** |
| **Σ** | | | **≈ −$285,62** |

➡️ Ezeken a markokon az új érték **≈ −$3 315,75 = −3,32%** lenne, azaz **a küszöb alatt**.

⚠️ **Ez aritmetika, nem előrejelzés** — a tényleges érték a mai fillektől függ, és a becslés
az elmúlt napokban **$71–164-gyel** tévedett (mindkét irányban). **De a mozgástér szűk: a
küszöb fölött maradáshoz pozitív napi realizált kell.**

📌 **A leállítás HUMAN-IN-THE-LOOP döntés, nem automatizmus** (pre-reg §4 + a monitor
tervezési elve: *„kizárólag jelez, nem cselekszik"*). **Tamás figyelmébe — ez az a helyzet,
amiért a STOP-monitor 2026-07-25-én megépült: hogy egy leállítási feltétel NE retroaktívan
derüljön ki.**

## 2. Fejléc
- **Realized net: −$521,28** (gross −$520,18, komm. $1,10) — **1 exit**.
- **Cumulative: −$2 859,20 (−2,86%)** — **új mélypont**.
- **Net Liq: $96 988,20** — napi Δ **−$312,49**.
- **Excess: +0,08%** (portfolio −0,52% vs SPY −0,60%). **MTM: +0,28%** — azonos előjel.
- **VIX 18,00 (+9,36%)** — **négy ülés alatt 14,38 → 18,00 (+25%)**, éles risk-off.
- **Nyitott pozíciók: 7**.

## 3. Exits (1) — az éra legnagyobb százalékos vesztesége
| Idő (UTC) | Ticker | Kanonikus típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 13:30:39 | **INTA** | **MENTAL_SL** | 102 | 42,91 → **37,80** | **−$521,28 (−11,91%)** | ≈ −$435 | −$86 |

🔴 **Az INTA −11,91% a swing-éra LEGNAGYOBB százalékos egy-tételes vesztesége**
(előző: FBIN −11,06%, 08-21). Dollárban a **2. legnagyobb** (−$521,28; rekord: USFD −$531,32, 07-23).
**A 7. MENTAL_SL**, és **két egymást követő napon a második** (MANH tegnap −$362,11).

📌 **A becslés harmadik napja ugyanabba az irányba téved**: a papír a tegnapi 38,64-es
zárómark alól **37,80-ra** esett. Risk-off tapén (VIX +9,36%) a mark-alapú extrapoláció
**rendszeresen alulbecsli a veszteséget** — $86, $93, $71 az elmúlt három exitnél.

## 4. ✅ A tegnapi §11.17-korrekció MÁSODSZOR IS IGAZOLÓDOTT
| Forrás | INTA |
|---|---|
| **Kanonikus** (`pending_exits`) | **MENTAL_SL** |
| `daily_metrics::exits` blokk | `sl: 1` ✓ |
| **`trades.details.exit_type`** | **„TP1"** ❌ |
| Fill | 13:30:39Z — a **normál 15:30-as ablak** |

**Pontosan a tegnap rögzített mechanizmus**: MENTAL_SL a 15:30-as ablakban → **„TP1"** címke.
Két egymást követő nap, két eset (MANH, INTA) — **a korrigált diagnózis megerősítve**.

⚠️ **A W37 heti riport TP1-metrikája így KÉT hamis TP1-találatot fog tartalmazni**
(MANH −$362,11, INTA −$521,28, Σ **−$883,39**). **A holnapi heti zárásban ezt kötelezően
korrigálom** a kanonikus `pending_exits` alapján.

## 5. Entries (2)
| Ticker | Qty | Planned→Fill | Slippage | Szektor |
|---|---|---|---|---|
| **ELVN** | 87 | 57,45 → **57,57** | +0,21% (adverz) | Healthcare |
| **OGE** | 232 | 46,92 → **47,37** | +0,96% (adverz) | **Utilities** (új) |

📌 **ELVN-visszalépés — OLCSÓBBAN.** Az ELVN-t **09-01-én** TIME_STOP-on zártuk **57,84**-en
(−$197,89), ma **57,57**-en visszavettük — **−0,47%-kal olcsóbban**.
**Visszalépés-sorozat n=9**: 6 drágább / **3 olcsóbb** (IMAX −0,29%, RCI −0,05%, **ELVN −0,47%**).
📌 **Mind a három olcsóbb eset az elmúlt két hétben történt** — a korábbi hat mind drágább volt.
**Leíró megfigyelés (G3)**, nem elemeztem az okát.

**Új szektor: Utilities** (OGE, 10,89%). A kitettség **42,41% → 53,99%**.

## 6. Nyitott pozíciók (7) — 09-10 záró mark
| Ticker | Szektor | Bázis | Záró | Unrealized |
|---|---|---|---|---|
| YPF | Energy | 54,18 | 56,06 | **+$191,76** |
| EQH | Fin. Services | 53,12 | 52,60 | −$70,36 |
| ELVN | Healthcare | 57,57 | 56,23 | −$116,58 |
| RCI | Comm. Services | 36,83 | 36,09 | −$162,80 |
| OGE | Utilities | 47,37 | 46,59 | −$180,96 |
| FBP | Fin. Services | 28,72 | 27,74 | −$324,68 |
| NWS | Comm. Services | 34,45 | 32,78 | **−$381,50** |
| **Σ** | | | | **−$1 045,12** |

A könyv **−$1 240,62 → −$1 045,12** (+$195,50) — a javulás **átsorolás** (az INTA realizálódott).
**1/7 pozitív** (csak a YPF). Az **NWS** a legrosszabb — **és ma este TIME_STOP-on zár** (§1).

## 7. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 14:30 Phase 4-6, 15:30 eod_flags (INTA MENTAL_SL),
  15:31 submit (ELVN, OGE), 22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó) — **ma mind tiszta**:
  `excess_10d_mean` **+0,01%** | `excess_15d_mean` −0,04% | `excess_10d_sum` +0,08% |
  `excess_15d_sum` −0,65% — **mind a küszöb felett**.
- 🔴 **`cum_30d` −1,88% → −2,67%** — **§1, a nap fő tétele.**

## 8. Anomáliák (új/változott/lezárt)
- **🔴 A `cum_30d` holnapi ablak-gördülése** (§1) — a legfontosabb nyitott tétel.
- **✅ A §11.17-korrekció megerősítve** (§4), második eset két nap alatt. **W37-korrekció kötelező.**
- **📌 Három olcsóbb visszalépés két hét alatt** (§5) — a sorozat első hat esete mind drágább
  volt. **Leíró (G3)**, ok nem vizsgálva.
- **📌 A becslés három egymást követő exitnél alulbecsülte a veszteséget** (§3) — a risk-off
  tape (VIX +25% négy ülés alatt) konzisztens magyarázat, de **nem verifikált mechanizmus**.
- **✅ VÁLTOZATLAN**: `swing_state.exits_today` félrenevezés (ma `{TIME_STOP:1, TP1:1}` ≡ a **mai**
  NWS/YPF flagek), `commission_total` csak exit-láb, `entry_price=planned`, `reconcile` csak
  ticker-halmaz, **szektor-cap monitorozási rés (§11.18)**, **TP1 utáni max_hold-túlfutás
  (09-04 §7)**, **FileVault**, **`docs/analysis/` sync-rés**, **§5.1/§5.2 döntések**.

## 9. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **MENTAL_SL** — **n=7** (+INTA −$521,28); két egymást követő napon kettő.
- **TP1-ciklusok (teljesen lezárt)** — n=6, mind pozitív, Σ +$850,84. Ma nem bővült.
- **Pozitív realizált nap** — 27/72 (ma nem).
- **Visszalépés exit után** — **n=9**: 6 drágább / **3 olcsóbb** (mind a három az elmúlt 2 hétben).
- **Next-day MKT fill slippage** — CC-éra **n=47** (+ELVN +0,21%, +OGE +0,96%): **34 adverz /
  13 kedvező** (72,3%). Teljes éra: n=73, 50 adverz (68,5%).
- **Kitettség** — **53,99%** (42,41%-ról); új szektor: Utilities.
- **VIX** — 14,38 (09-04) → **18,00** (+25% négy ülés alatt).
- **Rally/risk-off aszimmetria** — eső nap, realized szerint +0,08% felülteljesítés.
  Sorozat: 13 rally-lemaradás vs **15** eső-napi felülteljesítés.
- **TP-hit / pozitív-exit**: **0/1**. **Várt-vs-tény**: **−$86**.

## 10. Ma (péntek, 09-11) — várt + feltevés *(nagyságrend, nem előrejelzés)*
| Idő | Ticker | Típus | Qty | Bázis / 09-10 záró | `várt` |
|---|---|---|---|---|---|
| 15:30 | **YPF** | **TP1** (102→51) | 51 | 54,18 / 56,06 | **+$95,88** |
| 21:40 | **NWS** | TIME_STOP | 228 | 34,45 / 32,78 | **−$381,50** |
| **Σ** | | | | | **≈ −$285,62** |

- **Fókuszlista**: (1) **a `cum_30d` (§1)** — a nap első és legfontosabb száma;
  (2) a két exit; (3) a **W37 heti zárás** — **a TP1-metrika kötelező korrekciójával** (§4);
  (4) a −$1 045-ös könyv (1/7 pozitív); (5) a VIX (18,00).

## 11. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás.
**A kapuig 8 kereskedési nap.**

## 12. A nap egy mondatban
Az **INTA MENTAL_SL −$521,28-cal (−11,91%, az éra legnagyobb százalékos vesztesége)** új
kumulatív mélypontra vitte a könyvet (**−$2 859,20**) — miközben másodszor is igazolta a tegnapi
`exit_type`-korrekciót (MENTAL_SL a 15:30-as ablakban → „TP1") —, de a nap **valódi tétje a
holnapi ablak-gördülés**: a `cum_30d` **−2,67%**, és mivel holnap egy **+$359,68-as pozitív nap
gördül ki**, a pre-reg **−3,0%-os leállítási küszöb** fölött maradáshoz **pozitív mai realizált
kell (> +$30,13)** — a jelenlegi markok ezzel szemben **≈ −$286**-ot implikálnak.
