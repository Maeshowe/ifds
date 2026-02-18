# Task: SIM-L2 First Meaningful Comparison Run

**Date:** 2026-03-02 (hétfő)
**Priority:** LOW — manuális futtatás, nem CC task
**Előfeltétel:** ~15 kereskedési nap execution plan CSV (feb 11 → feb 28)

---

## Parancs

```bash
cd /Users/safrtam/SSH-Services/ifds && rm -rf data/cache/polygon/aggregates && .venv/bin/python -m ifds compare --config sim_variants_test.yaml
```

**Fontos:** A `rm -rf data/cache/polygon/aggregates` szükséges, mert a cache forward-looking date range-eket tárol, amik a futtatás napján még hiányosak lehetnek. Friss API fetch kell minden futtatás előtt.

## Várható adatmennyiség (márc 2-ra)

- ~14 execution plan CSV (feb 11-28, hétvégék és Presidents' Day nélkül)
- ~80-100 trade
- ~15 kereskedési nap bar per ticker
- Paired t-test sample: elég a szignifikancia-teszthez (n ≥ 30)

## Mit nézzünk az eredményben

1. **P&L irány:** Melyik variáns (baseline/wide/tight) a legjobb?
2. **Leg2 WR:** Eléri-e valamelyik variáns a TP2-t 15 nap alatt?
3. **p-value:** < 0.05 jelent szignifikáns különbséget
4. **Fill rate:** Változik-e a variánsok között?

## Backlog: cache TTL fix

A forward-looking date range cache probléma (`to_date > today`) rendszerszintű fix-et igényel. Nem blokkoló — `rm -rf` workaround működik. BC19 vagy BC20 scope.
