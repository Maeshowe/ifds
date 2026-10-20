Status: WIP
Updated: 2026-10-20
Note: **D-U1, D-U2=(B), D-U3 ELDÖNTVE** (Tamás, 2026-10-20). **D-U2 ÚJRANYITVA és (C)-re döntve** (2026-10-20, mérés alapján) — spec: §9. **D-U4 LEFUTOTT** — eredmény: `docs/review/2026-10-19-execution-wall-by-horizon.md` ERRATA, a fal ~4%-kal magasabb, a null megerősödik. **ÉLES 2026-10-20**: F-1a…F-1d + a (C) univerzum-definíció. Hátra: GICS-szektor a Wikipedia-parse-ból (§9.5/3) és az F-2/F-3/F-5 observability. A másik háromra CC javaslata a §7-ben. DÖNTÉS-task, nem bugfix. A `fail-open` a `50dfb3c` szándékos terve volt; a lecserélése viselkedés-változás egy pénzügyi kutatórendszerben, ezért Tamás döntése. A forrás-javítás (`1871ef7`) ettől függetlenül már bement.

# A néma degradálás: mi legyen a bukási mód, ha nincs elsődleges univerzum-forrás?

## 1. Miért van ez a task

A Russell-1000 Wikipedia-tábla **2026-08-12-én** kikerült a szócikkből, és ezt
**9 egymást követő heti futás** (2026-08-16 … 10-19) nem állította meg: mindegyik
WARNING-ot írt, majd **továbbment** a legacy FMP screenerre. A forrás-hibát a
`1871ef7` javította. **Ez a task a némaságról szól, nem a forrásról.**

A viselkedés nem hiba, hanem **terv**. A `50dfb3c` (2026-05-18, Day 63 §3.9) commit-üzenete
szó szerint: *„Phase 2 integration: … **Fail-open to raw screener with WARNING log**."*

## 2. Mit kóstált a némaság — mérve

| | |
|---|---|
| Csendes degradálás hossza | **64 nap** (2026-08-16 → 10-19), 9 heti futás |
| Amit a §3.9 el akart kerülni | a screener ~30%-os rotációja (percentilis-instabilitás) |
| Amit a fallback visszahozott | pontosan a screener |
| Riasztás, ami elment | heti WARNING a logba; a **23:00-as heartbeat** csak a *context korát* nézi, a *forrását* nem |
| Riasztás, ami NEM létezett | „az univerzum nem az elsődleges forrásból jött" |

### 2.1 🔴 Egy méret-alapú riasztás elvileg sem működött volna

Ez a lelet a vizsgálat legfontosabb korlátja, és megfordítja az intuíciót:

- A 08-16-i váltás **NEM** szűkítette az univerzumot, hanem **növelte**: 770 → 1454
  (`total_screened` 840 → 1553).
- A mai 730 nem a váltás, hanem **október eleji earnings-szezon + screener-szűkülés**
  (kb. 519 screener-kontrakció / 433 extra kizárás).
- Ugyanez a völgy **az index-korszakon belül is** megtörtént: 2026-07-19 → 438 név,
  2026-07-26 → 227 név, **stabil 1020-nevű tagság mellett**.

> **Következtetés:** bármilyen „ha az univerzum túl kicsi, riassz" szabály **hamis
> negatívot** adott volna a valódi regime-váltásra, és **hamis pozitívokat** minden
> earnings-szezonban. A helyes jelzés nem a méret, hanem a **forrás identitása**.

## 3. A javaslat (a panel és CC egyetért)

