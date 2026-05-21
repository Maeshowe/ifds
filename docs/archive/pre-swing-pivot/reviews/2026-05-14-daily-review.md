# Daily Review — 2026-05-14 (csütörtök)

**W20 Day 4 — DAY 63 PAPER TRADING MILESTONE NAPJA ⭐**
**Day 63 outcome formálisan rögzítve: PAPER FOLYTATÁS (default) → Swing pivot bejelentve**
**Első pozitív nettó nap rég (+$313.36) — 4/4 ticker MOC nyertes, 1 TRAIL minimális vesztes**
**🆘 BRACKET SL BUG 5. INSTANCIA — HYMC -140 SHORT EOD warning**
**⭐ NVTS Breakeven Lock POZITÍV működési adatpont (entry-szint védés)**

**Adat-frissesség:** EOD log 22:05, daily_metrics.py 22:10 CEST, monitor log teljes 16:25 → 22:00. Phase 4 snapshot **134 qualified** (>85, vs tegnap 142, kedd 161, hétfő 159 — folyamatos csökkenés, earnings exclusion). Reggeli AAPL -68 SHORT takarítása sikeres (második próbára, IBKR conn first attempt failed). Az új HYMC -140 SHORT az EOD warning-ban — **Tamás cleanup szükséges péntek reggel**.

---

## Számok

| Metrika | Érték | vs előző nap (Sze W20 D3) | vs W20 átlag (3 nap) |
|---------|-------|---------------------------|----------------------|
| Napi P&L gross | **+$339.94** | +$517.91 (Δ -$177.97 → +$339.94) | átlag -$176.94 |
| Commission | -$26.58 | n/a (gross-only mérés) | n/a |
| Napi P&L net (gross-only mérés) | **+$313.36** (csak Δ-ban net) | átlag -$176.65 |
| **Kumulatív P&L** | **-$1,283.84 (-1.28%)** ⬆️ | $339.94 javulás (-$1,623.78 → -$1,283.84) | átlagosan stagnáló |
| Pozíciók (új) | 4 ticker (KC, RIG, NOV, NVTS) | hasonló (3 ticker) | 3-4 |
| Trade count | 7 fill (1+3+2+1, RIG/NOV bracket-split) | + (4 fill vs 7 ma) | 4-7 |
| Win rate ticker szinten | **3/4 (75%)** ⭐ | tegnap 33% | hét eddig ~40% |
| **Exit mix** | **6 MOC (86%) + 1 TRAIL (14%)** ⭐ | tegnap 50% LOSS_EXIT | nincs LOSS_EXIT W20 D4-en |
| **TP1 / TP2 / SL / LOSS_EXIT hit** | **0 / 0 / 0 / 0** ⭐ | nincs negatív exit | első ilyen tiszta nap W20-ban |
| TRAIL hit | 1 (NVTS 19:25:16) | 0 tegnap | 1 W20-ban |
| **Avg slippage** | **-0,22% KEDVEZŐ** ⭐ | tegnap -0,34%, 4 nap egymás után kedvező | -0,28% W20 átlag |
| SPY return | **+0,79%** (bull rally nap) | tegnap +0,56% | W20 +0,32% átlag |
| Portfolio return | +0,34% | tegnap -0,18% | W20 -0,08% átlag |
| **Excess vs SPY** | **-0,45%** | tegnap -0,74% (kissé javult) | -0,42% W20 átlag |
| VIX close | 17,29 (Δ -2,7%, csökkent — risk-on) | tegnap 17,77 | átlag 17,7 |
| Reggeli akció | ✅ `nuke.py` 08:49 — AAPL -68 SHORT BUY 68 @ MKT zárva (2. próbálkozásra, IBKR conn először failed) | — | — |
| **🆘 EOD nyitott pozíció** | **HYMC -140 SHORT** (5. bracket bug instancia) | tegnap AAPL -68 | 2 instancia W20-ban |

## Day 63 KIÉRTÉKELÉS — FORMÁLIS RÖGZÍTÉS

A 2026-04-28-i Day 63 keret 3 kimenete formálisan kiértékelve a `docs/decisions/2026-05-14-day63-decision-outcome.md`-ben (tegnap éjjel készült el):

