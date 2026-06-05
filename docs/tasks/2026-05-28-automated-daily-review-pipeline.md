# Task — Automatizált napi review pipeline (CC-oldali)

**Status**: WIP
**Updated**: 2026-06-05
**Haladás**: §0 előfeltétel ✅ (Part A + Day 14). **1a data-aggregátor ✅** (`generate_review_data.py`, éles 6/3 validálva). **1b/1c connector-FÜGGETLEN mag ✅ KÉSZ** (`generate_review.py`): `build_cross_check_flags(review_data, ibkr)` pure cross-check logika (pnl_tracking_gap, state_ibkr_divergence, cumulative_drift — pont a Day 13/14 incidenseket fogná el; a 6/4 +243.42 swing-attr vs broker realized P0-t flag-elne), `render_review_markdown` determinisztikus draft (Chat §4 struktúra, adat-táblák + LLM-placeholderek). 1a→1c éles 6/4 adaton end-to-end validálva. +11 teszt, 1898 passing. **Hátra (connector kell)**: a thin connector-wrapper a `main()`-ben (IBKR snapshot lekérés: realized/positions/NetLiq → build_cross_check_flags), + az 1c LLM-narratíva kitöltés (CC review-időben). Az IBKR MCP probléma rendeződése után élesíthető.
**Prioritás**: P1 (a 0. fázis P0 előfeltétellel)
**Becsült effort**: ~6-9 óra CC (0. fázis külön ~2-3h, már megtervezve)
**Owner**: CC (implementáció + jövőbeli futtatás), Tamás (deploy jóváhagyás), Chat (stratégiai eszkaláció fogadása)
**Forrás**: Tamás munkamegosztási döntés 2026-05-28 (Chat=stratégia+tervezés, CC=review+bugfix+automatizáció) + Day 7/8 daily review-k + IBKR MCP connector elérhetőség

---

## 1. Probléma

A napi review jelenleg **manuális, Chat-oldali**: a Chat (Log Review session) beolvassa a synced logokat + state-et, és prózában megírja a `docs/review/YYYY-MM-DD-daily-review.md`-t a kialakult struktúrában. Tamás célja a **chat-es manualitás kikapcsolása**: CC generálja a review-t autonóm módon, és csak a stratégiai ítéletet eszkalálja a Chat-nek.

**Kritikus komplikáció (Day 8, 2026-05-27 felfedezve)**: a `cumulative_pnl.json` és `daily_metrics.json` **NEM rögzíti a realized P&L-t** a `close_positions.py` exit-jeiből (TP2/MOC/SL). A Day 8-i 7 exit -$695,77 realized P&L-je **teljesen hiányzik** a synced adatforrásokból (mindkét fájl `pnl: 0`). A valódi cumulative -$779,64 (IBKR Net Liq), a hivatalos +$39,33 — **$819 eltérés**.

**Következmény az automatizációra**: egy connector-mentes, "synced logokból" dolgozó review-skill **a téves +$39,33-at replikálná**. Az IBKR live read (connector vagy ib_async) NEM másodlagos cross-check — amíg a tracking gap fennáll, ez az **egyetlen megbízható realized P&L forrás**.

**Részletes evidence**:
- `docs/review/2026-05-27-daily-review.md` §0 (P0 tracking gap teljes diagnózis)
- `docs/review/2026-05-26-daily-review.md` §5.5, §8.5 (a gap első jelei + IBKR connector szerepe)

---

## 2. Stratégia — 3 réteg, prioritás-sorrendben

### 0. fázis (P0, MINDENEKELŐTT) — a P&L tracking gap fix

**NEM új munka** — a `docs/tasks/2026-05-26-daily-metrics-auto-update-from-reconcile.md` (Rész 3) már megtervezett task, csak **deploy hiányzik**. A `close_positions.py` exit-jei (TP2/MOC/SL) után írni kell:
- `cumulative_pnl.json daily_history[date]`: `pnl` (realized gross), `commission`, `trades`, `filled`, `tp1_hits`/`tp2_hits`/`sl_hits`/`moc_exits`
- `daily_metrics/YYYY-MM-DD.json`: `pnl.gross/commission/net`, `exits.{tp1,tp2,sl,moc}`, `swing_state.exits_today` (valódi aznapi exit, NEM next-day flag)

**HARD előfeltétel**: a 0. fázis deploy nélkül az 1. fázis review-skill hibás P&L-t generál. **Ez a blokkoló dependency.**

