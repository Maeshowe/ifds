# IFDS Daily Review — 2026-09-15 (kedd, Day 83/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ IBKR MCP connector nem elérhető — bróker-kereszt-ellenőrzés kimaradt; helyette Mini
> `reconcile_state` **silent OK**, kanonikus `pending_exits`, Polygon záró markok.

## 0. 🔴 D7 NAPI KÖTELEZŐ SOR — leállítási feltétel státusza
| | |
|---|---|
| **`cum_30d`** | **−3,45%** (−$3 454,79) — **BREACH**, **3. kereskedési nap** |
| Tegnapi projekció | bázis −3,55% + napi realizált; tény **+$98,17** → **−3,45%** ✓ |
| **Ma (09-16) kigördül** | 08-03, **$0,00** → bázis **változatlan −3,45%** |
| **A breach feloldásához a mai realizált kellene** | **> +$454,79** |
| A mai flagek implikált várakozása (09-15 mark) | ELVN MENTAL_SL ≈ **−$366**, FBP TIME_STOP ≈ **−$201** → **Σ ≈ −$568** |
| **Kapu** | **2026-09-22 — 5 kereskedési nap** (D7: ott döntés) |

🟢 A pre-reg irányadó **excess**-triggerek tiszták, és az `excess_15d_sum` **lejött a BREACH-ről**:
`excess_10d_mean` −0,01% | `excess_15d_mean` −0,05% | `excess_10d_sum` −0,06% | `excess_15d_sum` **−0,77%** ✓
**A `cum_30d` az egyetlen fennálló breach.**

## 1. Fejléc
- **Realized net: +$98,17** (gross +$100,40, komm. $2,23) — **2 exit**.
- **Cumulative: −$3 107,34 (−3,11%)**.
- **Net Liq: $96 742,15** — napi Δ **−$184,63**.
- **Excess: +0,56%** (portfolio +0,10% vs SPY −0,46%).
- **VIX 17,44 (+1,99%)**, SPY −0,46%.
- **Nyitott pozíciók: 9**; kitettség **69,94% → 60,24%**.

## 2. 🔴 A §11.20 FINDING ÉLES ESETE — a MANH „take profit" VESZTESÉGGEL zárt
| Idő (UTC) | Ticker | Kanonikus típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 13:30:23 | **MANH** | **TP1** (25→13) | 12 | 207,82 → **206,66** | **−$13,89 (−0,56%)** | ≈ +$48 | **−$62** |
| 19:59:38 | EQH | TIME_STOP | 136 | 53,13 → 53,95 | **+$112,06** (+1,55%) | ≈ +$75 | +$37 |
| **Σ** | | | | | **+$98,17** | ≈ +$123 | −$25 |

**A tegnap dokumentált mechanizmus (04-risks §11.20) 24 órán belül élesben megvalósult:**

| Lépés | Érték |
|---|---|
| Phase 6 **tervezett** ár | 201,82 |
| Tényleges MKT fill (09-14) | **207,69** (+2,91%) |
| `tp1_level` (= tervezett + 1,5 ATR) | **212,25** — a **valós** belépőhöz mérve csak **+2,20%** |
| 09-14 intraday **high** | **212,85** → TP1-trigger |
| **Végrehajtás** (09-15, 15:30) | **206,66** — **a belépő ALATT** |
| **Eredmény** | **−$13,89 — „nyereségcélon" realizált VESZTESÉG** |

📌 **Két hatás egymásra rakódott**: (1) a TP1-szint a **tervezett** árhoz kötött, ezért a valós
belépőhöz képest **58%-kal közelebb** volt; (2) a trigger az **intraday high**-ra tüzel, de a
**végrehajtás a KÖVETKEZŐ ülés 15:30-kor** — egy teljes ülésnyi elsodródás. A kettő együtt
fordította át a „profit"-ot veszteségbe.

### ⚠️ KORREKCIÓ a saját sorozat-címkémhez
A legutóbbi review-kban **„TP1-sorozat n=7, mind pozitív"**-ot írtam. **Ez egy szűk, általam
2026-08-21 óta követett részhalmaz volt, nem a teljes kép** — ugyanaz a címkézési hiba, mint
korábban a slippage-nél (CC-éra vs teljes éra).

**A teljes swing-éra TP1-képe: n=25, ebből 3 negatív:**
RBC **−$32,38** (06-26) | SLGN **−$63,01** (07-08) | **MANH −$13,89** (09-15).
Tehát a MANH a **harmadik** negatív TP1, és az **első 2026-07-08 óta** — **nem az első**, ahogy
az első ránézésre tűnt. **A sorozatot innentől teljes-éra bázison vezetem.**

## 3. Entries (0)
Nem volt belépő. A kitettség a két exittel **69,94% → 60,24%**-ra csökkent; a legnagyobb szektor
**Financial Services 17,64%** (az EQH kilépésével a 24,92%-ról).

## 4. Nyitott pozíciók (9) — 09-15 záró mark
| Ticker | Szektor | Bázis (fill) | Záró | Unrealized |
|---|---|---|---|---|
| YPF (TP1 után) | Energy | 54,21 | 57,61 | **+$173,40** |
| MANH (TP1 után) | Technology | 207,82 | 209,62 | +$23,40 |
| CRBG | Fin. Services | 34,97 | 35,02 | +$11,75 |
| IMAX | Comm. Services | 52,80 | 52,77 | −$2,90 |
| TS | Basic Materials | 57,39 | 56,64 | −$102,75 |
| FBP | Fin. Services | 28,72 | 28,11 | −$201,47 |
| RCI | Comm. Services | 36,83 | 35,84 | −$217,80 |
| **ELVN** | Healthcare | 57,57 | 53,36 | **−$366,27** |
| **OGE** | Utilities | 47,37 | 45,71 | **−$385,12** |
| **Σ** | | | | **−$1 067,75** |

