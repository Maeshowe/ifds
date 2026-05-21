# Session Close — 2026-05-13 20:36 CEST (W20 D3 — sequential dp enrichment hotfix)

## Összefoglaló

A tegnapi Phase 4 two-pass dp scoring (`90cf5b4`) első élesi futása ma 16:15-kor 81%-ban csökkentette a Phase 4 darkpool 429 hibákat (247 → 46), de a megmaradó 46 hiba még mindig 36% adat-elvesztést okozott a passed tickerek között (166 → csak 106 enriched). A parallel `asyncio.gather` még mindig túllépte a UW Basic rate limit-jét. **Sequential per-ticker + 200 ms inter-call delay** hotfix deployolva (`1f0ffb9`); live smoke test 166 tickeren **95.2% success rate, 0 hard error, 77.6s** total. Holnapi 14-i cron a végleges validáció.

## Mit csináltunk

### 1. Mai production log diagnózis
- **Total errors**: 304 (tegnap) → **146** (52% redukció)
- **Phase 4 /api/darkpool**: 247 → **46** (81% redukció — a fő fix lényegében működik)
- **Phase 5 /api/stock/greek-exposure**: 57 → 100 (nőtt — a Phase 4 nem fogyasztotta el a budget-et, így Phase 5 többet tudott próbálni; Polygon fallback működik, nem blokkoló)
- **Pass 2 enrichment**: 166 passed → 106 enriched (64%) → 24 ticker dropped sign-flip miatt ✅
- **Maradék probléma**: 60 ticker `Pass 1 score` mellett ment tovább, dp signal nélkül → lehet közöttük olyan, amit a sign-flip drop-olnia kellett volna

### 2. Sequential + 200ms delay hotfix (commit `1f0ffb9`)
- **Probléma**: az `asyncio.gather` 166 task × sem_uw=5 parallel ~17 req/s burst-öt termelt → UW Basic rate limit
- **Fix**: `_enrich_passed_with_dp_{async,sync}` átalakítva sequential for-loop-ra `await asyncio.sleep(0.2)` / `time.sleep(0.2)` közötti delay-jel
- Új config `dp_enrichment_delay_s = 0.2` (futtatás közben tunolható)
- **Live smoke** 166 mai passed tickeren: **158/166 success (95.2%), 0 hard error, 77.6s** total (vs production parallel: 64% success, 46 errors)
- **A 8 "None" valid**: kis-likviditású ADR-ek (NMR, AEG, NG, BANC, CMRE…) — üres dark pool response, nem hiba
- **Tesztek változatlan**: 1564 passing (a 4 _apply_dp_enrichment unit test a pure functiont hívja, nem a wrappert)

## Commit(ok)

- `1f0ffb9` — fix(phase4): sequential dp enrichment with 200ms delay — UW rate-limit calibration

## Tesztek

**1564 passing**, 0 failure.

## Tanulságok

**Élő smoke test > extrapolált smoke test.** Vasárnap a 20-ticker × 300ms = 6s extrapoláció félreméretezte a problémát. Tegnap a sem_uw=5 / 166-task burst-öt nem teszteltem külön. Ma a **tényleges 166-ticker live smoke** (kódutaton kívül, ad-hoc Python script) **pontosan** azt a paramétert mérte, amit a production fog kapni — és bebizonyította, hogy a sequential + 200ms verzió 95.2% sikerrátát ad. Tanulság: minden rate-limit-érzékeny változtatás előtt **kötelező egy live smoke a teljes terheléssel**, nem extrapolációval.

**Iteratív hotfix kör működik.** 3 commit 4 nap alatt javította a dp jelfolyamot a "structurálisan 0" állapotból "95% accurate sign-flipped scoring"-ra:
1. `9a169b9` (5/10): sign-flip + per-ticker switch (broken: 1525 calls, 304 errors)
2. `90cf5b4` (5/12): two-pass scoring (1525 → 300 calls, 304 → 146 errors)
3. `1f0ffb9` (5/13): sequential + delay (146 → ~0 errors expected tomorrow)

Mindegyik a production log-ból derült ki, nem pre-deploy elemzésből. Ez tipikus rate-limit kalibráció — egyszeri smoke nem mindig elég.

## Következő lépés

1. **Tamás Mac Mini, 5/14 reggel:** `git pull origin master` (1 új commit: `1f0ffb9`)
2. **5/14 16:15 cron várt eredmény:**
   - `grep -c "HTTP 429" logs/cron_intraday_20260514_161500.log` → ~0 (vs tegnap 46 + 100)
   - `grep "Pass 2: enriched X/Y"` → X/Y >= 90% (vs tegnap 64%)
   - Phase 5 GEX UW success rate is várhatóan javul (Phase 4 nem konkurál)
3. **Day 63 (~máj 14): paper folytatás default kimenet a legvalószínűbb** (mai a Day 63!)
4. **Ha 5/14 tisztán fut**, mehet a W19+ P1 backlog: LOSS_EXIT bracket SL cancellation, 10-Q/10-K SEC filing exclusion, ADR earnings adatforrás fix

## Blokkolók

Nincs. A duplikált BMI guard Telegram alert továbbra is nyitott (kódbeli ok kizárva, crontab tiszta, root cron még nem ellenőrizve) — kozmetikai, holnap újra mérhető a `5 → 4` üzenet duplikáció státusza.
