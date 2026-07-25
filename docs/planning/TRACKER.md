# IFDS — Lane Tracker (CC-only koordináció)

> **Egyetlen igazságforrás** a párhuzamos CC work-streamek összehangolásához.
> Létrehozva 2026-07-25 (Tamás-kérés). Vezeti: CC. **2026-07-25 óta IFDS = CC-only, egyelőre**
> ([[division-of-labor-chat-cc]]) — a lane-ek nem külön repók, **UGYANAZT a checkoutot és git-et**
> használják (`/Users/safrtam/SSH-Services/ifds`).

## Shared-checkout higiénia (KÖTELEZŐ)

1. **Commit context-váltás előtt** — ne hagyj félkész változást a working tree-n másik lane-nek.
2. **SOHA `git add -A` / `git add .`** — mindig **explicit path** (freeze-szabály, `56043c3`); egyik lane
   ne commitolja a másik félkész munkáját. Commit előtt olvasd a `git status --short` outputot.
3. **Path-tulajdon diszjunkt** (lásd lent) — így a párhuzam biztonságos. Ha két lane ugyanazt a fájlt érinti
   (pl. a spec), az **soros** (egyszerre egy). *Megfigyelt eset: 2026-07-25 a spec-et a Loop és a
   Review-governance egyszerre érintette — tisztán feloldódott, de innen a szabály.*
4. `git pull --ff-only` a Mini-n a push után (a Mini a repo consumer-e, tiszta working tree).

## Lane-ek és path-tulajdon

| Lane | Birtokolt path-ok | Státusz |
|---|---|---|
| **Review** | `docs/review/`, `docs/analysis/` (rsync), napi/heti/biweekly rutin | 🟢 aktív |
| **FRL / Loop** | `research/`, `scripts/research/`, `docs/design/frl/`, a spec | 🟢 aktív |
| **Support** | `tests/`, bugfix | ⚪ **üres** (mindkét bug lezárva) |

## Nyitott tételek (minden lane)

| Tétel | Lane | Státusz | Következő |
|---|---|---|---|
| HYP-005 verdikt | FRL | ✅ **PARK(h5,h7)/KILL(h1,h3) — Tamás-megerősítve 2026-07-25** | a PARK auto-retestel; v2 ~szept közepe |
| T_eff-adekvácia gate | FRL | ✅ jóváhagyva + §5.5 dokumentálva | native a köv. batchre |
| `frl-cross-section-enrichment` | FRL | 🔨 WIP | enrichment sink (D_A jóváhagyva, §11.11) |
| `automated-daily-review-mini` | Review→Mini | 📋 OPEN | Phase B, deploy **Day 63 után** |
| historikus vasárnapi log-szennyezés | FRL-loader | 📋 OPEN (cross-flag `5ba8c95`) | **tartalom-alapú loader-szűrés** (ajánlás) |
| scoring_validation előjel-fix + éra-bontás | Review | 📋 backlog | a 2 biweekly-flag (report-bug + G5) |
| FileVault outage-gyökérok | ops | ⏸ Tamás-döntés | FileVault OFF + auto power-on + auto-login |
| **Kapu-protokoll D1/D2** | Review | ⏸ **Tamás-döntés** | „mi a swing Day 63" + dátum-bázis — Day 63 (~08-17) ELŐTT |
| **STOP-trigger monitor (P1)** | Review | 📋 OPEN | a pre-reg leállítási triggereket SEMMI nem számolja (§4) |
| Process: model/effort tuning | ops | ⏸ Tamás | `model` settings.json-be; effortLevel xhigh→high |

## Napi rutin (Review-lane)

- Piaczárás után (22:16+): `sync_from_mini.sh` → v6 review → `docs/review/YYYY-MM-DD-daily-review.md`.
- Péntek: + heti report (`weekly_metrics.py`) + Telegram. Kéthetente: `scoring_validation.py`.
- Következő: **hétfő 07-27** (Day 48) — a GTES TIME_STOP várt-vs-tény.

---

## Cross-lane üzenetek (a megosztott checkouton ezt olvassa a többi context)

### → FRL / Loop (2026-07-25)
- **Verdikt CONFIRMED.** A-0005/A-0006 KILL, A-0007/A-0008 **PARK_UNTIL_SWING_POWER** — a ledgerben
  `human_confirmed=True`, `by=Tamás`, `auto_decision` megőrizve. A javított logika a **következő batchre** natív.
- **Logika-fix APPROVED + dokumentálva** a spec §5.5-ben (`MIN_ADEQUATE_T_EFF=6`, `079e4a1`). A floor mostantól
  **döntés-hajtó governance-paraméter** — módosítása minden verdiktet érint, csak explicit döntéssel.
- **Historikus log cross-flag (`5ba8c95`) → most már FRL-lane-döntés** (CC-only). Ajánlás: **tartalom-alapú
  loader-szűrés** (AAA/BBB/CCC + circuit_breaker szignatúra), NEM destruktív cleanup — a loader-nek úgyis
  robusztusnak kell lennie a rank-2 forrás szennyezésére.
- **HEADS-UP:** a spec-et 2026-07-25 két lane egyszerre érintette (tisztán feloldva). Innentől: commit
  context-váltás előtt, explicit-path add.

### → Support (2026-07-25)
- **Lane ÜRES — mindkét bug lezárva** (pt_events P1 `db95c13`, e2e ordering-leak `04a50a2`, 2182 passing).
- Nincs nyitott support-tétel. Új, review-flagged bug ide route-olódik; addig a lane pihen.
