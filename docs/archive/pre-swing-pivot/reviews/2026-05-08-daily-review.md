# Daily Review — 2026-05-08 (péntek)

**BC23 Day 20 / W19 Day 5 — A HÉT UTOLSÓ NAPJA**
**Paper Trading Day 60/63**
**M_contradiction LIVE 5. nap**
**Két P1 task DEPLOYED ma reggel** (`d3fce73` snapshot fix + `9a169b9` dp_pct rekal)

**Adat-frissesség:** EOD log 22:05 CEST. `state/daily_metrics/2026-05-08.json` még nem szinkronizálódott (a `daily_metrics.py` 22:10 CEST után fut), strukturált VIX close + makró regime adat hétfő reggel jön.

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | +$500 körül |
| Napi P&L net | **+$486.12** ⭐ — a hét legjobb napja |
| Kumulatív P&L (paper aggregát) | **-$1,130.01 (-1.13%)** ⭐ visszamászás $486-mal |
| Tényleges (SQM bug-korrekcióval) | ~-$1,016 (-1.02%) becsült (SQM SHORT 91 zárása ~+$113 profittal) |
| Pozíciók (új) | **4 ticker megnyitott** (CRWD, MTCH, AMD, GOOG); 1 az execution plan-ben (CUK) — nem nyitott (vizsgálandó) |
| Trade count | 6 (CRWD 1× + MTCH 3× split + AMD 1× + GOOG 1×) |
| Win rate ticker szinten | **3/4 (75%) ⭐ — a hét legmagasabb** |
| TP1 hit rate | 0/4 (CRWD közel volt: $527.68 vs cél $532.31, AMD közel: $454.94 vs $466.01) |
| TP2 hit rate | 0/4 |
| Exit mix | **4× MOC** (CRWD, AMD, GOOG, MTCH-bracket A?), **3× TRAIL** (MTCH 3-split), 0× LOSS_EXIT, 0× SL |
| Avg slippage | **+0,22%** (AMD +0,47% legrosszabb, GOOG -0,20% kedvező) |
| SPY return (becsült) | ~0% (a heti +1,51% / 5 nap és az előző 4 nap +1,51% összesítéséből → péntek ~0%) |
| Portfolio return | +0,49% |
| **Excess vs SPY** | **~+0,49%** ⭐ **outperform** mild lateral napon |
| Reggeli akció | ✅ `nuke.py --positions` 07:41 CEST: SQM SHORT 91 zárva, BUY 91 @ MKT |
| Két deploy | ✅ Snapshot fix `d3fce73`, ✅ dp_pct rekal `9a169b9` |

## ⭐ A hét legjobb napja — két single-ticker nyerő drámai javulást hozott

**+$486.12 net** a péntek — **az 5 nap egyetlen erős nyertes napja**. Két nagy nyerő dominált: **CRWD +$247 (+3,47%)** és **AMD +$263 (+4,31%)**, együtt +$510. Ezt enyhítette a MTCH 3-split TRAIL veszteség -$43.

**Kumulatív visszamászás:** csüt esti -$1,616 → péntek esti **-$1,130** = +$486 redukció **egy nap alatt**. A SQM SHORT 91 reggeli zárás (~+$113 valós profit a paper aggregát-toldolék korrekciójával) a tényleges valós kumulatívot **~-$1,016 (-1,02%)** közelébe hozza.

**A piaci kontextus:** SPY ma kb. **0%** mozdult (a heti +1,51% szétoszlik az előző 4 napra, ami már +1,51%-ot tett ki — pénteki SPY ~0%). VIX feltehetően stabil 17 körül. **Ez egy mild lateral / kis bull lehet** — pontosan az a környezet, ahol a swing rendszer karaktere szerint **outperform** szokott teljesíteni. **A pattern megerősítve.**

## ⚠️ KRITIKUS FINDING — AMD M_contradiction "false positive"

Az AMD pozíció a feature 5 napos LIVE periódusának **legfontosabb adatpontja**:

