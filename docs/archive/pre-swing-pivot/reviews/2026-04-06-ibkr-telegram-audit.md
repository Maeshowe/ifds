# IFDS — IBKR-IFDS Információcsere + Telegram Audit — Kritikus Elemzés

## Dátum: 2026-04-06
## Készítette: Chat (Orchestrator)

---

## I. IBKR-IFDS Információcsere — Problémák

### 1. A pipeline és az execution KÖZÖTT nincs valódi kapcsolat

A pipeline (Phase 0-6) és az IBKR execution (PT scriptek) között az egyetlen kapcsolat a **CSV fájl** (`execution_plan_run_*.csv`). A pipeline generálja, a submit_orders.py olvassa. De:

- **Nincs visszacsatolás pipeline→IBKR→pipeline.** A pipeline nem tudja, hogy tegnap milyen pozíciók nyíltak, mi fillelt, mi nem, mekkora volt a P&L. Minden nap vakon méretez, nem tanul a korábbi napokból.
- **A submit_orders.py nem a mai pipeline-ból olvas** — ha nincs mai CSV, a `find_latest_csv()` a legutolsó CSV-t veszi (ma a 04-03-asat). Ez néha helyes (swing hold), de néha hibás (régi plan, már nem aktuális árak).
- **Az existing skip logika pozíció-szinten működik, nem order-szinten.** Ha egy ticker limitje nem fillelt (pending order), az `existing` setben van és skipeli. De a rendszer nem tudja, hogy a limit miért nem fillelt, és nem próbálja újra más áron.

### 2. A monitor_state.json mint egyetlen state forrás — törékeny

A `monitor_state_{date}.json` az egyetlen hely ahol a pozíciók állapota (entry price, SL, trail state) él. Ezt a submit_orders.py hozza létre, és a pt_monitor.py + pt_avwap.py módosítja.

**Problémák:**
- Ha a monitor_state nem jön létre (submit hiba), a pt_monitor nem talál monitorozandó tickert
- Ha a monitor_state régi dátumú, a pt_monitor régi tickereket monitoroz (→ LION/SDRL phantom)
- A monitor_state nem tartalmazza a TP1 forrását (ATR vs call_wall) — ezért az AVWAP TP1 újraszámítás hibás
- **Nincs IBKR pozíció→monitor_state szinkronizáció** — ha az IBKR-ben van pozíció amit a monitor_state nem ismer, a close_positions.py nem tudja helyesen kezelni

### 3. Az IBKR fill árak nem kerülnek vissza a rendszerbe

A submit_orders.py limit árat küld, de az IBKR fill ár eltérhet (AVWAP MKT fill, partial fill, price improvement). A tényleges fill ár csak az EOD reportban jelenik meg — a pipeline következő napi futásánál nem elérhető.

**Konkrét hatás:** a risk kalkuláció az execution plan limit price-ra épül, de a tényleges entry a fill price. Ha az AVWAP MKT fill 5% magasabb (CF: $127.98→$134.46), a risk/reward teljesen más.

### 4. A close_positions qty kalkuláció — még mindig törékeny

A net BOT-SLD fix javított, de a `get_net_open_qty` logika továbbra is az IBKR `reqExecutions()`-ra épül, ami nem mindig teljes. Ha a fill nem szinkronizálódott a lekérdezés idejéig (5s sleep), hibás qty-t számol.

### 5. A monitor_positions.py phantom detekciók

Ma 04-06-on CRGY és AAPL phantom-okat detektált. A script a `ib.positions()` hívásból olvassa a pozíciókat, ami más clientId-k session-jéből cache-elt adatokat mutathat. A monitor_positions 5× futott egymás után (crontab hiba), ami súlyosbította.

---

## II. Telegram Kimenet — Problémák és Újratervezés

### A jelenlegi Telegram üzenetek időrendje (BC20A Pipeline Split ELŐTT)

```
22:00  Pipeline Daily Report (1-2 üzenet) — Phase 0-6 eredmények
22:01  Company Intel (1-2 üzenet) — ticker elemzések
```

### A jelenlegi Telegram üzenetek időrendje (BC20A Pipeline Split UTÁN, tervezett)

```
22:00  Phase 1-3 Macro Snapshot — BMI, VIX, szektorok
15:35  Phase 4-6 Trading Plan — pozíciók, méretezés
15:35  Company Intel — ticker elemzések
15:45  SUBMIT — orderek beküldve
~16:00 AVWAP — MKT fill-ek (ha volt unfilled limit)
19:00+ MONITOR — trail/loss exit event-ek
21:40  CLOSE — MOC summary
22:05  EOD — napi P&L, kumulatív
```

### Probléma #1: A pipeline üzenet tartalmazza az execution plan-t, de a submit nem

A Daily Report (telegram.py) mutatja a pozíciótáblát (ticker, qty, entry, SL, TP1, TP2, risk, MMS). De a submit Telegram üzenet csak ezt:
```
📊 PAPER TRADING — 2026-04-06
Submitted: 2 tickers (4 brackets)
Exposure: $8,893 / $100,000 limit
Tickers: UNIT, SPHR
```

**Hiányzik:** melyik ticker, mekkora qty, milyen áron, milyen SL/TP-vel. A felhasználó nem tudja, hogy mit kereskedik a rendszer anélkül, hogy a pipeline reportot visszakeresi.

### Probléma #2: A Company Intel piac UTÁN megy ki (22:01)

A Company Intel elemzés (driver, risk, contradiction, catalyst) a pipeline futás részeként generálódik. Az új schedule-ban ez 22:00 CET-kor megy ki — **6 órával a piaczárás UTÁN, 15 órával a kereskedés ELŐTT**. Ennek a kereskedési nap ELEJÉN kellene jönnie, nem utána.

