# LOSS_EXIT Whipsaw Analysis — Adatvezérelt audit a -2% stop-loss szabály hatásáról

**Status:** DONE
**Updated:** 2026-04-29
**Created:** 2026-04-29
**Priority:** **P2** — fontos diagnosztika, de nem sürget
**Estimated effort:** ~1.5-2h CC

**Depends on:**
- nincs

**NEM depends on:**
- M_contradiction multiplier (P1, szerda) — független
- 19:00 CEST Breakeven Lock (élesben) — független
- MID Bundle Integration (élesben) — független

**Sürgősség:** **csütörtök vagy péntek** vagy hétvége — **NEM** szerda. A szerda az M_contradiction-é.

---

## Kontextus — a NIO 2026-04-28 eset

A 2026-04-28 (kedd) kereskedési napon a NIO pozíció `LOSS_EXIT`-tel zárt **-$239.25** (2 split: -$104.25 + -$135.00) veszteséggel. Tényleges idővonal:

```
16:18 CEST  Entry: NIO $6.43 (slippage +0.16% a $6.42 limithez)
            SL $5.98, TP1 $6.79, TP2 $7.00

~17:00-19:00 CEST  Az ár átmenetileg lefelé spike-ol (chart alapján
                   a mély piros wick ~$6.10-6.15 sávig ér)

19:05 CEST  LOSS_EXIT @ $6.29 trigger (-2.02% a $6.42 limittől)
            Tényleges fill: $6.28 (EOD reconciled)

19:05 után  Az ár visszamászott, MOC közeli ár ~$6.30-6.37 sávban
            (TradingView 22:00 CEST close: $6.37)
```

**Megfigyelés:** ha a pozíció **MOC-ig fennmaradt volna**, a veszteség **-$0.05 × 1595 = -$79.75** lett volna. A LOSS_EXIT viszont **-$239** kárt termelt — **háromszorosát** a MOC-szcenárió várható kárának. **A szabály ebben az esetben rontotta a teljesítményt.**

A felhasználó észrevétele teljesen jogos: **ez egy klasszikus "whipsaw"**, ahol az átmeneti spike kilőtte a stop-ot, mielőtt az ár visszajött volna.

## A kérdés, amit megválaszolunk

> **Az eddigi BC23 LOSS_EXIT triggerek átlagosan segítettek vagy rontottak a teljesítményen?**

Másik megfogalmazás: **mennyi a "whipsaw cost"** összesen? Ha pozitív, a LOSS_EXIT **rontott** átlagban (mint a NIO ma). Ha negatív, a LOSS_EXIT **megóvott** nagyobb kártól.

**Ez egy adatmérés, NEM viselkedés-változás.** A szabály változatlanul fut élesben. Csak **utólag mérjük**, hogy az eddigi 60+ napi adatban hogyan teljesít.

## A metodológia

Minden történeti LOSS_EXIT trade-re számoljuk ki:

```
whipsaw_cost = (actual_loss_exit_pnl) - (counterfactual_moc_pnl)
```

Ahol:
- **actual_loss_exit_pnl** = a tényleges P&L (negatív szám, ahogy a logokban van)
- **counterfactual_moc_pnl** = (moc_price - entry_price) × qty (hipotetikus, ha tartottuk volna MOC-ig)

A **whipsaw_cost** így:
- **Pozitív** → a LOSS_EXIT **rontott** (ki kellett volna várni a MOC-ot)
- **Negatív** → a LOSS_EXIT **megóvott** (jó, hogy korán kiestünk)
- **Nulla közeli** → semleges (a stop ár ≈ MOC ár)

**Példa NIO 2026-04-28:**
- actual_loss_exit_pnl = -$239.25
- counterfactual_moc_pnl = ($6.37 - $6.43) × 1595 = -$95.70 *(használjuk a TradingView 22:00 zárás $6.37 értéket)*
- whipsaw_cost = -$239.25 - (-$95.70) = **-$143.55** ← a LOSS_EXIT $143 többletkárt okozott

(Megjegyzés: a "whipsaw_cost" előjelét úgy állítjuk be, hogy **negatív érték = LOSS_EXIT rontott**, mert ez a számlád szempontjából az tényleges veszteség. Pozitív = LOSS_EXIT megóvott.)

## Adatforrás

### Bemenet 1: LOSS_EXIT események

**Fájl:** `logs/pt_events_*.jsonl` (összes nap a BC23 deploy óta, 2026-04-13-tól)

