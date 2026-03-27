---
Status: DONE
Updated: 2026-03-26
Note: Root cause: universe rotation → max 16/30 entries. Fix: mms_min_periods 21→10, 51 tickers activate.
---

# MMS Undetermined Investigation — Miért nincs hatása a BC18B-nek?

## Probléma

A BC18B (MMS activation) deployolása óta (2026-03-23) az MMS rezsim **minden
tickernél UND (undetermined)** — 3 egymás utáni napon 100/100. Ez azt jelenti,
hogy a `mms_enabled: True` config flag nem hat: sem a regime multiplierek
(Γ⁺ ×1.5, Γ⁻ ×0.25 stb.), sem a factor volatility nem dolgozik.

A `mms_min_periods: 21` küszöb tickerenként értendő — egy tickernek 21-szer
kell átmennie Phase 5-ön ahhoz, hogy z-score-okat számoljon. Ha a universe
naponta változik (más tickerek kerülnek be Phase 4-en), sok ticker soha nem
éri el a 21-et.

## Vizsgálat

### 1. state/mms/ felmérés

```bash
# Hány ticker van a store-ban?
ls state/mms/ | wc -l

# Hány entry-je van a top tickereknek?
for f in state/mms/*.json; do
    ticker=$(basename "$f" .json)
    count=$(python3 -c "import json; print(len(json.load(open('$f'))))")
    echo "$ticker: $count"
done | sort -t: -k2 -n -r | head -20

# Hány tickernek van >=21 entry-je?
for f in state/mms/*.json; do
    count=$(python3 -c "import json; print(len(json.load(open('$f'))))")
    if [ "$count" -ge 21 ]; then
        echo "$(basename "$f" .json): $count"
    fi
done
```

### 2. MMS store gyűjtés ellenőrzés

Ellenőrizd, hogy a napi pipeline futás tényleg ír-e az MMS store-ba:

```bash
# Mai dátum szerepel-e a store entry-kben?
python3 -c "
import json, os
mms_dir = 'state/mms'
today = '2026-03-25'
found = 0
for f in os.listdir(mms_dir):
    entries = json.load(open(os.path.join(mms_dir, f)))
    dates = [e.get('date') for e in entries]
    if today in dates:
        found += 1
print(f'{found} ticker(s) have entry for {today}')
"
```

### 3. Phase 5 MMS dispatch ellenőrzés

A `phase5_gex.py` dispatch-eli az MMS-t — ellenőrizd, hogy a `_run_mms_analysis()`
tényleg meghívódik-e minden tickerre, és az MMS store `append_and_save()` fut-e.

## Lehetséges fix

A vizsgálat eredményétől függ:

### A) Ha a tickerek 10-15 entry körül tartanak (lassú akkumuláció)
→ `mms_min_periods` csökkentése: 21 → 10
→ Config: `defaults.py` CORE szekció `"mms_min_periods": 10`
→ Trade-off: kevésbé stabil z-score, de legalább működik

### B) Ha a store üres vagy alig van benne adat
→ A pipeline nem hívja meg az MMS store-t — kód bug Phase 5-ben
→ `phase5_gex.py` és `phase5_mms.py` debug

### C) Ha sok tickernek van >=21 entry-je, de mégsem aktiválódik
→ A `classify_regime()` baseline check hibás — a `BaselineState.READY`
feltétel nem teljesül, vagy az `mms_enabled` flag nem propagálódik

## Tesztelés

1. `state/mms/` felmérés script — manuálisan futtatva a MacBook-on
2. Ha fix szükséges (min_periods csökkentés): unit test `mms_min_periods=10`
3. Ha kód bug: Phase 5 MMS dispatch integration test
4. Pipeline futtatás fix után — MMS rezsim eloszlás a logban (nem 100% UND)
5. Meglévő tesztek: 1034+ passing — regresszió

## Commit üzenet

```
fix(phase5): resolve MMS undetermined 100% — [oka a vizsgálattól függ]

MMS regime was undetermined for all tickers since BC18B activation.
Root cause: [vizsgálat eredménye].
Fix: [amit csinálunk].
```

## Érintett fájlok

- `state/mms/` — vizsgálat, nem módosítás
- `src/ifds/config/defaults.py` — ha min_periods csökkentés
- `src/ifds/phases/phase5_mms.py` — ha kód bug
- `src/ifds/phases/phase5_gex.py` — ha dispatch bug
- `tests/` — fix-specifikus tesztek