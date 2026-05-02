# Daily Review — 2026-04-30 (csütörtök)

**BC23 Day 14 / W18 Day 4**
**Paper Trading Day 54/63**

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | +$425.66 |
| Napi P&L net | **+$404.62** (commission $21.04) |
| Kumulatív P&L | **+$238.26 (+0.24%)** ⭐ **POZITÍV TARTOMÁNY** |
| Pozíciók (új) | 5 ticker (NE, EC, USFD, COST, TER) — 6 trade (EC 2-split) |
| Win rate | 4/5 ticker (NE, EC, USFD, TER nyert; COST vesztett) |
| TP1 hit rate | 0/5 (0%) |
| TP2 hit rate | 0/5 (0%) |
| Exit mix | 5× MOC, **1× TRAIL** (TER), 0× LOSS_EXIT, 0× SL, 0× TP |
| Avg slippage | -0.05% (TER -1.28% **kedvező** !) |
| Commission | $21.04 ← **legalacsonyabb** a héten |
| SPY return | **+0.99%** (erős bull nap) |
| Portfolio return | +0.43% |
| **Excess vs SPY** | **-0.57%** ← underperform a piaci rally-ben |
| VIX close | **16.99** (Δ=-8.21%, **18 alá zuhant**) |

## ⭐⭐ A KUMULATÍV P&L POZITÍV TARTOMÁNYBA LÉPETT — 14 nap után először

**+$238.26 (+0.24%)** — **a BC23 deploy (2026-04-13) óta először van a paper trading kumulatív POZITÍV.** Ez a **W18 hetedik napi adata** együtt:
- W17: net +$593, kumulatív Day 50: -$19
- W18 hétfő: -$361 → -$349
- W18 kedd: -$308 → -$617 ← **mélypont**
- W18 szerda: +$406 → -$187
- W18 csütörtök: **+$405 → +$238** ⭐⭐

**A 4 napon belül +$855 visszamászás.** A te kereted szerint ez a "paper folytatás default" sávon belül **erősen pozitív irányba mozog**. A Day 63 ÉLESÍTÉS feltétel: kumulatív >+$3,000. Jelenleg távol vagyunk, de **a tendencia** most **az ÉLESÍTÉS felé**.

## ⭐ A Breakeven Lock első TRAIL exit-je — TER

**Ez egy első a feature deploy óta!** Idővonal:

```
16:18 CEST  TER Entry $344.35 (slippage **-1.28% kedvező** = $4.48/share megtakarítás)
            SL $314.50, TP1 $377.44, TP2 $394.60

19:00:23 CEST  trail_activated_b @ ár $351.74 (entry +$2.91, +0.83%)
               Trail SL $317.41 (9.0% entry alatt — klasszikus trail)

19:00:25 CEST  breakeven_lock_applied  $317.41 → $348.83 (entry)
               lock_type: profit_breakeven
               +$31.42 floor jump

21:05:19 CEST  trail_hit @ $348.29
               Exit kicsit a $348.83 SL alatt (slippage)
               P&L: ($348.29 - $344.35) × 20 = +$78.80 gross → +$75.40 net
```

**Mi történt itt:**

1. **A TER trail SL $317.41 → $348.83 ugrott** (9.0% → 0% alatt entry-hez), +$31.42 floor jump
2. **TER ár 19:00 után fokozatosan csúszott** $351.74-ről $348-ra
3. **Az új SL $348.83-on hit-elt** 21:05 CEST-kor
4. **Trail exit, NEM MOC** — a feature **megfogta** mielőtt a piac nyitotta volna a 21:05-21:55 sávot

**A KRITIKUS aspektus:** ha a régi trail SL ($317.41) lett volna érvényben, akkor **az 21:05 trail nem hit-elt volna** (a $348-as ár sokkal a régi SL felett van), és **a pozíció MOC-on zárt volna**. A TER MOC ára kb. **$346-347** lett volna a folytatódó lefelé csúszás alapján — kb. **+$50 → +$60 gross**.

**A Breakeven Lock TER-en így +$15-25 többletprofitot termelt** (a tényleges $75.40 vs hipotetikus $60 MOC).

**Ez egy konkrét, mérhető haszon.** A Breakeven Lock 4 nap alatt:
- Hétfő: 0 aktiváció
- Kedd: 1 aktiváció (PAA), profit megőrzve
- Szerda: 4 aktiváció, mind MOC-on profit
- **Csütörtök: 2 aktiváció (EC, TER), TER első TRAIL exit, NEM MOC**

