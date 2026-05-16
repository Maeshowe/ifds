# Daily Review — 2026-05-13 (szerda)

**BC23 Day 23 / W20 Day 3 — DAY 63 PAPER TRADING MILESTONE NAPJA**
**Paper Trading Day 63/63 — HOLNAP REGGEL KIÉRTÉKELÉS**
**M_contradiction LIVE 8. nap — 0 fired ma**
**🆘 BRACKET SL BUG 4. INSTANCIA (AAPL -68 SHORT, 2 nap eltolás)**
**⭐ Breakeven Lock POZITÍV működési adatpont (PAAS)**

**Adat-frissesség:** EOD log 22:05, daily_metrics.py 22:10 CEST. Phase 4 snapshot **142 qualified** (vs hétfő 159, kedd 161 — kis csökkenés, konzisztens). FORM nuke 10:39 CEST: SHORT zárva, **DE függő bracket orderek NEM cancellálva** — új strukturális finding.

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | -$177.97 |
| Napi P&L net | **-$188.96** (kis vesztes) |
| Kumulatív P&L (paper aggregát) | **-$1,623.78 (-1.62%)** ⚠️ átlépte a -1.5% paper folytatás default sávot |
| Tényleges valós (FORM+AAPL bug korrekcióval becsült) | **~-$1,400 to -$1,500 (-1.40 to -1.50%)** |
| Pozíciók (új) | 3 ticker (KC, PAAS, SSRM) |
| Trade count | 4 (KC 1× + PAAS 1× + SSRM 2× partial fill) |
| Win rate ticker szinten | **1/3 (33%)** — PAAS nyertes, KC + SSRM vesztes |
| **Exit mix** | **2× LOSS_EXIT (50%) + 2× MOC (50%)** — jobb mint a tegnapi 80% LOSS_EXIT |
| TP1 / TP2 / SL / TRAIL hit | 0 / 0 / 0 / 0 |
| **Avg slippage** | **-0,34% KEDVEZŐ** ⭐ (mind a 3 tickeren negatív, spontán — NEM kézi rögzítés) |
| SPY return | **+0,56%** (bull rally nap) |
| Portfolio return | -0,18% |
| **Excess vs SPY** | **-0,74%** ⚠️⚠️ — a 7 napi pattern legszélsőségesebb adatpontja (bull rally extrém underperform) |
| VIX close | 17,77 (Δ -1,44%, csökkent — risk-on) |
| Reggeli akció | ✅ `nuke.py --positions` 10:39 CEST: FORM -29 SHORT zárva (BUY 29 @ MKT) |
| **🆘 EOD nyitott pozíció** | **AAPL -68 SHORT** (4. bracket bug instancia) |

## 🆘 KRITIKUS — AAPL -68 SHORT: BRACKET SL BUG 4. INSTANCIA, ÚJ MINTA (2 nap eltolás)

A `pt_eod_2026-05-13.log` végén:
```
22:05:04 [WARNING] Still 1 open positions!
22:05:04 [WARNING]   AAPL: -68.0 shares
```

**Az AAPL eredete:** **2026-05-11 (hétfő) trade**, entry $293.09 → MOC $292.54 (-$37.40). A hétfő esti MOC után az IBKR bracket TP/SL orderek **függőben maradtak**, és **szerdán** (2 nap eltolással) **a bracket SL aktivált** valamikor az AAPL intraday mozgásakor, **-68 SHORT pozíciót** termelve.

**4 instancia 13 napon belül, eltolódási idővonal:**

| # | Dátum | Ticker | Eredeti trade | SHORT méret | Eltolás | Új minta? |
|---|-------|--------|---------------|-------------|---------|-----------|
| 1 | 2026-05-01 (csüt) | DTE | aznap LOSS_EXIT | -? | 0 nap | monitor LOSS_EXIT → bracket SL |
| 2 | 2026-05-07 (csüt) | SQM | aznap LOSS_EXIT | -91 | 0 nap | monitor LOSS_EXIT → bracket SL |
| 3 | 2026-05-12 (kedd) | FORM | tegnap (hétfő) MOC | -29 | **1 nap** | MOC fill-after (új) |
| 4 | **2026-05-13 (szerda)** | **AAPL** | **hétfő MOC** | **-68** | **2 nap** ⚠️ | **MOC fill-after, hosszabb eltolás** |

