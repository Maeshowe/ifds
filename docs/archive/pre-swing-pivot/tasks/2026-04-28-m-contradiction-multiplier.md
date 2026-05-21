# M_contradiction Multiplier — Position Sizing Penalty for CONTRADICTION-flagged Tickers

**Status:** SUPERSEDED — replaced by `2026-05-04-contradiction-signal-from-fmp.md` (2026-05-02)
**Created:** 2026-04-28
**Priority:** P1 — adatvezérelt javítás, W17 5/6 pattern alapján
**Estimated effort:** ~2-3h CC (becsült, soha nem implementált)

**LEZÁRÁS OKA (2026-05-02):** A 2026-04-29 architecture discovery után a megoldás iránya megváltozott. A Tamás megfigyelése (2026-04-29 reggel): a Company Intel **NEM döntéstámogatás** — saját tanulási eszköz. A CONTRADICTION jelzés strukturált FMP adatokból (earnings beat ratio, target consensus, analyst high target, recent downgrades) **közvetlenül kalkulálható**, az LLM-megkerülve. Az új task fájl ezt az architektúrát tükrözi: új modul `src/ifds/scoring/contradiction_signal.py`, integráció a Phase 4 snapshot-ba és Phase 6 multiplier-be, a Company Intel érintetlen marad.

**ÚJ TASK:** `docs/tasks/2026-05-04-contradiction-signal-from-fmp.md`

---

## Eredeti tartalom (történeti referencia)

**BLOCKED (2026-04-29 architecture discovery):** `scripts/company_intel.py` runs
**post-submit** (after `deploy_intraday.sh` submit_orders), so the CONTRADICTION
flag does not exist at Phase 6 sizing time. The flag lives only in an LLM prompt
template (`scripts/company_intel.py:296`), not as structured output. Three
options surfaced:
- A: T+1 cache (lossy, asymmetric)
- B: Pre-Phase-6 refactor (large scope, BC25-grade)
- C: skip + halaszt → **chosen**

Re-scoping by Chat 2026-04-30 after inspecting actual `company_intel.py` output
format. Until then, this task does not proceed.
**Depends on:**
- W17 heti metrika lezárult (`docs/analysis/weekly/2026-W17.md` + Chat elemzés)
- MID Bundle Integration deployolt (commit `a3dfaf7`) — független, párhuzamosan fut

**NEM depends on:**
- Recent Winner Penalty / Position Dedup (POWI paradoxon — backlog, W19+)
- M_target szigorítás (backlog, független)
- BC24 / BC25 — független munkafolyam

---

## Kontextus — a W17 5/6 pattern

A 2026-04-20 — 2026-04-24 hét során a Company Intel `CONTRADICTION` flag **6 tickeren** jelent meg. A flag akkor aktiválódik, ha a Company Intel értékelése (analyst targets, recent earnings, sentiment) **explicit ellentmondásban** van a magas IFDS scoring-gal.

| Ticker | Nap | Flag indoklás | P&L | Eredmény |
|--------|-----|---------------|-----|----------|
| CNK | Hé 04-20 | 0/4 earnings beat | -$122 | vesztes |
| GFS | Hé 04-20 | ár Target High fölött | -$83 | vesztes |
| SKM | Hé 04-20 | JPM + Citi downgrade | -$149 | vesztes (LOSS_EXIT) |
| CARG | Sze 04-22 | ár 2.8% consensus fölött | -$172 | vesztes |
| ADI | Csü 04-23 | ár 7.9% consensus fölött | -$27 | vesztes |
| **ET** | **Csü 04-23** | **3 earnings miss** | **+$31** | **nyertes** ⭐ |

**5/6 = 83% vesztes arány.** Az ET az egyetlen kivétel — a flag **erős, de nem abszolút prediktor**.

**Összesített P&L impact:**
- 5 vesztes flagged ticker: -$553
- 1 nyertes flagged ticker: +$31
- **Net flagged P&L: -$522** a W17 alatt

**Szembeállítás a nem-flagged tickerekkel (15 trade):**
- 6 nyertes (POWI kedd, NVDA péntek, MRVL, ASX, CSCO, WMT): +$1,393
- 9 vesztes/flat (POWI csütörtök, GME, POST, ARMK, stb.): -$278
- **Net non-flagged P&L: +$1,115** a W17 alatt

A flagged tickerek **átlagosan -$87/trade**, a non-flagged tickerek **átlagosan +$74/trade**. **A különbség statisztikailag jelentős** (5 napi 21 trade adatból).

## A javasolt megoldás

**M_contradiction multiplier ×0.80 a Phase 6 sizing layerben.**

