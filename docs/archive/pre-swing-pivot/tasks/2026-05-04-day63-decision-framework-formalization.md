# Day 63 Decision Framework — Formalizálás docs/decisions/-be

**Status:** ✅ DONE — Chat manuálisan elkészítette 2026-05-02 szombat délelőtt
**Created:** 2026-04-29
**Completed:** 2026-05-02
**Priority:** **P1** — szóbeli megegyezés kódba/docs-ba öntés, a Day 63 (~máj 14) döntés alapja
**Estimated effort:** ~30-45 min Chat (manuális írás, nem CC kód-feladat)

**Eredmény:** `docs/decisions/2026-04-28-day63-decision-framework.md` — ~580 sor markdown, 3 kimenet feltételei (ÉLESÍTÉS / LEÁLLÍTÁS / PAPER FOLYTATÁS), 3 felülvizsgálati pont (Day 63/90/120), graceful exit 3 verzió, nyitott kérdések (havi infrastruktúra-költség, tőke skálázás, pszichológiai stressz), operatív használat (daily review-k, weekly metrika decision tracking szekció).

---

## Eredeti task tartalom (történeti referencia)

**Status:** PROPOSED (W18 záró vagy W19 nyitó task)
**Created:** 2026-04-29
**Priority:** **P1** — szóbeli megegyezés kódba/docs-ba öntés, a Day 63 (~máj 14) döntés alapja
**Estimated effort:** ~30-45 min CC (vagy Chat manuális írás)

**Depends on:**
- nincs

**NEM depends on:**
- M_contradiction multiplier (P1, szerda) — független
- LOSS_EXIT whipsaw analysis (P2, csütörtök-péntek) — független

**Sürgősség:** **vasárnap máj 3** (W18 weekly elemzéssel együtt) **vagy** hétfő máj 4. **Mindenképp Day 63 előtt** legyen meg.

---

## Kontextus — miért kell ez

A 2026-04-28 esti chat beszélgetésben formálisan rögzítettük a Day 63 (~máj 14) döntési kereteit. A megegyezés szóbeli maradt, és a következő válaszokat tartalmazza:

**Élesítés:**
- Kumulatív >+$3,000 → $10k tőke
- Skálázás: ugyanaz a 0.5% risk per trade ($50 risk × ~10 pozíció)
- Plusz feltétel: 20+ napon át a regime nem Stagflation **és** kumulatív excess vs SPY > +1%

**Leállítás:**
- 20+ kereskedési napon át VIX > 18 átlag mellett kumulatív excess vs SPY < -1.5%

**Paper folytatás (default):**
- Bármi a két szélső eset között
- Drawdown-tűrés: -$3,000 alatti drawdown is OK, ha statisztikailag indokolt
- Realisztikus alpha cél: **0.75-1% / hó**

**Időtartam-szabály:**
- Day 63 = felülvizsgálati pont, **nem ultimátum**
- Day 90 (~jún 5) második felülvizsgálat
- Day 120 (~júl 6) ha még mindig nincs egyértelmű jel → "graceful exit" mérlegelés

**Még nem eldöntött (nyitott kérdések):**
- Havi infrastruktúra-költség (API-k + Mac Mini áram + saját idő érték)
- "Graceful exit" konkrét forgatókönyve (hobby státusz, archív, infrastruktúra fenntartás)

**A probléma a "csak szóbeli" állapottal:** Day 63-on (~máj 14, ~2 hét múlva) a tegnap esti precíz számok könnyen elhomályosulhatnak. A Reminder app emlékeztetni fog, **de** a `docs/decisions/` mappában lévő formális dokumentum a **fix referencia**, amit a daily review-k és a weekly elemzések is hivatkozhatnak.

## A javasolt fájl

**Hely:** `docs/decisions/2026-04-28-day63-decision-framework.md`

**Megjegyzés:** ha a `docs/decisions/` mappa még nem létezik, létre kell hozni. Ez egy **új mappa konvenció**, ami formális architektúrális/üzleti döntéseknek ad helyet (szemben a `docs/planning/`-gal, ami terv, és a `docs/tasks/`-szal, ami feladat).

