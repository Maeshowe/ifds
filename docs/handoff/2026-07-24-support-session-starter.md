Status: OPEN
Updated: 2026-07-24
Note: Support Session indító — a review-flagged karbantartási/bugfix tételek álló lane-je. NEM review (az a review-sessionben), NEM FRL build (az külön). A pt_events P1 már DONE; a következő az e2e ordering-leak.

# Support Session — Task-indító

## Mi ez

A **Support Session** az IFDS **karbantartási / bugfix lane-je**: a napi review-sorozatban felszínre kerülő,
**freeze-safe** technikai adósságok javítása TDD-vel. Három párhuzamos szál:
1. **Review-session** — napi/heti v6 review + megfigyelés-sorozatok (marad, ahol van).
2. **FRL build-session** — a Factor Research Loop toolingja (`scripts/research/`, `test_frl_*`).
3. **Support-session (ez)** — bugfix/higiénia. Az előző körben lezárta a pt_events P1-et.

## Már KÉSZ (kontextus, ne csináld újra)

- ✅ **pt_events P1 test-izoláció** (`db95c13`, task archiválva `docs/tasks/archive/2026-07-23-pt-events-test-isolation.md`):
  `PTEventLogger` env-vezérelt (`IFDS_PT_EVENT_DIR`, default bitre `logs/` — viselkedés-invariáns) +
  conftest modul-tetős setdefault + 4 regressziós teszt. **2175 passed, 0 fail/warn.** Trigger azonosítva:
  a Phase 1-3 22:00 vasárnapi cron **pre-flight pytest** heti szennyezést okozott.
- ✅ **07-23 log cleanup**: a szennyezett `logs/pt_events_2026-07-23.jsonl` 194 → 6 sor (backup
  `.bak.pre_testclean`), byte-azonos a Mini-n és lokálisan (sha256 `bbcfd4b5…`).

## ELSŐDLEGES feladat: e2e test-ordering leak

**Task:** `docs/tasks/2026-07-24-e2e-test-ordering-leak.md` (OPEN, `9aba155`). Ezzel kezdj.

**Egymondatos tünet:** a `test_pipeline_e2e.py` (9 teszt) **izoláltan ÉS a teljes suite-ban zöld**, de
bizonyos fájl-részhalmazokkal együtt bukik (~16 fail egy adott kombinációban) — teszt-teszt globális
állapot-szivárgás.

**Amit a review-session már leszűkített (ne ismételd):**
- **NEM** a pt_events fix (`db95c13`) — stash-igazolt, a tiszta fán is megvan.
- **NEM** a FRL-tesztek — `test_frl_*` + e2e mindkét sorrendben zöld (175 passed).
- **NEM** a triviális páronkénti kombinációk (scoring_validation_spy / swing_universe / console / sector_bmi + e2e mind zöld).

**Erős gyökérok-hipotézis:** a `src/ifds/config/defaults.py` modul-szintű **mutálható** `CORE`/`TUNING`/`RUNTIME`
dictjeit egy teszt **helyben mutálja** restore nélkül → az e2e szennyezett defaultot olvas. Ez a
[[coding-style]] immutability-szabály sértése, a [[test-env-hygiene]] config-állapotra vetített rokona.

**A repró horgonya nálad van:** a ~16 failt adó **konkrét fájlhalmazt** a korábbi Support-futásból rögzítsd
a task §0-jába — a review-session páronként nem találta meg, a teljes bisection drága. Tedd determinisztikussá
`pytest-randomly` + seeddel. Fix: (2.a) a mutáló teszt monkeypatch/deep-copy; (2.b, ajánlott) **autouse
conftest snapshot/restore** fixture a `defaults` dictekre — strukturálisan lehetetlenné teszi a jövőbeli
előfordulást.

## MÁSODLAGOS (döntés-igényes, nem sürgős): vasárnapi historikus log-szennyezés

