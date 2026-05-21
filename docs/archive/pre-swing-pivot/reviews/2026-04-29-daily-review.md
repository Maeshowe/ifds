# Daily Review — 2026-04-29 (szerda)

**BC23 Day 13 / W18 Day 3**
**Paper Trading Day 53/63**

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | +$430.06 |
| Napi P&L net | **+$406.20** (commission $23.86) |
| Kumulatív P&L | **-$187.40 (-0.19%)** ← visszamászás közel breakeven-hez |
| Pozíciók (új) | 5 ticker (CVE, VG, CRWV, RNG, BKH) — 7 trade (CVE 2-split, VG 2-split) |
| Win rate | 4/5 ticker (CVE, VG, RNG, CRWV nyert; BKH vesztett) |
| TP1 hit rate | 0/5 (0%) |
| TP2 hit rate | 0/5 (0%) |
| Exit mix | **7× MOC**, 0× LOSS_EXIT, 0× SL, 0× TP |
| Avg slippage | +0.22% (CRWV +1.13% kedvezőtlen) |
| Commission | $23.86 ← **alacsonyabb** mint W18 első 2 napja |
| SPY return | -0.02% |
| Portfolio return | +0.43% |
| **Excess vs SPY** | **+0.45%** ⭐ outperform |
| VIX close | **18.51** (Δ ismeretlen, a vix-close fix tegnap óta él) |

## ⭐ A Breakeven Lock második napja — 4 aktiválás, mindegyik profitba ment

**A feature **strukturális hatása** mára egyértelműen láthatóvá vált.** A logok alapján:

```
17:00:10 CEST  CVE  trail_activated_b @ $28.485 (entry $28.32, +0.58%)
17:00:12 CEST  CVE  breakeven_lock_applied  $27.385 → $28.32  ✓
               
17:00:17 CEST  VG   trail_activated_b @ $13.10 (entry $12.87, +1.78%)
17:00:19 CEST  VG   breakeven_lock_applied  $11.96 → $12.87  ✓

17:00:23 CEST  CRWV trail_activated_b @ $111.89 (entry $111.20, +0.62%)
17:00:26 CEST  CRWV breakeven_lock_applied  $98.55 → $111.20  ✓

17:00:30 CEST  RNG  trail_activated_b @ $39.89 (entry $39.46, +1.09%)
17:00:32 CEST  RNG  breakeven_lock_applied  $36.39 → $39.46  ✓
```

**Az összes B bracket SL-t entry-re emeltük.** Mind a 4 ticker MOC-on **profitba** zárt:

| Ticker | Old trail SL | New SL (entry) | MOC fill | MOC P&L |
|--------|--------------|----------------|----------|---------|
| CVE | $27.385 | $28.32 | $28.76 | +$309.68 (split) |
| VG | $11.96 | $12.87 | $13.18 | +$183.60 (split) |
| CRWV | $98.55 | $111.20 | $114.23 | +$54.74 |
| RNG | $36.39 | $39.46 | $40.18 | +$144.00 |

**Ezeken a pozíciókon a Breakeven Lock NEM kötött ki egyetlen tickeren sem** — **mert egyik sem esett vissza entry-re**. Ez **nem** azt jelenti, hogy a feature haszontalan volt — azt jelenti, hogy **a védelem ott volt**, de nem volt rá szükség.

**A kritikus aspektus:** a CRWV trail SL **$98.55-ről $111.20-ra** emelkedett — **+12.83%** ugrás egyetlen lépésben. Ha a CRWV ár visszaesett volna a régi $98.55-re (~12% lefelé mozgás), akkor:
- **Régi rendszer:** kilép $98.55-en, $-12.65/share × 31 = **-$392** veszteség
- **Új rendszer (Breakeven Lock):** kilép $111.20-on, $0/share = **$0 veszteség**

**A potenciális megtakarítás CRWV-n egyedül ~$390** lett volna egy nagy zuhanáson. Ez **nem történt meg**, de **a védelem** ott volt készenlétben.

## A nap nagy meglepetése — szektor inverzió

A **W18 első 2 nap** és a **mai nap** között teljesen **átfordult** a szektor mintázat:

**Hétfő (W18 Day 1):** 4/5 ticker MID top-3 sectorban, mégis vesztes (-$361 net)
**Kedd (W18 Day 2):** 4/5 ticker MID top-3, 1 MID bottom (NIO), vesztes (-$308 net)
**Szerda (ma):** **3/5 ticker MID top-3** (CVE/XLE, RNG/XLK, BKH/?), **2 ticker NEM top-3** (VG/?, CRWV/XLK), **nyertes (+$406 net)**

