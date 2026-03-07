Session átadó dokumentum — a következő session azonnal folytatni tudja.

A `/wrap-up`-tól eltérő cél: ez a **következő sessionnek** íródik, nem az aktuálisnak.

## 1. Állapot összegyűjtése

```bash
git status
git diff --stat
git log --oneline -5
grep -rl "Status: OPEN\|Status: WIP" docs/tasks/ 2>/dev/null
python -m pytest tests/ -q 2>/dev/null | tail -1
cat scripts/paper_trading/logs/cumulative_pnl.json 2>/dev/null | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(f'Day {d[\"trading_days\"]}/21 | \${d[\"cumulative_pnl\"]:+,.2f} ({d[\"cumulative_pnl_pct\"]:+.2f}%)')" 2>/dev/null
```

## 2. Handoff dokumentum generálása

Írj `docs/journal/YYYY-MM-DD-handoff.md` fájlt:

```markdown
# Handoff — YYYY-MM-DD HH:MM CET

## Státusz egy mondatban
[pl. "BC17 Phase_17A preflight kész, Phase_17B monitor_positions következik"]

## Kész
- [task 1 — commit hash]
- [task 2 — commit hash]

## Folyamatban
- [task neve — hol tartunk, melyik fájl, melyik szekció]

## Következő lépés (konkrétan)
1. [első teendő — fájl + mit kell csinálni]
2. [második teendő]

## Nyitott task fájlok
- `docs/tasks/YYYY-MM-DD-xxx.md` — Status: OPEN/WIP

## Döntések ebből a sessionből
- [döntés + indoklás]

## Gotchák / nem nyilvánvaló dolgok
- [ami meglepett vagy amire figyelni kell]

## Paper Trading
- Day X/21 | cum. PnL: $XXX (+X.XX%)
- [bármi fontos — pl. nyitott pozíció, nuke szükséges-e]

## Tesztek
- N passing, 0 failure

## Resume parancs (másold be a következő session elejére)
> Folytasd az IFDS BC17 munkát. [1-2 mondat kontextus]. Következő lépés: [konkrét task].
```

## 3. Megerősítés

```
Handoff mentve: docs/journal/YYYY-MM-DD-handoff.md
Resume parancs: [kimásolva]
```

---

**Trigger:** "handoff", "add át", "folytasd majd", "átadom", "következő sessionre", vagy ha váltasz eszközt/gépet.
