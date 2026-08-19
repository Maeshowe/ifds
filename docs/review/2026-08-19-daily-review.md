# IFDS Daily Review — 2026-08-19 (szerda, Day 65/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett; IBKR MCP kereszt-ellenőrzés lefutott.

## 1. Fejléc
- **Realized net: −$96,64** (gross −$92,34, komm. $4,30) — **1 exit** (ADT TIME_STOP MOC).
  A 08-18-i várakozás **≈ −$229** volt → **Δ +$132 kedvezőbb** (§2).
- **Cumulative: −$738,18 (−0,74%)** — `pt_eod` 22:11:04. Új swing-éra mélypont.
- **Net Liq: $98 941,88** — napi Δ **+$230,29** (08-18: $98 711,59).
  **Négy ülés óta az első emelkedő nap** (utoljára 08-13).
- **Excess: −0,30%** — `daily_metrics::excess_return` (portfolio −0,09% vs SPY +0,21%).
  ⚠️ **MTM-olvasat: +0,02%** → **ismét ellentétes előjel** (§6).
- **VIX 15,02 (−5,18%)** — risk-on nap, két risk-off nap után (SPY −0,47% → −0,68% → **+0,21%**).
- **Nyitott pozíciók: 7** (`swing_positions` ≡ IBKR ✓, `reconcile_silent_ok`).

## 2. Exits (1) — `TIME_STOP` MOC, day-5 max_hold
| Ticker | Qty | Entry → Exit | Realized | `várt` (08-18 záró) | Δ |
|---|---|---|---|---|---|
| ADT | 803 | 7,51 → **7,39** | **−$96,64** (−1,60%) | ≈ −$229 | **+$132** |

**Bróker-verifikáció**: ADT SELL 803 @ 7,39 MOC 19:59:42Z, `realized_pnl` **−96,643638**,
komm. 4,296238 ≡ a `daily_metrics` netto **pennyre** ✓

A **Δ +$132 pontosan az ADT mai `daily_pnl`-je** (+132,21): a pozíció a záró napon
7,22 → 7,39-re erősödött. A becslés a **tegnapi** záróárat vette bázisnak — a hiba nem a
számításban, hanem abban van, hogy **egy napos mark-extrapoláció** ennél a volatilitásnál
±1,5%-os nagyságrendű.

## 3. Entries (1) — a **DLB self-reentry** végrehajtása
| Ticker | Qty | Planned→Fill | Slippage | Komm. |
|---|---|---|---|---|
| DLB | 94 | 61,10 → **61,95** | **+1,39%** (adverz) | $1,00 |

Belépő-jelöltek top-3: IMAX 96,3 | BANC 93,4 | **DLB 91,2** — 69 ticker a küszöb felett, 1 belépő.

> **A self-reentry ára, számszerűen.** A DLB **tegnap** 21:40-kor max_hold-on kiszállt **61,13**-on,
> **ma** 13:31-kor visszavettük **61,95**-ön. A `planned` ár **61,10** volt — vagyis a rendszer
> **lényegében a tegnapi exit-árra** tervezte a visszalépést, és **+1,39%-kal drágábban** kapta meg.
>
> | Tétel | Összeg |
> |---|---|
> | Ár-rés (61,95 − 61,13) × 94 | **−$77,08** |
> | Exit-komm. (08-18) + entry-komm. (08-19) | −$2,14 |
> | **A „felesleges" oda-vissza teljes súrlódása** | **≈ −$79,22** |
>
> Ez a `max_hold` ↔ belépő-jel ellentmondás **konkrét, mért ára** egyetlen tételen — a **D6
> SIM-napirend 1. tételének** (max_hold-érzékenység) közvetlen inputja. **Leíró megfigyelés (G3):**
> nem állítja, hogy a `max_hold=5` rossz — azt méri, mibe kerül, amikor a két szabály ütközik.

