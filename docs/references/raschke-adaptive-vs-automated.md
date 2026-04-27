# Linda Raschke — Adaptive Trading Over Pure Automation

**Forrás:** Linda Bradford Raschke, hedge fund manager (Barclay Hedge ranking: 17/4500). LinkedIn poszt / interjú részlet, 2025. Az IFDS projekt kontextusába felvéve: 2026-04-24.

**Hivatkozási kontextus:** Schwager *The New Market Wizards* (1992) — Raschke volt a könyvben szereplő egyik trader. 30+ év éles tapasztalat különböző piaci regime-kben (1987 crash, 2000 dot-com, 2008, 2020 COVID, 2022 inflation).

---

## Az idézet

> Most people assume the more automated a trading system, the better. Remove the human, remove the emotion, improve the results.
>
> Linda disagrees. Not because she's undisciplined. She runs three separate trading programs built on modeling and systematic rules.
>
> But she keeps discretionary elements because of one thing: **markets change.**
>
> "Human behavior has changed. Markets have changed. You see a lot more urgency and range expansion than you did 20 years ago. Humans adapt faster than systems."
>
> A fully automated system trades the market it was built on. When that market changes its behavior, the system doesn't notice.
>
> The human does.
>
> Her edge isn't in beating the system at its own game. It's in knowing when the environment the system was designed for no longer exists.
>
> This isn't an argument against automation. It's an argument for understanding what automation can and can't do.
>
> Systems apply rules consistently. Humans notice when the rules no longer apply to the current environment.
>
> The best traders she's studied aren't the most automated. **They're the most adaptive.**

---

## Miért fontos ez az IFDS-nek

**Ez nem egy motivációs idézet, hanem egy operatív elv.**

Az IFDS architektúra **explicit human-in-the-loop**: a pipeline (Phase 0-6) automatizált, de a stratégiai döntések — BC sorrend, scoring változtatások, deploy időzítés, paper/éles átállás — **emberi judgment**-hez kötöttek. Ez nem véletlen, és nem fejlesztési szakaszproblema. Ez **strukturális szándék**.

### Konkrét példák W17-ből

A 2026-04-20 — 2026-04-24 hét során 5 olyan helyzet volt, ahol az automatikus rendszer önmagában **nem vette észre** a problémát, de a human + Claude review megtette:

1. **W16 r=-0.414 felismerés** — a számot az algoritmus számolta, de "valami nem stimmel a scoring-gal" értelmezés emberi
2. **Hétfő -$433** — a contradiction pattern (3/3 flagged ticker veszített) csak utólagos elemzéssel látszott
3. **POWI paradoxon** (kedd +$758 → csütörtök -$253) — a scoring nem ismerte fel a recent winner trap-et
4. **MID vs IFDS XLB konfliktus** — két autonóm rendszer, két különböző válasz, csak emberi side-by-side összehasonlítás detektálta
5. **BC25 deploy elhalasztása** — a kód kész, az API él, a rendszer "akarja" deploylni; a "várj, mérjünk előbb" emberi judgment

Mind az 5 esetben a Raschke-modell érvényes: **a rendszer alkalmazza a szabályokat, az ember veszi észre, mikor nem érvényesek a szabályok**.

### A 4 szereplő modellje és Raschke

Az IFDS 4 szereplő architektúrája pontosan ezt az elvet kódolja:

| Szereplő | Szerep | Raschke értelmezésben |
|----------|--------|----------------------|
| Tamás | Product owner, jóváhagyás | A "discretionary layer" — felismeri, mikor változik a piac |
| Chat (Claude) | Orchestrator, review, design | Pattern detection, judgment szupport |
| Claude Code | Implementáció | Systematic rules consistent application |
| Pipeline (cron) | Execution | Automated rule execution |

A piramis tetején **Tamás judgment-je** van. A pipeline alul **következetesen** alkalmazza a szabályokat. A két layer közötti kommunikáció **pontosan** az, amit Raschke "adaptive trader"-nek nevez.

---

## Operatív következmények

### 1. Day 63 (~máj 14) éles/paper döntés nem mechanikus küszöb

**Rossz framing:** "ha Day 63-ig kumulatív >+5%, élesítünk; egyébként nem"

**Helyes framing:** "ha Day 63-ig kumulatív >+5% **és** látjuk hogy a piac stabil **és** a contradiction pattern reprodukálódik **és** Tamás szerint a setup érthető, akkor élesítünk"

