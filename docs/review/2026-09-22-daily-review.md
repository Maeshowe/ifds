# IFDS Daily Review — 2026-09-22 (kedd, Day 88/63) — **A KAPU NAPJA**

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ IBKR MCP connector nem elérhető — bróker-kereszt-ellenőrzés kimaradt; helyette Mini
> `reconcile_state` **silent OK**, kanonikus `pending_exits`, Polygon záró markok.

---

# 🔴 P0 — A KAPU NAPJA LEZÁRULT, A KAPU-FUTÁS NEM TÖRTÉNT MEG

## A. Tényállás (verifikálva)
| | |
|---|---|
| **A kapu dátuma** | **2026-09-22** — D2-ben, 2026-07-28-án **fixen** rögzítve |
| **Megtörtént-e a futás?** | **NEM** — sem a MacBookon, sem a Minin nincs `signal-attribution-*` vagy `gate-sample-*` riport 09-22-i dátummal *(a `docs/analysis/`-ban csak a 2026-06-24-i data-coverage doksi van)* |
| **§5.1 / §5.2 döntés** | **nem született meg** — a `gate_sample.py` pinje változatlanul **`68fc00e`** |
| **`cum_30d` a kapu napján** | **−5,22%** (a −3,0%-os küszöb ellenében) — **BREACH, 8. kereskedési nap** |

## B. Mit jelent ez a pre-reg keretében
- **A D7-döntés esedékessé vált.** A 2026-09-12-i rögzítés: *„elmegyünk a kapuig (2026-09-22),
  a folytatás/leállítás kérdésében ott születik döntés."* **A dátum elérkezett és elmúlt.**
- **A leállítási feltétel fennáll**, és a §3 szerinti olvasat változatlan: ha a feltétel a kapun
  áll, a **LEÁLLÍTÁS kritérium teljesül**; a *„DEFAULT: PAPER FOLYTATÁS"* csak akkor alkalmazandó,
  ha **sem** élesítési, **sem** leállítási feltétel nem áll fenn.
- **A kereskedés közben fut tovább** — ma is volt 3 exit és 1 belépő, a kumulatív **−$5 193,86**.

## C. Két út — mindkettő írásbeli rögzítést kíván, a futás ELŐTT
**1) A kapu-futás lebonyolítása most, egy-két nap késéssel (dokumentált eltérés).**
   A §6/3 kulcsfeltétele **továbbra is teljesíthető**: *előbb a minta-definíció fixálása →
   utána a futtatás.* A késés **önmagában nem sérti a pre-reg-et**, ha
   (a) a **§5.1/§5.2 döntés** megszületik és a pin rögzül **a futás előtt**, és
   (b) a **dátum-eltérés oka és mértéke** a futás **előtt** íródik a protokollba.
   ⚠️ Az egy-két nap plusz adat a mintába **bekerül** — ez a késés ára, és rögzítendő.

**2) A kapu-dátum újra-rögzítése.** Ez a **második halasztás** lenne (a D7 után), és a D2 fix
   dátumának lényegét gyengíti. Ha ez a választás, **új dátumot és indoklást kell rögzíteni
   azonnal, az adat további ismerete nélkül** — különben a „meddig várunk" kérdés
   megkülönböztethetetlenné válik az eredmény-figyeléstől.

📌 **CC nem választ a kettő közül** — ez Tamás-döntés. **Javaslom viszont, hogy MA szülessen meg**,
mert minden további nap növeli a 2) út felé sodródás kockázatát anélkül, hogy azt valaki
kimondta volna.

📌 **Amit a futás ELŐTT mindenképp el kell végezni** (gate-protokoll §8/E, §8/F):
a riport **szó szerint** rögzítse, hogy **2026-09-11 óta pre-reg leállítási feltétel él**;
idézze a **§D3/M** korlátot és a **§D3/P** UW-proveniencia mondatot; a `signal_attribution`
**leíró** marad (G1/G3), a leállítási kérdéshez **nem** input; és a riport a **Minin** készüljön
(a `docs/analysis/` sync-rés miatt).

