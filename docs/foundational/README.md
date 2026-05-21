# Foundational

Ez a mappa **referencia-szintű** kvantitatív elemzéseket és architektúra-design reasoning-et tartalmaz, ami a 2026-05-14 Day 63 outcome doc és a swing pivot architektúra **kvantitatív alapját** adja.

**NEM archív** — bár a fájlok jelentős része pre-2026-05-14 dátumú, az itt tárolt elemzések **aktívan hivatkozottak** lehetnek a Day 90 / Day 126 milestone értékelésen.

**Karakter**: időtlenebb, NEM time-bounded. A reasoning a swing pivot architektúrát **fundamentálisan alátámasztja**, ezért **megőrzendő aktív referenciaként**.

## Mappastruktúra

```
foundational/
├── analysis/                          # 21 fájl + plots/ + weekly/
│   ├── scoring-validation.md          # ⭐ Pearson r ≈ 0, Kelly f* negatív (kvantitatív alapcáfolat)
│   ├── flow-decomposition.md          # PCR + OTM-inverse kiderítés (a swing scoring alapja)
│   ├── dp-pct-retrospective-audit.md  # UW dark pool signal inverzió finding (a Day 90 calibration alapja)
│   ├── ticker-liquidity-audit*.{md,csv}  # univerzum-méretezés reasoning
│   ├── uw-api-inventory-v2.md         # UW API endpoint dokumentáció
│   ├── loss-exit-whipsaw-analysis.md  # a régi loss-exit mechanika cáfolata
│   ├── mid-vs-ifds-sectors-W18.md     # MID integration előkészítés
│   ├── scoring-validation-bc23-w16.md # a BC23 redesign kvantitatív megfigyelése
│   ├── spy_returns.json               # benchmark adat
│   ├── plots/                         # statisztikai grafikonok
│   └── weekly/                        # heti aggregáció riportok
│
├── strategic-review/                  # 3 fájl
│   ├── 2026-05-08-strategic-review-summary.md      # 5 oldalas vezetői összefoglaló
│   ├── 2026-05-08-strategic-review-full.md         # 25 oldalas teljes elemzés
│   └── 2026-05-08-strategic-review-mathematical.md # matematikai dekonstrukció
│
└── planning/                          # 3 fájl
    ├── etf-universe-design.md         # S&P 500 + R1000 univerzum reasoning
    ├── sector-rotation-logic.md       # sector rotation kvantitatív reasoning
    └── learnings-archive.md           # gyűjtött tanulságok historikus referencia
```

## Mit használjon belőle ki, mikor

### Day 90 milestone értékelés (~2026-08-26)
- `analysis/scoring-validation.md` — a régi rendszer Pearson r ≈ 0 cáfolat, a swing pivot összehasonlítási alapja
- `analysis/dp-pct-retrospective-audit.md` — UW dark pool signal kalibráció kontextusa
- `strategic-review/2026-05-08-strategic-review-*.md` — a Day 63 outcome doc forrásai, az új architektúra reasoning-jét részletesen indokolják

### Day 126 milestone értékelés (~2026-09-15, first GO/NO-GO)
- `analysis/scoring-validation.md` — a swing pivot vs régi rendszer kvantitatív összehasonlítás reproduceálható módszerei
- `strategic-review/2026-05-08-strategic-review-mathematical.md` — matematikai keretrendszer a "5 napi hold mutual information 5× erősebb" reasoning-hez

### Tervezési munkák
- `planning/etf-universe-design.md` — ha az S&P 500 + R1000 univerzumot bővíteni vagy szűkíteni akarjuk
- `planning/sector-rotation-logic.md` — ha a Phase 3 sector rotation logikát módosítjuk (pl. a MID ETF X-Ray integration `tasks/future-2026-04-17-bc-ifds-phase3-from-mid.md` keretében)

## Hivatkozási konvenció

Új tervezési doc-okból a `docs/foundational/` **explicit hivatkozható**. Példa:

```markdown
A scoring egyszerűsítését indokolja a [scoring validation](../foundational/analysis/scoring-validation.md)
Pearson r ≈ 0 finding-je (60 napi minta, p=0.996, Bonferroni minimum).
```

## NEM tartozik ide

- **Aktív backlog**: a `docs/planning/backlog.md` + `backlog-ideas.md` a post-Day-63 aktív tervezést tartalmazza
- **Aktív task-ok**: a `docs/tasks/` minden W21+ aktív task
- **Élő decisions**: a `docs/decisions/2026-05-14-day63-decision-outcome.md` cornerstone
- **Élő design**: a `docs/design/swing-pivot-architecture.md`

Ha bármi pre-2026-05-15-i tartalmat találsz a `foundational/`-on belül, ami **NEM** referencia-szintű (pl. csak régi tervezési vázlat), érdemes a `docs/archive/pre-swing-pivot/`-ba átsorolni.

---

*Frissítve: 2026-05-22 (Day 4 W21 docs reorganizáció)*
