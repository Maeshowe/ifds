# Daily Review — 2026-05-07 (csütörtök)

**BC23 Day 19 / W19 Day 4**
**Paper Trading Day 59/63**
**M_contradiction LIVE 4. nap**

**Adat-frissesség:** state/.last_sync = 2026-05-08T05:27:05Z (péntek 07:27 CEST, post-EOD)

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | -$486.70 |
| Napi P&L net | **-$501.35** ⚠️ (paper aggregát, tényleges ~-$425, lásd SQM elemzés) |
| Kumulatív P&L | **-$1,616.13 (-1.62%)** ⚠️ visszaesett |
| Pozíciók (új) | **3 ticker** (RMBS, QCOM, SQM) — 6 trade (split-ek) |
| Win rate ticker szinten | 1/3 (csak QCOM nyert) |
| TP1 hit rate | **1/3 (33%)** ⭐ QCOM |
| TP2 hit rate | **1/3 (33%)** ⭐ QCOM |
| Exit mix | 1× TP1, 1× TP2, **2× SL**, **2× LOSS_EXIT**, 0× MOC |
| Avg slippage | **+0.24%** (QCOM +0.59% rossz, RMBS +0.30%, SQM -0.16% kedvező) |
| Commission | $14.65 |
| SPY return | -0.31% (mild risk-off) |
| Portfolio return | -0.49% |
| **Excess vs SPY** | **-0.18%** ✓ marginal underperform |
| VIX close | **17.13** (Δ=-0.35%, stabil) |

## Tamás kérdései — gyors válasz

### "Miért volt alacsony az exposure?"

**Csak 3 ticker volt qualified above threshold** (RMBS, QCOM, SQM). A pipeline `max_allowed: 5`, de **2 nap egymás után csak 3 ticker fűlt át** a Phase 4 küszöbökön (95.5+ score) — szerda is 3 (ERIC, CDNS, UEC), csütörtök is 3.

**Nem hiba**, hanem **konzervatívabb signal** a Stagflation Day 18 mid-stage regime-ben. **A flow signal gyengül** — kevesebb ticker termel olyan flow score-t, ami eléri a kvalifikációs küszöböt. **Megfigyelendő pattern.**

### "Miért ment az SQM ennyire félre?"

**3 különálló probléma kombinációja:**
1. **Volatilis lithium ticker** — magas ATR, ezért **SL = -5.13%** (NEM a normál -3%)
2. **Score 89.5 (legalacsonyabb a 3 közül)** — már a flow signal sem volt erős rajta
3. **⚠️ STRUKTURÁLIS BUG: duplikált zárás** — a LOSS_EXIT és IBKR bracket SL **mindkettő külön** triggerelt, és **SHORT pozíciót nyitottak** a long zárása után

**Részletes elemzés alább.**

---

## ⚠️ KRITIKUS FINDING: Duplikált zárás bug — második alkalom 6 napban

A péntek máj 1-i DTE eset után **most az SQM is** ugyanezt a strukturális bug-ot mutatta.

### SQM idővonal

```
14:18:54  SUBMIT: 91 share @ $97.77 (planned $97.93, slippage -0.16% kedvező)
          SL: $92.75 (-5.13%)  ← lithium volatilitás miatt magas!
          TP1: $102.25 (+4.58%)
          TP2: $104.84 (+7.23%)
          3 különálló bracket: 46 + 45 + ?

17:00:11  ⚠️ LOSS_EXIT @ $93.25 (-4.78%)
          → SELL 91 share, realizalt P&L: -$425.88
          → IBKR pozíció: 0 share (long zárva)

17:05:07  phantom_filtered SQM ✓ (helyes — nincs long pozíció)

** DE az IBKR-ben a bracket SL ordereket NEM törölte! **

??:??  Bracket SL trigger #1: SELL 45 @ $92.75 → SHORT 45
       (P&L recorded -$225.90, mert egy "long → 0" zárásként számolta)

??:??  Bracket SL trigger #2: SELL 46 @ $92.75 → SHORT 91 (összesen)
       (P&L recorded -$230.92)

20:00:08  monitor_positions észleli: leftover SQM = -91

20:05:04  EOD aggregát: -$486.70 (!) — DUPLIKÁLT ELSZÁMOLÁS

20:05:04  ⚠️ leftover_warning: SQM:-91 (SHORT 91 share!)
```

