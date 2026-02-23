# Task: OBSIDIAN Store — Feb 16 bejegyzések törlése

**Dátum:** 2026-02-23  
**Prioritás:** HIGH  
**Típus:** Adattisztítás, nem kód változtatás  

---

## Háttér

2026-02-16 Presidents' Day volt — az amerikai tőzsde zárva tartott. A cron (`0 10 * * 1-5`) ennek ellenére lefuttatta a pipeline-t, és stale (Feb 13-i) adatokat gyűjtött be az OBSIDIAN store-ba. Ez a futás nem érvényes kereskedési nap, törölni kell mintha hétvége lett volna.

## Feladat

Minden JSON fájlból a `state/obsidian/` könyvtárban töröld ki a `"date": "2026-02-16"` bejegyzést, ha létezik.

## Implementáció

```python
import json
import os
from pathlib import Path

store_dir = Path("state/obsidian")
removed_count = 0
files_modified = 0

for fpath in sorted(store_dir.glob("*.json")):
    with open(fpath) as f:
        entries = json.load(f)
    
    filtered = [e for e in entries if e["date"] != "2026-02-16"]
    
    if len(filtered) < len(entries):
        # Atomikus írás
        tmp = fpath.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(filtered, f, separators=(",", ":"))
        os.replace(tmp, fpath)
        removed_count += len(entries) - len(filtered)
        files_modified += 1

print(f"Módosított fájlok: {files_modified}")
print(f"Törölt bejegyzések: {removed_count}")
```

Futtasd az IFDS repo gyökeréből:
```bash
cd /Users/safrtam/SSH-Services/ifds
python -c "$(cat docs/tasks/2026-02-23-obsidian-remove-feb16.md | grep -A30 '```python' | tail -n+2 | head -n-1)"
```

Vagy egyszerűbben, másold ki a Python kódot egy temp scriptbe és futtasd.

## Ellenőrzés

Futtatás után:
```bash
grep -l "2026-02-16" state/obsidian/*.json | wc -l
```
Eredménynek **0**-nak kell lennie.

## Várható eredmény

- Érintett fájlok: ~100-200 ticker (nem minden tickernél volt Feb 16-i entry)
- OBSIDIAN store érvényes futásnapjai: Feb 11, 12, 13, 17, 18, 19, 20, 23
- OBSIDIAN állás: **Day 8/21** (változatlan — a Feb 16-i stale nap amúgy sem számított volna)

## Megjegyzés

A jövőbeli ismétlődést a BC18-prep `trading_calendar.py` (`is_trading_day()`) megakadályozza — a deploy_daily.sh már nem fut ünnepnapon. Ez a task egyszeri adattisztítás.
