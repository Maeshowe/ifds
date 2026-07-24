Status: OPEN
Updated: 2026-07-24
Note: Freeze-safe (teszt-izoláció; ha a fix a Config defenzív-copy-ig nyúl, az VISELKEDÉS-INVARIÁNS). A bugfix-session lane-je (NEM a review, NEM a FRL build). Forrás: 2026-07-23 pt_events fix melléktalálata (bugfix-session, stash-igazolt pre-existing).

# test_pipeline_e2e ordering-leak — teszt-teszt globális állapot-szivárgás

## Probléma

A `tests/test_pipeline_e2e.py` **sorrend-függően bukik**: bizonyos fájl-részhalmazokkal együtt futtatva
elbukik (a bugfix-session ~16 failt figyelt meg egy adott kombinációban), **de izoláltan ÉS a teljes
suite-ban zöld** (2175 passed). Ez a klasszikus teszt-teszt globális állapot-szivárgás ujjlenyomata: egy
másik teszt-fájl **helyben mutál** egy megosztott globális állapotot, amit az e2e a default-értékén vár —
a teljes suite-ban egy későbbi fájl visszaállítja/elfedi, izoláltan a mutáló fájl nincs jelen, csak a
köztes részhalmazban látszik.

**Nem a pt_events fix (`db95c13`) okozza** — a bugfix-session stash-eléssel igazolta, hogy a tiszta fán
(a fix ELŐTT) is megvan. **Nem a FRL-tesztek** (verifikálva 2026-07-24: `test_frl_*` + `test_pipeline_e2e`
mindkét sorrendben zöld, 175 passed). **Nem a triviális páronkénti kombinációk**
(scoring_validation_spy / swing_universe / console / sector_bmi + e2e mind zöld).

## Gyökérok-hipotézis (rangsorolva)

**#1 (elsődleges) — megosztott mutálható `defaults` dictek helyben mutálása.**
A `src/ifds/config/defaults.py` modul-szintű **mutálható** dicteket exportál: `CORE` (13), `TUNING` (72),
`RUNTIME` (454). Több teszt `.update(...)` / item-assignmenttel **helyben** mutálja a config-ot (grep:
`test_swing_universe`, `test_console`, `test_scoring_validation_spy`, `test_sector_bmi`, `test_eod_*`, …).
Ha bármelyik a megosztott modul-dictet mutálja **restore nélkül** (nem `monkeypatch`-csel, nem deep-copyn),
az `e2e` `Config`/`run_pipeline` egy szennyezett defaultot olvas → a 9 e2e-teszt együtt bukik. Ez a
[[coding-style]] immutability-szabály sértése ("SOHA ne mutálj meglévő objektumot helyben").

**#2 (másodlagos) — más modul-szintű singleton/cache** a runner-úton (lásd a pt_events precedens:
`evt = PTEventLogger()` import-idejű globál). Keresendő: `lru_cache`/`@cache`/modul-szintű kliens- vagy
kontextus-instance, amit egy teszt bepiszkít.

## Megközelítés

### 0. lépés — determinisztikus repró (a bugfix-session ismeri a kiváltó halmazt)

1. **Rögzítsd a kiváltó fájlhalmazt** a bugfix-session megfigyeléséből (a ~16 failt adó kombináció) a
   §Eredménybe — ez a repró horgonya.
2. **Tedd determinisztikussá**: `pip install pytest-randomly` (dev-dep), majd
   `pytest -p randomly --randomly-seed=<seed>` — a bukó seed rögzíthető és CI-ben újrajátszható. (A repo
   jelenleg NEM használ randomly-t → a sorrend-függés csak véletlen fájl-részhalmazokon látszik.)
3. **Szűkítsd a kiváltó fájlra** `pytest <gyanús_fájl> tests/test_pipeline_e2e.py` bisecttel a rögzített
   halmazon belül (a páronkénti már kizárta a triviálisakat — a kiváltó valószínűleg egy `.update()`-elő
   config-teszt).

### 1. lépés — a mutáló teszt azonosítása + a szivárgó állapot

A kiváltó fájlban keresd a `defaults.CORE/TUNING/RUNTIME` (vagy egy `Config`-példány) **restore nélküli**
helyben-mutációját. Bizonyítsd: a mutáció ELŐTT/UTÁN `id()` + kulcs-diff a `defaults.TUNING`-on a kiváltó
teszt futása körül.

### 2. lépés — fix (két réteg; a 2.a önmagában is elég lehet)

**2.a — teszt-oldali (kötelező):** a mutáló teszt `monkeypatch`-et vagy deep-copy-t használjon
(ne a megosztott modul-dictet írja). Ez a minimális, teszt-only javítás.

**2.b — defenzív guard (ajánlott, viselkedés-invariáns):** egy **autouse conftest fixture**, ami minden
teszt körül **snapshotol + visszaállít** `defaults.CORE/TUNING/RUNTIME`-ot (`copy.deepcopy` a setupban,
restore a teardownban). Ez strukturálisan lehetetlenné teszi az osztály JÖVŐBELI előfordulását (a
[[test-env-hygiene]] mintája a config-állapotra). Opcionálisan: a `Config` loader **defenzív-copyzza** a
defaultokat betöltéskor, hogy prod-oldalon se legyen megosztott mutálható referencia — ez viselkedés-
invariáns (a default-értékek azonosak), de nagyobb felület, ezért csak ha a #1 megerősítést nyer.

## Implementációs terv (fájlok)

- `tests/conftest.py` — autouse `defaults`-snapshot/restore fixture (2.b)
- a kiváltó teszt-fájl(ok) — deep-copy/monkeypatch a helyben-mutáció helyett (2.a)
- (opcionális, csak megerősített #1 esetén) `src/ifds/config/loader.py` — defenzív copy
- `tests/test_config_isolation.py` (ÚJ) — regressziós guard:
  - mutálj `defaults.TUNING`-ot egy teszben → a KÖVETKEZŐ teszt `defaults.TUNING`-ja érintetlen (a
    snapshot-fixture bizonyítéka)
  - determinisztikus repró a rögzített seed-del (ha pytest-randomly bevezetve): a korábban bukó seed zöld

## Tesztelés

- A rögzített kiváltó fájlhalmaz **most zöld** (a fix után).
- `pytest -p randomly` több seeden zöld (min. a korábban bukó seed).
- Teljes suite továbbra is zöld (≥2175), 0 fail, 0 warning.
- A snapshot-fixture nem lassítja érdemben a suite-ot (deepcopy 3 dict/teszt — mérd, ha aggály).

## Commit

`fix(test): izoláld a megosztott defaults-dicteket a teszt-teszt szivárgástól (e2e ordering-leak)`

## Eredmény (a végrehajtás tölti)

- Kiváltó fájlhalmaz / seed: …
- A mutáló teszt + a szivárgó kulcs(ok): …
- Fix-réteg (2.a és/vagy 2.b): …
