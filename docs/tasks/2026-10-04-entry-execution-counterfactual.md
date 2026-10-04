Status: DONE
Updated: 2026-10-04
Note: EREDMÉNY — mind a 4 LMT-variáns veri a MKT-t; V1 +$2 442 (−$5 358 → −$2 915). Az adverz-szelekciós csapda valós de kicsi (6 kimaradó, +$98 vs +$2 971 ár-javulás). Minden degradálást túlél (+$2 293…+$3 558). A plan MINDIG LIMIT-et írt (669/669). Riport: docs/review/2026-10-04-sim-exec-entry-execution.md. A 4. pont — leíró mérés, NEM értékelő-motor. Független a (e) gazdasági kapu pre-regtől (docs/planning/2026-10-04-economic-gate-preregistration.md), párhuzamosan fut vele. A KITÖLTÉSI SZABÁLY ÉS A VARIÁNS-HALMAZ A FUTÁS ELŐTT RÖGZÍTVE (§3) — post-hoc variáns-bővítés TILOS.

# SIM-EXEC — a belépési végrehajtás ellenpróbája (LMT vs. next-day MKT)

## 1. A kérdés

A SIM-1 dekompozíciója szerint a belépési slippage a veszteség **26%-a**:
**−$1 958**, 41 bp a notionalra, **55/78 (71%) adverz fill**. Ez az egyetlen
**mért, mechanikai** veszteség-komponens, ami még nyitva van (a geometria ≈$0, az
exit-architektúra ≈$0).

**De a slippage megszüntetése nem ingyenes.** Egy LMT a tervezett áron nem tölt be,
amikor a papír elszalad — és **épp azok szaladnak el, amikben momentum van**. A valódi
kérdés tehát nem „mennyi slippage-et spórolnánk", hanem:

> **A megspórolt slippage több-e, mint az elszalasztott belépőkkel elvesztett P&L?**

Ez a klasszikus adverz-szelekciós csapda, és a mérés nélkül **nem tudható az előjele**.

## 2. Megközelítés

A SIM-1/SIM-2 validált harnesse (termelési `evaluate_position_eod()`), ugyanazon a
78 valós pozíción. Minden variánsban a szintek a **tényleges fillhez** horgonyozva
(a SIM-1 B konfigurációja — nincs értelme a jövőt a §11.20 defektre tervezni).

Ha egy variáns **nem tölt be**, a pozíció **$0**-val járul hozzá (nincs trade, nincs
költség) — és ez a mérés egyik fele: a kimaradás ára.

## 3. A VARIÁNSOK ÉS A KITÖLTÉSI SZABÁLY — a futás ELŐTT rögzítve

### 3.1 Variánsok

| # | Leírás |
|---|---|
| **V0** | **Baseline**: a tényleges next-day MKT fill (= SIM-1 B konfiguráció, Σ = −$5 357,89) |
| **V1** | LMT a **tervezett áron**, **DAY** (egy session) |
| **V2** | LMT a tervezett áron, **2 session**ig érvényes |
| **V3** | LMT a tervezett ár **+ 0,25·ATR**, DAY |
| **V4** | LMT a tervezett ár **+ 0,50·ATR**, DAY |

V3/V4 a kompromisszum-tengely: engedékenyebb limit → több fill, kevesebb spórolás.

**Post-hoc variáns-bővítés TILOS.** Ez leíró mérés, nem promóciós döntés, de a
variáns-halmaz utólagos bővítése akkor is „a legjobb kiválasztása" lenne.

### 3.2 A kitöltési szabály (vételi LMT `L` áron, `s` session)

```
ha  open_s <= L   ->  fill @ open_s      (a nyitás már kedvezőbb; azt kapjuk)
különben ha low_s <= L  ->  fill @ L     (a nap folyamán leérintette)
különben          ->  NINCS fill ezen a session-ön
```

- V2: ha `s`-en nincs fill, ugyanaz az `L` a következő session-ön is próbálkozik.
- Fill esetén a pozíció **belépési dátuma a fill session-je** (ez a `days_held`
  számítását is helyesen mozgatja — V2-ben a tartási ablak eggyel csúszhat).
- A szintek (`stop`/`tp1`/`tp2`) **a kapott fillhez** horgonyozva, a termelési
  multiplikátorokkal (2,0 / 1,5 / 3,0).

**A szabály konzervativizmusa kimondva:** a napi bar nem mondja meg, hogy a limit
*mikor* teljesült a napon belül, és hogy egy valós sorban álló LMT-t a `low` érintése
tényleg kitöltött volna (queue-pozíció, részteljesülés). A szabály tehát a
**fill-arányt felülbecsli** → az LMT javára torzít. Ha az LMT **így is** rosszabb,
az erős következtetés.

### 3.3 Kötelező dekompozíció

A puszta Σ-különbség nem elég — a riport **szétszedi** a két ellentétes erőt:

| Komponens | Definíció |
|---|---|
| **Ár-javulás** | Σ a betöltött pozíciókon: `(V0_fill − LMT_fill) × qty` |
| **Elszalasztott P&L** | Σ a NEM betöltött pozíciók **V0 szerinti net P&L-je** |
| **Fill-arány** | betöltött / összes |
| **Adverz-szelekciós teszt** | a kimaradt pozíciók **átlagos V0 P&L-je** vs. a betöltöttek átlaga |

Az utolsó sor a döntő: ha a kimaradók **jobbak** voltak, az LMT a nyertesekből vág ki.

## 4. Közös minta

Egy pozíció akkor használható, ha (a) a V0 feloldható, és (b) minden variánsban
**vagy nem tölt be, vagy betölt ÉS feloldható**. Ha betölt, de a bar-ablak elfogy →
**minden variánsból kiesik** (a SIM-2 közös-minta szabályának analógiája).

## 5. Implementációs terv

- [x] `tests/test_entry_execution.py` — TDD a kitöltési szabályra és a dekompozícióra
- [x] `scripts/analysis/entry_execution.py` — variánsok + dekompozíció + riport
- [x] Baseline-konzisztencia: a V0 **reprodukálja** a SIM-1 B-számát (−$5 357,89)
- [x] Riport `docs/review/2026-10-04-sim-exec-entry-execution.md`
- [x] `04-risks` §11.24

## 6. Keretezés

Post-gate, read-only, **leíró**. Nem kapu-input, nem módosít kereskedési logikát,
nem ír `state/`-be. Egy javított végrehajtási stílus élesítése **nem** következik
ebből automatikusan — ahhoz új élő pre-reg kell.

**Kapcsolódás a (e) kapuhoz:** ha a HYP-005 újrateszt `PARK_UNECONOMIC`-ot ad, ez a
mérés mondja meg, mennyit tud a végrehajtási oldal a breakeven IC-ből lefaragni —
vagyis ez a `PARK_UNECONOMIC` újratesztjének az inputja
(`docs/planning/2026-10-04-economic-gate-preregistration.md` §4).

## 7. Commit üzenet

```
feat(analysis): SIM-EXEC — a belépési végrehajtás ellenpróbája

LMT-variánsok (tervezett ár, +0.25/+0.50 ATR, DAY/2-session) a next-day MKT
baseline ellen, a SIM-1 validált harnessén. A kitöltési szabály és a
variáns-halmaz a futás előtt rögzítve; a riport szétszedi az ár-javulást és az
elszalasztott P&L-t, és kimondja az adverz-szelekciós tesztet.
```
