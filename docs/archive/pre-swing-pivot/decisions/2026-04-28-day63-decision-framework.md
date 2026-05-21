# Day 63 Decision Framework — Paper Trading → éles vagy folytatás döntése

**Döntés rögzítve:** 2026-04-28 esti chat beszélgetés (Tamás + Claude)
**Formalizálva:** 2026-05-02 (szombat délelőtt, Tamás utazás előtt)
**Felülvizsgálati pontok:** Day 63 (~2026-05-14), Day 90 (~2026-06-05), Day 120 (~2026-07-06)
**Cél:** strukturált, számszerű döntési keret, ami megakadályozza az érzelmi döntést a 60+ napos paper trading végén

---

## Kontextus — miért készült ez a doc

A 2026-04-28 esti beszélgetésben Tamás kérte Claude-tól, hogy legyen kritikus, és ne lustaljon el. A beszélgetésben felmerült néhány kemény, de fontos kérdés:

> Day 63-on a kumulatív +$3,000, élesítesz? Mennyi tőkével?
> Day 63-on a kumulatív -$200, leállítod?
> Mi az az adat, ami téged meggyőzne, hogy az IFDS pozitív alpha-t ad?

Tamás válaszolt mindegyikre. **A válaszok nagyrészt** **2 hete** is léteztek a fejében, **de** **a konkrét számszerű kritériumok** ("VIX 18 alatt 4 pozitív nap / hét, 1.5-2% alpha / hó") **csak akkor fogalmazódtak meg először**.

Claude kritikája az eredeti válaszokra:
- **A "havi 1.5-2% alpha" túl ambíciózus** — professzionális hedge fund top decile szint. Realisztikus első cél: **0.75-1% / hó**.
- **A "VIX 18 felett 0 pozitív nap" leállítási feltétel statisztikailag gyenge** — egy véletlen szám-generátor is ad ~3% eséllyel ilyen hetet.
- **A "VIX 18 alatt 4 nyertes nap" élesítési feltétel regime-vak** — érdemesebb a regime kontextushoz kötni.

A finomított keret ezt a doc-ot tükrözi.

**A szóbeli megegyezés docs-ba öntésének célja:** Day 63 közelében a tegnap esti precíz számok könnyen elhomályosulhatnak. **Ez a fix referencia**, amit a daily review-k és a weekly elemzések is hivatkozhatnak.

---

## A három kimenet

### 1. ÉLESÍTÉS — élő pénzes kereskedés indítása

**Feltételek (mindkettő szükséges):**

- (a) Day 63 kumulatív P&L > **+$3,000** (a +3% / 100k bázis)
- (b) Plusz feltétel: 20+ kereskedési napon át a piaci regime **nem Stagflation** ÉS kumulatív excess vs SPY > **+1%**

A (b) feltétel azért fontos, mert a 2026 áprilisi 60 nap nagyrészt Stagflation regime-ben volt, és a BC23 scoring ott bizonyítottan **kevésbé prediktív**. A scoring validation (2026-05-01) megerősítette: 378 trade-en a Pearson r ≈ 0 — a score önmagában nem prediktív. **A flow komponens** (+0.136*) az egyetlen statisztikailag jelentős prediktor.

**A +$3,000 kumulatív, ha kizárólag egy Stagflation-rali alatt jött össze, nem garantálja, hogy más regime-ekben is működik.** A (b) feltétel ezt zárja ki.

**Tőke:** $10,000

**Skálázás:** ugyanaz a paper trading kockázati struktúra:
- 0.5% risk per trade = $50 risk per trade
- ~10 pozíció elméleti maximum
- Ugyanaz a Phase 0-6 pipeline
- **W18-ban élesedett feature-ök** mind aktív: Breakeven Lock, MID shadow mode, vix-close, LOSS_EXIT whipsaw audit
- **W19-ben várható feature:** Contradiction Signal (M_contradiction multiplier)

**Indok a $10k-ra:**
- Nem $1,000 → tét nélküli, pszichológiai indifferens
- Nem $100,000 → túl nagy stressz, ami befolyásolhatja a következő fejlesztési iterációkat
- $10,000 → fáj annyira, hogy nincs lazaság, **de** nem fáj annyira, hogy ne mertük volna ugyanezt csinálni paper-en

### 2. LEÁLLÍTÁS — paper trading vége, projekt archív vagy hobby státusz

**Feltétel:**

