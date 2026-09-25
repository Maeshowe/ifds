# IFDS Daily Review — 2026-09-23 (szerda, Day 89/63) — **a kapu után, futás nélkül**

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ IBKR MCP connector nem elérhető — bróker-kereszt-ellenőrzés kimaradt; helyette Mini
> `reconcile_state` **silent OK**, kanonikus `pending_exits`, Polygon záró markok.
> ℹ️ **Késve készült** (2026-09-25) — a **09-24-i review + a W39 heti zárás** hátra van.

## 0. 🔴 D7 NAPI KÖTELEZŐ SOR + a kapu státusza
| | |
|---|---|
| **`cum_30d`** | **−5,36%** (−$5 359,37) — **BREACH**, **9. kereskedési nap** |
| Gördülés | +1 (09-24): **−5,36%** · +2 (09-25): **−4,95%** |
| **Kapu-futás** | 🔴 **TOVÁBBRA SEM TÖRTÉNT MEG** — ellenőrizve mindkét gépen; a `docs/analysis/`-ban csak a 2026-06-24-i data-coverage doksi |
| **§5.1 / §5.2 döntés** | **nem született meg**; a `gate_sample.py` pinje **`68fc00e`** |
| **A kapu dátuma óta eltelt** | **1 kereskedési nap** (a review dátumán, 09-25-én már **3**) |

🟢 A pre-reg **irányadó** triggerek tiszták: `excess_10d_mean` **−0,35%**, `excess_15d_mean` **−0,25%**.
⚠️ A `sum`-olvasatok BREACH (−3,55% / −3,69%) — **D4: megfigyelés**.

📌 **Emlékeztető a 09-22-i review §C-jéből** (04-risks §11.21): két út van — **(1) a futás
lebonyolítása dokumentált dátum-eltéréssel**, vagy **(2) a kapu-dátum újra-rögzítése**.
**Mindkettő írásbeli rögzítést kíván a futás ELŐTT.** Az akkor jelzett kockázat — *„minden
további nap a 2) út felé sodródás kockázatát növeli anélkül, hogy azt valaki kimondta volna"* —
**most már materializálódik**: a kapu dátuma óta eltelt napok száma nő, döntés nélkül.
**CC nem választ; Tamás-döntés.**

## 1. Fejléc
- **Realized net: +$26,26** (gross +$27,33, komm. $1,07) — **1 exit**. 🟢 **Pozitív nap.**
- **Cumulative: −$5 167,60 (−5,17%)**.
- **Net Liq: $94 453,93** — napi Δ **−$552,39**. ⚠️ A NetLiq **nagyot esett** egy pozitív
  realizált napon: a nyitott könyv **−$576**-ot vesztett (§4).
- **Excess: +0,75%** (portfolio +0,03% vs SPY −0,72%).
- **VIX 15,31 (+7,74%)**, SPY −0,72% — risk-off.
- **Nyitott pozíciók: 5**; kitettség **40,24% → 37,48%**.

## 2. Exits (1)
| Idő (UTC) | Ticker | Kanonikus típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 19:59:41 | **IMAX** (TP1-maradék) | TIME_STOP | 53 | 52,82 → 53,32 | **+$26,26** (+0,94%) | ≈ +$40 | −$14 |

### ✅ Az IMAX HARMADIK ciklusa zárult — és mind a három pozitív
| Ciklus | Belépő | Lezárás | **Nettó** |
|---|---|---|---|
| #1 | 08-28 @ 52,48 | TP1 +$76,32 → TIME_STOP −$6,84 | **+$69,48** |
| #2 | *(ugyanaz a tétel folytatása)* | TIME_STOP 09-08 | **+$12,83** |
| #3 | 09-14 @ 52,80 | TP1 +$32,36 (09-22) → TIME_STOP +$26,26 (09-23) | **+$58,62** |
| | | **IMAX összesen** | **+$140,93** |

📌 **Az IMAX az egyetlen ticker három lezárt ciklussal — és mind a három pozitív.**
Ez **kontraszt** a visszalépés-sorozat általános képével (3 lezárt ELVN/FBP/RCI-ciklus, mind
negatív, Σ −$1 027). ⚠️ **n=3 egy tickeren, nem általánosítható (G3)** — de a D6 SIM-napirend
visszalépés-tételénél érdemes külön megnézni, mi különbözteti meg.

📌 Ezzel a **teljesen lezárt TP1-ciklusok: n=8** — 7 pozitív + 1 negatív (MANH −$25,48),
Σ **+$883,98**.

## 3. Entries (0)
Nem volt belépő. A kitettség **37,48%**.