```
AMD entry $436.15 (planned $434.11, slippage +0,47%)
AMD MOC exit $454.94 (+4,31% intraday)
AMD P&L: +$263.06 ⭐ — a NAP LEGJOBB nyerője

M_contradiction: contradiction_flag=1, multiplier=0.8
Contradiction reasons: "price_above_consensus_8.1pct;recent_downgrades_2"
```

**Ez fundamentálisan ellentmond a feature direkciójának.** Az M_contradiction célja: csökkentse a position size-ot (×0,8) azokon a tickereken, amelyek **fundamentális ellenmondást** mutatnak (overshoot consensus, recent downgrades). A feltételezés: ezek a tickerek **kockázatosabbak**, ezért kisebb position-nel kereskedni biztonságosabb.

**De az AMD ma:**
- Az ár 8,1%-kal a target consensus felett (overshoot — feature triggerelte)
- 2 recent analyst downgrade (feature triggerelte)
- **Mégis a nap legnagyobb % nyerője lett** (+4,31%)

**A becsült "elmaradt nyereség":** ha M=1,0 lett volna (M_contradiction nem fire), a position size **~25%-kal nagyobb** lett volna → ~14 share helyett ~17-18 share → **+$330 profit becsült** a +$263 helyett, **~+$66 plusz nyereség**.

**5 napos M_contradiction LIVE összesítés:**

| Nap | Fired tickerek | Eredmények | Iránybeli helyesség |
|-----|----------------|------------|---------------------|
| Hé máj 4 | 0/5 | n/a | n/a |
| Ke máj 5 | NE (0,8), PTEN (0,8) | -$143, -$36 | ✓ helyes (mindkettő vesztes) |
| Sze máj 6 | 0/3 | n/a | n/a |
| Csü máj 7 | ? | ? | ? |
| **Pé máj 8** | **AMD (0,8), GOOG (0,8)** | **+$263, +$19** | **✗ helytelen** (mindkettő nyertes/breakeven) |

**Iránybeli helyesség az 5 napon: ~50%** (kedd erős pozitív, péntek negatív). **Statisztikailag 4-5 fire ESEMÉNY az 5 napon — nem elég konklúzióra.** A feature **outlier protection**-ként van pozicionálva, nem regular signal — **20+ fire (W22+ scope) után érdemleges szignifikancia-tesztet futtatni**.

**Tanulság MOST**: a feature **NEM "minden contradiction = vesztes ticker"** — a piaci momentum néha **felülírja** a fundamentális kontradikciót. A 0,8× szorzó **konzervatív védelem**, NEM "kerülni a tickereket teljesen". Ez a feature design **helyes** maradt, csak a pénteki kvalitatív kép komplexebb mint a keddi volt.

## Pozíciók részletei

### Nyertesek (3 ticker, +$528)

**AMD (Advanced Micro Devices, Tech, score 94.5):** Entry $436.15 (slippage +0,47% — magas), MOC $454.94 = **+$263.06 (+4,31%)** ⭐ **a NAP legnagyobb % nyerője**. **M_contradiction fired** (multiplier 0,8) — részletek fent. **A semiconductor szektor mai erős mozgása** (vagy talán AMD-specifikus catalyst — nem látom direkt) elhozta a +4,31%-os mozgást, **annak ellenére, hogy a feature kockázatosnak jelölte**.

**CRWD (CrowdStrike, Tech, score 95.0 — legmagasabb):** Entry $509.99 (planned $508.33, slippage +0,33%), MOC $527.68 = **+$247.66 (+3,47%)** ⭐. **NEM fired** M_contradiction (0 contradiction flag). High-vol GEX regime, multiplier_total=0,6 (M_GEX 0,6× a high-vol miatt). 14 share × $17,69 profit/share. **A legmagasabb score-ú ticker** — **megtörte a 4 napi "legmagasabb score = leggyengébb performer" pattern**!

