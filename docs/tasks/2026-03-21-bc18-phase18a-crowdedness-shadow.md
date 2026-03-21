---
Status: BLOCKED
Updated: 2026-03-21
Note: BC18 Phase_18A/2 — crowdedness shadow. Vár Tamás döntésére (3 kérdés).
---

# BC18 Phase_18A/2 — Crowdedness Shadow Mode

## Kontextus

A crowdedness layer szétválasztja az intézményi akkumulációt (Good Crowding)
és a zsúfolt pozíciókat (Bad Crowding) az MMS adatokból. Shadow mode-ban
a score számolódik és logolódik, de a Phase 6 sizing-ot NEM módosítja.

**Design doc:** `docs/planning/crowdedness-decision-prep.md` (245 sor, részletes)

**Prioritás:** P1, de BLOCKED — 3 döntési pont vár Tamás válaszára

---

## Döntési pontok (BLOKKOLÓ)

### 1. dark_share küszöb
| Opció | Érték | Trade-off |
|-------|-------|-----------|
| **A** | > 0.45 | Korán detektál, több ticker, shadow-ban biztonságos |
| **B** | > 0.55 | Konzervatívabb, csak valóban crowded tickerek |
| **C** | > 0.60 | Közel a DD küszöbhöz, legkevesebb false positive |

Chat ajánlása: **B (0.55)**

### 2. Bad Crowding hatás (élesítés után)
| Opció | Leírás |
|-------|--------|
| **A — Kiszűrés** | score < -0.5 → ticker kiesik |
| **B — Penalty** | Multiplier csökkentés (×0.5) |
| **C — Mindkettő** | Erős bad (< -0.7) kiszűr, közepes penaltyzik |

Chat ajánlása: **C (Mindkettő)**

### 3. Good Crowding boost
| Opció | Leírás |
|-------|--------|
| **A — Additív** | Crowdedness boost az MMS multiplier mellé (+0.1..+0.15) |
| **B — Override** | Crowdedness felváltja az MMS multiplier egy részét |
| **C — Csak Bad** | Good Crowdingnál nincs boost, csak Bad penaltyzik |

Chat ajánlása: **A (Additív)**

---

## Shadow Mode implementáció (döntések után)

### Composite score formula

```python
def compute_crowding_score(
    dark_share, z_block, z_dex, iv_skew, median_iv_skew, daily_return,
    threshold_high=0.55,  # ← döntés #1
) -> float:
    """Crowdedness composite ∈ [-1.0, +1.0]."""
    if dark_share < threshold_high or z_block is None or z_block < 0.5:
        return 0.0

    direction = 0.0
    if z_dex is not None:
        direction -= z_dex * 0.4
    direction += daily_return * 20
    direction = max(-1.0, min(1.0, direction))

    fear = (iv_skew - median_iv_skew) * 5
    fear = max(-1.0, min(1.0, fear))

    intensity = min(1.0, (dark_share - threshold_high) / 0.3 + z_block / 3.0)

    raw = (direction * 0.6 - fear * 0.4) * intensity
    return max(-1.0, min(1.0, raw))
```

### Hol fut

- **Phase 5** (`phase5_mms.py`): `_compute_mms_analysis()` után, az MMS features-ből
- **Shadow log**: napi output, EventLogger-rel
- **Phase 6 impact**: NINCS (shadow mode), `crowding_score` csak logolódik

### MMS rezsim ↔ Crowdedness mapping

| MMS Rezsim | Várható Crowdedness |
|------------|---------------------|
| DD | Good (+0.5..+1.0) |
| ABS | Good (+0.3..+0.8) |
| DIST | Bad (-0.5..-1.0) |
| VOLATILE | Bad (-0.3..-0.8) |
| Γ⁺ | Semleges |
| Γ⁻ | Bad (-0.2..-0.6) |
| NEU | Semleges (0.0) |

---

## Tesztelés

1. Unit: `compute_crowding_score()` — Good Crowding input → score > +0.5
2. Unit: `compute_crowding_score()` — Bad Crowding input → score < -0.5
3. Unit: `dark_share < threshold` → 0.0
4. Unit: `z_block < 0.5` → 0.0 (not crowded enough)
5. Unit: Shadow mode → Phase 6 sizing unchanged
6. Integration: Pipeline run with shadow logging → crowding_score in event log

---

## Commit üzenet

```
feat(phase5): crowdedness shadow mode — compute and log composite score (BC18A)

Compute Good/Bad Crowding score from MMS features (dark_share, z_block,
z_dex, iv_skew, daily_return). Shadow mode: score logged but does NOT
affect Phase 6 sizing. 2-week data collection before activation.

Config: crowdedness_shadow_enabled, crowdedness_threshold (default 0.55).
```

---

## Érintett fájlok

- `src/ifds/config/defaults.py` — `crowdedness_*` config kulcsok
- `src/ifds/phases/phase5_mms.py` — `compute_crowding_score()` + shadow logging
- `src/ifds/models/market.py` — `MMSAnalysis.crowding_score` mező (opcionális)
- `tests/test_bc18_crowdedness.py` — új tesztek

---

## Prioritás

**P1, BLOCKED** — Tamás döntése szükséges a 3 kérdésben.
Az EWMA (Phase_18A/1) és MMS aktiválás (Phase_18B) ettől függetlenül implementálható.
