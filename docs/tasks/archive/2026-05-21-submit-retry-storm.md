# Task: Submit Orders — Autonomous Retry on IBKR Gateway Disconnect

Status: DONE
Updated: 2026-05-21
Note: Implementálva (~2.5h CC). `lib/retry_orchestrator.py` IBKRSubmitOrchestrator class + `lib/connection.py` IBKRConnectionExhausted exception + `raise_on_exhaust` kwarg + submit_orders.py `--resume` flag + orchestrator integration + monitor_submit_heartbeat.py STUCK threshold 300s → 900s. **+9 új unit test** (test_retry_orchestrator.py: happy path, retry success, exhausted+Telegram, non-retryable propagate, gateway probe gating, backoff schedule, state reload, telegram failure non-blocking). 1747 → **1756 passing**, 0 regression. Day 3 (2026-05-20) Gateway-down forgatókönyv autonóm módon kezelt: 5 attempt × exponential backoff (15s → 240s) = ~7.75 min outer retry window.

**Priority:** P0 (NEM hotfix — Day 5 vagy következő hét)
**Created:** 2026-05-21
**Owner:** Claude Code
**Estimated effort:** ~3-4h CC (logic + retry framework + tests + Telegram integration)

**Source incident:** [`docs/review/2026-05-20-daily-review.md`](../review/2026-05-20-daily-review.md) §6 §0.5 — Day 3 (2026-05-20) submit retry storm, 5 attempt 35 perc alatt.

**Depends on:** —

**NOT a hotfix because:** A Day 3-i incidens **Tamás manuális trigger**-rel megoldódott (16:05 reggel resubmit attempt sikerült), és a `submit_orders.py` jelenlegi silent retry mechanikája **3/3 nap 100% rátán** sikeresen handle-eli az Error 10349 TIF Cancellation-eket. A sürgősebb a sector cap hotfix (lásd `2026-05-21-sector-cap-hotfix.md`). Ez a task **strukturális javítás**, ami a manuális intervenció szükségét eliminálja jövőre.

---

## 1. A probléma

Day 3 (2026-05-20) reggel a `submit_orders.py` cron run **5 különböző attempt-en** futott le 35 perc alatt:

| Időpont | Esemény | Eredmény |
|---------|---------|----------|
| 15:31:01 | 1. cron attempt | Csak `Reading: execution_plan...` — folyamat megszakítva |
| 15:51:53 | 2. attempt (manuális trigger?) | `[DRY RUN] — No IBKR connection` ⚠️ |
| 15:52:14 | 3. attempt | Error 10349 mindhárom új ticker-re (VLO, ON, CNC) |
| **16:05:19** | **4. attempt** | **Sikeres** (mind a 3 entry beadva) ⭐ |
| 16:20:44 | 5. attempt (duplikált) | Mind a 3 már nyitva, csak ismétlés |

**Plus**: a `pt_heartbeat_monitor_2026-05-20.log` 15:45:03-on:
```
[STUCK] submit_orders STUCK: attempt at 2026-05-20T13:31:01+00:00 is 86455s newer than
last success at 2026-05-19T13:30:06+00:00 (threshold 300s)
```

**Pipeline timeline rekonstrukció:**
1. **15:25 CEST**: IBKR Gateway preflight OK (a `pt_gateway_2026-05-20.log` szerint)
2. **15:31:01**: A 14:30:00 cron-időpont submit attempt-je elindult, IBKR-be csatlakozott, **DE a folyamat megszakadt** valami exception miatt (a log csak `Reading: execution_plan...` szöveget mutat, a `Submitted: X tickers` befejezés hiányzik)
3. **15:45-15:50 CEST körül**: az IBKR Gateway-kapcsolat megszakadt (a `[DRY RUN] — No IBKR connection` 15:51:53-on bizonyítja ezt)
4. **15:45:03**: a `pt_heartbeat_monitor` detektálta a "STUCK" állapotot (Telegram alert?), mert a `last_success` 24 órával régebbi (Day 2 utolsó sikeres submit)
5. **15:51:53 → 15:52:14**: Tamás manuális trigger debug-szerű attempt-eket (DRY RUN majd live submit)
6. **15:49:48 + 16:04:52**: 2 további gateway preflight OK
7. **16:05:19**: Tamás manuális resubmit sikeres
8. **16:20:44**: Duplikált 5. attempt (state-tudatlan re-run)

## 2. Root cause analysis

### (A) A 15:31:01 első attempt **exception** miatt megszakadt

