# Daily Review — 2026-04-27 (hétfő)

**BC23 Day 11 / W18 Day 1**
**Paper Trading Day 51/63**

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | -$329.82 |
| Napi P&L net | **-$360.90** (commission $31.08) |
| Kumulatív P&L | **-$348.85 (-0.35%)** ← visszaesett a -$19 breakeven-ből |
| Pozíciók (új) | 5 ticker (MU, MPC, RIG, POST, ON) — state-split miatt 9 trade |
| Win rate | 2/5 ticker (MU, RIG nyert; POST, ON, MPC vesztett) |
| TP1 hit rate | 0/5 (0%) |
| TP2 hit rate | 0/5 (0%) |
| Exit mix | 8× MOC, 1× LOSS_EXIT (ON), 0× SL, 0× TP |
| Avg slippage | -0.11% (kevert; MU és ON pozitív, POST/RIG/MPC negatív) |
| Commission | **$31.08** ← újabb napi maximum |
| SPY return | +0.17% |
| Portfolio return | -0.33% |
| **Excess vs SPY** | **-0.50%** ← underperform enyhén pozitív bull napon |
| VIX close | (Phase 0 nem rögzítette — `vix_close: null`) |

## Piaci kontextus — átállás új regime közelébe?

**A SPY +0.17% csendes pozitív, de a belső dinamika érdekes.** Tegnap a péntek +0.78%-os záró után ma egy enyhe kontinuáció. Viszont a **mi portfólió-állományunk -0.33%-ot ad**, miközben SPY +0.17% — a -0.50% excess **a W17 leggyengébb napjához (szerda -0.94%) hasonló**.

**A MID bundle (frissen, ma este 22:00 cron):**
- **Regime:** Stagflation Day 11/28 (~40% mid-stage)
- **Top sectors (MID):** XLK, XLE, XLB
- **Bottom sectors (MID):** XLV, XLF, XLY
- **TPI:** 43.0 HIGH (Significant pressure)
- **Yield curve:** bull_steepener
- **Etf_xray freshness:** 2026-04-24 (3 napos elmaradás, péntek óta nincs új sector data — normál weekend gap)

**Mit vettünk ma vs. mit ajánlott a MID:**

| Ticker | Sector | MID rangsor |
|--------|--------|-------------|
| MU | Tech (XLK) | **TOP-3** ✓ |
| MPC | Energy (XLE) | **TOP-3** ✓ |
| RIG | Energy (XLE) | **TOP-3** ✓ |
| POST | Cons. Defensive (XLP) | nincs top/bottomban |
| ON | Tech (XLK) | **TOP-3** ✓ |

**4/5 ticker MID-ajánlott szektorban.** Mégis -$330. Ez **fontos signal**: a sector rotation **nem garancia** — még ha a "right sector"-ban is vagyunk, az **egyéni ticker selection** kritikus.

## Pozíciók részletei

### Nyertesek (2)

**MU (semi, score 94.5):** Entry $521 (slippage **-0.71%**, fill $521 a planned $524.75 helyett — **kedvező**), MOC close $524.51 = **+$52.72**. Az +$3.51 mozgás +0.67% intraday — gyenge nap a tech-szektorra, főleg a 94.5 score mellett. **Nem TP1 hit**: TP1 ~$535 (1.25×ATR ~+2.7%) lett volna.

**RIG (energy, score 92.0):** 4-split (4 trade), entry $6.44 mind, exit $6.52 mind = **+$140.64 összesen** (40+40+40+20.64). +1.24% intraday, **konzisztens nyertes**. Kis ticker ($6 ár), de **stabil mozgás** és **MID #2 sector** validáció.

### Vesztesek (3)

**MPC (energy, score 92.5):** Entry $230 (slippage +0.09%, gyakorlatilag flat), MOC $227.27 = **-$158.34**. -1.19%-os napi mozgás. Ugyan a MID szerint Energy top-3, **a MPC a refining alszektorban van** — ez nem feltétlen profitál a XLE momentumából (a MID XLE komponensek általában upstream-orientáltak).

**POST (cons. defensive, score 91.5):** 2-split, entry $105.59 (slippage **+0.30% rossz**), exit $103.87 = **-$299.28 összesen** (-127.28 - 172.00). **Napi vesztes**, -1.63% mozgás. **A POST a MID bottom-3 sektor (XLY consumer cyclical bár XLP defensive — ez érdekes split, ellenőrzendő)**.

