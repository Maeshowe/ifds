Status: OPEN
Updated: 2026-08-26
Note: [2026-10-04 frissítés] A KAPU LEZÁRULT (2026-10-03), tehát a lenti "a 2026-09-22-i
kapuig CSAK az 1-2. lépés" korlát TÁRGYTALAN — a 3. lépés (FRL-mérés) szabad. Az 1. lépés
adat-előfeltétele teljesült: a grouped_daily bar-tár folytonos 2026-02-11 → 2026-10-02
(2026-10-03-i backfill). A task STATUSA OPEN marad, de a prioritása a §3 stratégiai
döntéstől függ: ha a jelcsalád lezárul (C forgatókönyv), ez tárgytalanná válhat.
--- az eredeti Note: --- Adat-infrastruktúra a kutatási sávban. NEM érint termelési kereskedési logikát, NEM ír `state/`-be, NEM módosít `trade_plan`/`execution_plan` utat. A 2026-09-22-i kapuig CSAK az 1-2. lépés (tár + indikátor + validáció) hajtható végre; a 3. lépés (FRL-mérés) a kapu után indul. G1: minden itt keletkező mennyiség FRL-eredetű → örökre leíró és INADMISSIBILIS a kapuba. — 2026-08-26 (CC, implementáció ELŐTTI verifikáció a §6.1 fixture-ön): §5.1 LEZÁRVA (mult=√2, az 1,3766 cáfolva) · §5.2 LEZÁRVA (source=hlc3, mérve) · §5.3 ÁTÍRVA (a valódi kockázat a korrekciós ÉVJÁRAT, nem az `adjusted` flag — mérve 0,65% ticker/hó) · §6.4 verifikált referencia-implementáció · V4 tárgytalan · 0. lépés (.gitignore) hozzáadva.
# OHLCV-tár backfill + Gaussian Channel indikátor (kutatási sáv)