- 20+ kereskedési napon át VIX > 18 átlag mellett kumulatív excess vs SPY < **-1.5%**

**Indok:** ha a magas-vol környezetben (ami az IFDS scoringnak nehezebb terep) a rendszer 20+ napi adatban **konzisztensen alulteljesít** a piacnál, akkor:
- Vagy a scoring nem ad alpha-t Stagflation/magas-vol regime-ben
- Vagy a strukturális problémák (LOSS_EXIT/SL exit dominanciája, contradiction patterns, recent winner trap) nincsenek megfelelően kezelve

**A 20 napi minimum statisztikailag erős** — egy véletlen szám-generátor 20 napon át kevés eséllyel termel -1.5% kumulatív excess-t.

**Mit jelent a leállítás:**
- Élő pénzes kereskedés NEM indul
- A pipeline futása **leállítható** vagy **redukált tempóval** folytatódik (csak adatgyűjtés, nincs aktív paper trade)
- A projekt **archív státuszba** kerül vagy **hobby státusz**-ba (lásd "Graceful exit" alább)

### 3. PAPER FOLYTATÁS — default kimenet

**Feltétel:** bármi az ÉLESÍTÉS és LEÁLLÍTÁS feltételek között.

Ez **a legvalószínűbb kimenet** a 2026-05-02 állapot alapján:
- Day 55/63 kumulatív P&L: -$987 (-0.99%)
- 4 napi kumulált excess vs SPY: -0.40%
- W18 átlag VIX: 17.69 (a 18-as küszöb körül)
- A kumulatív Day 63-ra **realisztikusan +$700-1,150 sávban** lesz, ha a következő 8 nap átlagos napi +$80-100

**Mit jelent a paper folytatás:**
- +1 hónap paper trading (Day 63 → Day 90)
- Közben implementálódnak: **M_contradiction (W19)**, esetleg Recent Winner Penalty (W20+), MID Phase 3 integráció (BC25)
- BC24 (UW Institutional Flow) kezdés W19+
- BC25 (MID Phase 3 ← CAS) GO/NO-GO döntés a vasárnapi MID vs IFDS comparison alapján

**Drawdown-tűrés:**
- -$3,000 alatti kumulatív drawdown **NEM** automatikus leállás
- A leállítás csak az 1.5% excess feltétel alapján
- Egy átmeneti -$2,000-3,000 drawdown statisztikai zaj 60+ napos adatban

**Alpha cél (realisztikus):**
- **0.75-1% / hó** (~9-12% / év)
- Nem 1.5-2% / hó (az túl ambíciózus, professzionális hedge fund top decile szint)
- Első cél: **stabil, pozitív, kontrollált alpha** — később lehet optimalizálással növelni

---

## Időbeli felülvizsgálati pontok

### Day 63 (~2026-05-14, csütörtök)

- **09:00 CEST Reminder app notification**
- Paper trading végeredmény: kumulatív P&L, excess vs SPY, TP1 hit rate, regime breakdown
- Döntés: **ÉLESÍTÉS / LEÁLLÍTÁS / PAPER FOLYTATÁS**
- Új doc keletkezik: `docs/decisions/2026-05-14-day63-decision-outcome.md`

### Day 90 (~2026-06-05)

- Második felülvizsgálati pont
- **Csak akkor releváns**, ha Day 63-on PAPER FOLYTATÁS volt
- Új szempont: a Day 63 utáni implementált változások (M_contradiction, esetleg Recent Winner Penalty, MID integráció) hatása mérhető
- A Day 63-on indított nap-30-ra eldönthető, hogy ezek a feature-ök valóban értéket adnak-e

### Day 120 (~2026-07-06)

- Ha még mindig nincs egyértelmű jel → **"graceful exit" mérlegelés**
- Itt a kérdés: érdemes-e tovább paper-elni, vagy a projekt **strukturálisan** nem fog alpha-t produkálni?

---

## Graceful Exit — fogalom definíció

Ha a Day 120 vagy későbbi felülvizsgálatkor a döntés **NEM ÉLESÍTÉS**, akkor a "graceful exit" három verziója:

### A) Hobby státusz

- A pipeline **továbbra is fut** napi cron-nal a Mac Mini-n
- A paper trading **leáll** (nincs új submit, IBKR Gateway opcionálisan kikapcsolva)
- A daily review-k **megszűnnek**
- A backlog **archiválódik**, új feature-ök nem implementálódnak
- A meglévő infrastruktúra **referencia jellegű** marad

