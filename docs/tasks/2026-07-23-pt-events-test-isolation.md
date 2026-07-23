Status: OPEN
Updated: 2026-07-23
Note: Freeze-safe (teszt-env-higiénia; a production kódút VISELKEDÉS-INVARIÁNS — a default útvonal változatlan, ha az env var nincs beállítva). Forrás: 2026-07-23 daily review §6/P1. A test-env-hygiene szabály 3. rése (phase4_snapshot/04-15, uw_shadow/05-19 után).

# pt_events production-log teszt-izoláció (test-env-hygiene P1)

## Probléma

A `tests/` futtatása a **production `logs/pt_events_{today}.jsonl`-be ír**. A 2026-07-23-i review
(§6/P1) elkapta: 176 legacy esemény (`circuit_breaker cum_pnl=-6000`, `moc_submitted`, `trail_activated`;
tickerek **AAA/BBB/CCC** teszt-fixture + AAPL/LION/SDRL) került a valós logba 16:34-16:51 CEST-kor egy
pytest-futásból.

**Gyökérok** (verifikálva):
- `scripts/paper_trading/lib/event_logger.py`: `PTEventLogger.__init__(log_dir: str = "logs")` → a `log()`
  a `logs/pt_events_{today}.jsonl`-be ír (production).
- `close_positions.py:54`, `pt_monitor.py:52`, `submit_orders.py:55`: **modul-szintű** `evt = PTEventLogger()`
  importáláskor, a default `"logs"`-szal, csak `try/except ModuleNotFoundError`-ra guardolva (ami sosem áll fenn).
- Bármely teszt, ami importálja e scripteket vagy a legacy circuit_breaker/trail kódutakat exercise-eli
  (`test_bc11_circuit_breaker`, `test_circuit_breaker_halt`, `test_close_positions_split`,
  `test_monitor_positions`, `test_console`, `test_phase0`, `test_pipeline_e2e`, …), a valós logot szennyezi.
- `tests/conftest.py` létezik, de **nincs benne event-log redirect**.

**Hatás:** a hiteles P&L-lánc (`pending_exits`→`daily_metrics`→`cumulative`) NEM érintett (a teszt nem ad be
valós IBKR-ordert), DE a `pt_events` a **v6 §5 ops-forrás** ÉS az **FRL loader rank-2 forrása**
(`docs/design/2026-07-21-factor-research-loop-spec.md` §4.1). Az FRL éles indulásakor ez a szennyezés a
dp_pct/AAPL-mock hibaosztályt ismételné — ezért P1.

## Megközelítés (TDD)

### 0. lépés — trigger azonosítása (kód-olvasás, nem blokkoló a fixre)

Állapítsd meg, MI futtatta a pytestet a Mini-n 16:34-16:51 CEST-kor (a `deploy_intraday.sh` 15:45-ös
pre-flight? manuális run?). A fix trigger-agnosztikus, de a triggert a §Eredménybe dokumentáld — ha egy
cron pre-flight, az minden nap szennyezne (a korábbi napok kis `pt_events`-e arra utal, hogy NEM napi —
verifikálandó: `logs/pt_events_*.jsonl` méret-eloszlás a swing-érában).

### 1. lépés — env-vezérelt log-dir (production, VISELKEDÉS-INVARIÁNS)

`scripts/paper_trading/lib/event_logger.py`:
```python
def __init__(self, log_dir: str | None = None) -> None:
    log_dir = log_dir or os.environ.get("IFDS_PT_EVENT_DIR", "logs")
    ...
```
Env var nélkül a viselkedés **bitre azonos** (`"logs"`) — a production cron útját nem érinti. Ez a
freeze-carve-out alapja (§4.2/1 tracking-higiénia; a d3fce73 precedens mintája).

### 2. lépés — conftest izoláció (a valódi védelem)

