# IFDS Master Reference Card — Index

**Verzió**: 1.1 (Day 63 outcome + Swing pivot)
**Utoljára frissítve**: 2026-05-14
**Frissítési felelős**: Chat (Claude) — eseményalapú + heti péntek 22:00 weekly metric után
**Cél**: a rendszer **aktuális állapotának** egyetlen "source of truth"-a. Tamás, Chat, CC és csapat ehhez fordul.

> **Korszakváltás (2026-05-14)**: a Day 63 milestone outcome alapján a rendszer **swing pivot**-ot indít (3-5 napi hold, PCR + OTM-inverse scoring, mental stop, rolling 10-12 sizing). A részletes döntési dok: [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md). A `01-system-snapshot.md` és `02-exit-mechanics.md` a **Fázis 3 deploy után** (kb. 2026-06-23, W26) frissítődik az új swing architektúrára; addig a régi rendszert tükrözik.

---

## A 4 dokumentum

| # | Fájl | Tartalom | Karbantartás |
|---|------|----------|---------------|
| 1 | [`01-system-snapshot.md`](01-system-snapshot.md) | Aktuális paraméter-snapshot, scoring kompozíció, multiplier chain | Eseményalapú: minden CC commit / paraméter-tuning után |
| 2 | [`02-exit-mechanics.md`](02-exit-mechanics.md) | Exit-mechanika állapot-diagram, T1/T2/SL/LossExit/MOC trigger-ek | Eseményalapú: minden exit logika változás után |
| 3 | [`03-day63-status.md`](03-day63-status.md) | Day 63 keret, jelenlegi mérőszámok, döntési kritériumok | Heti: péntek 22:00 weekly metric után |
| 4 | [`04-risks-and-open-questions.md`](04-risks-and-open-questions.md) | Aktív kockázatok, nyitott kérdések, P1 backlog | Eseményalapú: minden új finding / debug eredmény után |

## Kapcsolódó dokumentumok (NEM része a master reference-nek, csak link)

| Cél | Dokumentum |
|-----|-----------|
| Stratégiai irány | [`docs/strategic-review/2026-05-08-strategic-review-full.md`](../strategic-review/2026-05-08-strategic-review-full.md) (25 oldal) |
| Stratégiai exec summary | [`docs/strategic-review/2026-05-08-strategic-review-summary.md`](../strategic-review/2026-05-08-strategic-review-summary.md) (5 oldal) |
| Aktuális állapot | [`docs/STATUS.md`](../STATUS.md) |
| API stratégia | [`docs/API_STACK.md`](../API_STACK.md) (frissítendő, 2026-03-01-i!) |
| Backlog | [`docs/planning/backlog-ideas.md`](../planning/backlog-ideas.md) |
| Roadmap | [`docs/planning/roadmap-2026-consolidated.md`](../planning/roadmap-2026-consolidated.md) |
| Day 63 framework | [`docs/decisions/2026-04-28-day63-decision-framework.md`](../decisions/2026-04-28-day63-decision-framework.md) |
| Daily review-k | [`docs/review/`](../review/) |
| Heti elemzések | [`docs/analysis/weekly/`](../analysis/weekly/) |
| Scoring validation | [`docs/analysis/scoring-validation.md`](../analysis/scoring-validation.md) |
| Flow al-komponens | [`docs/analysis/flow-decomposition.md`](../analysis/flow-decomposition.md) |
| Linda Raschke elv | [`docs/references/raschke-adaptive-vs-automated.md`](../references/raschke-adaptive-vs-automated.md) |

## Hogyan használd

**Tamás (PO):**
- **Reggel**: `03-day63-status.md` áttekintés (Day, kumulatív, VIX állás)
- **Stratégiai döntés előtt**: `04-risks-and-open-questions.md` átolvasása
- **Új paraméter-tuning gondolat előtt**: `01-system-snapshot.md` ellenőrzése (mit változott legutóbb)

**Chat (orchestrator):**
- **Daily review írásakor**: `01` és `03` referenciaként
- **Backlog frissítéskor**: `04` szinkronizálása a backlog-ideas.md-vel
- **Heti weekly review után**: `03` mérőszámok frissítése

**CC (implementátor):**
- **Új feature előtt**: `01` ellenőrzése (ne duplikáljon meglévő logikát)
- **Commit után**: a változott szakasz **frissítendő** (Chat felelős, de CC jelezhet)

**Csapat (külső):**
- **Onboarding**: `01` → `02` → `03` sorrend (~30 perc átolvasás)
- **Egy konkrét kérdés**: a fenti táblázat alapján a megfelelő fájl

## Frissítési protokoll

**Eseményalapú frissítés** (CC bármikor jelezheti):
1. Egy paraméter-tuning a `defaults.py`-ban → **`01-system-snapshot.md`** táblázat soros frissítése
2. Egy exit-logika módosítás → **`02-exit-mechanics.md`** állapot-diagram update
3. Egy P1 backlog idea státusz-változás → **`04-risks-and-open-questions.md`** sor update
4. Egy stratégiai döntés (pl. UW marad/kannibalizál) → érintett fájl(ok) update

**Heti frissítés** (Chat, péntek 22:00 weekly metric után):
1. **`03-day63-status.md`** — kumulatív P&L, win rate, excess, VIX átlag, BMI átlag
2. Konzisztencia-check: az eseményalapú frissítések mind beépültek-e
3. Backlog (a `04`-ben) szinkronban van-e a `backlog-ideas.md`-vel

**Mérföldkő frissítés** (Chat + Tamás, Day 63 / Day 90 / Day 120 után):
1. Mind a 4 dokumentum **teljes átfutása**
2. A stratégiai review (`docs/strategic-review/`) frissítése, ha lényeges változás
3. Egy "Master Reference v2.0" verziójelölés, ha a struktúra is változik

---

**A dokumentum vége.**
