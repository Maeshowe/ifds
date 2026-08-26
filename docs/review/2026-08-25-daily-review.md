# IFDS Daily Review — 2026-08-25 (kedd, Day 69/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.

## 1. Fejléc
- **Realized net: −$311,09** (gross −$305,98, komm. $5,11) — **4 exit, mind a 4 flag szerint**.
- **Cumulative: −$1 843,66 (−1,84%)** — új swing-éra mélypont.
- **Net Liq: $99 349,82** — napi Δ **−$121,61**. ⚠️ A NetLiq **negyedannyit esett**, mint a
  realizált veszteség, mert a **nyitott könyv tovább javult** (§4).
- **Excess: −0,63%** (portfolio −0,31% vs SPY +0,32%). **MTM: −0,44%** — **azonos előjel**,
  0,19 pp rés. Ma **volt exit**, tehát nincs §D3/M-artefakt.
- **VIX 15,42 (−2,71%)**, SPY **+0,32%** — enyhe risk-on.
- **Nyitott pozíciók: 8** (9-ről; `reconcile_silent_ok` ✓).

## 2. Exits (4) — mind a négy a hétfőn beállított flag szerint
| Idő (UTC) | Ticker | Típus | Qty | Entry → Exit | Realized |
|---|---|---|---|---|---|
| 13:30:45 | **PSO** | **TP1** (530→265) | 265 | 16,08 → **16,54** | **+$121,76** (+2,86%) |
| 13:30:25 | **IMAX** | **TP1** (88→44) | 44 | 52,79 → **54,52** | **+$76,32** (+3,29%) |
| 19:59:32 | ZBRA | TIME_STOP | 10 | 379,84 → 360,41 | **−$194,28** (−5,11%) |
| 19:59:31 | BANC | TIME_STOP | 269 | 19,77 → **18,60** | **−$314,89** (−5,92%) |
| **Σ** | | | | | **−$311,09** |

📌 **Két TP1 egyetlen napon — a swing-éra első ilyen napja**, és mindkettő a **nyitáskor**
(13:30Z = 15:30 CEST) telt ki, pontosan a tervezett ablakban.

📌 **A nap tökéletesen kirajzolja a Day 63-as strukturális képet**: a **nyertesek TP1-en**
szállnak ki (+$121,76 / +$76,32), a **vesztesek max_hold-on** (−$194,28 / −$314,89).
A 08-21-i DLB TP1-gyel együtt **3 TP1 három ülés alatt, mind pozitív** — a korábbi
érában ez az ág ritka volt. **Leíró megfigyelés (G3)**, n=3.

## 3. Entries (1)
| Ticker | Qty | Planned→Fill | Slippage | Szektor |
|---|---|---|---|---|
| NWBI | 780 | 15,37 → **15,3851** | +0,10% (adverz) | Financial Services |

76 ticker a küszöb felett, 1 belépő. A jelölt-lista **top-3-ja ismét teljesen Healthcare**
(ELVN 105,4 | MD 98,1 | FMS 90,7) — de a rendszer **nem** vett fel újabb Healthcare tételt.

## 4. Nyitott pozíciók (8) — 08-25 záró mark
| Ticker | Szektor | Bázis | Záró | Unrealized |
|---|---|---|---|---|
| DLB (TP1 után) | Technology | 61,96 | 66,12 | **+$195,49** |
| PSO (TP1 után) | Comm. Services | 16,08 | 16,59 | **+$136,47** |
| MD | Healthcare | 26,62 | 26,99 | +$67,71 |
| ELVN | Healthcare | 60,35 | 61,01 | +$51,48 |
| IMAX (TP1 után) | Comm. Services | 52,76 | 53,90 | +$50,10 |
| RGEN | Healthcare | 180,72 | 181,69 | +$24,25 |
| FMS | Healthcare | 23,69 | 23,51 | −$50,40 |
| NWBI | Fin. Services | 15,39 | 15,30 | −$66,38 |
| **Σ** | | | | **+$408,73** |

🟢 **A könyv második napja pozitív és tovább javult**: −$225,96 (08-21) → +$242,53 (08-24) →
**+$408,73**. **6/8 tétel pozitív.** Mind a három TP1-es maradék (DLB, PSO, IMAX) **nyereségben**.

## 5. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 14:30 Phase 4-6, 15:30 eod_flags (2 TP1), 15:31 submit (NWBI),
  21:40 time_stop (2 MOC), 22:00–22:45 eod-lánc.
- ✓ **`reconcile_silent_ok`** — state ≡ IBKR. A `pending_exits` mind a 4 sora `processed: true`.
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó):
  `excess_10d_mean` **−0,14%** ✓ | `excess_15d_mean` **−0,18%** ✓ | `cum_30d` **−2,07%** ✓
  ⚠️ `excess_10d_sum` −1,43% és `excess_15d_sum` −2,66% BREACH — **D4: megfigyelés, nem trigger**.
- 🟢 **A `cum_30d` LEJÖTT a mélypontjáról**: −2,41% (08-24) → **−2,07%**. A −3,0%-os küszöbtől
  mért távolság 0,59 → **0,93 pp**. **Továbbra is a legfontosabb figyelendő trigger.**

