Session indítás és kontextus betöltés. Futtasd MINDIG a munkamenet legelején.

## 1. Journal kontextus betöltés
Olvasd el az utolsó 2 journal entry-t a stratégiai kontextusért:
```bash
ls -t docs/journal/ 2>/dev/null | head -2 | while read f; do echo "=== $f ==="; cat "docs/journal/$f"; done
```
Ha a `docs/journal/` könyvtár nem létezik vagy üres, hagyd ki ezt a lépést.

## 2. Aktuális állapot
Olvasd el a CLAUDE.md "Aktuális Kontextus" szekciót az aktív task-okért és státuszért.

## 3. Mutasd tömören (max 8 sor):
- **Előző session**: utolsó journal entry 1 soros summary-ja
- **Open tasks**: CLAUDE.md-ből (ha van)
- **Folytatás**: "Mivel folytatjuk?"

Legyél tömör — a user tudja mi a projekt, nem kell újra elmagyarázni.
