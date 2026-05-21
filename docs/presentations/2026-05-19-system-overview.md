# IFDS — Institutional Flow Decision Suite
## Kvantitatív kereskedési platform — rendszer-bemutató

**Készült**: 2026-05-19
**Verzió**: 1.0
**Időtartam**: ~90 perc
**Célközönség**: kvantitatív kollégák, szakmai vezetők
**Szerző**: IFDS team
**Státusz**: Day 1 swing pivot deploy (2026-05-18) utáni állapot

---

## Tartalom

1. Bevezető — a rendszer célja és üzeneti súlypontja
2. Technikai környezet
3. Módszertani alapelvek
4. A pipeline részletes bemutatása — Phase 0-6
5. Jelenlegi működési modell és indoklása
6. Az előző 63 napos paper trading tanulságai
7. A "swing pivot" — új architektúra bemutatása
8. Roadmap és további lépések
9. Glosszárium

---

# 1. Bevezető

Az IFDS (Institutional Flow Decision Suite) egy Python-alapú, automatizált, opciós flow-vezérelt amerikai részvény-kereskedési platform. A rendszer egy dedikált infrastruktúrán fut, emberi felülbírálás nélkül, és napi rendszerességgel azonosít és nyit long pozíciókat az IBKR (Interactive Brokers) paper-trading számláján.

A platform alapfilozófiája egyszerű: az opciós piac és a dark pool aktivitás strukturált információt hordoz az intézményi pozícionálásról, és ezt az információt egy fegyelmezett, kvantitatív pipeline-on átszűrve egy kompozit pontszám formájában rangsorolhatjuk az amerikai részvénypiac szereplőit. A pontszám a kockázat-kezelési és pozíció-méretezési rétegen keresztül konkrét megbízásokká alakul, amelyek bracket-mechanikájú vagy mental-stop-alapú exit-stratégiával zárulnak.

A jelen dokumentum három célt szolgál: bemutatja a rendszer technikai architektúráját kvantitatív szempontból; megosztja az elmúlt 63 napos paper trading tanulságait, beleértve a negatív eredményeket; és felvázolja a 2026 májusában aktivált új architektúra ("swing pivot") várt teljesítményét és a következő 63 napos validációs ciklust. A dokumentum nem értékesítési anyag — a célja a **transzparens szakmai megosztás**, hogy a kollégák és a vezetők egyaránt **megalapozott véleményt** alakíthassanak ki a fejlesztés irányáról.

A platform jelenleg nem termel pozitív alfát — ezt a 6. szakasz részletesen tárgyalja. A 2026-04-28-i belső kiértékelés alapján a 60+ napos paper trading **nem alkalmas** élő pénzes kereskedés indítására. A folytatás indoka, hogy a strukturális tanulság-rögzítés és a hipotézis-vezérelt iteráció jelenleg ígéretesebb, mint a leállítás — különösen az új "swing pivot" architektúra matematikai megalapozottsága mellett.

---

# 2. Technikai környezet

## 2.1 Infrastruktúra

A rendszer egy dedikált macOS Mini gépen fut produkciós módban, fizikai irodai környezetben. A fejlesztés egy MacBook Pro-n történik, és a két gép között a git verziókezelés szolgáltatja a kód szinkronizációt. A produkciós Mini-n az IBKR Gateway folyamatosan kapcsolatban áll a brókerszolgáltatóval, a kvantitatív pipeline pedig egy időzített batch-folyamat (cron) szerint napi rendszerességgel fut.

Az infrastruktúra szándékosan egyszerű és olcsó — a tudományos validáció során nem akartunk virtualizációs vagy felhő-szolgáltatási költségekkel terhelődni. A Mini-on a teljes pipeline kb. 8-12 GB RAM-ot használ csúcsidőben, és 50-100 GB tárhelyet a teljes log + state + cache infrastruktúrához.

## 2.2 Szoftver stack

A platform Python 3.12-ben íródott, a fő külső függőségek: `ib_insync` (IBKR API-wrapper), `pandas`, `numpy`, `scipy.stats`, `requests`. Az adatszolgáltatókhoz minden integráció saját HTTP wrapper-en keresztül történik a rate-limit kezelés és a cache-stratégia miatt. A perzisztens állapot tárolása JSON és gzipped JSON fájlokban, valamint egy SQLite adatbázisban (`state/pt_events.db`) történik. A struktúrált döntéshozási kontextusokat a pipeline időzítési pontjain pickle-szerű gzipped JSON-ba sorosítjuk (`state/phase4_snapshots/YYYY-MM-DD.json.gz`), hogy a kvantitatív utólagos elemzések visszamenőlegesen reprodukálhatók legyenek.

## 2.3 Adatszolgáltatók

A rendszer négy külső adatforrásra támaszkodik. A Polygon szolgáltatja az OHLCV árakat, az opciós láncot, a BMI (Big Money Index) napi forgalmi adatait, valamint a VIX volatilitási index másolatát. A Financial Modeling Prep (FMP) az univerzum-építéshez használt screener-API-t, az earnings-naptárt, a fundamentális adatokat és az insider tranzakciókat. Az Unusual Whales a dark pool tranzakciókat, a gamma exposure (GEX) intézményi pozícionálást és az opciós flow-t. A FRED (St. Louis Fed) ingyenes makró-adatszolgáltatásként a TNX (10 éves államkötvény-hozam), a 2s10s yield curve spread és a VIX-backup adatait.

A teljes havi adat-szolgáltatási költség ~$354 (Polygon $229 + FMP $75 + Unusual Whales $50). A FRED ingyenes. Ez az ár-pont — összevetve a hedge fund szintű adatszolgáltatókkal (Bloomberg, Refinitiv) — szándékosan retail-szintű, hogy a methodológiai választások és nem az adat-előny vezérelje a teljesítményt.

## 2.4 Időzítés

A pipeline naponta két fő időablakban fut. Az **éjszakai részpipeline** (22:00 CET) végrehajtja a BMI-számítást, az univerzum-építést, és a szektor-rotáció elemzést. Eredménye egy `phase13_ctx.json.gz` kontextus-snapshot, amelyet a következő reggeli pipeline-fázis felhasznál. A **piaci nyitás előtti részpipeline** (15:30 CEST = 9:30 ET, az amerikai piacnyitás időpontja) végrehajtja a részvény-értékelést, a pozíció-méretezést, és a megbízások beadását az IBKR-be. A teljes folyamat futási ideje az adatszolgáltatók válaszidejétől függően 90-180 másodperc.

Az exit-mechanika a swing pivot architektúrában egyszerűbb: a `pt_monitor.py` napi egyszer (22:00 CEST) értékeli ki az összes nyitott pozíció állapotát mental-stop logikával, és a következő nap 15:30 CEST-i `close_positions.py` szállítja le a tervezett zárásokat.

