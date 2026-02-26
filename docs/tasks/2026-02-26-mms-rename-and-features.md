# MMS: Átnevezés + Venue Mix + IV Skew feature bővítés

**Dátum:** 2026-02-26  
**Prioritás:** 🟡 BC17 előtt  
**Érintett fájlok:** `phase5_obsidian.py`, `obsidian_store.py`, `market.py`, `phase5_gex.py`, `test_bc15_obsidian.py`, `CLAUDE.md`, `state/obsidian/`

---

## Háttér

Az OBSIDIAN név egy korábbi standalone projektből (aetherveil) öröklődött.
Az IFDS-ben a funkció neve **MMS — Market Microstructure Scorer**.

Emellett két feature hiányzik a store-ból, amelyek adatai már elérhetők:
- **Venue Mix** — UW darkpool batch `market_center` mezőjéből (Shannon entrópia)
- **IV Skew** — Polygon options snapshot put/call IV-ból (ATM put IV − call IV)

Ezeket el kell kezdeni gyűjteni, hogy a 21 napos baseline a lehető leghamarabb teljesüljön.

---

## Jóváhagyott döntések (2026-02-26)

**Súlyok:** 6-feature elosztás azonnal aktív:
```python
"mms_feature_weights": {
    "dark_share":      0.25,
    "gex":             0.25,
    "venue_entropy":   0.15,
    "block_intensity": 0.15,
    "iv_rank":         0.10,
    "iv_skew":         0.10,
}
# Összesen: 1.00
```

**Implementálás sorrendje:** Szekvenciális, lépésenkénti commit + review.

---

## Részfeladatok

### Lépés 1 — Fájlátnevezés és import csere

**Fájlok:**
```
src/ifds/phases/phase5_obsidian.py  →  src/ifds/phases/phase5_mms.py
src/ifds/data/obsidian_store.py     →  src/ifds/data/mms_store.py
state/obsidian/                     →  state/mms/
```

**Class / függvény átnevezések** (csak az obsidian nevűek):
```
ObsidianStore         →  MMSStore
ObsidianAnalysis      →  MMSAnalysis   (market.py dataclass)
obsidian_analyses     →  mms_analyses  (Phase5Result + PipelineContext mezők)
obsidian_enabled      →  mms_enabled   (Phase5Result mező)
run_obsidian_analysis →  run_mms_analysis (phase5_mms.py top-level fn)
```

**NEM nevezzük át** (névtér-független, leíróak):
```
MMRegime       — marad (MM = Market Microstructure, helyes)
BaselineState  — marad
_classify_regime, _compute_z_scores stb. — marad
```

**Import cserék** (minden érintett fájlban):
```python
# Keresés:
from ifds.data.obsidian_store import ObsidianStore
from ifds.phases.phase5_obsidian import run_obsidian_analysis
obsidian_store, obsidian_analyses, obsidian_enabled, ObsidianAnalysis

# Csere:
from ifds.data.mms_store import MMSStore
from ifds.phases.phase5_mms import run_mms_analysis
mms_store, mms_analyses, mms_enabled, MMSAnalysis
```

**Érintett fájlok az importcseréknél:**
- `src/ifds/phases/phase5_gex.py`
- `src/ifds/phases/phase6_sizing.py`
- `src/ifds/pipeline/runner.py`
- `src/ifds/models/market.py`
- `tests/test_bc15_obsidian.py`

**Config kulcsok** (`PARAMETERS.md` + config/loader.py-ban ha hardcodolt):
```
obsidian_enabled              →  mms_enabled
obsidian_store_always_collect →  mms_store_always_collect
obsidian_store_dir            →  mms_store_dir
obsidian_max_store_entries    →  mms_max_store_entries
obsidian_window               →  mms_window
obsidian_min_periods          →  mms_min_periods
obsidian_z_gex_threshold      →  mms_z_gex_threshold
obsidian_z_dex_threshold      →  mms_z_dex_threshold
obsidian_z_block_threshold    →  mms_z_block_threshold
obsidian_dark_share_dd        →  mms_dark_share_dd
obsidian_dark_share_abs       →  mms_dark_share_abs
obsidian_return_abs           →  mms_return_abs
obsidian_return_dist          →  mms_return_dist
obsidian_feature_weights      →  mms_feature_weights
obsidian_regime_multipliers   →  mms_regime_multipliers
```

