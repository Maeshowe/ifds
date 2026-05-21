# Contradiction Signal — Strukturált FMP-alapú multiplier (M_contradiction)

**Status:** DONE
**Updated:** 2026-05-02
**Created:** 2026-05-02 (vasárnap, Tamás utazás előtt előkészítve)
**Priority:** **P1** — adatvezérelt javítás, W17 5/6 + W18 DTE -$988 alapján
**Estimated effort:** ~4-4.5h CC (egyetlen fejlesztési kör)
**Replaces:** `2026-04-28-m-contradiction-multiplier.md` (SUPERSEDED)

**Depends on:**
- nincs

**NEM depends on:**
- MID Bundle Integration (élesben fut, független)
- Breakeven Lock (élesben fut, független)
- Company Intel script (érintetlen marad — saját tanulási eszköz)

---

## Kontextus — két konkrét eset igazolja a feature szükségességét

### W17 (2026-04-20 — 2026-04-24): 5/6 = 83% pattern

A Company Intel `CONTRADICTION` flag **6 tickeren** jelent meg a héten. Az 5 vesztes, 1 nyertes:

| Ticker | Nap | Flag indoklás | P&L |
|--------|-----|---------------|-----|
| CNK | Hé 04-20 | 0/4 earnings beat | -$122 |
| GFS | Hé 04-20 | ár Target High fölött | -$83 |
| SKM | Hé 04-20 | JPM + Citi downgrade | -$149 |
| CARG | Sze 04-22 | ár 2.8% consensus fölött | -$172 |
| ADI | Csü 04-23 | ár 7.9% consensus fölött | -$27 |
| **ET** | **Csü 04-23** | **3 earnings miss** | **+$31** ⭐ kivétel |

Net flagged P&L: **-$522** vs net non-flagged: **+$1,115** (~$74/trade vs -$87/trade különbség).

### W18 péntek (2026-05-01): DTE -$988 egyetlen ticker

A DTE Energy **kedden (ápr 28) Q1 earnings miss-t jelentett be** (-7.1% vs estimate, Zacks szerint). Az IFDS scoring **3 nappal később** (ápr 30 csütörtök) **92.0 score-t** adott rá. Másnap a DTE pozíció 4-split LOSS_EXIT/SL kombinációval **-$988** veszteséggel zárt.

**Hipotetikus számítás:**
- M_contradiction nélkül: 260 share × -$3.80/share = -$988
- M_contradiction ×0.80: 208 share × -$3.80/share = -$790 (~$200 megtakarítás)

**A scoring nem fogta meg** a recent earnings miss kontextust. Pontosan ezt orvosolja a feature.

---

## Architektúra — strukturált FMP, nem LLM

### A 2026-04-29 architektúrális felismerés

A **régi BLOCKED task** (`2026-04-28-m-contradiction-multiplier.md`) a `scripts/company_intel.py` LLM-output parsolásán alapult. **Ez nem működik**, mert:

1. A `company_intel.py` **a Phase 6 UTÁN** fut (deploy_intraday.sh sorrendben submit_orders előtt vagy után)
2. A CONTRADICTION flag **csak az LLM prompt sablonban** él (`scripts/company_intel.py:296`), nem strukturált kimenet
3. A Company Intel **funkciója nem döntéstámogatás** — Tamás saját tanulási eszköze, érintetlen kell hogy maradjon

### Az új megoldás: közvetlen FMP-számítás

A `scripts/company_intel.py` 6 különböző FMP endpoint-ot hív (vonalak 51-200):
- `/stable/profile` — vállalati alapadatok
- `/stable/price-target-consensus` — analyst consensus target (low/avg/high)
- `/stable/earnings` — utolsó 4 quarter EPS actual vs estimate
- `/stable/grades-consensus` — buy/hold/sell konszenzus
- `/stable/grades` — utolsó 5 analyst grade change (upgrade/downgrade)
- `/stable/news/stock` — utolsó 5 hírcím

**Mind az 5 jelzés**, ami a CONTRADICTION flag-hez vezet az LLM-ben, **strukturált FMP adatokból közvetlenül kalkulálható** — az LLM-megkerülve, determinisztikusan, gyorsan.

### Az új modul felépítése