A log szerint csak `Reading: execution_plan_run_20260520_123000_4ac59f.csv` szöveg jelenik meg, és **NEM** `[SWING] Submitted: X tickers` befejező sor. Hipotézis: az `submit_orders.py` valami exception-t dobott a `Reading` lépés és a `Submitting` lépés között.

**Lehetséges okok:**
- IBKR Gateway megszakadt (de a 15:25 preflight OK volt)
- TWS API timeout
- Network error
- Adatfájl olvasási hiba (`execution_plan` CSV)

**Vizsgálandó:** a `cron_intraday_20260520_*.log` (a `submit_orders.py` parent cron log) tartalmazhat-e exception traceback-et.

### (B) Az `submit_orders.py` NINCS autonóm retry logikával

A jelenlegi `submit_orders.py` viselkedés: ha az IBKR connection fail-el, akkor:
1. Logol egy WARNING-ot
2. **Visszatér** a függvényből / processz exitel
3. **NEM próbálkozik újra** autonóm módon
4. A heartbeat monitor **detektálja a STUCK állapotot** 14 perccel később, és Telegram alert-et küld
5. **Az operátor (Tamás) manuálisan triggereli a resubmit-et**

Ez **NEM SCALABLE**: minden IBKR Gateway megszakadás (ami egy elosztott rendszerben elkerülhetetlen) **emberi intervenciót igényel**. Live trading deploy-nál (Day 126+) ez **kockázat**.

### (C) A 16:20:44 duplikált 5. attempt — state-tudatlan re-run

A `pt_submit_2026-05-20.log` 16:20:44-i log entry szerint:
```
16:20:48 VLO: MKT BUY 16 @ ~$262.62 | stop $244.71 | TP1 $276.05 | TP2 $289.48
16:20:50 ON: MKT BUY 27 @ ~$106.02 | stop $93.50 | TP1 $115.41 | TP2 $124.80
16:20:51 CNC: MKT BUY 95 @ ~$59.15 | stop $55.50 | TP1 $61.89 | TP2 $64.63
16:20:51 [SWING] Submitted: 3 tickers | State: state/swing_positions.json (7 open)
```

**DE a 16:05:19 attempt-ben a 3 ticker MÁR sikeresen submitted volt** (`[SWING] Submitted: 3 tickers | State: state/swing_positions.json (7 open)` — szintén 7 open!). A 16:20:44 attempt **újra logolja ugyanazt**, de a state szerint **nem történt double-submit** (a `swing_positions.json` ugyanazt a 7 pozíciót tartalmazza Day 3 záró).

**Hipotézis**: a 16:20:44 attempt egy `submit_orders.py` reentrant futás, ami a már létező pozíciókat **felismeri** (`Existing IBKR positions/orders: {'MASI', 'EC', 'PFGC', 'LBRT'}` log szerint — bár ez **csak a 4 régi pozíciót** tartalmazza, NEM a friss 3 új-at). **Lehet, hogy a state-ellenőrzés cache-elt vagy stale**.

## 3. Megoldás javaslat

### 3.1. Autonóm retry logika a `submit_orders.py`-ban