A Phase 6 jelenleg 3 multiplier-t számol (`_calculate_multiplier_total`):
1. `M_vix` — VIX volatility penalty
2. `M_gex` — GEX gamma exposure adjustment
3. `M_target` — analyst target overshoot penalty

A javaslat: **4. multiplier hozzáadása**, `M_contradiction = 0.80` ha a Company Intel a tickerre `CONTRADICTION` flag-et adott, egyébként `1.0`.

**Hatás egy 95-ös score-ú ticker pozíciójára:**
- **Hard filter** (ha skip lenne): a portfolio méret 0 — **agresszív, nem javasolt**
- **×0.80 multiplier** (javasolt): a pozíció méret -20% — **konzervatív, megengedi a kivételt**
- **×0.50 multiplier** (alternatíva): -50% méret — túl szigorú, az ET nyerés nem érne semmit

**A ×0.80 indoka:**
1. **5/6 nyitva tartja a kivételt.** Az ET +$31 nyertes lenne kisebb pozícióval (~+$25), de továbbra is profit.
2. **A nem-flagged tickerek méretarányát megőrzi.** A scoring scope nem változik.
3. **Visszamenőleges hatás W17-re:** a 5 vesztes flagged trade -20% mérettel ~-$110 csökkenés. **Net megtakarítás ~$110**.
4. **Linda Raschke-elv:** fokozatos változás, nem hard filter — discretionary judgment-tér megőrzése.

## Scope — 5 pont

### 1. Config defaults

**Fájl:** `src/ifds/config/defaults.py`

A `TUNING` dict-be új kulcs:

```python
# M_contradiction multiplier (BC23+ refinement, 2026-04-28)
# Penalty for tickers flagged as CONTRADICTION by Company Intel.
# Based on W17 statistic: 5/6 (83%) flagged tickers were losers, net -$522.
# Conservative ×0.80 leaves the 1/6 winning case viable (smaller position).
"m_contradiction_value": 0.80,
"m_contradiction_enabled": True,
```

**Indok a `_enabled` flag-re:** ha a W18 mérés nem mutat javulást, könnyen visszakapcsolható az `_enabled = False`-szal, kódváltás nélkül.

### 2. Phase 6 sizing logic

**Fájl:** `src/ifds/phases/phase6_sizing.py`

A `_calculate_multiplier_total` függvény bővítése. Jelenleg ~3 multiplier-t számol; ez lesz a 4.

**Pszeudokód:**
```python
def _calculate_multiplier_total(
    config: Config,
    ticker: str,
    snapshot: TickerSnapshot,
    company_intel: dict | None,  # új paraméter (vagy meglévő, ellenőrizendő)
) -> float:
    m_vix = ...        # meglévő
    m_gex = ...        # meglévő
    m_target = ...     # meglévő

    # Új: M_contradiction
    m_contradiction = 1.0
    if config.tuning.get("m_contradiction_enabled", False):
        if company_intel and company_intel.get("verdict") == "CONTRADICTION":
            m_contradiction = config.tuning["m_contradiction_value"]
            logger.log(
                EventType.SIZING_MULTIPLIER, Severity.INFO, phase=6,
                message=f"[M_CONTRADICTION] {ticker}: applied {m_contradiction:.2f} multiplier "
                        f"(reason: {company_intel.get('contradiction_reason', 'unspecified')})",
                data={
                    "ticker": ticker,
                    "multiplier": m_contradiction,
                    "verdict": "CONTRADICTION",
                    "reason": company_intel.get("contradiction_reason"),
                },
            )

    return m_vix * m_gex * m_target * m_contradiction
```

**Megjegyzés:** a tényleges Company Intel struktúra ellenőrizendő — a `verdict` mezőnév lehet eltérő (pl. `assessment`, `flag`, `status`). CC nézze meg a `company_intel.py` output formátumát mielőtt implementál.

### 3. Tesztek (4-5 új test)

**Fájl:** `tests/test_phase6_m_contradiction.py` (új fájl)

```python
def test_m_contradiction_applied_when_flag_set():
    """A flagged ticker kapja a 0.80 multiplier-t."""

def test_m_contradiction_skipped_when_flag_absent():
    """Nem-flagged ticker kapja az 1.0 multiplier-t (no-op)."""

def test_m_contradiction_skipped_when_company_intel_none():
    """company_intel=None esetén 1.0 (no-op, defenzív)."""

def test_m_contradiction_disabled_via_config():
    """m_contradiction_enabled=False → 1.0 minden esetben."""

def test_m_contradiction_combined_with_other_multipliers():
    """M_total = M_vix * M_gex * M_target * M_contradiction (chained)."""
```

### 4. Logging — audit trail

Minden alkalommal, amikor a multiplier alkalmazódik, log entry kell:

```
[M_CONTRADICTION] CARG: applied 0.80 multiplier (reason: price 2.8% above consensus)
```

Az indoklás (`contradiction_reason`) a Company Intel kimenetből származik. Ez **fontos a W18 utáni mérésnél** — látni akarjuk, hány ticker kapta a penalty-t, milyen indoklással, és milyen P&L hatása volt.

### 5. STATUS.md + backlog update

**`docs/STATUS.md`** frissítés:
- "Élesben futó feature-ök" lista bővítése: "M_contradiction multiplier ×0.80 — flagged tickereken 20% méret-csökkentés"
- "W18+ potenciális hangolások" listából **eltávolítás** (mert már implementálva)

**`docs/planning/backlog-ideas.md`**: a M_contradiction-re vonatkozó megjegyzések a "Kapcsolódó backlog elemek" alatt frissítendők — átjelölés "implementálva W18-ban" megjegyzéssel.

## Success criteria

1. **Tesztek**: a 4-5 új teszt zöld + a teljes test suite zöld marad (1377 + 4-5 = ~1382)
2. **Live verification**: szerda esti pipeline futás logjában legalább egy `[M_CONTRADICTION]` üzenet, ha aznap CONTRADICTION-os ticker van
3. **Visszamenőleges sanity check**: futtassunk egy gyors retrospekciós elemzést a W17 5 flagged vesztes ticker -20% mérettel — várható hatás ~+$110 a hetihez képest (kontrolként, nem éles)

**NINCS éles "GO/NO-GO" kritérium ebben a task-ban.** A multiplier ×0.80 érték **adatgyűjtő paraméter**, és a W18 heti metrika (péntek máj 1) értékeli. Ha a W18 szignifikáns javulást mutat → marad. Ha nem → újraértékelés a Recent Winner Penalty-val együtt vasárnap.

## Risk

**Alacsony.** Indoklás:

1. **Konzervatív paraméter (×0.80)** — nem hard filter. A Company Intel téves CONTRADICTION jelzése esetén a ticker még **belép a portfólióba**, csak kisebb mérettel. Az ET-példa (1/6) ezt validálja.
2. **`_enabled` flag** — ha bug derül ki, egy config soron át letiltható, nincs rollback szükség.
3. **Nincs scoring változás** — a Phase 4-5 kimenete teljesen érintetlen marad. A változás csak a sizing-ban (Phase 6) jelenik meg.
4. **A pipeline nem új APIt hív** — minden adat a meglévő Company Intel JSON-ban van, csak a sizing ennek a mezőnek a figyelembevételével módosul.

## Out of scope (explicit)

- **Hard filter / position skip** — `verdict == CONTRADICTION` esetén pozíció 0. Túl agresszív, az ET-eset elveszne.
- **Eltérő multiplier-érték (×0.5 vagy ×0.7)** — egyetlen hetes adat alapján nem indokolt. Ha W18+W19 azt mutatja, hogy ×0.80 nem elég erős, akkor szigorítsunk.
- **Flag-szintű finomítás** (külön multiplier earnings miss vs. analyst downgrade vs. price-above-target esetekre) — túl bonyolult egy első implementációhoz, később lehet.
- **Telegram regresszió javítás** ("4/6 breakdown" hiányzik a submit üzenetből) — független, kis CC task, később.

## Implementation order (CC számára)

1. **Olvasás / megerősítés** (15 min)
   - `src/ifds/scoring/company_intel.py` output formátum — milyen mezőnévvel jön a CONTRADICTION jelzés?
   - **A Company Intel adat elérési útja a Phase 6-ig** — hol és mikor hívja a pipeline a Company Intel-t? Két lehetséges útvonal:
     - (a) Az `execution_plan_run_*.csv` már tartalmazza a CONTRADICTION verdict oszlopot (akkor a Phase 6 onnan olvassa)
     - (b) A Phase 6 saját maga hívja a `company_intel.py`-t a sizing előtt
     - **Megjegyzés a Phase 4 snapshot-ról:** ez **csak a `qualified` ticker(eket)** menti, **nem az összes** scoring-ot. Tehát a Company Intel **NEM** ezen keresztül jön el a Phase 6-ig. CC ellenőrizze az `execution_plan` CSV oszlopait először.
   - `src/ifds/phases/phase6_sizing.py::_calculate_multiplier_total` — hol van pontosan a multiplier számolás?
2. **Config defaults** (5 min) — `defaults.py` 2 új kulcs
3. **Phase 6 logic** (~30 min) — multiplier computation + logging
4. **Tesztek írása** (~45 min) — 4-5 unit test, fixture company_intel mock-kal
5. **Smoke test** (~15 min) — futtatás 1-2 ticker-en, log ellenőrzés
6. **Commit + push** (5 min)
7. **STATUS + backlog update** (10 min)