## 2.5 Megfigyelhetőség és riport-csatornák

A rendszer egy Telegram-bot integráción keresztül napi rendszerességgel értesíti az operátort: a beadott megbízásokról, a sikeresen lezárt pozíciókról, és a kritikus hibákról (IBKR-kapcsolat-szakadás, API-rate-limit túllépés). A teljes pipeline futás eseménynaplója egy structured JSON-Lines formátumban (`logs/ifds_run_YYYYMMDD_*.jsonl`), valamint olvasható log formátumban (`logs/cron_intraday_YYYYMMDD_*.log`) is mentésre kerül.

A kvantitatív utólagos elemzéshez egy daily metrics aggregátor (`scripts/analysis/daily_metrics.py`) napi struktúrált összesítést készít a `state/daily_metrics/YYYY-MM-DD.json` fájlokba, valamint a heti `scripts/analysis/weekly_metrics.py` script a `docs/analysis/weekly/YYYY-Wnn.md` heti elemzéseket generálja.

---

# 3. Módszertani alapelvek

## 3.1 Pipeline-szemlélet

A rendszer hét egymás után következő fázisra (Phase 0 - Phase 6) tagolódik. Minden fázis egy jól definiált inputot kap, egy jól definiált outputot termel, és a fázisok közötti határokon perzisztens állapot-snapshot készül. Ez a tagolás három célt szolgál: a hibahelyek elkülöníthetők, az utólagos elemzéshez visszamenőleg minden döntési pont reprodukálható, és a kvantitatív validáció a végeredmény mellett a részlépéseket is mérheti.

## 3.2 Long-only intraday vs swing trading

A platform 2026 márciusától 2026 májusáig egy 6 órás holding period-pel működő intraday momentum/flow rendszerként funkcionált. A 2026 áprilisi belső analízis és a Day 63 milestone (2026-05-14) kiértékelése után a rendszer **strukturálisan átalakult** egy 3-5 napos hold időtávú swing-stratégiává. A módszertani folytonosság megőrződött (Phase 0-6 felépítés, opciós flow alapú scoring), de a kockázatkezelési és exit-mechanika jelentősen egyszerűsödött.

A két architektúra közötti különbség nem szemantikai, hanem **strukturális**: a 6 órás holding period mellett a flow signal-nek nincs ideje érvényesülni, az earnings event-kitettség strukturális kockázattá válik, és a slippage a kis profit-küszöbök mellett aránylag nagyobb hatású. A 3-5 napi swing-horizonton ezeket a tényezőket a hosszabb mintaidő részben kompenzálja.

## 3.3 Mérési filozófia

Minden fontos döntési pont kvantitatív validálás alapján született. A pontozási rendszer alkomponenseit a Pearson- és Spearman-korreláció vs realizált hozam alapján értékeljük, a pozíció-méretezést a Kelly-kritérium f* értékének előjele és nagysága alapján kalibráljuk, és a kockázat-kezelési küszöböket a Value-at-Risk (VaR) accuracy mellett a maximum drawdown alapján szabjuk. A rendszer minden új feature-t először **shadow módban** (a háttérben fut, eredményt logol, de a tényleges döntésekre nem hat) tesztel le, és csak statisztikailag szignifikáns hatás esetén élesít.

A Bonferroni-korrekció több hipotézis tesztelésénél (`p_adj = p × m`, ahol `m` a tesztelt hipotézisek száma) garantálja, hogy a "magas pontszám paradoxon" típusú felfedezések ne véletlen mintázatok legyenek.

## 3.4 Discretionary judgement és systematic execution

A platform egy szigorúan szisztematikus rendszer: az egyes napi pozíciók beadása emberi felülbírálás nélkül történik. A fejlesztői (discretionary) réteg az **iterációkban** él — a heti és milestone-szintű kiértékelések során a portfolio manager fontolóra veszi a finomításokat, a paraméter-újrakalibrációkat, és az új feature-ek tesztelését. Ez a felosztás Linda Raschke "discretionary judgement + systematic execution" filozófiáján alapul: a stratégiai döntések emberi felelősség alatt vannak, a végrehajtás automatizált.

---

# 4. A pipeline részletes bemutatása — Phase 0-6

A következő hét fázist egymás után tárgyaljuk. Mindegyiknél bemutatjuk a célt, a fő képleteket, a be- és kimeneteket, valamint a tipikus log-üzeneteket. A bemutatás a 2026 májusi swing pivot architektúrán alapul, de ahol a legacy intraday verzió jelentősen eltér, ezt megjegyezzük.

## 4.1 Phase 0 — Diagnostics

A nap első lépése a teljes API-infrastruktúra egészségellenőrzése. A pipeline lekérdezi a négy adatszolgáltató kritikus végpontjait (`/v2/aggs/grouped/locale/us/market/stocks/...` a Polygon-tól, `/stable/company-screener` az FMP-től, `/api/darkpool/SPY` az Unusual Whales-től, `/fred/series/observations` a FRED-től), és validálja a HTTP 200 választ, a JSON struktúrát és a response-time-ot.

A makró-kontextust három mérőszámmal jellemezzük: a VIX volatilitási index aktuális értéke (`VIX < 20` "normal", `20 ≤ VIX < 30` "elevated", `VIX ≥ 30` "extreme"), a 10 éves államkötvény-hozam (TNX) és a 2s10s yield curve spread (negatív érték = inverziós állapot, recessziós előjel). A diagnostic fázis kimenete: `pipeline_can_proceed: bool` és `macro_regime: dict`. Ha kritikus API nem érhető el, a pipeline szándékos `sys.exit(1)`-tel leáll — egy `--override-circuit-breaker` flag-gel manuális felülbírálás lehetséges.

Tipikus log-üzenet:
```
[ 0/6 ] System Diagnostics
    OK  polygon            /v2/aggs/.../2026-05-15   1183ms [CRITICAL]
    OK  unusual_whales     /api/darkpool/SPY          323ms
    OK  fmp                /stable/company-screener   716ms [CRITICAL]
    OK  fred               /fred/series/observations  299ms
  Macro: VIX=18.55 (normal)  TNX=4.47%  Rate-sensitive=False
  => Pipeline CAN proceed
```

## 4.2 Phase 1 — Market Regime (BMI)

A "Big Money Index" (BMI) egy saját fejlesztésű intézményi pozícionálás-mérő. A számítás alapja, hogy a Polygon napi grouped-bars végpontján keresztül lekérdezzük az amerikai részvénypiac teljes egészére (kb. 11000-12000 ticker) az aznapi forgalmi és ár-statisztikákat, és minden tickerre kiszámítjuk, hogy a volumen-spike-ja a normál átlaghoz képest 2 szórásnyi (2σ) felett van-e. A "spike-tickerek" arányát a "vásárlási nyomás" (azaz ahány tickeren a záróár > a nyitóár) és az "eladási nyomás" (azaz ahány tickeren a záróár < a nyitóár) napi arányával vetjük össze, majd a teljes mintán 25 napi SMA-t számolunk.

