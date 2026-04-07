# Session Close — 2026-04-07 (session 8)

## Összefoglaló
P0 fix: Pipeline Split context load bug — `ctx.macro is None` → `not ctx.universe` a runner.py-ban. A 15:45-ös Phase 4-6 ezért skipelt minden napot ápr 6 óta. + stale CSV guard + deploy_intraday log redirect.

## Mit csináltunk
1. **Core fix** — `src/ifds/pipeline/runner.py:290`: feltétel cseréje. Phase 0 mindig fut, ezért `ctx.macro` mindig set, így a régi feltétel SOHA nem triggerelt.
2. **3 új regression teszt** — `test_pipeline_split.py::TestContextLoadCondition` (split mód, full pipeline, phases 1-3).
3. **Stale CSV guard** — `submit_orders.py`: kilép ha az execution plan dátuma nem mai (Telegram ⚠️ üzenettel).
4. **deploy_intraday.sh** — stdout/stderr → `logs/cron_intraday_YYYYMMDD_HHMMSS.log`.

## Commit(ok)
- `fa00a0e` — fix(runner): load Phase 1-3 context when universe is empty in split mode

## Tesztek
1294 passing (1291 + 3 új), 0 failure

## Következő lépés
- **Mac Mini git pull** — holnap reggel KÖTELEZŐ a 15:45 előtt
- Holnap log review: phase 4-6 valóban betölti-e a ctx-t, friss CSV készül-e
- TV layer taskok (parkolt)

## Blokkolók
Nincs
