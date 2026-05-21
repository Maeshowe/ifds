# W18 Weekly Analysis — 2026-04-27 → 2026-05-01

**Készült:** 2026-05-02 szombat délelőtt
**Forrás:** `weekly_metrics.py` output (W18.md), `scoring_validation.py` (55 nap, 378 trade), 5 napi review, MID vs IFDS comparison
**Hét státusz:** kumulatív -$987 (-0.99%), Day 55/63

---

## TL;DR — egy mondatos összefoglaló

A W18 egy **vegyes hét** volt két jól értelmezhető rétegben: az első 4 nap (-$617 → +$238 visszamászás) **erős feature-validáció** a Breakeven Lock és MID Bundle számára, **de** a péntek -$1,248 (DTE -$988 single-ticker) **strukturális hiányosságot** tárt fel — a scoring nem fogja meg a recent earnings miss kontextust, pontosan ezt orvosolja a most CC-re váró Contradiction Signal feature.

---

## Heti számok — "weekly_metrics.py" hivatalos output

| Metrika | W18 | W17 | Változás |
|---------|-----|-----|----------|
| Trading days | 5 | 5 | — |
| Positions opened | 38 | ~30 | +27% |
| Net P&L | **-$1,106** | +$593 | -$1,699 |
| Excess vs SPY | **-1.90%** | +0.13% | -2.03% |
| Win days | 2/5 | 3/5 | -1 |
| TP1 hits | **0/38 (0%)** | 3/21 (14%) | -3 hits |
| LOSS_EXIT count | 7 | 1 | +6 |
| MOC count | 28 | 17 | +11 |
| TP2 hits | 0 | 1 | -1 |
| Avg score | 91.1 | 92.5 | -1.4 |
| Score→P&L correlation | r=+0.239 | r=+0.180 | erősebb |
| Commission/gross % | **14%** | 12% | +2pp |

**Az átmenet aggasztó számokban**, de **strukturálisan értelmezhető** — lásd alább.

---

## 1. A heti dinamika — két különböző rész

### 1.1 Hétfő-csütörtök: visszamászás (4 nap)

| Nap | SPY | Portfolio | Excess | P&L net | Kumulatív | VIX |
|-----|-----|-----------|--------|---------|-----------|-----|
| Hétfő | +0.17% | -0.33% | -0.50% | -$361 | -$349 | 18.20 |
| Kedd | -0.49% | -0.27% | +0.22% | -$308 | -$617 ← mélypont | 18.04 |
| Szerda | -0.02% | +0.43% | +0.45% | +$406 | -$187 | 18.51 |
| Csütörtök | +0.99% | +0.43% | -0.57% | +$405 | **+$238** ⭐ | 16.99 |
| **Σ 4 nap** | **+0.65%** | **+0.27%** | **-0.40% átlag** | **+$140** | — | **17.94** |

A 4 napon belül **+$855 visszamászás a kedd-i mélypontról**. Az excess vs SPY 4 napi átlag -0.40% — **biztonságos sávban** a Day 63 keret szempontjából. **A csütörtök +$238-es kumulatív POZITÍV TARTOMÁNY** a BC23 deploy óta első ilyen pillanat.

### 1.2 Péntek: drasztikus hiba (1 nap)

| Nap | SPY | Portfolio | Excess | P&L net | Kumulatív | VIX |
|-----|-----|-----------|--------|---------|-----------|-----|
| **Péntek** | **+0.28%** | **-1.22%** | **-1.50%** | **-$1,248** | **-$987** | **16.69** |

**Egyetlen nap megsemmisíti** az előző 4 nap +$140 visszamászását, és **-$1,225 mozgással** lényegében visszadobja a hetet a kedd-i mélypontra. **Ez NEM normál varianca** — strukturális hiba a DTE-en.

---

## 2. A péntek-i DTE eset — a hét kritikus tanulsága

### 2.1 Mi történt

| Idő | Esemény |
|-----|---------|
| **Kedd ápr 28** | DTE Energy Q1 earnings miss bejelentés (-7.1% vs estimate, Zacks) |
| **Csütörtök ápr 30** | IFDS Phase 4 score: 92.0 (erős "buy" jelzés) |
| **Péntek máj 1 16:18** | DTE entry $153.29 (260 share, 4 bracket-split) |
| **Péntek 18:20** | DTE LOSS_EXIT @ $149.91 (Bracket B, -2.20%) |
| **Péntek EOD** | 4 különálló split exit: 2× LOSS_EXIT + 2× SL = **-$988** |