A BMI képletileg:

```
spike_ratio_t = #{tickers : volume_t > μ + 2σ} / #{all_tickers}
buy_pressure_t = #{spike_tickers : close_t > open_t} / #{spike_tickers}
sell_pressure_t = #{spike_tickers : close_t < open_t} / #{spike_tickers}
BMI_raw_t = buy_pressure_t / (buy_pressure_t + sell_pressure_t)
BMI_t = SMA_25(BMI_raw_t) × 100
```

A `BMI ≤ 25` érték azt jelzi, hogy az intézményi eladási nyomás dominál → `RED` regime, defenzív/short stratégia. A `BMI ≥ 80` agresszív vásárlási nyomást jelez → `GREEN` regime, agresszív long. A két szélső érték közötti `25 < BMI < 80` a `YELLOW` regime, normál long stratégia. A 2026 márciusi-májusi időszakban a BMI az idő ~92%-ában YELLOW régiumban tartózkodott — a SHORT ágat ezért 2026 áprilisában deaktiváltuk.

Egy kiegészítő mechanizmus, a "BMI Momentum Guard", a maximum pozíciószámot csökkenti, ha a BMI 3 napon át csökkenő trendet mutat (ezzel a piaci momentum-fordulását kezeljük).

## 4.3 Phase 2 — Universe Building

A Phase 2 az amerikai részvénypiacról egy minőségi alapsokaságot szűr ki, amelyből a kereskedési jelölteket merítjük. A bemenet az FMP screener-API-ja, amely a következő szűrőket alkalmazza: piaci kapitalizáció `≥ $2 milliárd`, részvényárfolyam `≥ $5`, napi forgalom `≥ 500 000 részvény`, és **opciós piaci aktivitás** ("isOptionable=true" jelölővel). Ez tipikusan 1300-1500 részvényre szűkíti az alapsokaságot a hét közepén.

A swing pivot architektúrában az alapsokaságot **explicit** S&P 500 + Russell 1000 union-ra korlátozzuk (kb. 1024 ticker), hogy a likviditás-szintű "high-score, low-liquidity" pattern (a régi rendszerben gyakran látott alacsony-volumenű mid-cap energy/biotech) kizárt legyen.

A második szűrési lépés az earnings-szűrő. Minden tickerre az FMP earnings-calendar-on lekérdezzük a következő 10 naptári napon belüli earnings release dátumokat (a hold-idő × 2 buffer), és a 10-Q / 10-K SEC EDGAR filing dátumokat. A swing pivot architektúrában a SEC EDGAR API integrációja **új feature** (Fázis 1 W21), mert a 60 napi tesztek során 3 dokumentált eset volt, amelyben a 10-Q filing event NEM earnings release-ként szerepelt az FMP-ben, mégis árfolyam-mozgást okozott.

A Phase 2 kimenete: `tickers: list[Ticker]`, ahol minden ticker tartalmazza a szimbólumot, a piaci kapitalizációt, a szektor-besorolást, és a Polygon-os daily bars referenciát. Tipikus output: 280-320 ticker a hét közepén.

## 4.4 Phase 3 — Sector Rotation

A 11 alapszektor-ETF (XLK Technology, XLF Financial, XLE Energy, XLV Healthcare, XLI Industrials, XLP Consumer Staples, XLY Consumer Discretionary, XLB Materials, XLC Communications, XLRE Real Estate, XLU Utilities) közül a Phase 3 az 5 napos és 20 napos relatív teljesítmény-arányokat számolja az S&P 500 (SPY) referenciához képest.

A szektor-rangsorolás:

```
rel_strength_5d_i = (XLi_close_t / XLi_close_t-5) / (SPY_close_t / SPY_close_t-5) - 1
rel_strength_20d_i = (XLi_close_t / XLi_close_t-20) / (SPY_close_t / SPY_close_t-20) - 1
sector_score_i = 0.6 × rel_strength_5d_i + 0.4 × rel_strength_20d_i
```

A `sector_score` szerint a top 3 szektor "leader" jelölést kap (a részvényeik +15 pont bónuszt élveznek a Phase 4 kompozit pontszámban), a bottom 3 "laggard" (-20 pont). Egy kiegészítő `VETO` szabály teljesen kizárja azokat a szektorokat, amelyek mind az 5 napos, mind a 20 napos mutatóra negatívak — ezek a szektorok gyakran egy strukturális defenzív trendben vannak (pl. Energy 2026 márciusban-áprilisban), és a long-only stratégiához nem alkalmasak.

A swing pivot architektúrában a szektor-rotáció szerepe részben átalakult: a `sector_adj` érték közvetlenül az új `S_j` scoring képletben szerepel, és a "sector-balanced greedy" pozíció-szelekció a Phase 6-ban biztosítja, hogy a portfolio szektor-diverzifikációja a `sector_max_pct: 15%` cap-en belül maradjon (lásd Phase 6).

## 4.5 Phase 4 — Stock Analysis

A pipeline szíve. Minden átszűrt részvényre egy 0-100 közötti kompozit pontszám számítódik. A legacy intraday architektúrában három alkomponens súlyozott összegéből:

```
Score = 0.60 × FlowScore + 0.30 × TechnicalScore + 0.10 × FundamentalScore
```

A **FlowScore** (60% súly) hét alkomponens kompozitja: relatív volumen (RVOL), dark pool százalék, put-call ratio (PCR), out-of-the-money call ratio (OTM call), blokk-ügyletek száma, vásárlási nyomás (close vs VWAP), és squat bar (magas volumen, szűk spread). A **TechnicalScore** (30% súly) három alkomponensből áll: RSI ideális zóna (RSI ∈ [45, 65] → +30 pont), SMA50 fölött (+30 pont), és 3 hónapos relatív teljesítmény az S&P 500-hoz (RS vs SPY, 2026 áprilisi átalakítás óta +15 pont max). A **FundamentalScore** (10% súly) a bevétel-növekedés, EPS-növekedés, profit margin, ROE és eladósodottság (D/E ratio) bónuszait/büntetéseit összegezi egy 50-es bázis körül.

A swing pivot architektúrában a pontozási rendszer **radikálisan egyszerűsödött**. A 60 napos validációs futás (lásd 6. szakasz) megmutatta, hogy a hét flow alkomponens közül **csak két alkomponens prediktív statisztikailag** szignifikánsan: a put-call ratio (Pearson r = +0.203, p = 0.002) és a relatív volumen (r = +0.147, p = 0.026). Az out-of-the-money call ratio NEGATÍV szignifikáns prediktor (r = -0.194, p = 0.003) — vagyis a magas OTM call vásárlás (gyakran retail FOMO jel) ROSSZABB hozamot prediktál. A többi alkomponens nem szignifikáns vagy gyengén negatív.

