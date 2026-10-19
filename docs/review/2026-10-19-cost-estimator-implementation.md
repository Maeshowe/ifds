# A költség-becslő cseréje — implementációs riport

**Dátum:** 2026-10-19
**Pre-reg:** `docs/planning/2026-10-19-cost-estimator-amendment.md` **D-C1…D-C4** (jóváhagyva
2026-10-19) + ugyanannak **ERRATA D-E1…D-E6** (jóváhagyva 2026-10-19)
**A (e) kapu slot-cseréje:** `docs/planning/2026-10-04-economic-gate-preregistration.md` **§9**
**Teszt:** 2418 → **2435 passing**, 0 fail

---

## 0. LEFEDETTSÉG-FEJLÉC (a 2026-10-04-i szabály szerint kötelező, nem feltételezve)

| oldal | n láb | napok | ablak | forrás | notional |
|---|---:|---:|---|---|---:|
| **belépés** | **89** | 55 | 2026-05-22 … 2026-09-22 | 78 `daily_metrics` + **11 broker-backfill** | $549 562 |
| **kilépés** | **108** | 59 | 2026-06-03 … 2026-09-30 | 108 `daily_metrics` | $512 246 |

> ⚠️ **A két ablak nem azonos, és ezt nem hallgatjuk el.** A belépési rögzítő az első 13
> swing-session alatt nem működött (ERRATA §E-4). A D-E1 döntés nyomán 11 láb
> visszanyerve a `slippage_backfill_map.json` broker-autoritatív IBKR BUY filljeiből;
> a maradék kettő a bar-egészség-ellenőrzésen akadt fenn, és a kizárás **ki van írva**
> a modell `excluded` mezőjébe. Kizárt lábak: belépés 6, kilépés 11.

---

## 1. A becslő

```
belépés (BUY)   adverz = a nyitás FÖLÖTT tölt   →  (fill − open) / open       notional-súlyozott
kilépés (SELL)  adverz = az ígért ár ALATT tölt →  (ref − fill) / ref          súlyozatlan
round_trip      =  c_entry + c_exit                                           NEM 2·c_entry
breakeven_ic    =  round_trip / (σ_cs · 10⁴)
```

A kilépési referenciát az **ordertípus** adja: MOC → hivatalos záró, csengő utáni market →
nyitó. Besorolatlan akció **nem kap** alapértelmezést, hanem kizáródik — egy új exit-akciót
tudatosan kell besorolni.

**Súlyozás (D-E4):** a §5 betűje szerint — belépés súlyozva, kilépés nem. A két tag így
szigorúan véve nem ugyanaz az estimand (dollár/dollár vs. dollár/megbízás); az eltérés
**konzervatív**, és a „mindkettő súlyozva" változat lent érzékenységként szerepel.

---

## 2. Az eredmény

| | belépés | kilépés | round trip | **breakeven (σ=0,06, h=5)** |
|---|---:|---:|---:|---:|
| **pontbecslés** | +40,32 | +23,20 | **63,52 bp** | **0,1059** |
| **egyoldalas 95% felső korlát** (kötő) | +52,20 | +32,53 | **84,73 bp** | **0,1412** |
| *a régi motor (2 × medián\|terv→fill\|)* | *83,5* | *—* | *167,0 bp* | *0,2783* |

A felső korlát **nap-klaszterezett bootstrap** (egység: kereskedési nap, B = 20 000,
mag = 20261019, egyoldalas 95%) — mind a négy konstans a `frl_config.py`-ban **regisztrálva**,
mert a jóváhagyott szöveg ezeket nyitva hagyta (ERRATA §E-7). A modell **bitre
reprodukálható**: két egymás utáni build azonos.

### 2.1 Mennyi ebből a pre-reg táblájához képesti eltérés

| | pre-reg §5 tábla | szállított |
|---|---:|---:|
| belépés pont | 48,3 | **40,32** |
| belépés felső korlát | 64,3 | **52,20** |
| kilépés pont | 23,2 | **23,20** ✅ |
| kilépés felső korlát | 31,7 | **32,53** |
| **fal** | 0,1192 / 0,1600 | **0,1059 / 0,1412** |

A belépési létra, tételesen: `48,3 (publikált, súlyozatlan) → 46,9 (a §5 saját súlyozásával)
→ 45,3 (fill-in-bar szűrő) → 40,3 (a 11 visszanyert láb, D-E1)`. Az első két lépés **nem a
motor eltérése a pre-regtől, hanem a pre-reg táblájáé a saját szabályaitól** (ERRATA §E-2):
a §5 képlete notional-súlyozást ír elő, a tábla súlyozatlan átlagot közölt; a §4 egyoldalas
95%-ot ír elő, a tábla kétoldalas 97,5. percentilist. A motor a **szöveget** implementálja.

> **A fal minden lépésben lefelé mozdult.** Ezt előre kimondtam a jóváhagyás kérésekor, és
> itt is kimondom: a csere a PROMOTE-ot kapuzó küszöböt **0,2783 → 0,1412-re**, azaz
> **49%-ára** viszi. A mért `|IC| < 0,009` ettől még mindig **~16×** alatta van.

### 2.2 Érzékenységek (mind a modellbe írva, nem csak ide)

