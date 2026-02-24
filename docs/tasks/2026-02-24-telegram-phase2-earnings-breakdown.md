# Task: Telegram Phase 2 earnings sor bővítés

**Date:** 2026-02-24  
**Priority:** MEDIUM — párhuzamos CC task  
**Scope:** `src/ifds/output/telegram.py`  
**Trigger:** A mai Zombie Hunter fix (Pass 2: ticker-specific) után a summary log már tartalmazza a `bulk=N, ticker-specific=M` bontást. Ez a Telegram Phase 2 sorában is jelenjen meg.

---

## Jelenlegi Telegram output

```
[ 2/6 ] Universe Building
Screened: 1673  Passed: 1397  Earnings excluded: 276
```

## Kívánt output

```
[ 2/6 ] Universe Building
Screened: 1673  Passed: 1397  Earnings excluded: 276 (bulk=273, ticker-specific=3)
```

Ha `ticker-specific=0` (normális nap, nincs ADR miss): csak `Earnings excluded: 276` — a zárójel nem jelenik meg. Csak akkor látható ha a Pass 2 ténylegesen fogott valamit.

---

## Implementáció

### `src/ifds/models/market.py` — `Phase2Result` bővítés

Ellenőrizd hogy a `Phase2Result` dataclass tartalmazza-e már a `bulk_excluded` és `ticker_specific_excluded` mezőket (a mai Zombie Hunter fix hozzáadhatta). Ha nem:

```python
@dataclass
class Phase2Result:
    tickers: list
    total_screened: int
    earnings_excluded: list[str]
    strategy_mode: StrategyMode
    # Új mezők — default 0 a backward compat-hoz:
    bulk_excluded_count: int = 0
    ticker_specific_excluded_count: int = 0
```

Ha már benne vannak a mai fix után — csak a Telegram formázás kell.

### `src/ifds/output/telegram.py` — `_format_phases_0_to_4()` módosítás

Keresendő blokk:
```python
# Phase 2: Universe
lines.append("")
lines.append(f"<b>[ 2/6 ] Universe Building</b>")
if ctx.phase2:
    lines.append(
        f"Screened: {ctx.phase2.total_screened}"
        f"  Passed: {len(ctx.phase2.tickers)}"
        f"  Earnings excluded: {len(ctx.phase2.earnings_excluded)}"
    )
```

Módosítandó:
```python
# Phase 2: Universe
lines.append("")
lines.append(f"<b>[ 2/6 ] Universe Building</b>")
if ctx.phase2:
    p2 = ctx.phase2
    earn_count = len(p2.earnings_excluded)
    bulk_n = getattr(p2, "bulk_excluded_count", 0)
    ticker_n = getattr(p2, "ticker_specific_excluded_count", 0)

    # Csak akkor mutasd a bontást ha a ticker-specific ténylegesen fogott valamit
    if ticker_n > 0:
        earn_str = f"{earn_count} (bulk={bulk_n}, ticker-specific={ticker_n})"
    else:
        earn_str = str(earn_count)

    lines.append(
        f"Screened: {p2.total_screened}"
        f"  Passed: {len(p2.tickers)}"
        f"  Earnings excluded: {earn_str}"
    )
```

---

## Függőség ellenőrzés

A mai Zombie Hunter fix (`phase2_universe.py`) a `_exclude_earnings()` summary log-ban logolta a `ticker_specific_excluded` értéket. Ellenőrizd hogy a `Phase2Result`-ba is visszakerül-e — ha a `run_phase2()` csak `earnings_excluded` listát ad vissza és nem bontja bulk/ticker-specific-re, akkor a `Phase2Result`-ot is bővíteni kell.

Ha a mai fix még nem adta hozzá a mezőket a `Phase2Result`-hoz: add hozzá ott is, és add át `run_phase2()`-ből.

---

## Tesztelés

```python
# Elvárt output ha ticker_specific_excluded_count > 0:
# "Earnings excluded: 276 (bulk=273, ticker-specific=3)"

# Elvárt output ha ticker_specific_excluded_count == 0:
# "Earnings excluded: 276"
```

2 unit teszt a `_format_phases_0_to_4()` earnings sor formázására.

---

## Git

```bash
git add src/ifds/output/telegram.py src/ifds/models/market.py  # ha Phase2Result bővült
git commit -m "feat: Telegram Phase 2 earnings bontás (bulk/ticker-specific)

Earnings excluded sor csak akkor mutatja a bontást ha ticker-specific > 0:
  'Earnings excluded: 276 (bulk=273, ticker-specific=3)'
Normál napokon: 'Earnings excluded: 276' (változatlan)

getattr fallback a backward compat-hoz ha Phase2Result mezők hiányoznak."
git push
```