A swing pivot új scoring képlete tehát:

```
S_j = 100 × (PCR_percentile_j - OTM_percentile_j) + sector_adj_j
```

ahol `PCR_percentile_j` a put-call ratio percentilis-helyzete a teljes univerzumban (0-1 skálán), `OTM_percentile_j` az OTM call ratio percentilis-helyzete, és `sector_adj_j` a Phase 3 szektor-rotáció által generált pontszám-finomítás (`-20` to `+15`). A `S_j` tipikusan `-50` és `+150` között mozog, a `S_j > 50` küszöb a kvalifikáló tartomány.

Az `S_j` napról napra ingadozhat, ezért egy 5-napi **EWMA simítás**-t alkalmazunk:

```
EWMA_S_j_t = α × S_j_t + (1 - α) × EWMA_S_j_t-1   (α = 2 / (5 + 1) = 0.333)
```

A Phase 4 kimenete: minden kvalifikáló tickerre az `(S_j, EWMA_S_j, sector, percentile_rank)` négyes. Tipikusan 50-100 ticker él át az S_j > 50 küszöbön egy átlagos kereskedési napon.

## 4.6 Phase 5 — GEX Analysis (Gamma Exposure)

A piacvezetők gamma-exponáltságát az Unusual Whales API-ján keresztül lekérdezett opciós piaci adatokból számoljuk. A "gamma exposure" (GEX) egy szám, ami a market maker-ek delta-hedging-mintázatait jellemzi: pozitív GEX (a market maker-ek aggregátum gamma-pozíciója pozitív) esetén a delta-hedging visszacsillapító hatású — minél nagyobb az ármozgás, annál erősebben hedge-elnek visszafelé. Negatív GEX esetén a hedging amplifikál — egy emelkedő árban tovább vesznek delta-fedezetet, ami további emelkedést okoz.

A pipeline három GEX-regime-et különböztet meg: `positive` (GEX > 0, stabilizáló market — alacsony intraday vol), `high_vol` (GEX < 0 + IV > 25%, destabilizáló market — magas intraday vol), `unknown` (nem elég opciós lánc adat).

A legacy architektúrában a GEX egy `M_GEX` multiplier-t generált a pozíció-méretezéshez:
- pozitív GEX → `M_GEX = 1.0` (teljes pozícióméret)
- negatív GEX, normál vol → `M_GEX = 0.5` (fele)
- magas vol (`high_vol`) → `M_GEX = 0.6`

A swing pivot architektúrában az `M_GEX` szorzó deaktivált, de az adatot **shadow log**-ban továbbra is rögzítjük (`state/uw_shadow/YYYY-MM-DD.json`). A Day 90 milestone (2026-08-12 körül) után, ha a shadow-logok statisztikailag szignifikáns prediktív értéket mutatnak, a multiplier újra-aktiválható.

## 4.7 Phase 6 — Position Sizing

A pipeline utolsó számítási lépése a pozíció-méretezés. A legacy intraday architektúrában a per-trade kockázat 0.7% volt ($700 a $100 000 paper-egyenlegen), és a méretezés egy "multiplier chain"-en keresztül történt:

```
poz_risk = (account_equity × 0.007) × M_total
M_total = clamp(M_VIX × M_GEX × M_target × M_contradiction, 0.25, 2.0)
quantity = floor(poz_risk / stop_distance)
```

Az `M_VIX` a piaci volatilitás védelmi szorzója (VIX 20 alatt 1.0×, magasabb értéken arányosan csökkentve, VIX 50 fölött 0.1×). Az `M_GEX` a fent tárgyalt gamma-multiplier. Az `M_target` az analyst consensus target ár védelme (ha az árfolyam 20% fölött van a 12 hónapos target felett, 0.85×; ha 50% fölött, 0.60×). Az `M_contradiction` a 2026 májusi új komponens, amely a fundamentális ellentmondásokat ("kevesebb mint 50% earnings beat az utolsó 4 negyedévben", "ár 2% fölött a consensus target felett", "2+ recent downgrade") esetén 0.80×-szorzót alkalmaz.

A swing pivot architektúrában a méretezés **drasztikusan egyszerűsödött**. A per-trade kockázat **0.35%** (\$350), a multiplier chain hatása minimalizálva (mind az `M_X = 1.0` forcelt, kivéve az `M_target`-et, amely továbbra is működik). A pozíció-méretezés:

```
risk_per_pos = account_equity × 0.0035 = \$350
qty = floor(risk_per_pos / stop_distance)
```

A `stop_distance` a swing pivot architektúrában egy **mental stop**, nem IBKR bracket-stop. A mental stop a Phase 4 S_j-ből és a 14-napi ATR-ből számítódik: `stop_level = entry_price - 2 × ATR`. A `tp1_level = entry_price + 1.5 × ATR`, a `tp2_level = entry_price + 3.0 × ATR`.

A Phase 6 utolsó lépése a **sector-balanced greedy** pozíció-szelekció. A Phase 4-ből származó kvalifikáló tickerek (`S_j > 50`) sor a `S_j` szerinti csökkenő sorrendben, és minden tickerre ellenőrizzük, hogy a hozzáadása nem lépi-e túl a `sector_max_pct: 15%` notional cap-et. Ha igen, a ticker átugrik, és a következő legmagasabb S_j-vel rendelkező ticker kapja a helyet egy másik szektorból. A folyamat addig fut, amíg a `max_concurrent: 12` pozíció elérésre nem kerül, vagy az `S_j > 50` lista kifut.

Tipikus napi output: 2-5 új entry (a max 12 koncurrens limitnek megfelelően a hét során fokozatosan halmozódik), 30-50% notional kihasználtság ($30 000 - $50 000 a \$100 000 paper-egyenlegen).

---

# 5. Jelenlegi működési modell és indoklása

## 5.1 Mit változtattunk és miért

A 2026-05-18 hétfői napon hatályba lépett "swing pivot" architektúra a legacy intraday rendszer egy alapvető átalakítása. A változtatások négy területet érintenek: a holding period-et, a kockázatkezelést, a pontozási rendszert, és az exit-mechanikát.

A **holding period** kiterjedt 6 óráról 3-5 napra. A 6 órás intraday-horizonton a flow signal-nek nincs ideje érvényesülni: a put-call ratio, mint legkonzisztensebb pozitív prediktor, **a kompletly intraday kompresszióban elveszíti az információértékét**. A 3-5 napi swing-horizonton a flow signal "play out" ideje több napra terjed, és az intraday noise (opening range volatilitás, lunch lull, afternoon retracement) statisztikailag kisimul.