## 4. Nyitott pozíciók (7) — 08-19 **záró** mark (IBKR `get_account_positions`)
| Ticker | Bázis | Záró | Unrealized | Napi Δ |
|---|---|---|---|---|
| DLB | 61,96 | 62,70 | **+$69,50** | +$69,50 (ma nyílt) |
| IMAX | 52,76 | 53,71 | **+$83,48** | **+$278,08** |
| SN | 187,64 | 181,24 | −$153,64 | −$37,92 |
| BANC | 19,77 | 18,94 | −$221,93 | −$96,84 |
| ZBRA | 379,73 | 354,92 | −$248,10 | −$115,00 |
| FBIN | 50,07 | 46,49 | −$268,75 | +$89,25 |
| EQH | 53,03 | 49,96 | **−$313,12** | −$89,76 |
| **Σ** | | | **−$1 052,56** | |

**A könyv javult**: −$1 378,72 → **−$1 052,56** (**+$326,16**). Ebből azonban csak **+$27,81** a
6 továbbvitt tétel érdeme — a többi az **ADT kilépése** (a −$228,86 unrealized −$96,64 realizálttá
vált) és az **új DLB** (+$69,50). **Két tétel pozitív** (DLB, IMAX) — 08-17 óta először nem mind negatív.

**Szektor-eltolódás**: az ADT kilépésével az **Industrials 0-ra** esett; a DLB visszavételével a
**Technology 3 760 → 9 504** (9,50%). Legnagyobb: Financial Services 10,70% — a 30%-os cap **messze**.

## 5. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 13:31 submit (DLB), 21:40 time_stop (ADT MOC), 22:11 eod,
  metrics, review_data.
- ✓ **`reconcile_silent_ok`** — state ≡ IBKR, 0 divergencia.
- ✓ **P&L-lánc bróker-pontos**: realized −$96,64 ≡ bróker `realized_pnl` −96,643638.
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó): `excess_10d_mean` **−0,01%** vs −1,0% →
  **nincs halt**, és **5× javult sorban** (−0,36% → −0,17% → −0,01%).
  🟢 **Az `excess_10d_sum` LEJÖTT a BREACH-ről** (−0,14% vs −1,0%) — hetek óta először.
  ⚠️ `excess_15d_sum` marad BREACH (−3,70%) — **D4: megfigyelés, nem trigger**.
- ⚠️ **`swing_state.exits_today` ÜRES**, holott volt exit (`exits.moc: 1` helyes) — az ismert
  `exit_type`/`swing_state` defekt (a `pending_exits` a kanonikus). Változatlan, nem új.
- ℹ️ **Holnapra nincs tervezett TIME_STOP** (`next_day_planned` üres) — hetek óta az első ilyen nap.

## 6. Anomáliák (új/változott/lezárt)
- **🔴 KORREKCIÓ a 08-18-i review-hoz — az állításom túl erős volt.**
  Tegnap ezt írtam: *„megerősíti a tegnap rögzített mechanizmust: a szétválás a 0-exites
  napokhoz kötött"*. **Ez nem áll.** A mai nap **közvetlenül cáfolja**: volt exit, és a két
  olvasat mégis **ellentétes előjelű** (realized −0,30% vs MTM +0,02%).
  **A tényleges megoszlás** (`stop_trigger_monitor`, swing-éra):

  | | n |
  |---|---|
  | Ellentétes előjelű nap | **12 / 44 (27,3%)** |
  | ebből **0-exites** | **3** |
  | ebből **volt exit** | **9** |

  Vagyis a 0-exites eset a szétválás **szélsőértéke** (ott `excess ≡ −SPY`), **nem a
  mechanizmusa**. A valódi ok általánosabb: **a realized-olvasat nem látja a nyitott könyv
  mozgását** — ma a könyv +$326-ot javult, miközben a realizált −$96,64 volt.
  ✅ **A gate-protokoll §D3/M szövege maga helyes volt** (3/11-et írt); a tegnapi review
  általánosított túl. A §D3/M számai ma frissítve (11/42 → **12/44**).