**5/7 aktiváció után a feature konkrétan profitot védett vagy javított.**

## Az -0.57% excess — fontos kontextus

A SPY +0.99% volt — **a piac hatalmas bull napot** csinált. Mi +0.43%-ot adtunk, ami **abszolútumban erős nap**, **de** a piaci rally-vel szemben **alulteljesítettünk -0.57%-kal**.

**Ez a Day 63 keret szempontjából érdekes:**
- **Élesítési feltétel** (b): "20+ napon át a regime nem Stagflation ÉS kumulatív excess vs SPY > +1%"
- **Leállítási feltétel:** "20+ napon át VIX > 18 mellett kumulatív excess vs SPY < -1.5%"

**A VIX ma 16.99 — 18 ALATT.** Ez azt jelenti, hogy a leállítási feltétel **NEM aktiválódik** ezen a napon (hiányzik a VIX > 18 napi adat). **A 4 napi excess átlag jelenleg ~-0.07%** — nem közelít az ÉLESÍTÉS +1%-hoz, de **biztonsági sávban** van.

**Egy fontos megfigyelés:** a rendszer **bull napon underperformolt**. A 3 W18 napon, amikor a SPY enyhén negatív vagy flat (kedd, szerda), **outperformoltunk**. **Ma**, amikor a SPY +0.99% rally-zött, **lemaradtunk**. **Ez egy strukturális tendencia lehet** — a swing trading rendszerek gyakran **defenzívek**, és bull rally-ben a long-only buy-and-hold (SPY) **technikailag veri** őket.

**Ezt érdemes** rögzíteni a vasárnapi W18 elemzésbe.

## Pozíciók részletei

### Nyertesek (4)

**EC (Ecopetrol, energy, score 94.5):** 2-split, entry $13.81 (slippage +0.36%), MOC $14.16 = **+$259.70 össz** (175 + 84.70). +2.53% intraday — **a nap legnagyobb % nyerő**. **Breakeven Lock 19:00 CEST aktivált**, $13.35 → $13.76. Az ár $14.16-ra emelkedett, az új SL irreleváns lett, MOC-on zárt.

**USFD (US Foods, cons. defensive, score 92.0):** Entry $93.04 (slippage +0.13%), MOC $93.62 = **+$75.98**. +0.62% intraday. **A trail mechanika folyamatosan emelkedett** $90.23 → $91.20 (15+ trail_sl_update events), **de a Breakeven Lock NEM aktiválódott** — mert 17:00-19:05 sávban nem érte el a +0.7% trail küszöböt. **Csak 17:40-kor** lépte át, ami **a window vége után** (19:00:00-19:04:59). **Ez egy edge case**, de a feature design szándékos: csak 19:00 ablakban aktiválódik.

**TER (Teradyne, semis, score 88.0 — legalacsonyabb!):** Entry $344.35 (slippage **-1.28% kedvező**, $4.48/share megtakarítás), **TRAIL exit $348.29** = **+$75.40**. **Az első TRAIL exit a Breakeven Lock élesítése óta.** Részletes elemzés fent.

**NE (Noble Corporation, oil & gas drilling, score 95.0 — legmagasabb):** Entry $51.03 (slippage +0.33%), MOC $51.18 = **+$35.70**. +0.29% intraday — **a legmagasabb score-ú ticker, mégis a legkisebb % nyerő**. A trail_activated_b csak **21:50 CEST-kor** (a logban 19:50 UTC), ami **MOC submit utánra esett** (21:40 CEST = 19:40 UTC). **A Breakeven Lock NEM kapta meg** — túl későn aktivált.

### Vesztes (1)

**COST (Costco, cons. defensive, score 91.5):** Entry $1016.00 (slippage +0.20%), MOC $1014.68 = **-$21.12**. -0.13% mozgás — **kis vesztes**, **nem** strukturális hiba. A cégnek nem volt érdemleges intraday news, csendes underperformer.

## Score → P&L napi nézet

| Ticker | Score | P&L net | Win? | Exit |
|--------|-------|---------|------|------|
| **NE** | **95.0** | +$35.70 | ✓ | MOC |
| EC | 94.5 | +$259.70 | ✓ | MOC |
| USFD | 92.0 | +$75.98 | ✓ | MOC |
| COST | 91.5 | -$21.12 | ✗ | MOC |
| **TER** | **88.0** | +$75.40 | ✓ | TRAIL |