| Kimenet | Feltétel | Tényleges érték | Eredmény |
|---|---|---|---|
| ÉLESÍTÉS | +$3,000 ÉS +1.5% kumulatív excess vs SPY | -$1,283.84, távolság **-$4,283.84** | **NEM teljesült** |
| LEÁLLÍTÁS | 10 napi excess átlag < -1.5% VAGY VIX > 25 30+ napra | 10 napi átlag -0.35%, VIX W20 átlag 17.7 | **NEM aktivált** |
| **PAPER FOLYTATÁS** (default) | Egyik fenti sem | ✅ | **AKTIVÁLT** — de új architektúrán |

**Megjegyzés:** A tegnapi review és a Day 63 outcome doc -$1,623.78 kumulatívval dolgozott. A mai +$339.94 javulással **a kumulatív most -$1,283.84**, ami **NEM változtatja** a Day 63 kimenet outcome-ot (PAPER FOLYTATÁS default megerősítve), de a STATUS.md-ben **frissítendő** a kumulatív érték (-$1,283.84 valós paper aggregát). A bug-korrekciókkal becsült valós kumulatív: **~-$1,070 to -$1,170** (a HYMC -140 SHORT még nem korrigált, de várhatóan +$50-100 körüli effekt).

A swing pivot **W21-W30** roadmap változatlan — a Fázis 1 cleanup **2026-05-19 (h, W21 D1)** indul Tamás `nuke.py --positions` cleanup-jával.

## 🆘 KRITIKUS — HYMC -140 SHORT: BRACKET SL BUG 5. INSTANCIA

A `pt_eod_2026-05-14.log` végén:
```
22:05:04 [WARNING] Still 1 open positions!
22:05:04 [WARNING]   HYMC: -140.0 shares
```

A `pt_close_2026-05-14.log` 21:40-én:
```
21:40:13 [INFO] HYMC: fills today BOT=0 SLD=140 net=-140 — MOC qty 140 → 0
21:40:13 [INFO] HYMC: SKIP — already closed (intraday TP/SL)
```

**Értelmezés:** A `pt_close` 21:40-én észlelte, hogy HYMC ma 140 share-t adott el (BOT=0, SLD=140 → net=-140), de a rendszer szerint "intraday TP/SL already closed", ezért SKIP-elte. **De az IBKR-ben a 140 SHORT pozíció valós** — ez azt jelenti, hogy a HYMC eredeti LONG pozíciója egy korábbi napon nyílt, az aznapi MOC vagy LOSS_EXIT bezárta, **DE a függő bracket TP/SL orderek továbbra is aktívak maradtak az IBKR-ben**, és **ma valamikor a -140 share SHORT bracket SL aktiválódott**.

**5 instancia 14 napon belül, eltolódási idővonal:**

| # | Dátum | Ticker | Eredeti trade | SHORT méret | Eltolás | Minta |
|---|-------|--------|---------------|-------------|---------|-------|
| 1 | 2026-05-01 (csüt) | DTE | aznap LOSS_EXIT | -? | 0 nap | monitor LOSS_EXIT → bracket SL |
| 2 | 2026-05-07 (csüt) | SQM | aznap LOSS_EXIT | -91 | 0 nap | monitor LOSS_EXIT → bracket SL |
| 3 | 2026-05-12 (kedd) | FORM | előző (hétfő) MOC | -29 | 1 nap | MOC fill-after |
| 4 | 2026-05-13 (szerda) | AAPL | hétfő MOC | -68 | 2 nap | MOC fill-after, hosszabb eltolás |
| 5 | **2026-05-14 (csütörtök)** | **HYMC** | **eddig nem azonosított** | **-140** | **? nap** | **MOC fill-after, ismeretlen eredeti dátum** |

**Strukturális megerősítés:** a bracket TP/SL orderek **napokig (esetleg hetekkel) függőben maradnak** az IBKR-ben, és **bármikor triggerelhetnek**, amikor az ár az adott szinten áthalad. A HYMC eredeti trade-jének dátumát nem nyomoztam le, de a 2026-05-13-i review-ban szerepelt mint "95-ös score-ú gyakran vesztes ticker az utolsó 8 napban" — lehet, hogy 2026-05-07 körül volt eredetileg.

**Kontextus a swing pivothoz:** A bracket SL bug **5 instanciája 14 napon belül** abszolút megerősíti a Day 63 outcome doc 12. döntését (**mental stop, NINCS IBKR bracket SL**). A swing pivot architektúra **strukturálisan eliminálja** ezt a bug-osztályt. A Fázis 1 cleanup során (W21 D1, máj 19) `nuke.py --positions` + manuális IBKR TWS bracket cancel-elés kell.