```python
def find_loss_exits(start_date, end_date):
    """Returns list of {date, ticker, entry_price, exit_price, qty, pnl}."""
    pattern = "logs/pt_events_*.jsonl"
    for log_file in sorted(glob.glob(pattern)):
        date = parse_date_from_filename(log_file)
        if not (start_date <= date <= end_date):
            continue
        for line in open(log_file):
            event = json.loads(line)
            if event.get("event") == "loss_exit":
                yield {
                    "date": date,
                    "ticker": event["ticker"],
                    "entry_price": event["entry_price"],
                    "exit_price": event["exit_price"],
                    "qty": event["qty"],
                    "pnl": event["pnl"],
                }
```

### Bemenet 2: Tényleges MOC zárás-árak (Polygon API)

A Polygon `get_aggregates(ticker, date, date, "day")` adja a napi OHLC adatokat. A `c` mező a closing price = MOC fill érték.

```python
def fetch_moc_close(ticker, date_str):
    """Fetch the closing price for a ticker on a specific date."""
    api_key = os.environ.get("IFDS_POLYGON_API_KEY")
    client = PolygonClient(api_key)
    bars = client.get_aggregates(ticker, date_str, date_str, timespan="day")
    if not bars:
        return None
    return bars[0].get("c")  # closing price
```

**Fontos pontosítás:** a **closing price ≠ a hipotetikus MOC fill ár** pontosan. A Polygon napi OHLC `c` érték a hivatalos záró ár (4:00 PM ET = 22:00 CEST). Ez egy elfogadható proxy a MOC fill árra. Kis eltérés (<0.1%) lehet a tényleges MOC fill ártól (ami a `MarketOnClose` order típus tényleges fill ára), de **a hatáselemzéshez** elég pontos.

### Bemenet 3: Daily metrics (kontextus)

**Fájl:** `state/daily_metrics/*.json`

Hasznos kontextushoz: aznapi VIX, SPY return, MID regime (ha van).

## Output — markdown report

**Fájl:** `docs/analysis/loss-exit-whipsaw-analysis.md`

### Struktúra

```markdown
# LOSS_EXIT Whipsaw Analysis — BC23 (2026-04-13 — 2026-04-28)

## Összegzés

- LOSS_EXIT triggerek száma: N
- Összesített tényleges P&L: $X
- Összesített counterfactual (MOC) P&L: $Y
- **Net whipsaw cost: $Z** (negatív = LOSS_EXIT rontott)
- Ítélet: "LOSS_EXIT átlagosan segített / semleges / rontott"

## Részletes táblázat

| Date | Ticker | Entry | LOSS_EXIT ár | MOC close | Qty | Actual P&L | Counterfactual MOC P&L | Whipsaw cost |
|------|--------|-------|--------------|-----------|-----|------------|------------------------|--------------|
| 2026-04-15 | SKM | $X | $Y | $Z | 100 | -$149 | -$80 | -$69 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |
| 2026-04-28 | NIO | $6.43 | $6.28 | $6.37 | 1595 | -$239 | -$96 | -$144 |

## Statisztika

- Átlag whipsaw_cost / trade: $X
- Median whipsaw_cost / trade: $Y
- Pozitív whipsaw_cost trades (ahol a LOSS_EXIT segített): N db
- Negatív whipsaw_cost trades (ahol a LOSS_EXIT rontott): M db

## Ticker eloszlás

| Ticker | LOSS_EXIT count | Avg whipsaw cost |
| ... |

## Időbeli minta

- Délelőtt (16-19 CEST): N trade, avg whipsaw $X
- Délután (19-22 CEST): M trade, avg whipsaw $Y

## Következtetés

- "A LOSS_EXIT a vizsgált időszakban átlagosan rontotta a teljesítményt $X-szel napi átlagban"
- VAGY: "Statisztikailag semleges (átlagos hatás <$10/nap)"
- VAGY: "Hasznos: $X-nyi nagyobb kárt fogott meg"

## Javaslatok (NEM most implementáció)

- Ha rontott: érdemes lehet... (időbeli tilalom, magasabb küszöb, stb.)
- Ha segített: a szabály jól van kalibrálva
- Ha vegyes: regime-függő finomítás
```

## Scope

### 1. Adatgyűjtés

Új script: `scripts/analysis/loss_exit_whipsaw_analysis.py`

- CLI flagok: `--start YYYY-MM-DD`, `--end YYYY-MM-DD`, `--output PATH`
- Default: BC23 deploy (2026-04-13) — mai dátumig

### 2. Polygon API integráció

Használja a meglévő `PolygonClient` osztályt (`src/ifds/data/polygon.py`). Cache-elje az aznapi árakat egy lokális JSON-be (`state/loss_exit_analysis_cache.json`), hogy ismételt futtatáskor ne kelljen újra hívni az API-t.

