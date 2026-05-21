# Task: dp_pct Rekalibráció — Sign-flip + Threshold + Batch Coverage

**Status:** DONE
**Priority:** P1 — scoring direkt rontja a P&L-t a jelenlegi konfigurációval
**Created:** 2026-05-08
**Updated:** 2026-05-08
**Owner:** Claude Code

**Deploy summary (2026-05-08):**
- `defaults.py` TUNING: `dark_pool_volume_threshold_pct` 40 → 12, `dp_pct_high_threshold` 60 → 18, `dp_pct_bonus` +10 → -10, `dp_pct_high_bonus` +15 → -15
- `phase4_stocks.py`: `>` → `>=` (inklúzív küszöbök az auditnak megfelelően)
- `pipeline/runner.py` + `phases/phase4_stocks.py` (sync + async): `UWBatchDarkPoolProvider` → `UWDarkPoolProvider` (per-ticker fetch). Smoke test: 20 tickerre 6.1s serial (~300ms avg), 100% success rate, no rate limit
- 6 új teszt + 11 meglévő teszt frissítve (sign-flip semantics)
- 1554 → 1556 passing, 0 failure

---

## Kontextus — Tamás döntése: az UW marad, de hatékonyan

A 2026-05-08-i dark pool retrospektív audit (60 trade, W17-W19) megerősítette, hogy **a UW dark pool % valódi prediktív tartalmat hordoz**, **DE** **inverz irányban**, mint amit a jelenlegi scoring feltételez.

### A finding számokban

| Mérőszám | Érték |
|----------|-------|
| Pearson r (dp_pct ↔ P&L $, per trade) | -0,140 (p=0,285) |
| **Pearson r (dp_pct ↔ P&L per share)** | **-0,265** (p=0,041) |
| **Spearman ρ (per share)** | **-0,327** (p=0,011) |
| Q5 - Q1 spread (per share) | -$163 (monoton inverz) |
| Q1 win rate (low dp_pct) | 58% |
| Q5 win rate (high dp_pct) | **25%** |

**A scoring jelenlegi konfigurációja:**

```python
# defaults.py — TUNING (jelenleg)
"dp_pct_high_threshold": 60,     # > 60% dp_pct
"dp_pct_bonus": 10,              # +10 bonus, ha dp_pct > 40%
"dp_pct_high_bonus": 15,         # +15 bonus, ha dp_pct > 60%
"dark_pool_volume_threshold_pct": 40,  # az alap küszöb
```

**Két strukturális probléma:**

1. **Sign hibás** — a magas dp_pct **negatív** P&L-t prediktál, de a scoring **pozitív bonust** ad
2. **Threshold irreális** — a 40%/60% küszöbök **soha nem fire-olnak**, mert a valós liquid ticker dark pool % sáv 7-15%

## A fix 3 részből áll

### 1. rész — Sign-flip a scoring-ban

A jelenlegi `dp_pct_bonus` és `dp_pct_high_bonus` paramétereket **negatív értékre** kell állítani:

```python
# defaults.py — TUNING (új)
"dp_pct_high_threshold": 18,     # új: 18% (volt: 60% — irreális)
"dark_pool_volume_threshold_pct": 12,   # új: 12% (volt: 40% — irreális)
"dp_pct_penalty": -10,           # új: ha dp_pct > 12% → -10 pont (volt: +10)
"dp_pct_high_penalty": -15,      # új: ha dp_pct > 18% → -15 pont (volt: +15)
```

**Indok**:
- A **threshold rekalibráció** (12%/18%) a tényleges dark pool % eloszlásra épül (a per-ticker UW direkt hívások 9-14%-ot mutatnak liquid tickerekre, így a 12% és 18% a Q3-Q4-Q5 quintile-eket fedi le)
- A **negatív penalty** a 60-trade Pearson -0,265\*\* alapján
- A **mérés egységessége** — a `dp_pct_score` mező a flow_score komponensben **negatív értéket** vehet fel

### 2. rész — Batch coverage javítása

A `UWBatchDarkPoolProvider` jelenleg ~3000 record-ot húz egy nap alatt (15 oldal × 200 limit), amelyet 5000+ ticker között kell elosztani. **Az átlagos lefedettség: 0-1 record/ticker**, ami statisztikailag **megbízhatatlan**.

**Két opció**:

**Opció A — Per-ticker fetch a Phase 4-ben**: minden Phase 4-be került ticker-re (azaz ~250-300 ticker naponta) **külön** UW dark pool API hívás. **Becsült API hívásszám: 250-300/nap** a UW Basic ($150/hó) tier-en belül. **Az UW Basic limitje** ellenőrzendő — a doksi szerint "?" (ismeretlen rate limit).

**Opció B — Batch coverage növelése**: a `UWBatchDarkPoolProvider` 15 oldal → 30-50 oldal-ra növelése. Ez **nagyobb** raw record halmazt ad (~6000-10000 record), amely **a top 500-1000 ticker-re** teljes lefedettséget ad. A többi ticker-re továbbra is 0-1 record marad, **DE** a Phase 4 jelöltek (top score-ú tickerek) **valószínűleg a top 500-ban vannak**.

**Ajánlott**: **Opció A** (per-ticker fetch). Ez **konzisztens** és **garantáltan teljes coverage-t** ad. A költség: ~250-300 új API hívás/nap, amely a UW Basic tier-ének **valószínűleg belül van** (a Polygon és FMP nagyságrendileg 1500+ és 4000+ napos hívásszámmal dolgozik).

**Megfontolandó**: a per-ticker fetch egy **csekken kívüli rate limit kockázat**. Egy gyors **prototípus tesztelés** (10-20 ticker × 1 nap) a deploy előtt indokolt.

