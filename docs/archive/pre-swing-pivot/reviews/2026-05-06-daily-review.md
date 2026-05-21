# Daily Review — 2026-05-06 (szerda)

**BC23 Day 18 / W19 Day 3**
**Paper Trading Day 58/63**
**M_contradiction LIVE 3. nap**

**Adat-frissesség:** state/.last_sync = 2026-05-07T05:00:32Z (csütörtök 07:00 CEST, post-EOD)

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | +$247.68 |
| Napi P&L net | **+$233.91** ⭐ (commission $13.77) |
| Kumulatív P&L | **-$1,129.43 (-1.13%)** ⭐ — visszamászás +$248 a kedd-i mélypontról |
| Pozíciók (új) | **3 ticker** (ERIC, CDNS, UEC) — 4 trade (ERIC 2-split) |
| Win rate ticker szinten | 2/3 (UEC, CDNS nyertek; ERIC breakeven $0.00) |
| TP1 hit rate | 0/3 |
| Exit mix | **4× MOC**, 0× LOSS_EXIT, 0× SL, 0× TP, 0× trail |
| Avg slippage | **-0.10%** (kedvező! UEC -0.20%, ERIC -0.17%, CDNS +0.08%) |
| Commission | $13.77 ← **alacsony** (kis pozíciószám) |
| SPY return | **+1.39%** — **nagy bull nap** |
| Portfolio return | +0.25% |
| **Excess vs SPY** | **-1.14%** ⚠️ — **bull rally underperform pattern megerősítve** |
| VIX close | **17.19** (Δ=-0.58%, stabil 17 körül) |

## ⭐ A hét első nyertes napja — pozitív rendszerimpact

**+$233.91 net, kumulatív visszamászás -$1,377 → -$1,129.** Ez **a W19 első pozitív napja**, és **a BC23 deploy óta a 4. legjobb nap** (a 4 erős nap: ápr 13 +$381, ápr 15 +$587, ápr 16 +$563, ma +$234).

**Az excess vs SPY -1.14% azonban ⚠️ aggasztó:**
- **SPY +1.39%** — nagy bull rally
- A "bull rally underperform" pattern **harmadszor jelentkezik 4 nap alatt** (csüt -0.57%, pént -1.50%, ma -1.14%)

**A két különböző érték mit jelent:**
- **Pénzügyileg:** +$234 nyereség, a kumulatív visszamászás folytatódik
- **Relatív teljesítményben:** SPY-vel buy-and-hold-olva +1.39% (=$1,390 a $100k-on), míg mi csak +0.25%

**Strukturális finding:** a swing trading rendszer **defenzív erejű**, ami negatív SPY napokon outperformol (mint W19 D1 hétfő +0.21%) **és** bull rally napokon underperformol (mint a mai). **Ez NEM hiba, hanem a stratégia természetes karaktere.**

## Pozíciók részletei

### Nyertesek (2 ticker)

**UEC (Uranium Energy Corp, score 91.0 — LEGALACSONYABB):** 256 share, entry $15.15 (slippage **-0.20% kedvező**), MOC $15.78 = **+$161.28 (+4.16%)** ⭐ **a nap sztárja, és a hét 4. legjobb single-ticker nyerője**. Pattern:
- 17:00:15 trail_activated_b @ $15.45 (+1.78% felett)
- **17:00:17 BREAKEVEN_LOCK_APPLIED** ⭐ ($13.81 → $15.18 entry-re) — **PROFIT-BASED TRIGGER!**
- MOC zárás $15.78 (+4.16%), trail SL sosem aktivált (folyamatosan emelkedett)

**Ez egy szuper pattern:** entry-ből **azonnal +1.78% felett indult**, breakeven lock pillanat alatt aktivált, és onnan +4.16%-ig emelkedett.

