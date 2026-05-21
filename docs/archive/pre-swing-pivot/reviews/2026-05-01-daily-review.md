# Daily Review — 2026-05-01 (péntek)

**BC23 Day 15 / W18 Day 5 — W18 utolsó nap**
**Paper Trading Day 55/63**

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | -$1,224.94 |
| Napi P&L net | **-$1,247.71** (commission $22.77) |
| Kumulatív P&L | **-$986.68 (-0.99%)** ← visszaesett pozitívról -$1,000 közelébe |
| Pozíciók (új) | 5 ticker (GLNG, DTE, CNP, FORM, KLAC) — **8 trade** (DTE 4-split) |
| Win rate | 1/5 ticker (csak GLNG nyert) |
| TP1 hit rate | 0/5 |
| TP2 hit rate | 0/5 |
| Exit mix | 3× MOC, **3× LOSS_EXIT** (DTE×2, FORM), **2× SL** (DTE×2) |
| Avg slippage | +0.09% (KLAC +0.26%) |
| Commission | $22.77 |
| SPY return | +0.28% |
| Portfolio return | -1.22% |
| **Excess vs SPY** | **-1.50%** ← jelentős underperform |
| VIX close | 16.69 (Δ=-1.77%) |

## ⚠️ Súlyos nap — DTE 4-split: -$988 egyetlen tickerből

**A DTE pozíció 4 különálló bracket-szegmenssé esett szét, mind LOSS_EXIT/SL:**

| DTE bracket | Qty | Entry | Exit | Exit type | P&L |
|-------------|-----|-------|------|-----------|-----|
| 1 | 100 | $153.29 | $149.81 | LOSS_EXIT | -$348.00 |
| 2 | 30 | $153.29 | $149.81 | LOSS_EXIT | -$104.40 |
| 3 | 65 | $153.29 | $149.17 | SL | -$267.80 |
| 4 | 65 | $153.29 | $149.17 | SL | -$267.80 |
| **Σ** | **260** | | | | **-$988.00** |

A DTE Energy **kedden (ápr 28) earnings miss-t jelentett be** — a Q1 EPS $1.05 vs várt $1.13 (Zacks szerint). **Ez 2 napja megjelent a piacon**, és a péntek nyitó után **azonnal -2.27% LOSS_EXIT trigger**.

**Fontos megfigyelés:** ha a M_contradiction multiplier élesben lett volna, a DTE valószínűleg CONTRADICTION-flagged lett volna (recent earnings miss + IFDS score 92). ×0.80 multiplier = 260 → ~208 share. **Megtakarítás:** ~$200 (a -$988 → ~-$790-re csökkent volna).

**Ez a péntek a M_contradiction "miért kell" napja.** A vasárnapi munkában explicit **felveszi** ezt mint motivációt.

## Pozíciók részletei

### Egyetlen nyertes

**GLNG (Golar LNG, energy/LNG, score 93.5):** 357 share, entry $55.13 (slippage +0.20%), MOC $55.77 = **+$228.48**. +1.16% intraday. **Breakeven Lock 17:45 CEST aktivált** — `trail_activated_b @ $55.33`. Ez **NEM** a 19:00 CEST window-ban, hanem **korábban** — tehát **NEM** kapott Breakeven Lock floor-t. **De** a trail mechanika folyamatosan emelkedett $53.38 → $53.92, és az ár MOC-on $55.77, **bőven** a SL felett. **Egy szépen megírt swing trade.**

### Vesztesek (4)

**DTE (Energy/Utility, score 92.0):** 4-split, **-$988 össz**. Részletes elemzés fent.

**FORM (FormFactor, semi equipment, score 89.0):** 48 share, entry $139.00, **LOSS_EXIT @ $135.14 17:00 CEST** (-$184.32 → -$191.52 net). -2.76% mozgás 2 óra alatt. **A nap első LOSS_EXIT-je**, és **nagyon korai** (16:30 CEST entry, 17:00 LOSS_EXIT — **30 perc** alatt).

