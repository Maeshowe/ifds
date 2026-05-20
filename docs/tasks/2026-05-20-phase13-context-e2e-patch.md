# Task: save_phase13_context e2e Patch (Proaktív Sink Audit Lezárás)

Status: DONE
Updated: 2026-05-20
Note: Defensive @patch hozzáadva mindkét meglévő e2e stack-hez + új dedikált test_phase13_context_save_is_mocked teszt (phase=(1,3) tuple form). 1745 → 1746 passing. Finding: a meglévő e2e tesztek phase=None-nal hívnak run_pipeline-t, ami a runner line 285 `isinstance(phase, tuple)` guard miatt SOHA nem triggereli save_phase13_context-et — ezért a "mock_called assert" csak a dedikált új tesztben él, nem a meglévő flow tesztekben (=  +1 új teszt, nem +2 mint a task spec sugallt).

**Priority:** P2 (proaktív, NEM aktív pollution incidens)
**Created:** 2026-05-20
**Owner:** Claude Code
**Estimated effort:** ~15 min CC

**Source**:
- [`docs/master-reference/04-risks-and-open-questions.md`](../master-reference/04-risks-and-open-questions.md) §8.1.6, §8.1.9 audit-szabály
- Day 2 (2026-05-19) `runner.py` sink-audit: 5 sink, 4 már patch-elt (`save_phase4_snapshot`, `write_shadow_snapshot`, `write_full_scan_matrix`, `write_trade_plan`), 1 patch-eletlen (`save_phase13_context`)

---

## 1. A probléma

A `src/ifds/pipeline/runner.py` `save_phase13_context(ctx)` hívása **implicit production path-ra** ír (`state/phase13_ctx.json.gz`). A `tests/test_pipeline_e2e.py` `test_full_pipeline_flow` és `TestSnapshotIsolation` mindkét test a `run_pipeline()` teljes flow-ját futtatja, **DE** a `save_phase13_context`-et **NEM mockolja** — ami pytest pre-flight pollution-risket jelent.

**Strukturális risk**: ha bárki `pytest`-et futtat a Mac Mini-n a vasárnap 22:00 cron-ablak előtt, a pytest pre-flight a `state/phase13_ctx.json.gz`-t mock universe-szel felülírhatja → a Phase 4-6 cron a következő héten **kompromittált context-tel** dolgozna.

**Aktuális status**: a `daily_metrics_2026-05-19.json` 96-os qualifying ticker count azt sugallja, hogy eddig **nem történt pollution** (vagy ha igen, akkor minimális). Tamás manuálisan ellenőrizheti a `state/phase13_ctx.json.gz` mtime-jét:
```bash
ls -la state/phase13_ctx.json.gz
# Várt: 2026-05-19 16:40 körül (manuális Phase 1-3 vége)
```

A patch **proaktív** — strukturális risk-megelőzés, NEM aktív incidens kezelése.

## 2. Megoldás

Adj hozzá `@patch("ifds.pipeline.runner.save_phase13_context")` decorator-t mindkét e2e patch-stack-be a `tests/test_pipeline_e2e.py`-ben.

**A tényleges modul-path verifikálandó**:
```bash
grep -n "from .* import save_phase13_context\|import save_phase13_context" src/ifds/pipeline/runner.py
# A grep output dönti el a `@patch` target-et:
# - "from ifds.data.phase13_ctx import save_phase13_context"  → @patch("ifds.data.phase13_ctx.save_phase13_context")
# - "from ifds.pipeline.context import save_phase13_context"  → @patch("ifds.pipeline.context.save_phase13_context")
# - vagy "ifds.pipeline.runner.save_phase13_context" ha runner.py közvetlenül definiálja
```

### 2.1. `test_full_pipeline_flow` (sor ~202-204 körül)

```python
@patch("ifds.output.execution_plan.write_trade_plan", return_value="/tmp/trade.csv")
@patch("ifds.output.execution_plan.write_full_scan_matrix", return_value="/tmp/scan.csv")
@patch("ifds.output.execution_plan.write_execution_plan", return_value="/tmp/test.csv")
@patch("ifds.data.uw_shadow.write_shadow_snapshot")  # 1eb9755
@patch("<modul-path>.save_phase13_context")            # ← ÚJ
def test_full_pipeline_flow(self, mock_save_phase13, mock_write_shadow, ...):
    # ...
    assert mock_save_phase13.called  # ← ÚJ defenzív assert
```

### 2.2. `TestSnapshotIsolation` (sor ~270-272 körül)

```python
@patch("ifds.output.execution_plan.write_trade_plan", return_value="/tmp/t.csv")
@patch("ifds.output.execution_plan.write_full_scan_matrix", return_value="/tmp/s.csv")
@patch("ifds.output.execution_plan.write_execution_plan", return_value="/tmp/p.csv")
@patch("ifds.data.uw_shadow.write_shadow_snapshot")
@patch("<modul-path>.save_phase13_context")            # ← ÚJ
def test_snapshot_isolation(self, mock_save_phase13, mock_write_shadow, ...):
    # ...
    assert mock_save_phase13.called  # ← ÚJ
```

## 3. Verifikáció

Fix előtt:
```bash
# Egyszeri ellenőrzés: a pytest pre-flight valóban felülírja-e?
# (Csak ha Tamás kíváncsi a kvantitatív validációra)
ls -la state/phase13_ctx.json.gz  # mtime előtte
pytest tests/test_pipeline_e2e.py -v
ls -la state/phase13_ctx.json.gz  # mtime utána — ha változott, a pollution igazolt
```