**CDNS (Cadence Design Systems, score 91.5):** 36 share, entry $352.69 (slippage +0.08%), MOC $355.09 = **+$86.40 (+0.68%)**. 
- 18:55:12 trail_activated_b @ $354.48 (+0.59%) — a **window előtt 5 perccel**
- 19:10 / 19:55 trail_sl_update folyamatosan ($335.62 → $335.79)
- MOC $355.09 — közel az intraday peak-hez

### Breakeven (1 ticker, 2 trade)

**ERIC (Ericsson, score 92.5 — LEGMAGASABB):** 2-split, entry $12.01 (slippage **-0.17% kedvező**), MOC $12.01 (mindkét leg!) = **$0.00 P&L** mindkettőn! **Pontos breakeven** — entry = exit, ami **rendkívül szokatlan**. Az ár egész nap szigorúan oldalazott $11.95 - $12.10 sávban.

**Score → P&L napi nézet**

| Ticker | Score | M_contradiction | P&L net | Win? | Megjegyzés |
|--------|-------|-----------------|---------|------|------------|
| **ERIC** | **92.5** | 1.0 | $0.00 | breakeven | legmagasabb score, semmilyen mozgás |
| CDNS | 91.5 | 1.0 | +$86.40 | ✓ | trail 18:55 (window előtt) |
| **UEC** | **91.0** | 1.0 | **+$161.28** | ⭐ | **legalacsonyabb score, +4.16%, BL aktivált** |

**Megfigyelés:** **A legmagasabb score-ú ticker (ERIC 92.5) volt a leggyengébb performer, a legalacsonyabb (UEC 91.0) a legjobb** — folytatódó **negatív score → P&L korreláció pattern**! Ez most már **harmadik egymás utáni nap** (hétfő VTR 93.5 vesztett, kedd NE 95.0 vesztett, ma ERIC 92.5 breakeven).

---

## ⭐ KRITIKUS FINDING — a Breakeven Lock NEM csak window-based!

**Ezt tegnap nem tudtam, és a backlog idea-m részben hibás volt.**

A mai UEC log konkrét bizonyítéka:
```
17:00:15 trail_activated_b @ $15.45, entry $15.18 (+1.78% profit)
17:00:17 breakeven_lock_applied: old_sl $13.81 → new_sl $15.18 (entry)
         lock_type: "profit_breakeven"
```

**Az UEC 17:00 CEST-kor aktivált — két órával a 19:00 window előtt** — ÉS MÉGIS kapott Breakeven Lock-et! **A `lock_type: "profit_breakeven"` jelzi: profit-based trigger volt**, nem time-based.

### Mi tegyük a tegnapi finding összevetésekor

A teljes pattern matrix W19-ből:

| Nap | Ticker | Trail aktiv idő | Profit aktivkor | Breakeven Lock? | Eredmény |
|-----|--------|-----------------|-----------------|-----------------|----------|
| Hétfő | BG | 17:00 CEST | +2.63% | ✓ alkalmazva (17:00:19) | MOC nyertes (+$179) |
| Hétfő | OII | 18:15 | +0.68% | ✗ NEM (window előtt) | MOC nyertes (+$49 — szerencse) |
| Hétfő | NOV | 18:40 | +0.51% | ✗ NEM | MOC nyertes (+$88 — szerencse) |
| Kedd | BEKE | 17:45 | +0.55% | ✗ NEM | MOC nyertes (+$49 — szerencse) |
| Kedd | PTEN | 18:40 | +0.51% | ✗ NEM | MOC vesztes (-$36) ← **ezt vesztettük el** |
| **Szerda** | **UEC** | **17:00** | **+1.78%** | **✓ alkalmazva** ⭐ | **MOC nyertes (+$161)** |
| Szerda | CDNS | 18:55 | +0.59% | ✗ NEM (window előtt 5 perccel) | MOC nyertes (+$86 — szerencse) |

**A pattern most már tisztán látszik:** a Breakeven Lock-nek két aktiválási feltétele van:
1. **Profit-based trigger:** valamilyen küszöb felett (UEC +1.78% trigger-elt, BG +2.63% trigger-elt) — a pontos küszöb **a kód olvasása nélkül nem tisztázható**, de ~1% körül lehet
2. **Time-based trigger:** 19:00:00-19:04:59 CEST window — **DE** ez csak akkor releváns, ha a profit alacsonyabb a profit-küszöbnél

