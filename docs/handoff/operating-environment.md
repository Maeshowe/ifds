# IFDS Működési Környezet — Operating Environment Reference

**Created**: 2026-05-26 (kedd) ~10:15 CEST
**Status**: LIVING DOCUMENT (frissítendő, ha az infrastruktúra változik)
**Purpose**: A két-gépes IFDS infrastruktúra (MacBook DEV + Mac Mini PROD) szerepének, sync-mechanizmusának, és operatív részleteinek dokumentálása. Új chat session-ök ezt olvassák be elsőként a kontextushoz.
**Audience**: Log Review chat, Swing Pivot Dev chat, CC, Tamás — minden szereplő, aki az IFDS rendszerrel dolgozik.

---

## 1. Áttekintés — két gép, három actor

Az IFDS rendszer **két fizikai gépen** fut, három logikai szereplővel:

```
┌─────────────────────────┐         ┌──────────────────────────┐
│      MacBook (DEV)      │  git +  │     Mac Mini (PROD)      │
│                         │  rsync  │                          │
│  • Fejlesztés (VSCode)  │ ◄─────► │  • Pipeline cron         │
│  • CC implementáció     │         │  • IBKR Gateway          │
│  • Log review (Claude)  │         │  • Paper trading engine  │
│  • Doc szerkesztés      │         │  • State source-of-truth │
└─────────────────────────┘         └──────────────────────────┘
         ▲                                       ▲
         │                                       │
         │           ┌──────────────┐            │
         └──────────►│    Tamás     │◄───────────┘
                     │  Manual ops  │
                     │  + decisions │
                     └──────────────┘
```

**Filesystem-first sync alapelv**: a két gép **NEM kommunikál egymással közvetlenül** (sem MCP, sem socket szinten). A kommunikáció **mindig a filesystem-en keresztül** történik:

- **MacBook → Mac Mini**: `git push origin master` (MacBook) → `git pull` (Mac Mini, Tamás kézzel)
- **Mac Mini → MacBook**: `scripts/sync_from_mini.sh` (MacBook, Tamás kézzel, általában 22:00 CEST után)

A két chat (Log Review + Swing Pivot Dev) **ugyanúgy filesystem-first sync-et használ** — soha nem üzennek egymásnak közvetlenül, csak a `docs/` mappán keresztül.

---

## 2. MacBook — Development Environment

### 2.1 Szerep

A **MacBook a fejlesztői gép**:
- **Kódfejlesztés**: CC (Claude Code VSCode extension) implementáció, manuális kód-review
- **Doc szerkesztés**: a Log Review chat és a Swing Pivot Dev chat a `docs/` mappát írja
- **Daily review írás**: a Log Review chat a `docs/review/YYYY-MM-DD-daily-review.md` fájlokat ide írja
- **Git commit + push**: minden CC commit a MacBook-on születik, push-szal kerül a remote-ra
- **Audit cél**: a MacBook állapota **általában 1 nap késéssel** szinkronizál a Mac Mini-vel

### 2.2 Tartalom (mit tárol)

- **Kódbázis** (`~/SSH-Services/ifds/`):
  - Python pipeline (`scripts/`, `src/ifds/`)
  - Tesztek (`tests/`)
  - Dokumentáció (`docs/`)
- **Dokumentáció** — ez a MacBook **fő szerepe** a Log Review chat számára:
  - `docs/review/YYYY-MM-DD-daily-review.md` (Log Review chat írja)
  - `docs/tasks/*.md` (Swing Pivot Dev chat írja, CC implementálja)
  - `docs/master-reference/` (élő dashboard)
  - `docs/handoff/` (chat-váltási handoff dokumentumok)
  - `docs/decisions/` (architektúra-döntések)
- **Logs (stale másolat)**: a `logs/` mappa **a Mac Mini-ről szinkronizálódik** (csak audit cél, nem itt futnak a script-ek)
- **State fájlok (stale másolat)**: a `state/` mappa szintén **Mac Mini-ről másolt** (audit cél)

### 2.3 Tools

| Tool | Szerep |
|------|--------|
| **VSCode + Claude Code extension** | CC implementáció (Python kódolás, tesztelés, commit) |
| **Claude.ai web app** | Log Review chat + Swing Pivot Dev chat (filesystem MCP-vel olvas/ír) |
| **Terminal + git** | Manuális commit kontroll (ritkán), `git push origin master` |
| **`scripts/sync_from_mini.sh`** | Mac Mini → MacBook szinkronizáló script (Tamás futtatja) |

