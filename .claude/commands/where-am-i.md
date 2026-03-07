Gyors orientáció: hol tartunk a projektben.

## 1. Kontextus betöltés

Futtasd:
```bash
# Teszt szám
python -m pytest tests/ -q 2>/dev/null | tail -1

# Nyitott taskok
grep -rl "Status: OPEN\|Status: WIP" docs/tasks/ 2>/dev/null

# Paper trading státusz
cat scripts/paper_trading/logs/cumulative_pnl.json 2>/dev/null | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(f'Day {d[\"trading_days\"]}/21 | cum PnL: \${d[\"cumulative_pnl\"]:+,.2f} ({d[\"cumulative_pnl_pct\"]:+.2f}%)')" 2>/dev/null

# Utolsó commit
git log --oneline -3
```

Olvasd el:
- `CLAUDE.md` — "Aktuális Kontextus" szekció
- `docs/journal/` — legutolsó entry

## 2. Mutasd strukturáltan

```
📍 IFDS — [aktív BC]

📊 Paper Trading: Day X/21 | cum. PnL: $XXX (+X.XX%)
🧪 Tesztek: N passing, 0 failure
🔀 Utolsó commit: hash — üzenet

📋 Nyitott taskok:
  - [task fájl neve] — [Status]
  - ...

⏭ Következő mérföldkő: [BC / Phase / dátum]

🚧 Blokkolók: [vagy "nincs"]
```

Ha nincs journal entry: "Nincs korábbi session — futtasd `/continue`-t az induláshoz."
