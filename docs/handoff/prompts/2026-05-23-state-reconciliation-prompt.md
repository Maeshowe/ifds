# Dev Chat First Message — State Reconciliation (α opció — hibrid status quo)

> **Usage**: ezt küldd át a következő Dev chat session-be first message-ként, miután a `swing-pivot-dev-prompt.md` rendszer-prompt be van állítva. **Sürgős deploy deadline**: 2026-05-26 (kedd) 14:00 CEST — az első piaci nap a hosszú hétvége után.
>
> **Frissítve 2026-05-25**: Tamás α opció (hibrid status quo) döntése után — architektúra-váltás NEM szükséges, csak state reconciliation + hit counter fix.

---

## Kontextus — a 2026-05-25-i kódbázis-elemzés eredménye

W21 záró (péntek 2026-05-22 piaczárás után) — a swing pivot architektúra első teljes hete befejeződött. A hétvégén (2026-05-23 szombat) **felfedezésre került két autonóm bracket trigger** Day 4-5-en, amit a logok NEM rögzítettek.

**Eredeti hipotézis (2026-05-23)**: a swing pivot IBKR bracket-stop módban fut, és a `submit_orders.py` autonóm child SL+TP1+TP2 bracket-eket ad be a parent MKT mellé.

**A kódbázis-elemzés (2026-05-25) megmutatta a helyes magyarázatot**: a `submit_orders.py::submit_swing_market_only` kódja explicit:

```python
# Single market BUY (no bracket).
order = MarketOrder(action="BUY", totalQuantity=t["total_qty"])
order.orderRef = f"IFDS_SWING_{sym}"
order.tif = "DAY"
trade = ib.placeOrder(contract, order)
```

A 7 cron-driven entry (LBRT, MASI, EC, PFGC, WMB, DXCM, AMH) **parent MKT-only**, NINCS child bracket. A swing pivot architektúra **HELYESEN mental-stop módban van** (a `2026-05-17-swing-sizing-phase6.md` design doc és a Day 1 prezentáció helyes).

**A Day 4-5 autonóm bracket-trigger-ek forrása**: a Day 3-i `04-risks` §0.4 (IBKR Error 354 RESOLVED) workaround során Tamás **manuálisan adta fel** a VLO/ON/CNC ticker-eket az IBKR TWS Workstation Order Entry-n a TWS GUI bracket template-jével. Ezek planned-alapú szintekkel kerültek be, és autonóm módon triggereltek Day 4-5-en. ORDER_REF ÜRES (NEM `IFDS_*`), mert TWS GUI-ból manuálisan generált.

**Tamás Day 6 reggel (2026-05-25 08:26 CEST)**: a CNC élő TWS bracket (Stop $55,50 + Limit $61,89 GTC) **manuálisan cancellálta** az IBKR TWS-ben. **Többé NINCS autonóm bracket order az IBKR-ben** — a teljes 8-pozíciós portfolio mental-stop módban van.

## A feladatod — α opció, 3 részes scope

**Tamás α opció (hibrid status quo) döntése**: NINCS szükség architektúra-váltásra. Csak az alábbi P0 task scope-ja kell:

### P0 task fájl
[`docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md`](../tasks/2026-05-23-state-reconciliation-from-ibkr.md) — **olvasd el TELJESEN**, különösen a **"⚠️ Frissítés 2026-05-25 — α opció"** szakaszt a fájl elején, amely a helyesbített scope-ot rögzíti.

### Rész 1 — `pt_monitor.py::reconcile_state_from_ibkr()` új függvény
A 22:00 EOD eval keretében `ib.positions()` + `ib.executions()` query, autonóm bracket trigger detect (Tamás manuális TWS bracket-jeinek autonóm trigger-je esetén), state + daily_metrics + cumulative_pnl update. Telegram alert bracket trigger detektálás esetén.

**Megjegyzés**: a Day 7+ cron-driven entry-knek NINCS bracket-je, így általában NEM lesz autonóm trigger. DE jövőbeni manual TWS submit-ek (pl. újabb Error 354 workaround) hasonló helyzetet okozhatnak — a reconciliation függvény ezeket is detektálja.

### Rész 2 — `scripts/admin/retroactive_reconcile_w21.py` egyszeri script
Utólagos Day 4 + Day 5 rögzítés:
- `daily_metrics/2026-05-21.json` (-$227,06 SL trigger)
- `daily_metrics/2026-05-22.json` (+$159,12 TP1 trigger)
- `cumulative_pnl.json` (cumulative: +$42,63, NEM +$107,27)
- `swing_positions.json` (VLO + ON eltávolítva, 8 nyitott pozíció)

**Backup fájlok kötelezőek** (`*.bak.pre_retroreconcile.2026-05-23`).

### Rész 3 — TP1/SL/TP2 hit counter fix
Új detect logika a `daily_metrics.py` és `cumulative_pnl.py`-ben:
- Elsődleges: `orderRef` substring match (`_TP1`, `_SL`, `_TP2`)
- Fallback: fill ár közelsége a bracket szintekhez (planned vagy fill-alapú — Tamás manuális TWS bracket-jeinek esetén)
- Új mező: `exits.detection_method` = `"order_ref"` / `"bracket_level_match"` / `"manual_close"`