```python
import asyncio
from typing import Optional

class IBKRSubmitOrchestrator:
    """Wrapper a submit_orders.py főlogika köré autonóm retry-jal."""

    MAX_ATTEMPTS = 5
    INITIAL_BACKOFF_SECONDS = 15  # 15s első retry, 30s második, 60s harmadik, exponential

    async def submit_with_retry(self, plan: ExecutionPlan) -> SubmitResult:
        """Submit orders with autonomous retry on IBKR connection failure."""
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                # 1. Preflight: Gateway connection check
                if not await self.check_gateway_alive():
                    logger.warning(
                        f"[RETRY {attempt}/{self.MAX_ATTEMPTS}] Gateway not alive. "
                        f"Backing off {self._backoff(attempt)}s..."
                    )
                    await asyncio.sleep(self._backoff(attempt))
                    continue

                # 2. Tényleges submit
                result = await self._do_submit(plan)
                logger.info(
                    f"[SUBMIT_OK attempt={attempt}] {len(result.filled)} tickers filled"
                )
                return result

            except IBKRConnectionError as exc:
                last_exception = exc
                logger.warning(
                    f"[RETRY {attempt}/{self.MAX_ATTEMPTS}] IBKRConnectionError: {exc}. "
                    f"Backing off {self._backoff(attempt)}s..."
                )
                await asyncio.sleep(self._backoff(attempt))

            except Exception as exc:
                # Nem retry-able exception (pl. config error, malformed plan)
                logger.error(f"[SUBMIT_FATAL attempt={attempt}] {exc}")
                raise

        # All retries exhausted
        logger.error(
            f"[SUBMIT_FAILED] All {self.MAX_ATTEMPTS} attempts failed. Last: {last_exception}"
        )
        await self._notify_telegram_failure(last_exception)
        raise SubmitExhaustedError(f"Max retries ({self.MAX_ATTEMPTS}) exhausted")

    def _backoff(self, attempt: int) -> int:
        """Exponential backoff: 15s, 30s, 60s, 120s, 240s."""
        return self.INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))

    async def check_gateway_alive(self) -> bool:
        """Quick health check (NOT full preflight)."""
        try:
            # ib_insync connection ping
            await self.ib.connectAsync(timeout=5)
            return self.ib.isConnected()
        except Exception:
            return False

    async def _notify_telegram_failure(self, exc: Exception) -> None:
        """Final Telegram alert if all retries exhausted."""
        await self.telegram.send_critical(
            f"🚨 SUBMIT EXHAUSTED — manuális intervenció szükséges\n"
            f"Időpont: {datetime.now(CET).isoformat()}\n"
            f"Last error: {exc}\n"
            f"Manuális resubmit: `python scripts/paper_trading/submit_orders.py --resume`"
        )
```

### 3.2. State-tudatos resubmit (duplikáció elkerülése)

```python
async def _do_submit(self, plan: ExecutionPlan) -> SubmitResult:
    """Tényleges submit, state-tudatos duplikáció-szűréssel."""

    # FRISS state betöltés MINDIG (NEM cache-elt)
    current_positions = load_swing_positions()  # state/swing_positions.json
    existing_tickers = {p.ticker for p in current_positions}

    # Duplikáció szűrése
    to_submit = [c for c in plan.candidates if c.ticker not in existing_tickers]
    skipped = [c for c in plan.candidates if c.ticker in existing_tickers]

    if skipped:
        logger.info(
            f"[STATE_DUPLICATE_SKIP] {len(skipped)} ticker(s) already in state: "
            f"{[s.ticker for s in skipped]}"
        )

    if not to_submit:
        logger.info(f"[SUBMIT] Nothing to submit (all {len(plan.candidates)} already open)")
        return SubmitResult(filled=[], skipped=skipped)

    # ... a meglévő submit logika
```

### 3.3. `--resume` flag a manuális resubmit-hez

A jelenlegi `submit_orders.py`-ban valószínűleg nincs explicit `--resume` mode. A Tamás Day 3-i 15:51:53 manuális trigger valószínűleg egy "újra futtatás" volt. Egy explicit `--resume` mode segítene:

```python
parser.add_argument(
    "--resume",
    action="store_true",
    help="Resume mode: ignore the heartbeat 'STUCK' threshold and re-attempt submit. "
         "Used by operator after manual investigation of a stuck submit.",
)
```

A `--resume` mode-ban:
1. State betöltődik (`state/swing_positions.json`)
2. Az execution plan újraolvasódik
3. **A `existing_tickers` szűrés alapján** csak a hiányzó ticker-ek kerülnek submit-re
4. Az autonóm retry logika fut (3.1 szerint)

### 3.4. Heartbeat monitor finomítás (informational)

A `pt_heartbeat_monitor.py` jelenlegi 300s threshold-ja triggerelte a Day 3-i STUCK alert-et. A retry logika bevezetésével a heartbeat threshold **emelhető 600s vagy 900s-ra** (mert az 5 retry × 240s exponential backoff = 1200s max), hogy a heartbeat **NE** triggerelje a Telegram alert-et **közben** a retry-logika fut.

```python
# pt_heartbeat_monitor.py config
STUCK_THRESHOLD_SECONDS = 900  # was: 300, increased to accommodate autonomous retries
```

## 4. Test scenarios

### Unit tests (`tests/test_submit_orders.py`)

