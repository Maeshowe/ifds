Status: DONE
Updated: 2026-04-03
Note: BC21 Phase_21B — Cross-Asset Regime réteg (~5h CC)

# BC21 Phase_21B — Cross-Asset Regime (HYG/IEF, RSP/SPY, IWM/SPY + 2s10s)

## Cél

Piac-szintű risk regime réteg: 3 ETF arány + 2s10s yield curve szavazási
rendszerrel határozza meg a piac állapotát (NORMAL → CAUTIOUS → RISK_OFF → CRISIS).
A VIX küszöböket tolja el (nem önálló multiplier), ezzel elkerülve a
multiplikátor-lánc exponenciális büntetését.

## Háttér

A jelenlegi BMI Momentum Guard (3+ nap csökkenés → max_pos 5) egy "gyors fix" volt.
A Cross-Asset Regime az igazi megoldás — több piaci dimenzió alapján dönt:
- **HYG/IEF** — credit spread, leghamarabb jelez (kapuőr)
- **RSP/SPY** — piaci breadth (equal-weight vs cap-weight)
- **IWM/SPY** — small cap relatív erő (feltételes, csak HYG-gel együtt szavaz)
- **2s10s** — yield curve (T10Y2Y, FRED API — shadow óta ápr 2, 4. szavazó)

## Scope

### 1. `src/ifds/phases/phase0_diagnostics.py` — ETF adatlekérés

A Phase 0-ban (System Diagnostics) már lekérjük a VIX-et és TNX-et.
Bővítés: 5 ETF + 2s10s lekérés.

```python
# Polygon: HYG, IEF, RSP, SPY, IWM — 25 nap daily bars (SMA20-hoz)
# FRED: T10Y2Y (2s10s yield spread) — már megvan shadow módban

cross_asset_etfs = ["HYG", "IEF", "RSP", "SPY", "IWM"]
for etf in cross_asset_etfs:
    bars = polygon.get_daily_bars(etf, lookback=25)
    # Calculate ratio: HYG/IEF, RSP/SPY, IWM/SPY
    # Calculate SMA20 of each ratio
```

### 2. `src/ifds/risk/cross_asset.py` — Új modul

```python
from dataclasses import dataclass
from enum import Enum

class CrossAssetRegime(Enum):
    NORMAL = "NORMAL"
    CAUTIOUS = "CAUTIOUS"
    RISK_OFF = "RISK_OFF"
    CRISIS = "CRISIS"

@dataclass
class CrossAssetResult:
    regime: CrossAssetRegime
    votes: int                     # 0-3 (+ optional 4th from 2s10s)
    hyg_ief_below_sma: bool
    rsp_spy_below_sma: bool
    iwm_spy_below_sma: bool
    yield_curve_inverted: bool     # 2s10s < 0
    vix_threshold_delta: int       # -5 to +3
    max_positions_override: int | None
    min_score_override: int | None
    details: dict

def calculate_cross_asset_regime(
    ratios: dict[str, list[float]],   # {"hyg_ief": [25 daily values], ...}
    vix_value: float,
    yield_spread: float | None,       # 2s10s from FRED (None if unavailable)
    config: dict,
) -> CrossAssetResult:
    """Calculate cross-asset regime from ETF ratios.
    
    Voting logic:
      votes = 0
      if hyg_ief < sma20(hyg_ief):   votes += 1  # credit — always votes
      if rsp_spy < sma20(rsp_spy):   votes += 1  # breadth — always votes
      if iwm_spy < sma20(iwm_spy) AND hyg_ief < sma20(hyg_ief):
          votes += 1                               # small cap — conditional
      
      # Optional 4th voter: 2s10s yield curve
      if yield_spread is not None and yield_spread < yield_curve_threshold:
          votes += 0.5  # half vote — yield curve is slow-moving
    
    Regime mapping:
      0 votes     → NORMAL   (VIX threshold ±0,  max_pos 8,  min_score 70)
      1 vote      → CAUTIOUS (VIX threshold -1,  max_pos 8,  min_score 70)
      2 votes     → RISK_OFF (VIX threshold -3,  max_pos 6,  min_score 75)
      3+ votes    → if VIX > 30: CRISIS (VIX -5, max_pos 4, min_score 80)
                    else: RISK_OFF
    """
```