## Tartalom

```markdown
# Day 63 Decision Framework — Paper Trading → éles vagy folytatás döntése

**Döntés rögzítve:** 2026-04-28 esti chat beszélgetés (Tamás + Claude)
**Felülvizsgálati pontok:** Day 63 (~máj 14), Day 90 (~jún 5), Day 120 (~júl 6)
**Cél:** strukturált, számszerű döntési keret, ami megakadályozza az érzelmi döntést a 60+ napos paper trading végén.

---

## A három kimenet

### 1. ÉLESÍTÉS — élő pénzes kereskedés indítása

**Feltételek (mindkettő szükséges):**

- (a) Day 63 kumulatív P&L > **+$3,000** (a +3% / 100k bázis)
- (b) Plusz feltétel: 20+ kereskedési napon át a piaci regime **nem Stagflation** ÉS kumulatív excess vs SPY > **+1%**

A (b) feltétel azért fontos, mert a 2026 áprilisi 60 nap nagyrészt Stagflation regime-ben volt, és a BC23 scoring ott bizonyítottan **kevésbé prediktív**. A +$3,000 kumulatív, ha kizárólag egy Stagflation-rali alatt jött össze, nem garantálja, hogy más regime-ekben is működik.

**Tőke:** $10,000

**Skálázás:** ugyanaz a paper trading kockázati struktúra:
- 0.5% risk per trade = $50 risk per trade
- ~10 pozíció elméleti maximum
- Ugyanaz a Phase 0-6 pipeline, M_contradiction multiplier, Breakeven Lock, MID shadow mode (BC25 deploy után aktivált)

**Indok a $10k-ra:**
- Nem $1,000 → tét nélküli, pszichológiai indifferens
- Nem $100,000 → túl nagy stressz, ami befolyásolhatja a következő fejlesztési iterációkat
- $10,000 → fáj annyira, hogy nincs lazaság, **de** nem fáj annyira, hogy ne mertük volna ugyanezt csinálni paper-en

### 2. LEÁLLÍTÁS — paper trading vége, projekt archív vagy hobby státusz

**Feltétel:**

- 20+ kereskedési napon át VIX > 18 átlag mellett kumulatív excess vs SPY < **-1.5%**

**Indok:** ha a magas-vol környezetben (ami az IFDS scoringnak nehezebb terep) a rendszer 20+ napi adatban **konzisztensen alulteljesít** a piacnál, akkor:
- Vagy a scoring nem ad alpha-t Stagflation/magas-vol regime-ben
- Vagy a strukturális problémák (LOSS_EXIT whipsaw, contradiction patterns, recent winner trap) nincsenek megfelelően kezelve

A 20 napi minimum **statisztikailag erős** — egy véletlen szám-generátor 20 napon át kevés eséllyel termel -1.5% kumulatív excess-t.

**Mit jelent a leállítás:**
- Élő pénzes kereskedés NEM indul
- A pipeline futása **leállítható** vagy **redukált tempóval** folytatódik (csak adatgyűjtés, nincs aktív paper trade)
- A projekt **archív státuszba** kerül vagy **hobby státusz**-ba (lásd "Graceful exit" alább)

### 3. PAPER FOLYTATÁS — default kimenet

**Feltétel:** bármi az ÉLESÍTÉS és LEÁLLÍTÁS feltételek között.

Ez **valószínű kimenet** az adatok jelenlegi trajektóriája alapján:
- W17 net +$593 (+0.13% excess)
- W18 hétfő-kedd: -$669 net (még csak 2 nap)
- A kumulatív Day 63-on várhatóan **breakeven** ± $1,000 sávban

**Mit jelent a paper folytatás:**
- +1 hónap paper trading (Day 63 → Day 90)
- Közben implementálódnak: M_contradiction (W18), LOSS_EXIT finomítás (ha indokolt, W19+), Recent Winner Penalty (W20+)
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

### Day 63 (~2026-05-14)

- **Csütörtök reggel** Telegram emlékeztető (Reminder app)
- Paper trading végeredmény: kumulatív P&L, excess vs SPY, TP1 hit rate, regime breakdown
- Döntés: ÉLESÍTÉS / LEÁLLÍTÁS / PAPER FOLYTATÁS

### Day 90 (~2026-06-05)

- Második felülvizsgálati pont
- Csak akkor releváns, ha Day 63-on PAPER FOLYTATÁS volt
- Új szempont: a Day 63 utáni implementált változások (M_contradiction, LOSS_EXIT finomítás, Recent Winner Penalty) hatása mérhető

### Day 120 (~2026-07-06)

- Ha még mindig nincs egyértelmű jel → "graceful exit" mérlegelés
- Itt a kérdés: érdemes-e tovább paper-elni, vagy a projekt **strukturálisan** nem fog alpha-t produkálni?

---

## Graceful Exit — fogalom definíció

Ha a Day 120 vagy későbbi felülvizsgálatkor a döntés **NEM ÉLESÍTÉS**, akkor a "graceful exit" három verziójában:

### A) Hobby státusz

- A pipeline **továbbra is fut** napi cron-nal a Mac Mini-n
- A paper trading **leáll** (nincs új submit, IBKR Gateway opcionálisan kikapcsolva)
- A daily review-k **megszűnnek**
- A backlog **archiválódik**, új feature-ök nem implementálódnak
- A meglévő infrastruktúra **referencia jellegű** marad

**Költség:** ~0 (Mac Mini áram, API-k egy része megszűnik)

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

- Polygon API: ?? / hó
- FMP API: ?? / hó
- Unusual Whales: ?? / hó
- FRED API: ingyenes
- Mac Mini áram: ~$5 / hó
- Telegram bot: ingyenes
- IBKR paper account: ingyenes
- **Saját idő:** ?? óra / hét × ?? hourly rate

**Cél:** Day 63 előtt összegezni — havi tényleges költség, és ennek tükrében értékelni, hogy az élő kereskedés **havi alpha** a költségeket fedezi-e.

**Ezt Tamás összegzi** valamikor a következő héten.

### 2. Élesítés tőke skálázódása

Day 63 → $10k. **Mi van**, ha:
- Day 90-on a $10k-os élő rendszer +$1,000-et hoz → érdemes felemelni $20k-ra?
- Day 120-on már $30k bízhatóan menne?

Ez **későbbi probléma**, csak kontextusként. A jelenlegi döntés a Day 63 → $10k.

### 3. Pszichológiai stressz mérése

A paper trading 60+ napjának **érzelmi tartalma** is fontos. Ha a Day 63-ra Tamás **kimerült**, **frusztrált**, vagy **tét nélkül érzi** a folyamatot, az **önmagában** indok a "graceful exit"-re — függetlenül a számoktól.

**Önreflexív kérdés Day 63-on:** "Még mindig motivál ez a projekt? Vagy már csak inertia?"

---

## A keret operatív használata

### Daily review-k

Minden napi review **utolsó pontként** rövid utalást tehet a keretre:

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

**Ezt egy kis CC task** tudná hozzáadni a `weekly_metrics.py`-hez (~30 min).

### Day 63 reggeli rutin (~2026-05-14)

- 09:00 Reminder notification
- Megnyitás: `docs/decisions/2026-04-28-day63-decision-framework.md`
- `weekly_metrics.py` futtatás full BC23 időszakra
- 3 kimenet összevetése a számokkal
- Decision rögzítése egy új doc-ban: `docs/decisions/2026-05-14-day63-decision-outcome.md`

---

## Linda Raschke-elv kontextus

Ez a doc **explicit a Raschke-modell mentén**: a systematic layer (számszerű kritériumok) ad keretet, **de** a végső döntés **emberi judgment**. A 3 kimenet közül egyik **nem automatikus** — a számok inputot adnak, Tamás dönt.

A nyitott kérdések (havi költség, pszichológiai stressz) **explicit kívül esnek** a systematic kereten — pontosan mert ezek az emberi judgment területei.

A Day 63 nem **algoritmus output**, hanem **strukturált döntési pillanat**.

---

*Rögzítve: 2026-04-28*
*Formalizálva docs-ba: 2026-05-04 (várható)*
*Felülvizsgálat: 2026-05-14 (Day 63), 2026-06-05 (Day 90), 2026-07-06 (Day 120)*
```