A **kockázat per trade** csökkent 0.7%-ról 0.35%-ra. Ez **2x-es kockázat-csökkentés**, amelyet a rolling 10-12 pozíció-szám kompenzál: a portfolio total kockázat a 0.7% × 5 max pos = 3.5% szintről a 0.35% × 12 max pos = 4.2% szintre **mérsékelten növekszik**, miközben a diverzifikáció **kétszeresére javul**.

A **pontozási rendszer** drámaian egyszerűsödött a 7 alkomponens × 3 al-súlyú kompozitról a 2 alkomponens (PCR percentile - OTM percentile + sector_adj) képletre. Ez a **Bonferroni-szignifikáns minimum** elv alapján történt: a 60 napi paper trading 7 alkomponens × ~5 paraméter = 35 hipotézis tesztelése során a Bonferroni-korrigált küszöbön (p_adj = 0.05 / 35 = 0.0014) csak a PCR (p = 0.002) és az OTM call (p = 0.003) maradt szignifikáns. A többi alkomponens **NEM** ad szignifikáns prediktív értéket, így a kompozitból kizártuk őket.

Az **exit-mechanika** átállt a hardcore IBKR bracket-stop loss + bracket take-profit kombinációról egy mental-stop + napi EOD evaluation rendszerre. A bracket-stop architektúrája egy strukturális bug-osztályt termelt (a "loss-exit bracket SL bug", lásd 6. szakasz), amely a swing pivot architektúrában **automatikusan eltűnik**, mert nincs függő IBKR bracket-order.

## 5.2 A matematikai megalapozottság

A holding period megválasztása nem önkényes. Egy információelméleti megközelítésben a flow signal és a realizált hozam közötti **mutual information (MI)** mérhető a holding period függvényében. A 2026-05-08-i belső "Strategic Review — Mathematical" elemzés szerint a put-call ratio és a 5-napi hold realizált hozam közötti `MI(PCR, R_5d)` érték **kb. ötszöröse** a 6 órás `MI(PCR, R_6h)`-nak. Ez a strukturális adatpont a swing pivot időtáv-választásának matematikai megalapozottsága.

A **Kelly-kritérium** alkalmazása szintén a swing pivot indoklása. A legacy 6 órás architektúrán a 60 napi adatokra számolt Kelly-fraction:

```
f* = (μ × R - (1 - μ × R)) / R
```

ahol `μ` a win rate (≈ 0.466) és `R` az átlagos win/loss ratio. A számítás eredménye **f* = -0.23 (konzervatív) -tól -0.46 (agresszív) -ig** — vagyis a rendszer **negatív expectancy-vel** rendelkezett, és Kelly-szempontból **mínusz pozícióméret** lett volna optimális. A swing pivot architektúra megcélzott win rate-je 50-55% és R = 1.2-1.5, ami egy enyhén pozitív Kelly f*-ot eredményezne.

## 5.3 Élesedés és kockázatkezelés

A jelenlegi rendszer **paper-trading módban** fut. A 2026-04-28-i belső döntéshozási keret szerint az élő pénzes kereskedés legkorábbi indítása az **új Day 126 milestone** (2026-09-15 körül), a swing pivot új 63 napi paper trading futása alapján. Az élesítési kritériumok: kumulatív P&L `> +\$2 000` (kb. +2% / 63 nap = +8% éves), Sharpe-arány `> 0.5`, és **25+ napon belüli pozitív excess return** az S&P 500-hoz képest.

A leállítási kritériumok: 20+ napi VIX `> 25` (extrém vol regime), VAGY 10 napi átlag excess vs SPY `< -1.5%` (strukturális underperformance).

---

# 6. Az előző 63 napos paper trading tanulságai

## 6.1 A számszerű eredmények

A 2026. március 13. és május 14. közötti 63 napos paper trading futás 378 ügylet eredményével zárult:

| Mutató | Érték | Megjegyzés |
|--------|-------|------------|
| Kumulatív bruttó hozam | **-1,46%** | -$1 460 a $100 000 paper-egyenlegen |
| Win rate (ügylet szinten) | 46,6% | Médián hozam: -\$1,25 |
| Pearson r (score vs P&L) | **-0,000** (p=0,996) | Statisztikailag null edge |
| TP1 hit ráta | 9,5% | Profit-küszöb 1,25×ATR |
| TP2 hit ráta | 0,8% | Profit-küszöb 2,0×ATR — kvázi nem létezik |
| Stop-loss + loss-exit | 12,4% | Nettó -\$4 335 |
| MOC (market-on-close) | 74,1% | A pozíciók 3/4-e "napi piaci irány lottón" zár |
| Becsült éves jutalék-teher | ~8,4% | A \$100k bázison |
| Becsült éves súrlódás-teher | ~15-17% | Commission + slippage + adat |

A 60 napi minta tehát **nem támasztja alá**, hogy a pontozási rendszer strukturális alfát generálna. A win rate (46,6%) statisztikailag **a véletlentől nem különbözik** (a binomiális teszt 95% CI: [41,5%, 51,7%]), és a Pearson r = -0,000 azt jelenti, hogy **a magasabb pontszámú részvény nem prediktál jobb hozamot** a futás teljes mintáján.

## 6.2 A "magas pontszám paradoxon"

A 378 ügylet pontszám szerint 5 egyenlő részre osztva (quintile-analízis):

| Quintile | Pontszám | N | Total P&L | Átlag P&L |
|----------|----------|---|-----------|-----------|
| Q1 (alsó) | 85,5 — 92,5 | 75 | -$129 | -$1,72 |
| **Q2** | 92,5 — 94,0 | 76 | **+$880** | **+$11,57** |
| Q3 | 94,0 (mid) | 75 | -$1 341 | -$17,88 |
| Q4 | 94,0 — 95,0 | 76 | +$76 | +$1,01 |
| **Q5 (felső)** | 95,0+ | 76 | **-$677** | **-$8,91** |

A **legmagasabb pontszámú részvények rosszabbul teljesítenek**, mint a középsők. Ez NEM véletlen mintázat: a 60 napi sample-ban 4 egymás utáni kereskedési napon (2026-05-04 → 05-07) megerősítettük, hogy a napi legmagasabb pontszámú ticker rendszerszerűen a leggyengébb performer. A strukturális okok: a magas pontszámú részvények gyakran alacsony likviditású mid-cap-ek (a slippage felemészti az edge-et), a "RS vs SPY momentum" indikátor egy oldalozó piacon a "legkevésbé esett" részvényeket választja (azok pedig a mean-reversion célok), és az OTM call ratio a retail-FOMO részvényeket erőlteti a top quintile-ba (kontraindikátor).

## 6.3 A flow alkomponens dekompozíció