A pt_events go-forward rés **zárva** (`db95c13`), de a **múltbeli vasárnapi logok szennyezettek maradtak**:
a heti pre-flight ugyanazt a 47-soros fixture-blokkot dumpolta **06-07, 06-21, 06-28, 07-12, 07-19**
(verifikálandó: `logs/pt_events_*.jsonl` méret-eloszlás, ~7613 byte-os vasárnapi ujjlenyomat).

**Miért számít:** a `pt_events` az **FRL loader rank-2 forrása** (`docs/design/2026-07-21-factor-research-loop-spec.md`
§4.1). Ha a loader valaha visszamenőleg olvassa e napokat, a fixture-események torzítanának.

**Döntés (Tamás + FRL build-session egyeztetés):** vagy (a) a szennyezett vasárnapi logok tisztítása (a
`clean_pt_events` időablak-szűrő általánosítása — de a vasárnapi ablak eltérhet, verifikálni kell), vagy
(b) az FRL loader gap-kezelése szűri ki a fixture-blokkokat (tartalom-alapú: AAA/BBB/CCC + circuit_breaker
szignatúra). **Ajánlás: (b)** — nem destruktív, és a loader-nek úgyis robusztusnak kell lennie a historikus
szennyezésre. Ez inkább **FRL-loader-tétel**, mint support — a Support-session csak **jelezze** az
FRL build-sessionnek (cross-flag), ne oldja meg egyoldalúan.

## Munkakörnyezet és szabályok

- **Freeze él Day 63-ig.** Csak viselkedés-invariáns / teszt-only / tracking-higiénia. Az e2e-fix ilyen
  (teszt-izoláció; a 2.b autouse fixture teszt-only, a 2.c Config defenzív-copy — csak megerősített #1 esetén —
  viselkedés-invariáns). Lásd [[freeze-production-churn-rule]].
- **TDD kötelező**: teszt előbb (RED) → fix (GREEN). Baseline **≥2175 passed**, csak nőhet; 0 fail, 0 warn.
- **Mini-írás**: `ssh ifds-mini` allowlisttel; nem-pénzügyi log/state OK (backuppal); pénzügyi ledgert a
  szemantikai guard blokkol → az Tamás-terminal ([[mini-financial-write-guard]]). A 07-23 cleanup precedens:
  verifikált script + 6-soros abort-guard + backup, a guard átengedte.
- **Commit**: `fix(test): …`; a task-fájl commit-üzenete. **Tamás pushol** (CC commitol). Task-workflow:
  OPEN→WIP (megnyitáskor) → DONE + `git mv` archive-ba (commit után).
- **NE nyúlj** a fagyott entry/exit-logikához (entry_price=planned, self-reentry = Day 63-input, NEM bugfix).

## Első lépések

1. Olvasd a `docs/tasks/2026-07-24-e2e-test-ordering-leak.md`-t + a §0 repró-stratégiát.
2. Status OPEN→WIP. Rögzítsd a kiváltó fájlhalmazt (a korábbi megfigyelésedből).
3. TDD: `test_config_isolation.py` (RED) → autouse snapshot/restore fixture + a mutáló teszt javítása (GREEN).
4. Determinisztikus repró (`pytest-randomly` seed) zöld + teljes suite ≥2175.
5. Commit, Status→DONE, archive, CHANGELOG.md.
6. **Cross-flag** az FRL build-sessionnek a másodlagos (vasárnapi historikus log) tételről.

## Referenciák

- Elsődleges task: `docs/tasks/2026-07-24-e2e-test-ordering-leak.md`
- Lezárt precedens: `docs/tasks/archive/2026-07-23-pt-events-test-isolation.md` + `docs/review/2026-07-23-daily-review.md` §6/P1
- Rokon szabály: `.claude/rules/ifds-rules.md` „Test environment higiénia"
- Memória: [[test-env-hygiene]], [[coding-style]] (immutability), [[freeze-production-churn-rule]],
  [[mini-financial-write-guard]], [[division-of-labor-chat-cc]]