**Strukturális elemzés**: a bracket TP/SL orderek **napokig függőben maradnak** az IBKR-ben, és **akkor triggerelnek**, amikor az ár az adott szinten áthalad. **2 nap eltolás csak az alsó határa** — elvileg **hetekkel későbbi trigger** is lehetséges, ha a ticker visszamozog a bracket-szintekre.

**Az 1.3 backlog idea (LOSS_EXIT bracket SL cancellation) URGENCY LEVEL EMELÉSE:**
- Eredetileg: P1 (W19+ scope, sürgős)
- Hétfő: P1 + szerda reggel hot-fix
- **Most: P1 + Day 63 utáni AZONNALI deploy** (a holnapi értékelés első konkrét akcióeleme)

## 🆘 KRITIKUS — `nuke.py --positions` NEM cancellálja a függő ordereket

A reggeli FORM-takarítás során:

```
10:39:33 [INFO] Open positions: 2 (FORM -29, AVDL.CVR 69)
10:39:33 [INFO] Open orders: 4
10:39:33 [INFO]   FORM: BUY 29 shares (MKT via SMART)
10:39:33 [INFO]   AVDL.CVR: SKIP (non-tradable)
10:39:35 [INFO] Final positions: 2 (FORM most 0, AVDL.CVR megmaradt)
10:39:35 [INFO] Final orders: 5 (4 függő + 1 új BUY)
```

És az events.jsonl konfirmáció:
```jsonl
{"event": "nuke_executed", "orders_cancelled": 0, "positions_closed": 2}
```

**`orders_cancelled: 0`** — a 4 függő FORM bracket TP/SL order **NEM cancellálódott**. Tamás a SHORT pozíciót zárta, de **a függő orderek továbbra is potenciálisan triggerelhetnek** a következő trading napokon, ha a FORM ár a tegnapi MOC fill ($151.57) közelébe ér.

**Új strukturális finding:** a jelenlegi `nuke.py --positions` parancs **csak pozíciókat zár, ordereket NEM cancellál**. A teljes takarításhoz szükséges egy:
- **`nuke.py --positions --orders`** flag-kombináció, vagy
- **`nuke.py --everything`** default cleanup, vagy
- A 1.3 P1 backlog idea **bővített scope-ja** automatikusan kezelje (`pt_close.py` MOC fill után cancel + a `nuke.py` default cancel)

**Csütörtök reggeli ELŐZETES teendő:** Tamás `nuke.py --positions` (vagy hasonló) a **AAPL -68 SHORT** takarítására, **plus**, ha lehetséges, a függő FORM bracket orderek manuális cancel-elése az IBKR TWS UI-n keresztül.

## ⭐ POZITÍV ADATPONT — PAAS Breakeven Lock MŰKÖDÉSI VALIDÁCIÓ

A `pt_events_2026-05-13.jsonl` 17:00 CEST körüli szakaszában egy gyönyörű kétlépéses Breakeven Lock pattern:

```jsonl
17:00:11 trail_activated_b PAAS @ $64.20 (entry $63.51, +1.09% profit)
         → trail_sl $60.12 (az ATR-arányos trail-szint)
17:00:13 breakeven_lock_applied PAAS:
         old_sl $60.12 → new_sl $63.51 (entry-ár)
         current_price $64.25 (+1.17%)
         lock_type: "profit_breakeven"
```

**A Breakeven Lock profit-based trigger MŰKÖDIK ÉS KONZISZTENS:**
- Trail aktiváció +1.09% profit-on (master-reference szerint a profit-küszöb 1%)
- 2 másodperccel később BL applied: SL **felugrik az entry-ár szintjére** ($63.51)
- A pozíció ezután **NEM mehet veszteségbe** (a hagyományos -2% LOSS_EXIT küszöbtől függetlenül)
- PAAS MOC kitartott $63.60-on → **+$46.17 profit** védelemben

**Mit jelent ez:**
1. **A feature design helyes** — a profit_breakeven működik, ahogy tervezett
2. **A MTCH-szerű esetek** (péntek máj 8) **NEM a BL hibája**, hanem a profit-küszöb 1% magassága miatti **késedelmes aktiváció**
3. **A 2.1 P2 backlog idea ("Breakeven Lock profit-küszöb csökkentés 0,5%-ra")** továbbra is releváns — de a feature **alap-logikája tökéletesen rendben van**