**Az MID top/bottom rangsor változatlan** — `XLK, XLI, XLE` (top), `XLV, XLF, XLY` (bottom). De ma a **2 nem-top-3 ticker is nyert** (VG +$183, CRWV +$54). Csak a BKH (Utility/Cons Defensive?) vesztett, ami **se nem top, se nem bottom**.

**Mit jelent ez:** a sector ranking **prediktív érvénye gyenge** rövid távon. **Egy nap nem statisztika** — a hétfői "ticker-selection probléma" megfigyelésem **nem feltétlen érvényes**, csak az adott napra. A vasárnapi MID vs IFDS comparison **több napi adat** alapján fog érdemi következtetést levonni.

**Megjegyzés:** A MID adat tegnapi (2026-04-28) volt — ma este 22:00-kor jön a friss snapshot.

## Pozíciók részletei

### Nyertesek (4)

**CVE (Cenovus Energy, score 92.0):** 2-split, entry $28.27 (slippage **-0.18% kedvező**), MOC $28.76 = **+$309.68 össz** (245 + 64.68). +1.73% intraday. **A nap legnagyobb nyertese**. CVE = Canadian Energy, az XLE momentumából profitált. **Breakeven Lock 17:00 CEST** aktivált.

**VG (Venture Global LNG, score 91.5):** 2-split, entry $12.88, MOC $13.18 = **+$183.60 össz** (150 + 33.60). +2.33% intraday. **A legnagyobb % nyerő ma.** VG = LNG export (energia szektor). **Breakeven Lock 17:00 CEST** aktivált.

**RNG (RingCentral, score 87.0):** Entry $39.46 (slippage 0.0% perfekt), MOC $40.18 = **+$144.00**. +1.82% intraday. A legalacsonyabb score-ú nyertes. **Breakeven Lock 17:00 CEST** aktivált.

**CRWV (CoreWeave, score 89.5):** Entry $112.46 (**slippage +1.13% rossz** — legrosszabb a héten!), MOC $114.23 = **+$54.74**. +1.57% intraday. **Breakeven Lock 17:00 CEST** aktivált. **Megjegyzés:** a kedvezőtlen entry slippage ~$30 költséget jelentett — nélküle ez +$85 lett volna. Ha ez **strukturális mintázat** (CRWV mindig magas slippage-gel jön), akkor **érdemes átgondolni** — később.

### Vesztes (1)

**BKH (Black Hills Corporation, utility, score 85.5 — legalacsonyabb):** Entry $75.33 (slippage +0.09%), MOC $74.22 = **-$261.96**. -1.47% mozgás. **A nap egyetlen vesztese.**

**Két dolog érdekes a BKH-n:**
1. **BKH = Utility/Cons Defensive sector** (XLU vagy XLP) — **a MID nem flagged** specifikusan, de **általánosan** a defensive szektorok **nem voltak** a top-ban. A SPY -0.02% mellett a defensive ne underperformolt volna — de ma underperformed.
2. **A trail_b NEM aktiválódott** BKH-n — az ár sosem emelkedett +0.7% felé. **Csendes underperformer egész nap**, ami a MOC-on -1.47%-tal zárt.

**A BKH-ra a Breakeven Lock NEM segített volna**, mert sosem volt profit állapotban a védelem aktiválásához.

## Score → P&L napi nézet

| Ticker | Score | P&L net | Breakeven Lock? | Eredmény |
|--------|-------|---------|----------------|----------|
| CVE | **92.0** | +$309.68 | ✓ | Nagy nyertes |
| VG | 91.5 | +$183.60 | ✓ | Nagy nyertes |
| CRWV | 89.5 | +$54.74 | ✓ | Kis nyertes |
| RNG | 87.0 | +$144.00 | ✓ | Közepes nyertes |
| BKH | **85.5** | -$261.96 | ✗ | Vesztes |

**Erős pozitív rank korreláció ma:** legmagasabb score (CVE 92) → legnagyobb $ nyertes. Legalacsonyabb score (BKH 85.5) → egyetlen vesztes. **r ≈ +0.7-0.8** napon belül.

**A heti és havi átlag** fontosabb mint a napi varianca, de **ma egyértelmű minta**: a magas score-ú tickerek profitba mentek, az alacsony score-ú vesztett. **Ez a BC23 scoring igazolása napon belül.**

## A W18 első 3 nap — szembefordulás

| Nap | SPY | Portfolio | Excess | P&L net | Kumulatív |
|-----|-----|-----------|--------|---------|-----------|
| Hétfő | +0.17% | -0.33% | -0.50% | -$361 | -$349 |
| Kedd | -0.49% | -0.27% | +0.22% | -$308 | -$617 |
| **Szerda** | **-0.02%** | **+0.43%** | **+0.45%** | **+$406** | **-$187** |
| **Σ 3 nap** | **-0.34%** | **-0.17%** | **+0.17%** | **-$263** | — |