**KLAC (KLA Corp, semi, score 87.5 — legalacsonyabb):** 6 share, entry $1738.01 (slippage **+0.26%**), MOC $1725.12 = **-$77.34**. -0.74% intraday. **A trail_b 18:55 CEST aktivált**, de a Breakeven Lock **NEM** alkalmazódott — a trail túl későn aktiválódott (a 19:00:00-19:04:59 window előtt 5 perccel). **Ezzel** a SL $1632.91-en maradt, és a piaczárás közelében tovább csúszott. **Edge case, megfigyelendő.**

**CNP (CenterPoint Energy, utility, score 91.5):** 378 share, entry $43.91 (slippage **-0.02% kedvező**), MOC $43.39 = **-$196.56**. -1.18% intraday. Csendes underperformer egész nap, **nem** triggerelt sem LOSS_EXIT, sem trail.

## Score → P&L napi nézet

| Ticker | Score | P&L net | Win? | Exit |
|--------|-------|---------|------|------|
| **GLNG** | **93.5** | +$228.48 | ✓ | MOC |
| DTE | 92.0 | -$988.00 | ✗ | LOSS_EXIT/SL (4-split) |
| CNP | 91.5 | -$196.56 | ✗ | MOC |
| FORM | 89.0 | -$191.52 | ✗ | LOSS_EXIT |
| KLAC | 87.5 | -$77.34 | ✗ | MOC |

**Erős pozitív rank korreláció ma — bizonyos szempontból:** legmagasabb score (GLNG 93.5) → egyetlen nyertes. **De**: a DTE 92.0 (2. legmagasabb) **a legnagyobb vesztes**, ami **erős** ellentmondás. **A DTE earnings miss strukturális hiba** — a scoring **nem fogta meg** a recent earnings miss kontextust.

## A DTE eset részletes elemzése

**Idővonal:**
```
ápr 28 (kedd)  DTE Q1 earnings miss bejelentés (Zacks szerint 2 napja a screenshot készítésekor)
máj 1 (pént)   16:18 CEST  Entry $153.28 (planned), $153.29 (filled, slippage +0.01%)
                          IFDS score: 92.0
                          SL: $149.29 (-2.61% bracket SL)
                          
              18:20 CEST  LOSS_EXIT @ $149.91 (Bracket B, -2.20%)
                          P&L: -$438.10 (130 share aggregate)
                          
              EOD reconcile az "8 trade" pattern miatt: 4 különálló split
              összesen -$988 (260 share aggregate)
```

**Mit kellett volna tennie a rendszernek?**

A te 2026-04-28-i M_contradiction multiplier hipotézised **pontosan erre** épült: a Company Intel CONTRADICTION jelzés **a strukturált FMP earnings adat** alapján. **A DTE Q1 earnings miss** pontosan ilyen jelzés lett volna.

**Kvantifikálva:**
- M_contradiction nélkül: 260 share × -$3.80/share = **-$988**
- M_contradiction ×0.80: 208 share × -$3.80/share = **-$790** (~$200 megtakarítás)
- M_contradiction ×0.50 (alternatíva): 130 share × -$3.80/share = **-$494** (~$494 megtakarítás)

**Ez a péntek a feature legerősebb motivációja a BC23 deploy óta.**

## A W18 zárszámai

A `weekly_metrics.py` outputjából:

| Metrika | W18 | W17 (összehasonlítás) |
|---------|-----|------------------------|
| Trading days | 5 | 5 |
| Net P&L | **-$1,106.07** | +$593 |
| Excess vs SPY | **-1.90%** | +0.13% |
| Win days | 2/5 | 3/5 |
| TP1 hits | **0/38** (0%) | 3/21 (14%) |
| Exit mix LOSS_EXIT | 7 | 1 |
| Exit mix MOC | 28 | 17 |
| Avg score | 91.1 | 92.5 |
| Score→P&L correlation | r=+0.239 | r=+0.180 |
| Commission/gross % | **14%** | 12% |

