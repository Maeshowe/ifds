# Daily Review — 2026-04-22 (szerda)

**BC23 Day 8 / W17 Day 3**  
**Paper Trading Day 48/63**

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | +$73.13 |
| Napi P&L net | **+$60.11** (commission $13.02) |
| Kumulatív P&L | **-$469.92 (-0.47%)** (gross-alapú, konzisztens a korábbi napokkal) |
| Pozíciók (új) | 3 ticker (MRVL, ASX, CARG) — state-split miatt 4 trade |
| Win rate | 2/3 ticker (MRVL, ASX nyert; CARG vesztett) |
| TP1 hit rate | 0/3 (0%) |
| TP2 hit rate | 0/3 (0%) |
| Exit mix | 4× MOC, 0× LOSS_EXIT, 0× SL, 0× TP |
| Avg slippage | -0.03% (ticker átlag — összességében neutrális) |
| Commission | $13.02 |
| SPY return | **+1.01%** ← **piac fordult** |
| Portfolio return | +0.07% (73/100000) |
| **Excess vs SPY** | **-0.94%** ← **alulteljesítés bull napon** |
| VIX close | 18.85 (-3.28%) |

## Piaci kontextus — a fordulat

**A 3 napos VIX emelkedés megtört.** A hétfő-kedd emelkedés (17.44 → 18.86 → 19.49) után ma visszatolta **18.85-re (-3.28%)**. Ezzel együtt **SPY +1.01%** — első zöld nap a hétben.

- **VIX trajektória:** 17.44 (pé) → 18.86 (hé) → 19.49 (ke) → **18.85 (sze)**
- **SPY trajektória:** 708.72 (hé) → ~703 (ke) → **711.21 (sze)**, +$6 rally

**Ez fontos kontextus: ma a piac risk-on-ra fordult.** A STAGFLATION félelem enyhült (ha csak 1 napra is), és a momentum tickerek nyertek volna — **de mi alulteljesítettünk a piacnál** (-0.94% excess). Ez a nap **másfajta** kudarc, mint a hétfő: nem a regime-mismatch, hanem a **helyi sector selection** miatt.

## Pozíciók

| Ticker | Score | Sector | Entry (avg fill) | Exit (MOC) | P&L | Notes |
|--------|-------|--------|------------------|------------|-----|-------|
| MRVL | **93.5** | Tech/Semi | $153.90 | $157.36 | **+$242** | Trail B aktív délután, MOC close |
| ASX | 93.0 | Tech/Semi | $29.91 | $29.92 | **+$2.50** | Flat MOC (+0.02%) |
| CARG | 93.0 | Cons. Cyclical | $38.54 | $38.11 | **-$172** | Kis loss, MOC-ig nem triggerelt bevágás |

## A nap története — MRVL, Trail B, de nem TP1

**MRVL a napi nyertes**, de **nem TP1 hit**. Nézzük meg a lánc részletét:

```
14:18 UTC  Entry: $154.25 (planned), fill $153.90 (pozitív slippage, -0.23%)
           SL $144.51, TP1 $162.36 (+5.47%), TP2 $167.23 (+8.68%)

17:00 UTC  Trail B activated @ $155.35 (+0.72%), trail_sl $145.61
17:05-17:25 Fokozatos trail: $146.19 → $146.73 (ár $155.93 → $156.47)
17:45      trail_sl $147.31 (ár $157.05)
17:55      trail_sl $147.60 (ár $157.34)
18:00-18:30 trail fokozatosan tovább: $147.80 → $148.69 (ár $157.79 → $158.43)
           >>> Legmagasabb intraday ár ~$158.43, TP1 $162.36 NEM ÉRTE EL
19:40      MOC close @ $157.36

Final P&L: +$242.20 (+2.25%)
```

**Kulcsmegfigyelés:** MRVL a nap legmagasabb pontján **$158.43** volt, a TP1 $162.36 — **távolság ~2.5%**. A volatilitás **nem volt elegendő** a TP1-re. Ha tegnap POWI-nél (+8.96% intraday) volt egy kiugró nap, akkor MRVL (+2.25% MOC) csak **átlagos**. **A TP1 1.25×ATR az átlagos napokon továbbra is messze van.**

## A CARG anomália — kétszeres balszerencse

CARG **-$172 a nap végén** (2 split × -$107.50 és -$64.07), de **NEM LOSS_EXIT**. Ez egy **új minta** — a loss_exit mechanika **nem triggerelt**, mert a ticker **nem esett -2% alá** a nap során. Csak MOC-nél zárult -1.12%-on.

