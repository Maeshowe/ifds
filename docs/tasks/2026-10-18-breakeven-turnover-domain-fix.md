Status: DONE
Updated: 2026-10-18
Note: KÉSZ. A javasolt netting-képletemet 3 független deriváció CÁFOLTA (ingyenebédet gyártott volna); a helyes fix egyszerűsítés: cost = (252/h)·2c, HL-mentes. Funda breakeven 0,0017 -> 0,2786. Verdikt-invariancia: 0/23. Értékelő-motor fix. A pre-reg forrás a FRL-spec §5.3 („turnover-becsléssel RANK-VÁLTOZÁSBÓL") és a motor saját docstringje („one round trip per half-life, THE HORIZON over which the ranking re-orders"). A motor mindkettőt sérti, amikor h ≠ HL. A ház szabálya szerint ilyenkor a MOTOR a hibás.

# `breakeven_ic` domain-hiba — a költség a bomlási, az alfa a rebalansz frekvencián

## 1. A hiba

```python
# frl_ic.py — két független helper, semmi nem köti őket össze
gross = |IC| * sigma_cs * (252/h)  * 1e4      # alfa a REBALANSZ frekvencián
cost  =          (252/HL) * 2 * c             # költség a BOMLÁSI frekvencián
=> breakeven_ic = (h/HL) * 2c / (sigma_cs * 1e4)
```

A `breakeven_ic` **a h/HL hányadossal skálázódik**, tehát tetszőlegesen hajtható pusztán
a két frekvencia széthúzásával. **Verifikálva** (c=83,5 bp, σ_cs≈0,06, h=5):

| Blokk | HL (nap) | h/HL | motor breakeven | mit jelent valójában |
|---|---:|---:|---:|---|
| Flow | 0,4 | **12,5** | **3,79** | a képlet **12,5 round tripet** számol egy **5 napos** tartáson belül |
| Tech | 2,8 | 1,79 | 0,4881 | 1,8 round trip 5 nap alatt |
| aggregát | 9,9 | 0,51 | 0,1406 | — |
| Funda | 799,8 | **0,006** | **0,0017** | a tábla legdegeneráltabb cellája |

**Reductio:** HL=10 000 nap (lényegében statikus címke, nulla re-ranking) → breakeven
**0,00056** h=20-on. A képlet szerint egy fix tiltet évi 12,6×-szer lehet kereskedni
~nulla költségen.

**A hiba pontos alakja:** a forgás **nem haladhatja meg a rebalansz-frekvenciát.**
A `252/HL` meghaladja a `252/h` plafont, valahányszor **HL < h** — pontosan a Flow és a Tech.

## 2. A pre-reg forrás (a házszabály 1. kötelező kísérője)

**Nem új modellt vezetek be — a motort a már rögzített szöveghez igazítom.**

1. **FRL-spec §5.3:** *„A rövid half-life önmagában nem elutasítás: **turnover-becsléssel
   (rank-változásból)** … szembesítendő."* A spec **rang-változásból** származtatott
   forgást ír elő. A motor ehelyett egy zárt alakú rövidítést implementált.
2. **A motor saját docstringje:** *„One full round trip is assumed per half-life (**the
   horizon** over which the cross-sectional ranking substantially re-orders)."* A zárójel
   **azonosítja a half-life-ot a horizonttal** — vagyis a képlet csak **h = HL** mellett
   érvényes. A motor nem kényszerítette ki ezt a feltételt.

→ Mindkét forrás a rang-változás-alapú forgást mondja; a motor eltér. **A motor a hibás.**

## 3. A javítás

```
turnover_per_rebalance = 1 - rho^h = 1 - 2^(-h/HL)     # a rang-változás hányada (spec §5.3)
annual_one_way_turnover = (252/h) * turnover_per_rebalance
annual_cost_bps         = annual_one_way_turnover * 2 * c
```

Határesetek (ezért helyes):

| Eset | Viselkedés |
|---|---|
| HL → 0 (teljesen zajos faktor) | `1 - 2^(-∞) → 1` → forgás = **(252/h)**, azaz a rebalansz-plafon. **Nem léphető túl.** |
| HL → ∞ (statikus címke) | `1 - 2^(-h/HL) → h·ln2/HL` → költség → **(252·ln2/HL)·2c**, azaz a régi képlet ~0,69-szerese: a „round trip per half-life" intuíció **a lassú limitben helyes volt** |
| h = HL | forgás/rebalansz = 0,5 → a ranking fele fordult meg; józan |

**A régi képlet tehát nem „teljesen rossz", hanem egy határeset-közelítés**, amit a motor
a teljes tartományra alkalmazott.

## 4. ⚠️ A GROSS oldal — amit NEM javítok, de kimondok

A `gross = |IC|·σ_cs(h)·(252/h)` a **várható hozamra** helyes akkor is, ha a periódusok
korreláltak (a korreláció a **szórást** csökkenti, nem a várható értéket). **De** a
Grinold-féle breadth-érv szerint egy 99,6%-ban azonos portfólió **nem ad 50,4 független
fogadást évente** — tehát a `net_annual_bps` egy **várható-hozam** szám, **nem
kockázat-korrigált**.

**Ezt dokumentálom, nem átírom:** a kockázat-korrekcióhoz IR/Sharpe kellene, ami új
modellezési döntés — a házszabály szerint nem kalibrálható független forrásból, tehát
nem vezetem be. A `CostedView` docstringje és a riport kiírja a korlátot.

## 5. Kötelező kísérők (házszabály 2–4)

- **Érzékenység:** a verdikt-stabilitás a mért négy blokkon és egy h ∈ {1..60} ×
  HL ∈ {0,4..800} rácson kiírva. A javítás **egyetlen meglévő verdiktet sem mozdíthat**.
- **Regressziós teszt egy KORÁBBI, megerősített verdiktre:** a HYP-005/006/007/008 karok
  mind **statisztikai** KILL-ek — a (e) gazdasági kapuig **el sem jutottak**, tehát a
  javítás rájuk definíció szerint nem hat. Ezt teszt rögzíti.
- **Nincs újrafuttatás verdikt-generálásért:** a 23 ledger-sor érintetlen.

## 6. Implementációs terv

- [x] Független derivációs panel a képletre (3 szög + adverzariális támadás) — **a kód előtt**
- [x] `tests/test_frl_ic.py` — TDD: határesetek, plafon, monotonitás, negatív ρ, verdikt-invariancia
- [x] `frl_ic.implied_turnover_cost_bps(half_life, cost, horizon)` — horizont-tudatos
- [x] `costed_view` docstring: a breadth-korlát kimondva
- [x] Hívási hely (`run_frl_batch.py`) + a (e) kapu `EconomicView` újraszámolása
- [x] Érzékenységi tábla a riportba
- [x] `research/cost_model.json` commitolása (eddig uncommitted, és ez a bemenet)
- [x] `04-risks` §11.28 + FRL-spec §5.3 javítás + CHANGELOG

## 7. Commit üzenet

```
fix(research): breakeven_ic domain-hiba — a forgás nem haladhatja meg a rebalanszt

A motor a költséget a bomlási (252/HL), az alfát a rebalansz (252/h) frekvencián
számolta, így a breakeven_ic a h/HL hányadossal skálázódott. Pre-reg forrás:
FRL-spec §5.3 (rang-változásból becsült forgás) és a motor saját docstringje
(„one round trip per half-life, THE HORIZON over which the ranking re-orders").
```