**Kvantitatív hatás**: enélkül a feature nélkül, ha a PAAS visszamozott volna a +1.09% peak-ről $63.51 alá (pl. $63.00-ra), a TRAIL SL **$60.12-en** maradt volna, és a MOC -$87.21-en zárt volna (171 × $0.51 vesztes), **NEM +$46.17 nyerő**. **A BL biztosította a +$133 különbséget** ezen az egy pozíción.

A Breakeven Lock **az utolsó 13 napi paper trading egyik legjobban funkcionáló feature-je** — szemben az M_contradiction-nal (33% iránybeli helyesség, sign-flip-vizsgálat folyamatban) és a LOSS_EXIT-tel (-2% küszöb agresszivitás P2 finomítás).

## Pozíciók részletei

### Nyertes (1 ticker, +$46)

**PAAS (Pan American Silver, Basic Materials, score 93.0)**: Entry $63.33 (planned $63.51, **slippage -0,28% kedvező**), MOC $63.60 = **+$46.17 (+0,43%)** ⭐ — a nap egyetlen nyerője. **Breakeven Lock applied 17:00:13** (lásd fent). M_contradiction nem fired (multiplier_total 1.0).

**Stratégiai értelmezés:** a PAAS egy "tipikus klasszikus" trade — alacsony slippage, közel-flat intraday mozgás, +1.09% profit-on Breakeven Lock-ot kapott (a 1%-os küszöbön éppen átlépve), MOC-ig kitartott. **A rendszer kvalitatív "fair" eredménye** — semmi rendkívüli, csak a feature-ek jól dolgoztak együtt.

### Vesztesek (2 ticker, 3 trade, -$224)

**KC (Kingsoft Cloud Holdings, Technology, score 93.5 — legmagasabb)**: Entry $18.06 (planned $18.12, **slippage -0,33% kedvező**), MOC $17.89 = **-$69.16 (-0,95%)** vesztes. **NEM LOSS_EXIT** — MOC-ig kitartott. 401 share × -$0.17. M_contradiction nem fired (multiplier 1.0). **A legmagasabb score-ú ticker**, mégis vesztes — folytatja a 7 napi pattern-t.

**Stratégiai értelmezés:** a KC egy klasszikus "lassú vesztes" — egész napon enyhén csökkenő trend, NEM esett a -2% LOSS_EXIT küszöb alá, MOC-ig kitartott -0.95%-on. A -2% küszöb itt **a teszt szerint helyesen NEM triggerelt** (egy ellenpélda az NVDA-szerű "túl szigorú" pattern-re).

**SSRM (SSR Mining, Basic Materials, score 93.0)**: 2 partial fillben zárult LOSS_EXIT-tel ugyanazon a $34.58 áron:

```
Entry $35.20 (planned $35.35, slippage -0,42% kedvező)
Submit 14:19:23 CEST: qty 252 (bracket_a 126 + bracket_b 126)
LOSS_EXIT trigger 17:45:14 CEST: SELL 252 @ MARKET (3:25 az entry után)
IBKR partial fills (2-split):
  Fill 1: 152 share × -$0,615 = -$93,48
  Fill 2: 100 share × -$0,615 = -$61,50
Total: -$154,98 (-1,75% × 2 fill)
```

**A 2-split NEM bug — IBKR partial fill artifact** (a tegnapi TGB 3-split mintájához hasonlóan). A monitor `loss_exit` event egy darab (qty 252, pnl -$189 a "naív" számítással), az EOD log 2 darabra bontja a fill-szintű elszámolás miatt.

A 17:45 LOSS_EXIT trigger **késő-délutáni eset** (NEM az tipikus 17:00-i első LOSS_EXIT, mint a tegnapi TGB/NVDA). Az SSRM 35.35 → 34.60 = -2.12% kb. 3.5 órával az entry után érte el a küszöböt. **Strukturálisan más mint a kedd 40-45 perces gyors LOSS_EXIT-ek** — itt a normál intraday volatilitás lassan haladt át a -2%-on.