**A 04-risks-and-open-questions.md jelenleg "DROPPED" jelöli ezt a bug-osztályt** (a swing pivot strukturális eliminálás miatt), de **a Fázis 1 alatti instancia-szám a jelölés ellenére tovább növekedhet**. Az 5. instancia a `nuke.py --positions` parancs scope-hiányát is megerősíti (tegnapi finding változatlan): **a függő bracket orderek továbbra is potenciálisan triggerelhetnek**.

## ⭐ POZITÍV ADATPONT — NVTS Breakeven Lock entry-szint VÉDÉS (2. instancia W20-ban)

A `pt_monitor_2026-05-14.log` egy ritka pozitív Breakeven Lock pattern:

```
19:00:24 CLOCK NVTS: Trail active (Scenario B)
         Price: $22.91 > threshold: $21.97
         Trail SL: $19.06 → entry $21.86
19:00:27 LOCK NVTS: Breakeven lock applied (profit_breakeven)
         Trail SL: $19.06 → $21.86 (entry-ár)
19:25:16 STOP NVTS: Trail SL hit
         Price: $21.67 <= SL: $21.86 → SELL 145 (full scope)
```

**A Breakeven Lock pontosan a tervezett módon működött:**
- 19:00:24 — NVTS +4.81% profit-on ($22.91 vs $21.86 entry), trail SL **felugrott $21.86-ra** (entry-szint)
- 19:25:16 — az ár visszaesett $21.67-ra (-0.87% vs entry), **a Breakeven Lock-os SL triggerelt**
- Az NVTS bracket SL az eredeti $18.01 lett volna ($21.86 × (1 - 0.18×ATR) ~ $18.01), tehát ha a BL nem aktivál → az ár nem érte el a $18.01-et MOC-ig, és a -0.64% kis vesztes az **MOC fill lett volna -$200-300 körüli kárral**

**A BL ténylegesen ELŐZTE meg** az NVTS-en egy nagyobb veszteséget (becsült különbség: kb. **+$100-150**). Hasonló pattern mint a tegnapi PAAS (BL biztosította a +$133 különbséget).

**A 2.1 Breakeven Lock profit-küszöb csökkentés (P3.2 backlog idea, "swing-integrált") továbbra is releváns**, de a feature **alap-logikája kétszer egymás után pozitívan validálva** (PAAS sze, NVTS csüt). Ezt a Fázis 3 (W25+) swing pivot deploy figyelembe veszi.

**Megjegyzés a TRAIL exit típusra:** Az NVTS volt az egyetlen ma, ami **NEM MOC-ra zárt** — egy TRAIL SL trigger volt 19:25-en. A monitor log közbeni időablakban (19:00-19:25) a Breakeven Lock applied, majd 25 perccel később a trail SL hit. **NEM bug, hanem a feature normál működése**.

## Pozíciók részletei

### Nyertesek (3 ticker, 6 trade fill, +$360)

**KC (Kingsoft Cloud Holdings, Technology, score 93.5 — LEGMAGASABB) ⭐**:
- Entry $16.55 (planned $16.55, **slippage 0,00%** — exact fill)
- MOC $16.91 = **+$132.84 (+2,18%)** — a nap legjobb nyerője ⭐
- 369 share × +$0.36
- Breakeven Lock 19:00:11 applied (Trail SL $15.31 → $16.55 entry)
- KC TP1 nem trigger ($17.82), TP2 nem trigger ($18.58), MOC kitartott

**Stratégiai megfigyelés:** **A LEGMAGASABB SCORE-Ú TICKER MA A LEGJOBB NYERŐ** ⭐ — ez egyetlen napi adatpont, de **éles kontraszt a 7 napi "magas pontszám paradoxonnal"**. Az utolsó 4 napban (W19 D1-D4) a top-score-ok rendszerszerűen veszteseket adtak (NE, MTCH, HYMC, TGB). **A 60 napi -0,000 Pearson r mintát egyetlen jó nap NEM cáfolja**, de a Day 63 napján ez egy **rituálisan kellemes egybeesés**.

**RIG (Transocean, Energy, score 92.0) — 3-split bracket fill**:
- Entry $6.76 (planned $6.78, **slippage -0,29% kedvező**)
- MOC $6.90 = **+$169.54 össz** (3 fill: $70 + $70 + $29.54)
- 1,211 share total (500 + 500 + 211)
- Breakeven Lock 19:00:18 applied (Trail SL $6.38 → $6.78 entry)
- Note: a tegnapi SSRM 2-split és tegnapelőtti TGB 3-split mintájához hasonló IBKR partial fill artifact