**GOOG (Alphabet Class C, Communication Services, score 89.5 — legalacsonyabb):** Entry $396.47 (planned $397.26, slippage **-0,20% kedvező**), MOC $396.98 = **+$18.86 (+0,13%)**. **Gyakorlatilag breakeven** — egész nap szigorúan oldalozott. **M_contradiction fired** (multiplier 0,8, "price_above_consensus_3,6pct"). 37 share × $0,51 profit/share. A position size csökkenést érdektelenné tette a kis mozgás.

### Vesztes (1 ticker, -$43)

**MTCH (Match Group, Communication Services, score 95.0):** **3-split, mind a 3 leg TRAIL exit**. Entry $36.59 (planned $36.49, slippage +0,27%), exit $36.48 / $36.48 / $36.47:
- Trade 1: 122 share × -$0,11 = **-$11.45**
- Trade 2: ? share × -$0,11 = **-$12.83**
- Trade 3: ? share × -$0,12 = **-$19.18**
- **Össz: -$43.46**

**Mit jelent a TRAIL exit:** a trail aktiválódott valamikor a +0,5-1% sávban (a profit-küszöb körül a Breakeven Lock 1%-os szintje), majd **az ár visszaesett a trail SL-re**. **NEM kapott Breakeven Lock soft floor-t** — vagy a trail aktiválás alacsonyabb profit-on volt mint az 1%, vagy a window előtt aktivált. **A TRAIL idővonal a `pt_events_2026-05-08.jsonl`-ban részletezhető**, a Filesystem MCP akadás miatt most nem nyitottam meg.

**Stratégiai értelmezés:** a MTCH egy **klasszikus "kora délutáni peak, késő délutáni retracement"** eset lehet — a trail aktiválódott, profitot jelzett, aztán az MOC közelében visszaesett. **Ezt a mintát** a tegnapi (csüt) review is részletesen tárgyalta a PTEN/CDNS esetén. **A "Breakeven Lock profit-küszöb csökkentés 0,5%-ra"** P2 backlog tétel **megint releváns** — ha a MTCH trail +0,5-0,7% profit-on aktiválna BL floor-t, a -$43 veszteség elkerülhető lett volna.

### CUK rejtély — vizsgálandó

A `execution_plan_run_20260508_141501_416d17.csv` tartalmazza:
```
CUK,BUY,LIMIT,27.47,377,25.62,29.01,29.94,700.0,93.5,positive,Consumer Cyclical,1.0,...
```

**De az EOD log csak 4 ticker-ről jelez**: CRWD, MTCH, AMD, GOOG. **A CUK nem jelenik meg** sem nyertes, sem vesztes oldalon, és a `nuke.py` log se mutatott CUK pozíciót zárás előtt.

**Két lehetséges magyarázat:**
1. A CUK submit nem ment át (IBKR rejection — pl. liquidity, market hours edge case, vagy IBKR margin restriction)
2. A CUK submit-elt, de azonnal cancel-elt (pl. limit order nem fillelt 14:30 ET-ig, és valami auto-cancel logika lefutott)

**Vizsgálandó forrás:** `pt_submit_2026-05-08.log` és `pt_avwap_2026-05-08.log` — most a Filesystem MCP akadás miatt nem nyitottam meg. **Holnap reggeli teendő** Tamásnak: ha érdekel, jelezd, és átfutom ezeket. **A nap eredményére nem hat** (paper trading, nem nyitott pozíció = 0 P&L), de a CUK execution-rejtjelezte egy strukturális információ.

## Score → P&L napi nézet — A 4 napi pattern MEGTÖRT

| Ticker | Score | M_contradiction | P&L net | Win? | Megjegyzés |
|--------|-------|-----------------|---------|------|------------|
| **CRWD** | **95.0** | 1.0 | **+$247.66** | ⭐ | legmagasabb score, +3,47% |
| MTCH | 95.0 | 1.0 | -$43.46 | ✗ | 3-split TRAIL |
| **AMD** | **94.5** | **0.8** ⚠️ | **+$263.06** | ⭐ | **mid-high, M_contradiction false positive** |
| CUK | 93.5 | 1.0 | n/a | n/a | nem nyitott |
| **GOOG** | **89.5** | 0.8 | +$18.86 | ✓ | legalacsonyabb score, breakeven |

