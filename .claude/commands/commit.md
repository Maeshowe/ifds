Smart commit: quality gates + kód scan + konvencionális commit üzenet.

## 1. Pre-commit audit

```bash
git status
git diff --stat HEAD
```

- Nincs `.env`, credential, vagy nagy bináris a staged fájlok között?
- Minden fájl szándékos? (nincs véletlen `state/`, `output/`, `logs/` a staged listában)

## 2. Quality gates

```bash
python -m pytest tests/ -q 2>/dev/null | tail -3
```

- Tesztek zöldek? Ha nem: javítás előbb, commit utána.
- Kihagyható csak ha a user explicit kéri (`--no-verify`).

## 3. Kód scan

Nézd át a staged diff-et (`git diff --cached`):
- `print()` debug kiírás?
- `TODO/FIXME/HACK` comment ticket nélkül?
- Hardcoded API kulcs, token, jelszó?
- Ideiglenes / teszt kód prodba kerülne?

Ha találsz → jelezd és kérdezd meg mit tegyen a user. Ne commitálj ilyennel.

## 4. Commit üzenet összeállítása

Ha van task fájl → **használd a task fájlban megadott commit üzenetet**.

Ha nincs task fájl, kövesd ezt a formátumot:

```
<type>(<scope>): <rövid összefoglaló, max 72 karakter>

<body — mit és miért, nem hogyan>
```

**Típusok:**
```
feat     új funkció
fix      bug javítás
docs     csak dokumentáció
test     csak tesztek
chore    konfiguráció, tooling, függőségek
data     data pipeline, API client változás
refactor viselkedés változás nélküli átírás
```

**Szabályok:**
- Imperatív mód: "add", "fix", "update" — NEM "added", "fixed"
- Body a *miértet* magyarázza, nem a *mit*
- Generikus üzenet tilos: "fix bug", "update code", "changes"

Mutasd meg a javasolt üzenetet és várj jóváhagyásra.

## 5. Commit végrehajtása

```bash
git add <konkrét fájlok>   # NEM: git add -A
git commit -m "<üzenet>"
git log --oneline -1        # megerősítés
```

## 6. Megerősítés

```
Commit: abc1234 — feat(close_positions): add TP/SL-aware MOC qty
Staged: 3 fájl (+47 -12)
Tesztek: N passing ✓
```

Van push is? → kérdezd meg a usert.

## Opciók

- `--no-verify` — quality gates kihagyása (csak indokolt esetben)
- `--amend` — előző commit módosítása
- `--push` — push is commit után

---

**Trigger:** "commit", "mentsd el", "commit this", vagy implementáció végén.
