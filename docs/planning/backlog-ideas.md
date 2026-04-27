# IFDS Backlog — Ötletek, nem ütemezett

## VectorBT CC Skill (BC20+ scope)

**Forrás:** marketcalls/vectorbt-backtesting-skills repo elemzése (2026-02-24)

**Ötlet:** IFDS-specifikus CC skill(ek) VectorBT parameter sweep-hez, a Phase 4 snapshot adatokon alapulva. Lehetséges fókuszok:
- `/sim-sweep` — min_score, weight_flow/funda/tech, ATR multiplier, hold napok sweep → heatmap + CSV
- `/sim-validate` — SimEngine vs VectorBT párhuzamos futtatás, eredmény összevetés
- `/sim-score` — scoring weight optimalizálás Sharpe alapján

**Miért érdemes:** munkamenet-gyorsítás — egy paranccsal CC végigcsinálja a teljes sweep → heatmap → CSV pipeline-t.

**Előfeltétel:** ~30-40 nap Phase 4 snapshot adat (legkorábban április, BC20 scope).

**Implementáció típusa (még nem döntött):** prompt template + tudásbázis, vagy prompt + kész `ifds_sim_vbt.py` modul.

**Státusz:** PARKOLT — BC20 előtt nem aktuális.

---

## MCP Server — IFDS + MID (BC23+ scope)

**Forrás:** financial-datasets/mcp-server repo elemzése (2026-02-28)

**Ötlet:** Saját MCP server a meglévő API-k (FRED, FMP, Polygon, Unusual Whales) fölé, két céllal:

**A) Template alapú saját MCP server:**
- A `financial-datasets/mcp-server` repo struktúráját követve
- Csak a már meglévő IFDS/MID API integrációk exponálása MCP toolként
- Claude Desktop-ból közvetlenül lekérdezhető: pipeline státusz, logok, paper trading P&L
- Nem új adatforrás — kizárólag meglévő wrapper-ek (FMPClient, stb.)

**C) IFDS/MID pipeline introspekció:**
- `get_pipeline_status` — legutóbbi cron futás eredménye
- `get_paper_trading_pnl` — kumulatív P&L, napi trades
- `get_positions` — aktuális nyitott pozíciók
- `get_regime` — aktuális BMI/GIP rezsim
- `query_logs` — log keresés dátum/ticker alapján

**Előfeltétel:** BC23 után — MID produkciós állapot, IFDS stabil.

**Státusz:** PARKOLT — BC23 előtt nem aktuális.

---

## Company Intel v2 — MCP-alapú adatgazdagítás (BC23+ scope)

**Forrás:** NXST GAAP vs adjusted EPS eset elemzése (2026-02-28)

**Ötlet:** A `company_intel.py` jelenleg FMP + Anthropic API kombinációt használ. BC23 után érdemes lehet:
- MCP server toolként exponálni (Claude Desktop direkt hívhatja)
- Adjusted EPS adatforrás integrálása (FMP `/stable/income-statement` vagy külső)
- Richer context: short interest, options flow summary, insider sentiment score
- Esetleg: napi automatikus futás Telegram push helyett MCP pull modellben

**Előfeltétel:** MCP server megléte (fenti item), BC23 után.

**Státusz:** PARKOLT — BC23 előtt nem aktuális.

---

## M_target penalty + TP1 ceiling az elemzői High target alapján (W18+ scope)

**Forrás:** GFS 2026-04-20 eset. Ticker ár $59.09, analyst High target $60, TP1 $62.18 — a TP1 3.6%-kal a legoptimistább elemzői célár felett. Company Intel explicit CONTRADICTION flag.

**A probléma:**
- A jelenlegi M_target penalty csak 20%+ consensus fölötti árat büntet (×0.85) — a GFS 15.5% fölött ezt nem éri el, M_total=1.000 marad
- A TP1 pedig **nem veszi figyelembe** az elemzői range-et — teljesen ATR-alapú, lehet messze a High fölött
- Eredmény: a rendszer olyan mozgást vár, amit **egyetlen Wall Street elemző sem** prediktál

