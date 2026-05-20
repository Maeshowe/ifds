# 04 — Aktív kockázatok és nyitott kérdések

**Utoljára frissítve**: 2026-05-19 (Day 2 — Task #T komplex Telegram audit + Task #D Phase 1-3 heartbeat + Task #E State/IBKR reconciliation ✅ DONE, commit `5dfab55`)
**Cél**: a swing pivot W21+ aktív backlog tételeit és a strukturális finding-okat tartalmazza, prioritás-sorrendben. **Ezt használd, ha gyorsan akarsz tudni mi a legfontosabb most**.

> **Korszakváltás (2026-05-14)**: a Day 63 milestone outcome alapján a régi 15-elemű backlog **drasztikusan átalakult**: **6 dropolva** (a swing pivot strukturálisan eliminálja), **4 átalakítva**, **6 új aktív**. A swing pivot 3 fázisú reset roadmap a `docs/decisions/2026-05-14-day63-decision-outcome.md` 6. fejezetében.

---

## 0. ⚠️ P0 — KRITIKUS, AZONNALI AKCIÓ (Day 1 GO-LIVE review)

**Időpont**: 2026-05-18 napi review során azonosítva (Log Review chat). Mindhárom **Day 2 (kedd, 2026-05-19) reggel** kezelendő a Dev chat által, mielőtt a 14:30 CEST cron újra futna.

**Forrás**: [`docs/review/2026-05-18-daily-review.md`](../review/2026-05-18-daily-review.md) — 6. szakasz

### 0.1 ✅ A régi `pt_monitor.py` 5-perces logika "futás"-a (RESOLVED 2026-05-20)

**Státusz**: ✅ RESOLVED — root cause **NEM** legacy 5-perces cron, hanem **pytest pre-flight FileHandler binding pollution**. Fix: `lib/log_setup.py::_resolve_log_dir()` redirect pytest alatt tmp dir-be. Commit: lásd `docs/tasks/2026-05-19-pt-monitor-replay-diagnosis.md` §6.

**Eredeti megfigyelés**: A `pt_monitor_2026-05-18.log` szerint a régi 5-perces monitor logic **3 időpontban** "futott" Day 1-en (12:06:58, 14:25:09, 14:25:52). A `pt_monitor_2026-05-19.log` Day 2-n megismételte ugyanezt (16:37:19). Mindenhol LION/SDRL "Trail SL hit"/"LOSS_EXIT Scenario B"/"IBKR cancelOrder" üzenetek — DE a LION/SDRL NEM aktív pozíció.

**Diagnózis (2026-05-20, CC)**: a `scripts/paper_trading/lib/log_setup.py::setup_pt_logger("monitor")` modul-import időben bind-ol egy `FileHandler`-t a process-wide `logging.getLogger("monitor")`-hoz, ami a **produkciós** `logs/pt_monitor_YYYY-MM-DD.log`-ra ír. A `tests/test_pt_monitor*.py` 28 teszt-je (LION/SDRL state mockokkal) `logger.info()` / `logger.warning()` hívásokat tartalmaz — ezek a hívások a `deploy_daily.sh` pytest pre-flight ablakában a produkciós logfile-ra szivárognak. A 14:25 (5/18) és 16:37 (5/19) bélyegek pontosan egybeesnek a Mac Mini-n manuálisan futtatott `deploy_daily.sh --phases 1-3` időpontokkal — bizonyítva más logfile-ok (pl. `state/phase13_ctx.json.gz`) mtime-jával.

**A legacy 5-min code path élesben halott**: `submit_orders.py` 2026-05-15 óta NEM ír `scripts/paper_trading/logs/monitor_state_YYYY-MM-DD.json`-t (swing pivot átállás). Még ha valaki manuálisan `python pt_monitor.py`-t futtatna `--mode=scenario_a` default-tal, a `load_state(today_str)` üres dict-et adna vissza → early `return`. **Élesben semmilyen pt_monitor 5-perces logika nem futott** — csak a pytest-binding okozott logfile pollution-t.

**Fix**:
- `lib/log_setup.py::_resolve_log_dir(log_dir)` új helper: ha `PYTEST_CURRENT_TEST` set ÉS `log_dir == "logs"` (implicit default) → redirect `$IFDS_PT_LOG_DIR` vagy `$TMPDIR/ifds_pt_logs_test/`-re. Produkciós cron (PYTEST_CURRENT_TEST not set) bit-for-bit változatlan.
- `tests/test_log_setup_isolation.py` (5 új regressziós teszt) verifikálja az izolációt mind a 10+ PT script-re.

**Test deltas**: 1740 → 1745 passing.

**Mérséklő tényező visszaigazolva**: ahogy a Day 1 review feltételezte, **nincs live impact** — a "SELL parancsok" puszta log-szöveg-pollution, nem IBKR API hívás. A test fixture-ök `MagicMock(IB)`-et használtak.

### 0.2 ⚠️ `pt_submit` előzetes kísérlet 14:34:13 CEST + Error 10349 TIF (P0)

**Mi**: A `pt_submit_2026-05-18.log` szerint **két submit attempt** futott:
- **14:34:13 CEST** — 56 perccel a 15:30 entry előtt. **NEM dokumentált a briefingben**. MASI sikerült, **LBRT és EC `status=Cancelled`** Error 10349 ("Order TIF was set to DAY based on order preset")
- **15:30:02 CEST** — "Skipping LBRT/MASI/EC: already has position or swing state" — vagyis a 14:34 és 15:30 között **mindhárom megnyílt az IBKR-ben**, de **nem világos hogyan** (a 14:34 cancel és a 15:30 skipping között valami történt — silent retry? IBKR async fill? manuális resubmit?)

**Strukturális probléma**: 
1. **Honnan a 14:34-es előzetes submit?** Lehetséges források: (A) `cron_intraday_20260518_143000.log` magában tartalmaz egy submit phase-t, (B) második cron entry crontab-ban, (C) Tamás manuálisan
2. **Error 10349 TIF "DAY" preset hiba**: a 15:30 CEST submit (= 9:30 ET piacnyitás) után a NYSE csak ~6 órát tart nyitva. **A "DAY" TIF preset alapérték NEM kompatibilis** a swing pivot 15:30 entry-időpontjával.

**Akció**: Dev chat vizsgálja meg:
1. A `submit_orders.py` Error 10349-handling és TIF konfigurációt (`config.py` vagy `defaults.py`-ban)
2. A `cron_intraday_*.log`-ot a 14:30-as run-ra (19 KB) — tartalmaz-e submit phase-t?
3. A 14:34-15:30 közötti **silent retry** mechanika dokumentálását vagy eltávolítását (ha nem szándékos)

### 0.3 ⚠️ Phase 2 universe-building TIMEOUT (P1)

**Mi**: A `cron_20260518_142505.log` és `cron_20260518_142549.log` **mindkettő `KeyboardInterrupt`-tal halt el Phase 2-ben**:
- 14:25:05 cron: `_exclude_earnings` futures.as_completed timeout
- 14:25:49 cron: `_exclude_sec_filings` rate-limit sleep timeout

Mindkettő Phase 0-1-et sikeresen lefutott (1711 pytest passed, BMI=52,7% YELLOW LONG), **de Phase 2 universe-building közben halt el** parent-cron timeout miatt. A sikeres futás a `cron_intraday_20260518_143000.log`-ban (19 KB) van.

**Strukturális probléma**: A Phase 2 universe-building (earnings exclusion + SEC EDGAR 10-Q lookup) **lassú** — a SEC EDGAR rate-limit sleep + futures.as_completed várás összesen **> 60s** lehet, ami a parent-cron timeout-ját túllépi.

**Akció**: Dev chat vagy:
1. Emelje a Phase 2 timeout-ot a crontab parent-job-ban
2. Optimalizálja a `sec_edgar.py:_http_get_json` rate-limit logikát
3. Csökkentse a Phase 2 work futures concurrency-jét

---

## 1. P1 — Sürgős, Fázis 1 (W21-W22) deploy

### 1.1 IBKR Gateway monitoring + Telegram alert ⭐ OPERATIONAL RISK

**Mi**: 2026-05-11 16:20 CEST — az IBKR Gateway elérhetetlen volt (timeout × 3 retry), a `submit_orders.py` failelt. Tamás 55 perccel később (17:15 CEST) vette észre, kézi rögzítés.

**Miért P1**:
- A jelenlegi rendszer **nem riasztja Tamást**, ha az IBKR Gateway leáll a 16:20-i submit-időpontban.
- Egy másik IBKR-akadás esetén a rendszer **csendben hibázhat** — Tamás csak EOD-időpontban (22:00 körül) látja.
- **Swing-architektúrán is releváns**: a 15:30 CEST entry-időnél is ugyanaz a kockázat.

**Megoldás**: a `submit_orders.py`-be IBKR connection failure detection + Telegram bot értesítés (meglévő Telegram bot infrastruktúra).

**Effort**: ~1 óra CC + 2-3 unit teszt

**Owner**: CC (W21+ azonnali deploy)

**Státusz**: ✅ DONE 2026-05-16 (CC Ülés A, Fázis 1 W21 close). Telegram WARNING anti-pattern fix + heartbeat (Fix C) deploy-olva. A 2026-05-11-i csendes failure root cause-a azonosítva (H1: `_send_telegram_alert` `except Exception: pass` minta), 2026-05-18 sikeres pre-market verifikáció.

**Forrás**: [`docs/review/2026-05-11-daily-review.md`](../review/2026-05-11-daily-review.md)

**Implementáció**: [`docs/tasks/2026-05-15-ibkr-gateway-monitoring.md`](../tasks/2026-05-15-ibkr-gateway-monitoring.md)

### 1.2 10-Q SEC Filing Exclusion + 10 napi earnings exclusion bővítés ⭐ SWING-EN KRITIKUSABB

**Mi**: AGNC 2026-05-04 — 10-Q SEC filing event 17:21 CEST, **NEM** earnings release, így a 7 napos earnings exclusion nem zárta ki. Eredmény: -$380 6-split LOSS_EXIT.

**Miért P1 a swing-en (REWORKED)**:
- A 7 napos earnings exclusion már **nem elégséges** swing horizonton (5 napi hold)
- **Új keret**: 10 napi earnings exclusion (hold × 2 buffer) + 10-Q SEC filing exclusion
- A jelenlegi earnings-szűrő nem fedi le a 10-Q / 10-K SEC filing event-eket

**Megoldás**:
1. `defaults.py`: `earnings_exclusion_days: 7 → 10`
2. SEC EDGAR API integráció — 10-Q és 10-K filing dátumok lekérdezése
3. Phase 2 universe-ből kizárás 10 napi előretekintéssel

**Effort**: ~2-3 óra CC

**Owner**: CC (W21+ azonnali deploy)

**Státusz**: ✅ DONE 2026-05-16 (CC Ülés B, Fázis 1 W21 close). `earnings_exclusion_days: 7 → 10` config change deploy-olva, SEC EDGAR API integráció 1611-ticker live smoke 100% success, 0 HTTP 429. Tolerancia ±10 nap, failure mode (C) cache → (A) fail-open.

**Implementáció**: [`docs/tasks/2026-05-15-earnings-exclusion-7to10.md`](../tasks/2026-05-15-earnings-exclusion-7to10.md), [`docs/tasks/2026-05-15-sec-10q-exclusion.md`](../tasks/2026-05-15-sec-10q-exclusion.md)

---

## 2. P2 — Fázis 2 analitikus + design (W23-W24)

### 2.1 Entry timing optimalizáció backtest ⭐ A SWING PIVOT KVANTITATÍV MEGALAPOZÁSA

**Mi**: A jelenlegi 16:20 CEST entry-idő strukturálisan a reggeli rally peak-jére esik. A swing pivot 15:30 CEST entry-t javasol (market open). **Kvantitatív validáció szükséges**.

**Megoldás (analitikus, NEM kód deploy)**:

Backtest a 60+ napi adaton 4 hipotetikus entry-időablakkal:
- 15:30 CEST (market open = 09:30 ET) — **az új javasolt**
- 16:20 CEST (jelenlegi = 10:20 ET)
- 17:15 CEST (= 11:15 ET, reggeli profit-taking utáni)
- 18:30 CEST (= 12:30 ET, lunchtime drift)

Minden ticker × minden hipotetikus entry-időpontra:
1. Visszaszámolni a hipotetikus entry-árat (Polygon 1-min bars)
2. Újrakalkulálni a P&L-t (a tényleges exit-tel)
3. Aggregátum analízis: melyik időablak ad a legjobb total P&L-t, a legkisebb LOSS_EXIT triggerelést, a legjobb excess vs SPY-t

**Várt eredmény**: az 15:30 entry előnyét kvantitatívan validálja, vagy más optimumot talál.

**Effort**: ~1-2 óra Chat-oldali

**Owner**: Chat (Fázis 2, W23)

**Forrás**: [`docs/review/2026-05-12-daily-review.md`](../review/2026-05-12-daily-review.md) — "ENTRY TIMING HIPOTÉZIS" + Tamás javaslata

### 2.2 M_contradiction sign-flip vizsgálat

**Mi**: 7 napos M_contradiction LIVE iránybeli helyesség: **33%** (2 ✓ + 4 ✗ a 6 fired esetből). **Rosszabb mint random**. A "double jeopardy" minta (FORM máj 11, CENX máj 12) megerősíti.

**Hipotézis**: a sign-flip ($M_c = 1.2 \times$ a $0.8 \times$ helyett) lehet, hogy pozitív expectancy-t ad. **Kvantitatív backtest szükséges**.

**Megoldás (analitikus)**:
- A 60+ napi adat összes M_contradiction fired esetére: ha sign-flippelt ($M_c \to 1.2$), mennyi lett volna a P&L?
- Bayes-faktor a sign-flip vs deaktiválás vs status quo között
- Döntés: (A) sign-flip, (B) deaktiválás ($M_c = 1.0$), (C) Status quo (status: alulvizsgált)

**Effort**: ~1 óra Chat-oldali

**Owner**: Chat (Fázis 2, W23)

### 2.3 TP1 cél revízió (új swing TP-struktúra)

**Mi**: A régi `tp1_atr_multiple: 1.25` swing horizonton **újrakalibrálandó**. A swing pivot új struktúrája:
- **TP1**: +1.5× ATR (~+4-5%) → 50% qty zárás, trail SL felfelé
- **TP2**: +3.0× ATR (~+8-10%) → maradék 50% zárás
- **SL (mental)**: -2.0× ATR (~-5-6%) — overnight gap buffer

**Megoldás**: `defaults.py` config update + scoring-független TP/SL logika a swing architektúra design dokban.

**Effort**: ~30 min config + ~1 óra CC unit teszt

**Owner**: CC (Fázis 2 design → Fázis 3 deploy)

### 2.4 Dinamikus pozíciószám — rolling 10-12, 0.35% risk

**Mi**: A 2026-04-11-i 13 pontos terv #7 javaslata — **dinamikus pozíciószám**. A swing pivot keretében az új paraméterek:
- Risk per position: **0.35%** ($350)
- Concurrent positions cap: **12 (steady state ~10)**
- Daily new entries: **2-3** (NEM kötelező napi 3-5)

Ha nincs minőségi flow signal egy adott napon, **NEM kereskedünk**. A "csak ha érdemes" filozófia.

**Indoklás**: a swing-en a 10-12 concurrent miatt a jelenlegi 5 fix napi entry **túl agresszív**.

**Megoldás**: `defaults.py` config + Phase 6 sizing logika átalakítás.

**Effort**: ~1 óra CC

**Owner**: CC (Fázis 3 deploy)

---

## 3. P3 — Fázis 3 vagy később

### 3.1 ADR earnings adatforrás fix

**Mi**: BUD 2026-05-05 — ADR earnings event, az FMP `/stable/earnings?symbol=BUD` **NEM tartalmazta** a 2026-05-05 dátumot. **5-10 hasonló eset** mehetett le észrevétlenül a 60 napi adatban.

**Megoldás (kombinált)**:
- (A) Polygon `tickers/{ticker}/events` — jobban lefedi ADR-eket
- (D) Hard-coded ADR blacklist konfig — top 50-100 ADR earnings dátum manuális tracking

**Effort**: ~3-4 óra CC

**Owner**: CC (Fázis 3, W25-W26 között)

### 3.2 Breakeven Lock profit-küszöb (swing-integrált)

**Mi**: A régi "Breakeven Lock" mechanizmus profit-trigger ~+1% felett aktivál. A swing TP/exit struktúrában a profit-küszöb integrálandó.

**Megoldás**: a swing exit logika design fázisban (Fázis 2) eldől.

**Effort**: ~30 min config (a design után)

**Owner**: CC (Fázis 3 deploy)

### 3.3 Phase 4 snapshot enrichment

**Mi**: A jelenlegi `state/phase4_snapshots/` csak a winner ticker-eket menti. A teljes ticker tábla mentése javasolt a Bonferroni-szignifikáns flow al-komponensek (PCR, OTM-inverse) longitudinális elemzéséhez.

**Megoldás**: Phase 4 snapshot logika módosítás — minden ~250-300 ticker mentése scoring táblával.

**Effort**: ~30-45 min CC + 3-4 unit teszt

**Owner**: CC (Fázis 3 deploy, az új scoring-gal párhuzamosan)

---

## 4. DROPPED — a swing pivot által strukturálisan eliminált backlog

A korábbi 15 backlog idea közül **8 dropolt**:

| # | Eredeti backlog | Drop indoklás |
|---|---|---|
| 1 | **LOSS_EXIT bracket SL cancellation** (4 instancia bug) | Mental stop architektúra strukturálisan eliminálja a bracket-rendszert |
| 2 | `nuke.py --orders` scope expansion | NINCS bracket order swing-en, `--positions` elég |
| 3 | UW rate limit kezelés finomítás | UW shadow log, scoring-ban deaktiválva (Day 90 audit) |
| 4 | LOSS_EXIT küszöb finomítás per-ticker ATR | Mental stop architektúra |
| 5 | dp_pct fallback default (universum-medián) | UW scoring-ban deaktiválva |
| 6 | Slippage-adjusted scoring validation | Új scoring eleve slippage-szembesített |
| 7 | High-score liquidity check | A "magas pontszám paradoxon" a scoring revízión át kezelendő (Bonferroni-minimum) |
| 8 | monitor.py belső replay események jelölése | Alacsony prioritás, későbbi |

**Plus a 2026-04-11 13 pontos terv**:
- `#10 Call wall T1 kikapcsolás` → **automatikusan megtörténik** (scoring egyszerűsítés kiveszi M_GEX-et)
- `#11 VWAP guard egyszerűsítés` → **automatikusan megtörténik** (új entry 15:30 market open, NEM AVWAP-alapú)
- `#12 Multiplier chain egyszerűsítés` → **a scoring revízió felülírja** (csak M_target marad)
- `#13 Flow al-komponens dekompozíció` → **MÁR ELVÉGEZTE** a 232-trade audit

---

## 5. Strukturális finding-ok (Day 63 alapján)

### 5.1 A "magas pontszám paradoxon" — kvantitatívan megerősített

**60 napi adat (n=378)**: Pearson $\rho(S, R) = -0.000$ (p=0.996). A 95% CI a true effekten: $[-0.10, +0.10]$. **Strong evidence** a "small effect" tartományra.

**Quintile minta**:
- Q1 (alsó 75): -$129 / -$1.72 átlag
- Q2 (közepes 76): **+$880 / +$11.57** ⭐
- Q3 (közép 75): **-$1,341 / -$17.88** ⚠️
- Q4 (felső 76): +$76 / +$1.01
- Q5 (legfelső 76): -$677 / -$8.91

**Stratégiai következmény**: a swing pivot **PCR + OTM-inverse only scoring** (Bonferroni-szignifikáns minimum) **strukturálisan kezelhetővé** teszi a paradoxont. A tech és funda sub-score (kvázi-zaj) **kikerül**.

### 5.2 Az időtáv-paradoxon — mathematical doc 5.2 mutual information

A flow signal **$h$-step mutual information** modellje: $I \propto h \cdot \rho^2$.

Ha a 1-step $\rho = 0.14$ (Bonferroni-szignifikáns PCR korreláció), akkor:
- $h=1$: $I \approx 0.020$
- $h=3$: $I \approx 0.059$
- **$h=5$: $I \approx 0.098$** ← **5× erősebb signal**
- $h=7$: $I \approx 0.137$ (de overnight gap risk-aggregáció)

**Optimum**: $h \in \{3, 5\}$ nap. A swing pivot **5 napi time-stop**-pal ezt operacionalizálja.

### 5.3 Negatív Kelly criterion — matematikai konkluzió

**Konzervatív (csak determinisztikus exit-ek)**: $f^* = 0.50 \cdot 50/92.56 - 0.50 = -0.23$
**Default (összes exit)**: $f^* = 0.466 \cdot 15.07/92.56 - 0.534 = -0.458$

**Mindkettő negatív** — a rendszer **negatív expectancy-jű**. Csak a swing pivot 5×-szöröse signal-erősítés (mathematical doc 5.2) tudja **pozitív irányba mozdítani**.

### 5.4 Operacionális kockázatok — 4 strukturális instancia 13 napon belül

| Dátum | Ticker | Bug típus | Kár |
|---|---|---|---|
| 2026-05-01 | DTE | LOSS_EXIT + bracket SL ugyanazon napon | -$988 (paper) |
| 2026-05-07 | SQM | LOSS_EXIT + bracket SL ugyanazon napon | -$425 (valós) |
| 2026-05-12 | FORM | MOC fill + bracket másnap aktivált | ~-$200 (valós) |
| 2026-05-12 | AAPL | MOC fill + bracket másnap aktivált | ~-$150 (valós) |

**Strukturális, NEM patchelhető** — a swing pivot **mental stop architektúra eliminálja a bracket-rendszert**.

### 5.5 Makró-rezsim degeneráltság

A 60 napi mintán:
- BMI = YELLOW 100% (sosem GREEN, sosem RED)
- $M_{\text{VIX}} = 1.0$ 100% (VIX mindig < 20)
- $M_{\text{GEX}}$ undetermined: 75%

**A multiplier chain effektíven csak $M_{\text{target}}$-en és $M_{\text{contradiction}}$-on különböztet meg tickereket**. Ez **inkonzisztens differenciálás**. A swing pivot **csak $M_{\text{target}}$-et tartja meg** (M_contradiction sign-flip vizsgálat után dönt).

---

## 6. Nyitott kérdések (strukturális hipotézisek, NINCS aktív task)

### 6.1 Information ratio mérése a tilt-kalibrációhoz

A Bayes-update Day 90-en (UW shadow log audit, $n \approx 150-180$): ha a true $\rho_{\text{dp}}$ a $[-0.20, +0.20]$ tartományon kívülre esik, az UW visszahozható a scoring-ba. A 95% CI mérése **érdemleges power**-rel.

### 6.2 Linkage method érzékenység (jövő iterációhoz)

Ha a swing pivot Day 126-on sikeres, a következő iteráció (Q4 2026) **HRP/HERC allokáció**-t vizsgálhat. A linkage method (ward / complete / average) érzékenységét **15 tickerrel** kell tesztelni — a `docs/planning/bc22-hrp-allocation-design.md`-ben részletezve.

### 6.3 Cross-Asset Regime integráció a swing-en

A jelenlegi Cross-Asset Regime (HYG, IEF, RSP, SPY, IWM 20 napi momentum) **RISK_OFF / CRISIS** állapotokra csökkenti a max pozíciószámot. **Swing-en**: a 12 concurrent cap az új keret, de **CRISIS-ben 6-ra csökkentés** természetes. Implementáció a Fázis 3-ban.

### 6.4 MID Bundle integráció

A MID — Macro Intelligence Dashboard napi shadow snapshot-okat produkál. A swing pivot kontextusában **portfolio context layer** lehet — pl. Stagflation regime-ben a pozíciómért kisebb, vagy a sector-rotation szabályok defenzívebb sektor-súlyokat alkalmaznak. **BC25 W26+ scope**, Fázis 3 után.

---

## 7. Mit NEM csinálunk (és miért)

| Korábbi terv | Akció | Indoklás |
|---|---|---|
| **A+C kombinációs roadmap** (strategic-review 7.5) | **MÓDOSÍTVA** | 6 nap új adat → csak B (swing pivot) |
| Inkremeális finomítás a régi rendszerre | **NEM** | Strukturális bug-források nem patchelhetők |
| BC24 Institutional Flow Intelligence | **PARKOLT** | Új scoring (PCR + OTM-inverse only) felülírja |
| BC25 IFDS Phase 3 ← MID CAS | **PARKOLT Day 126-ig** | Új paper trading után döntés |
| Élő pénzes kereskedés Day 90-en | **NEM** | Új Day 126 milestone (kb. 2026-09-15) az első valós döntés |
| Komplex statisztikai modellek (random forest, neural net) | **NEM** | Kis n probléma (Bonferroni-minimum a tisztább alap) |

---

**A frissítésért felel**: Chat (Claude) — eseményalapú (új finding, új debug eredmény, új P1/P2/P3 task után). A Fázis 1-2 alatt heti konzisztencia-check.

---

## 8. Fázis 3 deploy utáni finding-ek (2026-05-18, Day 1 GO-LIVE)

A Day 1 GO-LIVE (2026-05-18) első operációs futamból **9 új tétel rögzítve** (3 P1 + 4 P2 + 1 permanent observation + 1 vasarnap esti Phase 1-3 cron freshness alert).

### 8.1 P1 — Strukturalis, Day 1 finding-ek

#### 8.1.1 ATR_pct floor minimum threshold (MASI 0.165% case)

**Mi**: MASI Day 1 entry-jén ATR=$0.295, ATR_pct=0.165%. Ez extrém alacsony — a swing TP1 distance csak +0.247%, mental SL distance -0.330%, ami kisebb mint az 1 standard daily noise (VIX 18.55 → ~1.16% expected daily move). A swing-target window strukturalisan fáls trigger-erzekeny.

**Strukturalis ok**: a swing pivot scoring (PCR + OTM-inverse percentile) NEM szűri ki a low-ATR tickereket. A sizing-formula `qty = (equity × 0.0035) / (ATR_pct × 2.0)` viszont óriási qty-t allocál (MASI: 604 share vs normál ~100), így a slippage és noise dominálnak.

**Javasolt fix** (`defaults.py`): `swing_atr_pct_floor: 0.005` (0.5% min daily volatilitás). MASI-t (0.165%) kiszűrné, tipikus mid-cap-ek (1-2%) bent maradnak.

**Effort**: ~30-45 min CC + 2-3 unit teszt + ~30 min backtest a 60 napi régi mintán a pontos floor kalibráláshoz.

**Akciváció**: Day 1 EOD post-mortem után (2026-05-19 kedd reggel), ha MASI tényleg gyors trigger-elt.

**Owner**: CC (P1 hotfix, ha az EOD eval mutatja a problémát)

#### 8.1.2 State/IBKR reconciliation gap

**Mi**: A swing system két source-of-truth-tal — `state/swing_positions.json` (mental stop / TP1 / TP2 levels) és IBKR positions (actual holdings) — csendben divergálni tud.

**Mai eset**: 14:34 pre-market submit → 14:42 manuális state reset → 15:30 NYSE open → mind a 3 ticker filled. A `state/swing_positions.json` üres, az IBKR-ben 3 nyitott pozíció. A swing system számára a 3 pozíció "elveszett" — az EOD eval 22:00-kor üres state-en futott volna, NULL exit logikával.

**Strukturalis kockázat**: bármilyen jövőbeli IBKR connection-bug, manuális state reset, vagy `nuke.py` invokáció ugyanezt a divergenciát hozhatja létre.

**Javasolt megoldás**: napi reconciliation script (`scripts/paper_trading/reconcile_state.py`) ami eltérés esetén:
- Telegram WARNING ("State/IBKR divergence: N IBKR positions not in state")
- NEM auto-fix — Tamás dönt rekonstrukció vs nuke
- Cron entry: `15 22 * * 1-5` (5 perccel az EOD eval után)

**Effort**: ~45 min CC + 2-3 unit teszt

**Owner**: CC (W22-ben javítás)

#### 8.1.3 Submit cron Telegram silence 0-submit esetén

**Mi**: A 15:30 cron `submit_orders.py` futott, detektálta hogy MASI/LBRT/EC már nyitott pozíció IBKR-ben (a 14:34-i pre-market submit-ok filled-ek), és skippelte: "Submitted: 0 tickers". NEM küldött Telegram üzenetet, mert a Telegram trigger az új submit-eken aktivál, NEM a cron heartbeat-en.

**Strukturalis kockázat**: ha bármilyen jövőbeli okból a `submit_orders.py` futása 0 új entry-vel zárul, Tamás nem kap visszajelzést hogy a cron lefutott. Hallgatás ≠ siker mintázat.

**Javasolt fix**: a `submit_orders.py` MINDIG küldjön Telegram-ot, akkor is ha 0 új entry:
- 0 submit → `"✓ Submit cron ran 15:30. Submitted: 0 new (N existing skipped)"`
- 1+ submit → meglévő "📈 IFDS Swing Submit" formátum

**Effort**: ~15 min CC

**Owner**: CC (W22 elején P1 hotfix)

#### 8.1.6 ✅ pt_monitor.py "5-min replay events" pollution (RESOLVED 2026-05-20)

**Státusz**: ✅ RESOLVED — root cause azonosítva (H1: pytest pre-flight FileHandler bind), fix deploy-olva (`lib/log_setup.py::_resolve_log_dir()`), +5 regressziós teszt. Részletes diagnózis: `docs/tasks/2026-05-19-pt-monitor-replay-diagnosis.md` §6.

**Áthivatkozás**: lásd §0.1 — eredetileg ott jelent meg mint P0, Day 1+Day 2 megfigyelés. Day 2 (2026-05-19) `pt_monitor_2026-05-19.log` 91 sora ugyanazt a LION/SDRL "Trail SL hit"/"LOSS_EXIT" mintát mutatta 16:37:19 timestamp-pal — pontosan a Mac Mini-n manuálisan futtatott `deploy_daily.sh --phases 1-3` pytest pre-flight ablakában.

**Fix kompozíció**:
- `scripts/paper_trading/lib/log_setup.py`: `_resolve_log_dir(log_dir)` helper redirect pytest alatt (`PYTEST_CURRENT_TEST` env var detektálással) tmp dir-be.
- Csak az implicit default (`log_dir="logs"`) redirektált — explicit caller-supplied `tmp_path` változatlanul áthalad (a meglévő 5 `test_log_setup.py` teszt változás nélkül passing).
- `tests/test_log_setup_isolation.py` (5 új teszt): a redirect viselkedés minden ágát védi.

**Hatás**: minden PT script (10+ darab) automatikusan védett pytest-bind pollution-tól. Produkciós cron viselkedés bit-for-bit változatlan.

### 8.2 P2 — Operációs, Day 1 finding-ek

#### 8.2.1 Pre-market submit + PreSubmitted státusz risk

**Mi**: 14:34-i pre-market submit során az IBKR Error 10349 (DAY TIF outside RTH) látszólag cancelled minden order-t. Két ticker (LBRT, EC) status=Cancelled visszajelzéssel, MASI PreSubmitted-ként marad. A 14:42-i state reset abból a feltevésből indult, hogy 3 order = cancelled. 15:30-kor mind a 3 order filled lett a NYSE open-en.

**Tanulság**: IBKR PreSubmitted vagy "Cancelled" státusz pre-market időben nem garantálja a végleges állapotot. State reset csak akkor biztonságos, ha az `ib.positions()` valóban üres (verifikálva, NEM csak a log alapján).

**Javasolt fix**: a manuális state reset folyamat (ha valaha újra kell) MUST:
1. `ib.positions()` ellenőrzés — 0 nyitott pozíció confirm
2. `ib.openOrders()` ellenőrzés — 0 pending order confirm
3. State reset csak ha mindketto üres

**Effort**: dokumentáció + opcionális script enhancement (`scripts/paper_trading/state_reset_safe.py`) — ~30 min

**Owner**: CC (W22+ alacsony prioritás, ritka manuális művelet)

#### 8.2.2 IBKR "Existing positions" guard — value-add component

**Mi**: A 15:30 `submit_orders.py` helyesen detektálta hogy MASI/LBRT/EC már nyitott pozíció IBKR-ben (az `existing_positions` check működött), és NEM duplázta őket.

**Permanent record**: ez a guard megorzendo minden refaktoring során. A 14:34 pre-market submit utáni 15:30 cron-on a teljes pozíciómennyiség duplázása ($3500+ extra notional) strukturalis kockázat lett volna nélküle.

**Akció**: NINCS — csak rögzítendő mint value-add component, megorzendo.

#### 8.2.3 Phase 2 `_exclude_earnings` intermittent thread hang

**Mi**: 14:25-i manuális Phase 1-3 futtatás közben a `_exclude_earnings` futtatás `as_completed(futures)` waiter-en lógott (KeyboardInterrupt-tal lezárva, mert 14:30 cron közeledett).

**Diagnózis**: párhuzamos FMP earnings calendar hívások (`ThreadPoolExecutor`) között valószínűleg egy nem-responsive request a thread-poolt blokkolta. FMP rate limit vagy `concurrent.futures` timeout config gyanú.

**Strukturalis kockázat**: a jövő vasárnap esti (5/24 22:00) heti rebalance cron-on ha ugyanez a thread hang fennáll, a Phase 1-3 silent fail-elhet és a Phase 4-6 a régi péntek esti context-tel dolgozik tovább.

**Javasolt megoldás**:
- (A) Telegram alert ha a vasárnap esti Phase 1-3 cron NEM termel friss `state/phase13_ctx.json.gz`-t vasárnap 23:00-ig (heartbeat-szerű)
- (B) `_exclude_earnings` thread pool timeout pattern (per-future timeout + `cancel_futures=True`)

**Effort**: (A) ~15-20 min CC, (B) ~30 min CC + 2-3 unit teszt. Mindketto érdemes.

**Owner**: CC (W22 elején)

#### 8.2.4 Legacy wrapper script audit

**Mi**: A `scripts/deploy_intraday.sh` a Fázis 3 deploy ELŐTT tartalmazott `submit_orders.py` és `company_intel.py` futtatást a Phase 4-6 után. A 14:30 cron-on ez a régi inline submit pre-market submit-ot termelt (lásd §8.2.1). A `2026-05-17-swing-execution-exit.md` Task #4 a `submit_orders.py`-t és `pt_monitor.py`-t átírta, de a wrapper scripteket NEM auditalta.

**Strukturalis kockázat**: lehet hogy más legacy wrapper scriptek (`scripts/deploy_daily.sh`, `scripts/setup_cron.sh`) is tartalmaznak swing pivot előtti logikát.

**Javasolt megoldás**: full audit + cleanup task:
- `scripts/deploy_intraday.sh` ✅ FIXED (`ce06238`)
- `scripts/deploy_daily.sh` — audit szükséges
- `scripts/setup_cron.sh` — audit szükséges
- `scripts/paper_trading/*.py` — egyenkénti audit a bracket/LOSS_EXIT/5min reference-ekre

**Effort**: ~30-45 min audit + ~30 min cleanup. Új task fájl: `docs/tasks/2026-05-19-legacy-wrapper-script-audit.md`.

**Owner**: CC (W22 első napjaiban, P2 prioritás)

### 8.3 Permanent observations

#### 8.3.1 AVDL.CVR un-nuke-able orphan pozíció

**Mi**: Az IBKR paper account-ban van egy AVDL.CVR (Avadel Pharmaceuticals Contingent Value Right) pozíció, ami a Day 1 előtti időszak öröksége. Tamás korábban próbálta `nuke.py`-vel kivenni, NEM sikerült (CVR instrumentumok specifikus IBKR cancel-keretet igényelnek, ami a `nuke.py` scope-ján kívül esik).

**Akció**: NINCS — a swing system számára transparent. A `monitor_positions.py` reggeli leftover check valoszinuleg flag-eli, de nem blokkolja a swing entry-ket.

**Permanent record**: ez NEM bug, NEM aktiv kockazat — egyszerűen egy "orphan" pozíció, amit a swing system nem érint. **Day 63+ inherited, NO action**.

**Owner**: NONE

---