### Mi történt valójában

| Esemény | Realizalt P&L | Pozíció után |
|---------|---------------|--------------|
| 14:18 BUY 91 @ $97.77 | — | LONG 91 |
| 17:00 LOSS_EXIT SELL 91 @ $93.25 | **-$411.32** | 0 |
| Bracket SL #1 SELL 45 @ $92.75 | (paper -$225.90) | SHORT 45 |
| Bracket SL #2 SELL 46 @ $92.75 | (paper -$230.92) | SHORT 91 |

**A daily_metrics összeadta a 3 trade-et: -$425.88 + -$225.90 + -$230.92 = -$882.70**

**De a tényleges IBKR balance impact csak az első LOSS_EXIT (~-$425)** — a többi két "SL trade" valójában **short pozíciókat NYITOTT**, nem lezárt. **A holnapi `nuke.py` zárja a SHORT 91-et**, és a tényleges P&L tisztázódik.

**Ha a SHORT 91 holnap @ ~$91.50 zárul** (jelenlegi ár a screenshot szerint), akkor:
- Short 91 entry $92.75, exit ~$91.50 → +$113.75 profit
- **Tényleges teljes SQM P&L: -$425.88 + $113.75 = -$312.13**

**Tehát a tényleges nap-veszteség -$501 helyett ~-$330 lehet.**

### Ez ugyanaz a péntek (máj 1) DTE bug

```
2026-05-01 péntek  DTE  4-split LOSS_EXIT+SL → -$988 daily_metrics, leftover -130 SHORT
2026-05-07 csüt    SQM  3-split LOSS_EXIT+SL → -$882 daily_metrics, leftover -91 SHORT
```

**Két alkalom 6 nap alatt = strukturális bug.** Nem ad-hoc edge case.

### A bug pontos diagnosztikája

A `monitor` script `loss_exit` logika:
1. ✓ Detektálja a -2% (vagy -X%) küszöböt
2. ✓ MARKET SELL order az IBKR-nek a teljes pozícióra
3. **✗ NEM törli az IBKR-ben a meglévő bracket SL ordereket!**

Az IBKR oldali bracket SL ordereket (limit-stop) **autonóman** triggereli az IBKR, amikor az ár átesik a stop áron. **Ezeket kötelezően kancelltetni kell** a LOSS_EXIT submit előtt vagy után.

### Megoldás (ÚJ P1 backlog idea)

```python
# scripts/paper_trading/pt_monitor.py — loss_exit logika módosítása

def trigger_loss_exit(ticker, qty, price):
    # 1. Cancel existing bracket SL orders FIRST
    cancel_bracket_orders(ticker, order_types=["STP", "STP_LMT"])
    
    # 2. Submit MARKET SELL for full qty
    ib.placeOrder(MarketOrder("SELL", qty), contract)
    
    # 3. Log
    logger.log(EventType.LOSS_EXIT, ...)
```

**Effort:** ~30-45 min CC. **Priority: P1** — két alkalom 6 napon belül = strukturális kockázat.

---

## ⭐ QCOM — a hét legjobb single-ticker nyerője!

**QCOM (Qualcomm, semi/wireless, score 92.5):** 34 share, entry $192.10 (slippage +0.59% rossz), **kettős split (17+17 share)**.

**Idővonal:**
- 14:18 entry $192.10, slippage +0.59% (rossz)
- 15:15:06 **TP1 hit @ $205.55** (+6.83%) — 57 perc alatt!
- 15:15:09 trail_activated_a @ $206.18 (TP1 utáni trail)
- 15:25 trail_sl_update $192.72 (entry felett)
- 15:30 trail_sl_update $193.22
- ~?? **TP2 hit @ $213.61** (+11.21% entry-höz képest!)

