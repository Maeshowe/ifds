# A screener a MAI RÉSZLEGES volumenre szűr — az univerzum a futás idejétől függ

**Dátum:** 2026-10-20
**Hogyan került elő:** a (C) árnyék-mérés `enrichment gap = 390` száma, és a minta
(`ADP, AFL, ALL, AON, APD`), ami megállított: ezek $50–115 mrd kapitalizációjú nevek,
a screener nem zárhatja ki őket.

---

## 1. A mechanizmus

A `phase2_universe` a `universe_min_avg_volume` TUNING kulcsot (`500_000`,
*„500K shares/day"*) az FMP screener **`volumeMoreThan`** paraméterébe adja. Csakhogy
az FMP-nél a `volume` mező **a mai, részleges intraday volumen**, nem az átlag —
az átlag külön mezőben, `avgVolume`-ban van.

Élő mérés 2026-10-20 **17:51 CEST = 11:51 ET** (~2,3 óra a nyitás után),
`volumeMoreThan=1` mellett, hogy a mezők látszódjanak:

| ticker | `volume` (mai részleges) | `avgVolume` | kapitalizáció |
|---|---:|---:|---:|
| ADP | **503 361** | 2 164 048 | $115,8 mrd |
| AFL | **199 786** | 2 001 023 | $59,9 mrd |
| ALL | **342 717** | 1 919 792 | $63,0 mrd |
| AON | **395 130** | 1 630 415 | $62,5 mrd |
| APD | **195 932** | 1 068 935 | $66,6 mrd |

Az ADP épp átcsúszik az 500k-s küszöbön, a másik négy nem. **Nem illikvidek — csak
délelőtt 11:51-kor még nem forgott 500 ezer darab.**

### 1.1 A screener determinisztikus, csak idő-függő

Három egymás utáni hívás azonos paraméterekkel: **1197 / 1197 / 1200 sor**,
Jaccard **1,0000**. Vagyis nem véletlen — **a napszaktól függ**.

---

## 2. 🔴 Ez megfordítja két korábbi állításomat

### 2.1 A „424 név tervszerű" állításom HAMIS volt

2026-10-20-án azt írtam a kézi Phase 1-3 futás után: *„a mai 424 kisebb, de tervszerű
(earnings-völgy + 3 vétózott szektor), és minden neve a definiált univerzumból"*.

A szűkülés **nagyrészt a futás időpontja** volt, nem a terv. A három kézi futásom:

| futás | BP idő | ET idő | univerzum |
|---|---|---|---:|
| 2026-10-19 21:05 | 21:05 | 15:05 (szesszió közepe) | 730 |
| 2026-10-20 08:29 | 08:29 | **02:29 (pre-market)** | **424** |
| 2026-10-20 17:48 | 17:48 | 11:48 (szesszió közepe) | 520 |

Pre-marketben a `volume` mező ~0 → szinte minden név elbukik az 500k-s küszöbön.
Ezért volt a 424 a legkisebb.

### 2.2 Az ütemezett futás ezért volt rendben

A vasárnapi cron **22:00 CEST = 16:00 ET**, azaz **pontosan a záráskor** fut — a `volume`
mező ekkor ~teljes napi. Ez magyarázza, miért adott a történeti vasárnapi futás
**1008–1020** nevet, és miért láttam én 424–730-at.

> ⚠️ **Ez egyben latens törékenység:** a 22:00-as slot a határon van. Néhány perccel
> korábbi futás, vagy egy early-close nap, és nevek esnek ki — csendben.

---

## 3. A javítás egy paraméter

Megmérve, melyik volumen-paramétert **érvényesíti** az FMP (egy csendben eldobott
paraméter nem mozdítja a darabszámot):

| paraméter | 500k | 5M | 50M | érvényesül? |
|---|---:|---:|---:|---|
| *(nincs volumen-szűrő)* | 4733 | | | — |
| `volumeMoreThan` | 1205 | 246 | 18 | ✅ (mai részleges) |
| **`avgVolumeMoreThan`** | **2125** | **402** | **9** | ✅ **(valódi átlag)** |
| `averageVolumeMoreThan` | 4733 | 4732 | 4732 | ❌ **csendben eldobva** |
| `fakeVolumeMoreThan` *(kontroll)* | 4732 | 4732 | 4732 | ❌ |

Az `averageVolumeMoreThan` pontosan annyit ad, mint a **kitalált kontroll-paraméter** —
tehát figyelmen kívül hagyja. (Az első méréskor ezt tévesen „érvényesül"-nek jelöltem; a
±1 soros eltérés hívás-zaj volt, nem szűrés. Javítva.)

### 3.1 És ez kinyitja az enrichment-rést

| screener szűrő | sorok | tagságból lefedve | nem lefedve |
|---|---:|---:|---:|
| `volumeMoreThan` (mai részleges) | 1207 | **529 (51,5%)** | 498 |
| **`avgVolumeMoreThan`** (átlag) | 2125 | **921 (89,7%)** | **106** |

Egyetlen paraméter: a tagsági lefedettség **51,5% → 89,7%**, a rés **498 → 106**.

---

## 4. Miért ez **bugfix**, nem design-változás

A TUNING kulcs neve **`universe_min_avg_volume`**, a kommentje
*„500K shares/day"* — vagyis a **szándék** mindig az átlagos napi volumen volt. A kód
viszont egy olyan API-paraméterbe adta, ami **nem** az átlag. Ez a konfig-kulcs és az
API-paraméter közötti **szemantikai eltérés**, azaz „bug → szándékolt viselkedés".

---

## 5. Mi következik

### 5.1 A Mini jelenlegi contextje az ÉN futásom miatt degradált
A most élő context a 17:48-as (11:48 ET) futásból van: **520 név**. A
`state/state_backups/` mentései (730, 424) **ugyanígy** idő-degradáltak, és a tiszta
2026-10-04-i példány már nincs meg (azt felülírtam). Helyreállítás: **egy futás a
záráshoz közel**, vagy a §3 paraméter-javítás után bármikor.

### 5.2 A (C) ettől függetlenül jó — és most már olcsó
A (C) floor **lezárt napi bar-okból**, **20 session mediánján** számol, tehát a
napszaktól **konstrukció szerint független**. A §3 javítással a screener már csak
**enrichment**-forrás, és a rés 106-ra szűkül — a (C) bekötése ezzel egyszerű lesz.

### 5.3 Amit ez a már lezárt mérésekről mond
A swing éra scan matrixai a **vasárnapi 22:00-as** (≈zárás) futásokból származnak, tehát
a lezárt éra univerzuma **nem** idő-degradált. A ma commitolt költség/fal-számokat ez a
lelet **nem** érinti.