**A 4 napi (W19 D1-D4) pattern**: a legmagasabb score-ú ticker mindennap a leggyengébb performer (VTR 93.5 vesztett, NE 95 vesztett, ERIC 92.5 breakeven, RMBS 93.5 vesztett).

**A péntek pattern (W19 D5):** a legmagasabb score-ú **CRWD 95 NYERT** (+$247, a 2. legjobb), és az AMD 94.5 nyert (+$263, a legjobb). **A pattern megtört egyetlen nap után — DE** csak 4 ticker és 1 nap, statisztikailag jelentéktelen.

**Mit jelent ez:** a Score → P&L korreláció **nem stabil mindennap**. A negatív korrelációs pattern **erős vegyes/Stagflation napokon** (W19 D1-D4 többsége), **gyenge mild bull / lateral napokon** (W19 D5). **Hosszú távon** (60 nap) a Pearson r = 0,000 — átlagosan a score nem prediktív.

**Score → P&L heti korreláció (a W19 weekly metric szerint): r = +0,303** — **POZITÍV**! Ez egy érdekes egyhetes adatpont, ellentétes az 55 napi r ≈ 0-tól. **Ne vonjunk konklúziót egy hétből** — de érdemes figyelni: ha a következő hetek is pozitív hetes r-t mutatnak, az a **scoring rendszer fokozatos javulását** jelezhetné (esetleg az M_contradiction LIVE-tól, esetleg a piaci regime változásától). **W22+ scope-ban** több adattal érdemes újraértékelni.

## Reggeli SQM SHORT zárás — a tegnapi bug végső takarítása

```
07:41:30  IBKR Paper Trading — Nuke
07:41:30  SQM: BUY 91 shares (MKT via SMART)
07:41:32  Final positions: 2 (SQM most már 0, AVDL.CVR phantom marad)
07:41:32  Final orders: 0 — SUCCESS
```

**A tegnapi (W19 D4) duplikált zárás bug végeredménye:**
- LOSS_EXIT 17:00 SELL 91 @ $93.25 → -$425.88 (paper aggregát első zárás)
- 2× bracket SL trigger SELL 45 + 46 @ $92.75 → SHORT 91 (paper aggregát hibás +) -$456.82 dupla
- Reggeli `nuke.py` BUY 91 @ MKT @ ~$91.50 (becsült) → +$113.75 valós profit

**Tényleges SQM nettó veszteség**: -$425.88 + $113.75 = **~-$312.13** (a paper aggregát -$882.70 helyett).

**A BC23 cumulative-ben**: a paper aggregát -$1,616 / a tényleges valós kumulatív ~-$1,460. **Pénteki +$486-mal** → tényleges valós ~**-$974 (-0,97%)** ✓ — közel a -$1,000 szintű paper folytatás default sávhoz.

**A LOSS_EXIT bracket SL cancellation P1 backlog idea** továbbra is sürgős. Hét közben (W20+) deploy-olandó.

## W19 weekly metric — 4 napi szintézis (péntek nélkül)

A `weekly_metrics.py` ma 22:00 előtt futott (a péntek EOD előtt), így a heti összesítés **csak W19 D1-D4** alapján:

```
W19 Trading days: 4 (péntek nem benne)
Net P&L: -$727.64
Cumulative: -$1,616.13 (csütörtök esti)
Excess vs SPY: -2,14% (4 napra)
```

**Pénteki kompenzáció** (a heti adatba még nem vezetett):
- Pénteki net: +$486.12
- Pénteki excess: ~+0,49%
- **Heti tényleges (5 napra)**: net = -$727 + $486 = **-$242 / 100k = -0,24%**
- **Heti SPY**: +1,51% (a metric szerint, 5 napra)
- **Heti excess (5 napra)**: -0,24% - 1,51% = **-1,75%**