## 6. Anomáliák (új/változott/lezárt)
- **✅ MEGOLDVA A REJTÉLY — az `exit_type` defekt FILL-TIMESTAMP vezérelt, és a 08-21-i romlást
  az outage okozta.** A két nap közvetlen összevetése:
  | Nap | Ticker | Kanonikus (`pending_exits`) | `daily_metrics::exit_type` | Fill |
  |---|---|---|---|---|
  | 08-21 | DLB | **TP1** | **MOC** ❌ | 15:51:04Z (**késett, kézi**) |
  | 08-21 | EQH | **MENTAL_SL** | **MOC** ❌ | 15:51:04Z (**késett, kézi**) |
  | 08-25 | PSO | TP1 | **TP1** ✓ | 13:30:45Z (normál ablak) |
  | 08-25 | IMAX | TP1 | **TP1** ✓ | 13:30:25Z (normál ablak) |
  Vagyis **amikor a fill a várt időablakba esik, a mező HELYES**; amikor nem (a 08-21-i,
  outage miatti 2h21m késés), **„MOC"-ra degradál**. Ez pontosan megerősíti a
  `signal_attribution` 2. invariánsában rögzített mechanizmust
  (*„fill-timestamp based and unreliable"*), és **szűkíti** a defektet: nem általános romlás,
  hanem **ablak-eltérés-osztályozó**.
  📌 **Következmény visszamenőleg**: a **W34 heti riport hibás TP1-metrikája** (0/6, $0,00)
  **az outage következménye volt**, nem a metrika általános hibája — normál héten helyes lenne.
  ✅ A kaput továbbra sem érinti (invariáns #2: a betöltő a `pending_exits`-ből olvas).
- **📌 A Healthcare-koncentráció stabilizálódott** — 20,93%, **változatlan**. A jelölt-lista
  top-3-ja ismét teljesen Healthcare volt, de a rendszer **nem** vett fel újabbat onnan
  (az egyetlen belépő NWBI = Financial Services). A 08-24-i sorozat
  (6,03 → 10,7 → 13,12 → 20,93%) **megtört** — a felfutás nem folytatódott.
- **✅ VÁLTOZATLAN**: `swing_state.exits_today` félrenevezés (ma `{TIME_STOP:1}` ≡ a **holnapi**
  IMAX flag), `commission_total` csak exit-lábat számol, `entry_price=planned`, `reconcile` csak
  ticker-halmazt hasonlít, **FileVault**, **`docs/analysis/` sync-rés**, **§5.1/§5.2 döntések**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **🆕 TP1-sorozat** — **n=3, mind pozitív**: DLB +$154,47 (08-21), PSO +$121,76, IMAX +$76,32.
  Három ülés alatt három TP1 — az érában korábban ritka ág. **n=3, nem általánosítható (G3).**
- **Next-day MKT fill slippage** — CC-éra **n=32** (+NWBI +0,10%, adverz): **24 adverz / 8 kedvező**.
- **Szektor-koncentráció** — **20,93%**, változatlan (a felfutás megtört).
- **„Rés utáni visszalépés"** — lezárt sorozat, n=3, mind negatív.
- **Self-reentry** — n=3. A DLB maradék 47 db **+$195,49**-en, a sorozat legjobb tétele.
- **Outage-késleltetett exit** — n=4 (+ a 08-21-i EQH/DLB **döntés alatt**, §5.2).
- **Rally/risk-off aszimmetria** — emelkedő nap, realized szerint **−0,63% lemaradás**.
  Sorozat: **9** rally-lemaradás vs 9 eső-napi felülteljesítés.
- **TP-hit / pozitív-exit**: **2/4** — az érában az egyik legjobb arány.

## 8. Holnap (szerda, 08-26) — várt + feltevés
**Egy TIME_STOP 21:40 MOC** (feltevés: szerdai close ≈ keddi záró):

| Ticker | Qty | Bázis / záró | `várt` |
|---|---|---|---|
| **IMAX** (TP1 után) | 44 | 52,76 / 53,90 | **≈ +$50** |

📌 **Ha teljesül, ez lenne a swing-éra egyik ritka POZITÍV max_hold-exitje** — a TP1 után
megmaradt fél pozíció nyereségben zárna. Ha teljesül: cumulative −$1 843,66 → **~−$1 794**.

- **Fókuszlista**: (1) az IMAX TIME_STOP — pozitív max_hold-exit lehetősége;
  (2) a **`cum_30d`** (−2,07%, javuló) — továbbra is az egyetlen valódi trigger-közelség;
  (3) a **+$408,73-as könyv** tartása; (4) a Healthcare-koncentráció (20,93%) alakulása.

## 9. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás.

## 10. A nap egy mondatban
Mind a négy flag lefutott, és a nap **tankönyvi pontossággal rajzolta ki a Day 63-as strukturális
képet** — a **nyertesek TP1-en** szálltak ki (+$122 / +$76, a swing-éra első két-TP1-es napja), a
**vesztesek max_hold-on** (−$194 / −$315) —, a cumulative **−$1 843,66**-ra süllyedt, miközben a
**nyitott könyv +$408,73-ra javult** (6/8 pozitív); a nap mellékterméke pedig egy **lezárt
diagnózis**: az `exit_type` romlás **fill-timestamp vezérelt**, tehát a W34 hibás TP1-metrikája
**az outage következménye volt**, nem a metrikáé.
