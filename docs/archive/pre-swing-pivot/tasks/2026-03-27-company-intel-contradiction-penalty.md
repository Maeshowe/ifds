---
Status: DONE
Updated: 2026-03-28
Note: Phase 4 FMP fetch (async gather 7. slot), M_target multiplier Phase 6-ban, 12 teszt. Döntés: A opció (Phase 4 fetch, teljes lefedettség).
Note: Phase 6 — Company Intel contradiction penalty. Ha ár >20% analyst target felett → ×0.85 multiplier.
---

# Company Intel Contradiction Penalty — Phase 6 Multiplier

## Probléma

Az elmúlt hét review-jaiból (márc 23-27) egyértelmű mintázat rajzolódik ki:
azok a tickerek amelyeknél a Company Intel "contradiction" flag-et jelez
(ár messze az analyst consensus target felett), szisztematikusan veszteségesek.

Példák:
- **SEDG** (márc 26): 50% felett analyst target → -$360.24 veszteség
- **VICR** (márc 20): 61% felett analyst target → -$440 SL hit
- **OLN** (márc 26): 25% felett analyst high target → veszteséges
- **EQT** (márc 26): 23.5% felett high target → -$93.24

A scoring jelenleg nem veszi figyelembe az ár vs analyst target viszonyt
— ez kizárólag a Company Intel poszt-pipeline elemzésben jelenik meg,
ami a kereskedés UTÁN fut.

## Megoldás

Új Phase 6 multiplier: **M_target** — penalty ha az aktuális ár
szignifikánsan meghaladja az analyst consensus price target-et.

### Logika

```python
def _calculate_target_multiplier(
    current_price: float,
    analyst_target: float | None,
    config: Config,
) -> float:
    """Analyst price target proximity multiplier.
    
    If price is significantly above analyst consensus target,
    the upside is limited → reduce position size.
    """
    if analyst_target is None or analyst_target <= 0:
        return 1.0  # No data → no penalty
    
    overshoot_pct = (current_price - analyst_target) / analyst_target
    
    threshold = config.tuning.get("target_overshoot_threshold", 0.20)  # 20%
    penalty = config.tuning.get("target_overshoot_penalty", 0.85)       # ×0.85
    severe_threshold = config.tuning.get("target_severe_threshold", 0.50)  # 50%
    severe_penalty = config.tuning.get("target_severe_penalty", 0.60)     # ×0.60
    
    if overshoot_pct > severe_threshold:
        return severe_penalty    # 50%+ above → ×0.60
    elif overshoot_pct > threshold:
        return penalty           # 20-50% above → ×0.85
    else:
        return 1.0               # Within range → no penalty
```

### Adatforrás

Az analyst consensus price target a **FMP API**-ból jön:
`/stable/price-target-consensus?symbol=XYZ` → `targetConsensus` mező.

A Company Intel script (`scripts/company_intel.py`) már lekéri ezt az
`fetch_price_target()` metódussal. A kérdés: a pipeline-ban (Phase 4 vagy 6)
is le kell kérni, vagy a Company Intel-ből áthozni.

**Javaslat:** Phase 4-ben kérjük le (egy extra FMP hívás per ticker),
és a `StockAnalysis` dataclass-ba mentjük. Így Phase 6-ban elérhető
a multiplier számításhoz.

### Alternatíva: Phase 4 score-ba építés

Ahelyett, hogy Phase 6 multiplier lenne, a contradiction flag-et Phase 4-ben
is be lehetne építeni a `fundamental_score`-ba. De ez problémás mert a Phase 4
score a ticker rangsoroláshoz kell, nem a méretezéshez. A multiplier a
méretezésben finomabb — nem zárja ki a tickert, csak kisebb pozíciót vesz.

---

## Implementáció

### 1. FMP API hívás Phase 4-ben

```python
# phase4_stocks.py — _analyze_single_stock() bővítés
target_data = fmp.get_price_target_consensus(ticker)
analyst_target = target_data.get("targetConsensus") if target_data else None
```

### 2. StockAnalysis bővítés

```python
# models/market.py
@dataclass
class StockAnalysis:
    ...
    analyst_target: float | None = None  # FMP consensus price target
```

### 3. Phase 6 multiplier

A `_calculate_multiplier_total()` bővítése M_target-tel:

```python
# Jelenlegi: M_total = M_flow × M_insider × M_funda × M_gex × M_vix × M_utility
# Új:        M_total = M_flow × M_insider × M_funda × M_gex × M_vix × M_utility × M_target

m_target = _calculate_target_multiplier(
    stock.technical.price,
    stock.analyst_target,
    config,
)
```

### 4. Config kulcsok

```python
# defaults.py TUNING
"target_overshoot_enabled": True,        # Feature flag
"target_overshoot_threshold": 0.20,      # 20% above consensus → ×0.85
"target_overshoot_penalty": 0.85,
"target_severe_threshold": 0.50,         # 50% above → ×0.60
"target_severe_penalty": 0.60,
```

### 5. Logging

```python
if m_target < 1.0:
    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=6,
               message=f"[TARGET] {ticker} price=${price:.2f} target=${target:.2f} "
                       f"overshoot={overshoot_pct:.1%} → M_target={m_target}",
               data={"ticker": ticker, "m_target": m_target, "overshoot_pct": overshoot_pct})
```

---

## Tesztelés

1. Unit: price 10% above target → M_target = 1.0 (no penalty)
2. Unit: price 25% above target → M_target = 0.85
3. Unit: price 55% above target → M_target = 0.60
4. Unit: analyst_target = None → M_target = 1.0 (no data)
5. Unit: analyst_target = 0 → M_target = 1.0 (invalid)
6. Unit: price below target → M_target = 1.0 (no penalty for undervalued)
7. Unit: M_total clamp 0.25-2.0 megmarad M_target hozzáadásával
8. Integration: pipeline run → TARGET log sorok a cron logban
9. Meglévő tesztek: 1034+ passing — regresszió

---

## Commit üzenet

```
feat(phase6): analyst price target contradiction penalty (M_target)

Add multiplier M_target to Phase 6 sizing chain:
  price 20-50% above analyst consensus → ×0.85
  price >50% above analyst consensus → ×0.60
Fetch target from FMP price-target-consensus in Phase 4.

Addresses systematic losses on tickers flagged as contradictions
in Company Intel (SEDG -$360, VICR -$440, OLN, EQT pattern).

Config: target_overshoot_enabled, target_overshoot_threshold (0.20),
        target_severe_threshold (0.50).
```

---

## Érintett fájlok

- `src/ifds/data/fmp.py` — `get_price_target_consensus()` (ha nincs még)
- `src/ifds/phases/phase4_stocks.py` — analyst target lekérés + StockAnalysis
- `src/ifds/models/market.py` — `StockAnalysis.analyst_target` mező
- `src/ifds/phases/phase6_sizing.py` — `_calculate_target_multiplier()` + M_target
- `src/ifds/config/defaults.py` — target config kulcsok
- `docs/PARAMETERS.md` — frissítés
- `tests/test_target_penalty.py` — új tesztek