```
                                                                     
[Phase 4] → contradiction_signal.compute() → snapshot mező + CSV oszlop
                                                ↓
                                          [Phase 6 sizing]
                                                ↓
                                     M_contradiction = 0.80 (ha flag)
                                                ↓
                                          execution_plan.csv
                                                ↓
                                      submit_orders.py → IBKR
```

**A feature 4 réteg:**
1. **`contradiction_signal.py`** — pure function, FMP adatból kalkulál
2. **Phase 4 integráció** — snapshot bővítés
3. **Execution plan CSV bővítés** — új `contradiction_flag` oszlop
4. **Phase 6 multiplier** — ×0.80 alkalmazás CSV alapján

---

## CC részletes feladata — 7 lépés

### 1. Új modul: `src/ifds/scoring/contradiction_signal.py`

**Pure function, ami strukturált FMP adatokból kalkulál CONTRADICTION flag-et.**

```python
"""Contradiction Signal — structured FMP-based outlier protection.

Computes a CONTRADICTION flag from structured FMP fundamentals data.
Pure function, deterministic, ~50-100ms cache lookup, no LLM call.

Used by Phase 4 (or 5) to enrich snapshots, then by Phase 6 sizing
as M_contradiction multiplier (0.80 for flagged tickers).
"""

from __future__ import annotations
from typing import TypedDict, Literal


class ContradictionResult(TypedDict):
    """Result of contradiction signal evaluation."""
    is_contradicted: bool
    reasons: list[str]
    detail: dict[str, object]


# Configuration constants
CONSENSUS_OVERSHOOT_THRESHOLD = 0.02  # 2% above consensus target
EARNINGS_BEAT_RATIO_THRESHOLD = 0.5   # < 50% beats (i.e. 0/4 or 1/4)
RECENT_DOWNGRADES_THRESHOLD = 2        # 2+ downgrades in last 30 days
RECENT_DOWNGRADES_WINDOW_DAYS = 30


def compute_contradiction_signal(
    *,
    price: float,
    target_consensus: float | None = None,
    target_high: float | None = None,
    earnings_history: list[dict] | None = None,
    analyst_grades_recent: list[dict] | None = None,
) -> ContradictionResult:
    """Evaluate four CONTRADICTION conditions on structured FMP data.
    
    Conditions:
        1. Earnings beats < 50% in last 4 quarters
        2. Price > consensus target by 2%+
        3. Price > analyst HIGH target
        4. 2+ recent analyst downgrades (last 30 days)
    
    Args:
        price: Current ticker price (from execution plan)
        target_consensus: FMP price-target-consensus.targetConsensus
        target_high: FMP price-target-consensus.targetHigh
        earnings_history: FMP earnings (last 4Q), each item:
            {"date": str, "epsActual": float, "epsEstimated": float}
        analyst_grades_recent: FMP grades (last 5), each item:
            {"date": str, "action": str, "newGrade": str, "previousGrade": str}
    
    Returns:
        ContradictionResult with is_contradicted, reasons list, and detail dict.
        
    Defensive: missing data => no flag (returns False, []).
    """
    flags: list[str] = []
    detail: dict[str, object] = {
        "thresholds": {
            "consensus_overshoot": CONSENSUS_OVERSHOOT_THRESHOLD,
            "earnings_beat_ratio": EARNINGS_BEAT_RATIO_THRESHOLD,
            "recent_downgrades": RECENT_DOWNGRADES_THRESHOLD,
        }
    }
    
    # Jelzés 1: Earnings beat ratio
    if earnings_history:
        beats = sum(
            1 for e in earnings_history
            if isinstance(e.get("epsActual"), (int, float))
            and isinstance(e.get("epsEstimated"), (int, float))
            and e["epsActual"] >= e["epsEstimated"]
        )
        n = len(earnings_history)
        if n > 0 and (beats / n) < EARNINGS_BEAT_RATIO_THRESHOLD:
            flags.append(f"earnings_beats_below_half ({beats}/{n})")
            detail["earnings_beats"] = f"{beats}/{n}"
    
    # Jelzés 2: Price vs consensus target overshoot
    if target_consensus and target_consensus > 0:
        overshoot = (price - target_consensus) / target_consensus
        detail["consensus_overshoot_pct"] = round(overshoot * 100, 2)
        if overshoot > CONSENSUS_OVERSHOOT_THRESHOLD:
            flags.append(
                f"price_above_consensus_{round(overshoot * 100, 1)}pct"
            )
    
    # Jelzés 3: Price vs analyst HIGH target
    if target_high and price > target_high:
        flags.append("price_above_analyst_high")
        detail["target_high"] = target_high
    
    # Jelzés 4: Recent downgrades
    if analyst_grades_recent:
        from datetime import date, datetime, timedelta
        cutoff = (date.today() - timedelta(days=RECENT_DOWNGRADES_WINDOW_DAYS))
        downgrade_count = 0
        for g in analyst_grades_recent:
            if g.get("action", "").lower() not in ("downgraded", "downgrade", "down"):
                continue
            grade_date_str = g.get("date", "")
            try:
                grade_date = datetime.strptime(grade_date_str[:10], "%Y-%m-%d").date()
                if grade_date >= cutoff:
                    downgrade_count += 1
            except (ValueError, TypeError):
                continue
        detail["recent_downgrades_30d"] = downgrade_count
        if downgrade_count >= RECENT_DOWNGRADES_THRESHOLD:
            flags.append(f"recent_downgrades_{downgrade_count}")
    
    return ContradictionResult(
        is_contradicted=len(flags) > 0,
        reasons=flags,
        detail=detail,
    )
```