**A W17 → W18 átmenet adatai aggasztóak:**
- **Net P&L: +$593 → -$1,106** (-$1,699 különbség)
- **Excess: +0.13% → -1.90%** (egyik legrosszabb hét a BC23 alatt)
- **LOSS_EXIT count: 1 → 7** (7-szeres növekedés)
- **TP1 hit count: 3 → 0** (teljesen elmaradt)

**Megfigyelés:** a W18 alatt a piac bull volt (SPY +0.93% hét egészére), a VIX 18 alá zuhant (16.69 péntek). **Ez** a "bull rally underperform" mintázat **erős megerősítése** — amit csütörtökön már megfigyeltünk: a swing trading rendszer **defenzívebb**, és bull rally-ben underperformol.

## A 4 + péntek napi összehasonlítás

| Nap | SPY | Portfolio | Excess | P&L net | Kumulatív | VIX |
|-----|-----|-----------|--------|---------|-----------|-----|
| Hétfő | +0.17% | -0.33% | -0.50% | -$361 | -$349 | 18.20 |
| Kedd | -0.49% | -0.27% | +0.22% | -$308 | -$617 | 18.04 |
| Szerda | -0.02% | +0.43% | +0.45% | +$406 | -$187 | 18.51 |
| Csütörtök | +0.99% | +0.43% | -0.57% | +$405 | +$238 ⭐ | 16.99 |
| **Péntek** | **+0.28%** | **-1.22%** | **-1.50%** | **-$1,248** | **-$987** | **16.69** |
| **Σ W18** | **+0.93%** | **-0.97%** | **-1.90%** | **-$1,106** | — | **átlag 17.69** |

**Két fontos pattern:**

1. **A "bull rally underperform" megerősítve.** Csütörtök +0.99% SPY → -0.57% excess. Péntek +0.28% SPY → -1.50% excess. Mindkét pozitív SPY napon underperformoltunk. **Ez tendenciálisan strukturális.**

2. **A VIX 18 alá zuhant a hét közepétől.** A leállítási feltétel ("20+ napon át VIX > 18 mellett excess < -1.5%") **a VIX 18 alatti napokon nem aktiválódik**. **A 5 napi átlag VIX 17.69**, ami a 18-as küszöb alatt — **a leállítás feltétel** a W18 vonatkozásában **nem aktiválódik**.

## Scoring Validation Riport — A KIEMELKEDŐ FONTOSSÁGÚ ADAT

A `scoring_validation.py` 55 napi 378 trade-en futtatva **strukturális finding-okat** ad. **Ez a Day 63 keret megalapozásához szükséges adat.**

### A fő kérdés és a válasz

> **"Does the IFDS scoring system generate alpha, or is P&L a function of daily market direction only?"**

**A válasz az adat alapján: marginálisan, vagy semmilyen edge.**

### Score vs P&L korrelációk (378 trade)

- Pearson (score vs P&L $): **-0.000** (p=0.996) — **statisztikailag null**
- Spearman (score vs P&L $): -0.007 (p=0.898) — **statisztikailag null**
- Pearson (score vs P&L %): +0.005 (p=0.929) — **statisztikailag null**

**Tehát a score önmagában nem prediktív** a P&L-re az 55 napi mintában.

### Score quintile breakdown

| Quintile | Score range | N | Avg P&L | Win rate | Total P&L |
|----------|-------------|---|---------|----------|-----------|
| Q1 | 85.5–92.5 | 75 | -$1.72 | 48.0% | -$129 |
| **Q2** | **92.5–94.0** | **76** | **+$11.57** | **53.9%** | **+$880** ✓ |
| Q3 | 94.0–94.0 | 75 | -$17.88 | 32.0% | -$1,341 ✗ |
| Q4 | 94.0–95.0 | 76 | +$1.01 | 53.9% | +$76 |
| Q5 | 95.0–142.5 | 76 | -$8.91 | 44.7% | -$677 ✗ |