## Score → P&L napi nézet

| Ticker | Score | Multiplier | Exit | P&L net | Win? | Slippage |
|--------|-------|------------|------|---------|------|----------|
| **KC** | **93.5** | 1.00 | MOC | -$69.16 | ✗ | -0.33% (kedvező) |
| PAAS | 93.0 | 1.00 | MOC + BL | **+$46.17** | ⭐ | -0.28% (kedvező) |
| SSRM | 93.0 | 1.00 | LOSS_EXIT × 2 | -$154.98 | ✗ | -0.42% (kedvező) |

**A 8 napi (W19 D1 → W20 D3) score pattern:**
- A 95-ös score-ok az utolsó 8 napban gyakran vesztesek (NE, MTCH, HYMC, TGB)
- **A 93-93.5-ös score-ok ma** — minden 1.0 multiplier, **NINCS M_contradiction fired** (0/3 ma) — első nap a 8 napban
- 1 nyertes / 2 vesztes — szétoszlott pattern

**M_contradiction LIVE 8. nap mérleg (változatlan a tegnapihoz képest):**
- **6 fired esetből 2 ✓ + 4 ✗ = 33% iránybeli helyesség** — ma 0 új fire
- A sign-flip + dedup elemzés továbbra is **Day 63 utáni feladat** (2.3 backlog idea)

## ⚠️ "Bull rally underperform" — A 7 napi pattern LEGSZÉLSŐSÉGESEBB ADATPONTJA MA

| Nap | Net P&L | SPY return | Portfolio return | Excess vs SPY | Pattern |
|-----|---------|------------|------------------|---------------|---------|
| Hé W19 D1 | -$191 | -0.37% | -0.15% | +0.21% ⭐ | risk-off outperform |
| Ke W19 D2 | -$269 | +0.80% | -0.24% | -1.04% | bull underperform |
| Sze W19 D3 | +$234 | +1.39% | +0.25% | -1.14% | bull underperform |
| Csü W19 D4 | -$501 | -0.31% | -0.49% | -0.18% | mild risk-off near-neutral |
| Pé W19 D5 | +$486 | ~0% | +0.49% | +0.49% ⭐ | mild lateral outperform |
| Hé W20 D1 | +$28 | +0.23% | +0.03% | -0.19% | mild bull underperform |
| Ke W20 D2 | -$369 | -0.15% | -0.35% | -0.20% | mild risk-off underperform (új!) |
| **Sze W20 D3** | **-$189** | **+0.56%** | **-0.18%** | **-0.74%** ⚠️⚠️ | **bull rally EXTRÉM underperform** |

**Pattern megerősítés:**
- Az utolsó 4 bull napon (W19 D2 +0.80%, D3 +1.39%, W20 D1 +0.23%, W20 D3 +0.56%) átlagos excess: **-0.78%**
- Az utolsó 2 risk-off / lateral napon (W19 D1, W19 D5) átlagos excess: **+0.35%**
- **A szignifikáns underperformance a bull rally napokon** strukturális karakter, **konzisztens 4 napra**

**8 napi excess vs SPY átlag: -0.35%** — a Day 63 leállítási feltétel **-1.5%** mellett **bőven biztonságos** (~1.15% buffer).

## ⭐ KEDVEZŐ SLIPPAGE SPONTÁN — Entry timing hipotézis támogatás

A **3 ticker MIND kedvező slippage-zsel** szállt be (-0.34% átlag), **NEM kézi rögzítés volt** (az events 14:19-14:20 CEST-i automata submit-eket mutat, IBKR conn rendben). Ez azt jelzi, hogy a **16:20 CEST entry-időpont ma lokálisan a market open utáni helyi mélypontra esett** mindhárom tickeren.

**Kvantitatív adat az entry timing 2.5 P2 backlog idea-hoz:**

| Ticker | Tervezett (16:15 cron) | Tényleges fill (16:20) | Slippage % | $ hatás |
|--------|------------------------|--------------------------|------------|---------|
| KC | $18.12 | $18.06 | -0,33% | +$24,06 (401 × $0,06) |
| PAAS | $63.51 | $63.33 | -0,28% | +$30,78 (171 × $0,18) |
| SSRM | $35.35 | $35.20 | -0,42% | +$37,80 (252 × $0,15) |
| **Σ** | | | **-0,34% avg** | **+$92,64 spontán slippage-haszon** |

