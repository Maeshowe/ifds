Status: DONE
Updated: 2026-10-18
Note: KÉSZ. A kilépés NEM ingyenes (+50,0 bp előjelesen), de a nagyobb lelet, hogy a median|.| BECSLŐ duplázza a költséget — a SIM-1 dollár-könyvelése (41,0 bp) az előjeles számmal egyezik. A fal 0,280 -> 0,148. A 2. lépés. A motor `2c`-t terhel (a kilépést a belépéssel azonos árúnak veszi) — a kilépési oldalt SOHA nem mértük. Read-only mérés, nem módosít kereskedési logikát.

# A valódi round-trip költség — a soha nem mért kilépési oldal

## 1. A kérdés

A `breakeven_ic = 2c/(σ_cs·1e4)` **feltételezi, hogy a kilépés ugyanannyiba kerül, mint
a belépés** (`2 × 83,5 = 167 bp`). Ez **feltevés, nem mérés** — a kilépési oldalról
egyetlen szám sincs. Ha a valódi round-trip lényegesen alacsonyabb, a fal arányosan esik.

## 2. 🔴 Estimand-fegyelem (a 2026-10-04-i hiba megismétlésének elkerülése)

A meglévő két szám **nem összemérhető**:

| Szám | Referencia | Mit mér |
|---|---|---|
| belépési **83,5 bp** | a plan `limit_price`-a (12:30 UTC) | **döntés → fill**: drift + végrehajtás |
| SIM-1 exit **6,6 / 61,2 bp** | az ordertípus ígérte ár (close / open) | **csak végrehajtás** |

Ezért **három**, külön nevesített számot mérek **mindkét oldalon**:

1. **Implementation shortfall** — döntési ár → fill. **Ez a gazdaságilag helyes
   költség** egy forgás-terheléshez, és ez megy a `cost_model`-be.
2. **Execution slippage** — az ordertípus referenciája → fill. Ez a bróker/helyszín ára.
3. **Delay cost** = (1) − (2). A döntés és a végrehajtás közti elsodródás.

## 3. A döntési pont levezetése (cronból + kódból)

| Exit-típus | Flag mikor | Submit | Fill | **Döntési ár** |
|---|---|---|---|---|
| `TIME_STOP` | D−1 **20:00 UTC** eod_eval, D−1 close-zal | D 19:40 UTC | D close (19:59 UTC) | **D−1 close** |
| `TP1/TP2/MENTAL_SL/TRAIL_SL` | D **20:00 UTC** eod_eval, D close-zal | D+1 13:30 UTC | D+1 open | **D close** |

Egységesen: **a döntési ár a fill-session ELŐTTI session záróára.**

> ⚠️ **Aszimmetria, ami maga is lelet:** a belépő referenciája ~1 órával a fill előtti
> (azonos session), a kilépőé **egy teljes sessionnel** korábbi. A kilépési döntés tehát
> lényegesen hosszabb drift-kitettséget hordoz — ez **nem a mérés hibája, hanem a
> rendszeré**.

## 4. Adatforrások

| Mennyiség | Forrás |
|---|---|
| exit lábak (típus, qty, dátum) | `state/pending_exits/*.json` (bróker-autoritatív) |
| fill ár + `fill_time` | `state/daily_metrics/{d}.json → trades.details[]` |
| döntési ár + ordertípus-referencia | `research/cache/.../grouped_daily` (close / open) |
| belépési oldal | `daily_metrics.execution.slippage_per_ticker` (meglévő) |

## 5. Implementációs terv

- [x] `tests/test_roundtrip_cost.py` — TDD a döntési-pont feloldásra és a 3 metrikára
- [x] `scripts/analysis/roundtrip_cost.py` — mérés + riport
- [x] Adat-egészség: a fill essen a saját napi sávjába (a SIM-1 health-check analógja)
- [x] A hatás a falra: `breakeven = (c_entry + c_exit)/(σ_cs·1e4)` a mért `2c` helyett
- [x] Riport `docs/review/2026-10-18-roundtrip-cost.md` + `04-risks` §11.29

## 6. Amit ez NEM dönt el

A mért költség **nem** teszi nyereségessé a könyvet (a jel null). A tét az, hogy a
**jövőbeli** gazdasági kapu milyen falat használjon — és hogy a 2-es lépés után
tudjuk-e, mennyit ér a végrehajtási oldal javítása.

## 7. Commit üzenet

```
feat(analysis): a valódi round-trip költség — a soha nem mért kilépési oldal

Három külön nevesített metrika mindkét oldalon (implementation shortfall,
execution slippage, delay cost), hogy a belépési 83,5 bp és a kilépési szám
ugyanazon a konvención álljon.
```