A könyv **−$767,67 → −$1 067,75** (−$300,08), **4/9 pozitív**. A két legrosszabb tétel
(**ELVN**, **OGE**) együtt −$751 — az **ELVN ma MENTAL_SL-en zárhat** (§0).
📌 Az **ELVN a 09-10-i „olcsóbb visszalépés"** volt (−0,47%) — azóta **−7,3%**-on áll.

## 5. Ops-checklist
- ✓ **Cron-lánc**: 14:30 Phase 4-6, 15:30 eod_flags (MANH TP1), 15:31 submit (0 tétel),
  21:40 time_stop (EQH MOC), 22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🔴 **D7-sor** (§0): `cum_30d` −3,45%, BREACH, 3. nap.
- 🟢 **Az `excess_15d_sum` lejött a BREACH-ről** — a `cum_30d` az egyetlen fennálló.
- ✓ **Az `exit_type` ma HELYES** mindkét tételnél (MANH TP1 a 15:30-as ablakban, EQH
  TIME_STOP_MOC a 21:40-esben) — konzisztens a §11.17 korrigált mechanizmusával
  (az ablak alapértelmezése ezúttal egyezik a tényleges típussal).

## 6. Anomáliák
- **🔴 A §11.20 éles esete** (§2) — a mechanizmus **egy napon belül** igazolódott, mérhető árral
  (a becsléstől −$62). **Kapu után, SIM-ben** (D6/D7: prod fagyva).
- **⚠️ Saját sorozat-címke korrekció** (§2) — a TP1-sorozat teljes-éra bázison n=25, 3 negatív.
- **✅ VÁLTOZATLAN**: `swing_state.exits_today`, `commission_total` csak exit-láb,
  `entry_price=planned` (§11.10/§11.20), `reconcile` csak ticker-halmaz, szektor-cap rés (§11.18),
  TP1 utáni max_hold-túlfutás, **FileVault**, **sync-rés**, **§5.1/§5.2 döntések**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **TP1 (teljes swing-éra)** — **n=25, ebből 3 negatív** (RBC, SLGN, **MANH**). *(Címke javítva, §2.)*
- **Teljesen lezárt TP1-ciklusok** — n=6, mind pozitív, Σ +$850,84. A **MANH ciklusa nyitva**
  (13 db maradék, +$23,40).
- **Visszalépés exit után** — n=12 (9 drágább / 3 olcsóbb). Az **ELVN** (olcsóbb eset) −7,3%-on.
- **Next-day MKT fill slippage** — CC-éra n=51, változatlan (ma 0 belépő).
- **Kitettség** — 60,24% (a 69,94%-os rekordról).
- **MENTAL_SL** — n=7; a 8. **ma esedékes** (ELVN).
- **Pozitív realizált nap** — **28/75** (ma igen).
- **Rally/risk-off aszimmetria** — eső nap, realized +0,56% felülteljesítés.

## 8. Ma (szerda, 09-16) — várt + feltevés *(nagyságrend, nem előrejelzés)*
| Idő | Ticker | Típus | Qty | Bázis / 09-15 záró | `várt` |
|---|---|---|---|---|---|
| 15:30 | **ELVN** | **MENTAL_SL** | 87 | 57,57 / 53,36 | **≈ −$366** |
| 21:40 | **FBP** | TIME_STOP | 333 | 28,72 / 28,11 | **≈ −$201** |
| **Σ** | | | | | **≈ −$568** |

⚠️ **A D7-sor szerint a breach feloldásához > +$454,79 kellene** — a fenti implikált várakozás
ezzel **ellentétes irányú**. Az FBP a **második** visszalépése után zárna (09-08-i visszavétel).
- **Fókuszlista**: (1) **D7-sor**; (2) a két exit; (3) a **−$1 067,75-ös könyv** (ELVN/OGE −$751);
  (4) **a kapuig 5 kereskedési nap** — a **§5.1/§5.2 döntés** és az abból következő **új pin**
  még nyitott.

## 9. Freeze-sor
🔓 Freeze feloldva 08-17 — **D6: a production konfiguráció FAGYVA 2026-09-22-ig**; **D7: a breach
nem indok paraméter-változtatásra.** G1/G3–G7 élnek. Ma **nem történt** production-kód változás.

## 10. A nap egy mondatban
Pozitív realizált nap (**+$98,17**, az EQH +$112,06-os max_hold-exitjéből) — de a nap érdemi
tartalma az, hogy **a tegnap dokumentált §11.20 geometriai torzulás 24 órán belül élesben
megvalósult**: a MANH „nyereségcélja" a **tervezett** árhoz volt kötve, a trigger az intraday
high-ra tüzelt, a végrehajtás pedig a következő ülésen a **belépő alatt** történt — így a TP1
**−$13,89-cel, veszteséggel** zárt; a `cum_30d` eközben **−3,45%-on, harmadik napja BREACH-ben**,
és a mai flagek ezzel **ellentétes irányba** mutatnak.