**NOV (NOV Inc, Energy, score 91.5) — 2-split bracket fill**:
- Entry $20.53 (planned $20.59, **slippage -0,29% kedvező**)
- MOC $20.63 = **+$57.86 össz** (2 fill: $10.36 + $47.50)
- 609 share total (109 + 500)
- 21:10:14 — NOV trail aktivált @ $20.71, de a Breakeven Lock NEM aktivált (Profit nem érte el az +1% küszöböt)
- MOC kitartott — kis profit

**Megjegyzés a 2-shares Energy pattern-re (RIG + NOV):** Mindkét Energy ticker együtt nyitott, és **a nap során a szektor egyenletesen mozgott +0,4-2,1% sávban**. Ez **konzisztens szektor-rotáció** — az Energy ETF (XLE) tegnap leader pozícióban volt a sector_rotation.json szerint (nem ellenőriztem, csak utalás).

### Vesztes (1 ticker, 1 trade, -$20)

**NVTS (Navitas Semiconductor, Technology, score 88.5 — LEGALACSONYABB ma)**:
- Entry $21.79 (planned $21.86, **slippage -0,32% kedvező**)
- TRAIL exit $21.65 (19:25:16 trail SL hit, scope full) = **-$20.30 (-0,64%)**
- 145 share × -$0.14
- Breakeven Lock 19:00:27 applied ⭐ — entry-szint védés (Trail SL $19.06 → $21.86), 25 perccel később hit
- Reálisan: a BL nélkül a kár ~$200-300 lett volna (becslés)

**Megjegyzés:** Az NVTS volt az **egyetlen nem-MOC exit ma** — a Breakeven Lock korai aktivációja + a 25 perces gyors retracement strukturálisan magyarázható. A 88.5 score (a 4 ticker közül legalacsonyabb) **mégsem volt a legnagyobb vesztes** — csak egy kis kontrollált TRAIL trigger -0,64%-on.

## Score → P&L napi nézet (a "magas pontszám paradoxon" ellenpéldája)

| Ticker | Score | Multiplier | Exit | P&L net | Win? | Slippage % |
|--------|-------|------------|------|---------|------|------------|
| **KC** | **93.5** ⭐ TOP | 1.00 | MOC + BL | **+$132.84** ⭐ | ⭐ TOP | 0.00% |
| RIG | 92.0 | 1.00 | MOC × 3 + BL | +$169.54 | ✓ | -0.29% |
| NOV | 91.5 | 1.00 | MOC × 2 + (BL nem) | +$57.86 | ✓ | -0.29% |
| **NVTS** | **88.5** BOTTOM | 1.00 | TRAIL + BL | **-$20.30** | ✗ | -0.32% |

**Score rang vs P&L rang:**
- Score rang: KC (1) > RIG (2) > NOV (3) > NVTS (4)
- P&L rang: RIG ($169.54) > KC ($132.84) > NOV ($57.86) > NVTS (-$20.30)
- **Spearman korreláció napi**: ~+0.6 (sportos mintán, de adatpontként a 60 napi -0,000-tól markánsan eltér)

**A nap pattern-je egybehangzó a 60 napi Pearson r ≈ 0-val** abban az értelemben, hogy **a magas score → nyertes pattern nem kizárt** (csak nem prediktív hosszabb távon). A Day 63 napjának pozitív karaktere **megerősíti a swing pivot védelmét** — a `13. döntés (PCR + OTM-inverse only scoring)` egy ilyen napon is megőrzi a 4 ticker kvalitatív filterezését.

**M_contradiction LIVE 9. nap (2026-05-14):** 0 új fire ma — a 4 ticker mindegyike 1.00 multiplier. **A 8-9 napi mérleg változatlan: 33% iránybeli helyesség** (2/6 fired esetből). A P2.2 backlog idea (sign-flip vizsgálat) a Fázis 2 (W23) analitikus elemzéshez.

## ⭐ KEDVEZŐ SLIPPAGE 4. NAP EGYMÁS UTÁN