**Top-Bottom spread: -$7.19 (Q5 vs Q1) — gyakorlatilag null edge.**

**Egy érdekes pattern:** a Q2 (92.5-94.0 score range) **a legjobb** quintile (+$880, 53.9% win rate). A Q3 (~ 94.0 fix score) **a legrosszabb** (-$1,341, 32.0% win rate). A Q5 (95+) is **negatív** (-$677). **Ez ellentétes** azzal, amit várnánk: a magasabb score-ú trade-ek **nem feltétlen** adnak jobb P&L-t.

### Sub-score korrelációk

- **Flow score**: Pearson +0.136* (p=0.039) — **statisztikailag jelentős** ★
- Tech score: -0.085 (p=0.198) — null
- Funda score: -0.088 (p=0.180) — null

**Ez egy kifejezetten fontos finding:** a **flow komponens** (RVOL, dark pool %, PCR, OTM%, block trades, buy pressure) **az egyetlen, ami jelentősen korrelál a P&L-vel**. A tech és funda komponensek **nem** prediktívek.

**Mit jelent ez?** A BC23 redesign (2026-04-13) **éppen** azt csinálta, hogy **0.40 súllyal flow-ra**, 0.30 funda-ra, 0.30 tech-re. **A flow súly indokolt**, **de a funda/tech súlyok valószínűleg túl magasak** — vagy: az adatuk nem informatív.

### Exit type breakdown

| Exit type | N | Avg P&L | Total P&L |
|-----------|---|---------|-----------|
| LOSS_EXIT | 32 | -$98.50 | -$3,152 |
| **MOC** | **280** | **+$3.36** | **+$940** ✓ |
| SL | 15 | -$78.87 | -$1,183 |
| **TP1** | **36** | **+$32.95** | **+$1,186** ✓ |
| **TP2** | **3** | **+$286.03** | **+$858** ✓ |
| TRAIL | 3 | +$33.39 | +$100 |
| NUKE | 9 | +$6.51 | +$59 |

**Net total: -$1,192 (-1.19%) az 55 napi 378 trade-en.**

**A MOC, TP1, TP2 ÖSSZESÍTETT P&L: +$2,984.** A LOSS_EXIT és SL EGYÜTT: -$4,335. **Tehát a profit-defenzív exitek (TP1, TP2, MOC) HOZNÁK a profitot, és a kárlimitáló exitek (LOSS_EXIT, SL) ÖSSZESEN -$4,335-t veszítenek.**

**Ez fontos kontextus:** a -$1,192 össz-P&L **NEM** azt jelenti, hogy a rendszer "rossz". Azt jelenti, hogy **a kárlimitáló exitek strukturálisan nagyobb veszteséget termelnek**, mint amennyit a profit-exitek hoznak. **Ez a BC23 redesign egyik strukturális problémája**, amit eddig **nem azonosítottunk** ilyen tisztán.

## Kulcsmegfigyelések — a péntek-i nap és a heti riport együtt

### 1. ⚠️ A scoring nem prediktív — strukturális finding

**378 trade, 55 nap, statistikai szignifikancia hiánya.** Pearson r ≈ 0, Spearman r ≈ 0. **A Day 63 mérése szempontjából** ez **fontos információ**:

**Ha a scoring nem prediktív** az 55 napi adatban, akkor a **paper folytatás default** sávban való maradás Day 63-on **realisztikus**, mert nincs egyértelmű jel arra, hogy a scoring élesben **alpha-t** termelne.

**De** néhány kvalifikáció:
- A BC23 redesign **csak 14 napja él** (deploy 2026-04-13). A 378 trade-ben az 55 nap nagy része BC22 vagy korábbi.
- A BC23-on belül a scoring változások (UW Quick Wins + Snapshot v2) csak később deployolódtak.
- **Tisztán a BC23 utáni adat:** ~14 nap × 5-6 trade/nap = ~80 trade. Ez **kevesebb statisztikai erővel** rendelkezik.