### 2. FMP adatforrások beazonosítása

A `scripts/company_intel.py` már implementálja ugyanezeket az API hívásokat (lásd 51-200 sorok). **CC vagy újrahasznosítja a meglévő `_fmp_get` függvényt egy közös util modulba** (pl. `src/ifds/data/fmp_fundamentals.py`), **vagy** a Phase 4 már meglévő FMP cache-éből olvas (preferált, ha van).

**Megjegyzés CC-nek:** ellenőrizd, hogy a Phase 4 már lekéri-e ezeket az adatokat. Ha igen, a `compute_contradiction_signal()` **közvetlenül** azokból dolgozik, **nincs új API hívás**. Ha nem, akkor új cache-elt FMP fetcher kell, ami **batch módban** fut Phase 4 kezdetén az összes ticker-re.

**Latency cél:** ≤100ms per ticker. Ha új API hívás szükséges, **kötelezően cache-elendő** napi szinten (`state/contradiction_cache/YYYY-MM-DD/{TICKER}.json`).

### 3. Phase 4 snapshot bővítés

A Phase 4 ticker analízis után, a snapshot-ba bekerül:

```python
# src/ifds/phases/phase4_stocks.py (vagy ahol a snapshot elkészül)
contradiction = compute_contradiction_signal(
    price=ticker_data.price,
    target_consensus=fmp_data.target_consensus,
    target_high=fmp_data.target_high,
    earnings_history=fmp_data.earnings_4q,
    analyst_grades_recent=fmp_data.grades_5,
)

snapshot["contradiction_flag"] = contradiction["is_contradicted"]
snapshot["contradiction_reasons"] = contradiction["reasons"]
snapshot["contradiction_detail"] = contradiction["detail"]
```

A `state/phase4_snapshots/YYYY-MM-DD.json.gz`-ben így új mezők keletkeznek:
```json
{
  "ticker": "DTE",
  "score": 92.0,
  "contradiction_flag": true,
  "contradiction_reasons": ["earnings_beats_below_half (1/4)"],
  "contradiction_detail": {
    "earnings_beats": "1/4",
    "consensus_overshoot_pct": -0.5,
    "recent_downgrades_30d": 0,
    "thresholds": {...}
  }
}
```

### 4. Execution plan CSV bővítés

A Phase 6 (vagy ami az `execution_plan_run_*.csv`-t generálja) hozzáadja:

```csv
instrument_id,score,...,contradiction_flag,contradiction_reasons
DTE,92.0,...,1,earnings_beats_below_half (1/4)
NIO,85.5,...,0,
```

**Két új oszlop:**
- `contradiction_flag` — 0/1 integer
- `contradiction_reasons` — komma-elválasztott string (esetleg üres)

### 5. Phase 6 multiplier alkalmazás

A `Phase 6 sizing._calculate_multiplier_total()` (vagy ahol a multiplier chain összeáll) bővítendő:

