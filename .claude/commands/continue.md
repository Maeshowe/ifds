Session indítás és kontextus betöltés. Futtasd MINDIG a munkamenet legelején.

```bash
python -m conductor continue --project-dir .
```

## Journal kontextus betöltés
Az utolsó 1-2 journal entry-t olvasd el a stratégiai kontextusért:
```bash
ls -t docs/journal/ 2>/dev/null | head -2 | while read f; do echo "=== $f ==="; cat "docs/journal/$f"; done
```
Ha a `docs/journal/` könyvtár nem létezik vagy üres, hagyd ki ezt a lépést.
A journal tartalmazza a Chat session-ök döntéseit és kontextusát — ezek a "miértek".

Parse the JSON output és mutasd tömören:
- **Előző session**: summary (1 sor)
- **Open tasks**: ha van, listázd (ha nincs, ne említsd)
- **Active decisions**: ha van (ha nincs, ne említsd)
- **Rules**: ha van új rule az előző session óta
- **Új session**: #ID elindítva

Legyél tömör — max 5-8 sor. A user tudja mi a projekt, nem kell újra elmagyarázni.
Ha CONDUCTOR nincs inicializálva, futtasd: `python -m conductor init --project-dir .`