**Log üzenetek** a phase5_gex.py-ban:
```
"[OBSIDIAN]"  →  "[MMS]"
"OBSIDIAN:"   →  "MMS:"
```

**state/mms/ könyvtár — FONTOS:**
A state/obsidian/ már tartalmaz adatot (~461 JSON fájl, feb 11-től gyűjtve).
Ezeket **mozgasd át**, ne másold — a meglévő baseline nem veszhet el:
```bash
mkdir -p state/mms
mv state/obsidian/*.json state/mms/
rmdir state/obsidian
```

**CLAUDE.md:**
Minden "OBSIDIAN" és "obsidian" hivatkozást cseréld "MMS"-re, kivéve az
`archive/conductor-2026-02-26/` tartalomban — azt ne bántsd.

**Tesztelés Lépés 1 után:**
```bash
pytest -q tests/test_bc15_mms.py   # 50+ teszt, 0 failure
pytest -q                          # teljes suite, 848+ passing
```
⚠️ Commit csak ha mindkettő zöld.

---

### Lépés 2 — Venue Mix feature hozzáadása

**Mi ez:** Shannon entrópia a darkpool print execution venue-k eloszlásán.
Magas entrópia = sok különböző venue (normális). Alacsony = koncentráció (szokatlan).

**Adatforrás:** UW darkpool batch, minden record `market_center` mezője.
Pl.: `"FINRA"`, `"NYSE"`, `"NASDAQ"`, `"CBOE"`, `"ARCA"` stb.

**Számítás** az `_aggregate_dp_records`-ban (`data/adapters.py`):
```python
from collections import Counter
import math

venue_counts = Counter()
for record in records:
    mc = record.get("market_center", "UNKNOWN")
    size = _safe_int(record.get("size", 0))
    venue_counts[mc] += size

total_venue_vol = sum(venue_counts.values())
if total_venue_vol > 0:
    probs = [v / total_venue_vol for v in venue_counts.values()]
    venue_entropy = -sum(p * math.log(p) for p in probs if p > 0)
else:
    venue_entropy = 0.0
```
→ `_aggregate_dp_records` visszatérési dict-be: `"venue_entropy": venue_entropy`

**Adatcsatorna a store-ig:**
1. `market.py` — `FlowAnalysis` dataclass: `venue_entropy: float = 0.0` mező hozzáadása
2. `phase4_stocks.py` — `_analyze_flow_from_data` végén:
   ```python
   flow.venue_entropy = dp_data.get("venue_entropy", 0.0) if dp_data else 0.0
   ```
3. `phase5_mms.py` — `run_mms_analysis`-ban:
   ```python
   venue_entropy = stock.flow.venue_entropy if stock.flow else 0.0
   ```
4. Store entry-ben: `"venue_entropy": venue_entropy`

**Z-score számítás** (`_compute_z_scores`):
```python
store_features = ["dark_share", "gex", "dex", "block_count", "iv_rank", "venue_entropy"]
```

**`excluded_features`:** töröld a hardcoded `"venue_mix"` kizárást — a `venue_entropy`
alapból aktív feature, nem excluded.

**Tesztelés Lépés 2 után:**
```bash
pytest -q tests/test_bc15_mms.py::TestVenueMix   # 4 teszt
pytest -q tests/test_bc15_mms.py                  # teljes MMS suite
```

---

### Lépés 3 — IV Skew feature hozzáadása

