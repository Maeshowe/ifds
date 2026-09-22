# IFDS Daily Review — 2026-09-21 (hétfő, Day 87/63) — **AZ UTOLSÓ NAP A KAPU ELŐTT**

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ IBKR MCP connector nem elérhető — bróker-kereszt-ellenőrzés kimaradt; helyette Mini
> `reconcile_state` **silent OK**, kanonikus `pending_exits`, Polygon záró markok.

---

# 🔴 KAPU-NAP: 2026-09-22 (MA) — a belépő állapot

## A. D7 napi kötelező sor — a leállítási feltétel a kapu napján
| | |
|---|---|
| **`cum_30d` (09-21)** | **−4,86%** (−$4 861,25) — **BREACH**, **7. kereskedési nap** |
| Breach-sorozat | −3,38% → −3,38% → −3,45% → −4,26% → −4,62% → −5,15% → **−4,86%** |
| **Ma (09-22) kigördül** | 08-10, **+$110,77** → **bázis −4,97%** |
| **A mai flagek implikált várakozása** | IMAX TP1 ≈ +$65, CRBG TS ≈ −$40, MANH TS ≈ +$20 → **Σ ≈ +$45** |
| **➡️ A kapu-napi `cum_30d` várhatóan ≈ −4,93%** | **a −3,0%-os küszöb ALATT** |

🔴 **A pre-regisztrált leállítási feltétel a kapu napján FENNÁLL** — pontosan úgy, ahogy a
**D7** (2026-09-12) rögzítette: *„a trigger NEM resetelődik… a kapu napján is fennállhat."*
⚠️ **Emlékeztető a D7-ből**: ha a feltétel 09-22-én is áll, a **§3 szerint a LEÁLLÍTÁS
kritérium teljesül**; a *„DEFAULT: PAPER FOLYTATÁS"* kizárólag arra az esetre szól, amikor
**sem** élesítési, **sem** leállítási feltétel nem áll fenn.

🟢 A pre-reg **irányadó** triggerek tiszták: `excess_10d_mean` **−0,36%**, `excess_15d_mean` **−0,24%**
(küszöb −1,0%). ⚠️ `excess_10d_sum` −3,62% és `excess_15d_sum` −3,65% BREACH — **D4: megfigyelés**.

## B. A §3 élesítési kritériumok állása (tényszerű, előrejelzés nélkül)
| # | Kritérium | Küszöb | Állás (09-21) |
|---|---|---|---|
| 1 | Kumulatív paper P&L | > **+$2 000** | **−$4 939,47** (távolság $6 939,47) |
| 2 | Sharpe (60 napi) | > **0,5** | *a kapu-futásnál számolandó* |
| 3 | Pozitív excess vs SPY napok | **≥ 25** a megfigyelt napokra (D5) | *a kapu-futásnál számolandó* |

## C. ⚠️ MA ESEDÉKES, MÉG NYITOTT — §5.1 / §5.2 Tamás-döntés
A gate-protokoll **§6/3**: *„előbb a minta-definíció és a kizárások fixálása → **utána** a
futtatás. A futás után a mintán nem módosítunk."*

- **§5.1** — a **részleges-outage** kritérium (a 08-21-i eset: volt `daily_metrics`, de nem futott
  a Phase 4-6 és nem volt belépő).
- **§5.2** — az **EQH/DLB** besorolása (2h21m-es, outage okozta késés — napon belüli, míg az
  eddigi §5.2-esetek nap-léptékűek).