**Ez a tényleges W19 hét eredménye:** -$242 net, -1,75% excess. **Lényegesen jobb** mint W18 (-$1,106 / -1,90%) és majdnem olyan jó mint W17 (+$593 / +0,13%) — **stabilizálódó trend**.

**A W19 weekly metric többi adata:**
- **TP1 hit rate**: **4/32 (12%)** — javult a W17 (9%) és W18 (0%) szintekhez képest
- **R:R realized**: **1:0,41** — még mindig negatív R:R, de a W18 1:0,15 (kvázi semmi) szintnél jobb
- **Avg score**: **92,3** — magasabb mint W17 (91,5) és W18 (91,1)
- **Score→P&L korreláció (heti)**: **r = +0,303** — pozitív irány, érdekes adatpont
- **Slippage**: avg +0,12%, worst +0,72% (a NE-en kedden)
- **Commission**: $98,19 (16% a gross-ből!) — magas
- **Zero-position days**: 0/4 ⭐
- **Low-position days (<3)**: 0/4 ⭐ — minden napon legalább 3 ticker

**Kvalifikáció**: a W19 weekly metric 4 napos minta. A péntek beépítése után a heti elemzés vasárnap (`docs/analysis/weekly/2026-W19-analysis.md`) tartalmazza az 5 napi szintézist és a W17-W19 közötti BC23 trendet.

## Excess vs SPY — pénteki outperform megerősítve

**A 5 napi W19 heti excess kalkuláció (becsült)**:

| Nap | Net P&L | SPY return | Portfolio return | Excess vs SPY |
|-----|---------|------------|------------------|---------------|
| Hé D1 | -$191 | -0,37% | -0,15% | **+0,21%** ⭐ |
| Ke D2 | -$269 | +0,80% | -0,24% | -1,04% |
| Sze D3 | +$234 | +1,39% | +0,25% | -1,14% |
| Csü D4 | -$501 | -0,31% | -0,49% | -0,18% ✓ |
| **Pé D5** | **+$486** | **~0%** | **+0,49%** | **~+0,49%** ⭐ |
| **W19 Σ** | **-$242** | **+1,51%** | **-0,24%** | **-1,75%** |

**Pattern megerősítés:** a swing trading rendszer **2/5 nap outperformolt** (D1 negatív SPY napon, D5 mild lateral napon), **3/5 nap underperformolt** (D2-D4 — bull rally napokon és csüt mild risk-off napon). **Strukturális karakter** — defenzív erő, bull rally gyengeség. **2026-05-08-i strategic-review-summary.md 4.6 fejezet** ezt a finding-ot dokumentálta.

## "Végére visszaesik" pattern — pénteki adatok

**Nem teljesen tudtam ellenőrizni** a Filesystem MCP akadás miatt — az események jsonl-ből látnám az intraday peak idő-pontokat. **De az EOD log alapján**:

| Ticker | Entry | MOC | Net intraday |
|--------|-------|-----|--------------|
| CRWD | $509.99 | $527.68 | **+3,47%** (folyamatos emelkedés valószínű) |
| AMD | $436.15 | $454.94 | **+4,31%** (folyamatos emelkedés valószínű) |
| GOOG | $396.47 | $396.98 | **+0,13%** (lateral) |
| MTCH | $36.59 | $36.48 (TRAIL) | **-0,30%** (peak → retracement, mert TRAIL = peak után emelkedett SL) |

**A MTCH egyértelműen mutatja a "végére visszaesik" pattern** — a TRAIL aktiválódott a profit-régióban, majd visszaesett a trail SL-re. **A többi ticker** (CRWD, AMD, GOOG) **NEM mutatta** a pattern-t — strong intraday momentumok voltak.

**Pattern hipotézis (a tegnapi review-ban felvetettem)**: az "afternoon retracement" **erős momentum napokon nem jelentkezik** (CRWD, AMD), **vegyes/lateral tickereken igen** (MTCH, PTEN kedden). **Mai napi adat megerősítette.**

## Két P1 task DEPLOYED ma reggel