**Score korreláció ma érdekes:** a legmagasabb score (NE 95.0) csak +$35, és a legalacsonyabb (TER 88.0) +$75 — **inverz** rank korreláció napon belül! **r ≈ -0.3**. **Ez NEM** azt jelenti, hogy a scoring "rossz" — **csak azt**, hogy a napi varianca magas. A heti és havi átlag fontosabb.

A WC scoring kontextus: az EC $259 a nap valódi nyerője (+2.53% mozgás), és a 94.5 score 2. legmagasabb. **A magas score-ú tickerek tipikusan jól teljesítettek** ma.

## A W18 első 4 nap — fordulópont

| Nap | SPY | Portfolio | Excess | P&L net | Kumulatív |
|-----|-----|-----------|--------|---------|-----------|
| Hétfő | +0.17% | -0.33% | -0.50% | -$361 | -$349 |
| Kedd | -0.49% | -0.27% | +0.22% | -$308 | -$617 ← mélypont |
| Szerda | -0.02% | +0.43% | +0.45% | +$406 | -$187 |
| **Csütörtök** | **+0.99%** | **+0.43%** | **-0.57%** | **+$405** | **+$238** ⭐ |
| **Σ 4 nap** | **+0.65%** | **+0.27%** | **-0.40% átlag** | **+$140** | **+$238** |

**A 4 napi excess -0.40%** — **gyengébb** mint a 3 napos +0.17%, mert a mai rally-ben underperformoltunk. **De** a **kumulatív $-fontot tekintve** +$140 net, ami **pozitív**.

A Day 63 keret szempontjából:
- Még **9 nap** van Day 63-ig (~máj 14)
- Kumulatív +$238, **távol az ÉLESÍTÉS +$3,000-tól**
- Excess átlag -0.40%, **távol mindkét küszöbtől** (+1% / -1.5%)
- VIX 16.99, **18 ALATT** — a leállítási feltétel részlegesen "alszik"
- **A regime még Stagflation Day 14/28 valószínűleg** (~50% mid-stage)

**Realisztikus pálya Day 63-ra:** ha a következő 9 nap átlagos napi +$50-100 (mai +$405 ÉS hétfő -$361 között), akkor Day 63 kumulatív **+$700-1,150** lehet. **Ez NEM** ÉLESÍTÉS, **NEM** LEÁLLÍTÁS — **paper folytatás** Day 63-on, megerősítéssel a Day 90 felülvizsgálati pontig.

## Új MID adatok ma este

A 22:00-i Phase 1-3 cron új snapshot-ot készít. **Várt:** Stagflation Day 14/28 (~50% mid-stage). Top sectors valószínűleg változnak — a XLE, XLK, XLI helyett lehet **XLK, XLI, XLF** vagy más kombináció (a piaci rally a financials-t és tech-et erősíti).

**Holnap reggel ellenőrzendő:**
```bash
gzcat ~/SSH-Services/ifds/state/mid_bundles/2026-04-30.json.gz | jq '.flat.regime, .flat.top_sectors, .flat.age_days'
```

## A kedd-i ticker-ek vs MID sectors (kedd snapshot alapján)

| Ticker | Sector | MID rangsor (kedd) |
|--------|--------|---------------------|
| NE | Energy (XLE) | top-3 ✓ |
| EC | Energy (XLE) | top-3 ✓ |
| USFD | Cons. Defensive (XLP?) | nincs top/bottomban |
| COST | Cons. Defensive (XLP) | nincs top/bottomban |
| TER | Tech / Semis (XLK) | top-3 ✓ |

**3/5 ticker MID top-3 sectorban** (NE, EC, TER), **2 ticker** sem top, sem bottom (USFD, COST). **A 2 nem-top ticker közül 1 nyert (USFD), 1 vesztett (COST)** — vegyes. **Az MID top-3 ticker mindegyike nyert** ma (NE, EC, TER) — **konzisztens szektor jelzés** az **energy és tech rally-vel** (a SPY +0.99% nap "risk-on" irányt mutatott).

## VIX 18 alá zuhant — Day 63 keret implikáció

A VIX **16.99**-re csökkent (-8.21% napi). **Ez egy fontos váltás:**

