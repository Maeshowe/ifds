# BC23 Kiegészítés — Heti Metrika Aggregáció

**Status:** DONE
**Updated:** 2026-04-11
**Priority:** P2 — az első heti kiértékelés április 18
**Effort:** ~1h CC
**Depends on:** daily_metrics.py (2026-04-11-daily-metrics-collection.md)

---

## Implementáció

### Script: `scripts/analysis/weekly_metrics.py`

Nem cron — manuálisan futtatandó péntek piaczárás után (22:10+ CEST):

```bash
cd ~/SSH-Services/ifds && .venv/bin/python scripts/analysis/weekly_metrics.py
```

Vagy opcionálisan egy adott hétre:

```bash
python scripts/analysis/weekly_metrics.py --week 2026-04-14
```

### Bemenetek

```
state/daily_metrics/YYYY-MM-DD.json   → az adott hét 5 napja
```

### Kimenet

```
docs/analysis/weekly/YYYY-WNN.md      → pl. 2026-W16.md
```

Plusz Telegram üzenet a heti összefoglalóval.

### Tartalom

```markdown
# IFDS Weekly Report — 2026-W16 (Apr 14-18)

## Összefoglaló
- Kereskedési napok: 5
- Pozíciók nyitva: 18 (átlag 3.6/nap)
- Win days: 3/5 (60%)

## P&L
- Heti gross P&L: +$124.50
- Heti commission: -$68.40
- Heti net P&L: +$56.10
- Kumulatív: -$2,359.13 (-2.36%)

## SPY-Adjusted Excess Return
- Heti portfólió return: +0.06%
- SPY heti return: -1.20%
- **Excess return: +1.26%**

## Exit Breakdown
| Exit | N | % | Avg P&L |
|------|---|---|---------|
| TP1  | 3 | 17% | +$42 |
| TRAIL | 1 | 6% | +$28 |
| MOC  | 11 | 61% | -$8 |
| LOSS_EXIT | 2 | 11% | -$65 |
| SL   | 1 | 6% | -$48 |

## Scoring Quality
- Avg score opened: 91.2
- Score→P&L correlation (week): r=+0.18
- Qualified tickers (85+ avg): 6.2/nap
- Positions opened vs qualified: 3.6/6.2 = 58%

## TP1 Performance
- TP1 hit rate: 17% (3/18)
- TP1 avg profit: +$42
- R:R realized: 1:0.87 (közel 1:1)

## Slippage
- Avg MKT fill slippage: +0.28%
- Worst: FLEX +1.06%

## Commission Drag
- Commission: $68.40
- Commission % of gross P&L: 55% ← cél: <30%

## Dynamic Threshold
- Napok amikor 0 pozíció (threshold alatt): 0/5
- Napok amikor <3 pozíció: 1/5
- → threshold 85 megfelelő / túl magas / túl alacsony

## Anomáliák
- [lista ha van]

## Következő hét fókusz
- [manuálisan kitöltendő]
```

### Telegram összefoglaló

```
📊 IFDS WEEKLY — 2026-W16
Net P&L: +$56.10 | Cum: -$2,359 (-2.36%)
Excess vs SPY: +1.26%
Positions: 18 (3.6/nap) | Win days: 3/5
TP1: 3/18 (17%) | R:R: 1:0.87
Commission: $68 (55% of gross)
```

## Logika

```python
def generate_weekly_report(week_start: date = None):
    if week_start is None:
        # Legutolsó hétfő
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
    
    week_end = week_start + timedelta(days=4)  # péntek
    
    # Napi metrikák betöltése
    daily_files = []
    for d in range(5):
        day = week_start + timedelta(days=d)
        path = f"state/daily_metrics/{day.isoformat()}.json"
        if os.path.exists(path):
            daily_files.append(json.load(open(path)))
    
    if not daily_files:
        print("No daily metrics found for this week")
        return
    
    # Aggregálás
    total_pnl = sum(d["pnl"]["gross"] for d in daily_files)
    total_commission = sum(d["execution"]["commission_total"] for d in daily_files)
    total_positions = sum(d["positions"]["opened"] for d in daily_files)
    spy_weekly = sum(d["market"]["spy_return_pct"] for d in daily_files)
    # ... stb
    
    # Markdown generálás
    # Telegram küldés
```

## Tesztek

- `test_weekly_aggregation` — 5 napi metrikából helyes összegzés
- `test_weekly_no_data` — ha nincs adat a hétre → informatív üzenet, nem hiba
- `test_weekly_partial` — ha csak 3 nap van (ünnepnap) → helyes átlagolás

## Commit

```
feat(metrics): weekly metrics aggregation script

Generates weekly summary from daily_metrics JSON files.
Output: docs/analysis/weekly/YYYY-WNN.md + Telegram summary.
Tracks: excess return vs SPY, TP1 hit rate, R:R ratio, commission drag,
dynamic threshold effectiveness, scoring quality.

Run manually: python scripts/analysis/weekly_metrics.py
```