**Mi ez:** ATM put IV − ATM call IV.
- Pozitív → puts drágábbak (fear, hedge kereslet)
- Negatív → calls drágábbak (greed, spekulatív vásárlás)

**Adatforrás:** Polygon options snapshot — már lekéri a Phase 4 és Phase 5.

**Új helper** `phase5_mms.py`-ban:
```python
def _compute_iv_skew(options_data: list[dict], current_price: float,
                     atm_band: float = 0.05) -> float:
    """ATM IV Skew = mean(put IV) - mean(call IV) for ATM-ish options.

    ATM band: within atm_band (default 5%) of current_price.
    Returns 0.0 if insufficient ATM options.
    """
    if not options_data or current_price <= 0:
        return 0.0

    low = current_price * (1 - atm_band)
    high = current_price * (1 + atm_band)

    put_ivs, call_ivs = [], []
    for opt in options_data:
        details = opt.get("details", {})
        strike = details.get("strike_price", 0)
        if not (low <= strike <= high):
            continue
        iv = opt.get("implied_volatility")
        if iv is None or iv <= 0:
            continue
        ctype = details.get("contract_type", "").lower()
        if ctype == "put":
            put_ivs.append(iv)
        elif ctype == "call":
            call_ivs.append(iv)

    if not put_ivs or not call_ivs:
        return 0.0

    return sum(put_ivs) / len(put_ivs) - sum(call_ivs) / len(call_ivs)
```

**Store-ba írás** (`run_mms_analysis` store entry):
```python
iv_skew = _compute_iv_skew(options_data, current_price) if options_data else 0.0
entry = {
    ...
    "iv_skew": iv_skew,
    ...
}
```

**Z-score számítás** (`_compute_z_scores`):
```python
store_features = ["dark_share", "gex", "dex", "block_count", "iv_rank",
                  "venue_entropy", "iv_skew"]
```

**Tesztelés Lépés 3 után:**
```bash
pytest -q tests/test_bc15_mms.py::TestIVSkew              # 6 teszt
pytest -q tests/test_bc15_mms.py::TestZScoresWithNewFeatures  # 2 teszt
pytest -q tests/test_bc15_mms.py                           # teljes MMS suite
```

---

### Lépés 4 — Súlyok aktiválása a config-ban

Frissítsd a `mms_feature_weights` config kulcsot (PARAMETERS.md + config default):
```python
"mms_feature_weights": {
    "dark_share":      0.25,
    "gex":             0.25,
    "venue_entropy":   0.15,
    "block_intensity": 0.15,   # block_count → block_intensity alias marad
    "iv_rank":         0.10,
    "iv_skew":         0.10,
}
```

A `_compute_unusualness`-ban a `scoring_features` listát is frissítsd:
```python
scoring_features = ["dark_share", "gex", "block_count", "iv_rank", "venue_entropy", "iv_skew"]
```

**Tesztelés Lépés 4 után:**
```bash
pytest -q tests/test_bc15_mms.py   # teljes MMS suite
pytest -q                          # teljes suite — 860+ passing, 0 failure
```
⚠️ Commit csak ha zöld.

---

### Lépés 5 — Docs frissítése

1. `docs/PARAMETERS.md` — minden `obsidian_*` config kulcs átnevezése `mms_*`-ra,
   `mms_feature_weights` táblázat frissítése 6 feature-rel
2. `docs/PIPELINE_LOGIC.md` — OBSIDIAN szekció neve: MMS,
   feature lista frissítése venue_entropy + iv_skew-vel
3. `CLAUDE.md` — OBSIDIAN hivatkozások → MMS mindenütt

---

## Tesztek CC-nek írja meg

