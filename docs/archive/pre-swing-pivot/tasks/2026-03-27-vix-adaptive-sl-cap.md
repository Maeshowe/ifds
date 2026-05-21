---
Status: DONE
Updated: 2026-03-27
Note: Quick win — VIX-adaptív SL cap az AVWAP MKT fill utáni bracket rebuild-ben.
---

# VIX-Adaptív SL Cap — pt_avwap.py Bracket Rebuild

## Probléma

Az AVWAP MKT konverziókor (`pt_avwap.py` → `convert_to_market()`) a bracket
az eredeti SL distance-t (1.5× ATR) megőrzi. Magas VIX környezetben ez
túl nagy SL-t eredményez a fill árhoz képest — a veszteség nagyobb lehet
mint amit a volatilitási környezet indokol.

A review adatokból (2026-03-25, VIX=25.31): minden ticker veszteséggel zárt
MOC-on, és az AVWAP MKT fill-ek rosszabb entry-t adtak a tervezettnél
(MTZ +1.2%, HWM +1.2% slippage).

**Cél:** A VIX szintjétől függően cap-eljük a max SL distance-t az AVWAP
fill ár százalékában.

**Prioritás:** P1 — közvetlen kockázatcsökkentés
**Becsült idő:** 1 óra

---

## Design

### VIX-függő SL cap táblázat

| VIX szint | Max SL distance | Logika |
|---|---|---|
| < 20 | 1.5× ATR (nincs cap) | Normál volatilitás, eredeti SL rendben |
| 20-25 | min(1.5× ATR, fill × 2.0%) | Emelt vol — SL max 2% a fill-től |
| 25-30 | min(1.5× ATR, fill × 1.5%) | Magas vol — szűkebb SL |
| > 30 | min(1.0× ATR, fill × 1.0%) | Extrém — tight SL + csökkentett ATR |

A `min()` logika azt jelenti, hogy a két korlát közül a szigorúbbat használjuk.
Ha az ATR-alapú SL amúgy is szűkebb mint a %-os cap, az ATR marad.

### Hol jön a VIX érték?

A `pt_avwap.py` nem fér hozzá közvetlenül a pipeline VIX-hez. Két lehetőség:

**A) FRED API hívás (ajánlott):** Ugyanaz a `fred_client.py` VIX lekérés ami
Phase 0-ban fut. Ez egy extra API hívás, de a FRED free tier bőven bírja.

```python
from ifds.data.fred_client import FREDClient

fred = FREDClient(api_key=os.getenv("IFDS_FRED_API_KEY"))
vix = fred.get_vix()  # VIXCLS legutolsó érték
```

**B) Pipeline state fájlból (alternatíva):** A Phase 0 output-ot (VIX) egy
state fájlba mentjük és a pt_avwap.py onnan olvassa. Ez gyorsabb de
extra state management.

Javaslat: **A opció** — egyszerűbb, nincs state dependency.

---

## Implementáció

### pt_avwap.py — convert_to_market() módosítás

```python
def get_vix_adaptive_sl(fill_price: float, original_sl_distance: float,
                         atr: float | None = None) -> float:
    """Calculate VIX-adaptive SL distance.
    
    Returns the stop loss distance (positive number) from fill price.
    Uses min(ATR-based, VIX-cap) logic.
    """
    from ifds.data.fred_client import FREDClient
    
    fred = FREDClient(api_key=os.getenv("IFDS_FRED_API_KEY"))
    vix = fred.get_vix()
    
    if vix is None:
        logger.warning("VIX unavailable — using original SL distance")
        return original_sl_distance
    
    # Determine VIX-based cap
    if vix < 20:
        return original_sl_distance  # No cap
    elif vix < 25:
        max_pct = 0.020  # 2.0%
    elif vix < 30:
        max_pct = 0.015  # 1.5%
    else:
        max_pct = 0.010  # 1.0%
        # Also reduce ATR multiplier for extreme VIX
        if atr is not None:
            original_sl_distance = min(original_sl_distance, 1.0 * atr)
    
    pct_cap = fill_price * max_pct
    capped_sl = min(original_sl_distance, pct_cap)
    
    logger.info(
        f"VIX-adaptive SL: VIX={vix:.1f} | "
        f"original={original_sl_distance:.2f} | "
        f"pct_cap={pct_cap:.2f} ({max_pct*100:.1f}%) | "
        f"final={capped_sl:.2f}"
    )
    
    return capped_sl
```

### convert_to_market() bracket rebuild módosítás

A meglévő kódban:
```python
# RÉGI
new_sl = round(fill_price - sl_distance, 2)

# ÚJ
capped_distance = get_vix_adaptive_sl(fill_price, sl_distance)
new_sl = round(fill_price - capped_distance, 2)
```

### monitor_state frissítés

```python
# A capped SL-t is mentsük a state-be
s["stop_loss"] = new_sl
s["sl_distance"] = capped_distance  # frissített distance a trail-hez
s["vix_at_avwap"] = vix  # audit trail
```

Ez fontos, mert a `pt_monitor.py` Scenario A trail a `sl_distance`-ból
számolja a trail step-et. Ha a capped distance kisebb, a trail is szűkebb.

---

## Telegram üzenet bővítés

```python
msg = (
    f"AVWAP {sym}: Limit->MKT conversion\n"
    f"Fill @ ${fill_price:.2f}\n"
    f"VIX: {vix:.1f} | SL cap: {max_pct*100:.1f}%\n"
    f"New SL: ${new_sl:.2f} (distance: ${capped_distance:.2f})\n"
    f"TP1: ${new_tp1:.2f} | TP2: ${new_tp2:.2f}"
)
```

---

## Tesztelés

1. Unit: VIX < 20 → original_sl_distance unchanged
2. Unit: VIX = 22 → min(sl_distance, fill × 0.020)
3. Unit: VIX = 27 → min(sl_distance, fill × 0.015)
4. Unit: VIX = 35 → min(1.0 × ATR, fill × 0.010)
5. Unit: VIX unavailable → fallback to original
6. Unit: monitor_state sl_distance frissül → pt_monitor trail konzisztens
7. Meglévő tesztek: 1034+ passing — regresszió

---

## Commit üzenet

```
feat(pt_avwap): VIX-adaptive SL cap on AVWAP bracket rebuild

After AVWAP Limit→MKT conversion, cap the SL distance based on VIX:
  VIX < 20: no cap (original 1.5× ATR)
  VIX 20-25: min(1.5× ATR, 2.0% of fill)
  VIX 25-30: min(1.5× ATR, 1.5% of fill)
  VIX > 30: min(1.0× ATR, 1.0% of fill)

Updates monitor_state.sl_distance for consistent trail behavior.
Fetches VIX from FRED API (VIXCLS) at conversion time.
```

---

## Érintett fájlok

- `scripts/paper_trading/pt_avwap.py` — `get_vix_adaptive_sl()` + convert_to_market módosítás
- `tests/paper_trading/test_pt_avwap_vix_sl.py` — új tesztek