**Plusz egyszeri**: Day 1-8 canonical P&L rekonstrukció az IBKR `get_account_trades(DAYS_30)` realized fill-jeiből — a `cumulative_pnl.json` teljes újraszámolása a valódi -$656,44 realized-re (jelenleg téves +$39,33). A Chat ezt már elő tudja állítani az IBKR connector-ból (lásd §5 Adatfüggelék).

### 1. fázis — az automatizált review skill

Három alkomponens:

#### 1a — Determinisztikus data-aggregátor (`scripts/paper_trading/generate_review_data.py`)

Beolvassa az összes forrást és kiad egy strukturált `state/review_data/YYYY-MM-DD.json`-t:

**Input források**:
- `logs/pt_eod_{date}.log`, `pt_monitor_{date}.log`, `pt_close_{date}.log`, `pt_submit_{date}.log`, `pt_reconcile_{date}.log`
- `state/swing_positions.json` (záró állapot)
- `state/daily_metrics/{date}.json` (a 0. fázis után megbízható)
- `scripts/paper_trading/logs/cumulative_pnl.json`
- `state/uw_shadow/{date}.json`

**Számított mezők** (determinisztikus):
- Day szám (calendar + trading-day egyaránt, az inkonzisztencia explicit jelzésével)
- Realized P&L (a 0. fázis utáni daily_metrics-ből)
- Open pozíciók + days_held (calendar ÉS trading-day, lásd §3 anomália-szabály)
- Sector distribution + % + cap-távolság
- Új entries + exits (típus szerint: TP1/TP2/SL/TIME_STOP/MOC)
- UW shadow összegzés

**Output**: `review_data_{date}.json` (gépi struktúra az 1c LLM-réteghez)

#### 1b — IBKR live cross-check (a connector-kérdés itt dől el)

**ELSŐ LÉPÉS — connector-verify** (a CC nyitott technikai kérdése): tud-e CC csatlakozni az `api.ibkr.com/v1/api/mcp`-hez saját OAuth flow-val?
```bash
claude mcp add --transport http ibkr https://api.ibkr.com/v1/api/mcp
# majd: get_account_summary → DUH118657 visszajön-e?
```

**Ha a connector működik CC-ből** → a cross-check connector-alapú (`get_account_summary`, `get_account_positions`, `get_account_trades(TODAY)`).

**Ha NEM** (OAuth nem triviális CC-ből) → `ib_async` SSH fallback a Mac Mini-n, a meglévő `scripts/paper_trading/reconcile_state.py` mintájára (`ib.positions()` + `ib.executions()`).

**A cross-check kötelező logika** (akármelyik forrásból):
```
daily_metrics.pnl.gross  ≟  IBKR realized_pnl (get_account_trades TODAY összege)
state tickers            ≟  IBKR positions
daily_metrics cumulative ≟  IBKR Net Liq - 100000 (± nyitott unrealized)
```
**Ha bármelyik eltér → automatikus P0 flag a review-ban.** Ez kapná el a Day 8-szerű tracking gap-eket. (A 0. fázis után ennek mindig egyeznie kell — a cross-check a Rész 3 helyességének folyamatos őre.)