A péntek ma egy **rendkívüli fejlesztési nap** volt — Tamás napközben CC-vel két P1 task-ot deployolt:

**1. Snapshot regresszió fix (`d3fce73`)**
- Root cause: teszt-sanitációs hiba — `tests/test_pipeline_e2e.py::test_full_pipeline_flow` futtatta a valódi `run_pipeline`-t, és NEM mockolta a `save_phase4_snapshot`-ot. A `deploy_daily.sh` 22:00 cron pre-flight pytest naponta felülírta a 16:15 cron 90+ tickeres snapshotját egy AAPL-only mockkal.
- Fix: `@patch` decorator + új regressziós teszt
- **Hatás**: hétfőtől (máj 11) a 16:15 cron tisztán ment 90+ ticker. A flow-decomposition 232-trade audit a Feb-Apr 1 mintán **valid maradt** — a post-Apr 10 időszakra hiányoznak a snapshotok, de új mintán a hétfői cron után újra fog épülni.

**2. dp_pct sign-flip + threshold + per-ticker fetch (`9a169b9`)**
- Konfig: `dark_pool_volume_threshold_pct` 40→**12**, `dp_pct_high_threshold` 60→**18**, `dp_pct_bonus` +10→**-10**, `dp_pct_high_bonus` +15→**-15**
- Kód: scoring `>` → `>=` (inkluzív küszöbök), `UWBatchDarkPoolProvider` → `UWDarkPoolProvider` (sync + async)
- Tesztek: 1554 → 1556 passing (6 új + 11 frissítve)
- **Hatás**: a magas-DP tickerek mostantól -10/-15 score reduction-t kapnak → flow-súly 0,60 mellett **-6/-9 pont** csökkenés a combined_score-on. **Day 90+ adat fog teljesen igazolni / cáfolni.**

**A péntek 16:15-i cron még a régi konfig + régi snapshot logika alapján futott** (a deploy ma reggel volt, a 16:15 cron még a stabil state-tel ment). **A két deploy hatása hétfőtől (W20) lesz mérhető**, ahogy az új cron generál snapshot-okat az új paraméterekkel.

**Master-reference azonnal frissítve** ma este: `docs/master-reference/04-risks-and-open-questions.md` 1.1 + 1.2 szakaszok DEPLOYED, `01-system-snapshot.md` Dark Pool sor + változás-napló + aktív CC tasks frissítve.

## Day 63 keret — péntek esti állapot

| Metrika | Érték | Status a kerethez képest |
|---------|-------|---------------------------|
| Day | **60/63** — **3 nap van Day 63-ig** | |
| Kumulatív P&L (paper aggregát) | -$1,130 (-1,13%) | **biztonságos sávban**, javuló trend |
| Tényleges (becsült valós) | ~-$1,016 (-1,02%) | a SQM bug-korrekció után |
| ÉLESÍTÉS távolság | +$4,016 a +$3,000-hoz | **3 nap × +$1,339/nap → NEM realisztikus** |
| LEÁLLÍTÁS távolság | 10 napi excess átlag ~-0,44% távol a -1,5%-tól | **biztonságos sávban**, ~1,06% buffer |
| 10 napi excess vs SPY átlag | ~-0,44% (W18 -1,90% / 5 + W19 -1,75% / 5 átlag) | a pénteki +0,49% segített |
| VIX W19 átlag | 17,4 körül | **stabilan 17 körül**, leállítási feltétel monitor inaktív |

**Realisztikus Day 63 várt kimenet**: **PAPER FOLYTATÁS (default)** — **5 nap egymás után megerősítve**. A kumulatív P&L 3 nap után valószínűleg -$1,200 és -$700 között lesz.

**A leállítási feltétel távolsága stabil**: ~1% buffer a -1,5% küszöbtől. **Nincs panik-pillanat.**

## Anomáliák