### 3. Phase 0 integráció — `MacroRegime` bővítés

```python
# models/market.py — MacroRegime bővítés
cross_asset_regime: str = "NORMAL"
cross_asset_votes: int = 0
vix_threshold_adjusted: float = 20.0   # VIX threshold after cross-asset shift
```

### 4. Phase 6 integráció — VIX küszöb tolás

A jelenlegi `M_vix` számítás a `defaults.py` `vix_penalty_start` (20) küszöbből
indul. A Cross-Asset Regime ezt tolja el:

```python
# phase6_sizing.py — _calculate_multiplier_total módosítás
vix_threshold = config.tuning["vix_penalty_start"]

# Cross-asset VIX threshold adjustment
if macro.cross_asset_regime == "CAUTIOUS":
    vix_threshold -= 1   # VIX 19-től már büntet
elif macro.cross_asset_regime == "RISK_OFF":
    vix_threshold -= 3   # VIX 17-től büntet
elif macro.cross_asset_regime == "CRISIS":
    vix_threshold -= 5   # VIX 15-től büntet

# Existing VIX multiplier calculation with shifted threshold
if macro.vix_value > vix_threshold:
    penalty = (macro.vix_value - vix_threshold) * config.tuning["vix_penalty_rate"]
    m_vix = max(config.tuning["vix_multiplier_floor"], 1.0 - penalty)
```

### 5. Phase 6 — max_positions + min_score override

```python
# runner.py — Phase 6 előtt
if cross_asset.regime == CrossAssetRegime.RISK_OFF:
    config.runtime["max_positions"] = min(config.runtime["max_positions"], 6)
    # min_score check a _calculate_position-ben
elif cross_asset.regime == CrossAssetRegime.CRISIS:
    config.runtime["max_positions"] = min(config.runtime["max_positions"], 4)
```

A `combined_score_minimum` (70) felülírása RISK_OFF-ban 75-re, CRISIS-ben 80-ra.

### 6. Telegram alert

```python
if cross_asset.regime != CrossAssetRegime.NORMAL:
    regime_emoji = {"CAUTIOUS": "⚠️", "RISK_OFF": "🔴", "CRISIS": "🚨"}
    _send_message(token, chat,
        f"{regime_emoji[cross_asset.regime.value]} <b>CROSS-ASSET: {cross_asset.regime.value}</b>\n"
        f"Votes: {cross_asset.votes}/3\n"
        f"HYG/IEF: {'below' if cross_asset.hyg_ief_below_sma else 'above'} SMA20\n"
        f"RSP/SPY: {'below' if cross_asset.rsp_spy_below_sma else 'above'} SMA20\n"
        f"VIX threshold: {config.tuning['vix_penalty_start']} → {vix_threshold_adjusted}")
```

### 7. 2s10s yield curve integráció

A 2s10s shadow (BC18 follow-up, aktív márc 27 óta) itt élesedik:
- `yield_curve_shadow_enabled` → `yield_curve_enabled`
- A FRED T10Y2Y adatot Phase 0 már lekéri
- 2s10s < 0 (inverzió) → 0.5 szavazat a cross-asset regime-ben
- 2s10s < -0.5 (erős inverzió) → 1.0 szavazat

### 8. Config kulcsok