## Scope — 4 pont

### 1. Mappa létrehozás

```bash
mkdir -p ~/SSH-Services/ifds/docs/decisions/
```

### 2. Fájl létrehozás

A fenti tartalom mentés `docs/decisions/2026-04-28-day63-decision-framework.md`.

### 3. STATUS.md hivatkozás

A `docs/STATUS.md` "Paper Trading Day 63 (~máj 14)" sorba egy hivatkozás:

```markdown
- **Paper Trading Day 63** (~máj 14): éles/paper folytatás döntés
  - **Decision framework:** `docs/decisions/2026-04-28-day63-decision-framework.md`
```

### 4. backlog-ideas.md hivatkozás

A backlog-ban említett Recent Winner Penalty, M_contradiction stb. mind **a paper folytatás** scope-ban vannak. Egy összefoglaló sor:

```markdown
**Megjegyzés:** Az alábbi backlog elemek implementációja a Day 63 döntésen múlik.
Lásd: `docs/decisions/2026-04-28-day63-decision-framework.md`
```

## Success criteria

1. `docs/decisions/2026-04-28-day63-decision-framework.md` létezik és tartalmazza a fenti 3 kimenet feltételeit, időbeli felülvizsgálatokat, graceful exit verziókat
2. `docs/STATUS.md` és `docs/planning/backlog-ideas.md` hivatkozza
3. A Reminder app `IFDS - Paper Trading Day 63 — KIÉRTÉKELÉS` emlékeztető szövege a fájl elérési útját tartalmazza

