Status: OPEN
Updated: 2026-10-20
Note: DÖNTÉS-task, nem bugfix. A `fail-open` a `50dfb3c` szándékos terve volt; a lecserélése viselkedés-változás egy pénzügyi kutatórendszerben, ezért Tamás döntése. A forrás-javítás (`1871ef7`) ettől függetlenül már bement.

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
| **F-1** | A `phase13_ctx` **kiírása tilos**, ha az univerzum nem az elsődleges forrásból jött (`universe_source != primary`). A stale context **jobb**, mint egy csendben kicserélt populáció — a stale-t a 23:00-as heartbeat már most elkapja, a kicserélt populációt semmi. |
| **F-2** | A kontextusba kerüljön **`universe_provenance`** mező: `{source, fetched_at, count, degraded: bool}`. Minden downstream artefakt (Phase 4 snapshot, scan matrix, FRL attempt) ebből tudja, milyen populáción készült. |
| **F-3** | **Telegram ERROR** (ne WARNING) fallback esetén, a forrás nevével és azzal, hogy mi NEM íródott ki. |
| **F-4** | A méret-riasztás **`total_screened`-en** számoljon, a kizárásokat (earnings, SEC, inactive) **külön** jelentse — így az earnings-völgy nem kelt zajt. |
| **F-5** | A 23:00-as `check_phase13_freshness.py` a **korán kívül a provenance-t is** nézze: friss, de degradált context ugyanúgy riasztás. |

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

## 7. Mit kérek Tamástól

| Döntés | |
|---|---|
| **D-U1** | F-1…F-5 (fail-closed + provenance + ERROR + `total_screened`-alapú méret-riasztás + heartbeat-kiterjesztés) — **elfogadva / nem** |
| **D-U2** | A §5 kérdés: **(A) metszet marad / (B) csak index-unió / (C) index + likviditási floor** |
| **D-U3** | Ha (B) vagy (C): a váltás dátuma **új éra-határ**-ként rögzítendő (G5) — **igen / nem** |
| **D-U4** | Mérjük-e meg a (B) hatását a Phase 4 percentilis-rangokra **a váltás előtt** (ellenpróba a lezárt éra snapshotjain) — **igen / nem** |

## 8. Referencia

- Forrás-javítás: commit `1871ef7`
- Panel: 37 ágens, 4 lencse, 23 igazolt lelet / 7 blocker (2026-10-19)
- Mérések: `docs/CHANGELOG.md` 2026-10-19 (8) és (9)
- A §3.9 eredeti döntés: commit `50dfb3c`, Day 63 outcome §3.9 (Döntés 9)
