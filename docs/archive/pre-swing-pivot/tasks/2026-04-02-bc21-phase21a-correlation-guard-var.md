Status: DONE
Updated: 2026-04-03
Note: BC21 Phase_21A — Korrelációs Guard + Portfolio VaR (~5h CC)

# BC21 Phase_21A — Korrelációs Guard + Portfolio VaR

## Cél

Portfolio-szintű risk management: ne legyen 5 azonos szektorjellegű pozíció
egyszerre, és legyen VaR-alapú expozíció limit. Jelenleg csak ticker-szintű
és szektor-szintű limit van (max_positions=8, max_per_sector=3).

## Háttér

A jelenlegi rendszer max 3 pozíciót enged szektoronként, de a szektorok közötti
korreláció nincs kezelve. Példa: XLE (Energy) + XLB (Materials) + XLI (Industrials)
mind ciklikus szektorok — 3×3=9 pozíció lehet egyszerre ciklikusból, ami egy
risk-off napon katasztrofális.

## Scope

### 1. Korrelációs Guard — `src/ifds/phases/phase6_sizing.py`

Szektorcsoport-alapú limit (nem egyedi korreláció-számolás — az túl drága és
instabil kis mintán):

```python
SECTOR_GROUPS = {
    "cyclical": ["Technology", "Consumer Cyclical", "Industrials", "Basic Materials"],
    "defensive": ["Utilities", "Consumer Defensive", "Healthcare"],
    "financial": ["Financial Services", "Real Estate"],
    "commodity": ["Energy", "Basic Materials"],
}

MAX_PER_GROUP = {
    "cyclical": 5,      # max 5 ciklikus pozíció összesen
    "defensive": 4,
    "financial": 3,
    "commodity": 3,
}
```

A `_apply_position_limits()` függvénybe új lépés:

```python
# 6. Sector group diversification (correlation guard)
group_counts = {}
for pos in accepted:
    for group_name, sectors in SECTOR_GROUPS.items():
        if pos.sector in sectors:
            group_counts[group_name] = group_counts.get(group_name, 0) + 1

for group_name, sectors in SECTOR_GROUPS.items():
    if pos.sector in sectors:
        if group_counts.get(group_name, 0) >= MAX_PER_GROUP[group_name]:
            # skip — too many correlated positions
            counts["correlation"] += 1
            continue
```

### 2. Portfolio VaR — `src/ifds/risk/portfolio_var.py` (ÚJ)

Egyszerű parametrikus VaR (nem Monte Carlo — az túl lassú a pipeline-ban):

```python
def calculate_portfolio_var(
    positions: list[PositionSizing],
    atr_data: dict[str, float],     # {ticker: ATR14}
    confidence: float = 0.95,
    horizon_days: int = 1,
) -> float:
    """Calculate portfolio Value at Risk.
    
    Simplified: assume positions are independent (worst case).
    VaR_portfolio = sqrt(sum(VaR_i^2))
    
    Per-position VaR: position_value × daily_vol × z_score
    daily_vol ≈ ATR / price (crude but fast)
    """
```

A VaR-t a Phase 6 végén számoljuk, és ha meghaladja a limitet
(pl. `max_portfolio_var_pct = 3.0%`), a leggyengébb score-ú pozíciót
eltávolítjuk iteratívan.

### 3. Config kulcsok

```python
TUNING = {
    # Correlation Guard (BC21)
    "correlation_guard_enabled": True,
    "sector_group_max_cyclical": 5,
    "sector_group_max_defensive": 4,
    "sector_group_max_financial": 3,
    "sector_group_max_commodity": 3,
    
    # Portfolio VaR (BC21)
    "portfolio_var_enabled": True,
    "portfolio_var_confidence": 0.95,
    "portfolio_var_max_pct": 3.0,        # Max 3% account VaR
}
```

### 4. Phase6Result bővítés

```python
# Új mezők
excluded_correlation_limit: int = 0
portfolio_var_pct: float = 0.0
portfolio_var_usd: float = 0.0
var_positions_removed: int = 0
```

## Tesztelés

- `test_correlation_guard.py`:
  - 6 ciklikus pozíció → 5 elfogadva, 1 kiszűrve
  - 3 defensive + 2 financial → mind elfogadva (szeparált csoportok)
  - Üres pozíció lista → no crash
  - Disabled config → bypass
- `test_portfolio_var.py`:
  - 8 pozíció, normál ATR → VaR < 3%
  - 8 magas ATR pozíció → VaR > 3%, leggyengébb eltávolítva
  - Egypozíciós portfólió → VaR = position VaR
- Meglévő Phase 6 tesztek: all green

## Fájlok

| Fájl | Változás |
|------|---------|
| `src/ifds/risk/__init__.py` | ÚJ csomag |
| `src/ifds/risk/portfolio_var.py` | ÚJ — VaR számítás |
| `src/ifds/phases/phase6_sizing.py` | Correlation guard + VaR check `_apply_position_limits`-ben |
| `src/ifds/config/defaults.py` | Új TUNING kulcsok |
| `src/ifds/models/market.py` | Phase6Result bővítés |
| `tests/phases/test_correlation_guard.py` | ÚJ |
| `tests/risk/test_portfolio_var.py` | ÚJ |

## Commit

```
feat(phase6): add correlation guard and portfolio VaR limit

Sector group correlation guard limits cyclical/defensive/financial/
commodity exposure. Parametric portfolio VaR removes weakest
positions if aggregate risk exceeds max_portfolio_var_pct (3%).
```