A számok **input**, nem output. A döntés Tamásé, judgment-vezérelten.

### 2. A backlog priorítás folyamatos felülvizsgálat alatt áll

Egy "BC30 — Full Autonomous Trading" tervet **nem** írunk fel a roadmap-re. Akkor is, ha technikailag lehetséges lenne, a Raschke-elv mond szembe vele: a **rendszer nem fogja észrevenni**, mikor változik a piac, **az ember igen**.

### 3. A W18+ scoring változtatások konzervatív szintűek

- M_contradiction multiplier: ×0.80 (nem ×0.5) — még téves jel esetén is megengedi a pozíciót
- Recent Winner Penalty: ×0.80 (nem hard skip) — fokozatos hatás
- M_target szigorítás: 10%/25%/40% — fokozatos, nem bináris

Mindegyik változás **teret hagy** Tamás judgmentjének felülbírálásra. A systematic layer szigorítása nélkül **az adaptív képesség elvész**.

### 4. A MID-IFDS integráció (BC25) sem teljes automatizmus

Amikor a BC25 majd élesbe megy (W19+ döntés után), a Phase 3 sector rotation **konzumálja** a MID CAS adatokat, **de** a sector VETO végső döntést **a regime-context** értelmezi. Ha a MID STAGFLATION-t mond és a IFDS XLB-t leader-ként látja momentum alapon, akkor a **kombinált döntés** valami olyasmi, amit egyetlen rule sem tud tisztán kifejezni — ott Tamás reggel ránézhet a logra és azt mondja "nem, ma ne XLB".

---

## Kapcsolódó tanulság (Jansen 2020 Ch23)

Stefan Jansen *Machine Learning for Algorithmic Trading* könyvének zárófejezete (Ch23) **6 kulcsüzenete** közül kettő pontosan ezt erősíti:

> 2. "Domain expertise is key to realizing the value contained in data"
>
> 3. "ML is a toolkit to adapt and combine for your use case"

És a **quantamental investment style** (Ch1, p.15-16) Jansen szerint a "discretionary and algorithmic trading converge" — szó szerint a Raschke-modell.

A két forrás (Raschke 30 év gyakorlat + Jansen 2020 akadémiai szintézis) **független módon ugyanazt** mondja: az automatizálás nem alternatíva az emberi judgmentnek, hanem **multiplikátora**.

---

## Mikor kell ezt elővenni

Amikor a következő hónapokban felmerül egy "ezt is automatizáljuk" csábítás:

- "BC30 legyen full autonomous AI agent" → emlékeztető: a rendszer nem veszi észre a regime-váltást
- "A daily review automatizálható, hogy Claude maga írja log-ból" → részben igen, de Tamás judgmentjét nem helyettesíti
- "A Day 63 döntést egy if-else statement is meg tudja hozni" → nem; az értelmezés emberi
- "Az M_contradiction multiplier-t hard filter-nek tegyük" → nem; teret kell hagyni a felülbírálásnak

Ez a doc emlékeztető. **A human-in-the-loop nem fejlesztési szakasz, hanem strukturális elv.**

---

## Záró megjegyzés

Raschke nem azt mondja, hogy "ne automatizálj". Ő **3 különálló rendszerprogramot** futtat. A pozíciójában az automatizáció **kötelező** — egy ember nem tud 3 stratégiát figyelni egész nap.

Amit mond: **az automatizálás végső felelőse az ember kell legyen**.

Ez a te modelled. Tamás nem ír kódot 16:15-kor (Claude Code teszi). Tamás nem számolja a M_target-et (a pipeline teszi). Tamás nem küldi be az ordert (IBKR Gateway teszi).

De Tamás:
- Olvassa a logokat este
- Látja a contradiction pattern-t és tervet kér
- Mondja "BC25 várjon, mérjünk előbb"
- POWI esetén észreveszi a mean reversion-t
- A MID heatmap-en észreveszi az XLB konfliktust

Ez a "discretionary layer" a systematic layer fölött. **Ez Linda Raschke-modell éles gyakorlatban.**

---

*Felvéve: 2026-04-24*  
*Kapcsolódó: docs/references/ml4t-jansen-2020.md (Ch1 quantamental, Ch23 takeaways)*