```python
def _calculate_multiplier_total(
    config: Config,
    ticker: str,
    snapshot: TickerSnapshot,  # vagy ahol a contradiction_flag elérhető
) -> float:
    m_vix = ...        # meglévő
    m_gex = ...        # meglévő
    m_target = ...     # meglévő

    # ÚJ: M_contradiction
    m_contradiction = 1.0
    if config.tuning.get("m_contradiction_enabled", True):
        if getattr(snapshot, "contradiction_flag", False):
            m_contradiction = config.tuning["m_contradiction_value"]
            logger.log(
                EventType.SIZING_MULTIPLIER, Severity.INFO, phase=6,
                message=(
                    f"[M_CONTRADICTION] {ticker}: applied "
                    f"{m_contradiction:.2f} multiplier (reasons: "
                    f"{', '.join(snapshot.contradiction_reasons)})"
                ),
                data={
                    "ticker": ticker,
                    "multiplier": m_contradiction,
                    "reasons": snapshot.contradiction_reasons,
                },
            )

    return m_vix * m_gex * m_target * m_contradiction
```

**Config defaults** (`src/ifds/config/defaults.py`):
```python
TUNING = {
    ...
    # M_contradiction multiplier — outlier protection from FMP fundamentals
    # Verified W17 5/6 pattern + W18 DTE -$988 case (2026-05-02 task)
    "m_contradiction_enabled": True,
    "m_contradiction_value": 0.80,
}
```

**FONTOS:** csak akkor alkalmazódik a multiplier, ha **a Phase 6 olvassa a CSV/snapshot adatából**, NEM hív új API-t. Ez a kritikus path determinisztikussá és gyorssá teszi a sizing-ot.

### 6. Tesztek (8-10 új unit test)

**Fájl 1: `tests/test_contradiction_signal.py`** (új)

```python
def test_no_contradiction_with_clean_data():
    """Clean ticker (price under target, all beats, no downgrades) → no flag."""
    result = compute_contradiction_signal(
        price=100.0,
        target_consensus=110.0,
        target_high=120.0,
        earnings_history=[
            {"date": "2026-01-01", "epsActual": 1.0, "epsEstimated": 0.9},
            {"date": "2025-10-01", "epsActual": 0.95, "epsEstimated": 0.9},
            {"date": "2025-07-01", "epsActual": 1.1, "epsEstimated": 1.0},
            {"date": "2025-04-01", "epsActual": 0.85, "epsEstimated": 0.8},
        ],
        analyst_grades_recent=[],
    )
    assert result["is_contradicted"] is False
    assert result["reasons"] == []


def test_earnings_beats_below_half_triggers():
    """1/4 beats → flag (DTE-style case)."""
    result = compute_contradiction_signal(
        price=100.0,
        target_consensus=110.0,
        target_high=120.0,
        earnings_history=[
            {"date": "2026-01-01", "epsActual": 0.7, "epsEstimated": 0.9},
            {"date": "2025-10-01", "epsActual": 0.7, "epsEstimated": 0.9},
            {"date": "2025-07-01", "epsActual": 0.7, "epsEstimated": 0.9},
            {"date": "2025-04-01", "epsActual": 1.0, "epsEstimated": 0.9},
        ],
        analyst_grades_recent=[],
    )
    assert result["is_contradicted"] is True
    assert any("earnings_beats_below_half" in r for r in result["reasons"])


def test_price_above_consensus_2pct_triggers():
    """Price 2.5% above consensus → flag (CARG W17 case)."""
    result = compute_contradiction_signal(
        price=102.5,
        target_consensus=100.0,
        target_high=120.0,
    )
    assert result["is_contradicted"] is True
    assert any("price_above_consensus" in r for r in result["reasons"])


def test_price_above_analyst_high_triggers():
    """Price above analyst HIGH target → flag (GFS W17 case)."""
    result = compute_contradiction_signal(
        price=125.0,
        target_consensus=100.0,
        target_high=120.0,
    )
    assert result["is_contradicted"] is True
    assert "price_above_analyst_high" in result["reasons"]


def test_two_recent_downgrades_triggers():
    """2 downgrades in last 30 days → flag (SKM W17 case)."""
    from datetime import date, timedelta
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    last_week = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    result = compute_contradiction_signal(
        price=100.0,
        target_consensus=110.0,
        analyst_grades_recent=[
            {"date": yesterday, "action": "downgraded", "newGrade": "Hold", "previousGrade": "Buy"},
            {"date": last_week, "action": "downgraded", "newGrade": "Sell", "previousGrade": "Hold"},
        ],
    )
    assert result["is_contradicted"] is True
    assert any("recent_downgrades" in r for r in result["reasons"])


def test_old_downgrades_dont_trigger():
    """Downgrades > 30 days old → not counted."""
    from datetime import date, timedelta
    old_date = (date.today() - timedelta(days=60)).strftime("%Y-%m-%d")
    result = compute_contradiction_signal(
        price=100.0,
        target_consensus=110.0,
        analyst_grades_recent=[
            {"date": old_date, "action": "downgraded", "newGrade": "Hold", "previousGrade": "Buy"},
            {"date": old_date, "action": "downgraded", "newGrade": "Sell", "previousGrade": "Hold"},
        ],
    )
    assert result["is_contradicted"] is False


def test_multiple_flags_combine():
    """Multiple conditions → all reasons reported."""
    result = compute_contradiction_signal(
        price=125.0,
        target_consensus=100.0,
        target_high=120.0,
        earnings_history=[
            {"date": "2026-01-01", "epsActual": 0.7, "epsEstimated": 0.9},
        ],
    )
    assert result["is_contradicted"] is True
    assert len(result["reasons"]) >= 2  # Both consensus + high + earnings


def test_missing_data_returns_no_contradiction():
    """Missing FMP data → no flag (defensive default)."""
    result = compute_contradiction_signal(price=100.0)
    assert result["is_contradicted"] is False
    assert result["reasons"] == []
```

