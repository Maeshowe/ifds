# Handoff — Log Review chat-nek (emergency procedure CC review)

**Created**: 2026-05-25 (CC kódbázis-verify session)
**Target**: Log Review chat (Claude — a DRAFT v1 szerzője)
**Purpose**: A `docs/tasks/2026-05-25-operator-emergency-procedure.md` DRAFT v1 → REVIEWED v1.1 átmenet rögzítése. CC technikai verify-t végzett a kódbázis ellen, és **4 csoportnyi javítást** alkalmazott in-place. Ez a doc a **diff-szintű audit** — visszanyitható egy következő DRAFT v2 iterációhoz, ha a Log Review chat-nek további pattern-tartalom-bővítést szeretne hozzáadni.

---

## 1. Mit verify-elt CC a kódbázis ellen

Verify metódus: grep + Read + `add_argument` parse, minden script-re egyenként.

| Komponens | Doc claim | Reality | Verdict |
|-----------|-----------|---------|---------|
| `nuke.py --state-only` | Létezik, csak `swing_positions.json` reset | **NEM létezik** | ❌ FIX |
| `nuke.py --full` | Létezik, mindkettő + `cumulative_pnl.json` reset | **NEM létezik** | ❌ FIX |
| `nuke.py --orders` | Nem említve | **LÉTEZIK** (csak orders cancel) | ➕ ADD |
| `nuke.py` állapot fájlok kezelés | `--state-only` és `--full` érintik | **EGYÁLTALÁN NEM nyúl** state-hez (zero match grep-re) | ❌ FIX |
| `check_gateway.py --verbose` | Létezik, részletes IBKR pozíció lista | **NINCS argparse** (csak smoke ping) | ❌ FIX |
| `pt_monitor.py::reconcile_state_from_ibkr` | Public function név | Valójában `_reconcile_state_from_ibkr` (underscore prefix = private) | ⚠️ RENAME |
| `submit_orders.py --resume` | Létezik | ✓ LÉTEZIK ([submit_orders.py:460](../../scripts/paper_trading/submit_orders.py#L460)) | ✓ OK |
| `submit_swing_market_only` | Létezik | ✓ LÉTEZIK ([submit_orders.py:195](../../scripts/paper_trading/submit_orders.py#L195)) | ✓ OK |
| `IBKRSubmitOrchestrator + SubmitExhaustedError + retry_delays` | Létezik | ✓ LÉTEZIK ([retry_orchestrator.py:54,79](../../scripts/paper_trading/lib/retry_orchestrator.py#L54)) | ✓ OK |
| Pattern 3 detect orphan child orders (§7.1) | Backlog enhancement a `_reconcile_state_from_ibkr`-ra | NEM van detect-elve, valódi backlog | ✓ OK (helyes backlog) |
| ClientId-k (submit=10, close=11, eod=12, nuke=13, monitor=14, gateway=17) | Verify-elve | ✓ OK | ✓ OK |
| Log path-ok (`logs/pt_*.log`, `logs/pt_nuke_*.log`) | Verify-elve | ✓ OK | ✓ OK |
| Telegram értesítés formátumok | Verify-elve | ✓ OK (format string egyezés) | ✓ OK |

**Összegzés**: 6 ténybeli hiba (3 critical = `nuke.py` flag-ek félrevezetők, 1 minor = `check_gateway.py --verbose` nem létezik, 1 naming = underscore prefix elveszett, 1 conceptual = `nuke.py` szerepe félrevezetve). **Minden más helyes.**

---

## 2. Applied edits (in-place)

### Edit 1 — Header status: DRAFT v1 → REVIEWED v1.1

```diff
- **Status**: DRAFT v1
- **Becsült munka**: ~1.5 óra Log Review chat-ben
+ **Status**: REVIEWED v1.1 (CC kódbázis-verify 2026-05-25)
+ **Becsült munka**: ~1.5 óra Log Review chat-ben + ~20 min CC kódbázis-verify
```

### Edit 2 — `reconcile_state_from_ibkr` → `_reconcile_state_from_ibkr` (replace_all)

5 hivatkozás javítva (§1, §2.4, §4.4 ×2, §7.1). A `_` prefix Python konvenció szerint **module-internal**, nem public API. Operator doc-ban a valódi név kell, hogy a grep megtalálja.

### Edit 3 — §5.1 step 2: `check_gateway.py --verbose` → no flag

```diff
- 2. **IBKR Positions ellenőrzése** (mit lát az IBKR vs a state-fájl):
-    ```bash
-    python scripts/paper_trading/check_gateway.py --verbose
-    ```
+ 2. **IBKR Positions ellenőrzése** (mit lát az IBKR pre-flight health check-en):
+    ```bash
+    python scripts/paper_trading/check_gateway.py
+    ```
+    A `check_gateway.py` **NEM fogad argumentumokat** — csak egy connectivity smoke (clientId=17, 3s timeout, 1 retry). A részletes IBKR pozíció-listához használd a TWS GUI **Account Window → Positions** tab-ot vagy egy egyszeri Python REPL-t:
+    ```bash
+    python -c "from ib_async import IB; ib = IB(); ib.connect('127.0.0.1', 7497, clientId=99); print(ib.positions()); ib.disconnect()"
+    ```
```

### Edit 4 — §5.1 step 3: scope tisztázás

Tisztázva, hogy a `nuke.py` **CSAK az IBKR oldalt** kezeli (orders + positions). State fájlok manuális reset-jéhez **NEM a `nuke.py` a megfelelő tool** — lásd új §5.4. Új flag-mátrix:

| Flag | Hatás | Use case |
|------|-------|----------|
| (nincs flag) | orders cancel + positions close | Full pánik-zárás (default) |
| `--orders` | csak orders cancel | Orphan bracket cleanup tömegesen |
| `--positions` | csak positions close | Pozíció-pánik, orders ÉRINTETLENÜL |
| `--dry-run` | csak audit print | Bármelyik fenti móddal kombinálható |

### Edit 5 — §5.2: teljes átírás verified parancsokra

3 fikciós blokk (`--state-only`, `--full`) helyett 4 valós példa (default, `--orders`, `--positions`, `--dry-run`). A `--positions` figyelmeztetés (orphan bracket-ek nincsenek cancellálva) megmaradt + tisztázva, hogy `--orders` vagy default módban ez nem probléma.

### Edit 6 — §5.3: post-nuke recovery újraírva

Mivel `nuke.py` nem ír state fájlt, a "State-fájl verify" lépés és "Cumulative P&L verify a `--full` mód esetén" lépések **fiktívek voltak**. Új verzió tisztázza:
- `nuke.py` futtatás **divergence-t okoz** state ↔ IBKR között
- Day 7+: `_reconcile_state_from_ibkr` automatikusan korrigálja a következő EOD eval-on
- Day 6 előtti `nuke.py`: `retroactive_reconcile_w21.py`-szerű utólagos reconcile szükséges

### Edit 7 — Új §5.4: State fájl reset (NEM `nuke.py`-vel)

Új szekció a doc-ban, ami megfogalmazza a separation of concerns elvet:
- `nuke.py` = IBKR oldal (orders + positions API-n keresztül)
- `retroactive_reconcile_w21.py` típusú script-ek = state oldal (JSON manipuláció)

Hivatkozás a `scripts/admin/retroactive_reconcile_w21.py` (517 sor, idempotens sentinel) script-re mint mintára egyedi reset-szükségletekre.

### Edit 8 — §8: capabilities → VERIFIED táblázat

`"A kódbázis-elemzés még szükséges"` jelölés törölve. Új tartalom:
- Verified `nuke.py` flag-tábla (3 flag, default behavior)
- Critical "NINCS state file írás" verify (grep output mellékelve)
- Egyéb scripts verified state táblázat (`submit_orders.py`, `check_gateway.py`, `pt_monitor.py::_reconcile_state_from_ibkr`, `lib/retry_orchestrator.py`, `submit_orders.py::submit_swing_market_only`)

### Edit 9 — §9: verzió-tábla bővítés

Hozzáadva a v1.1 (REVIEWED) sor az alkalmazott változtatások összefoglalójával.

---

## 3. Mit NEM módosított CC

- **§1 — Áttekintés** (Általános alapelv, Mikor használd, Mikor NE) — semmi szöveg-szintű változás
- **§2 — Pattern 1 (Error 354)** — semmi szöveg-szintű változás (csak `_reconcile_state_from_ibkr` rename a §2.4-ben)
- **§3 — Pattern 2 (Gateway timeout)** — semmi szöveg-szintű változás
- **§4 — Pattern 3 (Bracket cleanup)** — csak `_reconcile_state_from_ibkr` rename a §4.4-ben
- **§6 — Post-emergency checklist** — semmi változás
- **§7 — Új CC tasks következménye** — semmi szöveg-szintű változás
- **§9 utáni "Tervezett frissítések"** — semmi változás (továbbra is releváns a W22-W30 tervekre)

---

## 4. Mit javasol CC a DRAFT v2-ben (Log Review chat scope)

Ezek **NEM ténybeli hibák**, hanem **operator UX javítások**, amelyek a Log Review chat-i felülvizsgálattal kerülhetnek bele:

### 4.1 Új Pattern 5 javaslat — IBKR Gateway 2FA timeout

W21 incident NEM fordult elő, DE backlog idea: ha a Tamás-féle 2FA mobile prompt timeout-ol Gateway login-kor, mit kell csinálni? (Restart, Saved Credentials, vagy escalation a IBKR support-hoz.) Ez P3 / nice-to-have.

### 4.2 Pattern 3 — orphan detector backlog szétbontás

A doc §7.1 jelenleg egy nagy Pseudo-code blokkal javasolja az orphan child order detect-et. A Log Review chat felbonthatná **két scope-ra**:
- (a) Detect-only (WARNING Telegram, kézi cancel marad) — könnyű, ~30 min
- (b) Auto-cancel mode (config flag mögött) — kockázatosabb, ~1.5h

### 4.3 §5.3 ⚠️ kockázat-leírás bővítés

A `nuke.py` futtatás után a state ↔ IBKR divergence **mennyi időre lehet veszélyes**? (Pl. ha Day 4-en futtatod a `nuke.py`-t és 22:00-ig nem fut `_reconcile_state_from_ibkr` mert még Day 7 előtt vagy, a `pt_submit` Day 5 reggel mit tesz a stale state-tel?) Ezt a kérdést a Log Review chat-i felülvizsgálat világosíthatja.

### 4.4 Pattern 1 (Error 354) — historical referencia tisztítás

A 2026-05-20 (Day 3) Error 354 incident **megoldva** a Workstation Configuration "Bypass Order Precautions" toggle-lel. A doc §2.4 hivatkozása "**Day 7+ napokon**" automatikus, de **Day 6 előtti** Error 354 a swing pivot architektúrában **nem várt** (nincs new entry). A Log Review chat egyszerűsítheti vagy archive-olhatja ezt a pattern-t (mint a `04-risks` §0.4-be visszahúzott "ritka esemény" entry).

---

## 5. Output deliverable summary

**Module:** `docs/tasks/2026-05-25-operator-emergency-procedure.md`
**Version:** DRAFT v1 → **REVIEWED v1.1** (CC kódbázis-verify)
**Lines:** 463 → ~510 (új §5.4 + §8 verified tábla)
**Critical fixes:** 6 (3 `nuke.py` flag, 1 `check_gateway.py`, 1 underscore prefix, 1 scope clarification)
**No breaking changes** — minden Tamás-féle Pattern 1-4 workflow változatlanul érvényes, csak a parancs-példák lettek pontosak.

**Recommended next:** Log Review chat felülvizsgálja a §4 javaslatokat a v2-re (P3 doc-task ütemterv W22-W26 időszakra).

---

**Doc vége.**