```python
@pytest.mark.asyncio
async def test_retry_on_gateway_disconnect():
    """Mocked IBKR connection drops on attempts 1-2, succeeds on attempt 3."""
    mock_ib = MockIBKR(fail_attempts=[1, 2], succeed_from=3)
    orchestrator = IBKRSubmitOrchestrator(ib=mock_ib)
    result = await orchestrator.submit_with_retry(plan=mock_plan)
    assert result.filled == ["VLO", "ON", "CNC"]
    assert mock_ib.attempt_count == 3

@pytest.mark.asyncio
async def test_retry_exhausted_telegram_alert():
    """All 5 attempts fail, Telegram alert sent."""
    mock_ib = MockIBKR(fail_attempts=[1, 2, 3, 4, 5])
    orchestrator = IBKRSubmitOrchestrator(ib=mock_ib)
    with pytest.raises(SubmitExhaustedError):
        await orchestrator.submit_with_retry(plan=mock_plan)
    assert mock_telegram.critical_sent == 1

@pytest.mark.asyncio
async def test_resume_mode_skips_existing():
    """Resume mode: 3 candidates, 1 already in state, 2 to submit."""
    state = [SwingPosition(ticker="VLO", ...)]  # VLO already open
    plan = ExecutionPlan(candidates=["VLO", "ON", "CNC"])
    result = await orchestrator.submit_with_retry(plan=plan, resume=True)
    assert sorted([c.ticker for c in result.filled]) == ["CNC", "ON"]
    assert sorted([c.ticker for c in result.skipped]) == ["VLO"]
```

### Integration tests (paper trading scenario)

A `tests/test_pipeline_e2e.py`-ban:
- `@patch("ifds.exec.submit_orders.IBKRConnection")` — mocked Gateway disconnect
- Verify: autonomous retry kicks in, no manual intervention required

## 5. Risk if NOT deployed (Day 5+)

- A Day 3 incidens **megismétlődhet** bármelyik nap, ha az IBKR Gateway megszakad 15:30 körül
- Minden megismétlődéskor **Tamás manuális intervenciója szükséges** (Telegram alert-re reagálva)
- Live trading deploy-nál (Day 126+) **a manuális trigger NEM elérhető éjjel-nappal**, és az automatizált stratégia **kihagyhat egy fontos entry-t**

**Day 4 reggelre NEM kritikus**, mert a Day 3-i manuális megoldás-pattern **valószínűleg újra működik** (Tamás aktív a 15:30 ablakban).

## 6. Acceptance criteria

- [ ] `IBKRSubmitOrchestrator` class implementálva `submit_with_retry()` metódussal
- [ ] Exponential backoff 5-attempt logika (15s → 240s)
- [ ] State-tudatos duplikáció-szűrés (existing_tickers check)
- [ ] `--resume` CLI flag a manuális retry-hez
- [ ] Telegram critical alert all-retries-exhausted esetén
- [ ] Heartbeat threshold 300s → 900s frissítve
- [ ] Unit tests passing (3 új test minimum)
- [ ] Integration test passing
- [ ] Documentation: `docs/master-reference/01-system-snapshot.md` szekció frissítve a submit retry logikával

## 7. Commit message (a teljes feature-re)

```
feat(submit_orders): autonomous retry on IBKR Gateway disconnect

Day 3 (2026-05-20) revealed that submit_orders.py has no autonomous
retry logic when the IBKR Gateway connection drops mid-submit.
The Day 3 incident required 5 manual attempts over 35 minutes,
triggered by a heartbeat 'STUCK' alert to the operator.

Changes:
- IBKRSubmitOrchestrator class with submit_with_retry() method
- Exponential backoff: 15s, 30s, 60s, 120s, 240s (5 attempts max)
- State-aware deduplication: load swing_positions.json each attempt,
  skip tickers already in IBKR
- --resume CLI flag for explicit manual retry mode
- Telegram critical alert if all retries exhausted (operator notified)
- Heartbeat threshold increased from 300s to 900s to accommodate
  the new autonomous retry window

Tests: 3 new unit tests + 1 integration test cover Gateway-disconnect
scenarios. Existing tests pass with no regression.

Refs: docs/review/2026-05-20-daily-review.md §6 §0.5
Refs: docs/tasks/2026-05-21-submit-retry-storm.md
```

## 8. Followup (post-merge, informational)

A `pt_heartbeat_monitor` Telegram alert formátum **dokumentálandó** a `docs/master-reference/01-system-snapshot.md`-be:
- Mikor küld `[STUCK]` alertet?
- Milyen küszöb-időtartam (300s, vagy az új 900s)?
- Mit kell tennie az operátornak a Telegram alert vételekor?
- Plus a `--resume` flag használati módja Telegram-alert-utáni reagáláskor.

Ez **NEM blokkolja** a fő implementációt, csak post-merge documentation update.
