# Session Close — 2026-05-12 20:37 CEST (W20 D2 — production hotfix kör)

## Összefoglaló

W20 Day 2 hotfix session. A vasárnapi `9a169b9` (dp_pct per-ticker switch) első élesi futása ma 16:15-kor **304 HTTP 429 rate-limit hibát** generált a UW API-n (247× /api/darkpool, 57× /api/stock/{T}/greek-exposure). A pipeline lefutott (1425 analyzed → 3 ticker IBKR-be), de a dp adat hiányos volt. Két production hotfix deployolva: **Phase 4 két-fázisú scoring** (UW per-ticker csak `passed` setre, ~100-200 hívás vs 1425) és **tiered BMI Momentum Guard** (a régi `5 → 5` no-op alert helyett valódi 5→4/3/2 redukció a streak hosszától függően). A user is felfedezte a duplikált BMI guard Telegram üzeneteket — a kódbeli ok kizárva, a Mac Mini-n `crontab -l | grep -c = 2` is hamis pozitívnak bizonyult (1 aktív + 1 historikus comment); a duplikáció valós forrása rejtély, holnap (5/13) tesztelünk.

## Mit csináltunk

### 1. Phase 4 two-pass dp scoring (commit `90cf5b4`)
- **Probléma**: vasárnap `9a169b9` switch (`UWBatchDarkPoolProvider` → `UWDarkPoolProvider`) miatt Phase 4 universe-loop **1425× hívta** UW per-ticker dark pool-t (universe ≠ candidate set — a smoke testem 20 tickeren félreméretezte). Result: **247× HTTP 429** + 57× Phase 5 GEX 429 (utóbbi nem blokkoló: Polygon fallback elnyelte)
- **Fix**: Pass 1 (1425 ticker) `dp_provider=None` → 0 UW hívás. Pass 2 enrichment (`_enrich_passed_with_dp_{async,sync}`) csak a `passed` ~100-200 tickeren per-ticker UW + flow re-scoring + szűrés újra. UW call budget: 1525 → 200-300 (rate window alatt)
- **Tesztek**: 4 új enrichment unit test (`test_apply_dp_enrichment_*`). 1556 → 1560 passing
- **Architektúra**: `dp_data["total_volume"]` denomination Pass 2-ben (close approximation Polygon daily volume-hoz)

### 2. Tiered BMI Momentum Guard (commit `b6db393`)
- **Probléma**: a tegnapi Telegram üzenetek `5 → 5` no-op redukciót mutattak — BC23 (`0b905e6`, ápr 13) csökkentette `max_positions`-t 8→5-re, de `bmi_momentum_max_positions=5` változatlan maradt → minden alert no-op volt. Mindezt **delta=-10.9** (jelentős 3+ napos BMI esés) mellett
- **Fix — tiered**:
  - **3-4 napja csökken** → max_positions = 4 (mild)
  - **5-6 napja csökken** → max_positions = 3 (strong)
  - **7+ napja csökken** → max_positions = 2 (severe)
- **Defenzív**: ha valamelyik tier-redukció nem kisebb mint a jelenlegi `max_positions`, INFO log + Telegram-skip (jövőbeli config drift ne termeljen újabb no-op zajt)
- **Algoritmus javítás**: `get_bmi_momentum_guard` most a teljes history-t végigjárja backward-ról, a tényleges csökkenő streak hosszát mérve (régi: csak `min_days+1` ablakot nézte — 7-napos slide-ot 3-naposnak látta)
- **Tesztek**: 7 új tiered teszt + 1 legacy frissítve. 1560 → 1564 passing
- **Live verifikáció**: a user `git pull` után a 19:23-as alert már `5 → 4` (mild tier) — fix MŰKÖDIK ✅

### 3. Crontab docs sync (commit `f62d954`)
- A `TÖRÖLT/INAKTÍV jobok` szekcióban 15:45-ös elavult komment (BC23 óta 16:15) javítva 16:15-re
- A user `crontab -l | grep -c "deploy_intraday" = 2` riasztás eredete: line 60 aktív cron + line 84 historikus comment → **NEM duplikáció**, hibás pozitív

### 4. Duplikált Telegram alert nyomozás
- Kódban csak 1 send-hívás (`runner.py:469`), `crontab -l` egyetlen aktív sor, `launchctl list | grep ifds` üres
- A 19:23-as run is duplikálva érkezett (mindkét üzenet `5 → 4`, helyes új tier) → két párhuzamos pipeline futás ugyanazon a percen belül
- Maradt 2 magyarázat (Mac Mini-n ellenőrizendő): root cron (`sudo crontab -l`, `/etc/cron.d/`) vagy Telegram szerver-oldali retry
- A duplikáció **kozmetikai zaj**, NEM hat a trading döntésre

## Commit(ok)

- `f62d954` — docs(crontab): fix outdated 15:45 reference in inactive jobs comment
- `b6db393` — fix(phase6): tiered BMI momentum guard — kill the 5 → 5 no-op alert
- `90cf5b4` — fix(phase4): two-pass dp scoring — restrict UW per-ticker to passed set

## Tesztek

**1564 passing** (1556 + 4 dp enrichment + 4 tiered BMI guard net), 0 failure.

## Tanulságok

**Production smoke test-em mérete számít.** A vasárnapi 20-ticker smoke (6.1s serial, 100% success) nem mintázta le a tényleges Phase 4 1425-ticker universe iteráció skáláját és a UW rate limit-et. Tanulság: **production switch előtt MINDIG verifikálni a tényleges hívásszámot** (`grep -c "API ERROR\|HTTP 429" prod_log_minta`) — vagy a kód olvasásával, vagy egy árnyékfutással a teljes universe-en. A "20 ticker × 300ms = 6 másodperc" extrapoláció rossz volt, mert (1) a Phase 4 az universe-en fut, NEM a candidate set-en; (2) a UW rate-limit nem hívás-időre, hanem hívás-frekvenciára érzékeny.

**Konfig drift észrevétlen marad ha az alert "fals pozitív" módban szól.** A `bmi_momentum_max_positions=5` BC23 óta no-op volt — minden BMI guard alert "aktiválódott" (= riasztott), de **0 hatású redukcióval**. A user megtanulta ignorálni, és csak akkor figyelt fel, amikor új session-ben **újraellenőrizte** a logikát. A defenzív refactor (`reduced < original_max_positions` előfeltétel a Telegram-küldéshez) megakadályozza ennek ismétlődését.

## Következő lépés

1. **Tamás Mac Mini, 5/13 reggel:** `git pull origin master` — utolsó 3 commit (Phase 4 two-pass, tiered BMI guard, crontab doc fix)
2. **5/13 16:15 cron — várt eredmények:**
   - `grep -c "HTTP 429" logs/cron_intraday_20260513_161500.log` → kis szám vagy 0 (volt: 304)
   - `grep "Pass 2: enriched X/Y" logs/...` → új diag log entry
   - `grep "Dark-pool re-scoring dropped" logs/...` → várhatóan 0-3 ticker drop az enrichment után
   - BMI guard üzenet (ha BMI csökkenőben): új formátum `Max pozíciók: 5 → 4/3/2`
3. **Duplikáció vs. crontab elhárítása** (ha az új tiered üzenet is duplikálva érkezik): `sudo crontab -l 2>/dev/null` + `ls -la /etc/cron.d/ /etc/crontab` a Mac Mini-n
4. **Day 63 (~máj 14): paper folytatás default kimenet a legvalószínűbb**

## Blokkolók

Nincs.