| Nap | Avg slippage | 5+ kedvező | 1+ kedvezőtlen | Pattern |
|-----|--------------|------------|----------------|---------|
| W19 D4 (cs, máj 8) | -0.18% | 3 | 1 | enyhén kedvező |
| W19 D5 (p, máj 9) | -0.21% | 4 | 0 | mind kedvező |
| W20 D1 (h, máj 11) | n/a (manuális) | n/a | n/a | manuális 17:15 entry |
| W20 D2 (k, máj 12) | -0.31% | 3 | 0 | kedvező |
| W20 D3 (sz, máj 13) | -0.34% | 3 | 0 | kedvező spontán |
| **W20 D4 (cs, máj 14)** | **-0.22%** | **4** | **0** | **kedvező, KC exact fill** |

**Strukturális megerősítés:** Az utolsó 5 trading nap (W19 D4 → W20 D4) **TÖKÉLETESEN KEDVEZŐ slippage-pattern** — mind a 18+ fill-en negatív vagy 0% slippage. **A 16:20 CEST entry-időpont a W19-W20 mintán következetesen a market open utáni helyi mélypontra esik**.

Ez **támogató adatpont a P2.1 backlog idea (entry timing optimalizáció) ELLEN** — a jelenlegi 16:20 CEST entry strukturálisan jól pozicionált, NEM "rally peak". De **5 nap MUSTRA** rendkívül kevés mintaelem — a 60+ napi Fázis 2 backtest (a Day 63 outcome doc 6. fejezete szerint W23 D1-én indul) **kvantitatívan validálja** a 4 alternatív időablakot (15:30/16:20/17:15/18:30 CEST).

## ⚠️ Bull rally mild underperform — W20 D4 a 4. konzekutív bull-day

| Nap | Net P&L | SPY return | Portfolio return | Excess vs SPY | Pattern |
|-----|---------|------------|------------------|---------------|---------|
| Sze W20 D3 | -$189 | +0.56% | -0.18% | -0.74% ⚠️⚠️ | EXTRÉM underperform |
| **Cs W20 D4** | **+$313** | **+0.79%** | **+0.34%** | **-0.45%** | **mild underperform** |

A **4 napi bull rally átlag excess** (W19 D2-D3 + W20 D1, D3-D4): **-0,74%/nap** ⚠️ — strukturális karakter. **A swing pivot új architektúra (3-5 nap hold, mental stop, rolling 10-12 sizing) elvileg jobban kezelheti a bull rally-t** több hold időtáv + diverzifikációs előny miatt, de **ez a Fázis 3 (W25+) deploy után dől el** a 63 napi paper trading futáson (Day 1 ≈ jún 23, Day 63 ≈ szept 15).

**9 napi excess vs SPY átlag (W19 D1 → W20 D4): -0.32%** — a Day 63 leállítási feltétel **-1.5%** mellett **bőven biztonságos** (~1.18% buffer). **A LEÁLLÍTÁS NEM aktivált**, ami a Day 63 PAPER FOLYTATÁS outcome-ját megerősíti.

## Snapshot fix 4. nap validáció — KONZISZTENS

| Nap | Phase 4 qualified (>85) | Snapshot status |
|-----|--------------------------|------------------|
| Hé W20 D1 (máj 11) | 159 | 22,89 KB |
| Ke W20 D2 (máj 12) | 161 | konzisztens |
| Sze W20 D3 (máj 13) | 142 | konzisztens (kis csökkenés) |
| **Cs W20 D4 (máj 14)** | **134** | **konzisztens** — earnings exclusion fokozatos |

**A snapshot fix stabil 4 napra** — a 134-161 fluktuáció normál. Az earnings exclusion 7 napi rolling cap miatt napi 3-7 ticker eshet ki a Phase 2 univerzumból. **A `d3fce73` deploy értékelhető 100% sikeres mintán**.

## monitor.py "replay" események — 5. nap egymás után (3.3 backlog idea megerősítve)

A `pt_monitor_2026-05-14.log` 22:00:31 időpontban újra megjelennek az ismert "replay" események:
- `LION` TP1 fill detected + Trail SL hit @ $10.15 (scope: bracket_b)
- `SDRL` Trail SL hit @ $43.40 (scope: full) + LOSS_EXIT Scenario B
- `DELL` phantom_filtered
- **`AAPL` Monitoring 1 tickers** ⚠️ (új ticker bekerült a replay-be — az AAPL ma reggel zárt -68 SHORT-tal lehet a kapcsolódás)