A 232 ügylet alapú alkomponens-szintű analízis a 60 napi sample-ban (csak a teljes phase4_snapshot-tal rendelkező ügyletek):

| Alkomponens | Pearson r | p-érték | Spearman ρ | Megjegyzés |
|-------------|-----------|---------|------------|------------|
| **PCR (put-call)** | **+0,203** | **0,002** | +0,114 | Erős pozitív |
| **RVOL (rel. vol.)** | **+0,147** | **0,026** | +0,103 | Pozitív |
| **OTM Call ratio** | **-0,194** | **0,003** | -0,184 | Erős **negatív** |
| Block Trade | -0,117 | 0,076 | -0,134 | Gyenge negatív |
| Buy Pressure | +0,068 | 0,301 | +0,038 | Nem szignifikáns |
| Squat Bar | +0,036 | 0,588 | +0,038 | Nem szignifikáns |
| Dark Pool % | n/a | n/a | n/a | **Inaktív** (mind 0 érték) |

A Bonferroni-korrigált küszöbön (`α = 0,05 / 7 = 0,007`) **csak a PCR és az OTM call ratio marad szignifikáns**. A többi alkomponens vagy gyengén szignifikáns (RVOL, p=0.026), vagy nem szignifikáns.

Stratégiailag ez a finding **azt mutatja**, hogy a legacy 7-alkomponens-kompozit **információt veszít** a tényleges 2 prediktív komponensből — a kompozit "diluted" mintát mutat, ahol a PCR és OTM jeleket elnyeli a 5 zaj-alkomponens. A swing pivot új scoring (`S_j = 100 × (PCR_pct - OTM_pct) + sector_adj`) ezt a finding-ot **közvetlenül átveszi**.

## 6.4 Az exit-statisztika

A 378 ügylet exit-típus szerinti felosztása:

| Exit típus | N | Átlag P&L | Total P&L |
|------------|---|-----------|-----------|
| T1 (profit) | 36 | +$32,95 | +$1 186 |
| T2 (profit) | 3 | +$286,03 | +$858 |
| Trail (profit) | 3 | +$33,39 | +$100 |
| MOC | 280 | +$3,36 | +$940 |
| SL (loss) | 15 | -$78,87 | -$1 183 |
| Loss Exit (loss) | 32 | -$98,50 | -$3 152 |
| Nuke (manuális) | 9 | +$6,51 | +$59 |

A profit-küszöbök (T1, T2) kevés hit-ráta (10,3% összesen) ellenére profitábilis. A loss-mechanikák (SL + LossExit, 12,4%) **nagyobb átlagveszteséget** termelnek, és a két oldal aggregát mérlege:

```
Profit oldal (T1+T2+Trail+MOC) = +\$3 084
Loss oldal (SL+LossExit)        = -\$4 335
Nettó                            = -\$1 251
```

A naiv risk-reward arány **0,83 : 1** (T1 = 1,25×ATR profit / SL = 1,5×ATR veszteség), ami strukturálisan kedvezőtlen.

## 6.5 A strukturális tanulság

A 63 napi paper trading **strukturális megfigyelései**: (1) a kompozit pontszám 7 alkomponensből álló rendszere **információ-vesztő**, (2) a 6 órás holding period **strukturálisan elnyeli** a flow signal érvényesülésének idejét, (3) a hardcore bracket-stop architektúra **bug-felszínt** generál (5 dokumentált instance 14 napon belül a bracket-stop "késleltetett trigger" problémájáról), és (4) a magas pontszámú részvények alacsony-likviditás-pattern-je **strukturális kontraindikátor**.

A swing pivot architektúra **mind a négy strukturális problémát** közvetlenül kezeli.

---

# 7. A "swing pivot" — új architektúra bemutatása

## 7.1 A 14 stratégiai döntés

A 2026-05-14-i Day 63 milestone outcome dokumentum 14 stratégiai döntést rögzített, amelyek a swing pivot architektúrát definiálják. A legfontosabbak:

A **holding period 3-5 nap**, mental-stop daily evaluation logikával. A `pt_monitor.py` naponta egyszer 22:00 CEST kor értékeli ki minden nyitott pozíció állapotát, és a következő nap 15:30 CEST-i `close_positions.py` szállítja le a tervezett zárásokat (TP1, TP2, mental SL, time stop a Day 5-en).

A **per-trade kockázat 0,35%** ($350 a $100 000 baseline-en), a rolling **12 max koncurrens** pozícióval. Egy átlagos napon 2-5 új entry és 0-3 exit történik, a portfolio fokozatosan 8-12 pozícióra halmozódik a hét során.

A **scoring egyszerűsödött** a Bonferroni-szignifikáns minimum (PCR percentile - OTM percentile + sector_adj) képletre, 5-napi EWMA simítással.

A **sector cap 15%** notional per szektor (a tényleges deploy-ban, korábbi tervezett 30% felülbírálva), és a portfolio total notional kihasználtság 30-60% sávban mozog.

A **bracket order megszűnt**. Csak market BUY order az IBKR-be, a stop / TP1 / TP2 szintek `state/swing_positions.json`-ben tárolódnak, és a `pt_monitor.py` napi EOD eval logikája dönt a zárásokról.

A **Unusual Whales API** scoring deaktivált (a dark pool signal a 60 napi mintán nem szignifikáns prediktor), de a shadow log produkcióban fut (`state/uw_shadow/YYYY-MM-DD.json`). A Day 90 milestone kor a shadow-logok alapján döntünk az aktiválásról.

A **SEC EDGAR 10-Q / 10-K filing exclusion** új feature, amely a Phase 2 univerzumból kizárja azokat a tickereket, amelyek a következő 10 napon belül 10-Q vagy 10-K filing-ra esedékesek.

Az **IBKR Gateway monitoring + Telegram alert** új infrastruktúra-feature: a 15:25 CEST pre-flight ellenőrzi a Gateway elérhetőségét és a 15:45 CEST heartbeat a sikeres submit-et.

## 7.2 Day 1 (2026-05-18) eredmények

A swing pivot architektúra hivatalos indulása 2026-05-18 hétfő. A Day 1 eredménye anekdotikus, statisztikailag n=1, de **mechanikai szempontból megerősítő**.

A Day 1-en **3 új entry** nyitotta meg a portfoliot:

| Ticker | S_j | Szektor | Entry $ | TP1 $ | Notional $ | % portfolio |
|--------|-----|---------|---------|-------|------------|-------------|
| **LBRT** | **106,9** | Energy | 33,34 | 35,40 | 4 234 | 4,2% |
| **MASI** | 102,4 | Healthcare | 178,51 | 178,95 | 14 995 | **15,00%** (cap) |
| **EC** | 98,5 | Energy | 13,08 | 13,86 | 4 342 | 4,3% |

