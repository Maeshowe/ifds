# Task: Swing Scoring — Phase 4 átalakítás (PCR + OTM-inverse, percentile, EWMA(5))

**Status:** DONE
**Priority:** P0 (Fázis 3 deploy)
**Created:** 2026-05-17
**Updated:** 2026-05-18 (Ülés A DEPLOY — Task #1 + #2 egy ülésben)
**Owner:** Claude Code
**Estimated effort:** ~3h CC
**Actual effort:** ~2h (1638 → 1656 tests, EWMA smoke verified)

**Source decision:** [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3.4, §3.5, §3.13 — Döntés [4, 5, 13]: scoring egyszerűsítése, EWMA, multiplier chain átalakítás.

**Depends on:** [`2026-05-17-swing-universe-sp500-r1000.md`](2026-05-17-swing-universe-sp500-r1000.md) — a percentile normalizálás stabil ~1000-es universe-distribúciót igényel.

---

## 1. A változás karaktere

**Drasztikus egyszerűsítés**. A jelenlegi 3-komponensű (flow 0.60 + tech 0.30 + funda 0.10) súlyozott scoring + 7 al-komponensű flow sub-score + 4-5 multiplier-es Phase 6 chain helyett:

$$S_j(t) = 100 \cdot (\text{PCR}_j^{\text{percentile}} - \text{OTM}_j^{\text{percentile}}) + \text{sector\_adj}_j(t)$$

ahol $\text{PCR}_j^{\text{percentile}}, \text{OTM}_j^{\text{percentile}} \in [0, 1]$ az aznapi univerzumból számolt rangsor-percentile, EWMA(5) simítva.

**Threshold**: $S_j > 50$ (Bonferroni-minimum, [`strategic-review-mathematical.md`](../strategic-review/2026-05-08-strategic-review-mathematical.md) §4).

## 2. Komponens-szintű változások

### 2.1. Eltávolítva (a Phase 4-ből)

- Technical sub-score (RSI ideális zóna, SMA50, RS vs SPY) — **NEM** számolódik
- Fundamental sub-score (revenue growth, EPS, profit margin, ROE, D/E) — **NEM** számolódik
- Flow sub-score 5 al-komponensből (RVOL, Dark Pool, Block Trade, Buy Pressure, Squat Bar) — **NEM** számolódik
- Insider activity multiplier — **NEM** alkalmazódik
- Freshness bonus — **NEM** alkalmazódik
- Clipping threshold (>95 crowded) — **NEM** alkalmazódik (a swing horizon-on a "crowded trade" elv másképp értelmezendő, Fázis 4+)

### 2.2. Megtartva (a Phase 4-ben)

- PCR (put-call ratio) percentile-szerű érték
- OTM call ratio percentile-szerű érték (sign-flipped — magas OTM → alacsonyabb score)
- Sector momentum adjustment (BC9 leader +15 / laggard -20 / VETO) — **kapcsolódik** az S_j-hez

### 2.3. Megtartva (de a Phase 6-ba átköltöztetve)

- `M_target` analyst consensus overshoot multiplier — Phase 6-ban marad (Decision 13)

### 2.4. Deaktivált (Phase 6-ban 1.0-ra forcelt)

- `M_VIX` (Day 63 §3.4: VIX-érzékelés a swing horizonon **kevésbé éles**, mert overnight gap kockázat túl gyakori VIX>20 esetén)
- `M_GEX` ✅ már Fázis 1-ben deaktiválva
- `M_contradiction` — **Fázis 2 backtest függvénye** (sign-flip elemzés). Vasárnap **deaktivált** (1.0), de a flag `m_contradiction_enabled: False` config-toggleable, így a backtest után könnyen reaktiválható (esetleg fordított előjellel).

## 3. Percentile normalizálás (D7 elfogadott)

```python
import numpy as np
from scipy import stats

def compute_percentile_score(values: np.ndarray, ticker_value: float) -> float:
    """Adott ticker érték rangsor-percentile a teljes univerzumban.

    Returns: [0, 1] közötti szám, ahol:
      - 0.0 = legalacsonyabb érték az univerzumban
      - 1.0 = legmagasabb érték az univerzumban
    """
    return stats.percentileofscore(values, ticker_value, kind='rank') / 100.0


def score_ticker(ticker_data, universe_data, config):
    """S_j(t) számítása."""
    # Univerzum-szintű distribúciók
    all_pcr = universe_data["pcr_values"]
    all_otm = universe_data["otm_call_ratios"]

    pcr_pct = compute_percentile_score(all_pcr, ticker_data["pcr"])
    otm_pct = compute_percentile_score(all_otm, ticker_data["otm_call_ratio"])

    raw_score = 100.0 * (pcr_pct - otm_pct)
    sector_adj = compute_sector_adjustment(ticker_data["sector"], config)

    return raw_score + sector_adj
```

### 3.1. Cold-start problem (Day 1)

A Day 1-en (2026-05-18) a percentile normalizálás a **current nap univerzumából** számolódik (cross-sectional rank). Ez egy "shift-invariant" megoldás:
- Day 1: PCR percentile = today_universe_rank
- Day 2+: PCR percentile = today_universe_rank (továbbra is cross-sectional)

**Megjegyzés**: a strategic review §4 ajánl rolling 5-day cross-sectional percentile-t a regime-rezisztencia érdekében, de a cross-sectional (single-day) percentile **a Day 1-en is operatív**, és a rolling-5 csak finomítás. **Most a single-day percentile-t használjuk**, és a rolling-5 a Fázis 4+ scope.

## 4. EWMA(5) simítás (D8 elfogadott)

A nyers $S_j(t)$ után EWMA simítás:

$$\bar{S}_j(t) = \alpha \cdot S_j(t) + (1 - \alpha) \cdot \bar{S}_j(t-1)$$

ahol $\alpha = 2/(N+1)$ és $N = 5$, vagyis $\alpha \approx 0.333$.

A `pandas.Series.ewm(span=5).mean()` használható.

### 4.1. EWMA history state

A `state/swing_ewma_state.json` tárolja az utolsó N=5 napi $S_j$ értékeket per ticker:

```json
{
  "AAPL": {"history": [54.2, 56.8, 58.1, 55.0, 57.3], "ewma": 56.3},
  "MSFT": {"history": [...], "ewma": ...},
  ...
}
```

Day 1-en (5/18) az EWMA = raw S_j (nincs history). Day 2-től elkezdődik a smoothing. Day 6+ stabil.

## 5. Sector adjustment (változatlan)

A `sector_adj_j(t)`:
- Leader sector: +15
- Laggard sector: -20
- Veto: $S_j = -\infty$ (kizárás)
- Egyébként: 0

A `phase3_sector_rotation.py` változatlan, az output ugyanaz (`leaders`, `laggards`, `vetos` listák).

## 6. Threshold + qualified candidates

```python
def filter_qualified(scored_tickers, config):
    """A Phase 4 output passed lista."""
    threshold = config["swing_score_threshold"]  # 50 (Bonferroni-minimum)
    return [t for t in scored_tickers if t.ewma_score > threshold and t.sector != "VETO"]
```

A Phase 6-ba érkező lista **rangsorolva** (`ewma_score` descending).

## 7. Új TUNING paraméterek (`defaults.py`)

```python
# Swing Scoring (2026-05-17, Day 63 §3.4, §3.5, §3.13)
"swing_scoring_enabled": True,
"swing_score_threshold": 50.0,          # Bonferroni-minimum
"swing_ewma_span": 5,                    # EWMA simítás (D8)
"swing_ewma_state_file": "state/swing_ewma_state.json",

# Deaktivált (Phase 4)
"flow_subscore_enabled": False,          # RVOL, Dark Pool, Block, Buy Pressure, Squat Bar
"tech_subscore_enabled": False,          # RSI, SMA50, RS vs SPY
"funda_subscore_enabled": False,         # Fundamentals
"freshness_bonus_enabled": False,
"insider_multiplier_enabled": False,
"clipping_enabled": False,               # crowded >95

# Deaktivált multipliers (Phase 6) — m_target marad
"m_vix_enabled": False,
"m_gex_enabled": False,                  # Már Fázis 1-ben False
"m_contradiction_enabled": False,        # Fázis 2 backtest függvénye
```

## 8. Implementáció lépésekben

1. **TUNING paraméterek** (10 min) — `defaults.py` új field-ek + meglévő deaktivált flag-ek
2. **`SwingUniverseDistribution` helper** (30 min) — daily PCR + OTM distribúció gyűjtés a Phase 4 elején
3. **`compute_percentile_score`** (15 min) — egyszerű scipy wrapper
4. **`score_ticker` átalakítás** (45 min) — a `phase4_stocks.py` `analyze_stock()` átírása az S_j képletre
5. **EWMA state management** (45 min) — load/write `swing_ewma_state.json`, per-ticker history
6. **Threshold + filter** (15 min) — a Phase 4 output `passed` list
7. **Tesztek** (45 min) — 12-15 unit teszt
8. **Smoke test** (15 min) — 1 mock napi futás
9. **Commit** (5 min)

**Összesen: ~3h.**

## 9. Tesztek (12-15)

```python
def test_compute_percentile_score_basic():
    """0.5 középérték → 0.5 percentile."""

def test_score_ticker_pcr_only_no_otm():
    """High PCR + low OTM → S_j magas."""

def test_score_ticker_high_otm_penalty():
    """High OTM → S_j alacsony (sign-flip)."""

def test_sector_adjustment_leader_bonus():
    """Leader sector +15 az S_j-hez."""

def test_sector_adjustment_veto_excluded():
    """Veto sector → kizárás."""

def test_ewma_state_persistence():
    """Day 2 EWMA = α × raw + (1-α) × Day 1."""

def test_ewma_state_empty_first_day():
    """Day 1 EWMA = raw (nincs history)."""

def test_swing_score_threshold_filter():
    """S_j > 50 csak."""

def test_universe_percentile_distribution_stable():
    """1000-es univerzumon a percentile distribúció stabil (KS test)."""

def test_phase4_integration_outputs_passed_list():
    """Phase 4 run output schema kompatibilis a Phase 6 input-tal."""

def test_subscores_disabled_when_swing_enabled():
    """A flow/tech/funda sub-score NEM számolódik ha swing_scoring_enabled=True."""

def test_freshness_bonus_disabled():
    """Freshness bonus 0 hatású."""

def test_crowded_threshold_disabled():
    """A 95-os crowded threshold NEM kizár."""

def test_m_contradiction_disabled_in_phase6_input():
    """A Phase 4 output NEM jelzi az M_c-ot ha disabled."""
```

## 10. Commit message

```
feat(scoring): swing Phase 4 simplification — PCR + OTM-inverse, percentile, EWMA(5)

Day 63 outcome §3.13: scoring radically simplified for swing horizon.
Only the Bonferroni-significant features survive (PCR positive,
OTM negative), normalized by cross-sectional percentile rank,
smoothed by EWMA(5).

S_j(t) = 100 × (PCR_percentile - OTM_percentile) + sector_adj(t)
        with EWMA(5) smoothing per ticker

- Phase 4 sub-scores disabled: flow (5 components), tech, funda
- Phase 4 modifiers disabled: freshness bonus, insider mult, clipping
- Phase 6 multipliers disabled: M_VIX, M_GEX (already), M_contradiction
- Phase 6 multiplier kept: M_target (analyst consensus overshoot)

Threshold: S_j > 50 (Bonferroni-minimum)
EWMA state: state/swing_ewma_state.json, per-ticker history N=5

Tests: 13 unit + 2 integration.

Refs: docs/decisions/2026-05-14-day63-decision-outcome.md §3.4, §3.5, §3.13
      docs/strategic-review/2026-05-08-strategic-review-mathematical.md §4
```

## 11. Kapcsolódó

- [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3.4, §3.5, §3.13
- [`docs/strategic-review/2026-05-08-strategic-review-mathematical.md`](../strategic-review/2026-05-08-strategic-review-mathematical.md) §4 (Bonferroni-minimum + EWMA javaslat)
- [`docs/design/swing-pivot-architecture.md`](../design/swing-pivot-architecture.md) §3, §8.1, §8.2
- [`docs/tasks/2026-05-17-swing-universe-sp500-r1000.md`](2026-05-17-swing-universe-sp500-r1000.md) (függőség)
- [`docs/tasks/2026-05-17-swing-sizing-phase6.md`](2026-05-17-swing-sizing-phase6.md) (downstream)