| | szabály |
|---|---|
| **F-1** *(átírva 2026-10-20, a (B) elfogadása után)* | **Ne bináris fail-closed legyen, hanem a TTL szemantikájának megfordítása.** Lásd §3.1 — ez jobb, mint a saját eredeti javaslatom. |
| **F-2** | A kontextusba kerüljön **`universe_provenance`** mező: `{source, fetched_at, count, degraded: bool}`. Minden downstream artefakt (Phase 4 snapshot, scan matrix, FRL attempt) ebből tudja, milyen populáción készült. |
| **F-3** | **Telegram ERROR** (ne WARNING) fallback esetén, a forrás nevével és azzal, hogy mi NEM íródott ki. |
| **F-4** | A méret-riasztás **`total_screened`-en** számoljon, a kizárásokat (earnings, SEC, inactive) **külön** jelentse — így az earnings-völgy nem kelt zajt. |
| **F-5** | A 23:00-as `check_phase13_freshness.py` a **korán kívül a provenance-t is** nézze: friss, de degradált context ugyanúgy riasztás. |

### 3.1 🔄 F-1 átírva: az index-tagságnál a **frissesség** nem a kritikus tulajdonság

Az eredeti F-1 javaslatom (ne írjuk ki a contextet fallback esetén) **túl tompa**, és a
(B) elfogadása után már jobb megoldás van. Az ok egy aszimmetria, amit a mai mérés
tett világossá:

> **Egy index-tagsági lista esetén a régiség szinte ártalmatlan, a CSERE viszont káros.**
> A Russell 1000 évente egyszer (júniusban) rekonstituálódik + negyedéves IPO-addok;
> egy háromhetes lista gyakorlatilag helyes. A mai mérés is ezt mondja: a 2026-08-04-i,
> **77 napos** cache 1018 nevet tartalmazott, a mai friss 1027-et — **4,5% eltérés
> 2,5 hónap alatt**. Ezzel szemben a csere 730 névből **377-et (52%)** olyanra váltott,
> ami nem is index-tag.

A mai kód ezt **fordítva** teszi: 7 napos TTL, és lejáratkor **cserél** ahelyett, hogy
**kinyújtaná**. Javaslat:

| | szabály |
|---|---|
| **F-1a** | Letöltési hiba esetén a rendszer a **cache-elt tagságot szolgálja ki TTL után is**, `degraded_stale: true` címkével és a `fetched_at` dátummal. |
| **F-1b** | Eszkalálódó riasztás a cache korára: **WARNING > 7 nap**, **ERROR > 45 nap** (a júniusi rekonstitúciós ablak előtt, amikor a lista valóban elavulna). |
| **F-1c** | A context kiírása **csak akkor tiltott**, ha egyáltalán **nincs** használható tagsági lista (se friss, se cache). Ekkor a stale context marad, amit a 23:00-as heartbeat már elkap. |
| **F-1d** | A screenerre való visszaesés **megszűnik** mint út: a (B) alatt a screener nem univerzum-forrás, csak enrichment. |

Mit adott volna ez a 9 hétre? **„9 hét korrektül címkézett, 4,5%-kal elavult tagság"** —
ami rendben van —, nem „9 hét csendben kicserélt populáció". És a 45 napos ERROR a
**9. hét előtt**, szeptember végén tüzelt volna.

## 4. Amit a döntés ELLEN fel kell hozni

Tisztességesen: a `fail-open`-nek volt értelme.

1. **A kutatási adatfolyam folytonossága.** Fail-closed esetén a 9 hétből **nulla**
   scan matrix születik, nem 9 hét degradált. A ma lezárt költség- és fal-mérések
   (`63,5 / 84,7 bp`, a horizont-rács) **ezen a 9 héten is** támaszkodnak adatra.
   Fail-closed mellett a swing éra utolsó harmada **üres** lenne.
2. **A kereskedés nem állt le tőle.** A degradálás ideje nagyrészt egybeesik a
   D8 leállással (10-03 óta nincs IBKR-futás), tehát pénzt nem veszítettünk rajta.
3. **A §3.9 stabilitás-célja a megvalósításban amúgy sem teljesült** — a
   `phase2_universe` a screenert **metszette** az index-unióval, és a metszet
   instabilabb volt, mint a screener önmagában (mérve: index-korszak heti panel
   226–1479, minden nap jelen lévő mag **0**; screener-korszak 1338–1824, mag **1053**).
   Vagyis a „primary" forrás visszaállítása önmagában **nem** adja meg a stabilitást,
   amiért a döntés született.