**Tervezett változtatások (3 szint):**

### 1. M_target szigorítás (gyors paraméter változtatás)
```python
# defaults.py
# Régi (BC23):
m_target_penalty_threshold_mid = 0.20
m_target_penalty_threshold_high = 0.50

# Új:
m_target_penalty_threshold_mid = 0.10    # 10%: ×0.85
m_target_penalty_threshold_high = 0.25   # 25%: ×0.60
# + új szint:
m_target_penalty_threshold_extreme = 0.40  # 40%+: ×0.40
```

### 2. Penalty High target alapján (nem consensus)
```python
# Ha az ár már a legoptimistább elemzői célár fölött:
if price > target_high:
    m_target = 0.50  # aggresszív penalty
elif price > target_consensus * 1.10:
    m_target = 0.85
else:
    m_target = 1.00
```

### 3. TP1 ceiling a High target-re
```python
tp1 = min(
    entry + tp1_atr,           # ATR-alapú (jelenlegi)
    target_high * 0.98,         # nem megyünk a legmagasabb célár fölé
)

# Ha ez után a TP1 < entry → skip position
if tp1 <= entry:
    # Nincs realisztikus TP1, ne kereskedj
    continue
```

**Miért fontos:**
- A scoring_validation r=-0.414 inverz korrelációs minta egyik lehetséges magyarázata: a magas score-ú, overvalued tickerek a gyenge performerek
- A Company Intel CONTRADICTION flag már most detektálja ezt, de a scoring nem veszi figyelembe
- GFS mai TP1 ($62.18) a High target ($60) fölött van 3.6%-kal — a realistic felső határ $60 lenne

**Kockázat:**
- Minden ticker-t érint — a BC23 balance változik
- 2 hét kell a hatás mérésére
- Néhány momentum ticker (ahol az elemzők lassan frissítik a target-et) így nem kapna pozíciót — ez esetleg alpha-t áldoz fel

**Státusz:** W18 heti metrika után újraértékelni. Ha a TP1 hit rate még mindig <5% és a magas score-ú tickerek veszítenek → implementálni.

**Priority:** P2 — nem blokkoló, de a BC23 eredményesség javításának lehetséges eleme.

**Effort:** ~2h CC (config + scoring logic + test).

---

## Regime-Aware Position Sizing (BC25+ scope) — ÚJ, 2026-04-20

**Forrás:** 2026-04-20 MID STAGFLATION Day 3 + IFDS −$433 nap eset.

**A megfigyelés:**

A mai nap világosan mutatta, hogy a BC23 momentum-heavy scoring **nem egyformán jól teljesít** minden makro regime-ben. A MID dashboard ma a következőt mutatja:

- **Regime:** STAGFLATION Day 3 (TPI 43 HIGH)
- **Stock-Bond correlation 20D:** +0.41 (Positive Stagflationary — mindkettő esik)
- **VIX:** 18.86 (+7.96% aznap), lockstep volatility regime
- **COR3M:** 14.8 transitional (implied correlation emelkedik)
- **Path:** G→ I↑ P↑ (growth stagnál, infláció+policy szigorodik)

Ebben a regime-ben:
- A momentum long stratégia **strukturálisan ellenszélben** van
- A Stock-Bond korreláció miatt nincs diverzifikáció
- A COR3M emelkedés miatt az egyedi ticker-ek nem differenciálódnak

Az IFDS BC23 momentum-scoring-ja ezt nem tudja. Az összes ticker ugyanazt a scoring-t kapja, regime-től függetlenül.

**Ellentmondás a MID momentum leaderboarddal:**

