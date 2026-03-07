Session lezárás: quality gates + learning capture + journal entry + CLAUDE.md szinkron.

## 1. Git audit

```bash
git status
git diff --stat
git stash list
```

- Van uncommitted változás? Ha igen: commitálni vagy stash-elni kell előbb.
- Van `.env` vagy credencial a staged fájlok között? Ha igen: STOP, ne commitálj.
- Van nyitott stash? Jelezd.

## 2. Quality gates

```bash
python -m pytest tests/ -q 2>/dev/null | tail -3
grep -rl "Status: OPEN\|Status: WIP" docs/tasks/ 2>/dev/null
```

- Tesztek zöldek?
- Van WIP task amit nem zártál le?

## 3. Kód scan — commit előtt

Nézd át az utolsó változtatásokat (`git diff HEAD`):
- Van `print()` debug kiírás ami nem kell?
- Van `TODO/FIXME/HACK` comment?
- Van hardcoded API kulcs vagy credential?
- Van olyan ideiglenes kód ami nem való prodba?

Jelezd ha találsz ilyet — ne wrappeld le commitálatlan debuggal.

## 4. Learning capture

Kérdezd meg:
- Volt valami meglepő vagy tanulságos ebben a sessionben?
- Volt correction (valamit másképp kellett csinálni mint tervezted)?

Ha igen → javasold a `/learn` commandot a rögzítéshez.
Ha nem → rendben, folytasd.

## 5. Paper trading státusz (ha releváns)

```bash
cat scripts/paper_trading/logs/cumulative_pnl.json 2>/dev/null | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(f'Day {d[\"trading_days\"]}/21 | cum PnL: \${d[\"cumulative_pnl\"]:+,.2f} ({d[\"cumulative_pnl_pct\"]:+.2f}%)')" 2>/dev/null
```

## 6. Journal entry írása

Írj `docs/journal/YYYY-MM-DD-session-close.md` fájlt.
Ha aznap már volt → `session-close-2.md`, `-3.md` stb.

```markdown
# Session Close — YYYY-MM-DD HH:MM CET

## Összefoglaló
[1-2 mondatos tömör összefoglaló]

## Mit csináltunk
- [konkrét dolog 1]
- [konkrét dolog 2]

## Döntések
- [döntés + indoklás] (ha volt)

## Commit(ok)
- `hash` — üzenet

## Tesztek
- N teszt passing, 0 failure

## Következő lépés
- [legfontosabb nyitott task]

## Blokkolók
- [vagy: Nincs]
```

## 7. CLAUDE.md Aktuális Kontextus frissítése

```bash
python -m pytest tests/ -q 2>/dev/null | tail -1
git log --oneline -1
```

Frissítsd a `CLAUDE.md` alján az `## Aktuális Kontextus` szekciót:

```markdown
## Aktuális Kontextus
<!-- CC frissíti a /wrap-up során -->
- **Utolsó journal**: docs/journal/YYYY-MM-DD-session-close.md
- **Aktív BC**: [szám + fázis]
- **Nyitott taskok**: [task fájlnév lista]
- **Teszt szám**: [N passing]
- **Utolsó commit**: [hash — üzenet]
- **Paper Trading**: Day X/21 (cum. PnL $XXX, +X.XX%)
- **Blokkolók**: [vagy: nincs]
```

## 8. Megerősítés

```
Session lezárva ✓
─────────────────────────────
Journal:  docs/journal/YYYY-MM-DD-session-close.md
Tesztek:  N passing
Commit:   hash — üzenet
CLAUDE.md: szinkronban
─────────────────────────────
Következő: [mit érdemes folytatni]
```