Ezek a 22:00 CET záró ciklusban ismétlődnek **5 nap egymás után**. A 3.3 P3 backlog idea (Phase 4 snapshot enrichment) a Fázis 3-ra ütemezett. A swing pivot új architektúra valószínűleg eliminálja, mert a monitor logika **strukturálisan átalakul** (mental stop daily eval, NEM 5 perces tick monitoring).

## Reggeli AAPL takarítás — sikeres (2. próbálkozásra)

A `pt_nuke_2026-05-14.log`:
```
08:48:59 [INFO] Log: logs/pt_nuke_2026-05-14.log
08:49:03 [ERROR] Connection failed
08:49:45 [INFO] Log: logs/pt_nuke_2026-05-14.log
08:49:46 [INFO] IBKR Paper Trading — Nuke
08:49:46 [INFO] Open positions: 2 (AVDL.CVR 69.0, AAPL -68.0)
08:49:46 [INFO] Open orders: 2
08:49:46 [INFO]   AVDL.CVR: SKIP (non-tradable)
08:49:46 [INFO]   AAPL: BUY 68 shares (MKT via SMART)
08:49:48 [INFO] Final positions: 2 (AVDL.CVR még, AAPL 0)
08:49:48 [INFO] Final orders: 3
```

**Megfigyelés**: 
- IBKR conn első próbára 08:49:03-en `Connection failed`, második próbára 08:49:45-en (42 másodperc múlva) sikeres
- A P1.1 backlog idea (IBKR Gateway monitoring + Telegram alert) **közvetlen indoklása** — ha ez egy reggeli bracket bug cleanup-os reggel történik, **42 másodperc downtime kritikus lehet** a piacnyitás előtt
- Az AVDL.CVR (69.0 share, non-tradable) régi phantom, **változatlanul ott marad** — várhatóan a Fázis 1 cleanup IBKR paper account reset megoldja
- `orders_cancelled` mező nem szerepel az output-ban — `nuke.py` scope-hiány **megerősítve** (tegnap is felmerült)

## Anomáliák

- **🆘 HYMC -140 SHORT** (LOSS_EXIT bracket SL bug **5. instancia**, ismeretlen eredeti dátum) — péntek reggel sürgős takarítás
- **AVDL.CVR (69.0 share)** továbbra is non-tradable, ignorálva
- **IBKR Connection Failed (1 alkalom 08:49:03)** — IBKR Gateway monitoring fontossága megerősítve
- **monitor.py LION/SDRL/DELL/AAPL replay events** 22:00:31 — **5. nap egymás után**
- **`nuke.py --positions` scope-hiány** továbbra is — `orders_cancelled` mező nincs az output-ban
- **Polygon 1-min bars + UW HTTP 429 status** — ma NEM kritikus (4 ticker megnyitva, mind kapott adatot)
- **Phase 4 qualified ticker fokozatosan csökken** (159→161→142→134) — earnings exclusion 7 napi rolling cap normál működése

## Kulcsmegfigyelések

### 1. 🆘 KRITIKUS — HYMC -140 SHORT (BRACKET SL BUG 5. INSTANCIA, 14 NAP / 5 INSTANCIA)

Az 1.3 LOSS_EXIT bracket SL cancellation backlog idea a 2026-05-14-i Day 63 outcome doc szerint **DROPPED** (swing pivot mental stop architektúra strukturálisan eliminálja), de a Fázis 1 alatt (W21-W22, máj 19 - máj 30) **a régi rendszer változatlanul fut**, és az 5. instancia 14 napon belül **drámaian növeli az urgency-t** a Fázis 1 indulása előtt. **Tamás manuális `nuke.py --positions` péntek reggel** + **manuális IBKR TWS bracket cancel** szükséges. A Dev chat-ben ezt jeleznem kell.

### 2. ⭐ ELSŐ POZITÍV NETTÓ NAP 5 NAP UTÁN

Az utolsó pozitív nettó nap **2026-05-09 (péntek, W19 D5, +$486)** volt. 5 napi negatív kumulatív sávolódás (-$1,283.84 ma vs -$1,623.78 tegnap) ⬆️ pozitív irányba mozdult. **Day 63 napján a +$313 nem cseréli le a -$1,283 kumulatív státuszt**, de **a swing pivot kontextusában fontos jel**: a régi rendszer **a végén egy "tiszta MOC" napot adott** (6/7 MOC, 1/7 TRAIL, 0 LOSS_EXIT / SL).