---

## 1. Fejléc
- **Realized net: −$254,39** (gross −$250,87, komm. $3,52) — **3 exit**.
- **Cumulative: −$5 193,86 (−5,19%)** — új mélypont.
- **Net Liq: $95 006,32** — napi Δ **−$720,26**.
- **Excess: −0,24%** (portfolio −0,25% vs SPY −0,02%).
- **VIX 14,25 (−4,17%)**, SPY −0,02% — csendes nap.
- **Nyitott pozíciók: 6**; kitettség **48,41% → 40,24%**.

## 2. Exits (3)
| Idő (UTC) | Ticker | Kanonikus típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 13:32:44 | IMAX | **TP1** (105→53) | 52 | 52,83 → 53,45 | **+$32,36** (+1,18%) | ≈ +$65 | −$33 |
| 19:59:32 | **MANH** | TIME_STOP | 13 | 207,81 → 206,92 | **−$11,59** (−0,43%) | ≈ +$20 | −$32 |
| 19:59:32 | **CRBG** | TIME_STOP | 235 | 34,98 → **33,81** | **−$275,16** (−3,35%) | ≈ −$40 | **−$235** |
| **Σ** | | | | | **−$254,39** | ≈ +$45 | **−$299** |

⚠️ **A becslés NYOLCADIK egymást követő napja alulbecsüli a veszteséget** (a CRBG egyedül −$235).
Sorozat: −$64 / −$172 / −$29 / −$171 / −$202 / −$198 / −$43 / **−$299**. **8/8 azonos irány.**

### 🔴 Az ELSŐ NETTÓ NEGATÍV TP1-ciklus — és épp a §11.20-eset
| Esemény | Dátum | Összeg |
|---|---|---|
| **TP1** (12 db @ 206,66) | 09-15 | **−$13,89** |
| **TIME_STOP** (13 db @ 206,92) | 09-22 | **−$11,59** |
| **Nettó** | | **−$25,48** |

📌 A **MANH** a **hetedik** teljesen lezárt TP1-ciklus — és **az első, amelyik nettó negatív**.
Az előző hat mind pozitív volt (Σ +$850,84); a hét együtt **+$825,36**.
⚠️ **Ez pontosan a §11.20-eset**: a MANH TP1-szintje a **tervezett** árhoz (201,82) volt kötve,
a valós fill 207,69 volt (+2,91%, éra-rekord adverz fill) — a „nyereségcél" a valós belépőhöz
mérve csak **+2,20%**-ra volt. **A ciklus mindkét lába veszteséges lett.** **n=1, leíró (G3).**

## 3. Entries (1)
| Ticker | Qty | Planned→Fill | Slippage | Megjegyzés |
|---|---|---|---|---|
| **MD** | 206 | 25,77 → **26,18** | **+1,59%** (adverz) | **Visszalépés** (09-01 TIME_STOP @ 26,47 → **−1,10%, olcsóbban**) |

📌 A **MD +1,59%** a CC-éra 4. legnagyobb adverz fillje. **Visszalépés-sorozat n=15**
(11 drágább / **4 olcsóbb**).

## 4. Nyitott pozíciók (6) — 09-22 záró mark
| Ticker | Szektor | Bázis (fill) | Záró | Unrealized |
|---|---|---|---|---|
| IMAX (TP1 után) | Comm. Services | 52,83 | 53,59 | **+$40,28** |
| MD | Healthcare | 26,18 | 26,35 | +$35,02 |
| EXLS | Technology | 35,51 | 35,02 | −$87,22 |
| NWBI | Fin. Services | 15,46 | 15,21 | −$167,75 |
| NWSA | Comm. Services | 30,13 | 29,25 | −$231,44 |
| **EQH** | Fin. Services | 54,96 | 52,20 | **−$389,16** |
| **Σ** | | | | **−$800,27** |

A könyv **−$308,25 → −$800,27** (−$492,02); **2/6 pozitív**. Az **EQH** a legrosszabb
(−$389,16, −5,0%) — ez a **09-17-i visszalépés** volt (+2,00% adverz fill).
Az **IMAX ma TIME_STOP-on zár** (≈ +$40).