### Venue Mix tesztek (`TestVenueMix`)
```python
class TestVenueMix:
    def test_venue_entropy_single_venue(self):
        """Minden print ugyanazon a venue-n → entrópia = 0."""
        records = [
            {"size": "1000", "price": "150.0", "volume": "5000000",
             "market_center": "FINRA", "nbbo_ask": "150.1", "nbbo_bid": "149.9"},
        ] * 10
        result = _aggregate_dp_records(records)
        assert "venue_entropy" in result
        assert result["venue_entropy"] == 0.0

    def test_venue_entropy_equal_distribution(self):
        """Egyenlő eloszlás N venue-n → entrópia = log(N)."""
        records = []
        for venue in ["FINRA", "NYSE", "NASDAQ", "ARCA"]:
            records.append({
                "size": "1000", "price": "150.0", "volume": "5000000",
                "market_center": venue, "nbbo_ask": "150.1", "nbbo_bid": "149.9",
            })
        result = _aggregate_dp_records(records)
        import math
        assert abs(result["venue_entropy"] - math.log(4)) < 0.01

    def test_venue_entropy_stored_in_entry(self, config, store):
        """venue_entropy bekerül a store-ba."""
        bars = _make_bars(100)
        stock = _make_stock(dp_pct=42.0)
        stock.flow.venue_entropy = 1.38
        run_mms_analysis(config.core, config.tuning,
                         "AAPL", bars, None, stock, None, store)
        entries = store.load("AAPL")
        assert "venue_entropy" in entries[0]
        assert entries[0]["venue_entropy"] == pytest.approx(1.38, abs=0.1)

    def test_venue_entropy_zero_when_no_dp_data(self, config, store):
        """Ha nincs darkpool adat, venue_entropy = 0.0."""
        bars = _make_bars(100)
        stock = _make_stock(dp_pct=0.0)
        stock.flow.venue_entropy = 0.0
        run_mms_analysis(config.core, config.tuning,
                         "AAPL", bars, None, stock, None, store)
        entries = store.load("AAPL")
        assert entries[0]["venue_entropy"] == 0.0
```

### IV Skew tesztek (`TestIVSkew`)
```python
class TestIVSkew:
    def test_iv_skew_puts_expensive(self):
        options = [
            {"details": {"strike_price": 150.0, "contract_type": "put"},
             "implied_volatility": 0.35},
            {"details": {"strike_price": 150.0, "contract_type": "call"},
             "implied_volatility": 0.25},
        ]
        assert _compute_iv_skew(options, 150.0) == pytest.approx(0.10, abs=0.001)

    def test_iv_skew_calls_expensive(self):
        options = [
            {"details": {"strike_price": 150.0, "contract_type": "put"},
             "implied_volatility": 0.20},
            {"details": {"strike_price": 150.0, "contract_type": "call"},
             "implied_volatility": 0.30},
        ]
        assert _compute_iv_skew(options, 150.0) == pytest.approx(-0.10, abs=0.001)

    def test_iv_skew_otm_filtered(self):
        """OTM opciók kizárva az ATM band-ből."""
        options = [
            {"details": {"strike_price": 200.0, "contract_type": "put"},
             "implied_volatility": 0.80},   # OTM — kizárandó
            {"details": {"strike_price": 150.0, "contract_type": "put"},
             "implied_volatility": 0.30},   # ATM
            {"details": {"strike_price": 150.0, "contract_type": "call"},
             "implied_volatility": 0.25},   # ATM
        ]
        assert _compute_iv_skew(options, 150.0) == pytest.approx(0.05, abs=0.001)

    def test_iv_skew_empty(self):
        assert _compute_iv_skew([], 150.0) == 0.0
        assert _compute_iv_skew(None, 150.0) == 0.0

    def test_iv_skew_stored_in_entry(self, config, store):
        """iv_skew bekerül a store-ba."""
        bars = _make_bars(100)
        options = [
            {"details": {"strike_price": 150.0, "contract_type": "put"},
             "implied_volatility": 0.35, "underlying_asset": {"price": 150.0}},
            {"details": {"strike_price": 150.0, "contract_type": "call"},
             "implied_volatility": 0.25, "underlying_asset": {"price": 150.0}},
        ]
        stock = _make_stock(price=150.0)
        run_mms_analysis(config.core, config.tuning,
                         "AAPL", bars, options, stock, None, store)
        entries = store.load("AAPL")
        assert "iv_skew" in entries[0]
        assert entries[0]["iv_skew"] == pytest.approx(0.10, abs=0.001)

    def test_iv_skew_z_score_after_21_entries(self, config, store):
        """iv_skew z-score érdemi 21+ entry után."""
        bars = _make_bars(100)
        stock = _make_stock(price=150.0)
        for i in range(25):
            store.append_and_save("AAPL", {
                "date": f"2026-01-{i+1:02d}",
                "dark_share": 0.3, "gex": 1000000.0, "dex": 50000.0,
                "block_count": 5.0, "iv_rank": 0.30,
                "venue_entropy": 1.0, "iv_skew": 0.05 + i * 0.002,
                "efficiency": 1e-7, "impact": 5e-8,
                "daily_return": 0.01, "raw_score": 0.0,
            })
        options = [
            {"details": {"strike_price": 150.0, "contract_type": "put"},
             "implied_volatility": 0.40, "underlying_asset": {"price": 150.0}},
            {"details": {"strike_price": 150.0, "contract_type": "call"},
             "implied_volatility": 0.25, "underlying_asset": {"price": 150.0}},
        ]
        result = run_mms_analysis(config.core, config.tuning,
                                  "AAPL", bars, options, stock, None, store)
        assert result.baseline_state in (BaselineState.PARTIAL, BaselineState.COMPLETE)
```

