# IFDS Daily Review — 2026-09-24 (csütörtök, **Day 90/63**) — a kapu után, futás nélkül

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ IBKR MCP connector nem elérhető — bróker-kereszt-ellenőrzés kimaradt; helyette Mini
> `reconcile_state` **silent OK**, kanonikus `pending_exits`, Polygon záró markok.
> ℹ️ **Késve készült** (2026-09-25) — a **mai (09-25) review + a W39 heti zárás** hátra van.

## 0. 🔴 D7 NAPI KÖTELEZŐ SOR + a kapu státusza
| | |
|---|---|
| **`cum_30d`** | **−5,87%** (−$5 872,39) — **BREACH**, **10. kereskedési nap** |
| Gördülés | +1 (09-25): **−5,46%** · +2 (09-28): −5,22% · +3 (09-29): −5,22% |
| **Kapu-futás** | 🔴 **TOVÁBBRA SEM TÖRTÉNT MEG** (ellenőrizve: 0 db 09-es attribution-riport) |
| **§5.1 / §5.2 döntés** | **nem született meg**; pin **`68fc00e`** |
| **A kapu dátuma (09-22) óta** | **2 kereskedési nap** *(a review dátumán, 09-25-én: 3)* |

🟢 A pre-reg **irányadó** triggerek tiszták: `excess_10d_mean` **−0,40%**, `excess_15d_mean` **−0,25%**.
⚠️ A `sum`-olvasatok BREACH — **D4: megfigyelés**.

📌 **A 09-22-i P0 (04-risks §11.21) nyitva.** A két út — **(1) futás dokumentált
dátum-eltéréssel**, **(2) a kapu-dátum újra-rögzítése** — változatlanul nyitva; mindkettő
**írásbeli rögzítést kíván a futás ELŐTT**. **CC nem választ; Tamás-döntés.**

## 1. 📌 DAY 90 ELÉRVE — a törölt roadmap-tétel dátuma
Ma a **Day 90**. Az eredeti terv szerint ide volt időzítve a **UW dark-pool Bayesian
rekalibráció** — amit a **2026-08-18-i UW-kivezetési döntés TÖRÖLT** (nem elhalasztott;
`docs/decisions/2026-08-18-uw-decommission.md`, 04-risks §11.14). Indok: a shadow-minta már a
06-18-i de-scope-nál **n=69** volt, ami elégtelen, és a kulcs hiányával nem is nőtt.
✅ **A tétel tehát a tervezett dátumon, tudatosan elmaradt** — nincs nyitott teendő belőle.

## 2. Fejléc
- **Realized net: −$505,17** (gross −$503,65, komm. $1,52) — **1 exit**.
- **Cumulative: −$5 672,77 (−5,67%)** — új mélypont.
- **Net Liq: $94 630,97** — napi Δ **+$177,04**. ⚠️ **A NetLiq EMELKEDETT** egy −$505-os
  realizált napon: a nyitott könyv **+$688**-at javult (§4).
- **Excess: −0,42%** (portfolio −0,50% vs SPY −0,08%).
- **VIX 15,46 (+1,84%)**, SPY −0,08% — csendes nap.
- **Nyitott pozíciók: 4**; kitettség **37,48% → 29,54%** — **a legalacsonyabb hetek óta**.

## 3. Exits (1)
| Idő (UTC) | Ticker | Kanonikus típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 13:30:11 | **NWSA** | **MENTAL_SL** | 263 | 30,14 → **28,22** | **−$505,17** (−6,37%) | ≈ −$529 | **+$24** |

✅ **MEGSZAKADT a 9 napos egyirányú becslési sorozat.** Kilenc egymást követő nap után
(−$64 / −$172 / −$29 / −$171 / −$202 / −$198 / −$43 / −$299 / −$14) **ma a tény $24-gyel
KEDVEZŐBB** lett a becslésnél. **A sorozat tehát nem szisztematikus torzítás, hanem
tape-függő** — a risk-off sorozat végével megfordult. **Leíró (G3).**

📌 A **NWSA a 9. MENTAL_SL**, és a **könyv legnagyobb nyitott vesztesége** volt.
⚠️ **A §11.17 defekt 5. esete**: kanonikus **MENTAL_SL**, a `trades.details.exit_type` mégis
**„TP1"** (fill 13:30:11Z, normál ablak); az `exits` blokk helyesen `sl: 1`.

## 4. Nyitott pozíciók (4) — 09-24 záró mark
| Ticker | Szektor | Bázis (fill) | Záró | Unrealized |
|---|---|---|---|---|
| EXLS | Technology | 35,51 | 35,16 | −$62,30 |
| MD | Healthcare | 26,18 | 25,66 | −$107,12 |
| NWBI | Fin. Services | 15,46 | 15,18 | −$187,88 |
| **EQH** | Fin. Services | 54,96 | 52,61 | **−$331,35** |
| **Σ** | | | | **−$688,65** |