## 5. Ops-checklist
- ✓ **Cron-lánc**: 14:30 Phase 4-6, 15:30 eod_flags (IMAX TP1), 15:31 submit (MD),
  21:40 time_stop (MANH, CRBG MOC), 22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🔴 **D7-sor**: `cum_30d` **−5,22%**, BREACH, **8. nap** — **a kapu napján is**.
- Gördülés innen (0 realizált): +1 **−5,39%** · +2 −5,39% · +3 **−4,98%**.
- ✓ Az `exit_type` ma **mindhárom tételnél helyes**.

## 6. Anomáliák
- **🔴 A kapu-futás elmaradt** (§A–C) — **a nap fő tétele.**
- **🔴 Az első nettó negatív TP1-ciklus** (MANH, −$25,48) — a §11.20-eset (§2).
- **⚠️ A becslés 8/8 egyirányú tévedése** (§2).
- **✅ VÁLTOZATLAN**: §11.17 `exit_type`, §11.18 szektor-cap rés, §11.20 (TP1/stop/breakeven a
  tervezett árhoz; a trail helyes), `swing_state.exits_today`, `commission_total`,
  `reconcile` csak ticker-halmaz, TP1 utáni max_hold-túlfutás, **FileVault**, **sync-rés**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Teljesen lezárt TP1-ciklusok** — **n=7**: 6 pozitív + **1 negatív** (MANH −$25,48);
  Σ **+$825,36**.
- **TP1 (teljes swing-éra)** — n=26 (+IMAX +$32,36), ebből 3 negatív.
- **Visszalépés exit után** — **n=15** (11 drágább / 4 olcsóbb); 3 teljes ciklus lezárva, mind negatív.
- **Next-day MKT fill slippage** — CC-éra **n=56** (+MD +1,59%): **41 adverz / 15 kedvező** (73,2%).
- **Kitettség** — 40,24%.
- **Pozitív realizált nap** — 28/80 (ma nem).
- **TP-hit / pozitív-exit**: **1/3**. **Várt-vs-tény**: **−$299** (8. egyirányú).

## 8. Ma (szerda, 09-23)
**Egy TIME_STOP 21:40 MOC**: **IMAX** 53 db (TP1-maradék), bázis 52,83 / záró 53,59 → **≈ +$40**.
📌 Ha teljesül, az **IMAX harmadik ciklusa** zárul (+$76,32 TP1 09-25… → most +$32,36 + ≈ +$40).
- **Fókuszlista**: (1) **a kapu-döntés (§C) — ma esedékes**; (2) az IMAX TIME_STOP;
  (3) a `cum_30d` (−5,22%, a gördülés +1-re −5,39%); (4) a −$800-as könyv (EQH −$389).

## 9. Freeze-sor
🔓 **A D6 szerinti prod-fagyás 2026-09-22-vel LEJÁRT.** ⚠️ **De a D6 feloldása a kapu-futáshoz
volt kötve** („a revíziók a kapu után"), és **a futás nem történt meg** — így a prod-konfiguráció
**változtatása továbbra sem indokolt**, amíg a §C szerinti döntés meg nem születik.
**G1/G3–G7 élnek.** Ma **nem történt** production-kód változás.

## 10. A nap egy mondatban
**A kapu napja lezárult anélkül, hogy a kapu-futás megtörtént volna** — a §5.1/§5.2 döntés nem
született meg, a pin változatlan (`68fc00e`) —, miközben a **pre-regisztrált leállítási feltétel
a kapu napján is fennállt** (`cum_30d` **−5,22%**, 8. nap); a kereskedés közben tovább futott,
3 exittel **−$254,39**-et realizálva (új mélypont: **−$5 193,86**), és lezárult az **első nettó
negatív TP1-ciklus** (MANH −$25,48) — épp az a tétel, amelyiknél a §11.20 geometriai torzulást
dokumentáltuk.