### 3. rész — A scoring kódba integrálás

A `compute_flow_score()` (vagy hasonló) függvényben a `dp_pct_score` kalkulációt **invertálni**:

```python
# src/ifds/scoring/flow.py — VÁLTOZÁS

def _compute_dp_pct_score(dp_pct_value, config):
    """Compute dark pool % score component.

    Inverse signal: high dp_pct correlates with NEGATIVE P&L per share.
    Based on 60-trade audit (W17-W19): Pearson r = -0.265**, Spearman = -0.327**.
    """
    high_threshold = config.tuning["dp_pct_high_threshold"]      # 18%
    base_threshold = config.tuning["dark_pool_volume_threshold_pct"]  # 12%
    penalty = config.tuning["dp_pct_penalty"]                    # -10
    high_penalty = config.tuning["dp_pct_high_penalty"]          # -15

    if dp_pct_value is None or dp_pct_value < base_threshold:
        return 0
    elif dp_pct_value < high_threshold:
        return penalty  # -10
    else:
        return high_penalty  # -15
```

**Tesztek**:
- `test_dp_pct_score_below_threshold_returns_zero` (dp_pct = 8% → 0)
- `test_dp_pct_score_mid_range_returns_minus_10` (dp_pct = 14% → -10)
- `test_dp_pct_score_high_returns_minus_15` (dp_pct = 22% → -15)
- `test_dp_pct_score_handles_none_gracefully` (dp_pct = None → 0)
- `test_dp_pct_score_boundary_at_12pct_inclusive` (dp_pct = 12.0 → -10)
- `test_dp_pct_score_boundary_at_18pct_inclusive` (dp_pct = 18.0 → -15)

## A flow_score kompozíció hatása

A `dp_pct_score` egy 7-komponensű flow_score része. A maximum bonus eddig +15, az új penalty -15. Ez **megfordítja a komponens hatását**:

| Forgatókönyv | Régi flow_score hatás | Új flow_score hatás |
|---------------|------------------------|----------------------|
| dp_pct = 8% (alacsony) | 0 | 0 |
| dp_pct = 14% (közepes) | 0 (mert 40% alatt) | **-10** |
| dp_pct = 20% (magas) | 0 (mert 60% alatt) | **-15** |
| dp_pct = 65% (extrém) | +15 (HIBÁS) | -15 |

**A 60-trade audit alapján**: a high dp_pct tickerek **átlagosan -$163 spread-et** mutattak Q5-ben Q1-hez képest. **Egy -15 penalty** a flow_score-on a teljes scoring-ra **kb. 2-3 pont csökkenést** termel a magas dp_pct ticker-eken (mivel a flow súlya 60%, így 0,6 × 15 = 9 pont csökkenés).

## A kalibráció kvalifikálása

**Fontos**: a 60-trade minta **kis n statisztikailag**. A sign-flip **megerősített hipotézis**, NEM végleges igazság. A Pearson -0,265 (p=0,041) **érdemleges, de nem rendkívüli**. **Két potenciális bias**:

1. **Időablak-szűkítés** (W17-W19) — egyetlen Stagflation regime sub-mintája
2. **Survivorship bias** — csak a tényleges entry-re került ticker-ek

**Kvalifikációs lépés**: a deploy után **30 napi friss adat** (W20-W23, ~50-80 új trade) **megerősíti vagy cáfolja** a sign-flip-et. **Day 90 értékelés** (kb. 2026-06-05) **újraértékelés**.

## A deploy után

### Smoke teszt

```bash
# A teljes pytest suite lefuttatása (1553+ teszt)
.venv/bin/pytest

# Egy minta Phase 4-6 futtatás (smoke)
.venv/bin/python -m ifds run --phases 4-6 --paper-mode --smoke
```

### Integration smoke

A 16:15 cron-ban (a snapshot regresszió fix után!) **megfigyelni**:
- A `dp_pct_score` mező a Phase 4 snapshot-ban **NEM 0** több ticker esetén (a per-ticker fetch után)
- A scoring-ban a magas dp_pct tickerek **alacsonyabb kompozit pontszámot** kapnak
- A flow al-komponens dekompozíció (a snapshot fix után) **inverz Pearson r-t** mutat

### Commit

```
feat(scoring): dp_pct sign-flip + threshold recalibration

Audit (60 trades, W17-W19): Pearson r = -0.265** (per share, p=0.041),
Spearman = -0.327** (p=0.011). High dp_pct correlates with NEGATIVE P&L
per share, contrary to the previous bonus configuration.

Changes:
- dp_pct_high_threshold: 60 → 18 (realistic)
- dark_pool_volume_threshold_pct: 40 → 12 (realistic)
- dp_pct_bonus: +10 → -10 (sign-flipped)
- dp_pct_high_bonus: +15 → -15 (sign-flipped)
- Phase 4: per-ticker UW dark pool fetch (vs batch ~3000 records)

Tests: <N új unit teszt>
Audit: docs/analysis/dp-pct-retrospective-audit.md
```

## Kapcsolódó

- `docs/analysis/flow-decomposition.md` (a "0 dp_pct" finding eredete)
- `docs/analysis/dp-pct-retrospective-audit.md` (a 60-trade audit eredménye)
- `docs/tasks/2026-05-08-snapshot-regression-fix.md` (a snapshot bug, **ez után deploy-olandó**)
- `src/ifds/scoring/flow.py` (a `dp_pct_score` kalkuláció)
- `src/ifds/data/unusual_whales.py` (UW client, batch + per-ticker)
- `src/ifds/config/defaults.py` (a paraméterek)
