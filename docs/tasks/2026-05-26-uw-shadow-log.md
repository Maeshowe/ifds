# Task: UW Dark Pool / GEX Deactivation + Shadow Logging

**Status:** OPEN
**Priority:** P1 (Fázis 1 lezárás, [`04-risks §1.3`](../master-reference/04-risks-and-open-questions.md) — UW scoring instability)
**Created:** 2026-05-26 (W22 D1 hétfő)
**Updated:** 2026-05-26
**Owner:** Claude Code
**Estimated effort:** ~1.5–2h (scoring deaktiválás + shadow log infra + dual-write + tesztek)

**Source decision:** [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3.2 — Döntés [2]: "UW dark pool / GEX deactivation; shadow logging through Day 90".

**Depends on:**
- [`2026-05-19-ibkr-gateway-monitoring.md`](2026-05-19-ibkr-gateway-monitoring.md) (Fázis 1 stabilizáció)
- [`2026-05-19-earnings-exclusion-7to10.md`](2026-05-19-earnings-exclusion-7to10.md) (Fázis 1 deploy)
- [`2026-05-21-sec-10q-exclusion.md`](2026-05-21-sec-10q-exclusion.md) (Fázis 1 deploy)

**NEM depends on:** swing pivot scoring/sizing implementáció (Fázis 3). A shadow log az új és régi rendszer közötti **híd-mérés** — az új paper trading Day 1-Day 90 alatt **mindkettő** scoring kimenete egymás mellett mérhető.

---

## 1. A probléma — UW scoring instabilitás

A 2026-05-08 dark pool retrospektív audit ([`docs/analysis/dp-pct-retrospective-audit.md`](../analysis/dp-pct-retrospective-audit.md), 60 trade W17-W19) megerősítette:

| Metrika | Érték | p-érték |
|---|---|---|
| Pearson r (dp_pct ↔ P&L per share) | **-0.265** | 0.041 |
| Spearman ρ | **-0.327** | 0.011 |
| Q5 vs Q1 win rate | 25% vs 58% | — |
| Q5 - Q1 spread | **-$163** | — |

A jel **inverze** annak, amit a `defaults.py` 2026-05-08 előtti `dp_pct_bonus: +10` paraméter feltételezett. A sign-flip korrekció már megtörtént (`dp_pct_bonus: -10` 2026-05-08 deploy), DE:

1. A 60 napi minta **nem elég** a flow al-komponensek megbízható kalibrálásához (Bonferroni-korrigált küszöbök szerint csak a PCR és OTM-inverse szignifikáns, ld. [`strategic-review-mathematical.md`](../strategic-review/2026-05-08-strategic-review-mathematical.md) §4)
2. A swing pivot scoring (Fázis 3) **csak PCR + OTM-inverse**-et használ — a UW dark pool / GEX scoring-input **kikerül a multiplier chain-ből**
3. **DE** a UW adat továbbra is érdekes mint shadow signal — egy esetleges későbbi Bayesi rekalibrálás vagy regime-conditional reactivation alapjához

**A 2026-05-04 W17-i 5/6 negative dp_pct-magas ticker pattern** további érv: a sign-flip után is van regime-függő variabilitás. A shadow log a Day 90 értékelési pontig (~2026-08-26, W34) gyűjti az adatokat.

## 2. Mit jelent a "shadow logging"?

A jelenlegi pipeline:

```
Phase 5 GEX engine → M_GEX multiplier → Phase 6 sizing
Phase 4 scoring → dp_pct bonus → combined_score → Phase 6 sizing
```

Az új viselkedés:

```
Phase 5 GEX engine → log to state/uw_shadow/YYYY-MM-DD.json (NEM hat)
                  → M_GEX forced to 1.0 in Phase 6
Phase 4 scoring → dp_pct bonus = 0 (NEM hat)
                → raw dp_pct érték → state/uw_shadow/YYYY-MM-DD.json
```

A shadow log a Day 90 értékelési pontig **gyűjti az adatokat** anélkül, hogy a scoring kimenet függne tőle. A Fázis 3 (~jún 23) swing pivot deploy **NEM** változtat ezen — az új scoring **eleve** csak PCR + OTM-inverse, tehát a shadow log strukturálisan kompatibilis.

## 3. Architektúra

### 3.1. Új TUNING kapcsoló (`defaults.py`)

```python
# UW Dark Pool / GEX Deactivation (2026-05-26, Day 63 outcome §3.2)
"uw_dark_pool_scoring_enabled": False,  # Phase 4 dp_pct bonus 0-ra forcelt
"uw_gex_sizing_enabled": False,         # Phase 6 M_GEX 1.0-ra forcelt
"uw_shadow_logging_enabled": True,      # state/uw_shadow/*.json írás
"uw_shadow_dir": "state/uw_shadow",     # shadow log helye
```

A két scoring kapcsoló (`dp_pool_scoring_enabled`, `gex_sizing_enabled`) **függetlenül** kapcsolható — Fázis 3 deploy után esetleges A/B teszthez. A shadow log mindig fut, ha az alapadat (UW API hívás) megtörténik.

### 3.2. Phase 4 módosítás — `dp_pct` bonus deaktiválás

A `src/ifds/phases/phase4_stocks.py`-ban:

```python
# Régi:
if dp_pct > config["dp_pct_high_threshold"]:
    score += config["dp_pct_high_bonus"]  # -15
elif dp_pct > 12:
    score += config["dp_pct_bonus"]  # -10

# Új:
if config["uw_dark_pool_scoring_enabled"]:
    if dp_pct > config["dp_pct_high_threshold"]:
        score += config["dp_pct_high_bonus"]
    elif dp_pct > 12:
        score += config["dp_pct_bonus"]
# A raw dp_pct értéket a shadow log megőrzi (lásd 3.4)
```

### 3.3. Phase 6 módosítás — `M_GEX` 1.0-ra forcelt

A `src/ifds/phases/phase6_sizing.py`-ban:

```python
# Régi:
m_gex = compute_gex_multiplier(phase5_result.gex_regime, config)
# pozitív 1.0, negatív 0.5, magas-vol 0.6

# Új:
if config["uw_gex_sizing_enabled"]:
    m_gex = compute_gex_multiplier(phase5_result.gex_regime, config)
else:
    m_gex = 1.0  # Shadow mode — GEX nem hat a sizing-ra
# A nyers gex_regime és gex_value a shadow log megőrzi
```

### 3.4. Shadow log infrastruktúra — `src/ifds/data/uw_shadow.py` (új, ~60 sor)

```python
"""UW Dark Pool / GEX Shadow Logger.

A scoring/sizing nem használja, de Day 90-ig naponta logoljuk a UW adatokat
egy esetleges későbbi Bayesi rekalibráláshoz vagy regime-conditional reactivation-höz.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

def write_shadow_snapshot(
    shadow_dir: Path,
    trading_date: str,  # YYYY-MM-DD
    snapshot: dict,
) -> Path:
    """Daily shadow snapshot mentése.

    Schema:
    {
      "date": "2026-05-26",
      "captured_at": "2026-05-26T22:35:12Z",
      "tickers": {
        "AAPL": {
          "dp_pct": 14.2,
          "dp_score_would_have_been": -10,  # Mit adott volna ha aktív
          "gex_regime": "gamma_positive",
          "gex_value": 1.23e9,
          "m_gex_would_have_been": 1.0,    # Mit adott volna ha aktív
          "phase4_passed": True,
          "combined_score": 67.3            # A tényleges scoring (shadow nélkül)
        },
        ...
      }
    }
    """
    shadow_dir.mkdir(parents=True, exist_ok=True)
    path = shadow_dir / f"{trading_date}.json"
    snapshot["captured_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(snapshot, indent=2))
    return path


def load_shadow_snapshot(shadow_dir: Path, trading_date: str) -> dict | None:
    """Egy adott napi shadow snapshot beolvasása. None ha nincs."""
    path = shadow_dir / f"{trading_date}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())
```

### 3.5. Pipeline integráció

A `src/ifds/runner.py`-ben (vagy ahol a Phase 4 és Phase 6 output összeáll):

```python
if config["uw_shadow_logging_enabled"]:
    shadow_snapshot = build_shadow_snapshot(
        phase4_result=phase4_result,
        phase5_result=phase5_result,
        phase6_result=phase6_result,
        config=config,
    )
    write_shadow_snapshot(
        shadow_dir=Path(config["uw_shadow_dir"]),
        trading_date=run_date_str,
        snapshot=shadow_snapshot,
    )
```

A `build_shadow_snapshot` egy helper, amely a 3.4 schema szerint összegyűjti minden Phase 4 passed ticker (vagyis a `combined_score >= 70`) raw UW field-jét + a "what-if scoring" értékét.

### 3.6. Daily metrics integráció (opcionális, javasolt)

A `scripts/paper_trading/daily_metrics.py`-be új mezők:

```python
"uw_shadow_summary": {
    "snapshot_path": "state/uw_shadow/2026-05-26.json",
    "tickers_logged": 154,
    "avg_dp_pct": 8.7,
    "avg_dp_pct_would_have_penalty_count": 23,  # Hány tickeren lett volna dp_pct penalty
    "gex_regime_distribution": {"gamma_positive": 89, "gamma_negative": 31, "neutral": 34},
    "m_gex_avg_would_have_been": 0.87,  # Az átlag m_gex ha aktív lenne
},
```

Ez **W22 péntek heti review-ban** látja Tamás: "ha aktív lett volna, hány tickert érintett volna".

## 4. Implementáció lépésekben

1. **TUNING kapcsolók (`defaults.py`)** — 4 új paraméter (~5 min)
2. **Phase 4 dp_pct guard** — `if uw_dark_pool_scoring_enabled:` köré (~10 min)
3. **Phase 6 M_GEX guard** — ugyanaz a minta (~10 min)
4. **`uw_shadow.py` modul** — write/load helperek (~20 min)
5. **`build_shadow_snapshot` helper** a runner-ben (~20 min)
6. **daily_metrics.py shadow summary** (~15 min)
7. **Tesztek (~30 min)**:
   - `test_phase4_dp_pct_bonus_disabled_when_scoring_off`
   - `test_phase6_m_gex_forced_to_one_when_sizing_off`
   - `test_shadow_snapshot_written_per_trading_day`
   - `test_shadow_snapshot_schema_complete`
   - `test_shadow_snapshot_skipped_when_logging_off`
   - `test_daily_metrics_includes_shadow_summary`
8. **Smoke test (~10 min)**: 1 mock napi futás, shadow JSON ellenőrzés
9. **Commit + push (~5 min)**

**Összesen: ~1.5–2h.**

## 5. Validáció (Tamás közreműködésével)

A deploy után (W22 D1 hétfő, máj 26) a következő:

```bash
# Mac Mini-n az aznapi 16:15-i cron futás után
ls -la state/uw_shadow/
cat state/uw_shadow/$(date +%Y-%m-%d).json | python -m json.tool | head -40

# Várt finding: ~150-200 ticker logolva, mindegyiknél raw dp_pct + would_have értékek
```

A daily P&L riportban (`pt_eod.log`):
- A `combined_score` értékek **NEM** tartalmazzák a dp_pct bonusst
- Az `M_GEX` mindenhol 1.0
- A Telegram daily report-ban szerepelhet egy új sor: "UW shadow: 154 tickers logged, 23 would-have-been penalty"

## 6. Day 90 értékelési pont (~2026-08-26, W34)

A shadow log Day 1–Day 90 alatt **~63 napi snapshot**-ot termel. A Day 90 értékelés:

| Kérdés | Válasz módszer |
|---|---|
| A dp_pct sign-flip a 90 napi mintán is konzisztens? | Pearson r újraszámítása a shadow + new paper trading P&L-ből |
| A GEX regime hatása szignifikáns marad? | M_GEX would-have vs tényleges P&L korreláció |
| Van regime-conditional pattern? (pl. magas VIX-en eltérő dp_pct hatás) | Conditional Pearson per VIX quintile |

Ha a 90 napi shadow audit **megerősíti** a flip-et, a `dp_pct` és `M_GEX` reactivation lehetséges (Fázis 4+ scope, NEM része ennek a tasknak). Ha **nem erősíti meg**, a UW dark pool / GEX végleg shadow marad.

## 7. Out of scope (explicit)

- **A UW API hívások deaktiválása** — a Phase 5 GEX engine **fut**, mert a shadow log adathoz kell. A UW costs ($50/hó) ezért NEM csökken Fázis 1-ben — a Day 90 utáni döntés alapján esetleg.
- **Visszamenőleges shadow log** a Fázis 1 előtti időszakra — a meglévő `state/phase4_snapshots/` és `pt_events_*.jsonl` retrospektíven feldolgozható, de **külön task** (alacsony prioritás, mert a 60 napi audit már megvan).
- **A `crowdedness_shadow_log`** ([`docs/tasks/2026-03-26-ewma-shadow-log.md`](2026-03-26-ewma-shadow-log.md)-féle) **megőrzendő** változatlanul — a UW shadow log a kettős scope-ú GEX + dp_pct adatra fókuszál, a crowdedness más feature.
- **Regime-conditional reactivation Fázis 1-ben** — túl korai döntés, Day 90 értékelési pont előtt nincs adat.

## 8. Commit message draft

```
feat(scoring): UW dark pool / GEX deactivation + shadow logging (Day 63 §3.2)

Day 63 outcome decision [2]: UW dark pool / GEX scoring deactivated,
but underlying data continues to be collected as shadow log through
Day 90 (~2026-08-26) for retroactive Bayesian recalibration analysis.

- Phase 4: dp_pct bonus gated by uw_dark_pool_scoring_enabled (default False)
- Phase 6: M_GEX forced to 1.0 unless uw_gex_sizing_enabled (default False)
- New module src/ifds/data/uw_shadow.py: daily snapshot writer
- Runner integration: post-Phase 6 shadow snapshot to state/uw_shadow/YYYY-MM-DD.json
- daily_metrics.py: new shadow_summary field

The change is consistent with the swing pivot scoring (Phase 3, ~2026-06-23)
which uses only PCR + OTM-inverse — UW dark pool / GEX have no role in the
multiplier chain. This task formalizes that decoupling and preserves the
raw data for future analysis.

Refs: docs/decisions/2026-05-14-day63-decision-outcome.md §3.2
      docs/analysis/dp-pct-retrospective-audit.md
```

## 9. Kapcsolódó

- `docs/decisions/2026-05-14-day63-decision-outcome.md` §3.2
- `docs/analysis/dp-pct-retrospective-audit.md` (60-trade audit, sign-flip dokumentáció)
- `docs/strategic-review/2026-05-08-strategic-review-mathematical.md` §4 (Bonferroni-minimum scoring)
- `docs/master-reference/04-risks-and-open-questions.md` §1.3
- `docs/tasks/2026-03-26-ewma-shadow-log.md` (különálló shadow log, megőrzendő)
- `docs/design/swing-pivot-architecture.md` §2.1 (Decision 2: UW shadow)