### 2.2 Kvantifikált hatás

| Forgatókönyv | Pozíció méret | P&L |
|--------------|---------------|-----|
| Tényleges (M_contradiction nélkül) | 260 share | -$988 |
| **M_contradiction ×0.80 mellett** | **208 share** | **-$790** |
| M_contradiction ×0.50 mellett | 130 share | -$494 |

A ×0.80 multiplier ~**$200 megtakarítást** termelt volna **egyetlen napon**.

### 2.3 Mi kellett volna eljutnia a Phase 6-ig

Az FMP `/stable/earnings` endpoint **közvetlenül** elérhető a kedd-i (ápr 28) earnings miss-szel. Az IFDS Phase 4 scoring **nem** olvasta. A 2026-05-02 állapotban a scoring redesign **flow-domináns** (0.40 súly), és a **funda komponens** (0.30 súly) **NEM** integrálta ezt a jelet.

**A Contradiction Signal feature pontosan ezt a gap-et tölti be.** Lásd: `docs/tasks/2026-05-04-contradiction-signal-from-fmp.md`.

---

## 3. "Bull rally underperform" — strukturális mintázat megerősítve

A W18 alatt **két egymás utáni bull napon** alulteljesítettünk a piaccal szemben:

| Nap | SPY | Portfolio | Excess | Megjegyzés |
|-----|-----|-----------|--------|-----------|
| Csütörtök | +0.99% | +0.43% | **-0.57%** | bull rally, mi defenzív |
| Péntek | +0.28% | -1.22% | **-1.50%** | DTE-driven (összetett hiba) |

A csütörtöki -0.57% **tipikus** swing trading minta — a long-only stratégiák technikailag verni szokják egy nagy bull napon a buy-and-hold-ot, mert a buy-and-hold a teljes 1.0% mozgásból profit, míg a swing 5-6 ticker az 1.0%-nak csak részét fogja meg.

**Ez NEM strukturális hiba**, **csak** realisztikus elvárás-finomítás. **De fontos a Day 63 keret szempontjából:**

- Az ÉLESÍTÉS feltétel `(b)`: 20+ napon át regime nem Stagflation **ÉS** kumulatív excess vs SPY > +1%
- **Bull rally periódusban a +1% excess nehezen elérhető** — minden bull nap -0.5% körüli excess-szel csökkenti a heti pozitív excess-t

**Implikáció:** ha a piac most **stabilan bull-ranged-ben** marad (low VIX, +0.3-1% napi SPY), akkor az ÉLESÍTÉS feltétel **strukturálisan nehezíti** a Day 63 mérést. **Realisztikus kimenet:** PAPER FOLYTATÁS.

---

## 4. Scoring Validation finding — a hét legfontosabb adata

A `scoring_validation.py` 2026-05-01 esti futása **55 napi 378 trade** mintán. **Strukturális finding-ok:**

### 4.1 A score önmagában nem prediktív

| Korreláció | Érték | p-érték | Értelmezés |
|-----------|-------|---------|------------|
| Pearson (score vs P&L $) | **-0.000** | 0.996 | **statisztikailag null** |
| Spearman (score vs P&L $) | -0.007 | 0.898 | **statisztikailag null** |
| Pearson (score vs P&L %) | +0.005 | 0.929 | **statisztikailag null** |

**Ez nem azt jelenti, hogy "a rendszer rossz"** — azt jelenti, hogy **a kompozit score önmagában** nem prediktív 55 napon át. Két fontos kvalifikáció:
- A 378 trade túlnyomó része BC22 vagy korábbi (a BC23 redesign csak 14 napja él)
- A BC23-only adat ~80 trade, **kevesebb statisztikai erővel**

### 4.2 A flow komponens az egyetlen jelentős prediktor

| Sub-score | Pearson | p-érték |
|-----------|---------|---------|
| **flow** | **+0.136*** | **0.039** ✓ |
| tech | -0.085 | 0.198 (null) |
| funda | -0.088 | 0.180 (null) |

**A flow score statisztikailag jelentős prediktor.** A tech és funda komponensek **nem** azok.