Ma az IFDS Phase 3 `XLE, XLB, XLU` szektorokat VETO-zta momentum alapján. De a MID Momentum Leaderboard **XLB-t #1 helyen** rangsorolja risk-adjusted 20-day alapján (+234.5). Ez azt jelenti, hogy a két rendszer **eltérő mérési módszer**-rel **eltérő szektorokat** rangsorol. Az IFDS Phase 3 simple momentum-ot (ETF return % / SPY), a MID risk-adjusted return-t használ.

**Javasolt megoldás (BC25 után, amikor MID CAS konzumálódik):**

### A) Regime-weighted scoring súlyok

```python
# A MID /api/dashboard/gip endpoint adja a GIP gauges értékeit
# regime_scoring_weights.py

def get_scoring_weights(mid_regime: str) -> dict:
    """Return scoring weights based on current MID regime."""
    if mid_regime == "GOLDILOCKS":
        return {"flow": 0.60, "funda": 0.10, "tech": 0.30}  # jelenlegi BC23
    elif mid_regime == "STAGFLATION":
        return {"flow": 0.30, "funda": 0.50, "tech": 0.20}  # funda weight ↑
    elif mid_regime == "RECESSION":
        return {"flow": 0.20, "funda": 0.60, "tech": 0.20}  # value dominant
    elif mid_regime == "REFLATION":
        return {"flow": 0.70, "funda": 0.05, "tech": 0.25}  # momentum max
    else:
        return {"flow": 0.40, "funda": 0.30, "tech": 0.30}  # neutral default
```

### B) Regime-aware position count cap

```python
# defaults.py vagy regime-driven
regime_max_positions = {
    "GOLDILOCKS": 5,       # normál
    "STAGFLATION": 3,      # csökkentett risk
    "RECESSION": 2,        # minimum
    "REFLATION": 5,
    "DEFAULT": 5,
}
```

### C) Regime-aware VIX multiplier floor

Jelenleg a `M_vix` 0.25 floor-t használ. STAGFLATION + VIX emelkedés → érdemes 0.10-re csökkenteni a floor-t, hogy a pozícióméret drámaibban reagáljon.

### D) Sector VETO a MID momentum leaderboard alapján

A jelenlegi Phase 3 a saját ETF momentum-át számolja. A BC25 után ezt felváltaná a MID CAS. DE: ha a MID **azt mondja XLB #1**, az IFDS **ne VETO-zza**. Ez lesz a BC25 kernel-je.

**Előfeltétel:**
- BC25 IFDS Phase 3 ← MID CAS integráció
- MID API-n elérhető `/api/dashboard/gip` endpoint (már létezik)
- MID Momentum Leaderboard API endpoint (valószínűleg létezik)

**Kockázat:**
- Regime-függő súlyok változása hirtelen eltorzíthatja a scoring-t ha a regime gyakran vált
- Regime mismatch: ha a MID regime detection késik (pl. csak napi frissülés), az IFDS intraday döntései nem igazodnak

**Mikor kell implementálni:**
- **NEM MOST** — először a BC24 (UW flow) kell, hogy a flow komponens valódi institutional signal legyen
- **BC25 után**, amikor a MID CAS már konzumálva van
- Legkorábban W22+ (május vége), realisztikusan június

**Priority:** P2 — strukturális javítás, nem kritikus bug fix

**Effort:** ~4-6h CC
- Új `RegimeScoringWeights` config class
- `MIDClient` bővítés regime endpoint-tal
- Phase 4-5-6 scoring hook-ok
- Tesztek: mind a 4 regime-re külön

---

## Recent Winner Penalty / Position Dedup — POWI paradoxon (W18+ scope) — ÚJ 2026-04-23

**Forrás:** POWI 2026-04-22 (kedd) és 2026-04-23 (csütörtök) eset. Egymást követő napokon ugyanaz a ticker 95.0 score-rel. Kedd: +$758 (TP1+TP2 chain, +8.96% intraday). Csütörtök: -$253 (LOSS_EXIT, -2.31%). **Mean reversion trap**: a 2 napos net +$505 megérte, de a csütörtöki belépés statisztikailag következetes vesztes setup volt.