> ⚠️ **Keret.** Ez a task **adatot és mérőeszközt** épít, **nem stratégiát**. Nem hoz létre
> belépési/kilépési logikát, nem nyúl a Phase 4-6-hoz, nem módosít cront, ami kereskedik.
> A `docs/planning/2026-08-23-day63-post-period-analysis.md` §9 tiltása („ne indíts új
> jelcsaládot azelőtt, hogy a költségoldal rendbe kerülne") **erre nem vonatkozik**: itt
> nem jelcsalád indul, hanem a mérés előfeltétele készül el.

---

## 1. Miért

### 1.1 A kiváltó ok

A `docs/planning/2026-08-23-day63-post-period-analysis.md` §4 megállapította, hogy a kötő
korlát a **fordulatszám-implikálta költség**, és §8.2 szerint a következő kutatási kérdés a
tartási idő / végrehajtási stílus. Ehhez **napi OHLCV-történet kell**, ami jelenleg nincs.

### 1.2 Mi van meg

```
research/cache/api/polygon/grouped_daily/YYYY-MM-DD/ALL.json     ~1,49 MB/nap
```

**113 kereskedési nap, 2026-02-11 → 2026-07-24.** A Polygon `grouped-daily` végpont
kimenete: a teljes US piac napi OHLCV-je, **naponta EGYETLEN hívásból**. Az FRL v1 sávja
építette (a `research/cache/returns.parquet` 2026-07-25-i keltezésű).

Két tulajdonsága, ami miatt ez a helyes alap:

1. **Nincs kilyukasztva az IFDS-outage-ek által.** Megvan benne a 2026-04-06, 04-07,
   06-29, 06-30, 07-01, 07-02, 07-06, 07-15, 07-16, 07-22 — mind olyan nap, amikor a
   pipeline állt, de a piac ment. Piaci adat, nem pipeline-output.
2. **Természeténél fogva túlélési torzítás mentes.** A `grouped-daily` azt adja vissza,
   ami *aznap ténylegesen kereskedett* — a később kivezetett tickerek is benne vannak.
   (Ez pontosan az a tulajdonság, aminek a hiányát a SIGNUM-backtestnél #1 kérdésként
   jelöltük meg.)

### 1.3 Mi NEM alkalmas

Az `output/full_scan_matrix_YYYY-MM-DD.csv` **nem használható alapnak**. Oszlopai:

```
Ticker,Status,Reason,Total_Score,Flow_Score,Funda_Score,Tech_Score,
Strategy,Sector_ETF,Sector_BMI,Sector_Regime,Price,ATR,Sector_Name
```

| # | Blokkoló | Következmény |
|---|---|---|
| 1 | nincs High/Low | True Range nem számolható → **nincs sáv** |
| 2 | nincs Open/Close pár | a szűrő forrása (`ohlc4`/`hlc3`) nem rekonstruálható |
| 3 | 123 nap, lyukakkal | a warm-up töredéke; hiányzik 04-06, 04-07, 06-19, 07-01…07-06, 07-15, 07-16, 07-22, 08-07 |
| 4 | változó univerzum | a Phase 2 naponta újraépít → per-ticker történet ragged |
| 5 | `Price` = scan-időpont | 14:30 CEST = **08:30 ET, pre-market** — nem napi zárás |

Bármelyik önmagában kizáró. Az 5. a legalattomosabb: egy pre-market snapshotokra épített
szűrő **más idősoron** futna, mint amin a kiértékelés történik.

---

## 2. Mennyi hiányzik — számolva

A cél-indikátor 4-pólusú Gauss-szűrő, `period=144` (α = 0,09540). Egységugrásra szimulált
beállási idő:

| Hibahatár | Warm-up |
|---|---|
| 10% | 65 bar |
| 5% | 75 bar |
| **1%** | **98 bar** |
| 0,1% | 128 bar |

> ⚠️ **2026-08-26: a „meglévő 113 nap" NEM használható fel** — §5.3 (korrekciós évjárat).
> A táblázat ezért a **teljes, egy évjáratban letöltendő** ablakot mutatja.

| | |
|---|---|
| Szükséges (98 warm-up + 250 értékelhető ablak) | **348 nap** |
| **Letöltendő ablak** (NYSE-naptárral számolva) | **348 nap** — 2025-04-07 → 2026-08-25 |
| Ebből a jelenlegi cache-ben megvan (de **más évjáratban**) | 113 nap — újratöltendő |
| Nyers JSON | **0,49 GB** (mért: 1,45 MB/nap) |
| Parquet (szűkített oszlopok) | ~35 MB |
| Polygon-hívás | **348** — mért 1,4 s/hívás → **8,1 perc** |

---

## 3. Scope

### 3.1 BENNE

| # | Komponens | Mit csinál |
|---|---|---|
| A | `scripts/research/backfill_grouped_daily.py` | Polygon `grouped-daily` letöltés dátumtartományra, cache-idempotens (meglévő nap kihagy) |
| B | `scripts/research/build_ohlcv_store.py` | `grouped_daily/*/ALL.json` → egyetlen partícionált parquet |
| C | `src/ifds/research/gc_indicator.py` | tiszta függvény: OHLCV DataFrame → `filter, upper, lower, trend` |
| D | `tests/research/test_gc_indicator.py` | egységtesztek + **külső referencia-validáció** (§6) |
| E | cron: napi append | a napi `grouped-daily` letöltés + store-frissítés |

### 3.2 KÍVÜL (explicit)

- ❌ Bármilyen belépési/kilépési szabály
- ❌ `trade_plan` / `execution_plan` módosítás
- ❌ Phase 4-6 érintés
- ❌ `state/` írás
- ❌ IBKR-érintés
- ❌ Az FRL HYP-006 futtatása — **az a kapu (2026-09-22) UTÁN indul**, saját taskkal

---

## 4. Architektúra

### 4.1 Tárolási hely

A store a **kutatási sávban** él, a rsync-halmazon KÍVÜL (Mini-master, `--delete` topológia):

```
research/data/ohlcv/
  year=2025/month=03/part.parquet
  year=2025/month=04/part.parquet
  ...
  _manifest.json        # lefedett napok, sorszám, forrás-hash, build-idő
```

**Indok:** a `research/` már most a sync-halmazon kívül van (04-risks / FRL topológia), és
a store 35 MB — nem tartozik a repóba. `.gitignore`-ba.

### 4.2 Séma

| oszlop | típus | megjegyzés |
|---|---|---|
| `date` | date | kereskedési nap |
| `ticker` | string | Polygon `T` |
| `o,h,l,c` | float64 | **adjusted=true** (§5.3) |
| `v` | float64 | volumen |
| `n` | int32 | trade-count (ha elérhető) |
| `vw` | float64 | VWAP (ha elérhető) |

### 4.3 A GC-indikátor specifikációja

A `docs/planning/2026-08-23-day63-post-period-analysis.md`-hez kapcsolódó SIGNUM-rekonstrukció
alapján (Trend Radar `gc` detektor, 21 napos idősoron illesztve):

```python
# Ehlers N-polusu Gauss-szuro
beta  = (1 - cos(2*pi/period)) / (2**(1/N) - 1)
alpha = -beta + sqrt(beta**2 + 2*beta)

# rekurzio (N=4-re kibontva):
f[t] = alpha**N * src[t] \
     + 4*(1-alpha)   * f[t-1] \
     - 6*(1-alpha)**2* f[t-2] \
     + 4*(1-alpha)**3* f[t-3] \
     -   (1-alpha)**4* f[t-4]

# sav: ugyanez a szuro a True Range-re, szorzoval, SZIMMETRIKUSAN
upper[t] = f[t] + mult * ftr[t]
lower[t] = f[t] - mult * ftr[t]

trend[t] = "Green" if f[t] > f[t-1] else "Red"
```

**Paraméterek** — mind **verifikálva 2026-08-26**, egyik sem szabadsági fok:

| Paraméter | Érték | Bizonyosság |
|---|---|---|
| `poles N` | **4** | **magas** — N=3 → R² 0,99997, N=5 → 0,99999 |
| `period` | **144** | **magas** — α = 0,09539877 mellett R² = 1,000000 |
| `mult` | **1,4142 (√2)** | **magas** — maradék-illesztés, LS 1,40845 / R² 0,999987; **§5.1** |
| `source` | **`hlc3`** | **magas** — előre-futtatás 17/17 trend, max rel. hiba 3,11e-06; **§5.2** |
| sáv-szimmetria | `(upper−f) = (f−lower)` | **magas** — max eltérés 1,56e-10 a fixture-ön |

> ⚠️ Az eredeti táblázat itt `mult = 1,3766 illesztve` és `source = nem azonosítható`
> értékeket hordozott. **Mindkettő a szűrő SZINTJÉRE illesztett becslőből jött**, ami a
> nem megfigyelt warm-up hibáját elnyeli. A rekurzió **maradékára** illesztve mindkettő
> egyértelműen meghatározható — lásd §5.1 és §5.2.

---

## 5. Döntések

> **2026-08-26:** §5.1 és §5.2 **lezárva méréssel** (implementáció előtt, a §6.1 fixture-ön).
> §5.3 **átírva** — az eredeti mitigáció nem védett a valós hibaalak ellen. §5.4 változatlanul nyitott.

### 5.1 ✅ LEZÁRVA — sáv-szorzó: **√2 = 1,4142**

> **Verifikálva 2026-08-26** a §6.1 BTC-fixture-ön, implementáció előtt. Az eredeti
> „1,3766 vs 1,4142" dilemma **megszűnt**: az 1,3766 **cáfolva**.

**Miért adott az eredeti illesztés 1,3766-ot.** A becslés a `upper` **szintjére** illeszkedett.
A szint viszont ~300 megfigyelés-előtti barból származik, amit a 21 napos ablak nem lát —
az illesztés az inicializálási hibát **a szorzóba szívta be**. A helyes becslő a rekurzió
**maradékára** illeszt, amiből az inicializálás kiesik:

```
g[t] := upper[t] − f[t]
g[t] = α⁴·mult·TR[t] + 4(1−α)g[t−1] − 6(1−α)²g[t−2] + 4(1−α)³g[t−3] − (1−α)⁴g[t−4]
      ⇒ mult = (g[t] − Σ…) / (α⁴ · TR[t])
```

| TR-definíció | `mult` (LS, nulla tengelymetszet) | R² |
|---|---|---|
| `max(h−l, \|h−pc\|, \|l−pc\|)` | **1,40845** | 0,999987 |
| `h−l` | 1,40860 | 0,999988 |
| `max(h,pc) − min(l,pc)` | 1,40845 | 0,999987 |

Bar-onkénti becslések tartománya (n=17): **1,4063 – 1,4491**. A √2 = 1,41421 a tartomány
belsejében van; az **1,3766 a tartományon kívül esik** (2,3%-kal az LS-becslés alatt).
A TR-definíció **nem azonosítható** (a három variáns 1e-4-en belül egyezik) és **nem is
számít** — bármelyik választható, `max(h−l,|h−pc|,|l−pc|)` a default.

**Döntés: `mult = 1.4142` (√2), configban rögzítve.** A **V4 teszt tárgytalan** (§6.2).

**Módszertani általánosítás** (ez a rész a fontosabb): *rekurzív szűrő paraméterét a
rekurzió maradékára illeszd, ne a szűrő szintjére.* A szint tartalmazza a nem megfigyelt
warm-up teljes hibáját; a maradék nem.

### 5.2 ✅ LEZÁRVA — forrás: **`hlc3`**

> **Verifikálva 2026-08-26** a §6.1 BTC-fixture-ön. Az eredeti „nem azonosítható 21 napból"
> állítás **téves volt** — nem az ablak rövid, hanem a becslő volt rossz.

**Miért látszott azonosíthatatlannak.** Az RMSE-illesztés a `filter` **szintjére** fut, ahol
az új bar hozzájárulása 0,0083% — elvész a zajban. De az α⁴·src tag a **rekurzió maradékából**
közvetlenül kiolvasható: `implied_src[t] = (f[t] − Σ…) / α⁴`. A maradék abszolút hibája a
fixture 5 tizedesjegyén ~1e-4, tehát `src` **±1,2 pontossággal** meghatározható 64 000-es
nagyságrenden — a jelöltek pedig 100-as nagyságrendben térnek el egymástól.

| forrás-jelölt | `implied_src` átlagos eltérése | RMSE |
|---|---|---|
| **`hlc3`** | **−13,4** | **30,4** |
| `ohlc4` | +121,0 | 333,9 |
| `hl2` | +82,7 | 294,7 |
| `close` | −205,6 | 640,2 |
| `open` | +524,3 | 1390,0 |

**Megerősítés előre-futtatással** (f[0..3] a referenciából, utána a jelölt forrás hajtja a
rekurziót 17 baron — ez pontosan a V1/V2 kritérium tökéletes warm-up mellett):

| forrás | max rel. hiba | trend-egyezés | V1 (<1e-5) | V2 |
|---|---|---|---|---|
| **`hlc3`** | **3,11e-06** | **17/17** | ✅ | ✅ |
| `ohlc4` | 2,37e-05 | 16/17 | ❌ | ❌ |
| `close` | 1,24e-04 | 17/17 | ❌ | ✅ |

**Döntés: `source = hlc3`, configban rögzítve — mérve, nem konvencióból.**

⚠️ A választás **nem kozmetikai**, szemben az eredeti „anyagilag irreleváns" megjegyzéssel:
az `ohlc4` éppen a **08-22-i BTC Red→Green fordulót rontja el** (16/17). A §6.3 precizitási
aggály tehát valós, és pont a forrás-választáson keresztül harap.

### 5.3 🔴 Korrekciós **évjárat** — nem az `adjusted` flag, hanem a lekérdezés IDŐPONTJA

> **Átírva 2026-08-26.** Az eredeti megfogalmazás („ellenőrizd, hogy a cache `adjusted=true`-val
> készült-e") **hamis biztonságot adott**: az ellenőrzés átmegy, és a store mégis hibás lesz.

**A helyzet.** Az `adjusted=true` mindkét kliensben megvan és mindig is megvolt
(`src/ifds/data/polygon.py:130`, `src/ifds/data/async_clients.py:97`) — az eredeti 2. lépés
tehát talált volna egy zöld pipát és továbbengedte volna a buildet.

**A valódi hiba.** A Polygon `adjusted=true` a **lekérdezés pillanatában ismert** splitekre
korrigál, nem a mai állapotra. A meglévő 113 napos cache **2026-07-21-én** épült. Mérés
(ugyanaz a nap, cache vs. friss lekérés, 2026-08-26):

```
nap = 2026-02-11      cache(07-21) = 11 926 ticker      friss = 11 926 ticker
ELTÉRŐ ZÁRÓÁR: 78 ticker (0,65%)  — mind reverse split 07-21 és 08-26 között
  LBGJ  79,60 → 15 920,00   (200×)      WETO   0,4951 →  49,51   (100×)
  RCON   1,22 →    244,00   (200×)      NXTT   2,96   → 296,00   (100×)
  FFAI   0,65 →     97,52   (150×)      SXTC   2,49   → 199,20   ( 80×)
```

**Egy hónap alatt a tickerek 0,65%-a kapott visszamenőleges korrekciót.** Ha a hiányzó napokat
ma töltjük le és a meglévő 113-at megtartjuk, minden ilyen tickernél **200×-os szakadás
keletkezik a 2026-07-24/27 varratnál**.

**A hatás nagysága — miért ez a legrosszabb lehetséges hiba ennél az indikátornál.** Egy
korrigálatlan felfelé ugrásra a 4-pólusú Gauss-szűrő **monoton** áll be (nincs túllövés,
minden pólus valós), tehát:

> Egy korrigálatlan reverse split után a `trend` **400+ baron át megszakítás nélkül `Green`** —
> az adott ticker teljes értékelhető ablaka elvész, és a torzítás iránya **szisztematikusan
> `Green`**, azaz pont a trend-követő jel javára hamisít.

**Döntés — a mitigáció NEM ellenőrzés, hanem építési szabály:**

1. **Egy évjárat, egy menet.** A meglévő 113 nap **nem menthető meg**; a teljes 348 napos
   ablak egyetlen futásban töltendő le. Ára: 8,1 perc gépidő, 0,49 GB. Nincs miért spórolni.
2. **`_manifest.json` kötelező mezője a `fetched_at` évjárat-dátum** (nem a build-idő).
   Két store csak akkor összehasonlítható, ha az évjáratuk azonos.
3. **A napi append (§3.1/E) ugyanezt a hibát termeli folyamatosan** — minden appendelt nap
   a saját évjáratát hozza. Kell egy **újraépítési politika**: havi teljes rebuild (8 perc,
   tehát olcsó) VAGY split-esemény-detektor. Az eredeti §3.1/E ezt nem tartalmazta.
4. **A `filter`/`trend` bármely publikált értéke mellé az évjárat is kiírandó** — különben
   két futás eltérő eredménye megmagyarázhatatlan.

⚠️ **Kereszthatás:** a `research/cache/returns.parquet` (FRL v1) ugyanebből a cache-ből épült.
Ma **konzisztens**, mert egyetlen menetben készült (2026-07-21) — de ha valaha *appendelve*
frissül, ugyanezt a varratot fogja tartalmazni. Jelölendő az FRL sáv felé.

### 5.4 Univerzum-szűrés a store-ban?

A `grouped-daily` ~10 000 tickert ad naponta (ETF, ADR, warrant, preferred, OTC).

**Javaslat:** a store tároljon **mindent** (a méret így is ~35 MB), a szűrés
fogyasztói oldalon történjen. Indok: a szűrési szabály maga is kutatási változó, és
a store újraépítése drágább, mint a szűrés futtatása.

---

## 6. ⭐ Külső referencia-validáció

Ez a task legértékesebb tulajdonsága: **van egy független implementáció, amihez mérni lehet.**
A SIGNUM Trend Radar `gc` detektora ugyanezt az indikátort számolja, és 21 napra kinyert
referencia-adat áll rendelkezésre.

### 6.1 A fixture

Mentendő: `tests/research/fixtures/gc_reference_signum_2026-08.csv`

**BTC** (teljes precizitás, nagy nagyságrend):

```
date,o,h,l,c,filter,upper,lower,trend
2026-08-02,62823.65,63796.33,62806.58,63570,64654.05627,67549.40388,61758.70867,Red
2026-08-03,63570.01,64080,62300,63520,64590.92424,67464.64255,61717.20593,Red
2026-08-04,63520,64549.16,63322.01,64106.56,64533.69547,67385.66624,61681.72470,Red
2026-08-05,64106.55,65025.22,63880,64665.23,64481.83611,67311.93511,61651.73711,Red
2026-08-06,64665.24,64999,64172,64323.61,64434.89975,67242.93823,61626.86127,Red
2026-08-07,64323.61,65390.99,64166,64923.19,64392.53497,67178.27222,61606.79771,Red
2026-08-08,64923.20,65192.54,64784.19,64962.60,64354.47218,67117.53405,61591.41030,Red
2026-08-09,64962.60,65474.46,64730.08,64901.59,64320.50343,67060.37626,61580.63060,Red
2026-08-10,64901.59,65391.14,63806.27,63970.01,64290.40850,67006.54301,61574.27399,Red
2026-08-11,63970.01,64515.43,63238,63600,64263.90974,66955.76035,61572.05913,Red
2026-08-12,63600.01,64500,63310.34,63479.99,64240.69320,66907.73770,61573.64869,Red
2026-08-13,63479.99,64010,62802.27,63490.86,64220.39991,66862.15737,61578.64244,Red
2026-08-14,63490.86,63617.45,62535.24,63043.56,64202.61981,66818.64962,61586.59000,Red
2026-08-15,63043.56,63187.98,62920,63086.01,64186.92152,66776.72962,61597.11342,Red
2026-08-16,63086.01,63390,62716,62900,64172.86944,66735.89903,61609.83986,Red
2026-08-17,62900,64610.01,62751.10,64532.10,64160.12100,66695.89113,61624.35086,Red
2026-08-18,64532.11,65058.81,64027.85,64725.42,64148.46178,66656.56410,61640.35947,Red
2026-08-19,64725.42,70000,64166,69334.79,64138.03671,66618.69207,61657.38135,Red
2026-08-20,69334.78,73400,68902.22,73025.15,64129.54574,66583.79333,61675.29814,Red
2026-08-21,73027.02,79500,73027.02,78338.03,64124.44794,66554.46170,61694.43418,Red
2026-08-22,78338.03,78828.15,76500,77074.93,64124.67310,66533.43221,61715.91400,Green
```

**AAVE** (teljes precizitás, közepes nagyságrend, végig Green — ellentétes ág):

```
date,o,h,l,c,filter,upper,lower,trend
2026-08-02,90.64,93.50,90.47,92.17,85.00689631,92.90911435,77.10467827,Green
2026-08-08,89.92,92.08,89.24,91.24,87.05391534,94.86071724,79.24711344,Green
2026-08-15,86.50,87.40,86.13,86.20,88.99171568,96.56083743,81.42259393,Green
2026-08-22,122.70,129.02,111.49,126.44,90.14913111,97.31360074,82.98466149,Green
```
*(a teljes 21 napos AAVE-sor a fixture CSV-ben; itt csak minta)*

⚠️ **SHIB-et NE használd validációra.** A mikro-nagyságrendű árak a payloadban
**3 értékes jegyre kerekítve** érkeznek (`4.55e-06`), ami a filter-változást elmossa —
a SHIB `trend` 08-16-án Red→Green vált, miközben a kerekített filter végig `4.55e-06`.
SHIB kizárólag **numerikus stabilitási smoke-teszthez** használható (nincs `NaN`/`inf`).

### 6.2 Az elfogadási kritériumok

| # | Teszt | Küszöb | Állapot |
|---|---|---|---|
| V1 | `filter` illeszkedés | **rel. hiba < 1e-5** minden barra a warm-up után | ✅ **BTC-n előzetesen teljesül** (3,11e-06) |
| V2 | `trend` címke egyezés | minden bar, beleértve a 08-22-i BTC Red→Green váltást | ✅ **BTC-n 17/17** |
| V3 | `upper`/`lower` szimmetria | `abs((upper−f) − (f−lower)) / f < 1e-9` | ⚠️ lásd lent |
| ~~V4~~ | ~~szorzó-döntés~~ | — | ❌ **TÁRGYTALAN** — §5.1 lezárva (√2) |
| V5 | numerikus stabilitás | SHIB-en nincs `NaN`, `inf`, előjelváltás | nyitott |

**V1/V2 hatóköre — pontosítás.** A §6.1 BTC-blokk 21 *egymást követő* barja elegendő a
rekurzió hajtásához, ezért a V1/V2 **BTC-n már most, implementáció előtt lefutott**
(f[0..3] a referenciából mint kezdeti feltétel, utána `hlc3` hajtja 17 baron).
Az **AAVE-sor ellenben csak 4, nem egymást követő mintát tartalmaz** a task szövegében —
abból rekurziót futtatni nem lehet. Az AAVE V1/V2-höz a **teljes 21 napos sort ki kell nyerni
SIGNUM-ból** (`get-trendradar-historic`); amíg ez nincs meg, **V1/V2 BTC-only**, és ezt
a teszt nevében is jelölni kell (ne látszódjon szélesebb fedésnek, mint amilyen).

**V3 minősítése.** Ha az implementáció `upper = f + m·ftr` / `lower = f − m·ftr`, akkor a
szimmetria **konstrukcióból következik** — a V3 a saját kimenetünkre alkalmazva közel üres
teszt. Referencia-ellenőrzésként volt értelme, és **le is futott**: a §6.1 fixture-ön
max `|(u−f)−(f−lo)|/f = 1,56e-10 < 1e-9` ✅ (a SIGNUM tényleg szimmetrikus sávot használ).
Megtartható regressziós őrszemként, de ne számítson bizonyítéknak.

### 6.3 ⚠️ Precizitási követelmény

**A BTC 2026-08-22-i Red→Green váltása a filter `64124,44794 → 64124,67310`
emelkedésén múlik: +0,22 abszolút, azaz +0,00035%.**

Vagyis a `trend` címke fordulópontokon a **6. értékes jegyen dől el**. Ebből következik:

- `float64` kötelező, `float32` **tilos**
- a warm-up nem lehet rövidebb a V1 küszöbnél — egy 1%-os filter-hiba a fordulópontok
  körül **rossz trend-címkét** ad
- a V2 teszt (trend-egyezés) **erősebb kritérium**, mint a V1 (filter-illeszkedés);
  ha V1 átmegy és V2 nem, a warm-up rövid

---

### 6.4 ✅ Verifikált referencia-implementáció

> Ez a mag **lefutott a §6.1 BTC-fixture-ön** (2026-08-26) és teljesítette a V1/V2-t.
> Az 5. lépés ebből induljon — a konstansok már nem szabadsági fokok.

```python
import math

def gc_coefficients(period: int = 144, poles: int = 4) -> tuple[float, float]:
    """Ehlers N-pólusú Gauss-szűrő együtthatói. period=144, N=4 -> alpha=0.09539877."""
    beta = (1.0 - math.cos(2.0 * math.pi / period)) / (2.0 ** (1.0 / poles) - 1.0)
    alpha = -beta + math.sqrt(beta * beta + 2.0 * beta)
    return alpha, 1.0 - alpha


def gc_step(src: float, prev: list[float], alpha: float) -> float:
    """Egy bar a 4-pólusú rekurzióból. prev = [f[t-1], f[t-2], f[t-3], f[t-4]]."""
    b = 1.0 - alpha
    return (
        alpha**4 * src
        + 4.0 * b * prev[0]
        - 6.0 * b**2 * prev[1]
        + 4.0 * b**3 * prev[2]
        - b**4 * prev[3]
    )
```

**Rögzített konstansok** (mind mérve, nem választva):

| paraméter | érték | forrás |
|---|---|---|
| `poles N` | 4 | illesztés, R² 0,99999 |
| `period` | 144 | α = 0,09539877, R² = 1,000000 |
| `source` | `hlc3` | **§5.2** — előre-futtatás 17/17 |
| `mult` | `1.4142` (√2) | **§5.1** — maradék-illesztés, LS 1,40845 |
| dtype | `float64` | **§6.3** — a fordulópont a 6. értékes jegyen dől el |

**Két invariáns, amit tesztben is rögzíteni kell:**

1. `alpha**4 == 8.2827e-05` (±1e-9) — ha ez elcsúszik, a `period`/`poles` pár rossz.
2. A szűrő **egységugrásra monoton** áll be (nincs túllövés, minden pólus valós).
   Ebből következik a §5.3 „400+ bar `Green`" állítás — és az is, hogy a `trend`
   **soha nem oszcillálhat** egy sima szakaszon. Ez jó néma-hiba-detektor.

**Warm-up (egységugrás beállás, verifikálva):**

| Hibahatár | Warm-up |
|---|---|
| 10% | 66 bar |
| 5% | 76 bar |
| **1%** | **99 bar** |
| 0,1% | 129 bar |

*(A §2 eredeti 65/75/98/128 táblája indexelési off-by-one volt — a 98-as warm-up
feltételezés érdemben helyes, a 348 napos ablak bőven fedezi.)*

---

## 7. Lépések

| # | Lépés | Effort |
|---|---|---|
| **0** | **`.gitignore`: `research/data/` felvétele** — a mai `research/cache/*` sor **nem fedi** a store helyét. A build ELŐTT, különben egy `git add` a 35 MB-os parquet-et beviszi (lásd `.claude/rules/ifds-rules.md`, „explicit path-lista") | **0,1 h** |
| 1 | `backfill_grouped_daily.py` — dátumtartomány, idempotens, retry, `adjusted=true`, haladásjelzés, **`fetched_at` évjárat-bélyeg** | 1,0 h |
| 2 | ~~A meglévő 113 nap `adjusted` beállításának ellenőrzése~~ → **TÁRGYTALAN** (§5.3). Helyette: **a teljes 348 napos ablak letöltése EGY menetben**, a meglévő cache figyelmen kívül hagyásával | 0,2 h |
| 3 | Backfill futtatás: **2025-04-07 → 2026-08-25, 348 kereskedési nap** | **8 perc** (gépidő) |
| 4 | `build_ohlcv_store.py` — JSON → partícionált parquet + `_manifest.json` (**`fetched_at` kötelező mező**) | 1,0 h |
| 5 | `gc_indicator.py` — tiszta függvény; `N=4`, `period=144`, **`mult=1.4142` (§5.1)**, **`source=hlc3` (§5.2)** rögzítve, a referencia-implementáció §6.4-ből | 0,3 h |
| 6 | Fixture mentése + V1/V2/V3/V5 tesztek (**V4 kiesett**); AAVE teljes sor kinyerése SIGNUM-ból, vagy BTC-only jelölés | 1,2 h |
| 7 | Napi append cron + freshness-heartbeat + **évjárat-újraépítési politika (§5.3/3)** | 0,7 h |
| 8 | `docs/` frissítés: 04-risks §12 új alszakasz a store-ról **és a korrekciós évjáratról** | 0,5 h |
| | **Összesen** | **~5,1 h** |

**Sorrend-megkötés:** az 5-6. lépés a 2-4. nélkül is fejleszthető (a §6.1 fixture önhordó),
tehát ha a backfill elakad, a GC-implementáció és a validáció **függetlenül elkészülhet**.
A **0. lépés viszont mindennek előfeltétele.**

---

## 8. Kockázatok

| Kockázat | Valószínűség | Hatás | Mitigáció |
|---|---|---|---|
| ~~A meglévő cache `adjusted=false`~~ | — | — | ❌ **ELVETVE** — az `adjusted=true` mindkét kliensben mindig is megvolt; ez a kockázat nem létezett |
| **Korrekciós évjárat-varrat** (inkrementálisan épült store) | **BIZONYOS** | **magas** | mérve: 0,65% ticker/hó; §5.3 — egy évjárat/egy menet + `fetched_at` a manifestben + újraépítési politika a cronhoz |
| ~~Polygon rate limit a backfillen~~ | alacsony | alacsony | ✅ **mérve**: 348 hívás ≈ 8,1 perc, 1,4 s/hívás, 0 hiba; 2024-08-26-ig visszamenőleg elérhető |
| ~~A `mult` nem dönthető el a validációval~~ | — | — | ❌ **ELVETVE** — §5.1 lezárva (√2), a becslő cseréjével |
| Ticker-átnevezések a 348 napos ablakon | közepes | közepes | a store nyers tickert tárol; a mapping fogyasztói probléma, **jelölendő nyitott kérdésként** |
| A store bekerül a git-be | **közepes** | közepes | a `.gitignore` ma **csak `research/cache/*`-ot** fed, a `research/data/`-t NEM → **0. lépés** a build ELŐTT (§7); + `_manifest.json` méret-assert |
| Scope-csúszás execution felé | **közepes** | **magas** | §3.2 explicit tiltás; a HYP-006 külön task, kapu után |

---

## 9. Commit message

```
feat(research): OHLCV store backfill + Gaussian Channel indicator

Data infrastructure for the research lane. No trading logic, no state
writes, no Phase 4-6 changes.

Motivation: docs/planning/2026-08-23-day63-post-period-analysis.md §4
identified turnover-implied cost as the binding constraint. Measuring
longer-hold alternatives requires daily OHLCV history, which did not exist.
output/full_scan_matrix_*.csv is unusable (no H/L, no history, pre-market
price, ragged universe, outage gaps).

- backfill_grouped_daily.py: Polygon grouped-daily, idempotent, adjusted=true,
  single-vintage (fetched_at stamped in the manifest)
- build_ohlcv_store.py: JSON -> partitioned parquet (research/data/ohlcv/)
- gc_indicator.py: 4-pole Gaussian filter (period=144, source=hlc3, mult=sqrt(2))
  + symmetric TR band
- Validated against an independent implementation (SIGNUM Trend Radar gc
  detector, 21-day reference fixture): filter rel.err 3.1e-6, trend labels
  17/17 on BTC.

Two parameters the task listed as open decisions were settled by measurement
before implementation, by fitting the recursion residual instead of the filter
level: source=hlc3 (not unidentifiable) and mult=sqrt(2) (not 1.3766 -- that
value absorbed the unobserved warm-up error).

The store is built in ONE fetch vintage: Polygon's adjusted=true corrects for
splits known at request time, and 0.65% of tickers/month get retroactively
re-adjusted. An incrementally-built store would carry silent 200x seams, and a
4-pole Gaussian filter crossing one stays Green for 400+ bars.

Coverage: 348 trading days (2025-04-07 .. 2026-08-25). 348 API calls
(~8 min), 0.49 GB raw, ~35 MB parquet.
grouped-daily is point-in-time, hence survivorship-bias free, and is NOT
punctured by the IFDS pipeline outages (04-06, 04-07, 06-29..07-06,
07-15, 07-16, 07-22).

Refs: docs/tasks/2026-08-24-ohlcv-store-backfill.md
      docs/planning/2026-08-23-day63-post-period-analysis.md §4, §8.2
```

---

## 10. Kapcsolódó

- `docs/planning/2026-08-23-day63-post-period-analysis.md` §4 (költség-korlát), §8.2 (végrehajtási stílus mint #1 kutatási kérdés)
- `docs/master-reference/04-risks-and-open-questions.md` §12 (FRL költségmodell)
- `research/cache/api/polygon/grouped_daily/` (meglévő 113 nap)
- `research/cache/returns.parquet` (FRL v1, 2026-07-25 óta nem frissült — a store átveheti)
- `docs/tasks/2026-07-21-frl-scan-matrix-loader.md` (a v1 sáv jelenlegi betöltője)

---

## 11. A KÖVETKEZŐ task (NEM ez) — a kapu után

`HYP-006 — gc_family` regisztrálása az FRL-be, **2026-09-22 után**:

```
HYP-006  gc_family                                   Šidák m=3
  v1  gc_upper_cross      (close − upper) / ATR
  v2  gc_upper_cross_hyst v1, kilépés upper − k·ATR, k ∈ {0.5, 1.0}
  v3  gc_filter_slope     sign(Δfilter), ill. Δfilter/filter percentilis
  horizontok: h ∈ {5, 10, 20, 40}
  költség-korlát: research/cost_model.json
```

⚠️ **Pre-regisztrációs kötelezettség, az adat megnézése ELŐTT:** a `v3` szűrő
csoportkésése `N(1−α)/α = 4 × 0,9046 / 0,0954 ≈ **38 nap**`. Ezért a `v3`-nak
**h=5-ön strukturálisan nem lehet jele** — a szűrő ott még nem tud semmit.
**Csak h=20 és h=40 értékelendő a `v3`-ra**, és ezt rögzíteni kell, mielőtt bármelyik
eredmény ismert. Különben a h=5-ös null utólag „várható volt"-ként lenne magyarázható,
ami megkülönböztethetetlen a post-hoc racionalizálástól.