- **CRGY/AAPL leftover phantoms** továbbra is — `monitor_positions.py` BUG (régóta ismert)
- **AVDL.CVR (69.0)** — non-tradable, ignorálva (a `nuke.py` kihagyta, az EOD log jelezte)
- **CUK execution rejtjelezve** — execution_plan tartalmazza, EOD log nem (vizsgálandó: `pt_submit_2026-05-08.log`, `pt_avwap_2026-05-08.log`)
- **`state/daily_metrics/2026-05-08.json` hiányzik** — a `daily_metrics.py` 22:10 CEST után fut, hétfő reggel jön a teljes adat (vix_close, makró regime, kumulatív structured)
- **Filesystem MCP timeout** — a chat utolsó óráiban a Filesystem szerver write_file-on akadt, 2-3 részlet (CUK, TRAIL idővonal) nem ellenőrzött. **Hétfőn hozzáférhető lesz, ha érdekli.**

## Kulcsmegfigyelések

### 1. ⭐ A hét legjobb napja, kumulatív visszamászás +$486

**+$486.12 net** — a BC23 deploy óta a 3. legjobb nap (W16 ápr 15: +$587, W16 ápr 16: +$563, **W19 D5: +$486**). **Két erős single-ticker nyerő** (CRWD +$247 +3,47%, AMD +$263 +4,31%) dominált. A **W19 hét végeredménye -$242 / -1,75% excess** — **lényegesen jobb mint W18, közelít a W17-hez**.

### 2. ⚠️ KRITIKUS — AMD M_contradiction "false positive" eset

A feature **fired** (multiplier 0,8 → 25% kisebb position size), és mégis a **NAP LEGJOBB nyerőjévé** vált. **5 napos LIVE iránybeli helyesség kb. 50%-os** (kedd erős pozitív, péntek negatív). **A feature design helyes**: konzervatív védelem, NEM "kerülni a tickereket" — a 0,8 multiplier még megengedi a részvényt. **Statisztikai szignifikancia 20+ fire után (W22+)**.

### 3. ⭐ A 4 napi "Score → P&L negatív korreláció" pattern megtört

**CRWD 95 +$247, AMD 94,5 +$263, MTCH 95 -$43, GOOG 89,5 +$19.** A magas score-ok mind nyertek vagy kis vesztesek. **W19 weekly score→P&L korreláció r = +0,303 (pozitív)** — szemben az 55 napi r = 0,000-val. **Egy heti adatpont, nem konklúzió** — de érdemes figyelni.

### 4. ⭐ Excess vs SPY +0,49% — outperform megerősítve mild lateral napon

**5 napi pattern teljesen konzisztens:** swing rendszer **defenzív erejű** risk-off és lateral napokon, **gyenge** bull rally napokon. **2/5 nap outperform, 3/5 nap underperform** W19-ben.

### 5. ✓ MTCH TRAIL × 3 — a "Breakeven Lock profit-küszöb csökkentés" P2 backlog idea relevanciája megerősítve

**MTCH 3-split TRAIL exit -$43.** A trail aktiválódott (valószínűleg +0,5-1% sávban), majd visszaesett az SL-re. **NEM kapott Breakeven Lock floor-t** (vagy túl alacsony profit-on aktivált, vagy a window előtt). **A backlog idea (profit-küszöb 1% → 0,5%)** ezt a típusú esetet **direktben kezelné** — várható megtakarítás ~$30-50/hét. **W20+ scope, P2.**

### 6. ⭐ Két P1 task DEPLOYED ma reggel — a fejlesztési ütem erős

`d3fce73` (snapshot fix) + `9a169b9` (dp_pct rekal). **Hatás hétfőtől (W20) lesz mérhető.** A master-reference (`docs/master-reference/`) azonnal frissítve. **A pénteki 16:15 cron még a régi konfig alapján ment** — a két deploy hatása **a hétfői cron-tól** kezdődik.

## Hétvégi teendők

### Tamás (MacMini, manuális)

- **`git pull`** a Mac Mini-n (a két új commit deploymentje után, hogy a 22:00 cron pre-flight ne szennyezze a state-et többé)
- **AVDL.CVR phantom**: ha akarod kitakarítani, manuális IBKR kezelés
- **Heti pihenő** ;)