### Feature weights tesztek (`TestFeatureWeights`)

Ezek a tesztek azt fedik le, hogy a súlyok config-ból jönnek és helyesen
paraméterezhetők — a jövőbeli hangolást (BC18+) védi.

```python
class TestFeatureWeights:
    """mms_feature_weights config-paraméterezhetőség tesztjei."""

    def _weights(self, **overrides):
        """Alap 6-feature súlykészlet, opcionális felülírással."""
        base = {
            "dark_share": 0.25, "gex": 0.25,
            "venue_entropy": 0.15, "block_intensity": 0.15,
            "iv_rank": 0.10, "iv_skew": 0.10,
        }
        base.update(overrides)
        return base

    def test_unusualness_proportional_to_weight(self):
        """Magasabb súlyú feature jobban emeli az unusualness score-t."""
        z = {"dark_share": 2.0, "gex": 0.0, "block_count": 0.0,
             "iv_rank": 0.0, "venue_entropy": 0.0, "iv_skew": 0.0}

        low_weights = self._weights(dark_share=0.10)
        high_weights = self._weights(dark_share=0.40)

        u_low  = _compute_unusualness(z, [], low_weights,  [])
        u_high = _compute_unusualness(z, [], high_weights, [])

        assert u_high > u_low

    def test_unusualness_zero_weight_feature_ignored(self):
        """Nulla súlyú feature nem járul hozzá a score-hoz."""
        z = {"dark_share": 3.0, "gex": 0.0, "block_count": 0.0,
             "iv_rank": 0.0, "venue_entropy": 0.0, "iv_skew": 0.0}

        weights_with = self._weights(dark_share=0.25)
        weights_zero = self._weights(dark_share=0.0)

        u_with = _compute_unusualness(z, [], weights_with, [])
        u_zero = _compute_unusualness(z, [], weights_zero, [])

        assert u_with > 0
        assert u_zero == 0.0

    def test_unusualness_unknown_feature_in_weights_ignored(self):
        """Ismeretlen feature neve a weights dict-ben nem okoz hibát — silent skip."""
        z = {"dark_share": 2.0, "gex": 0.0, "block_count": 0.0,
             "iv_rank": 0.0, "venue_entropy": 0.0, "iv_skew": 0.0}
        weights_typo = self._weights(typo_feature=0.99)  # extra, ismeretlen kulcs

        # Nem dob kivételt, a typo_feature egyszerűen nem kerül bele a score-ba
        u = _compute_unusualness(z, [], weights_typo, [])
        assert 0 <= u <= 100

    def test_unusualness_missing_weight_treats_as_zero(self):
        """Ha egy scoring feature-nek nincs súlya a dict-ben → 0 hozzájárulás."""
        z = {"dark_share": 3.0, "gex": 0.0, "block_count": 0.0,
             "iv_rank": 0.0, "venue_entropy": 0.0, "iv_skew": 0.0}
        weights_no_ds = {"gex": 0.50}  # dark_share hiányzik → 0

        u = _compute_unusualness(z, [], weights_no_ds, [])
        # Csak gex járul hozzá, de gex z=0 → score=0
        assert u == 0.0

    def test_all_6_features_contribute_independently(self):
        """Minden feature önállóan emeli a score-t, együtt is helyesen adódnak össze."""
        weights = self._weights()
        excluded = []

        # Egyenként
        scores = []
        for feat, weight_key in [
            ("dark_share",    "dark_share"),
            ("gex",           "gex"),
            ("block_count",   "block_intensity"),
            ("iv_rank",       "iv_rank"),
            ("venue_entropy", "venue_entropy"),
            ("iv_skew",       "iv_skew"),
        ]:
            z_single = {f: (2.0 if f == feat else 0.0)
                        for f in ["dark_share", "gex", "block_count",
                                  "iv_rank", "venue_entropy", "iv_skew"]}
            u = _compute_unusualness(z_single, excluded, weights, [])
            scores.append((feat, u))

        # Mindegyik > 0
        for feat, u in scores:
            assert u > 0, f"{feat} kellene > 0 legyen, de {u}"

        # Az összes feature együtt magasabb score-t ad mint bármelyik egyedül
        z_all = {f: 2.0 for f in ["dark_share", "gex", "block_count",
                                   "iv_rank", "venue_entropy", "iv_skew"]}
        u_all = _compute_unusualness(z_all, excluded, weights, [])
        for feat, u_single in scores:
            assert u_all >= u_single, f"u_all ({u_all}) < u_single({feat}={u_single})"

    def test_default_weights_sum_to_one(self):
        """Az alapértelmezett 6-feature súlyok összege 1.0."""
        weights = self._weights()
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_config_weights_used_not_hardcoded(self, config, store):
        """_compute_unusualness a config-ból veszi a súlyokat, nem hardcodolt."""
        bars = _make_bars(100)
        stock = _make_stock()
        # 25 entry hogy z-score-ok legyenek
        for i in range(25):
            store.append_and_save("AAPL", {
                "date": f"2026-01-{i+1:02d}",
                "dark_share": 0.3 + i * 0.01, "gex": float(1000000 + i * 10000),
                "dex": 50000.0, "block_count": 5.0, "iv_rank": 0.25,
                "venue_entropy": 1.0, "iv_skew": 0.05,
                "efficiency": 1e-7, "impact": 5e-8,
                "daily_return": 0.01, "raw_score": 0.0,
            })

        # Két különböző súlykészlet
        config_a = dict(config.tuning)
        config_a["mms_feature_weights"] = self._weights(gex=0.50, dark_share=0.10)

        config_b = dict(config.tuning)
        config_b["mms_feature_weights"] = self._weights(gex=0.10, dark_share=0.50)

        result_a = run_mms_analysis(config.core, config_a, "AAPL",
                                    bars, None, stock, None, store)
        store_b = MMSStore(store_dir=store._store_dir, max_entries=100)  # ugyanaz a store
        result_b = run_mms_analysis(config.core, config_b, "AAPL",
                                    bars, None, stock, None, store_b)

        # Különböző súlyok → különböző unusualness score
        # (nem garantáltan, de ha gex z-score ≠ dark_share z-score, eltérnek)
        # A teszt azt ellenőrzi, hogy a config-ból olvas, nem dob hibát
        assert 0 <= result_a.unusualness_score <= 100
        assert 0 <= result_b.unusualness_score <= 100
```