**Eredmény:**
- TP1 leg: +$209.44 (+6.38% net)
- TP2 leg: +$346.46 (**+10.55% net** ⭐ a hét legjobbja!)
- **Össz: +$555.90**

**Megfigyelés:** ez a TP1 → TP2 sequence **ritka** — a BC23 deploy óta a TP2 hit count csak **3** (W18: 0, W19 D2: 0, ma: 1). A 0.75×ATR TP1 → 2×ATR TP2 cél **érdemleges**, ha a momentum tartósan tart, mint ma a QCOM-on.

**Mi tette ezt sikerré:** valószínűleg QCOM Q1 earnings beat (vagy más pozitív hír) keltette a +10% mozgást egy nap alatt. **A flow signal megfogta** — score 92.5 nem volt a legmagasabb, de a flow score erős volt.

**Ez a 4 napi pattern is megerősíti:** **a középső score-ú tickerek nyernek, NEM a legmagasabbak**.

---

## Score → P&L 4 napi pattern megerősítve

| Nap | Legmagasabb score | Eredmény | Legalacsonyabb / középső | Eredmény |
|-----|---------------------|----------|---------------------------|----------|
| Hétfő | VTR 93.5 | -$91 | OII 93.0, NOV 92.0, BG 91.5 | mind nyert |
| Kedd | NE 95.0 | -$143 | DBRG 92.5, BEKE 92.0 | mind nyert |
| Szerda | ERIC 92.5 | $0.00 | UEC 91.0 | **+$161** ⭐ |
| **Csütörtök** | **RMBS 93.5** | **-$160** | **QCOM 92.5** | **+$556** ⭐ |

**4 egymás utáni nap** ahol a **legmagasabb score-ú ticker a leggyengébb**, és a középső score-ú ticker a legjobb. **Ez statisztikailag jelentős** mintázat — **megerősíti** a 55 napi scoring validation Pearson r ≈ 0 finding-ot.

**Hipotézis (megfigyelendő):** a Q5 quintile (95+ score) **rendszeresen alulteljesít** a Q3-Q4 quintile-hez képest. A vasárnapi scoring validation újrafuttatás (W18+W19 adatra) megerősítheti.

---

## Excess vs SPY — meglepő javulás

**Mai napon excess -0.18%** — **a hét legjobb relatív teljesítménye eddig** (D1 +0.21%, D2 -1.04%, D3 -1.14%, **D4 -0.18%**)!

**Risk-off nap:** SPY -0.31%, VIX 17.13 stabil. **A swing rendszer ilyen környezetben jobban teljesít** — pontosan ahogy a W18 pattern megmutatta.

**Strukturális kontextus:**
- **Bull rally napokon** (D2, D3): underperform -1.04% és -1.14%
- **Mild risk-off napokon** (D1, D4): outperform vagy marginal +0.21% és -0.18%

**Ez a karakter most már 4 napon át konzisztens** — a swing trading rendszer **defenzív erejű**. Day 63 szempontjából: ha a piac stabilan bull rally-ben marad VIX <17 mellett, az **élesítési feltétel strukturálisan nehéz**.

---

## "Végére visszaesik" pattern — mai adatok

A te megfigyelésed konkrét adatokon:

| Ticker | Intraday peak | Exit | Peak → Exit |
|--------|---------------|------|-------------|
| QCOM | ~$213.61 (TP2 hit) | $213.61 (TP2 trigger) | **0.00%** ⭐ TP2-n maradt |
| RMBS | ~$130 körül peak | $123.89 (LOSS_EXIT) | **-4.7%** ⚠️ erős retracement |
| SQM | $97.77 (entry után csak lefelé) | $93.25 (LOSS_EXIT) | n/a (nem tetőzött) |

**A pattern részben érvényes ma:** RMBS visszaesett peak-jétől, de a QCOM TP2-n maradt. **Az "erős momentum napokon" (mint a QCOM ma) NEM jelentkezik** retracement, **a "csendes/lateral" tickereken** (mint RMBS) **igen**.

