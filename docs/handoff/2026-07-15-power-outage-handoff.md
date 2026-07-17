Status: DONE
Updated: 2026-07-17
Note: Mini visszatért 07-16 23:43 (boot). 07-15+07-16 outage-napok. ITT/XPO reconcile+könyvelés kész (07-17). UPS megrendelve.

# Handoff — 2026-07-15 áramszünet (Mac Mini outage)

## ✅ 07-17 LEZÁRÁS — minden feloldva

A Mini **07-16 23:43-kor bootolt** (2 napos outage: 07-15 ~12:10 → 07-16 este; áramszünet).
Gateway auto-indult, nincs orphan. Elvégzett lépések (mind a Mini production state-jén):

1. **21:40 short-kockázat hatástalanítva** — ITT/XPO eltávolítva a `state/swing_positions.json`-ból
   (backup: `.bak-20260717-reconcile-ITTXPO`). A `next_action: TIME_STOP` flag flat pozíción MOC-shortot
   nyitott volna a 07-17 21:40 cronban. State: 6 → **4** (BIRK, PFGC, SLGN, USFD) ≡ IBKR 4 ✓.
2. **+$262.65 realizált bekönyvelve** — a 07-15-i manuális exit a proper mechanizmuson
   (`pending_exits` ledger 07-15 → `apply_pending_exits`, **broker_realized_pnl** ág, nem state-bázis):
   ITT +$211.61, XPO +$51.04. **cumulative_pnl.json: 228.69 → $491.34** (+0.491%), 07-15 daily_history
   sor létrejött (2 moc_exit). Idempotens (processed=True). A Gateway `reqExecutions` a 2 napos fillt nem
   érte el (0 execution boot után) → a broker realized számokat az IBKR `get_account_trades` (MCP) adta,
   penny-pontosan. **Tamás futtatta a Mini terminálban** (a ledger-write agent-guard alá esik).
3. **entry_price ≠ IBKR basis P1 rögzítve** (lásd lent) — a könyvelést nem érinti (broker-realized).

> **Guard-tanulság:** a Mini production-state írását két réteg védi — a permission-allowlist
> (`Bash(ssh ifds-mini:*)` hozzáadva) ÉS egy szemantikai auto-mode guard, ami az *agent-gépelte pénzügyi
> ledger-write*-ot allowlist ellenére is blokkolja. A P&L-számot érintő write ezért marad Tamás lane-je
> (Mini terminal), egyezik a CLAUDE.md-vel.

## Mi történt

- **2026-07-15 ~12:10 CEST** — a Mac Mini offline lett (Tailscale: `tamass-mac-mini … offline, last seen 1h ago`).
- **Ok:** áramszünet (Tamás megerősítette 13:1x-kor).
- **Diagnózis:** Tailscale (100.76.118.54) + LAN (192.168.0.115) + ping mind néma; a MacBook tailnet-je, az
  internet és a router rendben → maga a gép van lent. Lásd `[[mac-mini-connectivity]]`: mindkét path down =
  Mini down → fizikai (power-cycle) restart kell.
- **A 07-15 trading nap kiesik** (nincs Phase 4-6 @14:30, nincs submit @15:31, nincs eod_eval @22:00).

## Utolsó ismert jó állapot

- **Utolsó sync:** 2026-07-14T17:55:44Z (= 19:55 CEST). A 07-14 EOD adat (22:10 daily_metrics / 22:20
  review_data) **NEM került le** → lokálisan nincs meg.
- **Lokálisan meglévő 07-14 adat:** `state/uw_shadow/2026-07-14.json`, `state/phase4_snapshots/2026-07-14.json.gz`
  (14:31), `logs/pt_events_2026-07-14.jsonl` (15:31-ig).
- **Utolsó teljes review-adat:** `state/review_data/2026-07-13.json` (Day 38, cum. **$228.69 / +0.229%**).

### IBKR pozíciók — 2026-07-15 13:10 CEST (pre-market, MCP-n keresztül ellenőrizve)

`get_account_orders` → **`[]`** — nincs pihenő stop-order (architekturálisan helyes: a swing exit *mentális
stop*, a Mini-n futó `pt_monitor.py --mode=eod_eval` értékeli 22:00-kor).