```python
TUNING = {
    # Cross-Asset Regime (BC21)
    "cross_asset_enabled": True,
    "cross_asset_sma_period": 20,
    "cross_asset_vix_crisis_threshold": 30,     # CRISIS only if VIX > 30
    "cross_asset_cautious_vix_delta": -1,
    "cross_asset_risk_off_vix_delta": -3,
    "cross_asset_crisis_vix_delta": -5,
    "cross_asset_risk_off_max_positions": 6,
    "cross_asset_crisis_max_positions": 4,
    "cross_asset_risk_off_min_score": 75,
    "cross_asset_crisis_min_score": 80,
    
    # 2s10s Yield Curve (BC21 — élesítés)
    "yield_curve_enabled": True,                # upgrade from shadow
    "yield_curve_inversion_threshold": 0.0,     # inverted = negative spread
    "yield_curve_severe_threshold": -0.50,      # deep inversion
    "yield_curve_vote_weight": 0.5,             # half vote (slow-moving)
    "yield_curve_severe_vote_weight": 1.0,      # full vote on deep inversion
}

RUNTIME = {
    # Cross-Asset ETFs
    "cross_asset_etfs": ["HYG", "IEF", "RSP", "SPY", "IWM"],
    "cross_asset_lookback_days": 30,            # 25 trading days + buffer
}
```

## BMI Momentum Guard kapcsolat

A Cross-Asset Regime a **felettese** a BMI Momentum Guard-nak:
- Ha CRISIS aktív (max_pos 4) és BMI guard is aktív (max_pos 5) → a szigorúbb nyer (4)
- A runner.py-ben mindkettő fut, és `min()` határozza meg a végső max_positions-t

Hosszabb távon a BMI guard beolvadhat a cross-asset rendszerbe (BMI decline mint
4. szavazó), de egyelőre mindkettő fut párhuzamosan.

## Tesztelés

- `test_cross_asset.py`:
  - 0 vote → NORMAL, VIX threshold unchanged
  - HYG/IEF below → 1 vote → CAUTIOUS
  - HYG/IEF + RSP/SPY below → 2 votes → RISK_OFF
  - All 3 below + VIX > 30 → CRISIS
  - IWM alone below (no HYG) → 0 extra vote (feltételes!)
  - 2s10s inverted → +0.5 vote
  - 2s10s deep inverted → +1.0 vote
  - Phase 6: RISK_OFF → max_positions capped at 6, min_score 75
  - Phase 6: CRISIS → max_positions 4, min_score 80
  - VIX threshold shift: RISK_OFF VIX=22 → m_vix büntetés (22 > 17)
  - Config disabled → bypass
- Meglévő Phase 0 és Phase 6 tesztek: all green

## Fájlok

| Fájl | Változás |
|------|---------|
| `src/ifds/risk/cross_asset.py` | ÚJ — regime számítás |
| `src/ifds/phases/phase0_diagnostics.py` | ETF bars lekérés + ratio számítás |
| `src/ifds/phases/phase6_sizing.py` | VIX threshold shift + max_pos/min_score override |
| `src/ifds/models/market.py` | MacroRegime bővítés (cross_asset fields) |
| `src/ifds/pipeline/runner.py` | Cross-asset integráció Phase 0 → Phase 6 |
| `src/ifds/config/defaults.py` | Új TUNING/RUNTIME kulcsok |
| `src/ifds/output/telegram.py` | Cross-asset Telegram alert |
| `src/ifds/output/console.py` | Cross-asset regime kiírás |
| `tests/risk/test_cross_asset.py` | ÚJ |
| `tests/phases/test_phase6_cross_asset.py` | ÚJ — Phase 6 integráció |

## Commit

```
feat(risk): add cross-asset regime layer with ETF voting system

HYG/IEF (credit), RSP/SPY (breadth), IWM/SPY (conditional small cap)
vote on market regime: NORMAL→CAUTIOUS→RISK_OFF→CRISIS.
Shifts VIX penalty threshold (-1/-3/-5) instead of adding multiplier.
CRISIS mode: max 4 positions, min score 80, VIX threshold -5.
Integrates 2s10s yield curve as 4th voter (0.5-1.0 weight).
```