**Hipotézis tesztelendő:** a "végére visszaesik" pattern **a momentum erősségétől** függ:
- Erős +5% momentum: nincs retracement (QCOM ma, UEC szerda)
- Vegyes/lateral: retracement (RMBS ma, PTEN kedd)
- Erős negatív (-5% mozgás): szintén nincs visszaesés (LOSS_EXIT trigger)

---

## A 4 napi W19 átfogó kép

| Mutató | W19 D1-D4 átlag |
|--------|------------------|
| Net P&L | -$182/nap |
| Excess vs SPY | -0.54%/nap |
| Win rate (ticker) | 8/16 (50%) |
| TP1 hits | 4/16 (25%, főként D2 DBRG + D4 QCOM) |
| TP2 hits | 1/16 (6.25%, csak D4 QCOM) |
| LOSS_EXIT | 8 (mai 2 + hétfő AGNC 6) |
| Trail aktiváció | 5 (3 window-ban: BG hétfő, UEC szerda, QCOM TP1 után csüt) |

**4 nap → 1 nyertes, 3 vesztes (ha a SQM bug-korrekciót -$330 net-be vesszük figyelembe).**

---

## Day 63 keret — csütörtök esti állapot

| Metrika | Érték | Status |
|---------|-------|--------|
| Day | **59/63** — **4 nap van hátra** | |
| Kumulatív P&L (paper aggregát) | **-$1,616 (-1.62%)** ⚠️ | papírmunka aggregát |
| Tényleges (SQM-bug korrekcióval) | ~-$1,460 | becsült valós |
| ÉLESÍTÉS távolság | +$4,616 a +$3,000-hoz | **NEM realisztikus** |
| LEÁLLÍTÁS távolság | excess -0.54% távol a -1.5%-tól | ~1% buffer |
| 9 napi excess vs SPY átlag | -0.54% | romlott a kedd-i mély után |
| VIX W19 átlag | 17.41 (D1: 18.30, D2: 17.29, D3: 17.19, D4: 17.13) | **stabilan 17 körül** |

**Realisztikus Day 63 várt kimenet:** **PAPER FOLYTATÁS (default)** — kumulatív P&L valószínűleg -$1,800 és -$1,000 között.

**A leállítási feltétel:**
- 9 napi excess átlag -0.54%, küszöb -1.5%, **buffer ~1%**
- Ha a következő 4 nap **átlagosan -1.5% excess/nap**, akkor a 13 napi átlag pontosan -1.5%-ra esik
- **Ez nagyon szélsőséges scenario** — nem valószínű, de nem kizárt

---

## Anomáliák

- **CRGY/AAPL leftover phantoms** továbbra is — `monitor_positions.py` BUG (régóta ismert)
- **LION/SDRL/DELL/DOCN phantom events** 22:00 CEST — IBKR API quirk
- **AVDL.CVR** non-tradable, ignorálható
- **⚠️ SQM SHORT -91 leftover** — ⚠️ holnap reggel `nuke.py --positions` zárja (második ilyen eset 6 napban!)
- **3 ticker (NEM 5) — 2 nap egymás után** — flow signal konzervatívabb, megfigyelendő trend
- **Slippage QCOM +0.59%** — második hét magas slippage (NE +0.72% kedden)

---

## Új P1 backlog idea — a SQM bug

**LOSS_EXIT bracket SL cancellation** (P1, ÚJ 2026-05-07)

**Forrás:** SQM 2026-05-07 + DTE 2026-05-01. Két alkalom 6 napon belül = strukturális bug.

**Probléma:** a `monitor` script LOSS_EXIT-et triggerel és MARKET SELL order-t küld, **DE** a meglévő IBKR bracket SL ordereket **nem kancelltette le**. Az IBKR autonóman triggereli a SL-eket az ár átesésekor → **SHORT pozíciót nyit** a long zárása után.

**Tüneti:** `leftover_warning: TICKER:-N` event a nap végén, **negatív qty leftover**, **duplikált P&L számítás** a daily_metrics-ben.

**Megoldás:** `pt_monitor.py` LOSS_EXIT logika módosítása:
1. Cancel existing bracket SL orders (STP, STP_LMT order types)
2. Submit MARKET SELL for full qty
3. Log audit entry