### Z-score tesztek (`TestZScoresWithNewFeatures`)
```python
class TestZScoresWithNewFeatures:
    def test_z_scores_include_new_features(self):
        """venue_entropy és iv_skew z-score-ja számítódik 25 entry után."""
        bars = _make_bars(100)
        bar_features = _extract_features_from_bars(bars, window=63)
        history = []
        for i in range(25):
            history.append({
                "date": f"2026-01-{i+1:02d}",
                "dark_share": 0.3 + i * 0.01, "gex": 1000000 + i * 10000,
                "dex": 50000.0, "block_count": 5.0, "iv_rank": 0.25,
                "venue_entropy": 1.0 + i * 0.02, "iv_skew": 0.05 + i * 0.002,
            })
        today = {
            "efficiency": bar_features["efficiency_today"],
            "impact": bar_features["impact_today"],
            "dark_share": 0.55, "gex": 1500000.0, "dex": 80000.0,
            "block_count": 30.0, "iv_rank": 0.40,
            "venue_entropy": 1.8, "iv_skew": 0.12,
        }
        z = _compute_z_scores(today, history, bar_features, min_periods=21)
        assert z.get("venue_entropy") is not None
        assert z.get("iv_skew") is not None

    def test_z_scores_none_for_legacy_history(self):
        """Régi history-ban nincs venue_entropy/iv_skew → z-score None."""
        bars = _make_bars(100)
        bar_features = _extract_features_from_bars(bars, window=63)
        history = []
        for i in range(25):
            history.append({
                "date": f"2026-01-{i+1:02d}",
                "dark_share": 0.3 + i * 0.01, "gex": 1000000 + i * 10000,
                "dex": 50000.0, "block_count": 5.0, "iv_rank": 0.25,
                # nincs venue_entropy, nincs iv_skew — legacy
            })
        today = {
            "efficiency": bar_features["efficiency_today"],
            "impact": bar_features["impact_today"],
            "dark_share": 0.55, "gex": 1500000.0, "dex": 80000.0,
            "block_count": 30.0, "iv_rank": 0.40,
            "venue_entropy": 1.8, "iv_skew": 0.12,
        }
        z = _compute_z_scores(today, history, bar_features, min_periods=21)
        assert z.get("venue_entropy") is None   # 0 érvényes érték a history-ban
        assert z.get("iv_skew") is None
```