**Fájl 2: `tests/test_phase6_m_contradiction.py`** (új)

```python
def test_m_contradiction_applied_when_flagged():
    """A flagged ticker kapja a 0.80 multiplier-t."""
    
def test_m_contradiction_skipped_when_not_flagged():
    """Nem-flagged ticker → 1.0 multiplier (no-op)."""
    
def test_m_contradiction_disabled_via_config():
    """m_contradiction_enabled=False → mindig 1.0."""
    
def test_m_contradiction_combined_with_other_multipliers():
    """M_total = M_vix * M_gex * M_target * M_contradiction (chain)."""
```

### 7. Smoke test 3 historikus tickeren

Kézi futtatás a `state/phase4_snapshots/` fájlokon:

| Ticker | Dátum | Várt eredmény | Indok |
|--------|-------|---------------|-------|
| DTE | 2026-05-01 | `is_contradicted=True` | Q1 earnings miss (kedd ápr 28) |
| POST | 2026-04-27 | ellenőrzendő | -$299 (W18 hétfő) |
| CARG | 2026-04-22 | `is_contradicted=True` | W17 ár 2.8% consensus fölött |
| ET | 2026-04-23 | `is_contradicted=True` | W17 nyertes 1/6 — flag VAN, de a pozíció így is nyert |

**A smoke teszt manuális** — CC futtatja egy script-tel, ami az adott napi FMP adatokat lekéri (vagy cache-ből olvassa), és kimenetet logol. **NEM része a CI test suite-nak**, csak human verifikáció.

---

## Out of scope (explicit)

- **Hard filter / position skip** — ×0.0 a flagged tickerekre. Túl agresszív, az ET-eset elveszne.
- **Eltérő multiplier-érték** (×0.5, ×0.7) — `m_contradiction_value` config-rögzített, későbbi tuning lehet.
- **Külön multiplier eltérő flag-ekre** (earnings miss vs analyst downgrade vs price-overshoot) — túl bonyolult első implementációhoz.
- **Backtest a teljes BC23 időszakon** — külön script lehet, jelenleg csak smoke test.
- **MID Bundle data integráció** — a CONTRADICTION jel **csak FMP-ből** származik, **nem** a MID-ből. A két feature független.
- **Company Intel script módosítása** — érintetlen marad, Tamás saját tanulási eszköze.

---

## Success criteria