`tests/conftest.py` **modul-tetején** (a test-kollekció ELŐTT, mert a scriptek modul-szinten példányosítják
az `evt`-t importáláskor):
```python
import os, tempfile
os.environ.setdefault("IFDS_PT_EVENT_DIR", tempfile.mkdtemp(prefix="ifds_pt_events_"))
```
Így minden import-idejű `PTEventLogger()` a tmp-dirbe ír, függetlenül attól, melyik teszt melyik scriptet
importálja. (Fixture NEM elég: a session-scope fixture a kollekció UTÁN fut, a modul-szintű `evt` addigra
létrejött.)

### 3. lépés — regressziós guard-teszt (a "test mocked itself out" mintája)

`tests/test_pt_event_isolation.py`:
- **mtime-invariancia**: a `logs/pt_events_*.jsonl` (ha létezik) mtime + fájlhalmaz a teljes offending
  path exercise UTÁN sem változik (analóg a §8.1 sink-audit szabállyal). Reprezentatív hívás: importáld a
  `close_positions`/`pt_monitor` modult ÉS hívj egy legacy `evt.log(...)`-ot kiváltó függvényt.
- **pozitív**: `IFDS_PT_EVENT_DIR` be van állítva ÉS a `PTEventLogger().path` a tmp-dir alá mutat.
- **negatív-védő**: `monkeypatch.delenv("IFDS_PT_EVENT_DIR")` → `PTEventLogger().path` a `"logs/"`-ba mutat
  (a viselkedés-invariancia bizonyítéka: a default nem változott).

### 4. lépés — a már szennyezett 07-23 log tisztítása (Mini + lokális)

A `logs/pt_events_2026-07-23.jsonl` 176 teszt-eseményt tartalmaz. **Backup + szűrt újraírás**: a valós swing
események megtartása (`script ∈ {monitor_positions, submit, close, eod, reconcile}` ÉS `ticker ∉ teszt-halmaz`
ÉS a 16:34-16:51 UTC ablakon KÍVÜL), a legacy/teszt-események eldobása. A szűrő verifikálandó: a megmaradó
sorok pontosan a 07-23 review §2-§5-ben hivatkozott valós események (USFD exit+reentry, reconcile 5/5).
A Mini-írás az `ssh ifds-mini` allowlisttel megy; a log NEM pénzügyi ledger (a [[mini-financial-write-guard]]
nem tiltja), de backup KÖTELEZŐ.

## Implementációs terv (fájlok)

Módosuló:
- `scripts/paper_trading/lib/event_logger.py` — env-vezérelt `log_dir` (viselkedés-invariáns)
- `tests/conftest.py` — modul-tetős `IFDS_PT_EVENT_DIR` setdefault

Új:
- `tests/test_pt_event_isolation.py` — 3 teszt (mtime-invariancia, pozitív tmp-path, negatív default-védő)

Adat-cleanup (nem kód):
- `logs/pt_events_2026-07-23.jsonl` szűrt újraírás a Mini-n (backup: `.bak.pre_testclean`) + lokális sync

## Tesztelés

- Az új `test_pt_event_isolation.py` 3 tesztje zöld.
- **A teljes suite futtatása UTÁN a repo-gyökér `logs/pt_events_{today}.jsonl` mtime NEM változik** (a fix
  bizonyítéka — futtasd `IFDS_PT_EVENT_DIR` nélkül is, hogy lásd: a conftest védelme fog).
- Baseline: a jelenlegi passing szám (≥1985) **nő**, 0 failure, 0 warning.
- ⚠️ Ne szennyezd a fejlesztést sem: a MacBookon a suite eddig is a lokális `logs/`-ba írt — a 2. lépés ezt is megszünteti.

## Commit

`fix(test): izoláld a PTEventLogger-t a production pt_events logtól (test-env-hygiene P1)`

## Eredmény (a végrehajtás tölti)

- Trigger (0. lépés): …
- pt_events méret-eloszlás (napi szennyezés-e?): …
- 07-23 cleanup: megtartott/eldobott sorok száma …