### 2.4 Mit NEM csinál a MacBook

- **NEM futtat pipeline cron-t** — a paper trading engine **kizárólag a Mac Mini-n** fut
- **NEM csatlakozik az IBKR Gateway-hez** — az IBKR API kliens csak a Mac Mini-n él
- **NEM source-of-truth a state-re** — a `state/swing_positions.json` MacBook-on egy **audit-másolat**, a canonical állapot a Mac Mini-n van

### 2.5 Filesystem szerkezet (MacBook)

```
/Users/safrtam/SSH-Services/ifds/         ← projekt gyökér
├── .claude/                              ← CC slash commands + rules
├── .venv/                                ← Python venv (helyi)
├── docs/                                 ← DOKUMENTÁCIÓ (fő MacBook tartalom)
│   ├── review/                          ← daily review fájlok
│   ├── tasks/                            ← CC task fájlok
│   ├── master-reference/                ← élő dashboard
│   ├── handoff/                          ← chat-handoff dokumentumok
│   │   └── prompts/                      ← rendszer-prompt minták
│   ├── decisions/                        ← architektúra-döntések
│   ├── design/                           ← design dokumentumok
│   ├── planning/                         ← backlog
│   ├── strategic-review/                 ← stratégiai felülvizsgálatok
│   ├── analysis/                         ← elemzések, heti összefoglalók
│   │   └── weekly/                      ← heti összefoglalók (2026-W21.md, ...)
│   ├── journal/                          ← CC session-close summaries
│   ├── qa/                               ← QA audit outputs
│   └── presentations/                    ← prezentációk
├── scripts/
│   ├── admin/                            ← egyszeri admin script-ek
│   │   └── retroactive_reconcile_w21.py
│   ├── paper_trading/                    ← pipeline engine
│   │   ├── pt_monitor.py
│   │   ├── submit_orders.py
│   │   ├── close_positions.py
│   │   ├── daily_metrics.py
│   │   ├── weekly_metrics.py
│   │   ├── nuke.py
│   │   ├── check_gateway.py
│   │   ├── reconcile_state.py
│   │   ├── lib/                          ← közös library-k
│   │   │   ├── ibkr_reconciliation.py
│   │   │   ├── connection.py
│   │   │   ├── orders.py
│   │   │   └── ...
│   │   └── logs/                         ← pipeline logok (stale másolat)
│   └── sync_from_mini.sh                 ← Mac Mini → MacBook szinkronizáló
├── src/ifds/                             ← Python package (Phase 0-6 logika)
├── state/                                ← state fájlok (stale másolat)
│   ├── swing_positions.json
│   ├── daily_metrics/                    ← YYYY-MM-DD.json fájlok
│   ├── phase4_snapshots/
│   ├── uw_shadow/
│   └── backups/                          ← retroaktív backup fájlok
├── tests/                                ← pytest tesztek
├── output/                               ← Phase 6 output (execution_plan_*.csv)
└── logs/                                 ← cron logok (stale másolat)
```

---

## 3. Mac Mini — Production Environment

### 3.1 Szerep

A **Mac Mini a production gép**:
- **Cron-driven pipeline futtatás**: Phase 0-6 napi 14:30-22:15 CEST között
- **IBKR Gateway**: csatlakozás a Interactive Brokers paper account-hoz (DUH118657)
- **Paper trading engine**: state-vezetés, order beadás, position monitoring
- **State source-of-truth**: a `state/swing_positions.json` és `cumulative_pnl.json` **kanonikus állapota itt él**
- **Logs forrása**: minden pipeline log itt keletkezik (`logs/`, `scripts/paper_trading/logs/`)

### 3.2 Crontab (cron entries — Day 7 reggeli ellenőrzés szerint)

A `crontab -l` ellenőrzött entries (Mac Mini):

```cron
# Swing pivot architektúra (W21+)
31 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/submit_orders.py
 0 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/pt_monitor.py --mode=eod_eval
10 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/daily_metrics.py

# Inaktív (kommentelve):
# */5 16-21 * * 1-5 .venv/bin/python scripts/paper_trading/pt_monitor.py  ← legacy 5-perces monitor
```

### 3.3 ⚠️ Nyitott crontab kérdések (Day 7 reggeli verify után)

A teljes crontab-ot **NEM** ellenőriztük a Day 7 reggelen, csak a 4 fő minta-grep-pel. **Hiányzó/megerősítendő entries**:

#### 3.3.1 Phase 0-3 cron (14:30 CEST)

A swing pivot pipeline Phases 0-6 (BMI rezsim, univerzum, sector rotation, Phase 4 scoring, Phase 5 GEX shadow, Phase 6 sizing) **valahol kell hogy fusson** 14:30 körül, hogy a 15:31 `submit_orders.py` cron-nak legyen output (`output/execution_plan_run_*.csv`).

**Lehetséges helyek**:
- `cron_intraday.sh` shell-script (külön cron entry-ben)
- `scripts/phases/run_all.py` (vagy hasonló név)
- Egy másik cron entry pl. `30 14 * * 1-5 cd ... && .venv/bin/python ...`

**Verify parancs Tamás-tól**: `crontab -l | grep -v '^#'` (a teljes nem-kommentelt lista)

#### 3.3.2 `weekly_metrics.py` cron

A heti aggregát futás **NINCS** a 4-grep-pel ellenőrzött listában. Két lehetőség:

- (a) Külön cron entry **csak péntek záró napokon**: `15 22 * * 5 ...`
- (b) A `daily_metrics.py`-ból automatikusan hívva, péntek napon

**Verify parancs**: `crontab -l | grep -i weekly`

**Fallback (ha nincs cron)**: manuális futtatás péntek estén:

```bash
ssh ifds-mini "cd ~/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/weekly_metrics.py --week 2026-W21"
```

#### 3.3.3 `reconcile_state.py` 22:15 cron

Eredetileg a `reconcile_state.py` egy passzív divergence detektor volt (Day 1 motivációval — `docs/handoff/operating-environment.md` § érintetlen). Most a `pt_monitor.py::_reconcile_state_from_ibkr` (Rész 1) átveszi a fő szerepet a 22:00 EOD eval-ban. **A 22:15 cron továbbra is futhat** mint backup detector, de a Mac Mini-i crontab-ban ezt NEM verify-oltuk a Day 7 reggelen.

### 3.4 IBKR Setup

| Komponens | Részlet |
|-----------|---------|
| **Paper Account** | DUH118657 |
| **Gateway/TWS** | IBKR Gateway (futás Mac Mini-n, port 7497 paper) |
| **Workstation** | TWS opcionális (Tamás kézi műveletekhez, manuális order entry) |
| **API connection** | `ib_insync` Python library, `lib/connection.py::connect(client_id=N)` |
| **Permissions** | "Bypass Order Precautions for API Orders" engedélyezve (Error 354 fix után) |

**IBKR Gateway életciklus**:
1. **Indítás**: Mac Mini boot után **manuálisan** vagy launchd-vel (Tamás futtatja: `open -a "IBKR Gateway"`)
2. **Bejelentkezés**: Paper Account credentials + esetleg 2FA mobile prompt
3. **Connection check**: `scripts/paper_trading/check_gateway.py` (pipeline indítás előtt heartbeat)
4. **Disconnect**: napi automatikus reauthentication ablak (általában 04:00-04:30 ET között, Mac Mini Gateway konfigurációja szerint)

### 3.5 Filesystem szerkezet (Mac Mini)

A Mac Mini filesystem **megegyezik a MacBook-éval** (`/Users/safrtam/SSH-Services/ifds/`). **Különbség**:

- **Mac Mini source-of-truth a state-re**: a `state/swing_positions.json`, `cumulative_pnl.json`, `daily_metrics/*.json` **kanonikus állapota itt él**
- **Mac Mini source-of-truth a logokra**: a `logs/`, `scripts/paper_trading/logs/` **éjjel-nappal generálódnak a cron-ok által**
- **A `docs/` mappa**: a Mac Mini-n is megvan, **de csak git pull-tal frissül** (NEM a fejlesztői tartalom forrása)

---

## 4. Sync mechanizmus

### 4.1 MacBook → Mac Mini (kód-deploy)

**Workflow**:

1. **MacBook**: CC implementál + commit (`git commit -m "feat: ..."`)
2. **MacBook**: `git push origin master` (Tamás vagy automatizált)
3. **Mac Mini**: `ssh ifds-mini "cd ~/SSH-Services/ifds && git pull"` (Tamás manuális)
4. **Mac Mini**: a következő cron futáskor az új kód él

**Példa (2026-05-25 vasárnap deploy)**:

```bash
# MacBook (Tamás):
cd ~/SSH-Services/ifds
git push origin master   # commits: 55e5ff2, 5c8e79a, f1b6acd

# Mac Mini (Tamás):
ssh ifds-mini "cd ~/SSH-Services/ifds && git pull"
# A Mac Mini-n most már él az új kód
```

### 4.2 Mac Mini → MacBook (state + log sync)

**Workflow**: a `scripts/sync_from_mini.sh` shell-script futtatása MacBook-on.

**Mit szinkronizál** (a script tartalma alapján, ami a MacBook-on van):

- `state/swing_positions.json` (production állapot)
- `state/daily_metrics/YYYY-MM-DD.json` (napi metrikák)
- `state/uw_shadow/YYYY-MM-DD.json` (UW shadow log)
- `state/phase4_snapshots/` (Phase 4 snapshot fájlok)
- `scripts/paper_trading/logs/` (pipeline log fájlok)
- `logs/` (cron log fájlok)
- `output/execution_plan_run_*.csv` (Phase 6 execution plan output)

**Mit NEM szinkronizál**:
- `docs/` (a MacBook a fejlesztői source — a Mac Mini csak git pull-tal frissít)
- `src/`, `scripts/` Python kód (git-en keresztül szinkron)
- `tests/` (git-en keresztül)
- `.venv/`, `__pycache__/`, `*.pyc` (egyenként generálva, nem szinkron)

**Mikor futtatandó**: **manuálisan, általában 22:30 CEST után** (a Mac Mini 22:15-i cron-ok után). **NEM automatizált** — szándékos, hogy Tamás kontrollálja mikor frissül a MacBook audit-másolata.

### 4.3 Git workflow

```
MacBook              GitHub remote           Mac Mini
   │                       │                     │
   │  git commit           │                     │
   │  git push origin ─────┤                     │
   │                       │                     │
   │                       │◄──── git pull ──────┤
   │                       │                     │
   │  (further dev cycle)  │                     │
```

**Branch policy**:
- **Master**: a fő branch, minden CC commit ide kerül
- **Topic branches** (`fix/...`, `feat/...`): ritkán, csak komplex feature-ekhez
- **NINCS pull request workflow** — Tamás manuálisan engedélyezi a commit-ot (CC `/commit` slash command → quality gates → conventional commit → push approval)

---

## 5. A 3 actor szerepe

### 5.1 Tamás (Product Owner)

- **Manual operations**:
  - `nuke.py` futtatás (rendkívüli helyzet)
  - IBKR Workstation manuális order entry (Error 354 workaround mint Day 3 minta)
  - IBKR Workstation bracket cancel (mint Day 6 reggeli CNC cancel)
  - Manuális fill ár rögzítés (ritka eset)
- **Strategic decisions**: architektúra-döntések, prioritás-megválasztás, GO/NO-GO élesítés
- **Git workflow**: `push` MacBook-ról, `pull` Mac Mini-n
- **Sync**: `sync_from_mini.sh` futtatás
- **Tools**: Mac Mini terminal (SSH), MacBook terminal, VSCode, IBKR TWS

### 5.2 Chat (Claude) — két parallel session

**Session A: Log Review chat** (Claude.ai web app)
- Daily review írás (`docs/review/YYYY-MM-DD-daily-review.md`)
- Weekly summary (`docs/analysis/weekly/YYYY-WNN.md`) — manuális vagy CC futtatott
- Strukturális anomaliák detektálása, surfacing a backlog-ra
- **Mode**: STRICT READ-ONLY a production filesystem-re (kivéve `docs/review/`, `docs/handoff/`)
- **Tool**: Filesystem MCP (MacBook fájlrendszerre)

**Session B: Swing Pivot Dev chat** (Claude.ai web app)
- CC task fájlok írása (`docs/tasks/*.md`)
- Design docs (`docs/design/`)
- Architektúra-döntések (`docs/decisions/`)
- Cross-chat handoff prompt-ok (`docs/handoff/prompts/`)
- **Mode**: Read-write `docs/tasks/`, `docs/design/`, `docs/decisions/`, `docs/master-reference/`, `docs/planning/`, `docs/STATUS.md` és `docs/handoff/`

**Cross-chat sync rule** (KRITIKUS):
- A két chat **NEM kommunikál egymással közvetlenül**
- **A filesystem az egyetlen kommunikációs csatorna**
- Pl. Log Review chat detected anomalia → `04-risks-and-open-questions.md` új entry → Swing Pivot Dev chat következő session-kor olvassa
- **Urgent P0 escalation**: Log Review chat egy P0 entry-t ír `04-risks` legtetejére + flagel a chat response-ban, hogy Tamás manuálisan tájékoztassa a Dev chat-et

