# BC23 Phase 2 — TP/SL és Exit Redesign

**Status:** DONE
**Updated:** 2026-04-11
**Priority:** P0
**Effort:** ~2h CC
**Depends on:** BC23 Phase 1
**Ref:** docs/planning/bc23-scoring-exit-redesign.md

---

## Változások

### 2.1 TP1 emelés

**Fájl:** `src/ifds/config/defaults.py` → CORE

```python
# RÉGI:
"tp1_atr_multiple": 0.75,
# ÚJ:
"tp1_atr_multiple": 1.5,
```

Indoklás: a régi 0.75×ATR TP1 + 1.5×ATR SL = 0.5:1 R:R. Az új 1.5×ATR TP1 = 1:1 R:R, ami a minimum elvárás. A TP1 hit rate csökkenni fog (10% → ~5-7%), de a nyereség/hit duplázódik.

### 2.2 TP2 csökkentés

**Fájl:** `src/ifds/config/defaults.py` → CORE

```python
# RÉGI:
"tp2_atr_multiple": 3.0,
# ÚJ:
"tp2_atr_multiple": 2.0,
```

Indoklás: a 3.0×ATR TP2 40 nap alatt 1× ütött be (0.4%). A 2.0×ATR reálisabb swing target.

### 2.3 Bracket split megfordítás

A bracket A (TP1) és B (TP2) pozíciófelosztás:

**Jelenlegi:** `qty_tp1 = floor(qty / 3)`, `qty_tp2 = qty - qty_tp1` → 33/67 split
**Új:** `qty_tp1 = floor(qty / 2)`, `qty_tp2 = qty - qty_tp1` → 50/50 split

Keresendő fájl(ok): a split logika a `phase6_sizing.py`-ban vagy a `submit_orders.py`-ban van. Keresd:
```bash
grep -rn "qty_tp1\|qty_tp2\|scale_out_pct\|floor.*3" src/ifds/phases/phase6_sizing.py scripts/paper_trading/submit_orders.py
```

A `scale_out_pct` config paraméter valószínűleg a split arányt adja:
```python
# RÉGI:
"scale_out_pct": 0.33,
# ÚJ:
"scale_out_pct": 0.50,
```

### 2.4 Call Wall TP1 kikapcsolás

**Fájl:** `src/ifds/phases/phase6_sizing.py` → `_calculate_position()` függvény

```python
# RÉGI (~sor 420-430):
if gex.call_wall > 0 and gex.call_wall > entry:
    tp1 = gex.call_wall
else:
    tp1 = entry + tp1_atr

# ÚJ:
tp1 = entry + tp1_atr  # Mindig ATR-alapú, konzisztens
```

A call_wall GEX adat tegnap esti snapshot — a mai reggeli piacon irreleváns. A MKT entry-vel kombinálva instant negatív TP1 fill-eket okoz (NSA, SBRA esetek ápr 8-9).

A `put_wall` TP1-et is ki kell kapcsolni (SHORT ág):
```python
# RÉGI:
if gex.put_wall > 0 and gex.put_wall < entry:
    tp1 = gex.put_wall
else:
    tp1 = entry - tp1_atr

# ÚJ:
tp1 = entry - tp1_atr
```

## Tesztek

- Meglévő TP/SL unit tesztek frissítése az új ATR szorzókkal
- Új teszt: `test_tp1_always_atr_based` — call_wall értéktől függetlenül TP1 = entry + tp1_atr
- Új teszt: `test_bracket_split_50_50` — qty_tp1 ≈ qty_tp2
- Új teszt: `test_tp1_risk_reward_ratio` — TP1 distance >= SL distance (1:1 R:R)

## Commit

```
feat(exit): BC23 Phase 2 — TP/SL redesign for 1:1 R:R

- tp1_atr_multiple: 0.75 → 1.5 (risk:reward 0.5:1 → 1:1)
- tp2_atr_multiple: 3.0 → 2.0 (reachable swing target)
- scale_out_pct: 0.33 → 0.50 (equal bracket split)
- Call Wall TP1 override REMOVED — always ATR-based

40-day data: TP1 hit rate 10% at 0.75×ATR, TP2 hit rate 0.4% at 3×ATR.
The old TP1 was too tight (instant fill on MKT slippage) and the old TP2
was unreachable (1 hit in 252 trades). Call wall TP1 used stale overnight
GEX data, causing negative P&L on instant fills (NSA, SBRA Apr 8-9).
```
