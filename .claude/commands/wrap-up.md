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

## 7. docs/STATUS.md frissítése

```bash
python -m pytest tests/ -q 2>/dev/null | tail -1
git log --oneline -1
cat scripts/paper_trading/logs/cumulative_pnl.json 2>/dev/null | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(f'Day {d[\"trading_days\"]}/63 | {d[\"cumulative_pnl\"]:+,.2f} ({d[\"cumulative_pnl_pct\"]:+.2f}%)')" 2>/dev/null
```

Frissítsd a `docs/STATUS.md` fájlt **in-place** (nem új fájl, nincs dátum a névben):
- `<!-- Utolsó frissítés: YYYY-MM-DD, CC -->` sor
- Paper Trading: Day X/63, cum. PnL
- Aktív BC + nyitott taskok
- Shadow features státusz (ha változott)
- Utolsó commit hash + üzenet
- Blokkolók

**CLAUDE.md Aktuális Kontextus szekciót NEM frissítjük** — az stabil referencia marad.

## 8. Docs szinkron ellenőrzés

**BC milestone check:** Ha a session-ben BC státusz változott (pl. BC lezárult):
- `docs/planning/roadmap-2026-consolidated.md` — BC sor ✅ KÉSZ jelölés + dátum
- `CHANGELOG.md` — új szekció a BC deliverable-jeivel

**CHANGELOG check:** Ha volt commit a session-ben, de a CHANGELOG nem frissült:
- ⚠️ Jelezd: "CHANGELOG frissítés hiányzik — most pótolod vagy kihagyod?"
- Quick win / bugfix commitoknál a CHANGELOG update opcionális
- BC deliverable commitoknál KÖTELEZŐ

**Testing baseline check:** Olvasd el a `.claude/rules/testing.md` baseline számot.
Ha a jelenlegi teszt szám >50-nel meghaladja a baseline-t:
- Frissítsd a baseline-t a `testing.md`-ben

## 9. Megerősítés

```
Session lezárva ✓
─────────────────────────────
Journal:    docs/journal/YYYY-MM-DD-session-close.md
Tesztek:    N passing
Commit:     hash — üzenet
CLAUDE.md:  szinkronban
Docs sync:  [OK | CHANGELOG hiányzik | roadmap frissítve]
─────────────────────────────
Következő: [mit érdemes folytatni]
```