- **🟡 P2 (ÚJ) — a slippage-sorozat címkéje félrevezető.** A review-kban vezetett
  „next-day MKT fill slippage n=26" valójában a **CC-éra (2026-07-17→)** részhalmaza.
  A **teljes swing-éra**: **n=52** (35 adverz / 17 kedvező = **67,3% adverz**).
  A CC-éra: 26 (19 adverz = 73,1%). **Medián |slippage|: 88 bp (CC-éra) / 92 bp (teljes éra)** —
  konzisztens az FRL `cost_model.json` ~96–97 bp-jével. **Teendő**: a sorozat innentől
  **címkézve** („CC-éra") vagy teljes érára váltva. *(G1: nem kapu-input.)*
- **📌 A mai DLB-slippage nem rekord.** +1,39% a **CC-éra 4.** és a **teljes éra 6.** legnagyobb
  adverz fillje (rekord: FBIN +2,44%, 08-13; SSNC +1,78%, 08-05).
- **✅ VÁLTOZATLAN, nem ismételve**: `entry_price=planned` (§11.10), `uw_shadow` üresen ír
  (UW kivezetve — kapu utáni cleanup), `Day 65/63` számláló-artefakt, **FileVault** (parkolva),
  **`docs/analysis/` sync-rés** (a tegnapi P2 — a kapu előtt zárandó).

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **CC-éra n=26** (+DLB +1,39%, adverz): **19 adverz / 7 kedvező**.
  **Teljes swing-éra n=52**: 35 adverz / 17 kedvező. *(A címke-korrekció §6.)*
- **Self-reentry** — **n=3** (PFGC 07-21, USFD 07-23, **DLB 08-19**). A DLB az **első**, amelynek a
  súrlódási költsége **számszerűsítve** van (≈ −$79,22, §3).
- **„Rés utáni visszalépés"** — n=2 lezárt (JAZZ, GTES), **1 nyitva**: **EQH −$313,12**
  (08-18: −$223,36 → **tovább mélyült**, a nyitott könyv legrosszabb tétele).
- **Outage-késleltetett exit** — n=4, változatlan. **„Stop-közeli"** — n=5, változatlan.
- **Rally/risk-off aszimmetria** — ma **emelkedő** nap (SPY +0,21%), realized-olvasat szerint
  **−0,30% lemaradás**; MTM szerint +0,02%. Sorozat (realized-olvasat):
  **7** rally-lemaradás vs 7 eső-napi felülteljesítés.
- **TP-hit / pozitív-exit**: ma **0/1**. A TIME_STOP-tömb aránya tovább nő.
- **Várt-vs-tény**: **+$132 kedvezőbb** — a második egymást követő nap, amikor a mark-alapú
  becslés **érdemben** tévedett (08-18: +$46 Σ-ban, tételenként ellentétes irányban).

## 8. Holnap (csütörtök, 08-20) — várt + feltevés
**Nincs tervezett exit** (`next_day_planned` üres; a legidősebb tétel 4 napos).
Ha nem lesz mentális stop és nem születik új exit-flag: **realized $0,00** →
a nap kimenetele **teljes egészében a nyitott könyvön** múlik.

⚠️ **Ez pontosan a §D3/M szélsőérték-esete**: 0 exit mellett a realized-olvasat
**definíció szerint `excess = −SPY`** lesz. **Emelkedő tapén automatikusan „lemaradást",
eső tapén „felülteljesítést" fog mérni** — a valós teljesítménytől függetlenül.
A **MTM-olvasatot kell mellé olvasni** (diagnosztika; a D3 szerint a realized marad az irányadó).

- **Fókuszlista**: (1) a nyitott könyv (−$1 052,56) — 0-exites napon ez az egyetlen mozgás;
  (2) az **EQH** (−$313,12), a „rés utáni visszalépés" 3. esete, mélyülő;
  (3) a STOP-`mean` (−0,01%, 5× javult) és a `15d_sum` BREACH alakulása;
  (4) a **DLB** (+$69,50) — a self-reentry első teljes napja.

## 9. Freeze-sor
🔓 A parameter freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció
FAGYVA marad 2026-09-22-ig** (kétsávos: a revíziók a SIM-L2 / Mode 2 re-score infrán).
A **G1/G3–G7 guardrailek változatlanul élnek**. Ma **nem történt** production-kód változás.

## 10. A nap egy mondatban
Az ADT max_hold-exitje **$132-tal a vártnál kedvezőbben** zárt (−$96,64), a NetLiq négy ülés után
először emelkedett (+$230), a könyv −$1 052,56-ra javult és **08-17 óta először nem mind negatív** —
miközben a nap két tanulsága a **DLB self-reentry mért súrlódása (≈ −$79)** és az, hogy a
realized/MTM szétválás **nem a 0-exites napokhoz kötött**, ahogy tegnap tévesen írtam,
hanem a 12 ellentétes-előjelű napból **9-en volt exit**.