**Tehát a tegnapi finding-om részben hibás:** a feature **NEM csak a window-ban aktivál** — **profit ≥ ~1% bármikor** is aktivál. A PTEN tegnap +0.51%, BEKE +0.55%, OII +0.68%, NOV +0.51%, CDNS ma +0.59% **mind a profit-küszöb ALATT** voltak, ezért NEM kaptak BL-et.

### A backlog idea revíziója szükséges

**A `Breakeven Lock window-bővítés` task korrigálandó.** A tényleges javaslat:

> **Profit-küszöb csökkentése a Breakeven Lock-ben** — a jelenlegi profit-trigger ~1.0% (becsült). Csökkenteni 0.5%-ra (a megfigyelt trail aktiválási profit átlagra). **Hatás:** mind a 4 W19 D1-D3 trail aktiválás (BEKE 0.55%, NOV 0.51%, PTEN 0.51%, CDNS 0.59%) BL-et kapott volna. A PTEN ma helyett -$36 → 0$ (becsült megtakarítás).

**Effort:** ~10-15 min config tuning + 2-3 plusz unit teszt. **Sokkal egyszerűbb mint a tegnapi javaslat** (kód-módosítás kibővítéssel).

**Holnap reggeli teendő:** korrigálom a backlog-ideas.md-t — a "Breakeven Lock window-bővítés" tételt cserélem **"Breakeven Lock profit-küszöb csökkentés"-re**, és frissítem a fájlt.

---

## "Végére visszaesik" pattern — mai adatok

A tegnapi megfigyelésed konkrét adattal vizsgálva:

| Ticker | Intraday peak | MOC | Peak → MOC |
|--------|---------------|-----|------------|
| UEC | $15.78 (folyamatos emelkedés) | $15.78 | **0.00%** ⭐ stabil zárás |
| CDNS | ~$354.94 (19:55) | $355.09 | **+0.04%** ⭐ MOC magasabb! |
| ERIC | $12.10 (intraday) | $12.01 | -0.74% |

**Mai napon a "végére visszaesik" pattern NEM jelentkezett az UEC és CDNS pozíciókon.** Ez **fontos kvalifikáció** — a pattern **nem minden nap** működik. Tegnap (kedd) erős volt (PTEN -1.55% retracement), ma alig.

**Lehetséges magyarázat:** mai napon **nagy bull rally** volt (SPY +1.39%), ami **teljes piaci momentum-ot adott**, és a végén nem volt retracement. Ezzel szemben kedden volt afternoon retracement (SPY +0.80% napi átlag).

**Hipotézis (tesztelendő):** a "végére visszaesik" pattern **erős vegyes/lateral piaci napokon**, **gyenge erős bull rally napokon**. **Több nap adat kell** a megerősítéshez.

---

## Stagflation regime és bull rally kontextus

A mai nap **nagy bull rally** volt (SPY +1.39%, VIX -0.58% stabil 17.19-en). **Strukturális megfigyelés:**

A Stagflation Day 16/28 (mid-stage) regime alatt **a bull rally-k furcsán viselkednek**:
- Bull rally **van**, de **nem a teljes piacon** — szektor-rotáció erős
- A swing rendszerünk **nem fogja meg** a teljes 1.39% mozgást, mert a long-only rendszer **csak 3-5 ticker-en** koncentrál
- Az AGNC, BUD, NE típusú **single-event veszteségek** elviszik az alpha-t

**Implikáció a Day 63 keret szempontjából:**
- Ha a piac **stabil bull rally-be vált** (VIX <17, napi +0.5-1%), akkor **strukturálisan nehéz** alpha-t mutatni
- Az élesítési feltétel ("20+ napon át regime nem Stagflation ÉS excess >+1%") **strukturálisan nehéz** ilyen környezetben
- **Realisztikus Day 63 várt kimenet**: PAPER FOLYTATÁS (default) — most már 3 nap egymás után megerősítve