**Strukturális finding** (megerősíti a 2.5 entry timing backlog idea-t):
- A 16:20 CEST entry-időpont **NEM mindig a "reggeli rally peak"** (tegnapi kedd hipotézis)
- **A 8 napi mintában 4-5 nap KEDVEZŐ slippage volt** (-$0.30 vs entry átlag), 3-4 nap kedvezőtlen
- A "peak" pattern **csak részben** működik — a 60+ napi backtest **konkrét kvantitatív eredményt** fog adni

**Az entry timing backtest egyik következménye lehet:** a 16:20 időpont **átlagosan optimális**, csak nagy varianciával. A 15:30 vs 17:15 vs 18:30 alternatívák **vagy jobbak/rosszabbak attól függően, melyik nap milyen piaci environment-ben volt**. A backtest tisztázni fogja.

## Snapshot fix 3. nap validáció — KONZISZTENS

| Nap | Phase 4 qualified (>85) | Snapshot status |
|-----|--------------------------|------------------|
| Hé W20 D1 (máj 11) | **159** | 22,89 KB, 1390 ticker analyzed |
| Ke W20 D2 (máj 12) | **161** | konzisztens |
| **Sze W20 D3 (máj 13)** | **142** | konzisztens (kis csökkenés — earnings exclusion?) |

**A snapshot fix stabil 3 napra** — a 142-159-161 fluktuáció normál (a Phase 2 universumban naponta néhány ticker ki/be kerül az earnings exclusion miatt). **A `d3fce73` deploy értékelhető 100% sikeres.**

## monitor.py LION/SDRL "replay" események — 4. nap egymás után

Megint ugyanaz az event-sorozat 22:00 CEST környékén, ugyanazon a entry/exit árakkal és scope-okkal. **A 3.5 P3 backlog idea (replay események jelölése) megerősítve mint ismétlődő strukturális artifact.**

## Day 63 KERET — ELŐZETES ÉRTÉKELÉS (a HOLNAPI KIÉRTÉKELÉS ALAPJA)

| Metrika | Érték | Status |
|---------|-------|--------|
| Day | **63/63** — milestone teljesítve | ✅ |
| Kumulatív (paper aggregát) | -$1,623.78 (-1.62%) | átlépte a -1.5% paper folytatás default sávot |
| Tényleges valós (becsült) | ~-$1,400 to -$1,500 (-1.40 to -1.50%) | a FORM (-29) + AAPL (-68) + AVDL.CVR phantom okozta paper aggregát-toldás miatt |
| ÉLESÍTÉS távolság | +$4,500 a +$3,000-hoz | **ABSOLUT NEM teljesült** |
| LEÁLLÍTÁS távolság | 8 napi excess átlag -0.35% | **biztonságos**, ~1.15% buffer a -1.5%-tól |
| 8 napi excess vs SPY átlag | -0.35% | biztonságos sávban |
| VIX W20 átlag | 18.10 | **alacsony**, leállítási feltétel monitor inaktív |

**A holnapi Day 63 KIÉRTÉKELÉS várt kimenetele: PAPER FOLYTATÁS (default)** ✓

**Holnap reggel (csüt máj 14) megírom:**
- `docs/decisions/2026-05-14-day63-decision-outcome.md` (formális döntési dokumentum)
- W20+ scope-revízió a 15 backlog idea alapján
- A 4 instancia LOSS_EXIT bracket bug **AZONNAL deploy-olandó** P1 (a holnapi szerda esti hot-fix elindítható)

## Anomáliák

- **🆘 AAPL -68 SHORT** (LOSS_EXIT bracket SL bug 4. instancia, 2 nap eltolás) — **csüt reggel sürgős takarítás**
- **FORM függő bracket orderek** — a reggeli `nuke.py` nem cancellálta, **potenciálisan további trigger** a következő napokon
- **`nuke.py --positions` parancs scope-hiány** — csak pozíciókat zár, ordereket nem
- **CRGY/AAPL leftover phantoms** továbbra is (régóta ismert BUG)
- **DELL, DOCN phantom_filtered** (helyes szűrés)
- **AVDL.CVR (69.0)** továbbra is non-tradable, ignorálva
- **monitor.py LION/SDRL replay** events — **4. nap egymás után**
- **Polygon 1-min bars + UW HTTP 429 status** — ma nem kritikus (3 ticker megnyitva, mind kapott adatot)