## Risk

**Zéró.** Ez egy dokumentációs feladat, semmilyen kód vagy pipeline viselkedés nem változik.

## Out of scope

- A pipeline-ban kódolt logika a kerethez (pl. automatikus leállítás 20 napos mérés alapján) — ez **NEM** automatikus, **emberi döntés** Day 63-on
- A Day 63 kimenetét rögzítő doc (`2026-05-14-day63-decision-outcome.md`) — az Day 63-on jön, nem most
- weekly_metrics.py decision tracking szekció — opcionális kis CC task később

## Implementáció

**Két opció:**

**A) Chat manuálisan írja (most, vagy hétvégén)**
- Effort: ~30 min Chat
- Time: vasárnap máj 3 a W18 weekly elemzés mellé

**B) CC task vasárnap reggel**
- Effort: ~30 min CC
- A fenti tartalom egyszerű copy-paste, kis adaptáció

**Javaslat:** **A) Chat manuálisan**. Ez egy **filozófiai/strukturális** dokumentum, nem implementációs feladat. Chat ír docs-ot anélkül, hogy CC-nek kellene lefoglalni időt egy ilyen alacsony technikai komplexitású munkára.

## Implementáció időzítése

- **Vasárnap máj 3:** Chat W18 weekly elemzés + ezt a docs/decisions fájlt egyszerre megírja
- **Hétfő máj 4:** Tamás átolvassa, módosítást kér ha szükséges
- **Day 63 előtt (kb. máj 14 reggel):** a fájl referencia pontként szolgál a döntéshez

## Kapcsolódó

- Linda Raschke filozófia: `docs/references/raschke-adaptive-vs-automated.md`
- Backlog: `docs/planning/backlog-ideas.md`
- Élő STATUS: `docs/STATUS.md`
- W17 weekly elemzés: `docs/analysis/weekly/2026-W17-analysis.md`
- 2026-04-28 esti chat beszélgetés (a megegyezés forrása)
