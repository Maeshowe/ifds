# BC23 — Scoring & Exit Redesign

**Státusz:** APPROVED
**Dátum:** 2026-04-11
**Prioritás:** P0 — a scoring validáció bizonyította, hogy a jelenlegi rendszer nem termel alpha-t
**Becsült effort:** ~8-10 óra CC (hétvégi sprint)
**Trigger:** Scoring Validation Report (docs/analysis/scoring-validation.md) — r=+0.046, p=0.46, inverz quintilis minta

---

## Motiváció

40 nap paper trading, 252 trade, -$1,928 kumulatív P&L. A scoring validáció megállapította:

1. A combined score NEM korrelál a P&L-lel (r=+0.046, p=0.46)
2. A legmagasabb score-ú tickerek a LEGROSSZABBUL teljesítenek (Q5 vs Q1: -$22.16/trade)
3. A flow komponens gyengén szignifikáns (r=+0.136, p=0.039), a funda és tech nem
4. 75% MOC exit — a bracket rendszer nem termel értéket
5. TP1 hit rate 10%, TP2 hit rate 0.4% — a risk:reward fordított (0.5:1)
6. A freshness bonus (×1.5) a legkárosabb elem — a FRESH tickerek a legrosszabbul teljesítenek
7. Napi 8 pozíció × ~$27 commission = $8,400/év fix költség (8.4% éves drag)

## Alapelvek

- **Egyszerűsítés:** kevesebb komponens, kevesebb zaj, kevesebb trade
- **Flow-first:** az egyetlen gyengén prediktív komponens a flow — erre építünk
- **Költségcsökkentés:** kevesebb pozíció = kevesebb commission + slippage
- **Adatgyűjtés megmarad:** shadow módok továbbra is gyűjtenek adatot

---

## Változások — 13 pont, 4 fázisban

### Fázis 1: Scoring átírás (szombat este)

| # | Változás | Fájl | Régi | Új |
|---|---------|------|------|-----|
| 1 | Freshness bonus kikapcsolás | defaults.py CORE | 1.5 | 1.0 |
| 2 | RS vs SPY bonus csökkentés | defaults.py TUNING | 40 | 15 |
| 3 | Scoring súlyok átrendezés | defaults.py CORE | flow=0.40 funda=0.30 tech=0.30 | flow=0.60 funda=0.10 tech=0.30 |

**Validáció:** scoring_validation.py újrafuttatás a historikus adaton. A Q5-Q1 spread csökkenését és a flow korreláció javulását várjuk.

### Fázis 2: TP/SL és exit redesign (vasárnap délelőtt)

| # | Változás | Fájl | Régi | Új |
|---|---------|------|------|-----|
| 4 | TP1 emelés | defaults.py CORE | 0.75×ATR | 1.5×ATR |
| 5 | TP2 csökkentés | defaults.py CORE | 3.0×ATR | 2.0×ATR |
| 6 | Bracket split megfordítás | phase6_sizing.py vagy submit_orders.py | 33/67 (TP1/TP2) | 50/50 |
| 10 | Call Wall TP1 kikapcsolás | phase6_sizing.py `_calculate_position()` | call_wall override | mindig ATR-alapú TP1 |

A #10 implementáció:
```python
# JELENLEGI:
if gex.call_wall > 0 and gex.call_wall > entry:
    tp1 = gex.call_wall
else:
    tp1 = entry + tp1_atr

# ÚJ:
tp1 = entry + tp1_atr  # Mindig ATR-alapú
```

### Fázis 3: Pozíciószám és timing (vasárnap délután)

| # | Változás | Fájl | Régi | Új |
|---|---------|------|------|-----|
| 7 | Max positions: dinamikus, max 5 | phase6_sizing.py `_apply_position_limits()` | fix 8 | min(5, len(candidates score > dynamic_threshold)) |
| 8 | Submit idő tolás | crontab | 15:45 CEST (09:45 EDT) | 16:15 CEST (10:15 EDT) |

A #7 implementáció:
```python
# A max_positions ne fix 8, hanem a jelöltek számától függjön
# Ha csak 3 ticker éri el a küszöböt → 3 pozíció
# Ha 0 → "No actionable positions" (nem kereskedünk)
# Hard cap: 5 (nem 8)
max_positions = min(5, len([c for c in candidates if c.combined_score >= score_threshold]))
```

A `score_threshold` legyen a config-ban: `"dynamic_position_score_threshold": 85` — csak a 85+ score-ú tickerek kapnak pozíciót. Ha senki nem éri el → nem kereskedünk.

A #8 crontab módosítás:
```
# RÉGI:
45 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && ./scripts/deploy_intraday.sh
# ÚJ:
15 16 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && ./scripts/deploy_intraday.sh
```