### 5.3 Claude Code (CC) — implementáció

- **Mode**: VSCode extension, MacBook-on fut
- **Tools**: Read, Edit, Bash, Glob, Grep, WebSearch, slash commands (`/continue`, `/develop`, `/wrap-up`, `/commit`, `/decide`, `/review`)
- **Workflow**:
  1. Dev chat task fájlt ír `docs/tasks/`-ba
  2. Tamás `/continue` vagy `/develop`-vel indítja CC-t a MacBook-on
  3. CC Research → Plan → Implement → Commit ciklust végez
  4. CC `/commit`-tal a conventional commit-ot beadja, Tamás push-olja
- **Integrált Code QA**: a CC magában foglal kód-review-t (NEM külön QA chat)

---

## 6. Operational patterns

### 6.1 Normál napi ciklus

```
14:30 CEST   Mac Mini cron → Phase 0-3 pipeline
15:31 CEST   Mac Mini cron → submit_orders.py
21:40 CEST   Mac Mini cron → close_positions.py
22:00 CEST   Mac Mini cron → pt_monitor.py --mode=eod_eval ⭐ (reconcile + mental-stop eval)
22:10 CEST   Mac Mini cron → daily_metrics.py
22:15 CEST   Mac Mini cron → reconcile_state.py (passzív backup detector)
22:15 CEST   ❓ Mac Mini cron → weekly_metrics.py (péntek napokon, megerősítendő)
22:30 CEST   Tamás manuálisan → sync_from_mini.sh (MacBook felzárkózik)
22:45+ CEST  Új Log Review chat session (friss kontextusból)
             → daily review írás docs/review/YYYY-MM-DD-daily-review.md
```

### 6.2 Hétvégi ciklus

- Péntek 22:30 után: Log Review chat **W21/W22/... weekly summary**
- Hétvége: NEM fut pipeline cron, Tamás pihen
- Hétfő (vagy hétfő utáni első kereskedési nap) 14:30: új ciklus indul

### 6.3 USA ünnepnap kezelés (mint Day 6 USA Memorial Day)

- Crontab `1-5` (hétfő-péntek) szerint **a Mac Mini cron-ja fut**, DE a piac zárva
- A `submit_orders.py` `is_trading_day()` ellenőrzés (Tamás `lib/trading_day_guard.py`) — ha NEM trading day → korai exit, NO-OP
- A `pt_monitor.py --mode=eod_eval` is futhat, de NEM ad trading-relevant output-ot
- `daily_metrics.py` NEM létrehoz fájlt (vagy üres metrikát, megfigyelhetõ)

---

## 7. Recovery / Disaster Recovery

### 7.1 Egy commit hibás

**Lépések**:
1. MacBook-on: `git revert <commit-sha>` + `git push origin master`
2. Mac Mini-n: `ssh ifds-mini "cd ~/SSH-Services/ifds && git pull"`
3. A revert commit a következő cron futáskor él

### 7.2 State corruption

**Lépések**:
1. Mac Mini-n backup-ból restore: `cp state/swing_positions.json.bak.YYYYMMDD_HHMMSS state/swing_positions.json`
2. Cumulative pnl restore: `cp scripts/paper_trading/logs/cumulative_pnl.json.bak.YYYYMMDD_HHMMSS scripts/paper_trading/logs/cumulative_pnl.json`
3. Következő 22:00 EOD eval-on a `_reconcile_state_from_ibkr` autonóm korrigál

### 7.3 IBKR Gateway disconnect

Lásd: `docs/tasks/2026-05-25-operator-emergency-procedure.md` Pattern 2 (Gateway timeout) és `04-risks` §0.5.

### 7.4 Mac Mini hardver hiba

**Worst case scenario**: ha a Mac Mini elromlik, a fejlesztés folytatódhat MacBook-on, **de a paper trading megáll** (Gateway + cron stop). Recovery plan: új Mac Mini + git clone + venv + crontab + Gateway setup → vissza kell hozni a Day 7-i állapotba.

A `state/` mappa MacBook-on csak audit-másolat, de a `state/swing_positions.json.bak.*` fájlok és a `cumulative_pnl.json` lehetővé teszik a state retrokonstrukcióját, **ha a sync_from_mini.sh időben futott**.

---