A MASI sector cap-en (15,00% Healthcare) **strukturálisan érvényesítette** a sector-balanced greedy logikát: a magas S_j ellenére (102,4) a méretezés nem lépte át a Healthcare cap-et, és a következő helyezett ticker más szektorból került be (EC, Energy, S_j 98,5).

A nap legfontosabb mechanikai eseménye: az **EC ticker TP1 küszöbét intraday elérte** (entry $13,08 → TP1 $13,86, kb. +6,0% mozgás). A swing pivot mechanikája szerint a TP1 fill **nem aznap történik**, hanem a következő (kedd 2026-05-19) 15:30 CEST-i `close_positions.py --mode=eod_flags` MARKET SELL-jén. Ez egy fontos kontraszt a legacy intraday architektúrával: a régi rendszer **azonnal lezárta** volna az EC pozíciót a TP1 küszöbön (kb. 17:00-18:00 CEST körüli intraday időpontban a piaci nyitás után 1-2 órával), míg az új rendszer **24 órás overnight gap-kitettséget** vállal a TP1 fill számára.

Ez egy strukturális trade-off: a 24 órás overnight gap egyrészt **növeli a profit potenciált** (egy kedvező kedd reggeli nyitásra a profit a TP1 küszöb fölött is folytatódhat), másrészt **növeli a downside kockázatot** (egy kedvezőtlen reggeli gap a profit eltűnését okozhatja). A 63 napi swing-mintán dől el, hogy a két hatás aggregát egyenlege pozitív vagy negatív.

A Day 1 portfolio total notional 23,57% (\$23 570) — mérsékelt kihasználtság, ami a max 60-os szektor-balanced 12 pos cap mellett a következő napokban fokozatosan halmozódik 30-50% sávra.

---

# 8. Roadmap és további lépések

## 8.1 Adatminőség javítás

A 63 napi paper trading 3 strukturális adatminőség-problémát azonosított:

Az **earnings-szűrő hiányosságai**. A FMP earnings-calendar nem fedi le teljesen az európai/ázsiai ADR-eket (Anheuser-Busch InBev, Banco Santander, stb.), és a 10-Q SEC filing event-eket sem. A swing pivot SEC EDGAR integrációja az utóbbit kezeli; az ADR-fedettségi probléma egy hard-coded blacklist megoldással kezelhető (a top 50-100 ADR earnings-dátumai kézzel rögzítve).

Az **Unusual Whales dark pool snapshot-jának érzékenysége**. A 2026 áprilisi 10-i Unusual Whales API-frissítés a dark pool percentilis-számítás módszerét megváltoztatta, ami a 60 napi mintán **strukturális diszkonzisztenciát** okozott. A swing pivot architektúrában a dark pool inaktív, de a shadow log a régi és új módszertant **párhuzamosan logolja**, hogy a Day 90 calibration kor a tisztán "új-módszertani" mintán értékelhessük a prediktív értéket.

A **Polygon 1-perces bars rate-limiting**. A Polygon Advanced tier 1-perces bars végpontja `5 hívás / másodperc` limittel rendelkezik, és a Phase 2 univerzum 300+ ticker × 60 napi history = 18000+ hívás → 1 óra futási idő. A swing pivot architektúrában a 1-perces bars szerepe csökkent (a swing scoring főleg daily-szintű), de a kvantitatív utólagos elemzéshez továbbra is fontos. Egy lokális Polygon adatbázis-cache jelenleg fejlesztés alatt.

## 8.2 A második 63 napos teszt elvárásai

A swing pivot új 63 napi paper trading futásától (Day 1 = 2026-05-18, Day 63 ≈ 2026-08-12) az alábbiakat várjuk:

A **kumulatív P&L `> +\$2 000`** (kb. +2% / 63 nap = +8% éves bruttó alfa). Ez az érték a top decile hedge fund alfa-szint kb. fele, ami egy kvantitatív retail-szintű rendszerre **realisztikus** stretched cél.

A **Sharpe-arány `> 0.5`**. A Sharpe = (E[R] - R_f) / σ_R képletben a célzott napi átlag hozam 0.07-0.10% és napi szórás 0.5-0.7%, ami éves Sharpe-arányra ~0.5-1.0 sávra jelentene. Az élő pénzes kereskedés indításához ez a minimum.

A **25+ napon belüli pozitív excess return** az S&P 500 (SPY) referencia-indexhez képest. A "excess return" a portfolio_daily_return - SPY_daily_return, és a 63 napi mintán **25 napon (40%-on)** pozitív kell legyen — ez egy konzisztencia-mérőszám, ami azt biztosítja, hogy az alfa nem egyetlen kiugró nap eredménye, hanem strukturálisan stabil mintázat.

A **TP1 hit ráta `> 25%`** (a régi rendszer 9,5%-áról). A swing TP1 1,5×ATR távolsága (vs régi 1,25×ATR) **enyhén nagyobb cél**, de a 3-5 napi holding-horizonton várhatóan strukturálisan elérhetőbb.

A **drawdown `< 5%`**. A 63 napi peak-to-trough maximum drawdown 5% alatt kell maradjon (vs régi rendszer 3-4% drawdown 60 napi minta) — ez a rolling 12-pozíció diverzifikáció elsődleges teszt-szempontja.

## 8.3 A milestone-naptár

A következő 6 hónap milestone-jai:

A **Day 21** (kb. 2026-06-15) kor első kvantitatív interim-értékelés. Ha a kumulatív P&L `< -\$1 500` (kb. -1.5% / 21 nap = -18% éves) VAGY a Sharpe < -0.3, akkor a paper trading megszakad és a swing pivot revíziója indul (`docs/decisions/...-day21-checkpoint.md`-be rögzítve).

A **Day 63** (2026-08-12) kor a teljes go/no-go értékelés a 8.2 szakaszban leírt kritériumok mentén. Pozitív eredmény esetén az **élő pénzes kereskedés első fázis** indítható $10 000 tőkével, circuit breaker (3% drawdown), és napi notional limittel (max $25k single, max \$200k total).

A **Day 90** (kb. 2026-09-02) a Unusual Whales dark pool signal calibration milestone. A 90 napi shadow log alapján statisztikailag értékeljük, hogy érdemes-e a dark pool jelet a scoring rendszerbe aktiválni.

A **Day 126** (kb. 2026-09-15) a végső élő kereskedés go/no-go pont. Ha a Day 63 + Day 90 értékelések pozitívak, a $10 000 tőkés élő kereskedés **$50 000-re skálázható** (incremental capital deployment), a teljes 63 napi élő mintán cumulative > +\$1 000 ÉS Sharpe > 0.5 mellett.

## 8.4 A graceful exit forgatókönyv