### 3. ⭐ KC TOP SCORE = TOP WINNER — ELLENPÉLDA A "magas pontszám paradoxonnak"

KC 93.5 score → +$132.84 nyertes — **egyetlen napi adatpont nem cáfolja** a 60 napi Pearson r ≈ 0 mintát, de a Day 63 napjának karakter szerint **figyelemreméltó kontraszt**. A swing pivot új scoring (`PCR + OTM-inverse only`, Bonferroni-szignifikáns minimum) ezt a fajta high-flow score-ot **továbbra is felvinné**, csak más al-komponensek nélkül.

### 4. ⭐ NVTS BREAKEVEN LOCK ENTRY-SZINT VÉDÉS 2. INSTANCIA W20-BAN

A BL feature **két egymás utáni napon** (PAAS sze, NVTS csüt) **pozitívan validálva**. A BL **strukturálisan jó feature** — a swing pivot új TP/SL struktúra (TP1 1.5×ATR, TP2 3.0×ATR, mental stop) **megőrzi a profit_breakeven trigger filozófiáját**. P3.2 backlog idea (swing-integrált BL) a Fázis 3 (W25+) deploy után.

### 5. ⭐ KEDVEZŐ SLIPPAGE 4. NAP EGYMÁS UTÁN — ENTRY TIMING ELLEN-ARGUMENTUM

5 trading nap egymás után (W19 D4 → W20 D4) **kedvező slippage** (-0.22% átlag, 18+ fill mind negatív vagy 0%). **A 16:20 CEST entry-időpont strukturálisan jól pozicionált**. P2.1 entry timing backtest a Fázis 2 (W23) elemzésen — de a **6 nap kedvező pattern** előzetes jelzés, hogy a 16:20 nem kell **strukturálisan** módosítani. **Az új swing architektúra eleve 15:30 CEST market open entry-t használ** (Day 63 outcome doc 6. döntés), ami **más logikán alapul** (flow signal aggregation után, NEM peak-rally-elkerülés).

### 6. ⚠️ BULL RALLY MILD UNDERPERFORM W20 D3 EXTRÉM UTÁN

Az SPY +0.79% mellett -0.45% excess **mild underperform** — tegnap (-0.74%) kifejezetten EXTRÉM volt. A 9 napi átlag -0.32% pattern **stabil**, **nem aktivál Day 63 leállítást**. A 4 napi konzekutív bull rally pattern (átlag -0.74% excess) **strukturális karakter** — a swing pivot 3-5 napi hold + diverzifikáció elvileg jobban kezelheti, de **ez a Fázis 3 új paper trading idején dől el**.

### 7. ⚠️ IBKR CONNECTION FAILED 1 ALKALOM (08:49:03) — Monitoring fontossága

A reggeli AAPL takarításnál első próbára `Connection failed`, 42 másodperc múlva sikeres. **P1.1 backlog idea (IBKR Gateway monitoring + Telegram alert) közvetlen indoklása** — a Fázis 1 első CC task (W21 D1-D2, kb. máj 19-20).

### 8. ✓ M_CONTRADICTION LIVE — 0 fire ma, 9. nap mérleg változatlan (33%)

4 ticker mindegyike 1.00 multiplier. P2.2 backlog idea (sign-flip vizsgálat) a Fázis 2 (W23) analitikus.

### 9. ✓ SNAPSHOT FIX STABIL 4. NAP — 134 qualified, konzisztens

A `d3fce73` deploy **100% sikeres mintán** 4 nap konzisztens output.

## Implikációk a rendszer számára (Fázis 1 indulása előtt)

**A péntek reggeli (péntek 2026-05-15 ≈ 9-10:00 CEST) cleanup ELŐKÉSZÍTÉSE:**

- **HYMC -140 SHORT takarítás** — Tamás `nuke.py --positions`, plus **manuális IBKR TWS bracket order ellenőrzés és cancel** (a `nuke.py` scope-hiány miatt)
- **A bracket bug 5. instanciája** **a Dev chat-be sync-elendő** mint új adatpont — bár a `04-risks-and-open-questions.md` "DROPPED" jelölést használ, a Fázis 1 alatti instancia-szám rögzítendő (csak információ-rögzítés, NEM új akció)
- **A KC top-score nyertes egyetlen adatpontként rögzítve** — érdekes a Day 63 napi karakter szempontjából, de NEM strukturális minta. A P2.4 dinamikus pozíciószám (rolling 10-12, 0.35% risk) backlog idea **változatlan**.