**Mindkettő `gate_sample.py`-módosítást és ÚJ PINT kíván** (jelenlegi: **`68fc00e`**).
📌 **Ha ma nem születik döntés**, a kapu-futás a **jelenlegi, nem véglegesített §5-listával**
megy — ez önmagában legitim (a lista 08-18 óta „lezárt"), **de a két nyitott kérdés akkor
megválaszolatlanul marad, és utólag már nem nyúlhatunk a mintához.**

---

## 1. Fejléc
- **Realized net: −$199,47** (gross −$198,28, komm. $1,19) — **1 exit**.
- **Cumulative: −$4 939,47 (−4,94%)** — új mélypont.
- **Net Liq: $95 726,58** — napi Δ **−$158,61**.
- **Excess: −1,75%** (portfolio −0,20% vs SPY **+1,55%**) — 🔴 **a swing-éra LEGNAGYOBB
  egynapos lemaradása** (előző rekord: −1,52%, 09-17 — négy ülése).
- **VIX 14,77 (−0,27%)**, SPY **+1,55%** — erős rally.
- **Nyitott pozíciók: 7**; kitettség **39,58% → 48,41%**.

## 2. Exits (1)
| Idő (UTC) | Ticker | Kanonikus típus | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|---|
| 19:59:41 | **TS** | TIME_STOP | 137 | 57,41 → 55,95 | **−$199,47** (−2,54%) | ≈ −$156 | −$43 |

⚠️ **A becslés HETEDIK egymást követő napja alulbecsüli a veszteséget**:
−$64 / −$172 / −$29 / −$171 / −$202 / −$198 / **−$43**. **7/7 azonos irány.**
📌 A **TS** teljes ciklusa (09-11 belépő, +0,83% adverz fill → 09-21 TIME_STOP): **−$199,47**.

## 3. Entries (2)
| Ticker | Qty | Planned→Fill | Slippage | Megjegyzés |
|---|---|---|---|---|
| **NWBI** | 671 | 15,46 → **15,46** | **0,00%** | **Visszalépés** (09-02 TIME_STOP @ 15,44 → +0,13%) |
| EXLS | 178 | 35,15 → 35,51 | +1,02% (adverz) | új tétel |

📌 A **NWBI fillje pontosan a tervezett áron** — a CC-éra első **0,00%**-os fillje (n=55).
**Visszalépés-sorozat n=14** (11 drágább / 3 olcsóbb).
🟡 **`sector_cap_proximity` flag tüzelt**: **Financial Services 26,1%** (> 25%, cap 30%) —
a CRBG + EQH + NWBI együtt. *(§11.18: a Phase 6 cap előretekintő, a flag nem.)*

## 4. Nyitott pozíciók (7) — 09-21 záró mark
| Ticker | Szektor | Bázis (fill) | Záró | Unrealized |
|---|---|---|---|---|
| **IMAX** | Comm. Services | 52,80 | 54,04 | **+$130,45** |
| MANH (TP1 után) | Technology | 207,82 | 209,35 | +$19,89 |
| CRBG | Fin. Services | 34,97 | 34,80 | −$39,95 |
| EXLS | Technology | 35,51 | 35,26 | −$44,50 |
| NWBI | Fin. Services | 15,46 | 15,30 | −$107,36 |
| NWSA | Comm. Services | 30,13 | 29,70 | −$113,09 |
| EQH | Fin. Services | 54,96 | 53,87 | −$153,69 |
| **Σ** | | | | **−$308,25** |

A könyv **−$383,82 → −$308,25**; **2/7 pozitív**. Az **IMAX** (+$130,45) **ma TP1-en zárhat**.

## 5. Ops-checklist
- ✓ **Cron-lánc**: 14:30 Phase 4-6, 15:31 submit (NWBI, EXLS), 21:40 time_stop (TS MOC),
  22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🔴 **D7-sor** (§A): `cum_30d` −4,86%, BREACH, 7. nap.
- 🟡 **`sector_cap_proximity`** — Financial Services 26,1%.
- ✓ **Az `exit_type` ma HELYES** (`TIME_STOP_MOC` a 21:40-es ablakban).

## 6. Anomáliák
- **🔴 A leállítási feltétel a kapu napján fennáll** (§A) — a D7-ben rögzített forgatókönyv.
- **🔴 A realized-olvasat legnagyobb egynapos lemaradása** (−1,75%) — egy +1,55%-os rally-napon,
  ahol a portfólió −0,20%-ot realizált. *(A §D3/M korlát szerint ez részben mechanikus: a
  realizált a napi exitre szűkül, az index a teljes piacra.)*
- **⚠️ A becslés 7/7 egyirányú tévedése** (§2).
- **📌 Első 0,00%-os fill** (NWBI) az 55 elemű CC-éra slippage-sorozatban.
- **✅ VÁLTOZATLAN**: §11.17 `exit_type`, §11.18 szektor-cap rés, §11.20 (TP1/stop/breakeven a
  tervezett árhoz; a trail helyes), `swing_state.exits_today`, `commission_total`,
  `reconcile` csak ticker-halmaz, TP1 utáni max_hold-túlfutás, **FileVault**, **sync-rés**.

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Visszalépés exit után** — **n=14** (11 drágább / 3 olcsóbb); 3 teljes ciklus lezárva, mind negatív.
- **Next-day MKT fill slippage** — CC-éra **n=55** (+NWBI **0,00%**, +EXLS +1,02%):
  **40 adverz / 15 kedvező** (72,7%).
- **TP1 (teljes swing-éra)** — n=25, 3 negatív. **MENTAL_SL** — n=8. **TRAIL_SL** — n=1.
- **Kitettség** — 48,41%; **Financial Services 26,1%** (flag-küszöb felett).
- **Pozitív realizált nap** — 28/79 (ma nem).
- **Rally/risk-off aszimmetria** — erős rally-nap, **−1,75% lemaradás (rekord)**.
  Sorozat: **16** rally-lemaradás vs 15 eső-napi felülteljesítés.
- **TP-hit / pozitív-exit**: **0/1**. **Várt-vs-tény**: **−$43** (7. egyirányú).

## 8. MA (kedd, 09-22) — a KAPU napja
**Három exit**:
| Idő | Ticker | Típus | Qty | Bázis / 09-21 záró | `várt` |
|---|---|---|---|---|---|
| 15:30 | **IMAX** | **TP1** (105→53) | ~52 | 52,80 / 54,04 | **≈ +$65** |
| 21:40 | CRBG | TIME_STOP | 235 | 34,97 / 34,80 | ≈ −$40 |
| 21:40 | MANH | TIME_STOP | 13 | 207,82 / 209,35 | ≈ +$20 |
| **Σ** | | | | | **≈ +$45** |

📌 A **MANH TIME_STOP** a §11.20-eset ciklusának lezárása lenne: TP1 −$13,89 (09-15) + ≈ +$20 →
**≈ +$6 nettó** — a legkisebb TP1-ciklus-eredmény eddig.

**A kapu-futás teendői** (gate-protokoll §6, §8/E, §8/F):
1. **§5.1/§5.2 döntés → esetleges `gate_sample.py` módosítás + ÚJ PIN** — **a futás ELŐTT** (§C).
2. A futás a **pinelt `c5e9ed0` + `gate_sample.py` (`68fc00e` vagy az új pin)** eszközzel, egyszeri.
3. **§8/F — KÖTELEZŐ**: a kapu-riport **szó szerint** rögzítse, hogy **2026-09-11 óta
   pre-reg leállítási feltétel él**, a `cum_30d` akkori (−3,38%) és kapu-napi értékével.
4. **§8/E**: a **§D3/M** korlát és a **§D3/P** UW-proveniencia mondat idézése.
5. **G1/G3**: a `signal_attribution` **leíró**; a leállítási kérdéshez **nem** input.
6. ⚠️ **A `docs/analysis/` sync-rés** (08-18-i finding): a kapu-riport **a Minin** készüljön,
   vagy `--out-dir` a sync-halmazon kívülre — különben a következő sync törli.

## 9. Freeze-sor
🔓 Freeze feloldva 08-17 — **D6: prod FAGYVA 2026-09-22-ig** (azaz **MA LEJÁR**); **D7: a breach
nem indok paraméter-változtatásra.** G1/G3–G7 élnek. Ma **nem történt** production-kód változás.

## 10. A nap egy mondatban
Az utolsó nap a kapu előtt egyetlen max_hold-exittel (**−$199,47**) új mélypontra vitte a
kumulatívat (**−$4 939,47**), és egy **+1,55%-os rally-napon a realized-olvasat −1,75%-os
lemaradást mért — a swing-éra rekordja** — miközben a **`cum_30d` −4,86%-on, hetedik napja
BREACH-ben** áll, és a kapu-napi bázis **−4,97%**: a **pre-regisztrált leállítási feltétel a
kapu napján fennáll**, pontosan úgy, ahogy a D7 rögzítette — **a §5.1/§5.2 döntés pedig ma,
a futás előtt esedékes.**