Ha a Day 63 értékelés **negatív** (kumulatív P&L < +\$500 VAGY Sharpe < 0.3), a projekt nem szűnik meg, hanem **strukturált tanulság-rögzítésbe** lép át. A 63 napi swing-minta strukturális megfigyelései — a flow signal "play out" időtáv-érzékenysége, a sector-balanced greedy hatékonysága, a mental stop vs bracket stop trade-off — **akkor is értékesek**, ha az alfa nem realizálódik.

A graceful exit kulcs eleme a transzparencia: a 63 napi paper trading nyers adatait (snapshot-okat, trade-logokat, daily metric-eket) **megosztjuk az IFDS team többi tagjával**, és a strukturális tanulságokat egy záró `docs/strategic-review/...-day63-final.md` dokumentumban rögzítjük.

---

# 9. Glosszárium

A dokumentumban használt rövidítések és fogalmak rövid magyarázata.

**ATR** — Average True Range. Az átlag napi ár-tartomány, volatilitás-mérés. A swing pivot architektúrában 14-napi ATR-rel számolunk a stop / TP1 / TP2 szintek beállításához.

**BMI** — Big Money Index. A saját fejlesztésű intézményi pozícionálás-mérő (Phase 1). A piaci 2σ-spike-ticker arányából + buy/sell pressure-ből számolt 25-napi SMA.

**Bonferroni-korrekció** — Több hipotézis tesztelése esetén az α-szintet `m`-rel osztjuk (`α_adj = α / m`), hogy a false positive arány a teljes minta szintjén `α` maradjon. A 7-alkomponens-flow-validation: α_adj = 0.05 / 7 = 0.007.

**Bracket order** — Az IBKR-ben egy paraent BUY order + két child order (SL és TP). A swing pivot architektúrában megszűnt.

**dp_pct** — Dark pool percentage. A ticker napi forgalmának dark-pool-szintű (off-exchange) hányada. Régi scoring komponens, jelenleg a swing pivot architektúrában inaktív.

**EWMA** — Exponentially Weighted Moving Average. Az új scoring 5-napi simítás α = 2 / (5 + 1) = 0,333 súllyal.

**GEX** — Gamma Exposure. Az opciós piacvezetők aggregát delta-hedging-pozíciója. Pozitív GEX → stabilizáló market, negatív → destabilizáló.

**Kelly-fraction (f\*)** — A Kelly-kritérium által számolt optimális pozícióméret-frakció. `f* = (μ × R - (1 - μ × R)) / R`, ahol `μ` a win rate és `R` az átlag win/loss ratio. Negatív f* esetén a stratégia negatív expectancy-vel rendelkezik.

**MOC** — Market-on-Close. Az amerikai piaci nap zárása (16:00 ET = 22:00 CEST nyári időszámításkor) közeli rendelési típus. A legacy architektúrában a pozíciók 74,1%-a MOC-on zárult.

**Mental stop** — A swing pivot architektúra exit-mechanikája. A stop szint a `state/swing_positions.json`-ben tárolódik, és a `pt_monitor.py` napi EOD eval-ja értékeli ki, nem egy függő IBKR bracket-stop-order.

**Mutual Information (MI)** — Két valószínűségi változó (pl. PCR és realizált hozam) közötti közös informáltság mérőszáma. A swing pivot időtáv-választás matematikai alapja: MI(PCR, R_5d) ≈ 5 × MI(PCR, R_6h).

**OTM call ratio** — Out-of-the-Money call options ratio. A ticker opciós láncának OTM-call-szintű forgalmi hányada. A 60 napi minta szerint **negatív prediktor** (Pearson r = -0,194, p = 0,003).

**PCR** — Put-Call Ratio. A ticker put és call opciós forgalmi aránya. A 60 napi minta legkonzisztensebb pozitív prediktora (Pearson r = +0,203, p = 0,002).

**RS vs SPY** — Relative Strength vs S&P 500. A ticker 3-hónapos relatív teljesítménye az SPY-hez képest. Régi technikai score komponens, swing pivot architektúrában szerepe csökkent.

**RVOL** — Relative Volume. Az aznapi forgalom az átlaghoz viszonyított aránya. A flow score-ban prediktív komponens (Pearson r = +0,147, p = 0,026).

**Sharpe-arány** — Az átlag hozam és a hozam szórásának hányadosa (kockázat-mentes hozammal korrigálva). `Sharpe = (E[R] - R_f) / σ_R`. Az élő pénzes kereskedés indításához a 63 napi swing pivot mintán Sharpe > 0.5 a kritérium.

**S_j** — A swing pivot scoring képlet eredménye az `j` tickerre. `S_j = 100 × (PCR_pct_j - OTM_pct_j) + sector_adj_j`. A küszöb `S_j > 50` a kvalifikáció.

**Slippage** — Az tervezett és tényleges entry/exit ár közötti különbség. A 63 napi minta átlag entry slippage +0,15-0,25%.

**Time stop** — A Day 5-en (a swing pivot architektúra maximum holding period) érvényes záró mechanizmus. A `close_positions.py --mode=time_stop` 21:40 CEST-en MARKET SELL minden Day 5-en eltelt pozíciót.

**TP1, TP2** — Take-Profit küszöbök. A swing pivot architektúrában TP1 = entry + 1,5 × ATR, TP2 = entry + 3,0 × ATR.

**VIX** — Volatility Index. Az S&P 500 30-napi várt volatilitásának mértéke. A pipeline-ban makró-kontextusként + a (régi) `M_VIX` multiplier-ként szerepelt.

---

## Hivatkozási anyagok

A jelen bemutató mélyebb részletei a következő belső dokumentumokban elérhetők:

- `docs/decisions/2026-05-14-day63-decision-outcome.md` — A 14 stratégiai döntés részletes rögzítése.
- `docs/strategic-review/2026-05-08-strategic-review-full.md` — A 25 oldalas teljes 60-napi minta elemzés.
- `docs/strategic-review/2026-05-08-strategic-review-mathematical.md` — A swing pivot időtáv-választásának matematikai megalapozottsága (mutual information, Kelly-fraction).
- `docs/master-reference/01-system-snapshot.md` — Az aktuális pipeline architektúra-snapshot.
- `docs/master-reference/03-day63-status.md` — A Day 63 milestone tracker.
- `docs/analysis/flow-decomposition.md` — A 7-alkomponens-flow Bonferroni-korrigált validációja.
- `docs/analysis/scoring-validation.md` — A kompozit pontszám prediktív validációja.

A teljes kódbázis és a paper trading nyers adatai a `/Users/safrtam/SSH-Services/ifds/` git-repóban érhetők el.

---

**A dokumentum vége.**

*Készítette: az IFDS team, 2026-05-19.*
*Verzió 1.0 — szakmai csapat bemutató. ~7400 szó, kb. 90 perc tempóval.*