**Költség:** ~0 (Mac Mini áram, FRED API ingyen, egyéb API-k egy része megszűnik)

### B) Archív + szelektív aktiválás

- A pipeline **leáll** (cron disable)
- A repó megmarad GitHub-on, mint **referencia projekt**
- A MID API integráció **továbbra is élő**, mint külön projekt
- Új piaci regime esetén (pl. Stagflation → Reflation váltás) **opcionálisan** újraindítható

**Költség:** ~$0 / hó

### C) Teljes archívum

- A pipeline **leáll**
- Az API előfizetések **lemondva** (Polygon, FMP, UW)
- A Mac Mini **felszabadítódik** más projektekre
- A repó GitHub-on megmarad mint **case study**

**Költség:** $0 / hó

**A választás később:** Day 120-on (vagy később) Tamás dönti el, melyik verzió a leghelyesebb. A három verzió **most rögzített**, hogy ha eljön az idő, **ne kelljen ad-hoc gondolkodni**.

---

## Nyitott kérdések, amik még nem dőltek el

### 1. Havi infrastruktúra-költség

Tamás Day 63 előtt összegezni:
- Polygon API: ?? / hó
- FMP API: ?? / hó
- Unusual Whales: ?? / hó
- FRED API: ingyenes
- Anthropic API (Company Intel): ?? / hó (~30 hívás/nap × $0.01 = ~$10/hó)
- Mac Mini áram: ~$5 / hó
- Telegram bot: ingyenes
- IBKR paper account: ingyenes
- **Saját idő:** ?? óra / hét × ?? hourly rate

**Cél:** Day 63 előtt összegezni a havi tényleges költséget, és ennek tükrében értékelni, hogy az élő kereskedés **havi alpha** a költségeket fedezi-e.

**Példa kalkuláció:** ha havi infra ~$100, és Day 63-on $10k tőke élesedik 0.75% / hó alpha-val, akkor havi nyereség ~$75. **Ez nem fedezi a havi költséget.** Tehát **vagy alpha cél emelése**, **vagy** **tőke skálázás** szükséges hosszú távú profitabilitáshoz.

**Ezt Tamás összegzi** valamikor a következő héten.

### 2. Élesítés tőke skálázódása Day 90+ után

Day 63 → $10k. **Mi van**, ha:
- Day 90-on a $10k-os élő rendszer +$1,000-et hoz → érdemes felemelni $20k-ra?
- Day 120-on már $30k bízhatóan menne?

**Nincs eldöntve most.** Day 90-en az adatok alapján külön döntés.

### 3. Pszichológiai stressz mérése

A paper trading 60+ napjának **érzelmi tartalma** is fontos. Ha a Day 63-ra Tamás **kimerült**, **frusztrált**, vagy **tét nélkül érzi** a folyamatot, az **önmagában** indok a "graceful exit"-re — függetlenül a számoktól.

**Önreflexív kérdés Day 63-on:** "Még mindig motivál ez a projekt? Vagy már csak inertia?"

Ezt csak Tamás tudja megválaszolni — Claude **nem** ítélkezhet pszichológiai állapotokról.

---

## A keret operatív használata

### Daily review-k

Minden napi review **utolsó pontként** rövid utalást tartalmaz a keretre:

> "Mai kumulatív: $X. Élesítés feltétel távolság: $Y. Leállítás feltétel távolság: $Z napi VIX átlag mellett."

Ez **napi szinten láthatóvá** teszi, hol állunk a keretrendszerben.

### Weekly metrika

A pénteki `weekly_metrics.py` outputjához érdemes hozzáadni egy **decision tracking** szekciót:

```
=== Day 63 Decision Tracking ===
Cumulative P&L: $X
Days at VIX > 18: N / 5
20-day excess vs SPY: $Y%
Decision distance: ÉLESÍTÉS feltől $A, LEÁLLÍTÁS feltől $B
```

**Ezt egy kis CC task** tudná hozzáadni a `weekly_metrics.py`-hez (~30 min). **Backlog idea:** felvegyük, ha CC-nek szabadideje van W19+ scope-ban.

### Day 63 reggeli rutin (~2026-05-14)

- 09:00 Reminder notification
- Megnyitás: ezen doc
- `weekly_metrics.py` futtatás teljes BC23 időszakra
- 3 kimenet összevetése a számokkal
- Decision rögzítése egy új doc-ban: `docs/decisions/2026-05-14-day63-decision-outcome.md`