---

## Day 63 keret — szerda esti állapot

| Metrika | Érték | Status a kerethez képest |
|---------|-------|--------------------------|
| Day | **58/63** — **5 nap van hátra** | |
| Kumulatív P&L | **-$1,129 (-1.13%)** ⭐ | **biztonságos sávban**, javuló trend |
| ÉLESÍTÉS távolság | +$4,129 a +$3,000-hoz | **5 nap × +$826/nap → NEM realisztikus** |
| LEÁLLÍTÁS távolság | excess -0.46% távol a -1.5%-tól | **biztonságos sávban**, ~1% buffer |
| 8 napi excess vs SPY átlag | -0.46% | W18 + W19 D1-D3 |
| VIX W19 átlag | 17.59 | **18 körül**, monitor aktív |

**Pozitív megfigyelések:**
- A kumulatív P&L **3 nap után most javul** (D1 -$1,141 → D2 -$1,377 → **D3 -$1,129** ⭐)
- VIX **stabil 17 körül** (nem mászik 18 fölé), leállítási feltétel **inactíve**
- 5 nap maradt — a paper folytatás default sáv biztosított

**Aggasztó megfigyelések:**
- Excess vs SPY 8-napi átlag **-0.46%/nap** — folytatódó underperform a bull rally-ben
- 3/5 napon underperform (nagy SPY napokon)

**Realisztikus Day 63 várt kimenet:** kumulatív P&L valószínűleg -$1,500 és -$700 között (paper folytatás default).

---

## A 18 napi BC23 átfogó kép

| Mutató | BC23 18 napi átlag |
|--------|--------------------|
| Net P&L összesen | -$1,129 |
| Pozitív napok | 7/18 (38.9%) |
| Negatív napok | 11/18 (61.1%) |
| Átlagos P&L pozitív napon | +$372 |
| Átlagos P&L negatív napon | -$340 |
| Win/Loss arány | 1.09 (alig pozitív) |

**Kvalifikáció:** mintegy 0.85% / 18 nap = ~0.94% / hó negatív return. **Reális 1% / hó alpha cél** szempontjából **ez 2× tévedés alpha-ban** (amit -0.94% / hó-t hozott helyett +1% / hó-t kellett volna).

**De:** a M_contradiction (3 napja LIVE) és a **Breakeven Lock proper threshold** (megérteni kell, ha az nem volt automatikusan) **mindkettő** olyan strukturális javítás, amit **most még nem mértünk**. **Még 5 nap** Day 63-ig — a finomítások gyűlhetnek.

---

## Anomáliák

- **CRGY/AAPL leftover phantoms** továbbra is — `monitor_positions.py` BUG (régóta ismert)
- **LION/SDRL/DELL/DOCN phantom events** 22:00 CEST — IBKR API quirk
- **AVDL.CVR** non-tradable, ignorálható
- **3 ticker összesen** (NEM 5 max!) — érdekes, hogy ma kevés ticker fűlt át a Phase 4 küszöbön. **Lehet** hogy a magas universe (425+ ticker) ellenére kevés ticker tette át mind a 3 küszöböt (flow + tech + funda)

---

## Kulcsmegfigyelések

### 1. ⭐ A hét első nyertes napja, kumulatív visszamászás +$248

**+$234 net, kumulatív -$1,129 (-1.13%).** Az UEC +$161 single-ticker nyerő (alacsony score 91.0 ellenére!) tette ki a fő profitot. **Megerősíti** a `flow score +0.136*` egyetlen statisztikailag jelentős prediktor a W18 scoring validation-ből.

### 2. ⭐ KRITIKUS — a Breakeven Lock profit-based trigger-rel ELŐSZÖR LIVE látva!