A retroaktív reconcile után **ezeknek az értékeknek kell érvényesülnie**:
- `cumulative_pnl.json daily_history[2026-05-19].tp1_hits: 1` (EC Day 2)
- `cumulative_pnl.json daily_history[2026-05-21].sl_hits: 1` (VLO Day 4)
- `cumulative_pnl.json daily_history[2026-05-22].tp1_hits: 1` (ON Day 5)

### ❌ Rész 4 — TÖRÖLT

A korábbi "architektúra-szintű döntés" (bracket-stop fenntartása vs mental-stop teljesítése) **NEM része ennek a task-nak**. Tamás α opció (hibrid status quo) döntése 2026-05-25-én lezárta ezt a kérdést:

- A swing pivot már HELYESEN mental-stop módban van
- A `submit_swing_market_only` parent MKT-only kódja a design szerint helyes
- A Day 1 prezentációt és a `2026-05-17-swing-sizing-phase6.md` design doc-ot NEM kell frissíteni
- A CNC élő TWS bracket-et Tamás manuálisan cancellálta

## A 4 pontosító kérdésre válasz (a Log Review chat read-only kódbázis-elemzéséből)

### 1. `submit_orders.py` bracket-builder függvény neve?

**NINCS** bracket-builder a swing pálya `submit_swing_market_only`-ban (csak `MarketOrder` parent). A `lib/orders.py::create_day_bracket` csak a legacy ágban használt (`swing_execution_enabled=False`), ami a `defaults.py TUNING` flag-en keresztül van állítva.

### 2. `ib.modifyOrder()` integrációs minta?

**Irreleváns α opcióban**, mert NINCS child bracket order amit modify-olni kell. A Rész 1 logika a `swing_positions.json` `child_order_ids` mezőre NEM épül — egyszerűbb path-on dolgozik: `ib.executions()` query-zi a tényleges fill-eket.

### 3. `state/closed_positions.json` létezik-e?

**NEM létezik**. A `state/` mappa tartalmaz `swing_positions.json` + 5 backup-fájlt (`*.bak.*`), de **NINCS** `closed_positions.json`. **Két opció a Dev chat-nek**:
- (A) Új `state/closed_positions.json` fájl létrehozása az archiváláshoz
- (B) Egyszerűsítés: zárt pozíciókat csak töröljük a `swing_positions.json`-ból, és a `daily_metrics/YYYY-MM-DD.json trades.details` listában rögzítjük az exit-eseményt — archiválás nem szükséges

**Javaslat: (B) opció** — kevesebb komplexitás, a `trades.details` lista már létezik a daily_metrics-ben. A `closed_positions.json` archív fájlra később lehet visszatérni, ha Day 21+ analízishez szükséges.

### 4. `ib.executions(ExecutionFilter()) time format`?

A `submit_orders.py` line 696 már használja, megerősített pattern:

```python
from ib_insync import ExecutionFilter
todays_fills = ib.reqExecutions(
    ExecutionFilter(time=date.today().strftime("%Y%m%d") + " 00:00:00")
)
```

**Format**: `"YYYYMMDD HH:MM:SS"` az IBKR szerver TZ-jében (NY). A `04-risks` §8.1.5-ben rögzített rule a date-szintű post-filter szükségességéről **továbbra is releváns** — a Dev chat tartsa be.

## Operatív részletek

- **Day 6 (hétfő 2026-05-25)** = USA Memorial Day, **NINCS piaczárás**. A pipeline NEM fut. Ez a **te munkanapod a deploy-ra**.
- **Day 7 (kedd 2026-05-26)** = első piaci nap a hétvége után. **Critical deploy deadline: 14:00 CEST** — a 14:30-as Phase 0-3 cron futás előtt.
- Sorrend:
  1. Rész 2 (retroaktív reconcile) **ELŐSZÖR**, mert a Rész 1 új `pt_monitor.py` reconcile_state logika kétszer detektálná a Day 4-5-i bracket trigger-eket egy szennyezett state-ből
  2. Rész 1 (új `pt_monitor.py` function) **MÁSODIKKÉNT**, miután a state tiszta
  3. Rész 3 (hit counter fix) — egyidejűleg Rész 1-gyel (közös refactor a `daily_metrics.py`-ben)

## Kockázat — Day 7 reggel divergence

Ha a Rész 2 retroaktív reconcile **NEM deploy-olt** Day 7 14:00 CEST előtt:
- A `submit_orders.py` Day 7-en a VLO és ON ticker-eket **"already has position or swing state"** miatt skipping-elné (mert a `swing_positions.json` még tartalmazza őket nyitottnak)
- A valóságban mindkettő **zárva** az IBKR-ben (Tamás manuális TWS bracket-jeinek autonóm trigger-je)
- A Day 7 Phase 4 univerzum sector cap (`Energy 17,86% + Healthcare 25,05%`) és `max_concurrent: 12` számításai **téves baseline-ról** indínanak (10 nyitott pozíció helyett 8)