---

## A jelenlegi (2026-05-02 szombat) helyzet

| Metrika | Érték | Status a kerethez képest |
|---------|-------|--------------------------|
| Day | 55/63 | 8 nap van hátra |
| Kumulatív P&L | -$987 (-0.99%) | **biztonságos sávban** |
| ÉLESÍTÉS távolság | +$3,987 a +$3,000-tól | **8 nap alatt napi átlagos +$498 kellene → NEM elérhető** |
| LEÁLLÍTÁS távolság | excess +0.13% távol a -1.5%-tól | **biztonságos sávban** |
| 4 napi excess vs SPY | -0.40% | **biztonságos sávban** |
| VIX W18 átlag | 17.69 | **a 18-as küszöb körül** — leállítási feltétel részlegesen alszik |
| Regime | Stagflation Day ~14/28 | **~50% mid-stage** — még nem regime change |

**Realisztikus Day 63 várt kimenet:** **PAPER FOLYTATÁS (default)** — a kumulatív P&L valószínűleg +$700 és -$2,000 között lesz, ami **távol** mind az élesítési, mind a leállítási küszöbtől.

**A jelenlegi pálya nem** "vesztes paper trading" — **stabil, mérhető, és feldolgozható** adatpontot termel. A Day 63 nem a vég, hanem **az első felülvizsgálati pont**.

---

## Linda Raschke-elv kontextus

Ez a doc **explicit a Raschke-modell mentén**: a systematic layer (számszerű kritériumok) ad keretet, **de** a végső döntés **emberi judgment**. A 3 kimenet közül egyik **nem automatikus** — a számok inputot adnak, Tamás dönt.

A nyitott kérdések (havi költség, pszichológiai stressz) **explicit kívül esnek** a systematic kereten — pontosan mert ezek az emberi judgment területei.

A Day 63 nem **algoritmus output**, hanem **strukturált döntési pillanat**.

A 2026-04-28 esti beszélgetés is **ezt** tükrözte: Tamás kérte a kritikát, Claude felülbírálta a saját korábbi tanácsát, és **közösen** finomítottuk a keretet. A paper trading 60+ napos adatpontok **input**, nem ítélet.

---

## Kapcsolódó dokumentumok

- **Linda Raschke filozófia:** `docs/references/raschke-adaptive-vs-automated.md`
- **Backlog:** `docs/planning/backlog-ideas.md` — Day 63 utáni várható implementációk
- **Élő STATUS:** `docs/STATUS.md`
- **W17 weekly elemzés:** `docs/analysis/weekly/2026-W17-analysis.md`
- **W18 weekly riport:** `docs/analysis/weekly/2026-W18.md` (CC outputja)
- **W18 weekly elemzés (Chat):** `docs/analysis/weekly/2026-W18-analysis.md` (vasárnap készül)
- **Scoring validation:** `docs/analysis/scoring-validation.md` (55 napi 378 trade)
- **Forrás megegyezés:** 2026-04-28 esti chat beszélgetés (Tamás + Claude)
- **Reminder app:** `IFDS - Paper Trading Day 63 — KIÉRTÉKELÉS` (2026-05-14, 09:00)

---

## Jegyzet a hosszú távú perspektívához

A 2026-04-28 esti beszélgetésben Tamás megjegyezte: **"szeretnék haladni, valami maradandót alkotni."**

Claude válasza akkor: a "maradandó" gyakran **nem** a kódbázis, hanem **a döntés meghozatala**. Akár ÉLESÍTÉS, akár LEÁLLÍTÁS — **mindkettő érvényes, mindkettő maradandó**. **A halogatás nem.**

Ez a doc a **döntés strukturált meghozatalának** eszköze. Day 63-on a számokra rátekintünk, nem érzelmekre, nem reményre, nem félelemre.

Ha az élesítés feltétele teljesül — élesítjük. Ha a leállítás feltétele teljesül — leállítjuk. Ha köztes vagyunk — folytatjuk paper-en, és **újra felülvizsgáljuk Day 90-en**.

**A keret az érzelmi döntés ellen véd.** Ez a célja.

---

*Rögzítve: 2026-04-28 esti chat (szóbeli megegyezés)*
*Formalizálva: 2026-05-02 szombat délelőtt (Tamás utazás előtt)*
*Felülvizsgálati pontok: 2026-05-14 (Day 63), 2026-06-05 (Day 90), 2026-07-06 (Day 120)*