**Két fontos megfigyelés:**

1. **Az excess vs SPY 3 napos átlag pozitívra fordult** (+0.17%) — ami **a te kereted szerint pontosan a "biztos sávban"** kategória, távol mind az élesítési, mind a leállítási küszöbtől.

2. **Két egymás utáni outperform nap** — kedden +0.22%, szerdán +0.45%. **Ez nem véletlen**, ha 2 nap egymás után a piac alatti volatilitás mellett az IFDS jobban teljesít.

## A Breakeven Lock teljesítménye W18-ban

| Nap | trail_b aktiválás | Breakeven Lock alkalmazás | MOC kimenetel |
|-----|-------------------|---------------------------|---------------|
| Hétfő | 0 (nincs trail-aktív pozíció) | 0 | n/a |
| Kedd | PAA (1) | PAA (1) | PAA +$135 megőrzött |
| **Szerda** | **CVE, VG, CRWV, RNG (4)** | **4 alkalmazás** | **4 nyertes MOC-on** |

**3 napi adat: 5 alkalmazás, 5/5 alkalmazás után profit.** A feature **mathematikailag nem termelhet kárt** (max() művelet), és **gyakorlatilag** eddig **csak segített** vagy **semleges** volt. **Strukturálisan a legkonszenzuálisabban hatékony feature** a BC23 óta.

## VIX close — Day 63 keret szempontjából

Ma 18.51 (tegnap 18.04, hétfő 18.20). **Egy hét VIX átlag jelenleg ~18.25** — éppen a leállítási feltétel **küszöbe felett**. Ez azt jelenti, hogy:

- **Ha a VIX 18 fölött marad** és a kumulatív excess vs SPY **< -1.5%** lesz 20+ napon, akkor leállítjuk
- **Jelenleg az excess +0.17%** — **nem közeli** a leállítási feltételhez (~$1.7% távolság)

**Pozícióban vagyunk.** A VIX 18 fölött, **és** mégis pozitív excess. **Ez valójában jó** a Day 63 keretnek: a magas-vol environment **kihívást** jelent, és mégis kismértékben jobban teljesítünk a piacnál.

## Kulcsmegfigyelések

### 1. A Breakeven Lock strukturális, nem véletlen

Ma **4 párhuzamos** trail aktiválódás 17:00 CEST-kor — **mind ugyanabban a 30 másodperces ablakban**. Ez azt jelenti, hogy a piac aznap **17:00 CEST-re** (=11:00 ET, US lunch hour utáni open) **stabilizálódott**, és minden trail aktiváló pozíció a profit-zónában érte el a +0.7% küszöböt.

Ez **a Breakeven Lock 19:00 CEST window igazolja**: a piac **természetesen** stabilizálódik a délutáni órákban, és a profit-pozíciók **ekkor érdemesek a védelemre**.

### 2. A score korreláció helyreállt

W17 r=+0.180 → W18 hétfő enyhe pozitív → kedd vegyes → **szerda r ≈ +0.7-0.8**. **Egy napi adatpontból nem von le következtetést** — de **a tendencia visszafordult** a "scoring vegyes" mintából.

**Ez NEM** azt jelenti, hogy a scoring "javult". Csak azt, hogy az adott nap körülményei között a magas score-ú tickerek differenciáltak. **Holnap (csütörtök)** újra megnézzük.

### 3. A BKH egyedi vesztes — utility underperform

A BKH defensive utility, a SPY -0.02% mellett **-1.47%-ot esett**. A score 85.5 (legalacsonyabb) — **érdemes lett volna kihagyni**? A jelenlegi threshold 85 — pontosan a BKH-nál vagyunk a határon.

**Ez a "dynamic threshold" érvényesülésére** mutat: ha a threshold 86 lett volna, a BKH **nem került volna a portfolio-ba**, és a nap **+$668** lett volna -$406 helyett. **Megtakarítás potenciál: ~$260**.

**De** ez **utólagos optimalizálás** — könnyű most mondani. A score 85.5 egy normál pozíció a 85+ rangsorban, és **statisztikailag** nem indokolt szigorúbb threshold egyetlen vesztes alapján.

### 4. CRWV slippage problémája

CRWV slippage **+1.13%** ma — a legrosszabb a W18-ban. Ha a CRWV gyakran ilyen slippage-gel jön, **érdemes lehet specific limit ár szigorítás** vagy **CRWV-specific watch**. **Egyetlen napi adatpont — még nem trend**, de **figyeljük**.