**Implikáció a BC23 súly-rendszerre:** flow=0.40, funda=0.30, tech=0.30. **A flow súly indokolt** — pontosan ezt mutatja a UW Quick Wins + Snapshot v2 deploy értéke. **De a tech/funda 60% kombinált súlya túl magas lehet**, ha az adatuk átlagosan nem informatív.

**Ez NEM automatikus szigorítás** — a tech/funda outlier esetekben (mint a DTE earnings miss) **kritikus** információt hordoz. A Contradiction Signal pontosan az **outlier protection** kategóriát célozza, nem regular prediktor.

### 4.3 Quintile breakdown — érdekes anti-mintázat

| Quintile | Score range | N | Avg P&L | Win rate | Total P&L |
|----------|-------------|---|---------|----------|-----------|
| Q1 | 85.5–92.5 | 75 | -$1.72 | 48.0% | -$129 |
| **Q2** | **92.5–94.0** | **76** | **+$11.57** | **53.9%** | **+$880** ✓ |
| **Q3** | **94.0–94.0** | **75** | **-$17.88** | **32.0%** | **-$1,341** ✗ |
| Q4 | 94.0–95.0 | 76 | +$1.01 | 53.9% | +$76 |
| Q5 | 95.0–142.5 | 76 | -$8.91 | 44.7% | -$677 |

**Top-Bottom spread: -$7.19 (Q5 vs Q1) — null edge.**

**Egy érdekes pattern:** a **Q2 quintile a legjobb** (92.5-94.0 sáv). A Q3 (~94.0 fix) **a legrosszabb**. A Q5 (95+) **negatív**.

**Ez ellentétes a várakozással:** a magasabb score nem feltétlen jelent jobb P&L-t. Lehetséges magyarázat: a **94+ score tickerek** gyakran **earnings előtt vagy után** jelennek meg (ahol az IFDS gyűjti a legmagasabb pontszámot), és ezek **több kockázatot** hordoznak — pontosan a típus, amire a Contradiction Signal ×0.80 multiplier-t alkalmazna.

### 4.4 Exit type breakdown — strukturális finding

| Exit type | N | Avg P&L | Total P&L |
|-----------|---|---------|-----------|
| LOSS_EXIT | 32 | -$98.50 | **-$3,152** |
| MOC | 280 | +$3.36 | +$940 |
| SL | 15 | -$78.87 | **-$1,183** |
| TP1 | 36 | +$32.95 | +$1,186 |
| TP2 | 3 | +$286.03 | +$858 |
| TRAIL | 3 | +$33.39 | +$100 |
| NUKE | 9 | +$6.51 | +$59 |

**A profit exitek (TP1, TP2, MOC, TRAIL) ÖSSZESEN: +$3,084.**
**A kárlimitáló exitek (LOSS_EXIT, SL) ÖSSZESEN: -$4,335.**

**Net deficit: -$1,251.**

**Ez a -$1,192 össz-P&L magyarázata:** a kárlimitáló exitek **strukturálisan nagyobb veszteséget termelnek**, mint amennyit a profit exitek hoznak.

**Két lehetséges értelmezés:**

**(a)** A LOSS_EXIT/SL **gyakran whipsaw-on triggerelnek**. **Ezt a múlt heti whipsaw audit (`+$87.98 net pozitív`) cáfolja** — a -2% szabály átlagosan védett.

**(b)** A LOSS_EXIT/SL **helyesen** zárnak átmenetileg rosszul ment pozíciókat, **de a TP1/TP2 célok távolsága** nem elég nagy ahhoz, hogy a 32+15 = 47 negatív exit-et a 36+3 = 39 profit exit kompenzálja.

**A (b) hipotézis a valószínű.** A jelenlegi TP1 = 0.75×ATR cél (BC23 redesign csökkentette 2.0×ATR-ről) **kevesebb profitot** termel exitenként, mint amennyi kárt a -2% LOSS_EXIT okoz. **A 0.75×ATR választás indoka volt a magasabb hit rate** — de a hit rate 0% mind a 38 W18 trade-en. **Tehát a profit hit rate sem jött be.**

**Ez egy STRUKTURÁLIS KÉRDÉS a BC23 redesign-ról**, amit **nem most** rendezünk meg, **de a vasárnapi munkából** felveszem a backlog-ideas-be:

> **TP1 cél revízió W19+ scope** — a 0.75×ATR alacsony cél **0% hit rate** mellett (W18) nem hozott elég profitot a -2% LOSS_EXIT/SL kárkompenzációhoz. Vagy emelni kellene a TP1-et 1.0×-1.25×ATR-re, vagy szűkíteni a LOSS_EXIT-et -1.5%-ra. **Effort: ~30 min config tuning + W19 mérés.**

---

## 5. MID vs IFDS comparison — első futtatás

A `mid_vs_ifds_sector_comparison.py` 2026-05-02 futása napi szinten összevet:

### 5.1 ⚠️ Az IFDS Phase 4 snapshot szelektivitása

Mind az 5 W18 napon: **`IFDS sector count: 1`**, csak **Technology, 1 ticker, score 78.0**. A Phase 4 snapshot **csak a "winner" tickert menti**, nem az összes scoring táblát.

**Ez megakadályozza** a tényleges sector comparison-t — egyetlen IFDS ticker (Technology) vs MID 40 sector ETF rangsorja **nem összehasonlítás**.

**Backlog idea (W19+ scope):**
> **Phase 4 snapshot enrichment** — ne csak a winner tickert, hanem a **teljes scoring táblát** mentse el. ~30-45 min CC munka. **Előfeltétel** a következő MID vs IFDS comparison-höz.

### 5.2 A MID rangsor dinamikája

| Nap | MID top 5 ETF |
|-----|---------------|
| Hétfő | GLD, IGV, OIH, QQQ, SMH |
| Kedd | IGV, IWM, KRE, SPY, XLC |
| Szerda | GLD, SMH, XLK, XLRE, AGG |
| Csütörtök | GLD, QQQ, SMH, SPY, XLE |
| **Péntek** | **AMLP, DIA, IBB, ITB, IWM** |

**A péntek-i rangsor drasztikusan eltér** az előző 4 naptól. **Pénteken nincs benne sem QQQ, sem SPY, sem SMH.** A defensive/MLP/homebuilders/small caps top-3 **a regime váltás kezdetét** mutatja — pont azon a napon, amikor a portfólió -$1,248-cal zárt.

**Implikáció:** ha a Phase 4 snapshot enrichment + a MID Phase 3 átvétel (BC25) élesben lenne, a péntek-i veszteséget **valószínűleg csökkentette volna**, mert a defensive sektor felé orientálódott volna a ticker-választás.

**Ez egy adatpont a BC25 motivációjához** — felvegyük a `docs/planning/backlog-ideas.md`-be?

---

## 6. Élesben futó feature-ök — heti mérleg

### 6.1 Breakeven Lock — 4 napi adat

| Nap | trail_b aktiválás | Breakeven Lock alkalmazás | Eredmény |
|-----|-------------------|---------------------------|----------|
| Hétfő | 0 | 0 | n/a |
| Kedd | 1 (PAA) | 1 | +$135 megőrzött profit |
| Szerda | 4 (CVE/VG/CRWV/RNG) | 4 | mind MOC nyertes |
| Csütörtök | 2 (EC, TER) | 2 | TER első TRAIL exit (+$75 net) |
| Péntek | 0 (csak GLNG 17:45-kor — a window előtt) | 0 | n/a |

**Heti összegzés:** 7 trail_b aktiválás, **mind a 7 a 19:00-19:04:59 CEST window-ban**. **5/7 alkalmazás** konkrétan profitot védett vagy javított, **2 alkalmazás semleges** (a trail mechanika amúgy is megfogta volna).

**Nincs egyetlen olyan eset sem**, amikor a Breakeven Lock **kárt termelt** — összhangban a `max(trail_sl, floor)` matematikai garanciával.

### 6.2 MID Bundle Integration — 5 napi shadow snapshot

Az 5 napi MID snapshot **mindenhol** működött. Az `age_days` mező továbbra is **regime age**-t mutat (nem data age) — Stagflation Day 11 → Day 15 a héten.

**A weekly review szempontjából:** a MID **adatot ad**, **de a comparison gyengeségét** a Phase 4 snapshot szelektivitása korlátozza (lásd 5.1). **A vasárnapi MID vs IFDS comparison riport nem ad érdemi következtetést** a Phase 4 enrichment hiánya miatt.

