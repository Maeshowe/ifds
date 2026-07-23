# Biweekly Scoring-Validation Review-jegyzet — 2026-07-11

**Forrás**: `docs/analysis/scoring-validation.md` (regenerálva 2026-07-11, 465 trade, 465/465 SPY-joined) + `plots/`.
**Státusz-keret**: deskriptív anyag, NEM gate-input (exkluzív attribúciós út: `signal_attribution.py`, commit `c5e9ed0`). A minta **pooled** (legacy intraday + swing, swing-only szűrő nincs — Dev-chat backlog, Day 63-input). A §6.6 caveat érvényes.

## Review-oldali olvasat (leíró)

1. **Az „Evidence of alpha" auto-felirat félrevezető — megerősítve.** A score↔excess Pearson **−0,153\*\*** (p=0,001): szignifikáns, de **negatív** — a magasabb pooled score szignifikánsan rosszabb piac-semleges excess-t kísér. Ez a high-score paradox (Q5: −$1 288,83 total, 41,9% win; Q5−Q1 spread −$16,34/trade) folytonossága, nem alpha-bizonyíték. A felirat a szignifikanciát alpha-ként címkézi — display-hiba, a számok önmagukban helyesek.
2. **A jel nem robusztus**: Pearson −0,153\*\* mellett a Spearman **+0,009 (p=0,841)** — a rang-korreláció nulla, tehát a lineáris jelet valószínűleg outlier/farok-hatás viszi, nem monoton kapcsolat (`hipotézis`, a 04_score_vs_excess ábra vizuális ellenőrzésével összhangban vizsgálható).
3. **Komponens-bontás (271/465 enriched)**: flow −0,005 (nulla), tech **−0,148\***, funda **−0,126\*** — pooled, legacy-dominált mintán; a swing scoring (PCR + OTM-inverz) erre nem vetíthető, a bontás swing-rendszerbeli következtetésre alkalmatlan.
4. **Exit-címkézési eltérés a kanonikustól** ⚠️: a report TIME_STOP=3 / MENTAL_SL=1 sort mutat, miközben a swing-run ledgerében 7+ TIME_STOP és 2 MENTAL_SL zárult — `hipotézis:` a TIME_STOP_MOC→MOC bucketelés és/vagy join-címke eltérés; a report exit-táblája nem használható a `pending_exits`-kanonikus exit-statisztika helyett. (P3, a weekly_metrics-audit CC-task jelölttel közös család.)
5. **Belső display-inkonzisztencia** (P3): fejléc „32 trading days" vs Summary „71 trading days".

## Következmény
- Gate-döntéshez semmi nem használható belőle; a swing-only rekomputáció (Dev-chat backlog) előfeltétele bármilyen swing-releváns olvasatnak.
- A pooled negatív score↔excess jel iránya konzisztens a Day 63 legacy-verdikttel (r≈0 / high-score paradox) — új információt a swing rendszerről **nem** ad.