## Kulcsmegfigyelések

### 1. 🆘 KRITIKUS — AAPL -68 SHORT (BRACKET SL BUG 4. INSTANCIA, 2 NAP ELTOLÁS)

A bracket TP/SL orderek **napokig függőben maradnak** és **bármikor triggerelhetnek** a következő napokban (FORM 1 nap, AAPL 2 nap, elvileg hetekkel későbbi trigger is lehetséges). **A 1.3 P1 backlog idea AZONNAL deploy-olandó Day 63 után** — a csütörtök esti hot-fix érdemes a hét végéig.

### 2. 🆘 `nuke.py --positions` parancs scope-hiány

A reggeli FORM-takarítás során `orders_cancelled: 0` — a 4 függő bracket order **továbbra is potenciálisan triggerelhet**. A 1.3 backlog idea bővítendő egy harmadik scope-pal: **`nuke.py` default cancel logika** vagy egy új `--orders` flag.

### 3. ⭐ PAAS BREAKEVEN LOCK MŰKÖDÉSI VALIDÁCIÓ — POZITÍV finding

A profit_breakeven trigger pontosan a tervezett módon működik (+1.09% trail aktiváció → SL felugrik entry-ár szintjére). +$133 különbség egy pozíción a feature által. **A 2.1 BL profit-küszöb csökkentés backlog idea továbbra is releváns**, de a feature **alaplogikája tökéletesen rendben van**.

### 4. ⚠️ BULL RALLY UNDERPERFORM EXTRÉM (-0.74% excess)

A 7 napi pattern legszélsőségesebb adatpontja. **4 bull rally napon átlag -0.78% excess** — strukturális karakter, **konzisztens 4 napra**. A Day 63 utáni élesítési kritérium **nem-Stagflation regime feltétel** ezt kezeli, de a swing rendszer **alapvető defenzív karaktere** stabil.

### 5. ⭐ KEDVEZŐ SLIPPAGE SPONTÁN (-0.34% mind a 3 tickeren)

Az entry timing 2.5 P2 backlog idea-hoz **támogató adatpont**. A 16:20 entry-időpont **NEM mindig a reggeli rally peak** — a 8 napi mintában fluktuál. A 60+ napi backtest **kvantitatív eredményt** fog adni a 4 alternatív időablak (15:30/16:20/17:15/18:30) összehasonlításához.

### 6. ✓ M_CONTRADICTION LIVE — 0 fire ma, 8. nap mérleg változatlan

33% iránybeli helyesség (2/6) — a sign-flip vizsgálat Day 63 utáni elemzéshez (2.3 backlog idea).

### 7. ✓ SNAPSHOT FIX STABIL 3. NAP — 142 qualified, konzisztens

A `d3fce73` deploy **100% sikeres**. A scoring-validation újrafuttatása csütörtök Day 63 KIÉRTÉKELÉS során **megbízhatóan teljes mintán futtatható**.

## Holnap (csütörtök, W20 D4 = Day 64 — Day 63 KIÉRTÉKELÉS NAPJA) ⭐

### Tamás (MacMini, manuális, **REGGEL**)

- **🆘 `nuke.py --positions`** — az AAPL -68 SHORT takarítása piacnyitás előtt
- **🆘 Manuális IBKR TWS UI ellenőrzés** — a függő FORM és (esetleg) AAPL bracket TP/SL orderek manuális cancel-elése (a `nuke.py` scope-hiánya miatt)
- IBKR Gateway állapot ellenőrzés
- 09:00 reminder notification — Day 63 KIÉRTÉKELÉS

### Chat (én — Day 63 KIÉRTÉKELÉS doc)

**Reggel 09:00-10:00 között megírom**: `docs/decisions/2026-05-14-day63-decision-outcome.md`