**Ami még rosszabb:** az execution plan a Pipeline Split-ben 15:45-kor generálódik, de a Company Intel a 22:00-ás futáshoz van kötve. Ha a pipeline Phase 4-6-ot 15:45-kor futtatja, a Company Intel is 15:45-kor kellene menjen — közvetlenül az order submit ELŐTT.

### Probléma #3: Nincs fill rate / execution feedback Telegram

Amikor a submit beküld 8 tickert, a felhasználó nem tudja, hogy hány fillelt valóban. Az AVWAP fill-ekről jön üzenet (per ticker), de nincs összefoglaló: "8-ból 6 fillelt, 2 unfilled (X, Y)".

### Probléma #4: A MOC/trail/loss exit event-ek elszórtak

A pt_monitor egyenként küld Telegram üzenetet minden trail/loss exit event-re. Ha 4 ticker kap loss exit-et, az 4 külön üzenet. Nincs napi összefoglaló intraday event-ekről.

### Probléma #5: Az EOD report nem tartalmaz ticker-szintű bontást

Az EOD Telegram:
```
📊 PAPER TRADING EOD — 2026-04-06
Trades: 8 | Filled: 8/8
TP1: 0 | TP2: 0 | SL: 0 | MOC: 8
P&L today: $-91.23 (-0.09%)
Cumulative: $-1,497.00 (-1.50%) [Day 36/21]
```

**Hiányzik:** melyik ticker mennyit hozott/veszített. Az "Day 36/21" is hibás (kellene Day 36/63).

---

## III. Javaslatok

### A) IBKR-IFDS Információcsere javítás (CC taskok)

1. **monitor_state tp1_source mező** — jelölje, hogy ATR vagy call_wall a TP1 forrás (backlog, VIX ~15)
2. **monitor_positions phantom fix** — `ib.positions()` filter: csak `conId`-kat fogadjon el amik az IBKR accountban vannak és `symbol` nem `.CVR`
3. **monitor_positions idempotency** — ne fusson többször egymás után, vagy ha fut, ne logoljon dupla event-eket
4. **monitor_state régi fájl cleanup** — ha a state fájl >1 nappal régebbi, ne használja (→ LION/SDRL phantom)

### B) Telegram Újratervezés (CC task)

Az alábbi Telegram üzenet struktúrát javaslom:

#### B1. Pipeline Macro Snapshot (22:00 CET) — változatlan
```
[2026-04-06 22:00 CET] PIPELINE
📊 IFDS Macro Snapshot — 2026-04-06
VIX=24.38 (elevated) | TNX=4.31% | 2s10s=+0.52%
BMI=46.8% YELLOW (+1.8 vs tegnap) | Strategy: LONG
Sectors: XLK ↑5.3% | XLC ↑4.4% | XLRE ↑4.4%
VETO: XLE XLP XLU
Skip Day Shadow: NEM aktív
```

#### B2. Trading Plan + Execution (15:45 CET) — ÚJ formátum
```
[2026-04-07 15:45 CET] SUBMIT
📈 IFDS Trading Plan — 2026-04-07
8 pozíció | Risk: $2,216 | Exposure: $67,646

TICKER  QTY  ENTRY    SL       TP1      RISK$  EARN
AAPL    50   $175.20  $170.50  $178.70  $235   04-25
MSFT    30   $405.30  $395.80  $412.40  $285   04-23
...

Submitted: 8 tickers (16 brackets)
Existing skip: LIN, DBRG (already held)
```

#### B3. Fill Summary (16:30 CET) — ÚJ
```
[2026-04-07 16:30 CET] FILL SUMMARY
✅ 6/8 filled | ❌ 2 unfilled (AAPL, MSFT — limit not reached)
AVWAP: CF filled @ $134.46 (plan $127.98, slip +5.1%)
```

Ez lehet egy új script vagy az AVWAP script utolsó lépése (összefoglaló).

#### B4. Intraday Events — változatlan, de per-event (trail, loss exit)

#### B5. EOD Summary (22:05 CET) — BŐVÍTETT
```
[2026-04-06 22:05 CET] EOD
📊 PAPER TRADING EOD — 2026-04-06

P&L: $-91.23 (-0.09%) | Cum: $-1,497 (-1.50%) [Day 36/63]
TP1: 0 | SL: 0 | LOSS: 0 | TRAIL: 0 | MOC: 8

Top: UNIT +$101.67 | NEM -$79.65
Leftover: nincs ✅
CB: $-1,497 / $-5,000

BMI: 46.8% (+1.8) | VIX: 24.38
```

#### B6. Company Intel (15:46 CET) — ÁTHELYEZÉS
A Company Intel a Trading Plan UTÁN menjen, nem a pipeline este futásakor. Így a felhasználó a kereskedési nap elején látja az elemzést.

---

## IV. Összefoglaló — Priorizált akciólista

| # | Probléma | Súlyosság | Akció |
|---|----------|-----------|-------|
| 1 | monitor_state régi fájl → phantom tickerek | P0 | monitor_state dátum validáció |
| 2 | monitor_positions többszörös futás | P0 | crontab javítás (Mac Mini) |
| 3 | Telegram submit — hiányzó ticker részletek | P1 | submit Telegram bővítés |
| 4 | Telegram EOD — hiányzó ticker bontás + Day/63 fix | P1 | EOD Telegram bővítés |
| 5 | Company Intel időzítés (22:00→15:46) | P1 | BC20A Pipeline Split-tel |
| 6 | Fill Summary Telegram | P2 | AVWAP script összefoglaló |
| 7 | pipeline→IBKR visszacsatolás | P3 | BC20A+ scope |
