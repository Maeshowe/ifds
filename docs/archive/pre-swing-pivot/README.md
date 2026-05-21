# Pre-Swing-Pivot Archive

A IFDS dokumentáció **2026-05-14 Day 63 milestone outcome ELŐTTI** anyagai.

**Időszak**: W7-W20 (kb. 2026-02-12 → 2026-05-14)
**Archiválva**: 2026-05-22 (Day 4 W21 swing pivot deploy stabilizálás után)
**Architektúra**: intraday hybrid scoring (Phase 4-6 6-órás holding period, IBKR bracket order TP1/TP2/SL, multiplier chain M_VIX × M_GEX × M_target × M_contradiction)

## Miért archiválva?

A 2026-05-14 Day 63 milestone outcome **strukturálisan korszakváltó**: a kvantitatív elemzés (Pearson r ≈ 0, p=0.996 a kompozit score-on, negatív Kelly criterion) megmutatta, hogy az intraday hybrid scoring **nem deployolható**. A swing pivot (3-5 napi hold, mental stop, PCR + OTM-inverse percentile scoring, sector-balanced greedy sizing) **fundamentális architektúra-váltás**.

A pre-Swing dokumentumok **referencia-szintű historikus értékkel** bírnak, DE az aktív fejlesztési scope-ra **NEM relevánsak**. Az archiválás célja a `docs/` aktív területének **noise-csökkentése**, nem a tartalom törlése.

## Mappastruktúra

```
pre-swing-pivot/
├── tasks/        # ~102 task fájl (2026-02 → 2026-05-08)
├── reviews/      # Day 1-63 napi review-k (~38 fájl, 2026-03..2026-05-14)
├── journal/      # CC session-close summaries (~55 fájl, 2026-02-12..2026-05-13)
├── decisions/    # 2026-04-28 Day 63 framework (a 2026-05-14 outcome elnyelte)
├── handoff/      # 2026-05-08 strategic review handoff (a Day 63 outcome elnyelte)
├── planning/     # Régi BC framework design-ok (BC22 HRP, BC23 scoring, SimEngine L2,
│                 # swing hybrid exit, trailing stop, crowdedness, dev backlog)
│   └── legacy-archive/  # A meglévő `planning/archive/` sub-mappa korábbi rétege
└── qa/           # 2026-02-26/27 pre-deploy QA review csomag (8 fájl)
```

## Visszakeresési útmutató

### Történelmi BC framework design-ok
- **BC22 HRP Allocation** (Hierarchical Risk Parity): `planning/bc22-hrp-allocation-design.md` — a swing pivot egyszerű 30% sector notional cap-pel váltotta le.
- **BC23 Scoring/Exit Redesign**: `planning/bc23-scoring-exit-redesign.md` — a swing pivot Bonferroni-minimum scoring + mental stop architektúrával váltotta le.
- **SimEngine L2 Design**: `planning/simengine-l2-design.md` — a 60-napi SIM-L2 paper trading futtatás-keretrendszer.
- **Swing Hybrid Exit (Day 63-ELŐTTI!)**: `planning/swing-hybrid-exit-design.md` — NEM összekeverendő a mostani swing pivot-tal. Ez a 2026-02-19-i kísérleti hybrid intraday/overnight exit logika.
- **Trailing Stop Design**: `planning/trailing-stop-design.md` — a swing pivot eliminálta a bracket trail SL-t.

### Napi review-k (Day 1-63)
A `reviews/` mappa a 2026-03-12 (Day 1) → 2026-05-14 (Day 63) közötti napi paper trading review-kat tartalmazza. Egyenként ~5-10 KB, kvantitatív megfigyelésekkel. A Day 63 milestone outcome `docs/decisions/2026-05-14-day63-decision-outcome.md` ezek összegzéséből készült.

### CC session-close journal entry-k
A `journal/` mappa a CC `/wrap-up` parancs outputjait tartalmazza session-enként. A 2026-02-12 → 2026-05-13 időszak tartalmazza az architektúra fejlődésének **gondolati nyomvonalát**. Day 90 milestone értékelésen hasznos referencia lehet a "miért lett kvantitatív vakvágány a régi rendszer" kérdés rekonstruálásához.

## Hivatkozási útmutató

A pre-Swing dokumentumok **NEM hivatkozandók** új tervezési doc-okból (kivéve magyarázó/oktató szándékkal). Ha valamit foundational értékkel rendelkezőnek ítélsz, vidd át a `docs/foundational/`-ba — NEM hagyd archív-ban.

A `docs/decisions/2026-05-14-day63-decision-outcome.md` (cornerstone) a swing pivot architektúra teljes reasoning-ját tartalmazza, beleértve a régi rendszer kvantitatív cáfolatát is.

---

*A `git log --follow <archív-path>` minden mozgatás után az eredeti history-t megőrzi.*
