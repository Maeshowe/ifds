# Day 126 újratervezés — javaslat (Mini-outage 2026-06-29 → 07-07)

Status: PROPOSAL — Dev-chat + Tamás döntési input
Updated: 2026-07-01
Note: CC-készített, **stratégiai döntés a Dev-chat/Tamás-é**. CC nem módosít pre-reg
gate-kritériumot; ez a javaslat a döntéshez ad strukturált keretet + restart-runbookot.

> **Lane**: a Day 126 milestone újratervezése kanonikusan stratégiai (Dev-chat + Tamás).
> Ez a doc a Tamás által CC-nek adott közvetlen kérésre készült — **döntési input**,
> nem végleges re-plan. A dátumokat/kritériumokat a Dev-chat + Tamás hagyja jóvá.

---

## 1. Helyzet (2026-07-01, a Mini nem elérhető)

- **Mini down 2026-06-29 (hétfő) óta**, ma 07-01. Restart tervezett: **2026-07-07 (kedd)**,
  „ha nincs nagyobb baj".
- **Elvesztett trading napok (5)**: 06-29, 06-30, 07-01, 07-02, 07-06.
  (07-03 péntek **piaci ünnep** — Independence Day observed [júl 4 = szombat] — nem
  trading nap, nem „elveszett".)
- **Swing paper run állapota** (utolsó synced adat, 06-26): Day 1 = 2026-05-18,
  **trading_days = 28**, cumulative **+$540.05 (+0.54%)**.
- **8 nyitott pozíció, kezeletlen a kiesés alatt** (nincs time-stop / mental-stop /
  TP eval a Mini nélkül). IBKR-ból verifikálva (07-01): mind a 8 nyitva, össz.
  unrealized ≈ **+$382**.

| Ticker | Entry | Trading nap 07-07-re | IBKR qty | Lokális state qty | Megjegyzés |
|---|---|---|---|---|---|
| AXTA | 06-18 | ~12 | 146 | 146 | |
| RBC | 06-22 | ~9 | **5** | **9** ⚠️ | 06-26 TP1 −4 nincs a lokál state-ben |
| IEX | 06-22 | ~9 | 33 | 33 | |
| NSA | 06-23 | ~8 | 150 | 150 | |
| R | 06-23 | ~8 | 22 | 22 | |
| TDG | 06-24 | ~7 | **2** | **4** ⚠️ | 06-26 TP1 −2 nincs a lokál state-ben |
| PFGC | 06-25 | ~6 | 63 | 63 | |
| SLGN | 06-25 | ~6 | 128 | 128 | |

**Két probléma azonnal látszik:**
- **(P1) State-desync**: a lokális `swing_positions.json` (06-26) RBC=9/TDG=4/tp1_done=None,
  de az IBKR RBC=5/TDG=2 — a 06-26-i TP1-partialök nincsenek a lokál swing-state-ben.
  (A Mini-oldali state lehet, hogy helyes — nem tudom ellenőrizni, a Mini down.)
- **(P2) Mind a 8 pozíció túllépi az 5-napos time-stopot 07-07-re** — a kiesés miatt
  kényszerhold (6–12 trading nap), NEM a tervezett 5-napos swing.

---

## 2. Hatás

### 2.1 Timeline (Day 63 / Day 126 dátum)
- A swing run **63 AKTÍV trading napból** áll — a kiesés **pause**, nem csökkenti a
  63-as követelményt, csak **későbbre tolja** a naptári dátumot **~5 trading nappal**
  (+ a júl 4 ünnep-hét zavarása). Delta: **~1–1.5 hét csúszás.**
- ⚠️ **Definíciós kétértelműség tisztázandó**: a Day 63 outcome doc a „Day 126"-ot és
  az „új Day 63 milestone"-t ugyanarra a **~2026-09-15 (W37)** dátumra teszi (§7, §3.14),
  a kritériumok viszont „Sharpe 60 napi" + „25/63 nap" (63-napos ablak). A saját
  trading-nap-számolásom a **swing Day 63-ra ~2026-08-17-et** ad (28. nap = 06-26 +
  35 aktív nap). **A ~09-15 becslés és a ~08-17 számolás nem egyezik** — a pontos
  definíciót (swing Day 63 vs 126 trading nap a swing Day 1-től) és a bázis-dátumot
  **Dev-chat/Tamás tisztázza**. A kiesés-delta (~+5 trading nap) **bármelyik bázisra
  ugyanaz**.

### 2.2 Minta-integritás
- **A 8 kényszerhold-pozíció NEM tiszta swing** (6–12 nap tartás az 5 helyett a kiesés
  miatt). A kimenetük torzított — az edge-attribúcióba **nem valók** (a `signal_attribution`
  clean-sample fegyelmével konzisztens: outage-kontaminált).
- **~5 trading nap ÚJ belépő kiesett** (06-29 → 07-06 nincs új pozíció) → a tiszta
  swing-minta enyhén csökken. Ez **erősíti a vékony-n figyelmeztetést** (04-risks §6.6
  guardrail) — a Day 63/126 olvasat **IRÁNY, nem bizonyíték** marad.

---

## 3. Döntési pontok (Dev-chat + Tamás sign-off)

**D1 — A kiesés kezelése a mintában.**
- **(A) Pause & resume [JAVASOLT]**: a 63-as szám = 63 AKTÍV trading nap; a kiesés
  pause, nem számít. A 28 nap tiszta adat (+$540) megmarad. Day 63 dátuma ~1–1.5 hét
  csúszik.
- (B) Teljes restart (Day 1 reset 07-07): eldobja a 28 nap érvényes adatot — **NEM
  javasolt**.
- (C) Naptár-alapú számolás: elveti, mert 63 adat-nap kell iránytól függetlenül.

**D2 — A 8 kényszerhold-pozíció (07-07).**
- **(a) Restartkor mind exit + edge-mintából kizár [JAVASOLT]**: a time-stop eval
  úgyis flag-eli mind a 8-at (túl az 5 napon). Exit a normál úton; a realized P&L
  **beszámít az account/cumulative-ba** (valós pénz), de a pozíciók **outage-kontamináltként
  kizárva az edge/jel-érvényességi mintából**.
- (b) Egyenkénti eval — de mind past time-stop, így az exit a design-konzisztens lépés.

**D3 — Milestone dátum + kritériumok.**
- **Dátum**: a Day 63/126 dátuma **~+5 trading nappal csúszik** (a bázis tisztázása
  után pontosítandó a NYSE-naptárral).
- **Kritériumok: VÁLTOZATLANOK** (pre-reg fegyelem — a kiesés NEM indokol lazítást):
  cum > +$2,000, Sharpe(60d) > 0.5, pozitív-excess napok > 25/63. Early-stop:
  10-napi excess < −1.0%.
- **Guardrail**: az outage-kontaminált pozíciók kimenete NEM torzíthatja az edge-olvasatot
  (kizárás, mint fent). Az account-P&L tartalmazza (valós), de a Sharpe/edge-attribúció
  jelöli a kontaminációt.

---

## 4. Restart runbook — 2026-07-07 (Tamás, Mini terminal)

**Sorrend kötött — a reconcile ELŐBB, mint bármilyen eval:**

1. **Gateway/IBKR health**: `check_gateway.py` → „Gateway OK". Ha nem: a „nagyobb baj"
   ág — ne indíts pipeline-t, diagnózis előbb.
2. **State≡IBKR reconcile ELSŐ**: a `reconcile_state.py` (vagy `pt_monitor --reconcile`)
   futtatása, hogy a `swing_positions.json` az IBKR-hoz igazodjon — **kritikus a P1
   desync miatt** (RBC 9→5, TDG 4→2, tp1_done jelölés). Verifikáld: state qty == IBKR qty
   mind a 8-ra.
3. **„Nagyobb baj" check**: hasonlítsd a mai IBKR pozíciókat a 07-01-i baseline-hoz
   (8 pozíció, a fenti tábla qty-jai). Ha eltérés van (váratlan fill/close a kiesés
   alatt) → állj meg, vizsgáld.
4. **Time-stop eval → a 8 stale pozíció exit** (D2/a): `close_positions --mode=time_stop`
   (vagy eod_flags a napszaktól függően). Mind a 8 past-time-stop → MOC/MKT exit.
   A realized P&L a cumulative-ba; a pozíciók edge-mintából kizárva (jelöld a ledgerben
   / a Day 63 analízisben).
5. **Cumulative-folytonosság**: a kiesés-napok (06-29→07-06) **no-entry, no-exit** → a
   cumulative a gapen át lapos (leszámítva a 8 pozíció exitkor realizálódó unrealized-jét).
   Verifikáld a `cumulative_pnl.json` folytonosságát (nincs fantom-nap, trading_days
   helyes).
6. **Normál pipeline resume 07-07-től**: Phase 1-6 + submit a szokásos crontab szerint
   (a kiesés-napokat NEM pótoljuk vissza — nincs backfill-belépő).

---

## 5. Guardrailek (freeze + pre-reg)

- **Production-kód fagyott Day 63-ig** — ez a re-plan **nem** kódmunka; a restart
  operatív (Tamás). Ha a reconcile-robusztusság igényel kód-fixet (a P1 desync
  általánosítása), az **Dev-chat-döntés** + külön task, nem itt.
- **Pre-reg fegyelem**: a gate-kritériumok NEM lazulnak. A kiesés dátum-csúszást +
  minta-higiéniát (kontaminált kizárás) indokol, NEM küszöb-módosítást.
- **Aszimmetria (04-risks §6.6 mintájára)**: a csökkent tiszta-n miatt a Day 63/126
  olvasat IRÁNY marad; sem a kedvező, sem a kedvezőtlen swing-eredmény nem csúszhat
  „bizonyítékként" a kapuba a pre-reg úton (signal_attribution) kívül.

---

## 6. Nyitott kérdések a Dev-chatnek

1. **Day 126 definíció**: swing Day 63 (=126 total) VAGY 126 trading nap a swing Day
   1-től? A ~09-15 becslés vs ~08-17 számolás feloldása.
2. **A 8 kontaminált pozíció**: exit-all restartkor (D2/a) elfogadva? A kizárás módja
   az edge-mintából (ledger-flag vs analízis-szűrő)?
3. **Kell-e a reconcile-robusztusság kód-fix** (P1 desync) Dev-chat-taskként, vagy a
   meglévő reconcile elég a restartra?