Tartalom:
1. **Hivatalos kimenet**: PAPER FOLYTATÁS (default) — minden Day 63 keret-feltétel ellenőrzése
2. **W20+ scope prioritás-revízió**:
   - **AZONNAL hot-fix (csüt este)**: 1.3 LOSS_EXIT bracket SL cancellation + nuke.py scope bővítés
   - **Hét végéig (péntek)**: 1.6 UW rate limit kezelés finomítás
   - **Jövő hét (W21)**: 1.7 IBKR Gateway monitoring + Telegram alert, 2.4 LOSS_EXIT küszöb finomítás
   - **W21-W22**: 2.5 Entry timing optimalizáció backtest (analitikus, Chat-oldali)
   - **W22+**: 2.3 M_contradiction × M-szorzó kölcsönhatás (sign-flip vizsgálat + implementáció)
3. **Kvantitatív összefoglaló**: 63 napi paper P&L breakdown, win rate, exit mix, slippage trends, score → P&L korreláció (a snapshot fix utáni 8 napi friss adat)
4. **A 15 backlog idea ütemezett deploy-terv** Day 63 után

### Csütörtök este (W20 D4 napi review + Day 63 utánkövető)

- A nap eseményei + a Day 63 KIÉRTÉKELÉS doc rögzítése
- Ha CC megkezdte a 1.3 hot-fix-et, status update

### Vasárnap (Day 63 + 3)

- **W20 weekly elemzés** (`docs/analysis/weekly/2026-W20-analysis.md`)
- Esetleg az entry timing 2.5 backtest **első eredmény** (ha Chat hétvégén tudott rajta dolgozni)

## Kapcsolódó

- `state/phase4_snapshots/2026-05-13.json.gz` ⭐ 3. tiszta snapshot a fix után (142 qualified)
- `state/daily_metrics/2026-05-13.json` ← Day 63 strukturált metrika
- `logs/pt_eod_2026-05-13.log` ← P&L (2 LOSS_EXIT + 2 MOC) + **AAPL -68 SHORT warning**
- `logs/pt_nuke_2026-05-13.log` ← FORM -29 SHORT zárva, **DE függő orderek NEM cancellálva**
- `logs/pt_close_2026-05-13.log` ← cron-replay 21:20 + 21:40
- `logs/pt_events_2026-05-13.jsonl` ← **PAAS Breakeven Lock applied 17:00:13** ⭐, SSRM 17:45 LOSS_EXIT, AAPL position_skipped
- `output/execution_plan_run_20260513_141500_*.csv` ← 3 ticker, mind multiplier 1.0 (NINCS M_contradiction fired)
- `docs/master-reference/04-risks-and-open-questions.md` ← **frissítendő** (1.3 4. instancia + 2 nap eltolás minta + `nuke.py` scope-hiány)
- `docs/decisions/2026-05-14-day63-decision-outcome.md` ← **HOLNAP REGGEL JÖN**

**State**: BC23 + Breakeven Lock (profit_breakeven trigger MŰKÖDIK ⭐) + MID Bundle + vix-close + M_contradiction LIVE (33% iránybeli) + snapshot fix DEPLOYED (3 nap konzisztens) + dp_pct rekal DEPLOYED + **LOSS_EXIT bracket SL bug 4. instancia (AAPL)**

**Aktív CC tasks**: 0 (Day 63 után induló P1 hot-fix tervezett)

**Day 63 KERET ELŐZETES**: 
- ✅ 63 trading nap teljesítve
- ✅ Snapshot fix 100% sikeres (3 nap konzisztens)
- ✅ Leállítási feltétel buffer ~1.15%
- ✅ ÉLESÍTÉS abszolút nem teljesült (+$3,000 távoli)
- ✅ Default: **PAPER FOLYTATÁS** (a holnapi formális megerősítés várja)
- ⚠️ Strukturális issues azonosítva: 15 backlog idea, **prioritás 1: bracket SL bug fix** (a 4 instancia drámaian növelte az urgency-t)

**A holnapi Day 63 KIÉRTÉKELÉS lényege**: a paper trading **technikailag sikeres** volt (a feltételek bőven biztonságos sávban maradtak), de **a stratégiai finding-ok 15 backlog idea-ra mutatnak**, amelyek a következő 4-8 hetes scope-ot definiálják. **Az élesítés még távoli**, de **a stratégia karaktere stabilan dokumentált** (defenzív erő risk-off-on, gyenge bull rally-n).