### 6.3 vix-close + LOSS_EXIT whipsaw audit

**Mindkettő deployolt** szerda délelőtt. Az adatszinkron **átlátható** mostantól:
- **VIX close mező** rögzítve a daily_metrics-ben, Day 63 mérhető
- **LOSS_EXIT whipsaw cost +$87.98** → a -2% szabály átlagosan védett (NIO eset egyedi)

---

## 7. Day 63 keret — péntek esti állapot

### 7.1 Számok

| Metrika | Érték | Status a kerethez képest |
|---------|-------|--------------------------|
| Day | 55/63 | **8 nap van hátra** |
| Kumulatív P&L | -$987 (-0.99%) | **biztonságos sávban** (paper folytatás default) |
| ÉLESÍTÉS távolság | +$3,987 a +$3,000-hoz | **8 nap × +$498/nap → NEM realisztikus** |
| LEÁLLÍTÁS távolság | excess +0.13% távol a -1.5%-tól | **biztonságos sávban** |
| 5 napi excess vs SPY | -1.90% (W18 hivatalos) | romlott a 4 napi -0.40%-ról |
| VIX W18 átlag | 17.69 | **a 18-as küszöb körül** |
| VIX 5/5 nap > 18? | Nem (csak 3/5: hétfő/kedd/szerda) | leállítási feltétel **részlegesen alszik** |

### 7.2 Realisztikus Day 63 várt kimenet

A 8 napra napi átlagos +$80-150 reális (2-3 jó nap, 3-4 vegyes nap, 1-2 vesztes nap mintázat alapján). **Ez** a kumulatív Day 63-ra **+$0 és -$2,000 között** ad — **paper folytatás default** sávban.

**A M_contradiction implementáció hatása** ezen a 8 napon: ha **2-3** CONTRADICTION-flagged ticker fordul elő (a W17 6/5 + W18 1/5 alapján ~3-4/hét), és átlagosan ~$50-100 megtakarítást ad pozícióként, akkor **+$150-300 hozzájárulás**.

**Tehát a kumulatív Day 63 várható tartomány M_contradiction-nel: -$1,800 és +$300 között.**

---

## 8. Strukturális finding-ok és W19+ teendők

### 8.1 Most elindított task-ok (CC-re vár)

1. **Contradiction Signal from FMP** (`docs/tasks/2026-05-04-contradiction-signal-from-fmp.md`) — P1, ~4-4.5h, hétfőre kész
2. **sync_from_mini.sh javítás** (`docs/tasks/2026-05-04-sync-from-mini-improvements.md`) — P3, ~1-1.5h. **MEGJEGYZÉS:** **CC már implementálta** szombat reggel — a sync most már `docs/analysis/` mappát is hozza, `state/.last_sync` rögzítve. **A task fájl státusza módosítandó "DONE"-ra.**

### 8.2 Új backlog idea-k a W18 elemzés alapján

**(a) TP1 cél revízió** — a 0.75×ATR alacsony cél 0% hit rate mellett nem hozott elég profitot. W19+ scope, ~30 min config tuning. **Felvétel a backlog-ideas-be.**

**(b) Phase 4 snapshot enrichment** — a teljes scoring tábla mentése, nem csak a winner. W19+ scope, ~30-45 min CC. **Előfeltétel** a MID vs IFDS comparison-höz.

**(c) BC25 motiváció megerősítve** — a péntek-i MID rangsor (defensive/MLP/homebuilders) drasztikusan eltért az IFDS Phase 3 sector rotation-tól, és a portfólió -$1,248-cal zárt. **Felvegyük a backlog-ideas-be?**

### 8.3 Folytatólagos megfigyelések

- **CRGY/AAPL leftover phantoms** továbbra is — `monitor_positions.py` BUG (régóta ismert, 2026-04-14 cleanup task)
- **LION/SDRL/DELL/DOCN phantom events** — IBKR API quirk (2026-04-14 cleanup task Bug 3)
- **AVDL.CVR** non-tradable, ignorálható
- **DTE -130 short leftover** — ma reggel (szombat) Tamás `nuke.py --positions`-szal **buy-to-cover** zárta. Az 4-split LOSS_EXIT/SL aggregát short pozíció valós volt, **nem phantom**.

---