**ON (semi, score 89.5):** Entry $98.89 (slippage **-0.54% kedvező**), **LOSS_EXIT @ $97.40** = **-$65.56**. -1.51% mozgás, és a **csak ticker, ami a -2% küszöb alá ment** intraday. A 89.5 score volt a nap legalacsonyabb — **konzisztens score-vesztés korreláció**.

## Score → P&L napi nézet

| Ticker | Score | P&L net | Win? |
|--------|-------|---------|------|
| MU | **94.5** | +$52.72 | ✓ |
| MPC | 92.5 | -$158.34 | ✗ |
| RIG | 92.0 | +$140.64 | ✓ |
| POST | 91.5 | -$299.28 | ✗ |
| ON | **89.5** | -$65.56 | ✗ (LOSS_EXIT) |

**Egy kicsit pozitív rank korreláció:** a legmagasabb score (MU 94.5) nyert, a legalacsonyabb (ON 89.5) LOSS_EXIT. **De**: a MPC (92.5) a 2. legnagyobb vesztes, és a POST (91.5) a legnagyobb vesztes. **r ≈ +0.1, gyenge pozitív** — hasonló a W17 r=+0.180-hoz.

## A W18 első nap diagnosztikája

### 1. Visszaesés a -$19 breakeven-ből

**W17 zárta -$19 (gyakorlatilag breakeven). Egy nap múlva -$349.** Ez **-$330 napi visszaesés**, ami **22% a teljes BC23 deficitnek**. Egy nap rossz, de **statisztikailag nem rendkívüli** — a W17 hétfője is -$433 volt. **Egy ilyen nap nem cáfolja a BC23-at**, de a következő 4 napban **konzisztencia** kell.

### 2. State-split commission terhelés

**$31.08 commission egyetlen napon** — még az eddigi heti záró ($82 W17 alatt) **38%-a egyetlen napra**. A **RIG 4-split** egyedül ~$12-15 extra commission. Ha az ARMK 4-split (péntek) és a RIG 4-split (ma) **gyakori** lesz, akkor a 12% W17 commission ratio **emelkedhet** W18-ban. **Figyelendő.**

### 3. A MID first day működik — adat van

**Az első MID snapshot a `state/mid_bundles/2026-04-27.json.gz`-ben.** 17 mező feltöltve, top/bottom sectors elérhetők, freshness layer szétválasztva. A vasárnapi comparison script már **tényleges adatokon** dolgozhat.

A `freshness.etf_xray: 2026-04-24` jelzés **fontos** — péntek óta nincs új sector momentum a MID-en (normál weekend gap). A hétfő 17:15 ET (~23:15 CEST) cron majd frissít. **Azaz a kedd reggeli MID adat már friss XLE/XLK rangsorral fog dolgozni**, és tudja-e majd a MID hogy egy hétvégi piaci esemény (pl. olajár, kamatdöntés) hogyan alakította át a relatív szektor erőt.

### 4. A POST egy érdekes eset — szektor-ambiguitás

**POST = Post Holdings**, cereal company. A **szektor besorolás**:
- IFDS Phase 3 valószínűleg **XLP** (Consumer Defensive) sorolta — ezért score 91.5 magas
- A MID **Bottom sectors** közt **XLY** (Consumer Cyclical) van, **NEM** XLP
- Tehát a MID **NEM** mondja, hogy a POST szektora rossz

**Mégis -$299 vesztett.** Ez **ticker-specifikus** — az egyéni POST ár-mozgás (cereal piaci news? short interest? earnings közeli?) húzta le. **A MID nem segített ebben az esetben**, mert a sector level nem volt rossz, csak a ticker volt **rossz választás** a magas IFDS score-ra ellenére.

**Ha a M_contradiction multiplier (szerda implementáció) ma érvényes lett volna:** ellenőrizni kell, **kapott-e POST CONTRADICTION flag-et** a mai Company Intel-ben. Ha igen, ×0.80 méret = -$239 (-$60 megtakarítás). Ezt a kérdést a `state/phase4_snapshots/2026-04-27.json.gz`-ből lehet megválaszolni, érdemes szerda reggel megnézni.

### 5. Volatilitás a MID Stagflation 11/28 napon

**Stagflation regime "early-mid stage"** (11 nap a 28 nap mediánból). Ez **érdekes makro-jel**:

- A regime még **friss** — nem telített, a piac még alkalmazkodik
- A median szerint **17 nap múlva** kezd statisztikailag valószínűbb a regime váltás
- **Most** a "lockstep volatility" + "Stagflation" kombináció jellemző — az egyedi tickerek **NEM differenciálódnak** jól, mert a korreláció magas

