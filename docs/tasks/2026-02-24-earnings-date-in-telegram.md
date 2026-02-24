# Task: Earnings Date Column in Telegram Execution Table

**Date:** 2026-02-24  
**Priority:** HIGH — ma implementálandó  
**Scope:** `src/ifds/output/telegram.py` + `src/ifds/data/fmp.py`  
**Trigger:** KEP pozíció kiment tegnap annak ellenére, hogy ma (Feb 24) jelent volna — az FMP `/stable/earnings-calendar` bulk endpoint rossz dátumot tárolt KEP-re (március 10 helyett február 26 volt a valós earnings). Szükség van arra, hogy a Telegram reportban látható legyen az FMP earnings dátum minden pozícióra.

---

## Cél

A Telegram Phase 6 execution table-be kerüljön egy `EARN` oszlop, amely megmutatja az FMP szerint következő earnings dátumot minden pozícióhoz. Így napi szemrevételezéssel kiszűrhetők az FMP hibás/hiányzó adatai.

**Jelenlegi fejléc:**
```
TICKER   QTY    ENTRY     STOP      TP1      TP2   RISK$
```

**Új fejléc:**
```
TICKER   QTY    ENTRY     STOP      TP1      TP2   RISK$  EARN
```

Az `EARN` mező formátuma: `MM-DD` (pl. `03-10`) ha van adat, `N/A` ha nincs.

---

## Implementáció

### 1. Új FMP metódus: `get_next_earnings_date`

**Fájl:** `src/ifds/data/fmp.py`

Endpoint: `/stable/earnings?symbol={ticker}` (ticker-specifikus, nem bulk calendar)

```python
def get_next_earnings_date(self, ticker: str) -> str | None:
    """Get the next upcoming earnings date for a ticker from FMP.

    Uses /stable/earnings?symbol={ticker} endpoint (ticker-specific,
    more reliable than bulk /stable/earnings-calendar for ADRs).

    Returns:
        Date string 'YYYY-MM-DD' of next earnings, or None if not found.
    """
    from datetime import date
    today = date.today().isoformat()

    params = {"apikey": self._api_key, "symbol": ticker}
    result = self._get("/stable/earnings", params=params,
                       headers=self._auth_headers())

    if not result or not isinstance(result, list):
        return None

    # Find the next upcoming earnings date (date >= today, epsActual is null)
    upcoming = [
        entry for entry in result
        if entry.get("date", "") >= today and entry.get("epsActual") is None
    ]

    if not upcoming:
        # Fallback: first entry with date >= today regardless of epsActual
        upcoming = [
            entry for entry in result
            if entry.get("date", "") >= today
        ]

    if not upcoming:
        return None

    # Return earliest upcoming date
    return min(upcoming, key=lambda e: e["date"])["date"]
```

**Megjegyzés:** Nincs cache-elés — a report generáláskor frissen hívjuk, kis overhead (max 8 ticker).

---

### 2. Telegram `_format_exec_table` módosítása

**Fájl:** `src/ifds/output/telegram.py`

A `_format_exec_table` függvény fogadjon egy opcionális `earnings_map: dict[str, str]` paramétert (`ticker → 'YYYY-MM-DD' vagy None`).

```python
def _format_exec_table(positions: list, earnings_map: dict[str, str] | None = None) -> str:
    """Format execution plan table as monospace <pre> block."""
    rows: list[str] = []
    
    if earnings_map is not None:
        header = (
            f"{'TICKER':<7}"
            f"{'QTY':>4} "
            f"{'ENTRY':>8} "
            f"{'STOP':>8} "
            f"{'TP1':>8} "
            f"{'TP2':>8} "
            f"{'RISK$':>6}"
            f"  {'EARN':<7}"
        )
    else:
        header = (
            f"{'TICKER':<7}"
            f"{'QTY':>4} "
            f"{'ENTRY':>8} "
            f"{'STOP':>8} "
            f"{'TP1':>8} "
            f"{'TP2':>8} "
            f"{'RISK$':>6}"
        )
    rows.append(header)

    for p in positions:
        row = (
            f"{p.ticker:<7}"
            f"{p.quantity:>4} "
            f"${p.entry_price:>7.2f} "
            f"${p.stop_loss:>7.2f} "
            f"${p.take_profit_1:>7.2f} "
            f"${p.take_profit_2:>7.2f} "
            f"${p.risk_usd:>5.0f}"
        )
        if earnings_map is not None:
            full_date = earnings_map.get(p.ticker)
            earn_str = full_date[5:] if full_date else "N/A"  # 'YYYY-MM-DD' → 'MM-DD'
            row += f"  {earn_str:<7}"
        rows.append(row)

    return "<pre>" + "\n".join(rows) + "</pre>"
```

---

### 3. `_format_phases_5_to_6` módosítása

**Fájl:** `src/ifds/output/telegram.py`

A `_format_phases_5_to_6` függvény fogadjon egy `fmp` kliens referenciát, és hívja meg a `get_next_earnings_date`-t minden pozícióra.

