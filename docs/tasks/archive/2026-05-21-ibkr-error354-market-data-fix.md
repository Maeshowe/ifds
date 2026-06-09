# Task: IBKR Error 354 Market Data Block — Permanent Fix

Status: DONE
Updated: 2026-05-20
Note: RESOLVED 2026-05-20 19:00 CEST — Tamás bekapcsolta az API → Precautions → "Bypass Order Precautions for API Orders" beállítást a TWS Global Configuration-ben. 1-share VLO live smoke test t=1.0s Filled @ $254.08 (no Error 354). Cleanup SELL @ $253.19 (P&L -$0.89). State≡IBKR reconciled. **Holnapi Day 4 cron tisztán fut új tickerekkel is.**

**Priority:** P1 (blocks all new-ticker entries on the swing-pivot market-only path)
**Created:** 2026-05-20
**Owner:** Claude Code
**Estimated effort:** ~30-60 min CC + Tamás IBKR Workstation verification

**Source:**
- [`docs/master-reference/04-risks-and-open-questions.md`](../master-reference/04-risks-and-open-questions.md) §0.3 (to be added)
- 2026-05-20 Day 3 Incident — `pt_submit_2026-05-20.log` + diagnostic 1-share VLO submit via `/tmp/ibkr_debug_submit.py`

---

## 1. A probléma

A 2026-05-20 Day 3-i 15:31 CEST cron-driven `submit_orders.py` szubmit (VLO/ON/CNC) **silenty failed** az IBKR paper account-on:

```
Error 354: You are trying to submit an order without having market data
for this instrument. IBKR strongly recommends against this kind of blind
trading which may result in erroneous or unexpected trades. Restriction
is specified in Precautionary Settings of Global Configuration/Presets.
```

**Specifikum**:
- A 4 régi ticker (LBRT, MASI, EC, PFGC) sikeresen fillodott Day 1+2-n — feltehetően mert az IBKR market data cache ezekre érvényes
- A 3 új ticker (VLO, ON, CNC) elsőre került submit-ra — Error 354 silent cancel
- A `submit_orders.py` status check a placeOrder után 1.5s-cel PreSubmitted-et látott (valid) → state-be írta a position-okat → DE az IBKR async cancel-lott a connection close UTÁN
- Eredmény: **state/IBKR divergencia** (state=7, IBKR=4)

**Day 1-2 vs Day 3 különbség**: a swing-pivot előtt a `lib/orders.create_swing_bracket` MarketOrder PARENT + OCA bracket-et küldött. A paper account valamiért a parent-et fillelte silenty az Error 354 ellenére (bracket override quirk). A swing-pivot `submit_swing_market_only` bare MarketOrder-t küld bracket nélkül → nincs override mechanizmus.

## 2. Workaround (Day 3 alkalmazott)

Tamás manuálisan a IBKR TWS Workstation Order Entry-n adta fel a 3 BUY MKT order-t. A GUI csak interaktív "no market data" figyelmeztetést ad → Override + Submit → fillodott rendben.

State sync: az `entry_price`-ot az actual IBKR fill-re cseréltük, `stop_level`/`tp1_level`/`tp2_level`-t 2.0×ATR / 1.5×ATR / 3.0×ATR alapján recompute-oltuk (Day 1 reconstruction pattern). Backup: `state/swing_positions.json.bak.*`.

## 3. Permanent fix lehetőségek (válaszdás scope-szerint)

### A) IBKR Workstation Precautionary Settings disable (Recommended)

**Hatás**: globális, minden cron-submit-re érvényes, NEM kell kód-változás.

**Lépések**:
1. TWS/Gateway: **File → Global Configuration → Presets**
2. Válaszd ki a paper account preset-et (vagy "Default" preset)
3. **Precautionary Settings** szekció
4. Disable: **"Block submitting orders without market data"**
5. Save + OK

**Verify**: a holnapi 15:31 CEST cron egy új ticker (pl. VLO) submit-ra Error 354-et NEM ad.

**Risk**: alacsony — a "blind trading" figyelmeztetés a paper account-on irreleváns, mert már védelmi rétegek (price sanity, exposure limit, sector limit) máshol érvényesek a `submit_orders.py`-ban.

### B) Code patch — `reqMktData` warm-up

**Cél**: a `submit_swing_market_only`-ban a `placeOrder` ELŐTT request market data:

```python
# Before placeOrder
ib.reqMktData(contract, "", snapshot=False, regulatorySnapshot=False)
ib.sleep(2)  # wait for subscription to settle
trade = ib.placeOrder(contract, order)
# ... existing status check ...
ib.cancelMktData(contract)  # cleanup after the order is acknowledged
```

**Risk**: közepes — ha a paper account NEM ad streaming market data permission-t, ez nem segít. Akkor (A) opció kell.

**Verify**: feltehető-e a snapshot a paper account-on? Tamás a TWS-ben tudja ellenőrizni: TWS → Settings → Market Data → Stocks → check status.

### C) Live API permission upgrade (long-term)

IBKR Account Management → Market Data Subscriptions → "US Securities Snapshot/Streaming". Paper account-on ingyenes lehet, de account-specific.

## 4. Tesztelés

Mielőtt a code patch (B) commit-olódna:
1. Live smoke test 1-share VLO + 1-share ON + 1-share CNC submit (clientId=18, NEM clientId=10) **a fix-szel**
2. Verify: status=Filled vagy Submitted (NOT Cancelled)
3. Verify: IBKR-ben ténylegesen ott a position
4. Cleanup: 1-share ad-hoc trade-eket manuálisan SELL-elni az IBKR Workstation-en

## 5. Akciók a következő session reggelére (2026-05-21)

1. **Tamás**: IBKR Workstation Precautionary Settings disable (opció A) — 5 min
2. **CC**: a `04-risks` §0.3-ban dokumentálni az incident-et és a workaround-ot
3. **CC** (opció B-vel ha A nem elég): `submit_swing_market_only` patch + 1-share live smoke + regression test
4. **CC**: STATUS.md Day 3 record update (incident + workaround + permanent fix tracking)
5. **CC**: backlog task hozzáadása a `monitor_submit_heartbeat.py`-ba — Error 354 detection + Telegram alert (proaktív, hogy egy jövőbeli paper account permission revoke azonnal észlelve legyen)

## 6. Commit message draft (a permanent fix-hez)

```
fix(submit): bypass IBKR Error 354 "no market data" block

Day 3 (2026-05-20) incident: new-ticker submits (VLO/ON/CNC) failed
with Error 354 because IBKR paper account Precautionary Settings block
submits without market data. The legacy bracket builder masked this
via OCA parent fill quirk; the swing-pivot market-only path does not.

Fix: <A) Workstation setting disable> OR <B) reqMktData warm-up>

Refs: docs/master-reference/04-risks-and-open-questions.md §0.3
      docs/tasks/2026-05-21-ibkr-error354-market-data-fix.md
```

## 7. Kapcsolódó

- `scripts/paper_trading/submit_orders.py::submit_swing_market_only` (line 280-326)
- `scripts/paper_trading/lib/orders.py::create_swing_bracket` (legacy, for comparison)
- `04-risks` §0.2 (Day 1 Error 10349 TIF — kapcsolódó preset-bug-osztály)
- `04-risks` §0.3 (Day 3 Error 354 — ez a task lezárja)
- `.claude/rules/ifds-rules.md` — IBKR Paper Account quirks szekció bővítendő
