# BC23 Heti Metrika Elemzés — 2026-W16 (ápr 13-17)

**Ez az első teljes hét a BC23 deploy után.** Az eredmények vegyesek — az abszolút P&L kiemelkedő, de a piaci kontextusban aggasztó jelek vannak.

## Abszolút számok (pozitív)

- Gross P&L: +$1,720.70
- Net P&L (commission után): +$1,661.16
- Kumulatív: -$2,415 → **-$694.53 (-0.69%)** — egy hét alatt 71% visszanyerés
- 4/5 nyereséges nap
- Commission: $59.54 (4% a gross P&L-hez képest, vs régi 8.4% éves drag)
- Átlag slippage: +0.06%

## Piaci kontextus (aggasztó)

### SPY-adjusted Excess Return: **-2.73%**

- Portfólió heti: +1.72%
- SPY heti: +4.45%
- **Alulteljesítés**: a piac bull volt, és a rendszer kevésbé nyert mint egy passzív SPY ETF

Ez azt jelenti, hogy a BC23 előtti (-$60/nap) → BC23 utáni (+$344/nap) fordulat **nagy része nem a rendszer javulása, hanem a piac javulása**. A VIX 20-ról 18-ra esett, a SPY 4.5%-ot ment.

### Score→P&L korreláció: **r = -0.414**

**Negatív korreláció** a magasabb score és a P&L között — az inverz quintilis minta nem tűnt el a BC23-mal. Példák:

- Ápr 16: TIGO (91.0, legalacsonyabb) → +$412, legnagyobb nyerő
- Ápr 17: BALL (95.0, legmagasabb) → -$91, legnagyobb vesztes
- Heti átlag: 94.5 score → flat, 91.0 score → nyerő

### TP1 hit rate: 0/18 (0%)

Az új TP1 1.5×ATR egyszer sem ütött be a héten. 18 trade, 18 MOC exit. Az 1.5×ATR lehet túl agresszív az intraday mozgásokhoz.

## Összesítés

| Metrika | Eredmény | Értékelés |
|---------|----------|-----------|
| Abszolút P&L | +$1,721 | 🟢 Kiemelkedő |
| Win rate (napok) | 4/5 (80%) | 🟢 Jó |
| Commission ratio | 4% | 🟢 Javulás |
| Slippage | +0.06% | 🟢 Kiváló |
| **Excess vs SPY** | **-2.73%** | 🔴 **Alulteljesítés** |
| **Score korreláció** | **r=-0.414** | 🔴 **Negatív, nem prediktív** |
| **TP1 hit rate** | **0%** | 🔴 **TP1 túl magas** |

## Következtetés

A BC23 **mechanikailag működik** — kevesebb trade, alacsonyabb commission, jobb slippage, stabil pipeline. 

Azonban a **stock selection edge NEM bizonyított**. A pozitív abszolút P&L nagy részben a piac bullish mozgásából fakad, nem a rendszer kiválasztási képességéből. Ha a jövő hét bearish lesz, a rendszer várhatóan alulteljesít.

## Akciók

**Most (hétvégén):**
- Scoring validáció újrafuttatása az új live adatokkal (5 nap BC23) — a -0.414 korreláció érdemel mélyebb vizsgálatot

**Jövő héten (ha a minta tart):**
- TP1 csökkentés 1.5 → 1.25×ATR (ha a TP1 hit rate <5% 2 hét után)
- Dynamic threshold felülvizsgálat (85 → 88, vagy 85 → 80) — a szűk 90-95 sávban nincs differenciálás

**Hosszú távon:**
- Flow al-komponens dekompozíció (BC23 Phase 4, még nyitott CC task)
- Ha egyik flow al-komponens sem prediktív → a scoring koncepciót kell újragondolni

## Fontos megjegyzés

Ez az **első teljes BC23 hét**. Egy hét nem bizonyíték egyikre sem. A jövő hét (ápr 20-24) heti metrika kritikus:

- Ha SPY bearish + rendszer flat/pozitív → van edge
- Ha SPY bullish + rendszer még tovább alulteljesít → nincs edge
- Ha SPY flat + rendszer flat → status quo

**Ne ünnepeljünk korán.** A nyerő hét nem azt jelenti, hogy a rendszer jó — azt jelenti, hogy a piac jó volt.