Érintett scriptek időzítése:
- `check_gateway.py`: 15:30 → **16:00** (15 perccel a submit előtt)
- `pt_monitor.py`: `*/5 16-21` → marad (16:15 utáni első ciklus 16:20-kor, rendben)
- `close_positions.py`: 21:40 → marad (a swing exit logika nem változik)

### Fázis 4: Egyszerűsítés és cleanup (vasárnap este)

| # | Változás | Fájl | Régi | Új |
|---|---------|------|------|-----|
| 9 | MMS sizing kikapcsolás | defaults.py TUNING | mms_enabled: True | mms_enabled: False |
| 11 | VWAP guard: REDUCE eltávolítás | vwap.py | REJECT + REDUCE (50%) | csak REJECT |
| 12 | Multiplier chain egyszerűsítés | phase6_sizing.py + defaults.py | 7 multiplier | 3 aktív (M_vix, M_gex, M_target) |

A #12 implementáció — a `_calculate_multiplier_total()` függvényben:
```python
# A nem-prediktív multiplierek fix 1.0-ra
m_flow = 1.0      # volt: conditional 1.25
m_insider = 1.0   # volt: 0.75-1.25
m_funda = 1.0     # volt: conditional 0.50
m_utility = 1.0   # volt: score-based 1.0-1.3

# Aktív marad:
m_vix = macro.vix_multiplier          # piaci volatilitás védelem
m_gex = gex.gex_multiplier            # gamma exposure regime
m_target = _calculate_target_multiplier(...)  # analyst target protection

M_total = clamp(m_vix × m_gex × m_target, 0.25, 2.0)
```

### Elemzés (vasárnap — párhuzamosan)

| # | Változás | Fájl |
|---|---------|------|
| 13 | Flow al-komponens dekompozíció | scripts/analysis/flow_decomposition.py |

A flow_score jelenleg 7 al-komponenst összegez egyetlen számba. Az elemzés megmondja melyik prediktív:
- `buy_pressure_score` → P&L korreláció
- `dp_pct_score` → P&L korreláció
- `pcr_score` → P&L korreláció
- pure `rvol_score` (csak RVOL, squat nélkül) → P&L korreláció
- `block_trade_score` → P&L korreláció
- `otm_score` → P&L korreláció
- `squat_bar_bonus` → P&L korreláció

Kimenet: `docs/analysis/flow-decomposition.md`
Ez informálja a jövő heti flow súly finomhangolást.

---

## Nem változik

- Phase 0 (Diagnostics) — változatlan
- Phase 1 (BMI Regime) — változatlan
- Phase 2 (Universe Building) — változatlan
- Phase 3 (Sector Rotation) — változatlan
- Phase 5 (GEX) — a GEX regime multiplier marad, az MMS feature store továbbra is gyűjt adatot
- API-k — mind a 4 marad (Polygon, FMP, UW, FRED). Az FMP híváscsökkentés (financial_growth + inst_ownership skip) jövő heti task
- Swing exit logika (BC20A) — változatlan (Scenario A trail, Scenario B loss exit/trail)
- Shadow módok — crowdedness, yield curve, skip day továbbra is gyűjtenek adatot
- EWMA smoothing — marad aktív (ez stabilizálja a score-okat)
- Danger zone filter — marad aktív (key_metrics kell hozzá)
- Sector VETO — marad aktív
- BMI Momentum Guard — marad aktív
- Circuit breaker — marad aktív

---

## Kockázatok

| Kockázat | Mitigáció |
|----------|-----------|
| Túl sok változás egyszerre → nehéz azonosítani mi segített | A scoring validáció újrafuttatás a historikus adaton megmutatja a scoring változás hatását. A TP/SL és pozíciószám változás hatása csak live-ban mérhető. |
| A dynamic_position_score_threshold (85) túl magas → 0 pozíció napokig | Shadow: az első héten figyeljük hány ticker éri el a 85-öt. Ha <3 átlag → küszöb csökkentés 80-ra. |
| A TP1 1.5×ATR túl magas → TP1 hit rate tovább csökken | Az 1:1 R:R alapvető elvárás. Ha a TP1 hit rate <5% → TP1 csökkentés 1.25×ATR-re. |
| MKT fill + TP1 1.5×ATR → az instant-fill probléma enyhül de nem szűnik meg | A 16:15 submit (opening range után) stabilabb fill árakat ad. |

## Rollback

Minden változás paraméter vagy lokalizált kódmódosítás. Ha a hétfői futás hibás:
- Paraméterek: `git revert` egyetlen commit
- Crontab: `15 16` → `45 15` visszaállítás

## Siker kritériumok (2 hét live után)

1. A scoring validáció újrafuttatásakor a Q5-Q1 spread közelebb 0-hoz (nem inverz)
2. TP1 hit rate stabil (>5%) és a TP1 P&L pozitív (1:1 R:R)
3. Napi pozíciószám átlag 3-5 (nem fix 8)
4. Commission csökkenés ~40%
5. A kumulatív P&L trend javul (nem feltétlenül pozitív — a piac bearish)