## 4. Nyitott pozíciók (5) — 09-23 záró mark
| Ticker | Szektor | Bázis (fill) | Záró | Unrealized |
|---|---|---|---|---|
| MD | Healthcare | 26,18 | 25,86 | −$65,92 |
| EXLS | Technology | 35,51 | 34,83 | −$121,04 |
| NWBI | Fin. Services | 15,46 | 15,04 | −$281,82 |
| EQH | Fin. Services | 54,96 | 52,27 | **−$379,29** |
| **NWSA** | Comm. Services | 30,13 | 28,12 | **−$528,63** |
| **Σ** | | | | **−$1 376,70** |

🔴 **A könyv −$800,27 → −$1 376,70** (−$576,43) — **MIND AZ ÖT tétel negatív**.
A **NWSA** a legrosszabb (−$528,63, **−6,7%**) — **ma MENTAL_SL-en zárhat** (§8).
Az **EQH** (a 09-17-i visszalépés) második legrosszabb (−$379,29, −4,9%).

## 5. Ops-checklist
- ✓ **Cron-lánc**: 14:30 Phase 4-6, 15:31 submit (0 tétel), 21:40 time_stop (IMAX MOC),
  22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🔴 **D7-sor** (§0): `cum_30d` −5,36%, BREACH, 9. nap.
- 🔴 **A kapu-futás elmaradása** (§0) — **a nyitott P0** (04-risks §11.21).
- ✓ Az `exit_type` ma helyes (`TIME_STOP_MOC` a 21:40-es ablakban).

## 6. Anomáliák
- **🔴 A kapu-futás továbbra sem történt meg** (§0) — a 09-22-i P0 **nyitva**, és a késés nő.
- **📌 Az IMAX három pozitív ciklusa** (§2) — kontraszt a negatív visszalépés-ciklusokkal.
- **📌 A könyv mind az öt tétele negatív** — a 09-08-i óta az első ilyen nap.
- **✅ VÁLTOZATLAN**: §11.17 `exit_type`, §11.18 szektor-cap rés, §11.20 (TP1/stop/breakeven a
  tervezett árhoz; a trail helyes), §11.21 (a kapu-futás elmaradása), `swing_state.exits_today`,
  `commission_total`, `reconcile` csak ticker-halmaz, TP1 utáni max_hold-túlfutás,
  **FileVault**, **sync-rés**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Teljesen lezárt TP1-ciklusok** — **n=8**: 7 pozitív + 1 negatív; Σ **+$883,98**.
- **TP1 (teljes swing-éra)** — n=26, ebből 3 negatív. **MENTAL_SL** — n=8. **TRAIL_SL** — n=1.
- **Visszalépés exit után** — n=15 (11 drágább / 4 olcsóbb); **3 teljes ciklus lezárva, mind
  negatív** (Σ −$1 027,01) — szemben az **IMAX 3/3 pozitívjával** (§2).
- **Next-day MKT fill slippage** — CC-éra n=56, változatlan (ma 0 belépő).
- **Kitettség** — 37,48%.
- **Pozitív realizált nap** — **29/81** (ma igen).
- **Rally/risk-off aszimmetria** — eső nap, realized szerint +0,75% felülteljesítés.
- **TP-hit / pozitív-exit**: **1/1**. **Várt-vs-tény**: **−$14** — a 9. egyirányú, de a sorozat
  legkisebb eltérése.

## 8. Másnap (csütörtök, 09-24) — a flag szerint
**Egy MENTAL_SL 15:30-kor**: **NWSA** 263, bázis 30,13 / 09-23 záró 28,12 → **≈ −$529**.
Ez lenne a **9. MENTAL_SL**, és a könyv legnagyobb nyitott vesztesége.
*(A 09-24-i tényleges nap külön review tárgya — a `daily_equity` szerint a NetLiq
**$94 630,97**-re emelkedett, azaz **+$177,04**.)*

## 9. Freeze-sor
⚠️ A D6 prod-fagyás **formálisan 09-22-vel lejárt**, **de a feloldás a kapu utánra szólt**, és a
**futás nem történt meg** → a production-konfiguráció változtatása **továbbra sem indokolt**
(04-risks §11.21). **G1/G3–G7 élnek.** Ma **nem történt** production-kód változás.

## 10. A nap egy mondatban
Pozitív realizált nap (**+$26,26**), amellyel **az IMAX harmadik ciklusa is nyereséggel zárult —
mind a három pozitív, összesen +$140,93**, éles kontrasztban a három negatív visszalépési
ciklussal (−$1 027) —, de a **NetLiq mégis −$552-t esett**, mert a könyv **mind az öt tétele
negatívba fordult** (−$1 376,70, a NWSA egyedül −$529); a `cum_30d` **−5,36%-on, kilencedik napja
BREACH-ben**, és a **kapu-futás — a dátum elmúlta után is — továbbra sem történt meg**.
