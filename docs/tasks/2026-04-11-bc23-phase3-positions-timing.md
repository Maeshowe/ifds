# BC23 Phase 3 — Pozíciószám és Timing

**Status:** DONE
**Updated:** 2026-04-11
**Priority:** P0
**Effort:** ~2.5h CC
**Depends on:** BC23 Phase 1, Phase 2
**Ref:** docs/planning/bc23-scoring-exit-redesign.md

---

## Változások

### 3.1 Dinamikus pozíciószám (max 5)

**Fájl:** `src/ifds/phases/phase6_sizing.py` → `run_phase6()` és `_apply_position_limits()`
**Fájl:** `src/ifds/config/defaults.py` → RUNTIME és TUNING

Config változások:
```python
# defaults.py RUNTIME:
"max_positions": 5,                    # volt: 8

# defaults.py TUNING (ÚJ paraméter):
"dynamic_position_score_threshold": 85,  # csak 85+ score-ú tickerek kapnak pozíciót
```

Implementáció a `_apply_position_limits()` elején:
```python
# Dinamikus max_positions: csak a score threshold feletti tickerek
score_threshold = config.tuning.get("dynamic_position_score_threshold", 85)
qualified = [p for p in positions if p.combined_score >= score_threshold]
effective_max = min(config.runtime["max_positions"], len(qualified))

if effective_max == 0:
    logger.log(EventType.PHASE_DIAGNOSTIC, Severity.WARNING, phase=6,
               message=f"[DYNAMIC] No tickers above score threshold {score_threshold} "
                       f"— no positions today")
    return [], {"sector": 0, "position": len(positions), "risk": 0,
                "exposure": 0, "correlation": 0}

# A positions lista már score szerint rendezett (desc) — csak qualified-ot engedjük
positions = [p for p in positions if p.combined_score >= score_threshold]
max_positions = effective_max
```

Logolás — Telegram-ben is legyen látható:
```
[DYNAMIC] 3/8 tickers above threshold 85 — max positions today: 3
```
vagy:
```
[DYNAMIC] No tickers above threshold 85 — no positions today
```

### 3.2 Szektorcsoport-limitek rescale (8→5 pozícióhoz)

```python
# defaults.py TUNING:
"sector_group_max_cyclical": 3,    # volt: 5
"sector_group_max_defensive": 2,   # volt: 4
"sector_group_max_financial": 2,   # volt: 3
"sector_group_max_commodity": 2,   # volt: 3
"max_positions_per_sector": 2,     # volt: 3
```

### 3.3 Submit idő tolás: 15:45 → 16:15 CEST

**Fájl:** crontab (Mac Mini)

```bash
# RÉGI:
45 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && ./scripts/deploy_intraday.sh
30 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/check_gateway.py

# ÚJ:
15 16 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && ./scripts/deploy_intraday.sh
0  16 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/check_gateway.py
```

A monitor crontab (`*/5 16-21`) NEM változik — az első monitor ciklus 16:20-kor fut, ami pont a submit (16:15) után 5 perccel van.

**FONTOS:** A crontab módosítás NEM CC task — Tamás csinálja a Mac Mini-n. CC csak dokumentálja a szükséges változást.

Készíts egy `docs/deploy/bc23-crontab-changes.md` fájlt a pontos módosításokkal.

### 3.4 Risk recalibráció 5 pozícióhoz

```python
# defaults.py RUNTIME:
"risk_per_trade_pct": 0.7,          # volt: 0.5 — 5 × 0.7% = 3.5% total risk (volt: 8 × 0.5% = 4.0%)
"max_gross_exposure": 80_000,       # volt: 100_000 — 5 pozíció, max ~$16k/pozíció
"max_single_ticker_exposure": 20_000,  # marad
```

A per-trade risk emelkedik (0.5% → 0.7%), de a total risk csökken (4.0% → 3.5%) mert kevesebb pozíció van. Az egyes pozíciók nagyobbak → a TP1 és SL P&L is nagyobb → az edge (ha van) jobban érvényesül.

## Tesztek

- `test_dynamic_positions_threshold` — 85 fölötti tickerek száma = max positions
- `test_dynamic_positions_zero` — ha nincs 85+ score → üres kimenet, nem hiba
- `test_dynamic_positions_cap_5` — ha 10 ticker 85+ → max 5
- `test_sector_limits_rescaled` — új szektorcsoport-limitek érvényesülnek
- Meglévő position limit tesztek frissítése max_positions=5-re

## Commit

```
feat(sizing): BC23 Phase 3 — dynamic position count, timing shift

- max_positions: 8 → 5 (hard cap)
- dynamic_position_score_threshold: 85 (only quality setups get capital)
- risk_per_trade_pct: 0.5% → 0.7% (fewer but larger positions)
- sector group limits rescaled for 5-position portfolio
- submit time: 15:45 → 16:15 CEST (10:15 EDT, after opening range)
- crontab changes documented in docs/deploy/bc23-crontab-changes.md

252 trades over 40 days at fixed 8 positions/day generated -$1,928 with
$1,080+ in commissions alone (8.4% annual drag). Reducing to 3-5 quality
positions cuts friction by ~40% and eliminates forced low-conviction entries.
```