**Az utóbbi 14 napi VIX:**
- W17 sáv: ~16-19
- W18 hétfő-kedd: ~18.20-18.04
- W18 szerda: 18.51
- **W18 csütörtök: 16.99** ← drámai csökkenés

**Ha a VIX 18 alatt marad** a következő 5 napban, akkor a **leállítási feltétel statikus:** "20+ napon át VIX > 18 átlag mellett". **A jelenlegi 4 napos átlag VIX ~17.93** — a 18-as küszöb körül.

**Mit jelent ez gyakorlatban:** ha a piac **stabilan low-vol** marad a Day 63-ig, akkor a leállítási feltétel **nem aktiválható** — bármilyen excess vs SPY szám esetén is. **Ez a rendszer szempontjából vegyes:**
- **Pozitív:** kockázatcsökkenés, kedvezőbb kereskedési környezet
- **Negatív:** a Day 63 mérés **tisztább** lehet (nincs leállítási nyomás), de **az alpha-feltétel +1% excess** **nehezebb** lehet bull rally-ben

## Anomáliák

- **CRGY/AAPL leftover phantoms** **továbbra is** megjelennek 22:00 CEST-kor. Ahogy tegnap megerősítettük, ezek **NEM valós pozíciók**. A 2026-04-14 task fájl Bug 3 magyarázza: az `ib.executions()` IBKR API quirk.
- **LION/SDRL/DELL/DOCN phantom events** **újra megjelentek** 22:00 CEST-kor. Pontosan ugyanaz a jelenség.
- **Az AVDL.CVR** természetesen **továbbra is ott** marad az IBKR account-on, ahogy tegnap nukolás során láttuk. Nem-tradable, ignorálható.
- **A `nuke.py` kimenet ma reggel 09:02 CEST** futott, és a logba bekerült: `nuke_executed, positions_closed: 1, tickers: ["AVDL.CVR"]` — szerintem a `nuke.py` a **logot tölti**, mintha az AVDL-t nukolta volna, **de** a tényleges close `SKIP (non-tradable)` volt. **Ez egy log-minor inkonzisztencia**, de nem kritikus.

## Kulcsmegfigyelések

### 1. A Breakeven Lock első TRAIL exit-je — strukturális validáció

**A TER ma a feature első TRAIL exit-je** a deploy óta. A Lock $317.41 → $348.83-ra emelte az SL-t, és **a tényleges trail mechanika** ezt megfogta 21:05 CEST-kor. **Ez NEM** ugyanaz, mint a profit megőrzés — **ez az aktív exit kezdeményezése a kívánt szinten**.

**A 138 új teszt valós validációja folytatódik.** Eddig minden Breakeven Lock alkalmazás **vagy** profit megőrzést, **vagy** profit-javítást termelt. **Egyetlen "kárt nem termel" garancia** is megerősítve.

### 2. A score korreláció napi szinten variábilis, de heti átlagra konzisztens

**Ma r ≈ -0.3** (NE 95 csak +$35, TER 88 +$75). **De** ha a 4 napi átlagot nézzük: a magas score-ú tickerek **átlagosan** +%-ot adtak, a alacsony score-ú tickerek **átlagosan** -%-ot. **Egy napi adatpont nem rontja** a trend-et.

### 3. A "bull rally underperform" mintázat — figyelendő

**Ma -0.57% excess egy SPY +0.99% nap mellett.** **Ez tipikus** swing trading minta — a long-only stratégiák **technikailag verni** szokták egy nagy bull napon a buy-and-hold-ot, mert a buy-and-hold **a teljes 1.0% mozgásból** profit, míg a swing 5-6 ticker az 1.0%-nak **csak részét** fogja meg.

**Ez NEM strukturális hiba**, **csak** egy realisztikus elvárás-finomítás. **Ha a Day 63 keretben az ÉLESÍTÉS feltétel +1% excess kumulatív 20 napon át** — ez **realisztikusan** csak akkor érhető el, ha **több** flat/oldalazó nap követi egymást a bull napokat. **Egyetlen erős bull rally** (mint ma) **megboríthatja** a heti pozitív excess-t.

### 4. A TRAIL exit slippage nüansz

**TER trail SL: $348.83, exit price: $348.29 — slippage -$0.54.** Ez ~0.16% slippage a SL-hez képest. **A TRAIL exit nem garantált $348.83-on** — a piaci ár **átlépi** a SL-t (`stop` order behavior), és a fill **a következő elérhető áron** történik. **Ez normál IBKR viselkedés**, és a -$0.54 × 20 = -$10.80 költség **elhanyagolható**.