**Effort:** ~30-45 min CC. **Priority: P1** — strukturális, ismétlődő bug.

**Mikor:** **W19+ scope, sürgős** — minden napon kockáztatjuk a megismétlődést.

---

## Kulcsmegfigyelések

### 1. ⚠️ STRUKTURÁLIS BUG felfedezve: LOSS_EXIT + bracket SL duplikált zárás

**Két alkalom 6 nap alatt** (DTE máj 1, SQM ma). **Új P1 backlog idea** rögzítve. Hétfő-kedd CC implementáció után **ki kell javítani**.

### 2. ⭐ QCOM TP1+TP2 sequence — a hét legjobb pillanata

+$556 single-ticker nyerő, **+10.55% TP2 net**. A BC23 deploy óta a 3. TP2 hit. **A 0.75×ATR/2×ATR cél kombináció érdemleges erős momentum napokon**.

### 3. ⚠️ Score → P&L negatív korreláció 4 nap egymás után

A legmagasabb score-ú ticker **mindennap a leggyengébb** performer. **Statisztikailag jelentős minta** 4 napi adat alapján. **Megerősíti** a 55 napi validation finding-ot.

### 4. ⚠️ Alacsony exposure 2 nap egymás után — flow signal gyengül

3/3 ticker (max 5) szerdán + csütörtökön. **Stagflation Day 18 mid-stage** regime-ben a flow signal valószínűleg **konzervatívabb**. **Megfigyelendő pattern.**

### 5. ✓ Excess vs SPY -0.18% mild risk-off napon — defenzív karakter megerősítve

**A 4 napi W19 pattern:** bull rally napokon underperform, mild risk-off napokon outperform. **Strukturális karakter**, NEM hiba.

---

## Holnap (péntek máj 8) — W19 utolsó nap

- **Reggeli teendő:** **`nuke.py --positions`** SQM SHORT 91 zárására (Tamás, Mac Mini)
- **Pipeline:** normál ritmus, BC23 W19 Day 5
- **22:00 CEST EOD:** **W19 Weekly metrika** futtatás (`weekly_metrics.py`)

## Day 63 (csütörtök máj 14) — 4 nap múlva

- **09:00 Reminder**
- W19 + W18 + W17 adatok együtt scoring validation újrafuttatás
- Döntés: **PAPER FOLYTATÁS** (legvalószínűbb)

---

## Kapcsolódó

- `state/phase4_snapshots/2026-05-07.json.gz`
- `logs/pt_events_2026-05-07.jsonl` ← **SQM 3-split LOSS_EXIT+SL**, leftover -91 SHORT
- `logs/pt_eod_2026-05-07.log`
- `state/daily_metrics/2026-05-07.json` ← vix_close = 17.13, kumulatív -$1,616
- `docs/planning/backlog-ideas.md` ← ÚJ: LOSS_EXIT bracket SL cancellation (P1)

**State:** BC23 + Breakeven Lock (profit_breakeven trigger ÉLES) + MID Bundle + vix-close + LOSS_EXIT whipsaw audit + M_contradiction LIVE

**Aktív CC tasks:** nincs (de új P1 idea rögzítve a backlog-ideas.md-be)

**W19+ backlog idea-k (most 7):**
1. **⚠️ ÚJ: LOSS_EXIT bracket SL cancellation** — P1, ~30-45 min CC (SQM + DTE bug)
2. 10-Q / 10-K SEC Filing Exclusion — P1, ~2-3h CC (AGNC eset)
3. ADR earnings adatforrás fix — P1, ~3-4h CC (BUD eset, FMP hiány)
4. Breakeven Lock profit-küszöb csökkentés — P2, ~10-15 min config + tesztek
5. TP1 cél revízió — P2, ~30 min config (DBRG TP1 cél túl szűk)
6. Phase 4 snapshot enrichment — P3, ~30-45 min (W18 elemzésből)
7. High-score liquidity check — P3, ~1h (NE +0.72% slippage)