**Bónusz a connectorból**: a tényleges fill árak → valódi slippage per ticker (a `daily_metrics.execution.slippage_per_ticker` jelenleg üres, lásd Day 7/8 review §5.5 #3). A connector `get_account_trades` fill ára vs a `pt_submit.log` planned ára = valódi slippage, közvetlenül a review-ba.

#### 1c — CC LLM review-generátor + anomália-flag + Chat-eszkaláció

A CC (LLM-rétegként) az 1a JSON + 1b cross-check eredmény + a Chat review-template (lásd §4 struktúra-referencia) alapján:
- Megírja a `docs/review/YYYY-MM-DD-daily-review.md`-t a Chat struktúrájában (header + §0-§8 + State)
- Kitölti az anomália-szekciókat a §3 szabálykészlet alapján
- A **stratégiai ítéletet igénylő** finding-okat egy explicit `## ⚠️ CHAT ESCALATION` szekcióba gyűjti a review tetején (a Chat következő session-kor ezt olvassa először)

### 2. fázis (finomítás, alacsony prioritás)

- A legacy `reconcile_state.py` (22:15 cron) redundancia felülvizsgálat — ha az 1b cross-check megbízhatóan fut, a 22:15 detektor szerepe csökkenhet. **DE a cron-autonómiát NEM adjuk fel** (a connector nem fut 22:00-kor magától; a Mac Mini cron a source-of-truth).
- Operator emergency procedure **Pattern 6** doc entry: "IBKR állapot gyors lekérdezés a connector-on át" mint diagnosztikai lépés a Pattern 1-5 mellé (`docs/tasks/2026-05-25-operator-emergency-procedure.md` v1.2).

---

## 3. Anomália-detektálási szabálykészlet (1a/1c)

A rule-based flag-ek, amelyeket a data-aggregátor automatikusan azonosít:

| Flag | Szabály | Prioritás |
|------|---------|-----------|
| P&L tracking gap | `daily_metrics.pnl.gross ≠ IBKR realized (TODAY)` | **P0** |
| State/IBKR divergence | `state tickers ≠ IBKR positions` | **P0** |
| Cumulative drift | `\|daily_metrics cumulative − (IBKR NetLiq−100k−unrealized)\| > $50` | **P0** |
| days_held calendar-bug | `days_held (calendar) ≠ trading_days_between(entry, today)` ÉS TIME_STOP közeli | **P1** |
| ATR_pct floor breach | bármely entry `atr/entry_price < 0.005` | **P1** |
| ATR_pct ceiling breach | bármely entry `atr/entry_price > 0.05` | **P2** |
| Single-position koncentráció | bármely pozíció `notional/equity > 0.12` | **P2** |
| Sector cap közelség | bármely szektor `notional/equity > 0.25` (cap 0.30) | **P2** |
| Stop-közelség | bármely nyitott pozíció `\|mark − stop\| / mark < 0.02` | **P1 figyelő** |
| Autonóm bracket trigger | IBKR exec orderRef NEM `IFDS_*` | **P0** |
| Reconcile silent OK | `pt_reconcile.log` "match (silent exit)" | ✅ pozitív |

A stratégiai ítéletet igénylő (NEM rule-based) finding-ok → `## CHAT ESCALATION` szekció:
- Több napos P&L-trend értékelése (edge van-e?)
- Scoring-minta gyanú (pl. magas S_j + alacsony ATR korreláció — JHG Day 8)
- Architektúra-váltási javaslatok

---

## 4. Struktúra-referencia (1c LLM-réteg)

A review doc kötelező szerkezete (a Day 7/8 review mintája):

```
# IFDS Daily Review — YYYY-MM-DD (nap, Day N Swing Pivot, Wxx Dy)
[header: net P&L, realized, Net Liq, cumulative (hivatalos ÉS valódi), open positions]
[⭐/⚠️ Kulcs finding-ek bullet-ök]

## ⚠️ CHAT ESCALATION (ha van stratégiai ítélet-igény)   ← ÚJ szekció
## 0. Kritikus finding (ha P0)
## 1. Day N Trades (IBKR get_account_trades)
## 2. EOD State + következő nap outlook
## 3. Pipeline Log Review (pt_close/submit/monitor/reconcile/eod)
## 4. UW Shadow Log
## 5. Anomáliák / megfigyelések (P0/P1/P2/P3 állapotok)
## 6. Következő nap outlook
## 7. Files referenced
## 8. Strukturális finding-ek összefoglaló
## State (Day N — Wxx Dy)
[+ "napi karakter egy mondatban" záró]
```

Referencia fájlok a stílushoz: `docs/review/2026-05-26-daily-review.md`, `docs/review/2026-05-27-daily-review.md` (a legfrissebb, IBKR-integrált struktúra).

---

## 5. Adatfüggelék — Day 1-8 canonical realized P&L (IBKR `get_account_trades`)

A Chat által az IBKR connector-ból kinyert valódi realized fill-ek (a 0. fázis canonical rekonstrukcióhoz):

| Dátum | Ticker | Típus | Realized P&L |
|-------|--------|-------|--------------|
| 2026-05-19 (D2) | EC | TP1 | +$112,31 |
| 2026-05-20 (D3) | VLO | (1-share cleanup) | -$6,37 |
| 2026-05-21 (D4) | VLO | SL (Tamás Day 3 TWS bracket) | -$220,69 |
| 2026-05-22 (D5) | ON | TP1 (Tamás Day 3 TWS bracket) | +$159,12 |
| 2026-05-27 (D8) | EC | TP2 (100@14,51 + 66@14,44) | +$231,87 |
| 2026-05-27 (D8) | MASI | TIME_STOP MOC | +$16,99 |
| 2026-05-27 (D8) | LBRT | TIME_STOP MOC | -$418,66 |
| 2026-05-27 (D8) | WMB | TIME_STOP MOC | -$379,10 |
| 2026-05-27 (D8) | CNC | TIME_STOP MOC | -$48,68 |
| 2026-05-27 (D8) | DXCM | TIME_STOP MOC | -$100,06 |
| 2026-05-27 (D8) | PFGC | TIME_STOP MOC | +$1,87 |
| **Closed realized total (Day 1-8)** | | | **-$651,40** |

IBKR Net Liq 2026-05-27 záró: **$99 220,36** (= -$779,64 a $100k baseline-ról, ebből realized -$651,40 + nyitott 4 pozíció unrealized -$315,23 + korábbi napok M2M; a Net Liq a kanonikus igazság).

---

## 6. Implementációs sorrend (CC)

1. **0. fázis deploy** (`2026-05-26-daily-metrics-auto-update-from-reconcile.md` Rész 3) — close_positions.py P&L write
2. **Day 1-8 canonical rekonstrukció** (egyszeri script vagy manuális, az §5 tábla alapján)
3. **1b connector-verify** (`claude mcp add` + `get_account_summary` DUH118657 teszt) — ELŐSZÖR, mert ez dönti el az 1b adatforrást
4. **1a data-aggregátor** (`generate_review_data.py`) + unit tesztek
5. **1b cross-check** integráció (connector VAGY ib_async, a 3. lépés eredménye szerint)
6. **1c LLM review-generátor** — CC slash command (`/review-daily`) vagy wrapper, a §4 struktúrával
7. **End-to-end teszt**: az első futás a **Day 7 (2026-05-26) review újragenerálása** + a Day 9 (2026-05-28) első éles autonóm review

---

## 7. Tesztelés

- `tests/test_generate_review_data.py`: data-aggregátor unit tesztek (mock logok + state → várt JSON)
- Anomália-szabály tesztek: minden §3 szabályra (pl. injektált P&L mismatch → P0 flag)
- Cross-check teszt: mock IBKR response vs state divergence → P0 flag
- E2E: Day 7 review újragenerálás, összevetés a Chat által írt `2026-05-26-daily-review.md`-vel (a számszerű részek egyezzenek; a próza eltérhet)
- Regresszió: 0 a meglévő pt_* teszteken

---

## 8. Commit konvenció

```
feat(review): automated daily review data aggregator (1a)
feat(review): IBKR cross-check layer (1b, connector|ib_async)
feat(review): /review-daily CC command (1c)
fix(close_positions): write realized P&L to cumulative_pnl + daily_metrics (0. fázis, Rész 3)
data(reconcile): canonical Day 1-8 P&L reconstruction from IBKR
docs(emergency): Pattern 6 — IBKR connector quick-query (2. fázis)
```

---

## 9. Nyitott kérdések (CC verify a deploy előtt)

1. **CC OAuth az `api.ibkr.com/v1/api/mcp`-hez** — működik-e? (1b connector vs ib_async fallback dönti el)
2. **A `/review-daily` futtatás triggere** — manuális CC parancs Tamás-tól, VAGY cron-hook a Mac Mini 22:30 sync után? (Az autonómia szintje — kezdetben manuális, később cron-hook)
3. **A Chat-eszkaláció csatornája** — a review doc `## CHAT ESCALATION` szekciója elég, VAGY külön `docs/review/ESCALATE-{date}.md` flag fájl (amit a Chat következő session-kor explicit keres)?

---

## 10. Kapcsolódó dokumentumok

- **Blokkoló előfeltétel**: `docs/tasks/2026-05-26-daily-metrics-auto-update-from-reconcile.md` (Rész 3)
- **P0 finding forrás**: `docs/review/2026-05-27-daily-review.md` §0
- **IBKR connector kontextus**: `docs/review/2026-05-26-daily-review.md` §8.5
- **Master backlog**: `docs/master-reference/04-risks-and-open-questions.md` §0.10 (P0 visszaminősítés szükséges)
- **Munkamegosztás**: Tamás 2026-05-28 döntés (Chat=stratégia, CC=review+bugfix+automatizáció) — memóriába mentve