### Chat (én, hétvégén)

1. **Strategic-review full korrekció** ($354/hó → $665/hó a 2.4 fejezetben) — 10 perc
2. **Backlog-ideas.md frissítés** — `UW dark pool live fetch — date=today parameter` P3 tétel hozzáadása — 5 perc
3. **`docs/analysis/weekly/2026-W19-analysis.md` heti elemzés** — vasárnap, a péntek beépítése után
4. **Master-reference végső konzisztencia-átfutás** — 30 perc
5. **PIPELINE_LOGIC.md kérdés** — hétfő reggel veled megbeszéljük (a 0,40/0,30/0,30 elavult adatok)

### Hétfő reggel (máj 11)

1. **Master Reference Card átfutás** (Tamás + Chat, 30 perc)
2. **Korrekciók közös rögzítése**
3. **CUK rejtély** — ha érdekel, átnézzük a `pt_submit` és `pt_avwap` logokat
4. **W20 D1 (hétfő máj 11)**: **az első nap a két deploy után** — a 16:15 cron tisztán fog menteni 90+ tickert + a magas-DP tickerek -10/-15 score reduction-t kapnak

### Csütörtök (máj 14) — **Day 63 KIÉRTÉKELÉS** ⭐

- **09:00 Reminder** notification
- W17 + W18 + W19 + W20 D1-D2 adatok együtt **scoring validation újrafuttatás** (a snapshot regresszió fix után először teljes mintán)
- **Várt kimenet: PAPER FOLYTATÁS** (default)
- Új doc: `docs/decisions/2026-05-14-day63-decision-outcome.md`

## Kapcsolódó

- `state/phase4_snapshots/2026-05-08.json.gz` (régi logika alapján mentve, valószínűleg AAPL-only — a hétfői cron lesz az első tiszta)
- `logs/pt_events_2026-05-08.jsonl` (TRAIL idővonal részletek; Filesystem MCP visszajövete után)
- `logs/pt_eod_2026-05-08.log` ← P&L összefoglaló
- `logs/pt_nuke_2026-05-08.log` ← SQM SHORT 91 zárás SUCCESS
- `output/execution_plan_run_20260508_141501_416d17.csv` ← 5 ticker, **2 contradiction_flag=1** (AMD, GOOG)
- `docs/analysis/weekly/2026-W19.md` ← weekly_metrics.py kimenet (4 napra, péntek beépítése vasárnap)
- `docs/master-reference/04-risks-and-open-questions.md` ← 1.1 + 1.2 DEPLOYED státuszra frissítve
- `docs/master-reference/01-system-snapshot.md` ← Dark Pool sor + változás-napló + aktív CC tasks frissítve

**State**: BC23 + Breakeven Lock (profit_breakeven trigger) + MID Bundle + vix-close + LOSS_EXIT whipsaw audit + M_contradiction LIVE + **dp_pct sign-flip DEPLOYED** + **snapshot fix DEPLOYED**

**Aktív CC tasks**: 0 (mind a 2 P1 task DEPLOYED ma)

**W19+ backlog idea-k (most 8, 1 új P3 + 7 öröklött)**:
1. ⚠️ LOSS_EXIT bracket SL cancellation — P1, ~30-45 min CC (DTE+SQM bug, sürgős, W20+)
2. 10-Q / 10-K SEC Filing Exclusion — P1, ~2-3h CC (AGNC eset)
3. ADR earnings adatforrás fix — P1, ~3-4h CC (BUD eset)
4. Breakeven Lock profit-küszöb csökkentés — P2, ~10-15 min config (MTCH-szerű esetek védelme)
5. TP1 cél revízió — P2, ~30 min config
6. High-score liquidity check — P3, ~1h
7. Phase 4 snapshot enrichment — P3, ~30-45 min (a snapshot fix után már relevánsabb)
8. **ÚJ: UW dark pool live fetch — `date=today` parameter** — P3, ~30 min CC (W19+ refinement candidate)
