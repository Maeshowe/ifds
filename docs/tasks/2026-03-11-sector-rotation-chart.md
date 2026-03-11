# Task: Sector Rotation Chart — Standalone Script

**Status:** DONE
**Updated:** 2026-03-11
**Priority:** Low — dashboard tool, nem pipeline-kritikus

---

## Feladat

Írj egy `scripts/sector_rotation_chart.py` standalone scriptet, amely egy
**Relative Rotation Graph (RRG)** chartot generál a 11 GICS szektor ETF
rotációjáról. Referencia implementáció (logika és kvadráns-definíciók):
https://trendspider.com/trading-tools-store/indicators/69a731-sector-rotation-chart/

---

## Implementációs útmutató

### .env betöltés — `validate_etf_holdings.py` pattern alapján

```python
_env_file = Path(__file__).resolve().parents[1] / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))
```

API key: `os.environ["IFDS_POLYGON_API_KEY"]`

### Polygon client — meglévő osztályok használata

```python
from ifds.data.polygon import PolygonClient
from ifds.data.cache import FileCache

cache = FileCache("data/cache")
client = PolygonClient(api_key=api_key, cache=cache)
```

Heti aggregates lekérése:
```python
bars = client.get_aggregates(
    ticker,
    from_date=from_date,   # YYYY-MM-DD, elég 6 hónap visszafelé
    to_date=today,
    timespan="week",
    multiplier=1,
)
# bars: [{"t": timestamp_ms, "c": close, "o": open, ...}, ...]
```

**Fontos:** A `FileCache` a mai napot nem cache-eli (`date.today()` skip) —
a `to_date`-et mindig tegnapra vagy régebbre állítsd, különben minden futásnál
újra lekéri. Legegyszerűbb: `to_date = (date.today() - timedelta(days=1)).isoformat()`

### Számítási logika (TrendSpider source alapján)

```
LOOKBACK = 13 hét  (negyedév — RS számítás ablaka)
TRAIL    = 6 hét   (ennyi historikus pontot rajzolunk)

benchmark_change[i] = (VTI.close[i] - VTI.close[i-13]) / VTI.close[i-13]
sector_change[i]    = (ETF.close[i] - ETF.close[i-13]) / ETF.close[i-13]

RS[i]          = (1 + sector_change[i]) / (1 + benchmark_change[i]) * 100
RS_momentum[i] = (RS[i] / RS[i-1]) * 100
```

Középpont mindkét tengelyen: **100** (benchmark szintje).

### Szektorok

```python
SECTORS = [
    {"ticker": "XLE",  "name": "Energy",         "color": "#FF6B35"},
    {"ticker": "XLB",  "name": "Materials",       "color": "#A8DADC"},
    {"ticker": "XLI",  "name": "Industrials",     "color": "#6B9FD4"},
    {"ticker": "XLY",  "name": "Cons. Discr.",    "color": "#F4A261"},
    {"ticker": "XLP",  "name": "Cons. Staples",   "color": "#57CC99"},
    {"ticker": "XLV",  "name": "Health Care",     "color": "#E63946"},
    {"ticker": "XLF",  "name": "Financials",      "color": "#4CC9F0"},
    {"ticker": "XLK",  "name": "Technology",      "color": "#7B2FBE"},
    {"ticker": "XLC",  "name": "Comm. Services",  "color": "#F77F00"},
    {"ticker": "XLU",  "name": "Utilities",       "color": "#90E0EF"},
    {"ticker": "XLRE", "name": "Real Estate",     "color": "#FFBE0B"},
]
BENCHMARK = "VTI"
```

### Chart — 4 kvadráns + trail

```
Jobb-fent (x>100, y>100): LEADING   — zöld háttér  rgba(40,167,69,0.12)
Jobb-lent (x>100, y<100): WEAKENING — sárga háttér rgba(255,193,7,0.12)
Bal-lent  (x<100, y<100): LAGGING   — piros háttér rgba(220,53,69,0.12)
Bal-fent  (x<100, y>100): IMPROVING — kék háttér   rgba(30,144,255,0.12)
```

- Dark háttér (`plt.style.use("dark_background")`)
- Minden szektor: trail vonal + korábbi pontok (kis méret) + utolsó pont (nagy)
- Ticker label az utolsó pont mellé
- Szaggatott vonal a (100, 100) középponton át (mindkét tengely)
- Kvadráns feliratok sarokba: "LEADING", "WEAKENING", "LAGGING", "IMPROVING"

### CLI interface

```bash
python scripts/sector_rotation_chart.py                   # default: 6 hetes trail, PNG mentés
python scripts/sector_rotation_chart.py --trail 8         # hosszabb trail
python scripts/sector_rotation_chart.py --no-save         # csak megjelenít, nem ment
python scripts/sector_rotation_chart.py --output rrg.png  # custom output path
```

### Output

- Alapértelmezett: `output/sector_rotation_{YYYYMMDD}.png`
- Terminál összefoglaló is:

```
=== Sector Rotation — 2026-03-11 ===
LEADING   : XLF, XLK, XLI
IMPROVING : XLE, XLY
WEAKENING : XLV
LAGGING   : XLB, XLC, XLP, XLRE, XLU
```

---

## Függőségek

`matplotlib` és `numpy` valószínűleg már megvan a `.venv`-ben. Ha nem:
```bash
.venv/bin/pip install matplotlib numpy
```

---

## Tesztelés

Nincs pytest igény. Manuálisan:
1. `source .env && .venv/bin/python scripts/sector_rotation_chart.py`
2. 11 szektor megjelenik traillel ✓
3. Terminál összefoglaló konzisztens a chart kvadránsaival ✓
4. PNG létrejön `output/`-ban ✓

---

## Commit üzenet

```
feat(dashboard): sector_rotation_chart.py RRG standalone script
```