Amit a Company Intel jelzett CARG-ra:
> "Price trading 2.8% above analyst consensus target ($37.42) somewhat contradicts the high IFDS score (93.0)"

**Ez egy enyhe CONTRADICTION flag** — nem durva, mint a hétfői GFS (target High fölött), csak "above consensus 2.8%-kal". És **veszített**. Konzisztens a W17 Day 1 mintájával: **a contradiction flag negatív prognózis**, **még ha enyhe is**.

**Egy extra apróság — slippage is bántott:** CARG planned entry $38.47, fill $38.54 = **+0.18% negatív slippage**. 399 shares × $0.07 = **~$28 extra kár** a tervezetthez képest. Ez a napi -$172-ből kb. 16%. A CARG csak -1.12%-ot esett, de mi egy kis negative slippage-t is kaptunk — **double unlucky**.

**Ezzel szemben MRVL +0.23% pozitív slippage** ($154.25 → $153.90 fill). 70 × $0.35 = **~$25 extra nyereség** csak a fill minőségen. A net-net: a slippage ma **neutrális** volt átlagban (-0.03%), de ticker-szinten **aszimmetrikusan** osztott.


## ASX — flat nap, de nyereség

ASX +0.02%, gyakorlatilag **flat**. Az entry $29.91 → exit $29.92 = +$2.50. Legalább a kommisszió **nem vitte el** teljesen. Ez a ticker **tajvani semi back-end** cég (ASE Technology). Nincs analyst target a Company Intelben — ez **ritka** (általában van), és a cég **non-US listed ADR**, ezért lehet. Ez az adat-hiány **strukturális hátrány** az ADR tickereken, mint korábban SKM-nél is láttuk.

## W17 első 3 nap — kumulatív mintázat

| Nap | Pozíciók | Win rate | TP hit | Net P&L | Excess vs SPY | Contradiction |
|-----|----------|----------|--------|---------|---------------|---------------|
| Hétfő | 5 | 1/5 | 0/5 | **-$433** | **-0.21%** | 3/5 flagged → mind vesztett |
| Kedd | 3 | 2/3 | **2/5** | **+$553** | **+1.22%** | 0/3 flagged → 2 nyertes |
| Szerda | 3 | 2/3 | 0/3 | **+$73** | **-0.94%** | 1/3 enyhe flag (CARG) → flag vesztett |
| **W17 1-3 nap** | **11** | **5/11 (45%)** | **2/13 (15%)** | **+$193 net** | **átlag +0.02%** | 4/11 flagged, 4/11 flagged vesztett |

**Trend:** a contradiction pattern **tovább erősödik**. Eddig **8 ticker** közül **4 flagged**, **mind a 4 vesztett**, **0 nyert**. Ez már nem véletlen. **4/0 split**, 100% hit rate a negatív prediktorra.

## Kulcsmegfigyelések

### 1. Az első "mid" nap — sem jó, sem rossz

A hétfő-kedd drámai kontraszt után a szerda **unalmas**: +$73 nyereség, de **-0.94% alulteljesítés bull napon**. Ez **pontosan az** a középszer, amire a BC23 **is** képes. A rendszer **nem veszít sokat**, de **nem is fog alfát** bull piacon.

Ez egy fontos kép. Ha minden nap ilyen lenne, a heti eredmény ~+$250 lenne. **Nem rossz, de nem is kiváló.** A paper trading Day 63 döntéshez **több kell**, mint "nem veszít sokat".

### 2. A contradiction pattern most 4/4

3 napnyi adat után:
- **Hétfő:** CNK (0/4 beat), GFS (ár High fölött), SKM (JPM+Citi downgrade) — mind 3/3 vesztett
- **Kedd:** 0 flag — 2/3 nyertes
- **Szerda:** CARG (ár 2.8% consensus fölött) — 1/1 vesztett

**4/4, nincs kivétel.** Ez **statisztikailag** már közelíti a **szignifikanciát**, de a minta **még mindig kicsi** (4 adatpont). Pénteki heti metrika **megerősíthet** vagy **gyengíthet**.

**Ha a péntek is hozzá ad 1-2 flagged vesztes tickert:** W18 elején az **M_contradiction multiplier** erős jelölt a backlog-ideas-ből. Konzervatív implementáció: ×0.7 flag esetén (nem ×0.5 — kezdjük gyengébben).

### 3. A TP1 hit rate visszaesett

- Hétfő: 0/5
- Kedd: **2/5** (POWI)
- Szerda: 0/3