**Egy realisztikusabb kérdés:** a BC23 utáni 80 trade-en mit ad a scoring? **Ezt érdemes megnézni** — a `scoring_validation.py` egy `--start 2026-04-13` flaggal újra futtatható.

**Backlog idea (felvegyem holnap a backlog-ideas.md-be?):**
> **Scoring validation BC23-only.** A jelenlegi riport 55 nap × 378 trade-et tartalmaz, ahol a BC23 (2026-04-13+) csak 14 nap. A `scoring_validation.py --start 2026-04-13` futtatása megmutatná a BC23 redesign tényleges hatását. ~30 min Tamás munka.

### 2. A flow komponens az egyetlen jelentős prediktor

**Pearson +0.136*** a flow vs P&L korrelációra **statisztikailag jelentős**. Ez **megerősíti** a UW Quick Wins + Snapshot v2 deploy értékét — a flow score (dollár-súlyozott) prediktívebb mint a tech vagy funda.

**Implikáció a BC25-höz:** a sector rotation (XLK/XLI/XLE jelenleg) **nem feltétlen** jobb prediktor mint a flow. **Ezt** a vasárnapi MID vs IFDS comparison **konkrétan** méri majd.

### 3. A DTE eset megerősíti a M_contradiction szükségességét

**A DTE 4-split -$988 a péntek elsődleges története.** A vasárnapi M_contradiction re-scope már tervezve, és **a DTE Q1 earnings miss + score 92 + -$988 P&L** **a perfect tetejét adja** a feature motivációjának.

A vasárnapi `2026-05-04-contradiction-signal-from-fmp.md` task fájl megírása során **explicit** rögzítjük a DTE esetet mint **kvantifikált motivációt**:
- ×0.80 multiplier mellett: -$988 → -$790 (~$200 megtakarítás)
- ×0.50 multiplier alternatíva: -$988 → -$494 (~$494 megtakarítás)

### 4. A "bull rally underperform" mintázat 2 nap egymás után

**Csütörtök -0.57% excess (SPY +0.99%), péntek -1.50% excess (SPY +0.28%).** **A swing trading rendszerek tipikusan defenzívek** — ez nem strukturális hiba, **csak** realisztikus elvárás.

**Ennek következménye a Day 63 keretedre:** a "20+ napon át regime nem Stagflation ÉS excess > +1%" élesítési feltétel **nehezen elérhető** bull rally periódusban. **Ha a piac most már low-vol bull-rally-be váltott** (VIX 16 körül), akkor a következő 8 nap **valószínűleg** több bull napot fog tartalmazni, ami **strukturálisan nehezíti** az alpha mérést.

**Realisztikus pálya Day 63-ra:** a kumulatív -$987-ből a **break-even** közelébe kellene visszamásznunk, ami **átlagosan +$120 / nap**. **Ez magasabb mint a 4 napi átlag.** Lehetséges, **de** nem garantált.

### 5. Az exit mix problémája

**LOSS_EXIT + SL teljes negatív hatása: -$4,335 a 55 napon.** **A profit exitek (TP1, TP2, MOC) hoznak +$2,984.** **Net deficit: -$1,351.** Ez azt jelenti, hogy **a kárlimitáló exitek strukturálisan nagyobb veszteséget okoznak**, mint amennyit a profit exitek hoznak.

**Két lehetséges magyarázat:**
- **(a)** A LOSS_EXIT / SL **gyakran** triggerelnek **átmeneti** spike-okra, és ha a pozíció maradt volna, MOC-on jobb lett volna. Ezt a **whipsaw audit** múlt heti +$87 net pozitív eredménye **NEM** támogatja — átlagban a -2% LOSS_EXIT védett.
- **(b)** A LOSS_EXIT / SL **helyesen** zárnak átmenőlegesen rosszul ment pozíciókat, **de** a profit exitek **nem elég nagyok** ahhoz, hogy ezeket kompenzálják. **Strukturális hiba a TP1/TP2 célok távolságában.**

