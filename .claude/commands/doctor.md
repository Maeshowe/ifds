IFDS setup és CC konfiguráció egészség-ellenőrzése.

## Futtatandó ellenőrzések

### 1. Tesztek

```bash
python -m pytest tests/ -q 2>/dev/null | tail -3
```
- Zöld? ✓
- Van failure/error? → jelezd

### 2. Task fájl státusz

```bash
grep -rl "Status: OPEN\|Status: WIP" docs/tasks/ 2>/dev/null
grep -rl "^Status:" docs/tasks/*.md | wc -l    # mennyi fájlnak van fejléce
ls docs/tasks/*.md | wc -l                      # összesen mennyi task fájl van
```
- Minden fájlnak van `Status:` fejléce?
- Van WIP amit lezárni kell?

### 3. CLAUDE.md méret és frissesség

```bash
wc -l CLAUDE.md
```
- < 150 sor: OK
- 150-200 sor: Figyelj rá
- \> 200 sor: Modulokra bontandó

Ellenőrizd az `## Aktuális Kontextus` szekciót:
- Az `Utolsó journal` fájl tényleg létezik?
- A teszt szám naprakész?

### 4. Paper trading státusz (ha aktív)

```bash
cat scripts/paper_trading/logs/cumulative_pnl.json 2>/dev/null | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(f'Day {d[\"trading_days\"]}/21 | \${d[\"cumulative_pnl\"]:+,.2f} ({d[\"cumulative_pnl_pct\"]:+.2f}%)')" 2>/dev/null
```

### 5. Git állapot

```bash
git status --short
git stash list
git log --oneline -3
```
- Van uncommitted változás?
- Van stale stash?

### 6. Cron és pipeline

```bash
ls -lt logs/cron_*.log 2>/dev/null | head -3    # utolsó cron futások
ls -lt output/execution_plan_*.csv 2>/dev/null | head -1  # utolsó execution plan
```

### 7. Commands ellenőrzés

```bash
ls .claude/commands/
ls .claude/rules/
```
- Megvannak az expected commandok: `wrap-up`, `commit`, `develop`, `handoff`, `replay`, `learn`, `continue`, `where-am-i`, `review`, `test`, `refactor`, `decide`?

## Report formátum

```
IFDS Health Check — YYYY-MM-DD
──────────────────────────────
Tesztek:       N passing ✓ / X failure ✗
Task státusz:  N/M fájlban van fejléc | X WIP nyitott
CLAUDE.md:     N sor (OK / figyelj rá / bontandó)
Aktuális kt.:  [friss / elavult]
Paper Trading: Day X/21 | $XXX ✓ / nem aktív
Git:           clean ✓ / X uncommitted
Cron:          utolsó futás: YYYY-MM-DD ✓ / hiányzik
Commands:      N/12 megvan ✓
──────────────────────────────
[Ha van probléma: konkrét javítási javaslat]
```

---

**Trigger:** "check", "minden oké?", "setup check", "doktor", session elején ha bizonytalan a user.