> A 3. pont miatt az F-1 nem elég: ha a metszés-alapú konstrukció eleve nem stabil,
> akkor a „primary forrásra várunk" szabály egy olyan állapotot védene, ami nem volt
> jobb. **Ezért a §5 kérdés az igazi döntés.**

## 5. 🔴 A valódi nyitott kérdés: metszet vagy önálló univerzum?

A `phase2_universe._screen_long_universe` ma: `FMP screener ∩ (S&P 500 ∪ Russell 1000)`.
Két mozgó halmaz metszete, és **mindkettő rotációját örökli**.

| alternatíva | mi lesz az univerzum | stabilitás |
|---|---|---|
| **(A) marad a metszet** | screener ∩ index-unió | a mérés szerint a **legrosszabb** |
| **(B) csak az index-unió** | S&P 500 ∪ Russell 1000 (~1026) | évi rekonstitúció + negyedéves IPO-adds → **a legstabilabb** |
| **(C) index-unió + likviditási floor** | (B), majd ár/volumen szűrő | stabil, de a floor maga rotál |

A **(B)** az, ami a §3.9 **szándékát** valójában megvalósítja: a screener azért volt
benne, hogy likviditást és aktív kereskedést szűrjön — de a Russell 1000 alsó határa
(~$700M–1B cap) ezt **definíció szerint** már biztosítja, és az `isActivelyTrading`
szűrés a per-ticker enrichmentből külön is elvégezhető.

⚠️ **A (B) következménye mérendő a döntés ELŐTT:** az univerzum ~1026-ra áll be a mai
730 helyett, ami a Phase 4 percentilis-rangokat **újraskálázza**. A már lezárt FRL
attemptek populációja ettől különbözni fog — ez **G5-érintő** kérdés (éra-szeparáció),
tehát a váltás dátuma egy **új éra-határ**, és így kell rögzíteni.

## 6. Implementációs követelmények (ha F-1…F-5 elfogadva)

1. `universe_source` mint **explicit enum** a kontextusban, nem levezetett érték.
2. Fail-closed úton a runner **ne** írjon `phase13_ctx`-t, de a Phase 1 (BMI) és
   Phase 3 (szektor) eredményét **logolja** — a diagnózishoz kell.
3. Hermetikus tesztek: a fallback-út **ne** írjon state-et; guard-teszt arra, hogy
   degradált forrás mellett a kiírás **megtagadódik** (visszavezetéssel verifikálva).
4. A `check_phase13_freshness.py` kapjon **provenance-ellenőrzést**, és a két
   riasztás-ok (stale / degraded) legyen **külön** szövegű.
5. Mentés a felülírás előtt: minden olyan futás, ami a `phase13_ctx`-t vagy a
   `universe.json`-t felülírja, előbb `state/state_backups/`-ba mentsen
   (2026-10-20-tól CC gyakorlat, lásd memória).

## 7. Döntések — CC javaslatával

| Döntés | | **CC javaslata** |
|---|---|---|
| **D-U1** | A detektálás és a bukási mód | **alpontonként, lent** |
| **D-U2** | metszet / index-unió / index+floor | ✅ **(B) — ELDÖNTVE** (Tamás, 2026-10-20) |
| **D-U3** | Új éra-határ G5 szerint? | **NEM — regime-marker helyette** (lásd §7.2) |
| **D-U4** | Ellenpróba a váltás előtt? | **IGEN, és ez legyen az első** (lásd §7.3) |

### 7.1 D-U1 — alpontonként, mert nem egy csomag