Fix után:
```bash
ls -la state/phase13_ctx.json.gz  # mtime előtte
pytest tests/test_pipeline_e2e.py -v
ls -la state/phase13_ctx.json.gz  # mtime UGYANAZ — a pollution megakadályozva
```

Test suite: **1745 → ~1747 passing** (+2 mock_called assert).

## 4. Commit message

```
chore(tests): proaktív save_phase13_context e2e patch (sink audit lezárás)

A 2026-05-19 Day 2 runner.py sink-audit 5 sink-et azonosított:
- save_phase4_snapshot       ✅ patch-elt (d3fce73)
- write_shadow_snapshot      ✅ patch-elt (1eb9755, Task #G)
- write_full_scan_matrix     ✅ patch-elt (korábbi)
- write_trade_plan + write_execution_plan ✅ patch-elt (korábbi)
- save_phase13_context       ❌ patch-eletlen volt — EZ A FIX

Strukturális risk: pytest pre-flight a state/phase13_ctx.json.gz-t
mock universe-szel felülírhatta volna, a heti rebalance source-of-truth
kompromittálva → Phase 4-6 a következő héten rossz contexten dolgozna.

NEM aktív pollution incidens — proaktív audit-szabály alkalmazás
(§8.1.6 + §8.1.9 audit szabály).

Tests: 1745 → 1747 (+2 mock_called assert mindkét e2e stack-en).

Refs: docs/master-reference/04-risks-and-open-questions.md §8.1.6, §8.1.9
      docs/tasks/2026-05-20-phase13-context-e2e-patch.md
```

## 5. Out of scope (Fázis 4 backlog)

A 3-5 különálló `@patch` decorator hosszú távon **fragile minta**. **Strukturális megelőzés** (Fázis 4 scope):

- **Production path env var** — pl. `IFDS_STATE_DIR` env var, ami `defaults.py`-ben `state/`-re defaultál, de `conftest.py` `autouse=True` fixture a `tmpdir`-re bind-eli
- Effort: ~2-3 óra CC (általános refactor)
- Risk: közepes (ha rosszul implementálva, **minden** production path-ot érint)

Ezt **NEM most** — most a §8.1.6/§8.1.9 minta szerinti targeted `@patch` elég.

## 6. Kapcsolódó

- `tests/test_pipeline_e2e.py` (módosítandó)
- `src/ifds/pipeline/runner.py` (`save_phase13_context` hívási hely)
- `04-risks` §8.1.6 (audit szabály), §8.1.9 (UW shadow precedens)

## 7. Végrehajtás (2026-05-20, CC)

### Verifikált modul-path

```bash
grep -n "save_phase13_context" src/ifds/pipeline/runner.py
# 286:  from ifds.pipeline.context_persistence import save_phase13_context
# 287:  save_phase13_context(ctx)
```

A `runner.py` line 286 **lazy import**-ot használ a függvénytörzsből → patch a **source**-on (`ifds.pipeline.context_persistence.save_phase13_context`), nem a runner-en (a project rule szerint).

### Finding: meglévő e2e tesztek NEM triggerelik a save_phase13_context-et

```python
# runner.py:285
if isinstance(phase, tuple) and phase[1] <= 3:
    save_phase13_context(ctx)
```

A `test_full_pipeline_flow` és `test_save_snapshot_is_mocked_in_e2e` mindkettő `run_pipeline()`-t hív (default `phase=None`) → `isinstance(phase, tuple)` **False** → `save_phase13_context` NEM hívódik meg. Ezért a task spec §3 javasolt `mock_save_phase13.called` assert a meglévő tesztekben **mindig FALSE** lenne és buktatná a tesztet.

### Megoldás

1. **Defenzív `@patch`** mindkét meglévő e2e stack-be (`test_full_pipeline_flow`, `test_save_snapshot_is_mocked_in_e2e`) — risk-prevention jövőbeli refactor ellen, ha valaha tuple phase-szel hívják a flow-t.

2. **Új dedikált teszt** `TestSnapshotIsolation::test_phase13_context_save_is_mocked` — `run_pipeline(phase=(1, 3))` hívás, ami ténylegesen triggereli a save_phase13_context-et + `assert mock_save_phase13.called` regressziós védelem.

3. Mock parameter `mock_save_phase13` hozzáadva a function signature-ekhez.

### Verifikáció (Fix után)

```
$ stat state/phase13_ctx.json.gz  # before
May 19 16:40:48 2026, 2419 bytes
$ pytest tests/test_pipeline_e2e.py -v
8 passed (was 7)
$ stat state/phase13_ctx.json.gz  # after
May 19 16:40:48 2026, 2419 bytes  ✓ NEM változott (no pollution)
```

**Test deltas**: 1745 → 1746 passing (+1, NEM +2 mint a spec; lásd finding fent).

### A 5 sink végső állapota (Task #H után)

| Sink | Patch commit |
|---|---|
| `save_phase4_snapshot` | ✅ `d3fce73` |
| `write_shadow_snapshot` | ✅ `1eb9755` (Task #G follow-up) |
| `write_full_scan_matrix` | ✅ korábbi |
| `write_trade_plan` | ✅ korábbi |
| `write_execution_plan` | ✅ korábbi |
| `save_phase13_context` | ✅ Task #H (ez a commit) |

**6 sink, 6 patch** — strukturálisan teljes körű. A pytest pre-flight pollution kockázata a `runner.py` teljes scope-jában lezárt.