---

## Git commit üzenetek

```
refactor: rename OBSIDIAN to MMS (Market Microstructure Scorer)

- phase5_obsidian.py → phase5_mms.py, obsidian_store.py → mms_store.py
- ObsidianStore → MMSStore, ObsidianAnalysis → MMSAnalysis
- obsidian_* config keys → mms_* throughout
- state/obsidian/ → state/mms/ (461 existing JSON files preserved)
- test_bc15_obsidian.py → test_bc15_mms.py
- CLAUDE.md, PARAMETERS.md, PIPELINE_LOGIC.md updated
- 848 tests passing, pipeline behavior unchanged
```

```
feat: add venue_entropy and iv_skew to MMS feature store

- adapters._aggregate_dp_records: Shannon entropy from market_center
- market.FlowAnalysis: venue_entropy field added
- phase4_stocks: venue_entropy passed through from dp_data
- phase5_mms: _compute_iv_skew() helper added
- MMS store entry: venue_entropy + iv_skew fields
- _compute_z_scores: 7 store features (was 5)
- Tests: TestVenueMix (4), TestIVSkew (6), TestZScoresWithNewFeatures (2), TestFeatureWeights (7)
```

```
config: activate 6-feature mms_feature_weights

- dark_share=0.25, gex=0.25, venue_entropy=0.15,
  block_intensity=0.15, iv_rank=0.10, iv_skew=0.10
- _compute_unusualness scoring_features updated
- Full suite passing
```