**Rate limit szempont:** maximum ~10-15 LOSS_EXIT esemény van eddig (W17-W18). Egy hívás per ticker per nap. Polygon free tier 5 hívás/perc — bőven elég.

### 3. Számolás

```python
def compute_whipsaw_cost(loss_exit, moc_price):
    counterfactual_pnl = (moc_price - loss_exit["entry_price"]) * loss_exit["qty"]
    actual_pnl = loss_exit["pnl"]
    return actual_pnl - counterfactual_pnl  # negatív = LOSS_EXIT rontott
```

### 4. Markdown report generálása

Sablonalapú, használja a `tabulate` könyvtárat vagy egyszerű manuális formázást.

### 5. Tesztek

**Fájl:** `tests/test_loss_exit_whipsaw.py` (új)

```python
def test_whipsaw_cost_negative_when_moc_better_than_loss_exit():
    """LOSS_EXIT rontott eset — whipsaw_cost negatív."""
    result = compute_whipsaw_cost({...entry: 100, exit: 98, qty: 10, pnl: -20}, moc_price=99)
    assert result < 0  # -20 - (-10) = -10

def test_whipsaw_cost_positive_when_loss_exit_better_than_moc():
    """LOSS_EXIT megóvott eset — whipsaw_cost pozitív."""
    result = compute_whipsaw_cost({...entry: 100, exit: 98, qty: 10, pnl: -20}, moc_price=95)
    assert result > 0  # -20 - (-50) = +30

def test_loss_exit_event_parsing():
    """JSONL parsing helyesen szűri ki a loss_exit eseményeket."""

def test_polygon_moc_fetch_with_cache():
    """A cache működik, második futás nem hív API-t."""
```

## Success criteria

1. **Tesztek:** 4-5 új teszt + a teljes test suite zöld marad
2. **Live verification:**
   ```bash
   python scripts/analysis/loss_exit_whipsaw_analysis.py \
     --start 2026-04-13 --end 2026-04-29 \
     --output docs/analysis/loss-exit-whipsaw-analysis.md
   ```
3. **Output report tartalmaz:**
   - Minden eddigi LOSS_EXIT trade táblázatosan
   - Net whipsaw cost összegzve
   - Ítélet (rontott / semleges / megóvott)

## Risk

**Zéró.** Indoklás:

1. **Read-only operáció** — semmi sem változik a pipeline viselkedésében
2. **Csak adat gyűjtés és számolás** — egy markdown fájl keletkezik
3. **Nem érinti** a meglévő LOSS_EXIT triggereket, scoring-ot, sizing-ot
4. **Polygon cache** megakadályozza az ismételt API hívásokat

## Out of scope (explicit)

- **A LOSS_EXIT szabály módosítása** — csak adat, nincs viselkedés változás. Ha a riport rontást mutat, **külön task** lesz a finomításra (W19+ scope).
- **Walk-forward backtest** — nem szimulálunk teljes alternatív stratégiákat. Csak az adott LOSS_EXIT triggerek hatását mérjük.
- **Trail/SL whipsaw analízis** — csak a LOSS_EXIT-re koncentrálunk. A trail és hard SL más szabályok, külön audit-ra valók.
- **Egyéni ticker / sektor mintázatok** — a riport bemutatja, de nem von le mély következtetést. Azt a vasárnapi review fogja értékelni.

## Implementation order (CC számára)

1. **Olvasás / megerősítés** (10 min)
   - `logs/pt_events_*.jsonl` formátum ellenőrzése — biztos, hogy `event=loss_exit` mezőnévvel jönnek?
   - `src/ifds/data/polygon.py::PolygonClient.get_aggregates` signature ellenőrzése
2. **Script váza** (15 min) — argparse, log fájl iterálás, LOSS_EXIT események összegyűjtése
3. **Polygon integráció + cache** (20 min) — `fetch_moc_close()` cache-elt változat
4. **Whipsaw cost számítás** (10 min) — egyszerű matematika
5. **Markdown report generálás** (20 min) — tabulate vagy manuális
6. **Tesztek** (20 min) — 4-5 unit test
7. **Smoke test** (10 min) — futtatás a 2026-04-13 — 2026-04-29 sávra
8. **Commit + push** (5 min)

**Összesen: ~1.5-2h.**

## Commit message draft