| változat | belépés | kilépés | round trip | breakeven |
|---|---:|---:|---:|---:|
| **szállított** | 40,32 | 23,20 | **63,52** | **0,1059** |
| kilépés is notional-súlyozva | 40,32 | 18,62 | 58,94 | 0,0982 |
| belépés backfill nélkül (D-E1 előtt) | 45,32 | 23,20 | 68,52 | 0,1142 |
| **MOO belépő** (D-C4, production fix) | 0 | 23,20 | **23,20** | **0,0387** |

---

## 3. Verdikt-bizonyítás — a régi terv ÜRES volt, ezért kicserélve (D-E6)

A §6 eredeti terve: „futtasd le mind a 23 ledger-sort a régi és az új modellel, 0/23".
**Robbanó sentinel `EconomicView`-val mérve 0/23 sor éri el a (e) kaput** — mindegyik a
`bh_pass = False`-on akad el, a kapu soha nem dereferálódik. A 0/23 tehát **bármilyen**
költségszámra igaz, NaN-ra és negatívra is: semmit nem bizonyít. A §6 indoklása ráadásul
**hamis** volt (azt mondta, az éra-baron buknak; négy sor — A-0003/4/7/8 — átlépi a bart).

A helyére három külön állítás került (`tests/test_cost_estimator_invariance.py`, 14 teszt):

1. **A történeti verdiktek változatlanok.** A négy bart átlépő sor a régi sávval, az új
   sávval és sáv nélkül **azonos** verdiktet ad. A sorok **inline** vannak rögzítve, nem a
   `research/attempt_ledger.jsonl`-ből olvasva — az élő kutatási state, és egy abból olvasó
   teszt ezen a gépen lenne zöld.
2. **Pozitív kontroll.** `bh_pass = True` mellett a kapu **elérhető** (a sentinel robban), és
   egy ingyenes költségmodell `PROMOTE`-ot, egy irreális pedig `PARK_UNECONOMIC`-ot ad.
   Enélkül az 1. pont egy halott motorral szemben is átmenne.
3. **Az új sáv lazább — kimondva.** `|IC| = 0,12`-nél h=5-ön a verdikt
   `PARK_UNECONOMIC → INCONCLUSIVE_ON_COST`.

**Szabotázs-ellenőrzés:** a kaput költség-vakká tettem (`if True` a küszöb-összehasonlítás
helyén) → **4 teszt bukik**. A bizonyítás tud bukni.

### 3.1 A régi verdiktek és az emberi döntések

A négy sor mindegyike `decision_source: human`. Az A-0007/A-0008 auto-KILL volt és Tamás
2026-07-24-én PARK-ra írta felül; az A-0003/A-0004 emberi megerősítésű KILL 07-21-ről.
A mai motor ugyanezekre a számokra `PARK_UNTIL_SWING_POWER`-t adna, mert a **T_eff-adekvácia
kapu** (`079e4a1`, 2026-07-25) **később** készült. Ez nem ellentmondás: a ledgert verdikt-
generálásért **nem futtatjuk újra** (házszabály 4. kísérő), a régi sorok a régi verdikten
maradnak. A teszt ezt a kettősséget explicit rögzíti.

---

## 4. Házszabály-kísérők

| | |
|---|---|
| **1. pre-reg forrás** | commit-üzenet + kódkomment: amendment D-C1…D-C4 + ERRATA D-E1…D-E6; a slot-cseréé a 10-04-i (e)-kapu pre-reg §9 |
| **2. érzékenység** | §2.2 négy változata + a bootstrap-konstansok regisztrálva; a `MIN_ROUND_TRIP_BPS = 1.0` degeneráció-padló tolerancia-alapú |
| **3. regressziós teszt** | `tests/test_cost_estimator_invariance.py` — szabotázzsal verifikálva |
| **4. nincs újrafuttatás** | a 23 ledger-sor érintetlen; a `cost_model.json` újraépült, a ledger nem |

---

## 5. Amit a csere mellett javítani kellett

- **Hermetikusság.** A kétoldalas becslő három production-fát olvas (daily metrics, pending
  exits, Polygon bar-cache). A `build_cost_model` minden útvonala injektálható lett, a
  `run_batch` kapott egy `cost_model=` paramétert, és a batch-tesztek fixture-t adnak be.
  Előtte: a suite 32 s és **felülírta a `research/cost_model.json`-t**; utána: 9,5 s és a
  `research/` mtime-ja a futás után **változatlan**.
- **Séma-őr.** A `load_cost_model` **visszautasít** egy v1 modellt ahelyett, hogy
  adaptálná — a v1 `cost_bps_per_side`-ja ugyanaz a típus, más jelentéssel, és az új motor
  round tripként terhelné, azaz feleannyit.
- **Paraméter-átnevezés.** `as_traded_cost_bps(horizon, cost_bps_per_side)` →
  `(horizon, round_trip_cost_bps)`. Egy azonos típusú, csendben jelentést váltó argumentum
  az egyetlen hiba, amit a hívó nem lát; ezért nem újrahasználtam a nevet.

---

## 6. Ami nyitva marad

- **A MOO belépő (D-C4)** production-javítás, nem ez a commit. Hatása a falra:
  **0,1059 → 0,0387**, a mai motorhoz képest **7,2×**.
- **A `deflate()` NaN családi p-k** (4 a 10-ből) felfújják a BH `m`-jét 6-ról 10-re, azaz
  konzervatív irányba. Backlog-tétel, nem verdikt-érintő.
- **A fill-in-bar tolerancia** (`0,005`) regisztrálva és érzékenységgel közölve, de
  független forrásból kalibrálva **nincs** — ha egyszer kötővé válik, az kell hozzá.