1. **`contradiction_signal.py` modul** létezik, 8 unit teszt zöld
2. **Phase 4 snapshot** tartalmazza a `contradiction_flag` mezőt
3. **execution_plan_run_*.csv** új oszlopa szerepel
4. **Phase 6 multiplier** alkalmazódik, audit log entry minden alkalmazáskor
5. **Tesztek:** összesen ~12 új teszt (8 signal + 4 phase 6), test suite 1535 → ~1547 passing
6. **Smoke test:** DTE 2026-05-01 → `is_contradicted=True` minimum (mert Q1 earnings miss)
7. **Live verification:** hétfő máj 5 cron-ban legalább egy `[M_CONTRADICTION]` audit log entry, ha aznap CONTRADICTION-flagged ticker van

---

## Risk

**Alacsony.** Indoklás:

1. **Konzervatív paraméter (×0.80)** — nem hard filter
2. **`_enabled` flag** — egyetlen config sor `False`-ra állítása letiltja
3. **Defenzív default** — hiányzó FMP adat esetén `is_contradicted=False`, nincs hamis pozitív
4. **Determinisztikus** — nincs LLM, nincs latency variance
5. **Független** a Breakeven Lock-tól és a MID-tól, párhuzamosan fut
6. **Backtesztelhető** — a W17 + W18 historikus FMP adat alapján visszaszámolható a hatás

**Egy kockázat:** a scoring validation tegnapi finding-ja szerint a **funda komponens nem prediktív** (Pearson -0.088, p=0.180). A M_contradiction lényegében **funda-szerű multiplier** (earnings + analyst targets + downgrades). **Lehetséges, hogy átlagosan nem ad alpha-t.**

**Ellenérv:** a feature **NEM átlagos** funda jel, hanem **outlier protection** — extrém ellentmondások esetén csökkenti a kockázatot. A DTE -$988 és a W17 -$522 net konkrét megtakarítási potenciált jelez ×0.80 multiplier mellett (~$140-200 / hét). Ez **outlier-szintű hatás**, nem regular alpha. A Day 63 mérésben **független adatpont** lesz.

---

## Implementation order (CC számára) — ~4-4.5h egy fejlesztési kör

| Lépés | Tartalom | Idő |
|-------|----------|-----|
| 1 | Olvasás: `scripts/company_intel.py`, `src/ifds/phases/phase4_stocks.py`, `src/ifds/phases/phase6_sizing.py` | 20 min |
| 2 | `src/ifds/scoring/contradiction_signal.py` modul + 8 unit teszt | 1.5h |
| 3 | FMP adatforrás integráció (cache vagy új batch fetcher) | 30-45 min |
| 4 | Phase 4 snapshot bővítés (3 új mező) | 20 min |
| 5 | Execution plan CSV oszlop | 15 min |
| 6 | Phase 6 multiplier integráció + 4 új teszt | 30 min |
| 7 | Smoke test 3 historikus tickeren (DTE, POST, CARG) | 20 min |
| 8 | Commit + push, STATUS.md + backlog update | 15 min |
| **Összesen** | | **~4-4.5h** |

---

## Commit message draft