**Mit jelent ez gyakorlatilag:** a magas score-ú ticker **és** a low score-ú ticker is hasonló módon mozognak. A scoring **kevésbé prediktív** ebben a regime-ben — pontosan a Regime-Aware Position Sizing (BC25+) javaslat indoklása.

## Kulcsmegfigyelések

### 1. Az első W18 nap rossz, de nem katasztrófa

A -$330 net napi vesztes **a W17 hétfőhöz** (-$433) hasonló nagyságrend. **Nem új probléma**, hanem **a BC23 ismert kockázata**. Az M_contradiction multiplier (szerda) és a vasárnapi MID comparison **több hét múlva** ad választ arra, hogy ezek strukturálisan kezelhetők-e.

### 2. A MID infrastruktúra dolgozik, de még nem segít

**Az adat ott van** — első snapshot, top/bottom sectors elérhetők. A `mid_vs_ifds_sector_comparison.py` **vasárnap fog futni**. **Most még nem hatja a döntéseket**, csak passzívan gyűjti.

**De máris észrevettünk valamit:** 4/5 mai ticker MID top-3 sectorban volt, mégis -$330. **Az IFDS Phase 3 sector rotation tehát "rendben van"** ebből a szempontból — a probléma **a ticker-szintű választás** a sectoron belül. Ez **fontos finding**: a BC25 (MID Phase 3 átvétel) **nem fog csodát** hozni, mert a sector level már most is jó. **A ticker-választás javítása** kell.

### 3. POST rossz választás magas score ellenére

A POST -$299 a nap legnagyobb vesztese. Score 91.5 magas, a MID nem flagged a sector-t bottom-ban. **Mégis** rossz mozgás. **Pontosan** az a típusú eset, amire a M_contradiction multiplier épül — ha a Company Intel CONTRADICTION-flagged a POST-ot, akkor a -$299 → -$239 lenne -20% mérettel.

**Szerda reggel ellenőrzendő:** a `state/phase4_snapshots/2026-04-27.json.gz`-ben **mit mondott** a Company Intel POST-ról?

### 4. A score korreláció továbbra is enyhe pozitív

W17 r=+0.180. Ma egy napon belül **rank-szinten**: legmagasabb score nyert, legalacsonyabb score LOSS_EXIT. De a középső 3 vegyes (MPC, RIG, POST). **Néhány héti adattal** stabil-e ez a +0.1-0.2 sáv, vagy visszacsap negatívba? **Kiderül**.

## Anomáliák

- **`vix_close: null`** a daily_metrics.json-ben. A Phase 0 vagy a metrika script nem rögzítette. Nem kritikus, **de** ha tendenciásan elmarad a következő napokban, **kis CC task** lesz (a `daily_metrics.py`-ban a VIX read-back fix).
- **MID Bundle első éles snapshot kész** — 17 mező feltöltve, freshness layer látható
- **Telegram regresszió** változatlanul él
- **CRGY + AAPL leftover** — már 6+ napja, **hétvégén nem nukolva**, csendben tovább pörögnek a portfolio-ban (de nem érintik a P&L-t, mert a portfólió-érték scriptek figyelmen kívül hagyják)

## Teendők

- **Ma este:** nincs
- **Holnap kedd ápr 28:**
  - Normál pipeline, BC23 W18 Day 2
  - Chat: M_contradiction task fájl megírva (`docs/tasks/2026-04-28-m-contradiction-multiplier.md`) — szerdára CC-nek kész
- **Szerda ápr 29:**
  - CC: M_contradiction multiplier implementáció (kb. 2-3h)
  - Tamás reggel: `gzcat state/mid_bundles/2026-04-28.json.gz | jq '.flat.regime'` ellenőrzés
  - Tamás: ellenőrizze, hogy a hétfői POST kapott-e CONTRADICTION flag-et a Company Intel-ben (szerda reggeli phase4_snapshots inspekció)
- **Csütörtök-péntek:** normál pipeline, M_contradiction live data
- **Vasárnap máj 3:** Chat W18 weekly elemzés + MID vs IFDS comparison

## Kapcsolódó

- `state/phase4_snapshots/2026-04-27.json.gz`
- `logs/pt_events_2026-04-27.jsonl`
- `logs/pt_eod_2026-04-27.log`
- `state/daily_metrics/2026-04-27.json`
- **`state/mid_bundles/2026-04-27.json.gz` ← első MID shadow snapshot ✨**
- `docs/tasks/2026-04-28-m-contradiction-multiplier.md` (megírás folyamatban kedd reggel)