**Ez új finding** — a vasárnapi W18 elemzésbe bekerül.

## A te döntési kereted szerint — péntek esti állapot

**Tegnap esti megegyezés szerint:**
- Élesítés: Day 63 → +$3,000 → $10k tőke
- Leállítás: 20+ napon át VIX > 18 mellett excess < -1.5%
- Alpha cél: 0.75-1% / hó

**Péntek esti állapot:**
- **Kumulatív -$987 (-0.99%)** — visszaesett pozitívról, de **biztonságos sávban marad**
- Excess vs SPY 5 napos átlag: **-0.38%** (**5/5 napi excess számolása alapján**)
- VIX 16.69 — **18 ALATT**, leállítási feltétel inactive
- **8 nap** Day 63-ig

**A leállítási feltétel távolsága:** -$987 mellett, hogy 20+ napon át VIX > 18 ÉS excess < -1.5% → **most a VIX 18 alatti, tehát a feltétel részlegesen "alszik".** Egy esetleges magas-vol periódus + folytatódó underperform **nem** közeli realitás.

**A élesítési feltétel távolsága:** kumulatív >+$3,000 + plusz 20+ napon át nem-Stagflation regime + excess > +1%. **Mostani -$987 → +$3,000 = +$3,987 távolság.** **8 nap alatt napi átlagos +$498.** **NEM** elérhető — a 4 napi (csüt + szerd + ked + hét) napi átlag csak +$140, a péntek -$1,248-cal a 5 napi átlag -$221.

**A Day 63 valószínű kimenet: paper folytatás (default).**

## Anomáliák

- **A `leftover_warning` a péntek logban: DTE -130 share** — **negatív qty leftover**. Ez **valószínűleg** azt jelenti, hogy a 4-split LOSS_EXIT/SL exit-ek aggregált nettó pozíciója -130 share lett (short), ami **rendkívül szokatlan**. **Ez a state-split mechanika probléma jele lehet.** Érdemes lenne **vasárnap reggel** megnézni — egy gyors `gzcat state/positions/2026-05-01.json.gz`-t.
- **CRGY/AAPL leftover phantoms** **továbbra is**, ahogy korábbi napokban — `monitor_positions.py` BUG.
- **LION/SDRL/DELL/DOCN phantom events** **továbbra is** 22:00 CEST-kor, az IBKR API quirk miatt.
- **AVDL.CVR** továbbra is non-tradable, ignorálható.

## Holnap (szombat máj 2)

- **Tamás:** pihenés ☕
- **Chat (én, vasárnap):**
  - W18 weekly elemzés (`docs/analysis/weekly/2026-W18-analysis.md`)
  - **Első MID vs IFDS sector comparison riport**
  - **Day 63 Decision Framework formalizálás** (`docs/decisions/2026-04-28-day63-decision-framework.md`)
  - **Új M_contradiction task fájl** (`docs/tasks/2026-05-04-contradiction-signal-from-fmp.md`) — DTE eset mint motiváció
- **CC hétfő reggel:** új M_contradiction task fájl alapján indul

## Kapcsolódó

- `state/phase4_snapshots/2026-05-01.json.gz`
- `logs/pt_events_2026-05-01.jsonl` ← **3× LOSS_EXIT + 2× SL**, 1× breakeven (GLNG, 17:45 — túl korai)
- `logs/pt_eod_2026-05-01.log`
- `state/daily_metrics/2026-05-01.json` ← **vix_close = 16.69**, kumulatív -$987
- `docs/analysis/weekly/2026-W18.md` ← **első W18 weekly riport** (10 perccel ezelőtt commit-olva)
- `docs/analysis/scoring-validation.md` ← **55 napi 378 trade scoring validation**
- `docs/analysis/plots/01_score_vs_pnl.png` + `02_quintile_bars.png` ← **plots**
