# Task: Swing Sizing — Phase 6 átalakítás (0.35% risk, 12 cap, 30% sector notional, sector-balanced greedy)

**Status:** OPEN
**Priority:** P0 (Fázis 3 deploy)
**Created:** 2026-05-17
**Owner:** Claude Code
**Estimated effort:** ~2h CC

**Source decision:** [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3.7, §3.11 — Döntés [7, 11]: sizing + sector cap átalakítás.

**Depends on:** [`2026-05-17-swing-scoring-phase4.md`](2026-05-17-swing-scoring-phase4.md) — az új S_j scoring output kell

---

## 1. A változás

| Paraméter | Régi | Új |
|---|---|---|
| Risk per trade | 0.7% ($700) | **0.35% ($350)** |
| Max concurrent positions | 5 (BMI guard 4-3-2) | **12** |
| Daily new entries | 5 (kötelező) | **2-3 (csak ha érdemes)** |
| Sector cap | 2 ticker/sector | **30% notional/sector** |
| Stop multiplier (sizing képletbe) | 1.5×ATR | **2.0×ATR** |
| Active multipliers | M_VIX × M_GEX × M_target × M_contradiction | **csak M_target** |

## 2. Sizing képlet

$$\text{notional}_j = \frac{\text{equity} \cdot 0.0035}{\text{ATR}_{\text{pct},j} \cdot 2.0} \cdot \text{entry\_price}_j \cdot M_{\text{target},j}$$

ahol $\text{ATR}_{\text{pct},j} = \text{ATR}_j / \text{entry\_price}_j$.

A `M_target` változatlanul a meglévő `target_overshoot_penalty` / `target_severe_penalty` szabályok szerint (0.85× ha 20-50% target felett, 0.60× ha >50% felett).

A többi multiplier (`M_VIX`, `M_GEX`, `M_contradiction`) **1.0-ra forcelt** a Task #2 (swing scoring) szerinti config flag-ekkel.

## 3. Daily entry workflow

```python
def select_daily_entries(scored_candidates, open_positions, config):
    """A Phase 6 entry-selection logika.

    Sector-balanced greedy fill (D10):
    1. Rangsoroljuk az S_j szerint
    2. Iteratíven hozzáadjuk a legjobb tickert, ha a sector 30% notional cap-et nem sérti
    3. Megáll, ha 2-3 új entry vagy a (12 - len(open_positions)) cap
    """
    max_new = min(
        config["swing_max_daily_new"],          # 3 (default), config-toggleable
        config["swing_max_concurrent"] - len(open_positions),  # 12 cap
    )

    # Rangsor S_j szerint
    ranked = sorted(scored_candidates, key=lambda t: -t.ewma_score)

    # Sector notional állapot
    sector_notionals = compute_sector_notionals(open_positions)
    total_equity = config["account_equity"]
    sector_cap_pct = config["swing_sector_cap_pct"]  # 0.30

    selected = []
    for candidate in ranked:
        if len(selected) >= max_new:
            break

        candidate_notional = compute_notional(candidate, config)
        candidate_sector = candidate.sector

        new_sector_total = sector_notionals.get(candidate_sector, 0) + candidate_notional
        if new_sector_total > total_equity * sector_cap_pct:
            continue  # Sector cap miatt skipped

        selected.append(candidate)
        sector_notionals[candidate_sector] = new_sector_total

    return selected
```

### 3.1. `max_daily_new` finomítás

A "2-3 új entry" napi javaslat a Day 63 outcome §3.7-ből származik. **Default**: 3 (felső érték). A config-toggleable, de **a sector-balanced greedy + 30% sector cap maga is természetes korlátot ad** (egy magas-koncentrációjú nap nem fog 3-nál többet adni egy sectorba).

A `swing_max_daily_new: 3` mellett a tipikus nap **0-2 új entry** lesz (a S_j > 50 küszöb + sector cap szelektálja). A 60 napi régi mintán a "napi 5 kötelező" pattern miatt sok marginális ticker bekerült; az új rendszerben "csak ha érdemes" filozófia szellemében a 0-entry nap is megengedett és **nem hibajelzés**.

## 4. Sector groupok (a 30% cap-hez)

A Phase 3 sector klasszifikáció (XLK, XLF, XLE, etc.) megmarad. A 30% notional cap:

```python
SECTOR_GROUPS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Energy": "XLE",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Consumer Defensive": "XLP",
    "Consumer Cyclical": "XLY",
    "Basic Materials": "XLB",
    "Communication Services": "XLC",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
}
```

A "cyclical / defensive / financial / commodity" csoportosítás (BC21 régi correlation guard) **elhagyva** — a 30% per-sector notional cap önmagában elegendő diverzifikációs védelem.

## 5. Új TUNING paraméterek (`defaults.py`)

```python
# Swing Sizing (2026-05-17, Day 63 §3.7, §3.11)
"swing_sizing_enabled": True,
"swing_risk_per_trade_pct": 0.35,        # 0.35% = $350 / $100k account (D[7])
"swing_max_concurrent": 12,               # 12 cap (D[7])
"swing_max_daily_new": 3,                 # 2-3 daily új entry (D[7])
"swing_sector_cap_pct": 0.30,             # 30% notional per sector (D[11])
"swing_stop_atr_multiple": 2.0,           # 2.0×ATR mental stop (sizing-ban)
"swing_min_notional": 1_000,              # Floor: a 12×$350 / 12 = $29/ticker risk minimum

# Multiplier deactivation (m_target kivételével)
"m_vix_enabled": False,                    # Swing horizon nem érzékeny (D[4])
"m_gex_enabled": False,                    # Fázis 1 DONE
"m_contradiction_enabled": False,          # Fázis 2 backtest függvénye

# RUNTIME módosítások
"max_positions": 12,                       # Régi: 5
"max_gross_exposure": 150_000,            # Régi: 80_000 (12 × ~$12.5k avg)
"max_single_ticker_exposure": 15_000,     # Régi: 20_000 (kisebb per-ticker)
```

A `max_positions_per_sector: 2` (régi BC23) **elhagyva** — a 30% notional cap helyettesíti.

## 6. Régi sizing komponensek deaktiválása

A `phase6_sizing.py`-ban:

```python
if config["swing_sizing_enabled"]:
    # Új swing sizing path
    new_entries = select_daily_entries(scored, open_positions, config)
    for entry in new_entries:
        notional = compute_swing_notional(entry, config)
        # ...
else:
    # Régi multiplier chain (legacy fallback)
    new_entries = legacy_size_positions(scored, config)
```

A régi BMI Momentum Guard, BC21 Cross-Asset Regime adjusts, Correlation Guard sector groups **NEM** futnak a swing path-on. A Cross-Asset Regime mint **monitoring/log signal** megmarad, de a `max_positions` átírás **nem** alkalmazódik (a 12 cap fix).

## 7. Implementáció lépésekben

1. **TUNING + RUNTIME paraméterek** (15 min)
2. **`compute_swing_notional`** (20 min) — az új képlet
3. **`select_daily_entries` sector-balanced greedy** (40 min)
4. **`phase6_sizing.py` átalakítás** (30 min) — config-toggle + új path
5. **Tesztek** (45 min) — 10-12 unit teszt
6. **Smoke test** (10 min) — mock 1000-es univerzum + 200 qualified ticker
7. **Commit** (5 min)

**Összesen: ~2h.**

## 8. Tesztek (10-12)

```python
def test_compute_swing_notional_basic():
    """notional = (equity × 0.0035) / (ATR_pct × 2.0) × entry × M_target."""

def test_compute_swing_notional_m_target_penalty():
    """20-50% target overshoot → ×0.85 notional."""

def test_select_entries_respects_max_daily_new():
    """Max 3 daily new entry."""

def test_select_entries_respects_max_concurrent():
    """Open=10, max_new=3 → csak 2 új (12 cap)."""

def test_select_entries_sector_cap_30pct():
    """Egy sector már 25% notional → új ticker abban a sectorban kizárt, ha az új notional >30%-ot lépne."""

def test_select_entries_sector_balanced_greedy():
    """High-S_j ticker tech, de tech cap eléri → következő ranking ticker kiválasztva, akkor is ha alacsonyabb S_j."""

def test_select_entries_zero_new_when_no_qualified():
    """Ha 0 ticker > 50 score → 0 daily new entry."""

def test_select_entries_zero_new_when_at_cap():
    """Open=12 → 0 daily new entry."""

def test_m_vix_disabled_no_size_effect():
    """VIX 30 → notional UGYANANNYI mint VIX 15-ön (M_VIX=1.0 forcelt)."""

def test_m_contradiction_disabled_phase6():
    """Phase 4 jelez M_c trigger-t, de Phase 6 NEM alkalmazza (m_contradiction_enabled=False)."""

def test_phase6_integration_with_phase4_swing_output():
    """End-to-end: Phase 4 swing output → Phase 6 entry selection."""
```

## 9. Commit message

```
feat(sizing): swing Phase 6 — 0.35% risk, 12 cap, 30% sector notional, sector-balanced greedy

Day 63 outcome §3.7 + §3.11: sizing radically rescaled for swing horizon.
"Quality over quantity" principle: fewer but larger positions, with
sector concentration capped by notional (not ticker count).

- Risk per trade: 0.7% → 0.35%
- Max concurrent: 5 → 12 (daily new 2-3, config-toggleable)
- Sector cap: 2 ticker → 30% notional per sector
- Stop ATR multiple in sizing formula: 1.5 → 2.0
- Active multipliers: only M_target (M_VIX, M_GEX, M_contradiction disabled)

Sector-balanced greedy fill (D10): rank by S_j, fill while respecting
30% notional cap per sector.

Tests: 11 unit + 1 integration.

Refs: docs/decisions/2026-05-14-day63-decision-outcome.md §3.7, §3.11
```

## 10. Kapcsolódó

- [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3.7, §3.11
- [`docs/design/swing-pivot-architecture.md`](../design/swing-pivot-architecture.md) §2.3, §8.4
- [`docs/tasks/2026-05-17-swing-scoring-phase4.md`](2026-05-17-swing-scoring-phase4.md) (függőség)
- [`docs/tasks/2026-05-17-swing-execution-exit.md`](2026-05-17-swing-execution-exit.md) (downstream)
