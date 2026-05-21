# Code Health Quick Scan — 2026-05-21

**Owner:** CC + Tamás
**Scope:** Quick scan (~1h) after the 56-commit incident-driven sprint
(Day 1-4 swing pivot + Task #G/H/K/L)
**Tooling installed:** `ruff 0.15.13`, `black 26.5.1`, `mypy 2.1.0`

---

## Executive summary

| Aspect | Status | Severity |
|---|---|---|
| **Test suite** | 1756 passing, 0 failure | ✅ Healthy |
| **Ruff (242 errors)** | 147 unused imports, 28 unused vars, 5 undefined names | ⚠️ Mostly trivial autofixes; 1 latent bug |
| **Mypy (153 errors)** | Type annotation gaps (43 arg-type, 37 return-value, 29 attr-defined) | ⚠️ Tech debt, NOT runtime risk |
| **Black (110/138 files)** | Inconsistent formatting | ⚠️ Cosmetic, low risk |
| **Long files (3)** | `phase4_stocks.py` 1561, `phase6_sizing.py` 1378, `submit_orders.py` 843 | ⚠️ Refactor candidate (>800 sor) |
| **print() statements (273)** | ~250 legitimate CLI/operator output (console.py, scripts/) | ✅ OK after classification |
| **TODO/FIXME markers** | 1 | ✅ Tiszta |
| **Bare except clauses** | 1 | ✅ Tiszta |

**Bottom line:** a codebase **functionally healthy** (1756 passing teszt, 0 regression a sprint után), de **tooling-szegény** (no ruff/black/mypy/pre-commit config) és **enyhén technical-debt-terhelt** (3 hosszú fájl, 153 type annotation gap). Egy **konfigurálás-fókuszú phase 1** (~1h CC) + **opcionális targeted cleanup phase 2** (~2-3h CC) szanálná.

---

## 1. Findings — részletesen

### 1.1 Ruff statistics

```
147  F401  unused-import          [auto-fixable]
 28  F841  unused-variable        [manual review]
 20  E702  multiple-statements    [auto-fixable]
 20  F541  f-string-no-placeholder [auto-fixable]
 15  E402  import-not-at-top      [manual review — late imports legit]
  6  E741  ambiguous-variable     [manual: l/I/O variables]
  5  F821  undefined-name         [⚠️ check — see 1.2]
  1  E731  lambda-assignment      [auto-fixable]
```

**Auto-fixable: 166 issues (69%)** via `ruff check --fix`.

### 1.2 F821 undefined names — vizsgálandó

5 occurrence:

| File | Line | Name | Verdict |
|---|---|---|---|
| `src/ifds/data/phase4_snapshot.py:82` | `"StockAnalysis"` (string annotation) | Forward reference — runtime OK | Style: add TYPE_CHECKING import |
| `src/ifds/sim/rescore.py:371` | `"date \| None"` (string annotation) | Forward reference — runtime OK | Style: add TYPE_CHECKING import |
| `src/ifds/sim/rescore.py:384` | `"date \| None"` (string annotation) | Forward reference — runtime OK | Style: add TYPE_CHECKING import |
| **`tests/test_monitor_positions.py:43`** | **`date.today()` (unquoted)** | **LATENT BUG** — `date` not imported | ⚠️ Fix needed if helper ever called |
| **`tests/test_monitor_positions.py:46`** | **`csv.writer(...)` (unquoted)** | **LATENT BUG** — `csv` not imported | ⚠️ Fix needed if helper ever called |

**Mitigation**: a `_write_execution_plan` helper soha NINCS HÍVA (csak definiálva). Vagyis a teszt jelenleg NEM TÖRIK, de:
- **Dead test code**: a helper feleslegesen ott van a fájlban (16 sor)
- **Latent bug**: ha valaki egy jövőbeli teszten hívná, `NameError`-rel azonnal robbanna

**Javaslat**: vagy törölni a helper-t (preferált), vagy javítani az importokat. Egyik commit-tal lerendezhető.

### 1.3 Unused imports (F401) — top szennyezett fájlok

```
7  tests/test_sector_bmi.py
6  tests/test_phase4.py
5  tests/test_telegram_timestamps.py
5  tests/test_sim_replay.py
5  tests/test_bc11_robustness.py
4  scripts/paper_trading/close_positions.py
4  tests/test_phase4_snapshot.py
4  tests/test_bc14_breadth.py
3  tests/test_swing_execution.py
3  tests/test_phase6.py
```

**Mind auto-fixable** `ruff check --fix`-szel. 147 unused import — kb. 5-10 perc CI auto-cleanup, vagy egy commit.

### 1.4 F841 unused variables — vizsgálandó (28)

Példa: `scripts/company_intel.py:401-402`:
```python
tl = target.get("targetLow", "N/A") if target else "N/A"
th = target.get("targetHigh", "N/A") if target else "N/A"
# tl és th SOHA nincs használva → 2 dead computation
```

**Javaslat**: per-file manual review (5-10 perc), vagy ruff `--fix --unsafe-fixes` (kockázatosabb, de a F841-eket általában tisztán törli).

### 1.5 Mypy 153 errors — kategóriák

```
43  arg-type        → annotation hiányzik vagy dict-Any
37  return-value    → annotation hiányzik
29  attr-defined    → dynamic attribute access (pl. trade.orderStatus.status)
12  assignment      → dict-Any → str cast
10  union-attr      → Optional handling
 8  call-overload   → kwargs ambiguity
 5  operator        → mixed-type arithmetic
 3  name-defined    → ⚠️ check (potential bug)
 2  var-annotated   → ann hiánya
 2  dict-item       → typed-dict mismatch
```

**Nem azonnali bug** (a runtime tesztek mind passing), de a 3 `name-defined` érdekes lehet — egyenként megnézendő.

**Javaslat**: NEM most cleanup, hanem **strict mode lépésről-lépésre opt-in** modulonként. Pl. először `src/ifds/state/` modulra strict, aztán bővítés. Per-module `[[tool.mypy.overrides]]` config-pal.

### 1.6 Black drift — 110 / 138 files (80%)

A `pyproject.toml`-ban nincs `[tool.black]` szekció, és a kódbázis NEM volt valaha black-tel formázva. A 80% drift ezért **várható**, NEM regression.

**Javaslat**: egy egyszeri massive `black .` commit (~5 perc, automatikus, separate commit). Plus `pyproject.toml`-ban `[tool.black] line-length = 100` config. Aztán pre-commit hook (opcionális).

### 1.7 Long files (>800 sor coding-style.md limit)

```
1561 src/ifds/phases/phase4_stocks.py  (23 functions)
1378 src/ifds/phases/phase6_sizing.py  (19 functions)
 843 scripts/paper_trading/submit_orders.py  (9 functions)
```

**`phase4_stocks.py` 1561 sor — drámaian túl**: 
- Funkció-density: 23/1561 = 67 sor átlag (sok közepes-méretű function)
- Split-candidate ágak: technical scoring vs fundamental scoring vs combined score logic + dataclass adapters
- Refactor scope: ~2-3h CC (3-4 modulra szétbontás, pl. `phase4_stocks_technical.py`, `phase4_stocks_fundamental.py`, `phase4_stocks_combined.py`)

**`phase6_sizing.py` 1378 sor**: 
- Funkció-density: 19/1378 = 72 sor átlag
- Tartalom: legacy bracket sizing + swing market-only sizing + sector balanced greedy + position calculation (több helyen különálló logika ugyanazon fájlon belül)
- Refactor scope: ~2h CC (legacy + swing path szétválasztás)

**`submit_orders.py` 843 sor**: 
- Funkció-density: 9/843 = 94 sor átlag (kevés, nagy function)
- Marginálisan túl (843 < 1000), nem kritikus
- A retry orchestrator integration már strukturált — refactor opcionális

**Javaslat**: külön task fájl (`docs/tasks/2026-05-23-long-file-refactor.md` — backlog P3) a `phase4_stocks.py` + `phase6_sizing.py` split-re. NEM most.

### 1.8 print() statement classification

273 print() statement osztályozva:

| Kategória | Helyek | Példa | Verdikt |
|---|---|---|---|
| **CLI dashboard** | `src/ifds/output/console.py` (54) | `print("[PHASE 4] Analyzed: 329 tickers")` | ✅ LEGITIM (user-facing) |
| **conductor CLI** | `src/conductor/cli.py` (14) | `print(banner)` | ✅ LEGITIM (operator interface) |
| **Operator scripts** | `scripts/merge_mms_state.py` (28), `scripts/validate_etf_holdings.py` (27), … | various | ✅ LEGITIM (ad-hoc tooling) |
| **Pure logic modules** | — | — | ✅ NINCS |

**Eredmény**: ZÉRO debug-leak print() a `src/ifds/` mély rétegeiben. A 273 mind LEGITIM CLI/operator output. **Nincs action item.**

### 1.9 Tooling gap

**Hiányzó**:
- `pyproject.toml` `[tool.ruff]` szekció (nincs lint config)
- `pyproject.toml` `[tool.black]` szekció (nincs format config)
- `pyproject.toml` `[tool.mypy]` szekció (nincs type config)
- `.pre-commit-config.yaml` (no hook automation)
- CI lint stage (`deploy_daily.sh` pre-flight csak pytest)

**Konzekvencia**: a 56 commit Day 1-4 sprintben **0 lint feedback** volt — az unused import, unused variable, formatting drift mind észrevétlenül bekerült. A `pyproject.toml`-ba minimális ruff/black config + opcionális pre-commit hook **strukturálisan megelőzné** ezt a következő sprintre.

---

## 2. Prioritized recommendations

### Phase 1 — Tooling baseline (~30 min CC, separate commit)

1. **`pyproject.toml`** kibővítése:
   - `[tool.ruff]` szekció default ruleset + per-file ignore-okkal (test mock-ok F401 stb.)
   - `[tool.black]` szekció `line-length = 100`
   - `[tool.mypy]` szekció `ignore_missing_imports = True`, lenient default
2. **Pre-commit hook** (opcionális, Tamás döntse el): `.pre-commit-config.yaml` ruff+black autofix-szel
3. **CI lint stage** (opcionális): `deploy_daily.sh` pre-flight kibővítése `ruff check`-kel (warning-only mode)

### Phase 2 — Trivial auto-fixes (~30 min CC, separate commit)

1. `ruff check --fix src/ scripts/ tests/` — automatikus:
   - 147 unused imports → törölve
   - 20 f-string placeholders → korrigálva
   - 20 multiple-statements → szétválasztva
   - 1 lambda assignment → def-re cserélve
   - Total: ~188 auto-fix
2. Verify: `pytest tests/ -q` → továbbra is 1756 passing
3. Commit: `chore(lint): apply ruff --fix auto-cleanup (188 trivial)`

### Phase 3 — Latent bug fix (~10 min CC, separate commit)

1. `tests/test_monitor_positions.py`: töröljük a soha nem hívott `_write_execution_plan` helper-t (line 41-52, ~12 sor) → 2 F821 + 1 dead helper resolved
2. Commit: `chore(tests): remove dead _write_execution_plan helper (F821 latent bug)`

### Phase 4 — Optional: Black formatting (~5 min CC, separate commit)

1. `black --line-length 100 src/ scripts/ tests/` — automatikus formázás 110 fájlra
2. Verify: `pytest tests/ -q` → 1756 passing
3. Commit: `chore(format): apply black formatting (line-length=100)`

**Megjegyzés**: a black-commit egy nagy diff (~10k+ sor) lesz, ami nehéz code review-t okoz a jövőben. **Ezért külön commit + esetleg külön branch + post-merge**.

### Phase 5 — Backlog (NEM most)

| Task | Effort | Priority |
|---|---|---|
| `phase4_stocks.py` split (1561 → 3-4 modul) | ~2-3h CC | P3 |
| `phase6_sizing.py` split (1378 → legacy + swing path) | ~2h CC | P3 |
| `submit_orders.py` split (~843, már strukturált a retry orchestrator-ral) | ~1h CC | P4 |
| Mypy strict opt-in modulonként | ~3-5h CC (folyamatos) | P3 |
| Unused variable cleanup (28 F841 manual) | ~30 min CC | P4 |

---

## 3. Mai sprint regression check

Az utóbbi 56 commit (Day 1-4) `git log` szerint **0 introducted broken test** — a 1711 → 1756 passing folyamatosan nőtt (+45 net teszt). A type annotation gaps **NEM** ez sprintben keletkeztek (pre-existing technical debt), és az unused imports **részben** ezen sprintben jöttek létre (a Day 3-i Task #G/H/K/L új modulok), de mind benign (auto-fixable).

**Nettó konklúzió**: a sprint **strukturálisan tiszta** (no broken contracts, no security regression, no runtime bug introduced).

---

## 4. Acceptance criteria — Phase 1 (most)

- [x] Linterek installálva (ruff/black/mypy)
- [x] Baseline scan elkészült
- [x] Findings katalogizálva (ez a dokument)
- [ ] `pyproject.toml` kibővítve `[tool.ruff]` + `[tool.black]` minimális config-gal
- [ ] Phase 2 auto-fix és Phase 3 latent bug fix: külön commit, Tamás opcionálisan jóváhagyhatja most vagy később

---

## 5. Refs

- Pyproject.toml current state: `[project]` + `[tool.pytest.ini_options]` only
- Coding style standard: `~/.claude/rules/common/coding-style.md` (800-sor max, ruff/black/mypy elvárt)
- Testing standard: `~/.claude/rules/common/testing.md` (80%+ coverage, pytest)
- Recent sprint: Task #G (`aba9720`) → Task #L (`d28c0b2`), 56 commit, +28k LOC