🟢 A könyv **−$1 376,70 → −$688,65** (**+$688,05**) — de a javulás **döntően átsorolás**
(a NWSA −$529-es unrealizedje realizálttá vált). **Mind a négy tétel negatív.**
Az **EQH** (a 09-17-i visszalépés) a legrosszabb — **ma TIME_STOP-on zár** (≈ −$331).

## 5. Ops-checklist
- ✓ **Cron-lánc**: 14:30 Phase 4-6, 15:30 eod_flags (NWSA MENTAL_SL), 15:31 submit (0 tétel),
  22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🔴 **D7-sor** (§0): `cum_30d` −5,87%, BREACH, 10. nap.
- 🔴 **A kapu-futás elmaradása** (§0) — nyitott P0.
- ⚠️ **§11.17, 5. eset** (§3).

## 6. Anomáliák
- **🔴 A kapu-futás továbbra sem történt meg** (§0) — a késés nő.
- **✅ A 9 napos egyirányú becslési sorozat megszakadt** (§3) — tape-függőnek bizonyult.
- **📌 Day 90 elérve**; a hozzá kötött UW-rekalibráció **tudatosan törölt** (§1).
- **⚠️ §11.17 5. eset** (§3).
- **✅ VÁLTOZATLAN**: §11.18 szektor-cap rés, §11.20 (TP1/stop/breakeven a tervezett árhoz; a
  trail helyes), §11.21 (kapu-futás), `swing_state.exits_today`, `commission_total`,
  `reconcile` csak ticker-halmaz, TP1 utáni max_hold-túlfutás, **FileVault**, **sync-rés**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **MENTAL_SL** — **n=9** (+NWSA −$505,17).
- **Teljesen lezárt TP1-ciklusok** — n=8 (7 pozitív + 1 negatív), Σ +$883,98. *(Ma nem bővült.)*
- **TP1 (teljes swing-éra)** — n=26, ebből 3 negatív. **TRAIL_SL** — n=1.
- **Visszalépés exit után** — n=15 (11 drágább / 4 olcsóbb); 3 teljes ciklus lezárva, mind negatív
  — szemben az IMAX 3/3 pozitívjával.
- **Next-day MKT fill slippage** — CC-éra n=56, változatlan (ma 0 belépő).
- **Kitettség** — **29,54%**, hetek óta a legalacsonyabb (a 09-14-i 69,94%-os rekordról).
- **Pozitív realizált nap** — 29/82 (ma nem).
- **Becslési irány** — **9 egyirányú nap után megfordult** (§3).
- **TP-hit / pozitív-exit**: **0/1**. **Várt-vs-tény**: **+$24**.

## 8. Ma (péntek, 09-25)
**Egy TIME_STOP 21:40 MOC**: **EQH** 141, bázis 54,96 / 09-24 záró 52,61 → **≈ −$331**.
📌 Ezzel lezárulna az **EQH második ciklusa**: 1. ciklus **+$112,06** (09-15 TIME_STOP) →
visszalépés 09-17 @ 54,96 (**+2,00% adverz fill, +1,87% drágábban**) → 2. ciklus ≈ **−$331**
→ **≈ −$219 nettó**. Ez lenne a **negyedik** lezárt visszalépési ciklus — és **mind a négy negatív**.
- **Fókuszlista**: (1) **a kapu-döntés (§0)** — 3 kereskedési nap késés; (2) az EQH TIME_STOP;
  (3) **W39 heti zárás** — a §11.17 miatt **a TP1-sor korrekciója ismét kötelező**
  (a NWSA MENTAL_SL-je „TP1"-ként fog megjelenni); (4) a `cum_30d` (−5,87%).

## 9. Freeze-sor
⚠️ A D6 prod-fagyás formálisan 09-22-vel lejárt, **de a feloldás a kapu utánra szólt**, és a futás
nem történt meg → a production-konfiguráció változtatása **továbbra sem indokolt** (§11.21).
**G1/G3–G7 élnek.** Ma **nem történt** production-kód változás.

## 10. A nap egy mondatban
**Day 90**-en — annak a napnak a dátumán, amelyre az azóta **tudatosan törölt** UW-rekalibráció
volt időzítve — egy MENTAL_SL **−$505,17**-tal új mélypontra vitte a kumulatívat (**−$5 672,77**),
miközben a **NetLiq mégis emelkedett** (+$177), mert a veszteség **már be volt árazva**; a
kilenc napos egyirányú becslési sorozat **megszakadt** (+$24), a kitettség **29,54%-ra** esett —
és a **`cum_30d` −5,87%-on, tizedik napja BREACH-ben** áll, **a kapu-futás pedig három
kereskedési nappal a dátum után is elmaradt**.
