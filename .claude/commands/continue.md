Session indítás és kontextus betöltés. Futtasd MINDIG a munkamenet legelején.

## 1. Journal kontextus betöltés

```bash
ls -t docs/journal/ 2>/dev/null | head -2 | while read f; do
  echo "=== $f ==="
  cat "docs/journal/$f"
done
```

Ha a `docs/journal/` könyvtár nem létezik vagy üres, hagyd ki.

## 2. Nyitott taskok

```bash
grep -rl "Status: OPEN\|Status: WIP" docs/tasks/ 2>/dev/null
```

## 3. Gyors állapot

```bash
python -m pytest tests/ -q 2>/dev/null | tail -1
git log --oneline -3
```

## 4. Mutasd tömören (max 10 sor)

- **Előző session**: utolsó journal entry 1 soros summary-ja
- **Nyitott taskok**: lista (ha van)
- **Tesztek**: N passing
- **Utolsó commit**: hash — üzenet
- **Folytatás**: „Mivel folytatjuk?"

Legyél tömör — a user tudja mi a projekt.
