# Archive

Ez a mappa a IFDS dokumentáció **historikus** anyagait tartalmazza, korszakvonalak szerint rendezve.

## Mappastruktúra

- **`pre-swing-pivot/`** — A 2026-05-14 Day 63 milestone outcome ELŐTTI időszak (W7-W20, kb. 2026-02-12 → 2026-05-14). Az intraday hybrid scoring architektúra dokumentumai. Lásd a [`pre-swing-pivot/README.md`](pre-swing-pivot/README.md)-t a részletekért.

## Mi NEM tartozik ide

- **Foundational reference**: a kvantitatív elemzéseket (scoring-validation, flow-decomposition, ticker-liquidity-audit, ETF universe design reasoning, sector rotation reasoning) a [`docs/foundational/`](../foundational/) tartalmazza. Ezek **referencia-szintű** anyagok, NEM archív — a Day 90 / Day 126 milestone értékelésen aktívan hivatkozottak lehetnek.

- **Day 63 outcome cornerstone**: a [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) **élő** dokumentum, a swing pivot architektúra forrása.

## Korszakváltások — időrendben

- **2026-02-12** (~Day -90): IFDS projekt indulás, kezdeti architektúra
- **2026-03-12** (~Day 1): első paper trading futás
- **2026-04-28**: Day 63 decision framework megfogalmazás (a Day 63 milestone értékelés előkészítése)
- **2026-05-08**: kvantitatív stratégiai review (60 napi paper trading után)
- **2026-05-14** (Day 63): milestone outcome — **swing pivot deklarálás**, korszakváltás
- **2026-05-15** (W21): Fázis 1 cleanup kickoff
- **2026-05-18** (W21 Day 1): swing pivot GO-LIVE

Az ezt megelőző dokumentumok az **archive/pre-swing-pivot/**-ban érhetők el.

## Visszakeresés

Ha bármilyen pre-Swing referenciát keresel:

```bash
# Régi task fájlok
ls archive/pre-swing-pivot/tasks/ | grep <keyword>

# Régi napi review-k
ls archive/pre-swing-pivot/reviews/

# Régi journal entry-k
ls archive/pre-swing-pivot/journal/

# Régi BC framework design-ok
ls archive/pre-swing-pivot/planning/
```

A `git log --follow <path>` parancs minden mozgatás után megőrzi az eredeti fájl-history-t.