| Ticker | Qty | Entry (avg) | Ár | Unrealized | held_trading (07-13) | Megjegyzés |
|---|---|---|---|---|---|---|
| ITT  |  26 | 183.97 | 194.92 | **+284.74** | 4 | ⚠️ max_hold 07-14-én |
| XPO  |  21 | 203.12 | 209.97 | **+143.90** | 4 | ⚠️ max_hold 07-14-én |
| PFGC |  62 | 115.27 | 112.98 | −141.74 | 3 | 07-15 lenne az 5. nap |
| BIRK |  84 |  45.14 |  44.36 | −65.68 | 3 | 07-15 lenne az 5. nap |
| SLGN | 120 |  44.71 |  44.70 | −1.00 | 1 | van tér |
| USFD |  56 | 102.60 | 101.00 | −89.48 | 0 (07-14 belépő) | stop 95.08 / tp1 105.98 / tp2 110.65 |

**Összes unrealized: +$130.74.** NetLiq (07-14 intraday, tájékoztató): $100,762.80.

## ✅ FELOLDVA — ITT / XPO manuális zárás (2026-07-15 17:52-17:53 CEST)

Tamás jóváhagyásával a két elakadt max_hold exit **manuálisan végrehajtva** (TradingView → IBKR Paper
integráció; a CC által előkészített `create_order_instruction` deep-linket nem használtuk, de a paraméterek
azonosak voltak). A két instrukció (id 100, 101) **törölve** — flat pozíciónál a beküldésük short-ot nyitott volna.

| Ticker | Fill | Idő (UTC) | Tőzsde | Komm. | Realized P&L | trade_id |
|---|---|---|---|---|---|---|
| ITT | SELL 26 @ **192.15** | 2026-07-15T15:52:51Z | NASDAQ | $1.108064 | **+$211.61** | `00025b45.6a5e39ae.01.01` |
| XPO | SELL 21 @ **205.60** | 2026-07-15T15:53:14Z | NYSE | $1.093101 | **+$51.04** | `00025b47.6a5723da.01.01` |

**Realizált összesen: +$262.65** (komm. $2.20). IBKR pozíció-verifikáció: ITT=0, XPO=0 ✓.
Maradó pozíciók: BIRK 84, PFGC 62, SLGN 120, USFD 56.

### ‼️ P1 (ÚJ) — state entry_price ≠ IBKR average_price

| | IFDS `entry_price` (07-13 review) | IBKR `average_price` | Eltérés |
|---|---|---|---|
| ITT | 190.07 | **183.97** | −6.10 |
| XPO | 206.78 | **203.12** | −3.66 |

Az IBKR `realized_pnl` a saját bázisával penny-pontosan kijön → **az IBKR az igazság**:
- ITT: (192.15 − 183.97) × 26 = 212.68 − 1.11 komm. ≈ **+211.61** ✓
- XPO: (205.60 − 203.12) × 21 = 52.08 − 1.09 komm. ≈ **+51.04** ✓

Az IFDS bázisán számolva **XPO −$24.78 veszteség** lenne (206.78 belépővel) a tényleges +$51.04 helyett —
**előjel-váltó eltérés**, nem kerekítési hiba.

**Hipotézis:** a 07-07-i manuális belépő (journal: *"ITT/XPO manuális belépő (Tamás GO, kedvező áron)"*) —
mindkét eltérés Tamás javára szól, ami ezzel egyezik. Vagyis a state a **tervezett** belépő árat rögzítette,
nem a **tényleges** fillt. **Verifikálandó** a Mini visszatérésekor: `get_account_trades(DAYS_30)` a 07-07-i
ITT/XPO BUY lábakra vs. `state/swing_positions` `entry_price`.

**Hatás:** ha a hipotézis igaz, minden manuálisan nyitott pozíció P&L-je téves bázison könyvelődik →
érinti a cumulative_pnl-t és a Day 63 gate-et. Rögzítendő §11 + Day 63 kiértékelés.

## (Történeti) P1 — ITT / XPO elakadt max_hold exit

`src/ifds/state/swing_manager.py:127`:
```python
if pos.hold_days >= cfg["max_hold_trading_days"]:   # 5
    → SwingDecision(action=MOC_EXIT, reason="max_hold")
```
Az exit **nem azonnal** hajtódik végre: a 22:00 eod_eval *flag*-el, és a **következő nap 15:30**-kor a
`close_positions.py --mode=eod_flags` adja be a market SELL-t.