```
feat(scoring): add CONTRADICTION signal from structured FMP data + M_contradiction multiplier

Adds src/ifds/scoring/contradiction_signal.py — a pure function that computes
a CONTRADICTION flag from structured FMP fundamentals (earnings beat ratio,
analyst consensus target, analyst high target, recent downgrades). The flag
flows through Phase 4 snapshot → execution_plan CSV → Phase 6 sizing as
M_contradiction multiplier (×0.80 for flagged tickers).

This replaces the BLOCKED 2026-04-28-m-contradiction-multiplier task, which
attempted to parse the LLM-based Company Intel output post-submit (architecture
mismatch). The new approach computes the same CONTRADICTION conditions
DIRECTLY from FMP structured data, before Phase 6 sizing — deterministic,
fast (~50-100ms), no LLM call, and the Company Intel script remains
untouched (it's Tamás's learning tool, not a decision-support system).

Conditions evaluated (any one triggers flag):
  1. Earnings beats < 50% in last 4 quarters
  2. Price > consensus target by 2%+
  3. Price > analyst HIGH target
  4. 2+ recent analyst downgrades (last 30 days)

Motivation:
  - W17 (Apr 20-24): 5/6 = 83% of CONTRADICTION-flagged tickers were losers
    (CNK, GFS, SKM, CARG, ADI), net -$522. Only ET (1/6) was a winner.
  - W18 Friday (May 1): DTE -$988 single-ticker loss after Q1 earnings miss
    announcement (Tuesday Apr 28). IFDS scored DTE 92.0 despite the miss.
    With M_contradiction × 0.80, position would have been -$790 (~$200 saved).

The multiplier is gated by m_contradiction_enabled config flag (default True)
for easy rollback. A new audit log line `[M_CONTRADICTION] {ticker}: applied
0.80 (reasons: ...)` records every application.

Tests:
  contradiction_signal:
    - test_no_contradiction_with_clean_data
    - test_earnings_beats_below_half_triggers
    - test_price_above_consensus_2pct_triggers
    - test_price_above_analyst_high_triggers
    - test_two_recent_downgrades_triggers
    - test_old_downgrades_dont_trigger
    - test_multiple_flags_combine
    - test_missing_data_returns_no_contradiction
  phase 6:
    - test_m_contradiction_applied_when_flagged
    - test_m_contradiction_skipped_when_not_flagged
    - test_m_contradiction_disabled_via_config
    - test_m_contradiction_combined_with_other_multipliers

Smoke test verified manually:
  - DTE 2026-05-01 → is_contradicted=True (1/4 earnings beats)
  - CARG 2026-04-22 → is_contradicted=True (price 2.8% above consensus)
  - POST 2026-04-27 → is_contradicted=<TBD by snapshot>

Test suite: 1535 → 1547 passing.

Replaces: docs/tasks/2026-04-28-m-contradiction-multiplier.md (SUPERSEDED)
```

---

## Megjegyzés a Linda Raschke-elv kontextusban

A `docs/references/raschke-adaptive-vs-automated.md` rögzíti: **a systematic szabály akkor érvényes, ha a piaci környezet támogatja**. A 2026 áprilisi Stagflation regime-ben a magas IFDS score-ú tickerek **gyakran ellentmondtak** a recent earnings/target adatoknak (W17 5/6 + W18 DTE).

**Az ember (Tamás) észrevette ezt** — a 5/6 pattern a W17 napi review-k során, a DTE eset a W18 péntek adatból. **A systematic réteg most kódba önti a felismerést**: ha extrém ellentmondás van a kvantitatív score és a kvalitatív fundamentumok között, a pozíció méretét csökkentjük.

**Ez nem a scoring szigorítása**, hanem **outlier protection** — a Day 63 mérés szempontjából **független adatpont**.

---

## Kapcsolódó

- W17 5/6 pattern részletek: `docs/analysis/weekly/2026-W17-analysis.md`
- W18 péntek DTE eset: `docs/review/2026-05-01-daily-review.md`
- Tamás architektúrális felismerés: 2026-04-29 reggeli chat (Company Intel funkció-eltolás veszélye)
- Régi BLOCKED task (történeti referencia): `docs/tasks/2026-04-28-m-contradiction-multiplier.md`
- Linda Raschke filozófia: `docs/references/raschke-adaptive-vs-automated.md`
- Forrás kód: `scripts/company_intel.py` (vonalak 51-200, FMP endpoint-ok)
- Phase 6 reference: `src/ifds/phases/phase6_sizing.py::_calculate_multiplier_total`
- Scoring validation: `docs/analysis/scoring-validation.md` (funda komponens átlagosan nem prediktív, de outlier protection más kategória)

---

## Implementáció időzítése

- **Most (2026-05-02 szombat):** Tamás előkészíti CC-nek
- **Vasárnap-hétfő (Tamás utazás közben):** CC független fejlesztési körben implementálja
- **Hétfő reggel commit + push:** Tamás `git pull` a Mac Mini-n
- **Hétfő 16:15 CEST cron:** **első éles nap** a M_contradiction-nel
- **Csütörtök máj 8:** **első weekly mérés** a feature hatásáról (W19 péntek `weekly_metrics.py`)
- **Day 63 (~máj 14):** a M_contradiction 8 napi adata bekerül a Day 63 értékelésbe

---

*Task előkészítve: 2026-05-02 szombat délelőtt, Chat (Tamás utazás előtt)*