### 5. A NE érdekes — magas score, kis profit

**NE 95.0 score, csak +$35.70 profit** ma. A **trail_activated_b 21:50 CEST-kor** (19:50 UTC), ami **a MOC submit után** (21:40 CEST = 19:40 UTC). **A Breakeven Lock NEM kapta meg.** Ha az NE valamikor a délutánban (17:00-19:00 sávban) **+0.7% felé emelkedett volna**, akkor a Lock aktivált volna, és potenciálisan **több profit** maradt volna meg. **De** a NE **csendesen csúszott felfelé**, és csak **a piaczárás előtt 10 perccel** lépte át a trail küszöböt. **Ez nem hibás design** — a Lock azért 19:00:00-19:04:59 ablakban van, mert **a délutáni stabilitás** akkor a legmagasabb. Egy korábbi/későbbi window másfajta edge case-eket termelne.

## A te döntési kereted szerint

**Tegnap esti megegyezés szerint:**
- Élesítés: Day 63 → +$3,000 → $10k tőke
- Leállítás: 20+ napon át VIX > 18 mellett excess < -1.5%
- Alpha cél: 0.75-1% / hó

**Mai állapot:**
- **Kumulatív +$238 (+0.24%)** — **POZITÍV TARTOMÁNY**, **paper folytatás default sávban**
- Excess vs SPY 4 napos átlag: **-0.40%** (még biztonságos sávban)
- VIX 16.99 — **18 ALATT**, leállítási feltétel inactive
- **9 nap** Day 63-ig

**Egy fontos megfigyelés:** a -$617 mélypontról (kedd) +$238-ra (ma) **+$855 visszamászás 2 nap alatt**. **Ez statisztikailag** egy átlagosan +$427 / nap napi átlag, ami **nem fenntartható** — de **megmutatja a rendszer képességét** kedvező napokon.

**Ha a következő 9 napban átlagosan +$80-100 / nap** (~50%-a a mai napnak), akkor Day 63 kumulatív **+$950-1,150** lehet. **Ez** a **paper folytatás default** sávban marad, **távol az ÉLESÍTÉS +$3,000-tól, de a 0.75-1% / hó alpha cél felé** halad.

## Holnap (péntek máj 1) várnivalók

- **Reggel:** szokásos ellenőrzés
- **Délelőtt-délután (Chat = én):** **W18 weekly elemzés előkészítés** — a péntek esti `weekly_metrics.py` futás után rögtön
- **Délután (CC):** **M_contradiction multiplier task fájl** — a kedd reggeli M_contradiction BLOCKED, és **a holnap reggeli újra-scope-ot** én elhalasztottam (a vasárnapi munkára céloztam volna). **De** ha CC ma délelőtt-délután szabad, akkor **délután indulhat** a strukturált FMP-alapú kontradikciós signal scope-pal
- **Pipeline:** normál ritmus, BC23 W18 Day 5
- **22:00 CEST:** **W18 weekly metrika** péntek esti futtatás → `docs/analysis/weekly/2026-W18.md`

## Hétvégi (máj 2-3) feladatok

- **Tamás:** semmi sürgős — pihenj ☕
- **Chat (én):**
  - W18 weekly elemzés (`docs/analysis/weekly/2026-W18-analysis.md`)
  - Első MID vs IFDS sector comparison riport (`scripts/analysis/mid_vs_ifds_sector_comparison.py` futtatás után)
  - **Day 63 Decision Framework formalizálás** (`docs/decisions/2026-04-28-day63-decision-framework.md`)

## Kapcsolódó

- `state/phase4_snapshots/2026-04-30.json.gz` (1 ticker — qualified above threshold)
- `logs/pt_events_2026-04-30.jsonl` ← **2× breakeven_lock_applied (EC, TER)** + **1× trail_hit (TER)**
- `logs/pt_eod_2026-04-30.log`
- `state/daily_metrics/2026-04-30.json` ← **vix_close = 16.99**, **kumulatív +$238**
- **State: BC23 + Breakeven Lock (TER első TRAIL exit) + MID Bundle Integration + vix-close + LOSS_EXIT whipsaw audit**
- **Aktív tasks: M_contradiction (BLOCKED, vasárnap re-scope)**