Függvény szignatúra változás:
```python
def _format_phases_5_to_6(ctx: PipelineContext, config: Config,
                           fmp=None) -> str:
```

A positions block-ban:
```python
if positions:
    earnings_map = None
    if fmp is not None:
        earnings_map = {}
        for p in positions:
            try:
                earnings_map[p.ticker] = fmp.get_next_earnings_date(p.ticker)
            except Exception:
                earnings_map[p.ticker] = None
    lines.append(_format_exec_table(positions, earnings_map=earnings_map))
```

---

### 4. `send_daily_report` módosítása

**Fájl:** `src/ifds/output/telegram.py`

```python
def send_daily_report(ctx: PipelineContext, config: Config,
                      logger: EventLogger, duration: float,
                      fmp=None) -> bool:
```

És a `_format_success` hívásban:
```python
part1, part2 = _format_success(ctx, duration, config, fmp=fmp)
```

```python
def _format_success(ctx: PipelineContext, duration: float,
                    config: Config, fmp=None) -> tuple[str, str]:
    lines_04 = _format_phases_0_to_4(ctx, duration, config)
    lines_56 = _format_phases_5_to_6(ctx, config, fmp=fmp)
    ...
```

---

### 5. Pipeline runner hívás frissítése

**Fájl:** `src/ifds/pipeline/runner.py`

Keresendő sor (valahol a pipeline végén):
```python
send_daily_report(ctx, config, logger, duration)
```

Módosítandó:
```python
send_daily_report(ctx, config, logger, duration, fmp=fmp_client)
```

A `fmp_client` már létezik a runner scope-jában (Phase 2 és 4 is használja).

---

## Tesztelés

Manuális ellenőrzés a mai execution plan alapján:

```python
# Gyors teszt script (nem kell becommitolni)
import os, sys
sys.path.insert(0, "src")
from ifds.data.fmp import FMPClient

fmp = FMPClient(api_key=os.environ["IFDS_FMP_API_KEY"])
tickers = ["GE", "LMT", "BWXT", "T", "NEE", "FE", "KEP", "SKM"]
for t in tickers:
    d = fmp.get_next_earnings_date(t)
    print(f"{t}: {d}")
```

Elvárt output (közelítőleg):
```
GE:   2026-04-XX
LMT:  2026-04-XX  
BWXT: 2026-04-XX
T:    2026-04-XX
NEE:  2026-04-XX
FE:   2026-05-XX
KEP:  2026-03-10   ← FMP szerint (valós: 2026-02-26 per Bloomberg)
SKM:  2026-03-XX
```

Ha KEP-nél `2026-03-10` jelenik meg → megerősíti, hogy az FMP dátum hibás. Legalább **látjuk** az FMP értéket és manuálisan dönthetünk.

---

## Várható Telegram output (mai lista alapján)

```
[ 6/6 ] Position Sizing
Positions: 8  |  Risk: $2,677  |  Exposure: $58,521

TICKER   QTY    ENTRY     STOP      TP1      TP2   RISK$  EARN
GE         27 $ 343.22 $ 328.35 $ 363.04 $ 372.95 $  404  04-22
LMT        11 $ 658.26 $ 629.91 $ 667.50 $ 714.95 $  336  04-22
BWXT       27 $ 206.44 $ 191.80 $ 225.96 $ 235.72 $  401  04-24
T         409 $  27.98 $  27.00 $  29.00 $  29.94 $  401  04-23
NEE        60 $  92.18 $  88.87 $  94.00 $  98.81 $  200  04-22
FE        130 $  50.20 $  48.67 $  52.24 $  53.26 $  200  05-01
KEP       307 $  22.45 $  21.37 $  23.89 $  24.61 $  333  03-10  ← látható!
SKM       194 $  31.17 $  29.11 $  35.00 $  35.30 $  401  03-XX
```

---

## Git

```bash
git add src/ifds/output/telegram.py src/ifds/data/fmp.py
git commit -m "feat: earnings date column in Telegram exec table (BC17-prep)

- FMPClient.get_next_earnings_date(): /stable/earnings?symbol= endpoint
- _format_exec_table(): opcionális earnings_map paraméter, EARN oszlop
- send_daily_report(): fmp paraméter átadás a format chain-en át
- Pipeline runner: fmp_client átadása send_daily_report-nak

Trigger: KEP position kiment 2026-02-23-án, valós earnings 2026-02-26
FMP bulk calendar rossz dátumot tárolt (2026-03-10). Az új oszlop
láthatóvá teszi az FMP adatot → manuális ellenőrzés lehetséges."
git push
```

---

## Megjegyzések

- **Nincs cache** a `get_next_earnings_date`-re — report generáláskor 8 extra API hívás, elhanyagolható overhead
- **Backward compatible** — ha `fmp=None` marad a `send_daily_report`-ban, az EARN oszlop nem jelenik meg (régi viselkedés)
- **Nem változtatja** a Zombie Hunter logikáját — ez csak observability, nem filtering
- **Hosszú távon** (BC18): ha az EARN dátum < Today + 7, WARNING kerülhet a reportba vagy a Zombie Hunter átválthat ticker-specifikus endpointra
