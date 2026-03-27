---
Status: DONE
Updated: 2026-03-27
Note: Phase 0 bővítés — 2s10s yield curve spread shadow log. TNX mellé, nem helyette.
---

# 2s10s Yield Curve Spread — Shadow Log a Phase 0 Diagnostics-ban

## Kontextus

A pipeline jelenleg a TNX-et (10-Year Treasury, FRED: `DGS10`) használja
Phase 0-ban a makro diagnostics-hoz és a rate sensitivity szűrőhöz.
A TNX abszolút kamatszintet mér — "magasak-e a kamatok?"

A 2s10s spread (10Y − 2Y) más információt hordoz: a hozamgörbe meredekségét,
ami a piac gazdasági várakozásait tükrözi. Invertálás (spread < 0) historikusan
recessziós jelzés volt (6/7 esetben 1976 óta), az un-inversion (visszafordulás
pozitívba) pedig azonnalibb figyelmeztetés.

**Cél:** Shadow log — a spread logolása Phase 0-ban, 2-3 hétig gyűjtjük,
utána döntünk a Szint 2 (küszöbök) és Szint 3 (BC21 Cross-Asset Regime
integráció) bevezetéséről.

**Prioritás:** P2 — nem blokkoló, de hasznos makro kontextus
**Becsült idő:** 1 óra

---

## FRED API

A 2s10s spread egyetlen sorozatként elérhető a FRED-en:

- **Series ID:** `T10Y2Y`
- **Endpoint:** `fred/series/observations?series_id=T10Y2Y` (v1 API, amit az IFDS már használ)
- **Frekvencia:** Daily
- **Egység:** Percentage points (pl. +0.35 = 35 bps meredekség, -0.50 = 50 bps inverzió)
- **Forrás:** Federal Reserve Bank of St. Louis

A meglévő `fred_client.py` már tud `DGS10` (TNX) és `VIXCLS` (VIX) sorozatokat
lekérni — a `T10Y2Y` ugyanazzal a mechanizmussal elérhető, nincs új API dependency.

---

## Implementáció

### 1. fred_client.py — új sorozat lekérés

A meglévő `get_series_value()` (vagy hasonló) metódussal:

```python
# fred_client.py
def get_yield_curve_2s10s(self) -> float | None:
    """Get 2s10s yield curve spread (T10Y2Y) from FRED.
    
    Returns spread in percentage points.
    Positive = normal curve, Negative = inverted.
    """
    return self._get_latest_value("T10Y2Y")
```

### 2. Phase 0 diagnostics — shadow log

A VIX és TNX mellé:

```python
# phase0_diagnostics.py
yield_curve_2s10s = fred.get_yield_curve_2s10s()

if yield_curve_2s10s is not None:
    curve_status = "INVERTED" if yield_curve_2s10s < 0 else (
        "FLATTENING" if yield_curve_2s10s < 0.20 else "NORMAL"
    )
    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.INFO, phase=0,
               message=f"Yield Curve 2s10s: {yield_curve_2s10s:.2f}% ({curve_status})",
               data={
                   "yield_curve_2s10s": yield_curve_2s10s,
                   "curve_status": curve_status,
               })
```

### 3. MacroRegime dataclass — új mező

```python
# models/market.py — MacroRegime bővítés
@dataclass
class MacroRegime:
    vix: float
    vix_regime: str
    vix_multiplier: float
    tnx: float
    rate_sensitive: bool
    yield_curve_2s10s: float | None = None  # ÚJ — shadow, nincs hatás
    curve_status: str = "UNKNOWN"            # ÚJ — NORMAL/FLATTENING/INVERTED
```

### 4. Telegram report — opcionális sor

A Phase 0 Telegram blokkban:

```
Macro: VIX=25.31 (elevated)  TNX=4.39%  Rate-sensitive=True  2s10s=+0.35% (NORMAL)
```

### 5. Config kulcsok

```python
# defaults.py TUNING
"yield_curve_shadow_enabled": True,    # Shadow log (no effect on sizing)
```

---

## Amit NEM csinálunk most

- Phase 6 sizing-ra nincs hatás (shadow only)
- Nincs VIX küszöb tolás a spread alapján (az Szint 2)
- Nincs BC21 Cross-Asset Regime integráció (az Szint 3)
- Nincs SMA20(2s10s) számítás (az Szint 2-höz kell majd)

---

## Tesztelés

1. Unit: `get_yield_curve_2s10s()` — FRED mock, pozitív érték
2. Unit: `get_yield_curve_2s10s()` — FRED mock, negatív érték (inverted)
3. Unit: `get_yield_curve_2s10s()` — FRED API hiba → None, pipeline tovább fut
4. Unit: `curve_status` — "NORMAL" (>0.20), "FLATTENING" (0..0.20), "INVERTED" (<0)
5. Unit: MacroRegime dataclass — `yield_curve_2s10s` opcionális mező
6. Meglévő tesztek: 1034+ passing — regresszió

---

## Commit üzenet

```
feat(phase0): add 2s10s yield curve spread shadow log

Fetch T10Y2Y from FRED API and log yield curve status (NORMAL/FLATTENING/
INVERTED) in Phase 0 diagnostics. Shadow mode: logged but does NOT affect
Phase 6 sizing. TNX rate sensitivity unchanged.

Config: yield_curve_shadow_enabled (default True).
```

---

## Érintett fájlok

- `src/ifds/data/fred_client.py` — `get_yield_curve_2s10s()` metódus
- `src/ifds/phases/phase0_diagnostics.py` — shadow log sor
- `src/ifds/models/market.py` — `MacroRegime.yield_curve_2s10s` mező
- `src/ifds/output/telegram.py` — 2s10s sor a Macro blokkban
- `src/ifds/config/defaults.py` — `yield_curve_shadow_enabled` config
- `tests/test_yield_curve.py` — új tesztek