A keddi POWI volt a **kivétel, nem a szabály**. Ahhoz, hogy a TP1 működjön, **ticker-szintű +5-8% intraday move** kell — ez a napok többségén **nincs meg**. A MRVL ma +1.6% intraday (entry → max), ami **nagyon átlagos**, és a TP1 $162 (+5.5%) messze volt.

**Ez erősíti a backlog-ideas-ben rögzített javaslatot:** a TP1 távolságát érdemes lesz **ticker-szintű volatilitással** skálázni (GARCH vagy realizált ATR), nem fix 1.25×ATR multiplierrel. De ez **BC24+ scope**, nem most.

### 4. A regime + SPY bounce miatt a momentum most nem segített

Paradox: ma a SPY +1.01%-ot csinált, ami **bullish** nap, de a **mi momentum-heavy scoring-unk NEM nyert**. Ez érdekes — az elmúlt 3 nap együtt:

- Hétfő (SPY -0.20%): BC23 -$433 → momentum szekror-rotáció rossz
- Kedd (SPY -0.65%): BC23 +$553 → semi szektor divergence, momentum jó
- Szerda (SPY +1.01%): BC23 +$73 → semi szektor **lassult** (MRVL +2.25%, ASX flat), broad market nyert

A BC23 scoring **sector-bias-szal** jár: ha a semi/tech rally-zik (kedd), nagy nyereség; ha a broad market rally-zik (szerda), **alig nyerünk**. Ez **szektor-kitettségi kockázat**.

**A MID CAS heatmap a hétfőn mutatta:** ma **XLI Industrials +4.1** (CAS OVERWEIGHT), **XLV Health +4.0** (CAS OVERWEIGHT). **Ma a broader cyclicals rally-ztek**, nem a semi. Ha a Phase 3 ezt látta volna, talán XLI/XLV tickert vett volna, nem MRVL/ASX-et. **Pontosan a BC25 MID Bundle Integration task motivációja.**

## Leftover-ek

- `CRGY` még mindig ott van (régi márciusi)
- `AAPL` még mindig ott van
- **Hétvégi teendő:** Tamás manuálisan nuke

## Telegram regresszió megmaradt

A Telegram submit üzenet **NEM tartalmazza** a "4/6 Individual Stock Analysis" breakdown-t. Ez BC23 utáni regresszió, backlog-ba felvéve. Kis task, később CC fogja.

## Anomáliák

- **daily_metrics.json késve érkezett, de megvan.** Az első ellenőrzéskor (~22:30) még nem volt ott, de ~1 órával később megjelent. **Nem hiba** — a `pt_daily_metrics` cron valószínűleg a pt_eod után futott késleltetéssel. Érdemes lesz a cron logot **hétvégén** átnézni, hogy pontosan mikor fut, és dokumentálni.
- **pt_events `trades: 4`** de **3 ticker** — a CARG kétszer split (200+199), tehát ticker-szinten 3 pozíció volt, de a trade count 4 (CARG két split-je). Nem hiba, state-split artifact.

## A hét közepi tanulságok (W17 1-3 nap)

1. **A contradiction pattern 4/4** — erősödő jelzés a M_contradiction multiplier felé
2. **A TP1 1.25×ATR feltételes** — csak magas realized vol napokon működik (POWI)
3. **A szektor-kitettség számít** — bull broad market napon a semi-heavy portfolio alulteljesít
4. **A loss_exit nem triggerel minden rossz napon** — CARG -1.12%-on nem vágott be, csak MOC-on
5. **Az ADR hátrány** (ASX, SKM) adatminőség-probléma — nincs elemzői target, lassabb Company Intel, nehezebben megítélhető

## Teendők

- **Ma este:** nincs
- **Csütörtök-péntek:** napi review-k folytatódnak
- **Péntek (ápr 24):** W17 heti metrika — 5 napos BC23 Day 6-10 összegző
- **Hétvégén:**
  - Tamás: CRGY + AAPL leftover nuke
  - daily_metrics generation ellenőrzése (miért nem futott ma)
  - Chat: kezdeti MID vs IFDS sector összehasonlítás (most még szerény, csak vizuális CAS heatmap alapján)

## Kapcsolódó

- `state/phase4_snapshots/2026-04-22.json.gz`
- `logs/pt_events_2026-04-22.jsonl`
- `logs/pt_eod_2026-04-22.log`
- `logs/cron_intraday_20260422_161500.log`
- `state/daily_metrics/2026-04-22.json` — **HIÁNYZIK**, nézendő