**A probléma:**

A pipeline minden napi scoring-ot **újraindulva** számol, nem ismeri a ticker **napi korrelációt** az előző napokkal. Ha POWI tegnap +8.96% volt, a ma-i scoring ugyanakkora értéket ad, mintha a tegnapi rally nem történt volna. A post-rally korrekció (-2 — -3% a következő napon) gyakori mintazás, de az IFDS scoring ezt nem kalkulálja be.

**Két potenciális megoldás:**

### A) Recent Winner Penalty (scoring-alapú)

```python
# Phase 4 után, Phase 6 előtt
def compute_recency_multiplier(ticker, snapshot_history) -> float:
    for days_ago in range(1, 4):  # N=3
        recent_return = get_return(ticker, days_ago)
        if abs(recent_return) >= 0.05:  # ±5%
            return 0.80  # 20% penalty
    return 1.0
```

**Előny:** integrált a scoring-ba, fokozatos hatás (80% még mindig kerülhet portfolio-ba, de ritkábban).  
**Hátrány:** 80% multiplier egy 95 score-ból még mindig ~76 effektív score — nem biztos hogy kiesik.

### B) Position Dedup (hard filter)

```python
# Phase 6 sizing után
def filter_recent_positions(positions, trade_history) -> list:
    """Skip ticker ha az elmúlt 3 nap bármelyikén pozíció volt."""
    return [p for p in positions 
            if p.ticker not in trade_history.get_last_3_days()]
```

**Előny:** egyszerű, biztos — a POWI eset nem ismétlődne.  
**Hátrány:** esetleg túl aggresszív. Előfordulhat, hogy egy ticker 2 napig tényleg többször jó belépés.

### Hibrid opció

Ha az előző nap pozitív move (>+5%) volt, `M_recency × 0.80` (penalty).  
Ha negatív move (<-5%) volt, `M_recency × 1.20` (dip buying bonus).

Momentum + mean reversion kombinatciw. De túl komplex, egyelőre hagyjuk.

**Érték becslés:**
- A POWI-típusú hiba elkerülhető — potenciális ~$200-300 megtakarítás ilyen napokon
- A 4 napos W17-ben 1 eset → **évi 50-60 ilyen nap** várható → **~$10-15k/év potenciál**

**Fontos:** ez nem scoring hiba — a POWI scoring helyesen számolt (a ticker valóban magas flow-val és funda-val bír). A probléma az **időzítés**: túl hamar újravettuk.

**Státusz:** W18 heti metrika után értékelendő. Ha pénteken (ápr 24) még egy hasonló eset jön, vagy ha a W18 során ismétlődő ticker-vásárlási problémák jelennek meg → **B) Position Dedup** első változatként (egyszerű, biztos), később esetleg A) finomhangolás.

**Priority:** P2 — struktúrális javaslat, egyetlen eset alapján még nem kritíkus, de a paradoxon tankonyvi.

**Effort:**
- B) Position Dedup: ~1.5h CC (pozíció history query + filter + tests)
- A) Recent Winner Penalty: ~2h CC (scoring multiplier + historical return lookup + tests)

---

## Kapcsolódó backlog elemek

- BC24 (Institutional Flow Intelligence) — **előfeltétel**, a flow komponens jobb jel nélkül nincs értelme regime-weighted-nek
- BC25 (IFDS Phase 3 ← MID CAS) — **előfeltétel**, a MID API client ott kerül be
- M_target penalty (fent) — **független**, W18-ban eldőlhet külön
- M_contradiction multiplier (finomítva ×0.80-ra 2026-04-23 után, 5/6 = 83% pattern alapján) — **független**, de jobb együtt tenni a regime-aware változtatásokkal, nehogy túl sok változó egyszerre
- **Recent Winner Penalty / Position Dedup** (most rögzítve, POWI paradoxon alapján) — **független**, egyszerű, hamar implementálható