| | javaslat | miért |
|---|---|---|
| **F-2** provenance-mező | ✅ **IGEN, feltétel nélkül** | Tiszta hozzáadás, nulla viselkedés-változás, és ez teszi minden downstream artefaktot önleíróvá. Ez menjen be akkor is, ha minden más elbukik. |
| **F-3** ERROR a WARNING helyett | ✅ **IGEN** | Detektálás, nem viselkedés. Ez fogta volna el a 9 hetet. |
| **F-5** heartbeat provenance-check | ✅ **IGEN** | Ugyanaz; a heartbeat ma csak a *kort* nézi, a *forrást* nem — pedig a forrás volt a baj. |
| **F-1** (átírva: F-1a…F-1d) | ✅ **IGEN, de a §3.1 alakjában** | Az eredeti bináris fail-closed túl tompa; a TTL-megfordítás egyszerre őrzi a folytonosságot és tiltja a néma cserét. |
| **F-4** `total_screened`-alapú méret-riasztás | ⚠️ **IGEN, de utolsó prioritás** | A mérés szerint egy méret-riasztás ezt a hibát **elvileg sem** fogta volna el (a váltás NÖVELTE a számot). Más hibára jó (screener-összeomlás), nem erre. Ne ez legyen az első. |

### 7.2 D-U3 — miért NEM új éra, hanem regime-marker

Megmértem, mit kóstál egy kemény vágás a 2026-08-16-i határon (`T_eff = napok/h`,
floor 6,0):

| h | teljes éra | index-rész | screener-rész | vágás után |
|---:|---:|---:|---:|---|
| 5 | 17,2 | 10,6 | 6,6 | mindkettő tesztelhető |
| **7** | 12,3 | 7,6 | **4,7** | ⛔ **csak EGYÜTT tesztelhető** |
| **10** | 8,6 | 5,3 | **3,3** | ⛔ **csak EGYÜTT tesztelhető** |