**Következtetés:** ITT és XPO 07-13-án `days_held_trading=4` volt → **07-14-én elérték az 5-öt** → a 07-14
22:00 eval (a Mini ekkor még élt, ~12:10-ig fent volt) **max_hold exitre jelölte őket** → az exit **2026-07-15
15:30-kor futott volna** → **az áramszünet blokkolta**. Mindkettő nyitva maradt, együtt **+$428.64**
unrealized nyereséggel, amit a stratégia már realizálni akart.

**Verifikálandó a Mini visszatérésekor** (nem tudtam ellenőrizni, mert a `state/` a Mini-n van):
- `state/pending_exits/2026-07-14.json` (vagy a ledger) tartalmaz-e ITT + XPO `max_hold` flaget.
- Ha igen → ezek **lejárt, végre nem hajtott exitek**; a 07-16 15:30-i futás ezeket 2 nappal késve adná be.

## Holnapi (07-16) restart checklist

A 07-07-i restart mintáját követve (lásd `docs/journal/2026-07-11-session-close.md`):

1. **Mini fent van?** `ssh ifds-mini 'uptime'` — jegyezd fel a boot időt.
2. **Nincs orphan run?** `ps aux | grep -E "deploy_daily|deploy_intraday"` — lásd `[[ssh-prod-process-orphan]]`.
   Ha több `deploy_*.sh` fut: PID-alapú kill (NE `pkill -f`), majd egy tiszta run.
3. **Sync:** `./scripts/sync_from_mini.sh --dry-run` → deletions ellenőrzés → éles sync.
   Ez hozza le a **07-14 ÉS 07-15** adatot (ha van 07-15).
4. **pending_exits audit** (P1, fent): ITT/XPO `max_hold` flag ellenőrzése — az exit **már megtörtént
   manuálisan 07-15-én**, tehát a flageket lezártként kell könyvelni, nem újra végrehajtani.
   ⚠️ **A 07-16 15:30-i `close_positions.py --mode=eod_flags` futás NE adjon be újabb SELL-t ITT/XPO-ra**
   (flat pozíciónál az short-ot nyitna). A script `existing_skip` logikája ezt elvileg kezeli (a pozíció
   már nincs meg), de **futás előtt ellenőrizd**.
5. **Manuális fillek beírása a state-be:** ITT SELL 26 @ 192.15, XPO SELL 21 @ 205.60 (2026-07-15).
   A `state/swing_positions` még nyitottként tartja őket → a reconcile divergenciát fog jelezni
   (state: nyitva / IBKR: flat). **Ez várt, nem bug.**
6. **entry_price ≠ IBKR basis audit** (új P1, fent): `get_account_trades(DAYS_30)` a 07-07-i ITT/XPO BUY
   lábakra vs. `state/swing_positions.entry_price`.
7. **state ≡ IBKR reconcile:** a `qty_remaining` (NEM `qty`) mezőt olvasd — a 07-07-i téves „desync"-riasztás
   ebből eredt.
8. **IBKR Gateway** fut-e (clientId ütközés nélkül).
9. **Friss Phase 1-3 kontextus** kell-e (a 07-12 vasárnapi kontextus lehet elavult).
10. **07-14 review** → Chatnek átadható, amint a `state/review_data/2026-07-14.json` lejött.

## Minta-kontamináció (Day 63 gate)

A **2026-07-15 outage-nap** — a 06-29→07-07 precedens szerint (`docs/planning/2026-07-01-day126-replan-proposal.md`:
pause-and-resume, gate criteria UNCHANGED, outage-kontaminált pozíciók kizárva az edge-mintából) —
**kizárandó az edge-mintából**, és az **ITT/XPO 07-15-i manuális exit szintén kontaminált**: a stratégia
07-14 22:00-kor döntött a zárásról, a végrehajtás 07-15 15:30 helyett **17:52-53 CEST-kor**, kézzel történt.
A ~2 órás csúszás alatt mindkét papír esett (ITT −1.32%, XPO −2.01%) → a realizált **+$262.65** helyett az
automatizált 15:30-i exit vélhetően magasabb lett volna (a 13:10-es pre-market unrealized +$428.64 volt).
A különbség **outage-artifact, nem stratégia-jel** — a Day 63 edge-számításból kiveendő.

Rögzítendő: `docs/master-reference/04-risks-and-open-questions.md` §11 (freeze-log) + a Day 63 kiértékelésnél.

## Freeze státusz

Production-kód **fagyva Day 63-ig** — ez az outage **nem** indokol kódváltoztatást. A handoff dokumentum és a
§11 bejegyzés docs-only, freeze-safe.