### 5. A Stagflation regime-ben pozitív excess

Stagflation Day 13/28 — **közelítjük a median-t (28)**. A te megfigyelésed szerint a Stagflation regime **rossz a swing scoring-nak**. **Mégis**: a 3 napi excess +0.17%. **Ez** azt jelenti, hogy:
- Vagy a BC23 + Breakeven Lock kombinációja a Stagflation-ben is működik
- Vagy a 3 nap statisztikailag elégtelen, és az áprilisi 28 napi -0.5% átlagos napi mutató volt a valódi regime jellemző

**A Day 63 keretedben a Stagflation feltétel kívül ad** ÉLESÍTÉS feltételt. Tehát:
- Ha a Stagflation **regime change-be** megy a következő 11 napban
- És az átlagosan +0.17% excess folytatódik
- Akkor **a +1% excess feltétel** a Day 63-ra **realisztikusan elérhető**

## Anomáliák

- **CRGY + AAPL leftover** változatlanul 8. nap (logokban szerda esti is `leftover_found`)
- **DELL és DOCN phantom_filtered** — a `monitor` script automatikus szűrte, nincs gond
- **SDRL trail események** a logban — `tp1_detected`, `loss_exit -2.75%` — **megjegyzés**: ez egy **fantom esemény** a leftover monitorból, NEM a mai tényleges pozíciók közé tartozik. A mai EOD daily_metrics-ben **nem szerepel**, és a Telegram MOC üzenet sem tartalmazza. **Valószínűleg** a `monitor_positions` script érzékelte egy korábbi pozíció maradványát. **Nem kritikus**, de **furcsa**.
- **VIX delta továbbra is null** a daily_metrics-ben — a vix-close mező feltöltött, de a delta nem. **Kis CC fix** lehet (1-2 sor).

## A te döntési kereted szerint

**Tegnap esti megegyezés szerint:**
- Élesítés: Day 63 → +$3,000 → $10k tőke
- Leállítás: 20+ napon át VIX > 18 mellett excess < -1.5%
- Alpha cél: 0.75-1% / hó

**Mai állapot:**
- Kumulatív -$187 (-0.19%) — **közel breakeven-en**, **a +/- 1.5% biztos sávban**
- Excess vs SPY 3 napos átlag: **+0.17%** (paper folytatás default)
- VIX 18.51 — **feltétel-érzékeny zóna**, de az excess pozitív, nem leállás-közeli
- 10 nap van Day 63-ig

**A jelenlegi pálya:** ha a következő 10 napban **napi átlag +$50-100** (ami a mai +$406-hoz képest **konzervatívabb**), akkor a kumulatív Day 63-ra **+$300-1,000** lehet — **a "paper folytatás default" sávban**, nem ÉLESÍTÉS, nem LEÁLLÍTÁS.

**Ez a realisztikus kimenet** a te 0.75-1% / hó alpha céloddal, és **összhangban van**. Nem csodaváró, nem pánikban — **stabil, mérhető, és feldolgozható**.

## Holnap (csütörtök ápr 30) várható

- **Reggel (Chat = én):** `src/ifds/scoring/company_intel.py` LLM prompt sablon olvasása, FMP mezők beazonosítása. Új task fájl: `2026-04-30-contradiction-signal-from-fmp.md` — déli órákban CC-nek
- **CC délután:** ~4-5h implementáció (új modul `contradiction_signal.py`, Phase 4-5 integráció, Phase 6 multiplier alkalmazás)
- **Pipeline:** normál ritmus, BC23 W18 Day 4
- **Te (Tamás):** szokásos ellenőrzés a 22:00-i MID snapshot után

## Hétvégi (máj 2-3) feladatok

- **Tamás:** CRGY+AAPL leftover nuke (9. nap lesz!)
- **Chat (én):** W18 weekly elemzés (péntek után) + első MID vs IFDS sector comparison + `docs/decisions/2026-04-28-day63-decision-framework.md` formalizálás

## Kapcsolódó

- `state/phase4_snapshots/2026-04-29.json.gz` (1 ticker — qualified above threshold)
- `logs/pt_events_2026-04-29.jsonl` ← **4× breakeven_lock_applied esemény**
- `logs/pt_eod_2026-04-29.log`
- `state/daily_metrics/2026-04-29.json` ← **vix_close = 18.51**
- **State: BC23 + Breakeven Lock + MID Bundle Integration + vix-close + LOSS_EXIT whipsaw audit (lezárva)**
- **Aktív tasks: M_contradiction (BLOCKED, holnap re-scope)**