## 8. ❓ Open questions a Mac Mini setup-re

Az alábbi részletek a Day 7 reggeli verify-ig **NEM voltak teljesen tisztázva**:

| # | Kérdés | Hol verify-andó | Várt válasz |
|---|--------|------------------|--------------|
| 8.1 | Phase 0-3 cron entry | `crontab -l \| grep -v '^#'` Mac Mini-n | Külön sor, ~14:30 CEST |
| 8.2 | `weekly_metrics.py` cron | `crontab -l \| grep -i weekly` Mac Mini-n | Péntek-csak entry, vagy `daily_metrics.py` belső hívás |
| 8.3 | `reconcile_state.py` 22:15 cron | `crontab -l \| grep reconcile` Mac Mini-n | Megőrzött legacy backup detector |
| 8.4 | IBKR Gateway launchd vagy manuális indítás | Mac Mini System Preferences | Tamás döntés szerint |
| 8.5 | 2FA mobile prompt re-authentication ablak | IBKR Gateway settings | Általában 04:00-04:30 ET |

**Akció**: az új Log Review session vagy Tamás verifikálja ezeket a Day 7 estén/Day 8-on.

---

## 9. Filesystem szerepek összefoglaló

| Mappa / fájl | MacBook (DEV) | Mac Mini (PROD) | Source-of-truth |
|--------------|----------------|------------------|------------------|
| `docs/` | **PRIMARY** (chatek írják) | másolat (git pull) | MacBook |
| `scripts/`, `src/`, `tests/` | **PRIMARY** (CC ír) | másolat (git pull) | MacBook → git → Mac Mini |
| `state/swing_positions.json` | stale másolat (audit) | **CANONICAL** | Mac Mini |
| `scripts/paper_trading/logs/cumulative_pnl.json` | stale másolat | **CANONICAL** | Mac Mini |
| `state/daily_metrics/*.json` | stale másolat | **CANONICAL** | Mac Mini |
| `logs/`, `scripts/paper_trading/logs/` | stale másolat | **CANONICAL** | Mac Mini (cron generál) |
| `output/execution_plan_*.csv` | stale másolat | **CANONICAL** | Mac Mini |
| `state/backups/` | szinkron-másolat | **CANONICAL** | Mac Mini |
| `.venv/` | helyi (saját) | helyi (saját) | Külön mindkét gépen |

**Általános elv**:
- **Kódot a MacBook-on fejlesztünk** → git push → Mac Mini pull
- **State + log a Mac Mini-n keletkezik** → sync_from_mini.sh → MacBook audit

---

## 10. Memóriaként fontos technikai részletek

### 10.1 Python venv

- **MacBook**: `/Users/safrtam/SSH-Services/ifds/.venv/` (helyi)
- **Mac Mini**: `/Users/safrtam/SSH-Services/ifds/.venv/` (helyi)
- **A két venv NEM szinkronizált** — `requirements.txt` keep-in-sync

### 10.2 Telegram bot

A Telegram bot tokent a `.env` fájl tartalmazza (NEM git-elve). Mind a két gépen helyi `.env` van.

### 10.3 API kulcsok

- **Polygon**: `.env POLYGON_API_KEY`
- **FMP**: `.env FMP_API_KEY`
- **Unusual Whales**: `.env UNUSUAL_WHALES_API_KEY`
- **FRED**: ingyenes, kulcs opcionális

### 10.4 Logs retention

- Pipeline logs (`scripts/paper_trading/logs/pt_*.log`): **napi rotáció**, manuális cleanup havi
- Cron logs (`logs/cron_*.log`): **napi rotáció**, manuális cleanup havi
- State backup (`state/backups/`): manuális cleanup (Tamás döntése)

---

## 11. Frissítési politika

**Ezt a dokumentumot frissíteni kell, ha**:
- Új cron entry kerül a Mac Mini-re
- Az `sync_from_mini.sh` script tartalma változik
- Új machine kerül a setup-be (pl. cloud backup)
- Az IBKR Paper Account változik
- A Python venv struktúra módosul

**Aki frissítheti**: Log Review chat vagy Swing Pivot Dev chat — bármelyik. **Cross-check elv**: ha kétséges valami, a másik chat session-ben (és Tamás-tól) erősítsd meg.

---

**A dokumentum vége.**

**Használat**: új Log Review vagy Swing Pivot Dev chat session-ök indításakor **első olvasandó dokumentum** a kontextushoz. A handoff prompt-okkal együtt használandó.