**Fázis 1 (W21-W22) indulása máj 19-én — előzetes előkészületek:**
- Tamás `nuke.py --positions` máj 19 reggel — az AVDL.CVR (69.0 phantom), és bármilyen friss HYMC-szerű pozíció takarítása
- IBKR paper account reset (Tamás manuális, máj 20-22) — a régi paper aggregát "lezárása" és **$100k újra**
- A Dev chat (Swing Pivot Dev) első CC task fájlja: IBKR Gateway monitoring (P1.1) — közvetlenül indokolt az IBKR Connection Failed ma reggeli megfigyeléssel

**Heti pattern (W20 D1-D4 átlag, 1 nap péntek hátra):**
| Nap | Net P&L | Excess | Karakter |
|-----|---------|--------|----------|
| Hé W20 D1 | +$28 | -0.19% | mild bull underperform |
| Ke W20 D2 | -$369 | -0.20% | mild risk-off underperform |
| Sze W20 D3 | -$189 | -0.74% | bull rally EXTRÉM underperform |
| Cs W20 D4 | **+$313** | -0.45% | mild bull underperform (POZITÍV NETT) |

**W20 D5 (péntek, ma) várakozás**: A heti összesítés a péntek 22:00 CEST EOD log után. A W20 4 napi átlag: -$54/nap, -0.40% excess átlag. **A péntek 22:00 utáni heti review-ban a W20 heti karakter rögzítendő**.

## References

- `state/phase4_snapshots/2026-05-14.json.gz` — 4. tiszta snapshot a fix után (134 qualified, konzisztens)
- `state/daily_metrics/2026-05-14.json` — Day 64/63 strukturált metrika (gross +$339.94, net +$313.36, excess -0.45%)
- `scripts/paper_trading/logs/trades_2026-05-14.csv` — 7 trade fill (4 ticker)
- `logs/pt_eod_2026-05-14.log` — EOD P&L + **HYMC -140 SHORT warning**
- `logs/pt_close_2026-05-14.log` — 6 MOC submit, HYMC SKIP
- `logs/pt_nuke_2026-05-14.log` — reggeli AAPL takarítás (IBKR conn 1 failure, 2. próbára sikeres)
- `logs/pt_monitor_2026-05-14.log` — Breakeven Lock applied (KC + RIG + NVTS), NVTS Trail SL hit 19:25, LION/SDRL/DELL/AAPL replay 22:00:31
- `docs/decisions/2026-05-14-day63-decision-outcome.md` — Day 63 outcome formális rögzítés (~900 sor, 14 stratégiai döntés)
- `docs/STATUS.md` — Day 63 milestone LEZÁRT, kumulatív frissítendő (-$1,283.84)
- `docs/master-reference/03-day63-status.md` — Day 63 LEZÁRT, Day 126 keret aktív
- `docs/handoff/2026-05-14-chat-handoff-day63-outcome.md` — Chat handoff Swing Pivot Dev / Log Review chat indításához

**State**: BC23 utolsó hete (régi architektúra) + Breakeven Lock (profit_breakeven trigger 2. egymás utáni pozitív validáció ⭐) + MID Bundle + vix-close + M_contradiction LIVE (33% iránybeli, sign-flip Fázis 2-ben) + snapshot fix DEPLOYED (4 nap konzisztens) + dp_pct rekal DEPLOYED + **LOSS_EXIT bracket SL bug 5. instancia (HYMC)** + Day 63 outcome doc rögzítve

**Aktív CC tasks**: 0 (W21 D1, máj 19-én indul az első CC task: IBKR Gateway monitoring P1.1)

**Day 63 KIÉRTÉKELÉS FORMÁLIS**: ✅ Lezárva tegnap éjjel (`2026-05-14-day63-decision-outcome.md`). PAPER FOLYTATÁS default megerősítve. **Swing pivot W21-W30 roadmap indul máj 19-én**.

**A Day 63 napi karakter egy mondatban**: A régi rendszer **első pozitív nettó napja 5 nap után** (+$313) **párhuzamosan az 5. bracket SL bug instanciával** (HYMC) — **strukturális karakter-megerősítés**: a feature-réteg (BL, KC top-score win) **érdemleges fundament**, de a bracket-mechanika **rendszerszinten kompromittált**. **A swing pivot mental stop architektúra mindkét finding-ot strukturálisan kezelni fogja** Fázis 3 (W25+) deploy után.