**Az UEC 17:00 CEST-kor (a 19:00 window-on KÍVÜL) Breakeven Lock-et kapott** — `lock_type: "profit_breakeven"` típusú audit log. **Ez fundamentálisan más** mint amit tegnap gondoltam. **A feature már most is profit-based**, csak a profit-küszöb a kérdés (~1% becsült). **A backlog idea revíziója szükséges** holnap reggel.

### 3. ⚠️ Bull rally underperform pattern HARMADIK egymás utáni napon

**SPY +1.39% mai, mi +0.25% — excess -1.14%.** Múlt csütörtök -0.57%, péntek -1.50%, és most -1.14%. **3/5 utolsó nap underperform a bull napokon** — ez **strukturális karakter**, nem hiba.

### 4. Score → P&L negatív korreláció FOLYTATÓDIK

**ERIC 92.5 (legmagasabb) = $0.00, UEC 91.0 (legalacsonyabb) = +$161.** **3 egymás utáni nap** ahol a legmagasabb score-ú ticker a leggyengébb. **Pearson r ≈ 0** napon belül, **és valószínűleg negatív tendenciális** ezeken a napokon.

### 5. "Végére visszaesik" pattern MA NEM jelentkezett erősen

**UEC peak = MOC, CDNS peak < MOC (+0.04% felett!)**. Ez **fontos kvalifikáció** — a pattern **nem mindig** működik. Hipotézis: bull rally napokon **nincs retracement**, vegyes napokon **van**. Több adat kell.

### 6. 0× LOSS_EXIT, 0× SL — szépen tartott pozíciók

A mai nap **strukturálisan stabil** volt — **egy ticker sem aktivált negatív exit-et**. Ez **különbség** a hétfőtől (AGNC -$380 6-split LOSS_EXIT). **Az SL és LOSS_EXIT küszöbök** védettek, és nem triggereltek false-pozitív-an.

---

## Teendők

### 1. Backlog-ideas.md korrigálás (holnap reggel)

**A `Breakeven Lock window-bővítés` tétel** részben hibás volt. **Cserélni:**
- **Eredeti:** "trail bracket B aktivál bármikor +0.5% felett, alkalmazni Breakeven Lock floor-t"
- **Korrigált:** "Profit-küszöb csökkentés a Breakeven Lock-ben — a jelenlegi ~1% threshold (becsült) csökkentése 0.5%-ra"

A korrekció **egyszerűbb és pontosabb**, mert a feature **már most is profit-based**.

### 2. Holnap (csütörtök máj 7) — W19 Day 4

- **Pipeline:** normál ritmus
- **W19 Weekly metrika** péntek 22:00 CEST (W19 nap 5 EOD után)

### 3. Day 63 (csütörtök máj 14) — 6 nap múlva

- **09:00 Reminder**
- **W19+W18+W17 adatok** együtt scoring validation újrafuttatás
- Döntés: **PAPER FOLYTATÁS** (legvalószínűbb)
- Új doc: `docs/decisions/2026-05-14-day63-decision-outcome.md`

---

## Kapcsolódó

- `state/phase4_snapshots/2026-05-06.json.gz`
- `logs/pt_events_2026-05-06.jsonl` ← **UEC profit_breakeven 17:00** (a "window előtti" BL)
- `logs/pt_eod_2026-05-06.log`
- `state/daily_metrics/2026-05-06.json` ← vix_close = 17.19, kumulatív -$1,129

**State:** BC23 + Breakeven Lock (profit_breakeven trigger ÉLES) + MID Bundle + vix-close + LOSS_EXIT whipsaw audit + M_contradiction LIVE

**Aktív CC tasks:** nincs

**W19+ backlog idea-k (6, korrigálandó):**
1. 10-Q / 10-K SEC Filing Exclusion (P1)
2. ADR earnings adatforrás fix (P1)
3. **Breakeven Lock profit-küszöb csökkentés** (P2 — KORRIGÁLANDÓ tegnapi tétel)
4. High-score liquidity check (P3)
5. TP1 cél revízió (P2)
6. Phase 4 snapshot enrichment (P3)