```
feat(analysis): LOSS_EXIT whipsaw cost retrospective audit

Adds scripts/analysis/loss_exit_whipsaw_analysis.py to compute the
counterfactual MOC P&L for every LOSS_EXIT trigger since BC23 deploy
(2026-04-13). The script answers a structural question raised by the
NIO 2026-04-28 case (LOSS_EXIT $6.28, MOC close $6.37, whipsaw cost
-$144 on a 1595-share position):

  Does the -2% LOSS_EXIT rule help or hurt on average?

For each historical LOSS_EXIT:
  whipsaw_cost = actual_pnl - counterfactual_moc_pnl

Where counterfactual_moc_pnl uses Polygon's daily close as the MOC
proxy. Negative whipsaw_cost means LOSS_EXIT made things worse.

Output: docs/analysis/loss-exit-whipsaw-analysis.md
- Per-trade table with whipsaw cost
- Net summary, time-of-day distribution, ticker distribution
- Conclusion: "rontott / semleges / megóvott"

This is a read-only audit. No pipeline behavior is changed. If the
audit shows a structural problem with LOSS_EXIT, follow-up tasks will
address it in W19+.

Tests:
  - test_whipsaw_cost_negative_when_moc_better_than_loss_exit
  - test_whipsaw_cost_positive_when_loss_exit_better_than_moc
  - test_loss_exit_event_parsing
  - test_polygon_moc_fetch_with_cache
```

## Várható eredmények

Becslés W17-W18 adatból (gyors fejszámolás):

| LOSS_EXIT eset | Becsült whipsaw cost |
|----------------|----------------------|
| SKM 2026-04-20 | ? (intraday spike vagy folytatódó zuhanás?) |
| POWI 2026-04-23 | ? (recent winner mean reversion — valószínűleg folytatta a lefelé) |
| CRWV 2026-04-28 | ? |
| NIO 2026-04-28 (split 1) | ~-$70 (becsült) |
| NIO 2026-04-28 (split 2) | ~-$74 (becsült) |

Ha a teljes mintában **>50% rontott** és **net whipsaw cost > $200**, akkor **strukturális probléma** azonosítva, és a W19+ scope-ban érdemes javasolni egy módosított LOSS_EXIT szabályt:
- **A) Time-of-day:** csak 19:00 CEST után triggerelhet (a délelőtti zaj filterezve)
- **B) "Stay below" feltétel:** csak akkor triggerel, ha 15 percen át tartja a -2%-ot
- **C) Magasabb küszöb:** -2% → -3% (kisebb whipsaw kockázat, nagyobb cap)

**De ezek csak akkor jönnek**, ha az adat indokolja. Most csak mérés.

## Kapcsolódó

- **NIO 2026-04-28 daily review:** `docs/review/2026-04-28-daily-review.md`
- **Felhasználó észrevétele (chat 2026-04-29 reggel):** TradingView screenshot, NIO MOC ár $6.37 vs LOSS_EXIT $6.29
- **Linda Raschke filozófia:** `docs/references/raschke-adaptive-vs-automated.md` — "systems apply rules consistently. Humans notice when the rules no longer apply."
- **Backlog idea (a riport után frissítendő):** `docs/planning/backlog-ideas.md` — új bekezdés a LOSS_EXIT finomításra
- **Polygon kliens reference:** `src/ifds/data/polygon.py::PolygonClient`

## Implementáció időzítése

- **Szerda ápr 29:** **NEM** ekkor — szerda az M_contradiction multiplier-é
- **Csütörtök ápr 30 vagy péntek máj 1:** ha CC-nek van szabad kapacitása
- **Hétvége (máj 2-3):** ha addig nem történt meg, vasárnap megelőzheti a W18 weekly elemzést
- **Vasárnapi W18 weekly elemzés:** ha a riport addig elkészül, beépül a W18-analysis.md-be a kulcs finding-ok közé

## Megjegyzés a Linda Raschke-elv kontextusban

Ez **pontosan** az a típusú vizsgálódás, amit a Raschke-elv javasol: **a systematic szabály (LOSS_EXIT -2%) jól működött 2024-2025-ben** (amikor BC22-23 előtt még nem volt élesben), **de változnak a piacok**. A 2026 áprilisi Stagflation regime + lockstep volatility környezetben **gyakoribbak** a whipsaw mintázatok, mint normál trending piacon.

Az ember (Tamás) észrevette ezt a NIO eseten keresztül. A systematic layer **kódba önti** ezt a felismerést, **mérve** és **dokumentálva**. Ha a finding alátámasztja a megfigyelést, **akkor és csak akkor** módosítjuk a szabályt — fokozatosan, konzervatívan, a Raschke-modellnek megfelelően.

Ez a script **maga a discretionary judgment kódolt formája**. Nem implementál új viselkedést — csak **láthatóvá teszi** a szabály hatását.
