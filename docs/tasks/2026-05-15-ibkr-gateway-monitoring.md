# Task: IBKR Gateway Monitoring — Diagnózis + Targeted Fix

**Status:** DONE
**Priority:** P1 (operational risk — `04-risks-and-open-questions.md` §1.1)
**Created:** 2026-05-15 (Chat által írás, pre-Fázis 1 deploy)
**Updated:** 2026-05-16
**Deploy:** 2026-05-16 (CC Ülés A, Fázis 1 W21 close)
**Note:** baseline (§10 Fix C + §11 anti-pattern) deployed + verified Mac Mini-n
2026-05-16. §3 H1/H2/H3 diagnózis: H1 igazolt (Telegram alert nem ért el a
requests.post-ig), H2 részleges (check 16:00 → 20 perc submit előtt). Fix A
NEM szükséges (load_dotenv), Fix B halasztva (swing pivot 15:30 CEST átállás
után újraértékelendő).
**Owner:** Claude Code
**Estimated effort:** ~1–1.5h (diagnózis 20–30 min + targeted fix + tesztek)

**Source decision:** [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §6.1 — Fázis 1 első CC task.

**Depends on:** nincs

**NEM depends on:** semmilyen swing pivot komponens (a régi rendszer Fázis 1-2 alatt változatlanul fut). A monitoring **kettős célt** szolgál: a régi rendszer hátralévő ~20 napját stabilizálja, és a Fázis 3 utáni új paper trading-en is releváns (15:30 CEST entry-időnél ugyanaz a Gateway-leállási kockázat).

---

## 1. Kontextus — a 2026-05-11-i incidens

A `docs/review/2026-05-11-daily-review.md` "KÉZI ORDER SUBMISSION — DUPLA INFRA AKADÁS" szakasz dokumentálja:

```
16:20:11 [INFO] IFDS Paper Trading — 2026-05-11
positions request timed out
open orders request timed out
completed orders request timed out
account updates for DUH118657 request timed out
IBKR connection attempt 1/3 FAILED (clientId=10)
[ismétlődik 3x retry-ra]
IBKR connection FAILED after 3 attempts (clientId=10):
```

**Tamás 17:15 CEST-kor (55 perccel később) vette észre kézi monitoring során** — NEM Telegram alert-ből. A kézi rögzítés mellékhatása viszont kedvező volt (avg slippage -1.79%, vs a tipikus +0.20%), de ez **nem skálázódik** és **nem reprodukálható**.

## 2. Mi létezik már (NEM kell újraépíteni)

| Komponens | Helye | Állapot |
|---|---|---|
| Retry logic (3 attempt, 5s delay, 15s timeout) | `scripts/paper_trading/lib/connection.py:48–108` | DONE (`IBKR Connection Hardening` 2026-02-24) |
| Telegram alert helper | `scripts/paper_trading/lib/connection.py:_send_telegram_alert` | DONE |
| Env var configolhatóság | `IBKR_CONNECT_MAX_RETRIES`, `_RETRY_DELAY`, `_TIMEOUT` | DONE |
| Pre-flight health check script | `scripts/paper_trading/check_gateway.py` | LÉTEZIK (3s timeout, 1 retry) |
| Telegram bot infrastruktúra | `IFDS_TELEGRAM_BOT_TOKEN`, `IFDS_TELEGRAM_CHAT_ID` env | LÉTEZIK |

**Tehát a P1.1 task NEM "új feature építés" — diagnózis + targeted fix az ÖSSZEKAPCSOLÁSI rétegen.**

## 3. A három diagnosztikai hipotézis

### H1 — A Telegram alert nem küldött 2026-05-11-én

Lehetséges okok:
- A `IFDS_TELEGRAM_BOT_TOKEN` és/vagy `IFDS_TELEGRAM_CHAT_ID` env var **nincs beállítva** a production cron environment-ben (`launchd` vagy `crontab -e`). Az `.env` fájl csak a manuális futtatáskor töltődik, a cron-szülő-process környezete eltérő lehet.
- A `_send_telegram_alert()` függvényen belüli `except Exception: pass` **csendesen elnyel** minden hibát — pl. `requests` import error, network error, vagy 4xx response. A 2026-05-11-i logban **NEM látszik** Telegram alert-küldési kísérlet sem (sem sikeres, sem sikertelen).

**Diagnosztika:**

```bash
# A 2026-05-11-i submit_orders log átolvasása
cd ~/SSH-Services/ifds
grep -E "telegram|alert|FAILED" logs/cron_intraday_20260511_*.log | head -20
grep -E "telegram|TELEGRAM" logs/pt_submit_2026-05-11*.log | head -20

# Production env var ellenőrzése (Tamás manuálisan a Mac Mini-n)
launchctl getenv IFDS_TELEGRAM_BOT_TOKEN
launchctl getenv IFDS_TELEGRAM_CHAT_ID
# VAGY ha crontab-ban:
crontab -l | grep -E "IFDS_TELEGRAM|env"
```

**Várt finding:** ha az env varok hiányoznak a cron environmentből, a `_send_telegram_alert` az első `if not token or not chat_id: return` ágon csendesen kilép.

### H2 — A `check_gateway.py` nincs cron-ba kötve, vagy túl későn fut

A `check_gateway.py` 3 másodperces timeout-tal, 1 retry-val gyorsan ellenőriz — DE csak akkor segít, ha **a `submit_orders.py` ELŐTT** fut (pl. 15:30 CEST = 5 perccel a 15:35 CEST IBKR Gateway szokásos restart-ja után, 45 perccel a 16:20 CEST submit előtt). Ha a Gateway 16:00 CEST körül omlott össze (mint 2026-05-11-én), a 15:30-i check már átment.

**Diagnosztika:**

```bash
# crontab-ben vagy launchd-ban van-e check_gateway.py hívás?
crontab -l | grep -E "check_gateway|gateway"
ls -la ~/Library/LaunchAgents/*ifds* 2>/dev/null
# A deploy scriptek átolvasása
grep -rn "check_gateway" scripts/ deploy*.sh 2>/dev/null
```

**Várt finding:** vagy nem fut cron-ban (kell deploy), vagy túl korán fut (kell egy 2. check a submit előtt 5 perccel).

### H3 — A submit_orders.py csendben fail-elt a Telegram alert nélkül

A `connect()` `sys.exit(1)` előtt **megpróbálja** a Telegram alertet, de ha `_send_telegram_alert` exception-t dob és nincs egy második fallback (pl. file-touch + külön cron-monitor), a halál csendes marad.

**Diagnosztika:** ld. H1 — ugyanaz a vizsgálat. Plusz:

```bash
# Volt-e bármi telegram-helper-t használó alert a submit-failure időpontban?
grep -rn "submit_orders\|submit failed\|abort" logs/cron_intraday_20260511_*.log | head -20
```

## 4. Targeted fix javaslat (a diagnózis után)

A diagnózis eredménye alapján a tényleges fix **egyike** vagy **kombinációja**:

### Fix A — Env var sync (ha H1 igazolódik)

A `~/.env` és/vagy a cron environment szinkronizálása. A `launchd` plist-ben explicit `EnvironmentVariables` vagy a cron job előtt egy `source ~/.env && python ...` wrapper.

**Effort:** ~10–15 min (Tamás közreműködésével, mert production env)

### Fix B — Két-fázisú pre-flight (ha H2 igazolódik)

A `check_gateway.py` futtatása **kétszer**:
- 15:30 CEST (early warning): a 16:15-i Phase 4-6 cron előtt 45 perccel
- 16:18 CEST (immediate pre-submit): a 16:20-i `submit_orders.py` előtt 2 perccel — ha itt fail, küldjön sürgős alertet és **bypass-olja** a 16:20 submit-et

A 16:18-i check ára **2-3 perces korábbi figyelmeztetés** — Tamás 55 perc helyett ~30 perc alatt reagálhat.

**Effort:** ~30–45 min (cron entry add + `check_gateway.py` enhancement: Telegram alert FAIL esetén + lockfile a duplázás megelőzésére)

### Fix C — File-based dead-man switch (ha H3 igazolódik)

A `submit_orders.py` indulásakor érintsen meg egy `state/last_submit_attempt.json` fájlt (timestamp), a sikeres befejezésekor egy `state/last_submit_success.json`-t. Egy **független** cron job (16:35 CEST, 15 perccel a tervezett submit után) ellenőrzi:
- Ha `last_submit_attempt > last_submit_success` és a delta > 5 perc → Telegram alert "submit_orders STUCK or FAILED, manual check needed"
- Ha `last_submit_attempt` nem létezik egyáltalán → Telegram alert "submit_orders DID NOT RUN"

Ez a megoldás **nem függ** a `submit_orders.py` belső Telegram képességétől — egy külső monitor.

**Effort:** ~45 min (új script `scripts/paper_trading/monitor_submit_heartbeat.py` + cron entry + 3-4 unit teszt)

**Megjegyzés:** A Fix C koncepciója **swing-architektúrán is releváns** (15:30 CEST entry → 15:50 CEST monitor check), tehát Fázis 3 deploy-után sem avul.

## 5. Implementáció lépésekben

1. **Diagnózis (20–30 min, Mac Mini-n Tamás közreműködésével)**
   - H1/H2/H3 ellenőrzése a fenti `grep`/`launchctl`/`crontab -l` parancsokkal
   - **Output:** rövid finding-jegyzet a task fájl aljára (`## 7. Diagnózis eredménye` szakaszba)
2. **Fix implementáció a finding alapján (30–45 min)**
   - A diagnózis eredményétől függően Fix A, B, vagy C (esetleg több)
   - **Új fájl(ok):** csak ha Fix C — `scripts/paper_trading/monitor_submit_heartbeat.py`
   - **Módosított fájl(ok):** `check_gateway.py` (Telegram alert FAIL esetén — jelenleg `connect()`-ben van, de itt is kell), cron entry-k
3. **Tesztek (15–20 min)**
   - Ha Fix B: `test_check_gateway_fails_with_telegram_alert`, `test_check_gateway_lockfile_prevents_duplicate`
   - Ha Fix C: `test_heartbeat_detects_stuck_submit`, `test_heartbeat_detects_missing_submit`, `test_heartbeat_passes_when_recent_success`
   - Mock Telegram + mock time + mock filesystem
4. **Smoke test (5 min)**
   - `python scripts/paper_trading/check_gateway.py` manuális futtatás Gateway lekapcsolva (Tamás)
   - **Ellenőrzendő:** Telegram alert érkezik
5. **Commit + push (5 min)**

## 6. Tesztek vázlata

```python
# tests/test_ibkr_gateway_monitoring.py

def test_check_gateway_sends_alert_on_failure(monkeypatch):
    """check_gateway.py fail esetén Telegram alert küld (a connect() alerten kívül).

    Jelenleg a connect() küld alertet ha minden retry fail — de a check_gateway-nek
    a saját kontextusát jelző üzenet kell (pl. 'PRE-FLIGHT FAILED').
    """
    ...

def test_heartbeat_detects_stuck_submit(tmp_path, monkeypatch):
    """A heartbeat monitor felismeri, ha last_submit_attempt > last_submit_success."""
    ...

def test_telegram_alert_logged_even_if_send_fails(caplog):
    """A _send_telegram_alert() jelenleg csendben elnyel — legalább logoljon WARNING-ot."""
    ...
```

**Ennek a 3. tesztnek fontos a karaktere**: a `_send_telegram_alert()` jelenlegi `except Exception: pass` mintája **anti-pattern** monitoring kontextusban — egy WARNING log szint nélkül **soha nem fogjuk észrevenni**, ha a Telegram bot leáll. **Tamás 2026-05-15 jóváhagyta a fixet** — a `pass` cseréje `logger.warning(f"Telegram alert send failed: {e}")`-re kötelező változtatás, lásd §11.

## 7. Diagnózis eredménye (kitöltendő CC-által a diagnózis után)

> Itt rögzítse a CC a H1/H2/H3 ellenőrzés eredményét, és melyik Fix-et választotta. Ez a task fájl marad a permanent record-ja a 2026-05-11-i incidens root cause-ának.

### Baseline deploy 2026-05-16 (commit függőben — Ülés A)

A §10 Tamás-jóváhagyott Fix C (file-based heartbeat) és a §11 mandatory
anti-pattern fix **a diagnózistól függetlenül** deploy-olva:

- `scripts/paper_trading/lib/connection.py::_send_telegram_alert`:
  `except: pass` → `logger.warning(...)` (env var hiány, HTTP 4xx, kivétel
  mind WARNING-ként log-olva).
- `scripts/paper_trading/lib/connection.py::connect()`: új
  `context_label` param → az alert üzenet a hívót tükrözi.
- `scripts/paper_trading/check_gateway.py`: `"PRE-FLIGHT Gateway health
  check"` context, hogy a connect()-alert megkülönböztethető legyen.
- `scripts/paper_trading/lib/heartbeat.py`: új modul (atomic write,
  `touch`/`read` API).
- `scripts/paper_trading/submit_orders.py`: `heartbeat_touch("submit_attempt")`
  a `connect()` előtt, `heartbeat_touch("submit_success", extra={...})` a
  `disconnect()` után.
- `scripts/paper_trading/monitor_submit_heartbeat.py`: új független
  cron-monitor (~16:35 CEST javasolt) → OK / STUCK / MISSING / COLD_START.
- 15 új unit teszt `tests/test_ibkr_gateway_monitoring.py`-ban (1567 → 1582).

### Mac Mini diagnózis eredménye (2026-05-16, Tamás)

**H1 — Telegram alert (igazolt):** a `cron_intraday_20260511_161500.log`
**KIZÁRÓLAG** `IBKR connection attempt N/3 FAILED (clientId=10)` + `IBKR
connection FAILED after 3 attempts` sorokat tartalmaz — **semmilyen**
`telegram` vagy `TELEGRAM` log entry, sem siker, sem hiba. A
`_send_telegram_alert()` SOHA nem ért el a `requests.post()`-ig az
incidens idején. Két lehetséges ok:

  - **(a)** A `.env`-ben 2026-05-11-én még nem voltak a Telegram
    tokenek, és a függvény az `if not token or not chat_id: return`
    ágon csendesen kilépett.
  - **(b)** A tokenek megvoltak, de a `requests.post` HTTP 4xx vagy
    network error-ba futott, és az `except Exception: pass` elnyelte.

A §11 fix után **mindkét eset** mostantól visible:
`logger.warning("Telegram alert NOT sent: ...")` vagy
`logger.warning("Telegram alert send failed: HTTP ...")`.

**H2 — check_gateway timing (részleges):** crontab tartalmazza:

```
0 16 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/check_gateway.py
```

A check 16:00 CEST-kor fut → 20 perccel a 16:20-i `submit_orders.py`
cron előtt. A gateway 16:00–16:20 közötti összeomlása esetén a
check átment, de a submit fail-elt — pontosan ez történt 2026-05-11-én.

**H3 — silent submit fail:** H1+H2 következménye. A 2026-05-11-i
16:20 submit fail-elt, és mivel a Telegram alert sem ment ki (H1),
Tamás csak 17:15-kor (55 perccel később) észlelte kézzel.

### Fix verdikt

| Fix | Szükséges? | Indoklás |
|---|---|---|
| §11 anti-pattern (`logger.warning`) | ✅ DEPLOY (5/16) | Mostantól H1 mindkét ágán látható |
| §10 Fix C (heartbeat) | ✅ DEPLOY (5/16) | A heartbeat-monitor a primary out-of-band detect |
| Fix A (env sync) | ❌ NEM | `load_dotenv()` minden script-ben → `.env` szinkron elegendő |
| Fix B (két-fázisú pre-flight 16:18) | ⚠️ HALASZTVA | Az átállás-előtti ~20 nap alatt a heartbeat-monitor 16:35-kor 15 perces detect-késleltetéssel elegendő. A swing pivot 15:30 CEST entry-vel (Day 63 §3.6) az új cron-ütemezés más lesz — Fix B akkor újraértékelendő. |

### Új cron entry javaslat (Mac Mini, Tamás)

```cron
# IBKR submit heartbeat monitor — 16:35 CEST, 15 min after submit_orders cron
35 16 * * 1-5 cd ~/SSH-Services/ifds && source .env && python scripts/paper_trading/monitor_submit_heartbeat.py >> logs/heartbeat_monitor_$(date +\%Y\%m\%d).log 2>&1
```

## 8. Commit message draft

```
feat(monitoring): IBKR Gateway pre-flight + heartbeat alerting

Root cause of 2026-05-11 silent failure: <H1 / H2 / H3>

Fix: <A / B / C kombinációja>

- <konkrét lista>
- <konkrét lista>

The change closes 04-risks §1.1 (operational risk).
The same monitoring stack carries over to the swing pivot architecture
(Phase 3, ~2026-06-23) — 15:30 CEST entry has the same Gateway dependency.

Tests: <N új unit teszt>

Refs: docs/decisions/2026-05-14-day63-decision-outcome.md §6.1
```

## 9. Out of scope (explicit)

- **Új monitoring framework** (Prometheus, Grafana, stb.) — overkill egy 1-machine paper trading rendszerhez
- **IBKR Gateway automatikus újraindítása** — túl invazív, manuális Tamás-művelet marad
- **Multi-channel alerting** (SMS, email) — a Telegram bot elegendő, ha tényleg működik
- **Cron-monitoring framework** (Healthchecks.io, Cronitor) — Fázis 3 deploy-jal együtt érdemes nézni, most a meglévő stack-be illeszkedés a prioritás

## 10. Döntések (Tamás 2026-05-15)

- **Fix C (file-based heartbeat) Fázis 1-ben megéri** — a diagnózistól függetlenül implementálandó (low effort, fail-safe redundancia). Fázis 3 deploy-jal (≈jún 23) újraértékelendő.
- **`_send_telegram_alert` anti-pattern fix kötelező** — a jelenlegi `except Exception: pass` minimum `logger.warning(f"Telegram send failed: {e}")`-re cserélendő. Ezt **a diagnózis előtt** módosítja a CC, mert ez maga is hozzájárul a 2026-05-11-i csendes failure-hoz (ha a Telegram nem ment, soha nem fogjuk megtudni a logból). Lásd új §11.

## 11. Mandatory anti-pattern fix — Telegram silent swallow

**Hely:** `scripts/paper_trading/lib/connection.py:_send_telegram_alert()`

**Jelenlegi (anti-pattern):**
```python
try:
    requests.post(..., timeout=5)
except Exception:
    pass  # Telegram failure must never block
```

**Kötelező csere:**
```python
try:
    response = requests.post(..., timeout=5)
    if response.status_code >= 400:
        logger.warning(
            f"Telegram alert send failed: HTTP {response.status_code} — {response.text[:200]}"
        )
except Exception as e:
    logger.warning(f"Telegram alert send failed: {e}")
```

**Indoklás:** a Telegram failure soha nem blokkolhat (`sys.exit(1)` továbbra is fut), de **láthatóvá kell tenni** a logban. Enélkül a 2026-05-11-i incidens root cause-a nem megállapítható, és a jövőbeli hasonló esetek is csendben maradnak.

A hibakezelő nem reraise-el — csak logol. A `connect()` függvény továbbra is fut a `sys.exit(1)` felé.

## Kapcsolódó

- `scripts/paper_trading/lib/connection.py` — meglévő retry + Telegram alert
- `scripts/paper_trading/check_gateway.py` — meglévő pre-flight
- `docs/review/2026-05-11-daily-review.md` — az incidens dokumentációja
- `docs/master-reference/04-risks-and-open-questions.md` §1.1
- `docs/tasks/2026-02-24-ibkr-connection-hardening.md` — az előzmény task (DONE)