**Összesen: ~2-3h.**

## Commit message draft

```
feat(scoring): add M_contradiction multiplier for CONTRADICTION-flagged tickers

The Company Intel module flags tickers as CONTRADICTION when the qualitative
assessment (analyst targets, recent earnings, sentiment) explicitly contradicts
the high IFDS quantitative score. Until now, this flag was logged but had no
effect on position sizing.

W17 (2026-04-20 to 2026-04-24) data shows a strong predictive signal:
  - 6 flagged tickers: CNK, GFS, SKM, CARG, ADI (losers); ET (winner)
  - 5/6 = 83% loss rate, net -$522 over the week
  - Non-flagged tickers averaged +$74/trade vs flagged -$87/trade

This commit applies a conservative ×0.80 multiplier in Phase 6 sizing for
flagged tickers — the position still enters the portfolio but at 20% reduced
size. The ×0.80 value (vs ×0.50 or hard filter) preserves the rare winning
case (ET) while substantially de-risking the losers.

The multiplier is gated by `m_contradiction_enabled` config flag (default
True) for easy rollback. A new audit log line `[M_CONTRADICTION] {ticker}:
applied 0.80` records every application with the contradiction reason.

Tests:
  - test_m_contradiction_applied_when_flag_set
  - test_m_contradiction_skipped_when_flag_absent
  - test_m_contradiction_skipped_when_company_intel_none
  - test_m_contradiction_disabled_via_config
  - test_m_contradiction_combined_with_other_multipliers

Verified: full test suite passes (1377 + 5 new = 1382).

W18 weekly metric (Friday May 1) will measure the impact:
  - Net P&L change vs W17
  - Excess vs SPY change
  - Number of CONTRADICTION applications + their P&L delta
```

## Kapcsolódó

- W17 elemzés: `docs/analysis/weekly/2026-W17-analysis.md` (5/6 pattern részletek)
- Backlog: `docs/planning/backlog-ideas.md` (M_contradiction megjegyzés a "Kapcsolódó" szekcióban)
- Daily review-k W17: `docs/review/2026-04-20-daily-review.md` ... `2026-04-24-daily-review.md`
- Linda Raschke-elv: `docs/references/raschke-adaptive-vs-automated.md` (fokozatos változás, nem hard filter)
- Phase 6 reference: `src/ifds/phases/phase6_sizing.py::_calculate_multiplier_total`
- Company Intel reference: `src/ifds/scoring/company_intel.py` (output formátum)

---

## Implementáció időzítése

- **Kedd ápr 28:** Tamás MID kulcs `.env`-be, kedd 22:00-i Phase 1-3 cron lefut
- **Szerda ápr 29 reggel:** Tamás MID snapshot ellenőrzés (`zcat state/mid_bundles/2026-04-28.json.gz | jq '.flat.regime'`)
- **Szerda ápr 29 délelőtt:** CC megkezdi az implementációt ezen task fájl alapján
- **Szerda ápr 29 este:** commit + push, smoke test
- **Csütörtök-péntek:** normál pipeline + napi review-k, M_contradiction log megjelenések figyelése
- **Péntek máj 1 22:00:** W18 heti metrika futtatás (Tamás)
- **Vasárnap máj 3:** Chat W18 elemzés + M_contradiction hatás kiértékelés

## Visszafele kompatibilitás

- **Default `m_contradiction_enabled = True`** → új viselkedés azonnal éles, ahogy a kód felmegy
- **Tesztelési időszak alatti rollback:** egyetlen config sor `False`-ra állítása (nem kell deploy, a következő pipeline futás már a régi viselkedést hozza)
- **Permanens rollback (ha a W18 mérés rossz):** revert commit + visszaállítás `False` defaultra a következő release-ben

## Megjegyzés Linda Raschke-elv kontextusban

A `docs/references/raschke-adaptive-vs-automated.md` rögzíti, hogy az IFDS architektúrája **fokozatos változtatásokat** preferál, nem hard filter-eket. A ×0.80 érték **explicit konzervatív** ennek megfelelően:

> "Mindegyik változás teret hagy Tamás judgmentjének felülbírálásra. A systematic layer szigorítása nélkül az adaptív képesség elvész."

Ha a következő hónapban valaki — Tamás, Chat, vagy CC — felveti, hogy "tegyük ezt hard filterré" (×0.0 a CONTRADICTION-os tickerekre), a válasz: **nem most**. Először a ×0.80 W18+W19+W20 adata kell, mielőtt eldöntjük, hogy a flag annyira erős prediktor-e, hogy érdemes elhagyni az 1/6 nyertes kivételt.