## A kódbázisban releváns kontextus

A Log Review chat 2026-05-25-i kódbázis-elemzése:

| Kérdés | Válasz | Forrás |
|--------|--------|--------|
| Mit ad be a `submit_swing_market_only`? | CSAK parent `MarketOrder("BUY")` + `orderRef: IFDS_SWING_{sym}` | `submit_orders.py` line ~250-330 |
| Hol van a `create_day_bracket`? | `lib/orders.py` — DE csak legacy `swing_execution_enabled=False` ágban használt | `submit_orders.py` line ~430 |
| Melyik flag aktiválja a swing pályát? | `defaults.py TUNING swing_execution_enabled=True` | `submit_orders.py` line ~395 |
| `state/closed_positions.json`? | NEM létezik | `Filesystem:list_directory state/` |

## Fontos fájlok és linkek

### Az új P0 task (PRIMARY)
- [`docs/tasks/2026-05-23-state-reconciliation-from-ibkr.md`](../tasks/2026-05-23-state-reconciliation-from-ibkr.md) — **a fájl elejére `⚠️ Frissítés 2026-05-25` szakasz került**, ami a helyesbített scope-ot rögzíti

### A felfedezés forrásai (kontextus)
- [`docs/review/2026-05-21-daily-review.md`](../review/2026-05-21-daily-review.md) §9 — Day 4 VLO SL bracket trigger felfedezés (helyesbítve 2026-05-25)
- [`docs/review/2026-05-22-daily-review.md`](../review/2026-05-22-daily-review.md) §9 — Day 5 ON TP1 + W21 reconciled summary (helyesbítve 2026-05-25)

### Master reference
- [`docs/master-reference/04-risks-and-open-questions.md`](../master-reference/04-risks-and-open-questions.md) §0.10 — új P0 anomalia entry (helyesbítve 2026-05-25)

### Forrás-logok
- `logs/pt_submit_2026-05-20.log` — Day 3 entry log a planned bracket szintekkel (VLO stop $244,71, ON TP1 $115,41, CNC stop $55,50 / TP1 $61,89) — ezeket Tamás TWS-be írta be manuálisan
- IBKR TWS screenshot-ok (2026-05-23 reggeli) — a "Last 6 Days" Trades log + Positions + Orders + Trades Summary
- IBKR TWS screenshot (2026-05-25 08:26 CEST) — CNC bracket Cancelled megerősítés
- `state/swing_positions.json` (W21 záró, 10 nyitott pozíció — **valójában 8** az IBKR-ben)
- `scripts/paper_trading/logs/cumulative_pnl.json` (hivatalos cumulative +$107,27 — **valójában +$42,63**)

## Becsült munka

- Rész 1 + 2 + 3: **~4-5 óra CC** (a task fájl szerint, tesztekkel együtt)
- **Total**: 4-5 óra CC a Day 7 reggelig (kedd 14:00 CEST)

Day 6 (hétfő) = USA Memorial Day, teljes munkanap rendelkezésre áll. **Időben elférünk** (~50% margin).

## Első konkrét feladatod

1. **Olvasd be teljesen** a `2026-05-23-state-reconciliation-from-ibkr.md` task fájlt, **különösen a `⚠️ Frissítés 2026-05-25` szakaszt** a fájl elején
2. **Olvasd be** a Day 4 + Day 5 review §9 szakaszait (mindkettő helyesbítve 2026-05-25-én)
3. **Olvasd be** a `04-risks-and-open-questions.md` §0.10 entry-t (helyesbítve 2026-05-25)
4. **Készíts egy implementációs tervet** (NE kezdj el kódolni még!) — mutasd meg ide review-ra:
   - Sorrend a Rész 1-2-3 között (Rész 2 → 1 → 3)
   - A `pt_monitor.py::reconcile_state_from_ibkr` skeleton (function signature, return type)
   - A `retroactive_reconcile_w21.py` `--dry-run` mode logikája (a konkrét numerikus értékekkel a task fájl Rész 2 szerint)
   - A `daily_metrics.py::compute_exits_from_executions` skeleton
   - A unit teszt esetek (a task §5.1 alapján)
5. Ha a terv ready, **Tamás jóváhagyja**, **akkor** kezdesz kódolni — `/develop` parancs Research → Plan → Implement → Commit ciklusban.

---

**Sürgős figyelmeztetés**: ez P0 task, Day 7 reggeli pipeline futás előtt deploy-andó. Ha bármilyen blokkoló kérdés merül fel, **azonnal jelezz Tamás-nak**.

**Architektúra-megerősítés**: a swing pivot MENTAL-STOP módban van (helyes). NINCS szükség a `submit_orders.py` módosítására. NINCS szükség design doc frissítésre. Csak state reconciliation + retroaktív rögzítés + hit counter fix.