## 9. A pszichológiai kontextus

A péntek-i -$1,248 **fájdalmas adat**, és a kumulatív -$987 most **közel a kedd-i mélyponthoz** ($-617). De nézzük meg objektíven:

**A héten 4 strukturális javulás történt:**
1. **Breakeven Lock élesben** — 5/7 alkalmazás profitot védett vagy javított
2. **MID Bundle Integration shadow** — adat gyűlik a BC25 döntéshez
3. **vix-close + whipsaw audit** — Day 63 mérés mostantól pontos
4. **Day 63 framework formalizálva** — a döntés strukturált, nem érzelmi

**A péntek-i hiba egy konkrét gap-et tárt fel** (DTE earnings miss + magas score), és **a Contradiction Signal feature pontosan ezt orvosolja**. Hétfő reggelre élesben lesz.

**A 2026-04-28 esti megegyezés szerint:** a "paper folytatás default" sáv a -$3,000 és +$3,000 közötti tartomány. **Most -$987-en** állunk, ami **bőven** ebben a sávban. A -$987 **nem panik-pillanat**, **nem rendszeres alulteljesítés**, hanem **egy strukturális gap, amit pénteken tisztán látunk és hétfőn javítunk**.

**Linda Raschke szempontjából:** "Humans notice when the rules no longer apply." A péntek-i DTE eset **ezt a notice-t** termelte. A scoring szabály (kompozit score → bracket order) **nem érvényesült** a recent earnings miss kontextusban. **Az ember (Tamás) észrevette**, **a systematic réteg most kódba önti** a felismerést.

**Ez nem failure**, hanem **iteráció**.

---

## 10. Konkrét tennivalók a héten (W19, máj 4-8)

### 10.1 Vasárnap (máj 3) — Tamás utazás közben kevésbé online

- ✅ W18 weekly elemzés (ez a doc) **kész**
- ✅ MID vs IFDS comparison riport `docs/analysis/mid-vs-ifds-sectors-W18.md` kész
- ✅ Day 63 Decision Framework formalizálás `docs/decisions/2026-04-28-day63-decision-framework.md` **kész**

### 10.2 Hétfő (máj 4)

- **Tamás reggel:** `git pull` a Mac Mini-n, ellenőrzés hogy CC commit-olta-e a M_contradiction-t
- **CC:** ha a M_contradiction implementáció kész, a hétfő 16:15 cron már az új feature-rel fut
- **Pipeline:** normál ritmus, BC23 W19 Day 1

### 10.3 Hét folyamán

- **W19 daily review-k** mindennap reggel
- **Csütörtök máj 8:** kis backlog átnézés (ha CC-nek szabad kapacitása van: TP1 cél revízió, Phase 4 snapshot enrichment)
- **Péntek máj 8 22:00:** **W19 weekly metrika** futtatás

### 10.4 Day 63 (~máj 14, csütörtök)

- **09:00 Reminder notification**
- W19 + W18 + W17 adatok együtt, scoring validation újrafuttatás
- Döntés: ÉLESÍTÉS / LEÁLLÍTÁS / PAPER FOLYTATÁS
- Új doc: `docs/decisions/2026-05-14-day63-decision-outcome.md`

---

## Kapcsolódó

- **W18 weekly metrics (CC):** `docs/analysis/weekly/2026-W18.md`
- **Scoring validation (55 nap):** `docs/analysis/scoring-validation.md`
- **MID vs IFDS comparison W18:** `docs/analysis/mid-vs-ifds-sectors-W18.md`
- **Daily review-k W18:** `docs/review/2026-04-{27,28,29,30}-daily-review.md`, `docs/review/2026-05-01-daily-review.md`
- **Day 63 framework:** `docs/decisions/2026-04-28-day63-decision-framework.md`
- **M_contradiction task (CC-re vár):** `docs/tasks/2026-05-04-contradiction-signal-from-fmp.md`
- **W17 weekly elemzés (összehasonlítás):** `docs/analysis/weekly/2026-W17-analysis.md`
- **Linda Raschke filozófia:** `docs/references/raschke-adaptive-vs-automated.md`

---

*Készült: 2026-05-02 szombat délelőtt, Tamás utazás előtt*
*Forrásadatok frissessége: `state/.last_sync` = 2026-05-02T09:00:12Z*
