Tesztek futtatása és eredmények értelmezése.

## 1. Futtatás
```bash
python -m pytest --tb=short -q
```

## 2. Eredmény értelmezése
Az output-ból olvasd ki:
- **total_tests:** összes futtatott teszt
- **passed:** sikeres tesztek
- **failed:** bukott tesztek
- **errors:** hibás tesztek (nem assertion failure, hanem error)
- **skipped:** kihagyott tesztek
- **duration_seconds:** futási idő másodpercben

## 3. Bemutatás
- Ha ZÖLD: "N teszt zöld (X.Xs)"
- Ha PIROS: "N teszt, ebből F bukott, E error. Bukott tesztek: [lista]"
- Ha vannak failure-ök → adj konkrét javítási javaslatot