Egy kemény éra-vágás tehát **megszüntetné a h=7 és h=10 tesztelhetőségét** — és épp a
**h=10** az, ahol a fal a legalacsonyabb (0,0233 a mért „D" végrehajtási forgatókönyvben),
vagyis ahol egy jövőbeli jelnek a legnagyobb esélye van átmenni. Egy éra-vágás a
legígéretesebb horizontot zárná el.

Ráadásul a két meglévő éra **stratégia** szerint különül el (legacy bracket vs swing);
ez itt **univerzum** szerinti különbség, változatlan stratégiával.

**Javaslat:** ne éra, hanem **`universe_regime` marker** a `frl_config`-ban (határ:
2026-08-16), a provenance-mezőben rögzítve, és **kötelező szabály**, hogy minden jövőbeli
attempt vagy (i) egyetlen regime adatán fut, vagy (ii) **kiírja a keverési arányt**.

> ⚠️ **Amit ez nem ad meg:** ez **gyengébb** garancia, mint egy igazi éra-szeparáció.
> A G5 azért létezik, hogy a keverés ne történhessen meg csendben; a marker ezt a
> *csendet* szünteti meg, a keverést magát nem tiltja. Ezt kimondom, nem szépítem —
> és a már lezárt 23 attempt keveredése amúgy sem visszafordítható (4. kísérő:
> nincs újrafuttatás verdikt-generálásért).

### 7.3 D-U4 — IGEN, és ez legyen az ELSŐ lépés

Nem csak azért, mert óvatos: **egy élő ellentmondást zár le.**

A panel szerint a tervezett univerzum visszaállítása **csökkenti** a σ_cs-t és így
**emeli** a falat. A saját közvetlen mérésem az **ellenkezőjét** adta: az index-rész
σ_cs(5) = **0,0609**, a screener-rész **0,0564** — vagyis a visszaállítás **emelné** a
σ_cs-t és **csökkentené** a falat. Ez a két állítás nem lehet egyszerre igaz, és
a fal a projekt központi száma.

A mérés **olcsó**: a lezárt éra Phase 4 snapshotjai megvannak
(`state/phase4_snapshots/*.json.gz`). Újraszámolható a percentilis-rang **csak az
index-tagokra** szűkítve, és összevethető a tényleges, lefutott rangokkal. Ez
egyszerre adja meg: (a) mennyit mozdulnak a score-ok, (b) a σ_cs igazi irányát,
(c) hogy a lezárt null-eredmények máshogy alakultak volna-e.

**Javaslat:** a D-U4 fusson le **a (B) élesítése előtt**, és az eredménye kerüljön a
falat közlő riportba (`docs/review/2026-10-19-execution-wall-by-horizon.md`) erratába,
ha a σ_cs irány az enyémmel szemben a panelt igazolja.

## 8. Referencia

- Forrás-javítás: commit `1871ef7`
- Panel: 37 ágens, 4 lencse, 23 igazolt lelet / 7 blocker (2026-10-19)
- Mérések: `docs/CHANGELOG.md` 2026-10-19 (8) és (9)
- A §3.9 eredeti döntés: commit `50dfb3c`, Day 63 outcome §3.9 (Döntés 9)

---

# §9 — A (C) IMPLEMENTÁCIÓS SPEC (D-U2 újranyitva és eldöntve: **(C)**, Tamás 2026-10-20)

## 9.1 Miért nem (B) — mérve

| | |
|---:|---|
| screener visszaad (production paraméterek) | **1965** nev |
| index-tagság | **1027** |
| ebből a screener lefedi | **879 (85,6%)** |
| **hiányzik** | **148 (14,4%)** |

A hiányzó 148 **azért** hiányzik, mert elbukik a konfigurált likviditási küszöbökön
(`universe_min_market_cap` $2B, `universe_min_price` $5, `universe_min_avg_volume` 500k).
A (B) literálisan **ezt a 148 illikvid nevet vinné be** — pont azt, amit a swing
architektúra kerülni akar. Ráadásul **nincs per-ticker enrichment implementálva**
(a docstring említi, a kód nem), tehát (B) új kódot + ~148 heti API-hívást igényelne,
ami a 2026-05-14-i rate-limit szabály szerint **élő smoke-ot** kíván.

## 9.2 A (C) definíció

```
univerzum = index-tagság ∩ { ár ≥ universe_min_price  ÉS  ADV ≥ universe_min_avg_volume }
```

A floor **ugyanazokkal a TUNING küszöbökkel** dolgozik, de **helyben** számol, nem az
FMP screener rotáló kimenetéből — így deterministikus. A **cap-küszöb elhagyva**, mert a
Russell 1000 tagság definíció szerint cap-rangsor; ezt a riportban ki kell mondani.

**Mért méretezés** (lokális 20 napos bar-ablakon, 1018 nevű tagsággal):
`tagság 1018 → floor átmegy 911, elbukik 94, nincs bar 13`.

## 9.3 🔴 ÚJ KÉNYSZER: a Mini-n NINCS bar-cache

A `research/cache/api/polygon/grouped_daily` **lokális kutatási artefakt** —
a production gépen **0 nap** van belőle (`research/` gitignore-olt, nincs syncelve).
**A floor adata tehát NEM onnan jöhet.**

A helyes forrás: a **Phase 1 már letölti** a grouped daily bar-okat a BMI-hez
(SMA25 → ~25 session). Ezt kell átadni a Phase 2-nek — **nulla új API-hívás**, tiszta
wiring. ⚠️ Ez **fázisok közötti adatfolyam-változás a production pipeline-ban**, tehát
saját design-passzt érdemel, nem egy hosszú session végét.

## 9.4 Share-class normalizálás — mérve, két külön ok

A 13 „nincs bar" név **két** csoport:

| csoport | n | ok | kezelés |
|---|---:|---|---|
| `BF-A, BF-B, BRK-B, HEI-A, LEN-B, UHAL-B` | 6 | a Polygon **dot**-alakot használ (`BRK.B`), a repo kötőjelre normalizál | **mindkét alakot próbálni** |
| `AVB, EA, EQR, LBRDA, LBRDK, MASI, WBS` | 7 | valóban nincs a bar-fájlban (0,7%) | **kizárni + számolni + logolni** |

## 9.5 Implementációs lépések (sorrendben)

1. **Phase 1 → Phase 2 bar-átadás.** A BMI-hez letöltött grouped bar-ok elérhetővé
   tétele a Phase 2-nek. Ez a kritikus és leginvazívabb lépés.
2. **`src/ifds/data/liquidity_floor.py`** (új, pure): `(bars, thresholds, lookback) → (passes, excluded_with_reasons)`.
   Dot/kötőjel variánsok kezelése. Tolerancia-alapú összehasonlítás, nem `== 0`.
3. **GICS szektor a meglévő parse-ból.** A Wikipedia tábla fejléce
   `['Company','Symbol','GICS Sector','GICS Sub-Industry']` — a szektor **ugyanabból a
   letöltésből** jön, amit már parse-olunk. A parser ma csak a Symbol kolonnát veszi.
4. **Enrichment-rés kezelése.** Ami átmegy a floor-on, de nincs screener-sora
   (cap-alapon kizárva): **kizárni, számolni, logolni** — nem lekérdezni. A rés méretét
   a production gépen meg kell mérni (lokálisan nem lehet, mert nincs ott screener-hívás).
5. **F-2/F-3/F-5 observability.** A `provenance` mezőbe a `universe_definition` is
   bekerül (`index_union_plus_floor`), így minden downstream artefakt tudja, melyik
   definíció szerint készült.

## 9.6 Amit a (C) NEM old meg

A már lezárt swing éra **nem** (C) szerint futott, tehát a 2026-08-16-i regime-határ
és a D-U3 `universe_regime` marker **változatlanul kell**. A (C) élesítése egy
**harmadik** univerzum-definíciót hoz be (index-metszet → screener → index+floor),
amit a markernek rögzítenie kell.

---

# §10 — A (C) ÉLES VERIFIKÁCIÓ (2026-10-20 18:21, production)

```
FMP screener response: 2123 raw tickers          <- csak ENRICHMENT
Swing universe loaded: 1027 symbols (S&P 500 + Russell 1000 union)
Universe (C): 898 tickers from 1027 members
  — floor excluded 118, no screener enrichment 11, inactive 0
Universe: 440 tickers (screened=898, earnings_excluded=381, sec_filing_excluded=77)
```

`1027 − 118 − 11 = 898` ✅ — a szám pontosan az, amit az árnyék-mérés megjósolt.

| | érték |
|---|---:|
| index-tagság | 1027 |
| floor kiesés | −118 |
| enrichment nélkül | −11 |
| **(C) univerzum** | **898** |
| earnings-kizárás (okt Q3 szezon) | −381 |
| SEC 10-Q/10-K | −77 |
| **context univerzum** | **440** |

A 440 és a korábbi degradált futásaim (424 / 520 / 730) közti különbség **már
értelmezhető**: a 381 earnings-kizárás a valódi októberi Q3 szezon, nem a napszak.

## §10.1 Ami ezzel lezárult

| | |
|---|---|
| a screener **összetételének** hatása | megszűnt — csak enrichment |
| a screener **napszak-függése** | megszűnt (D-V1) |
| néma populáció-csere | strukturálisan lehetetlen (F-1c/F-1d) |
| lejárt cache → screener | megszűnt (F-1a staleness-létra) |

## §10.2 Ami nyitva van

1. **GICS-szektor a meglévő Wikipedia-parse-ból** (§9.5/3). Ma a szektor a screener
   `sector` mezőjéből jön, tehát a 11 enrichment nélküli név kizárásának **egyik** oka
   a szektor. A Wikipedia-tábla fejléce `['Company','Symbol','GICS Sector',
   'GICS Sub-Industry']` — a szektor ugyanabból a letöltésből kinyerhető, és akkor a
   rés tovább szűkül.
2. **F-2/F-3/F-5 observability**: a `universe_provenance` a kontextusba, Telegram-ERROR
   a degradált úton, és a 23:00-as heartbeat provenance-ellenőrzése.
3. **D-U3 `universe_regime` marker**: a (C) élesítése egy **harmadik** univerzum-definíciót
   hoz be (index-metszet → screener → index+floor), amit a markernek rögzítenie kell.
