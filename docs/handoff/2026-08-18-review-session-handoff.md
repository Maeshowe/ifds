# Handoff — IFDS review-session → új session (2026-08-18)

Status: ACTIVE
Updated: 2026-08-18

## 0. Egy mondatban
A **Day 63 elérve (2026-08-17): a parameter freeze feloldódott** — de a Day 63-hoz kötött
**érdemi utómunka (kizárási lista → leíró `signal_attribution` futás) MÉG NEM történt meg**.
Ez az új session első feladata. A napi review-rutin változatlanul fut.

## 1. Hol tartunk

| Tétel | Állapot |
|---|---|
| Paper trading | **Day 63/63 lezárva** (2026-08-17). Cumulative **−$449,88 (−0,45%)** |
| Freeze | 🔓 **FELOLDVA** 08-17-től (D1). A **G1/G3/G4–G7 guardrailek VÁLTOZATLANUL élnek** |
| Kapu (gate) | **2026-09-22** (D2) — fix dátum, nem „Day N" |
| Nyitott pozíciók | **8** (08-17 zárás), unrealized **−$1 119,25** — mind negatív, swing-éra mélypont |
| STOP-trigger | `excess_10d_mean` **−0,36%** vs −1,0% → nincs halt; 3× javult egymás után |
| Utolsó review | `docs/review/2026-08-17-daily-review.md` (commit `c6d587d`) |
| Utolsó heti | `docs/analysis/weekly/2026-W33.md` (net −$369,90, excess −0,76%) |
| Utolsó biweekly | `docs/analysis/scoring-validation.md` — swing n=48, Pearson **−0,409** (p=0,004) |

## 2. AZONNALI TEENDŐK (prioritási sorrendben)

### P0 — Day 63 utómunka (a freeze feloldódott, ez már nem vár)
1. **Kizárási lista véglegesítése** — gate-protokoll `docs/planning/2026-07-25-gate-protocol-preregistration.md`
   **§8/B**. Tartalma: **5 outage-nap** + **4 késett exit** (ITT/XPO, PFGC/BIRK, USFD, DE — mind a
   négy rosszabbul zárt a szándékoltnál). **Ez a `signal_attribution` futás előfeltétele.**
2. **A realized/MTM korlát írásbeli rögzítése** a protokoll módszertani szakaszában.
   Indok: 2026-08-17-en **először állt fenn az ellentétes-előjelű eset** (realized-only **+0,47%**
   vs MTM **−0,38%**). ⚠️ **NEM a mező cseréje** (az pre-reg-sértés lenne) — **ismert korlátként**
   dokumentálandó. A D3-döntés (realized-only marad irányadó) **változatlan**.
3. **Az első, LEÍRÓ `signal_attribution` futás** — pinned **`c5e9ed0`**.
   ⚠️ **NEM go/no-go.** A kapu 2026-09-22. **G3: nincs jel-érvényességi nyelv** a kapu-futásig.

### P1 — Tamás-döntést igénylő nyitott ügyek
4. **UW API kulcs** — **2026-06-24 óta hiányzik** a Mini `.env`-jéből
   (`API_HEALTH_CHECK: unusual_whales → skipped`). A pipeline **nem áll**: dokumentált
   **Polygon-fallback** aktív, a Phase 5 egészséges (79 analyzed / 73 passed / 6 excluded).
   **De**: a teljes kapu-minta ezen a fallback-úton keletkezett (adat-proveniencia tény), és a
   **Day 90-re tervezett UW dark-pool Bayesian rekalibráció input nélkül maradna**.
   → Döntés: pótoljuk a kulcsot, vagy tudatosan a Polygon-úton maradunk + a tervet módosítjuk.
5. **FileVault** — a Mini áramszünet után a feloldó-képernyőn ragad, `launchd`/`sshd`/`cron` nem indul.
   **2 előfordulás** (07-22, 08-07). Csomagban kell: FileVault OFF + auto power-on + auto-login.
   **Régóta nyitott Tamás-döntés.**

## 3. Napi rutin (változatlan)
1. `./scripts/sync_from_mini.sh`
2. **STOP-trigger ELŐSZÖR**: `python scripts/analysis/stop_trigger_monitor.py`
   — **D4: a `mean` az irányadó**, a `sum` csak megfigyelés (jelenleg BREACH-en áll, ez normális)
3. Review a **v6 10-szekciós** formátumban → `docs/review/YYYY-MM-DD-daily-review.md`
4. **Péntek**: + heti (`weekly_metrics.py`) | **kéthetente**: + `scoring_validation.py --fetch-spy`
5. Commit → **push CSAK Tamás explicit jóváhagyásával**

## 4. Amire figyelj (élő megfigyelés-sorozatok)
- **„Rés utáni visszalépés"** — a legérdekesebb friss mintázat. **n=2 lezárt, mindkettő negatív**
  (JAZZ −$251,02, GTES −$265,91), és **mindhárom visszalépés MAGASABB áron** történt, mint az előző
  exit (+2,8% / +11,3% / +9,5%). A 3. eset (**EQH**) **nyitva**, jelenleg −$155,02. **n=2 — nem
  általánosítható**, de Day 63-input.
- **Slippage** n=24 (17 adverz / 7 kedvező) — FRL `cost_model.json` input.
- **Rally/risk-off aszimmetria** — ⚠️ **óvatosan**: a 0-exites napok a realized-only mező miatt
  automatikusan „felülteljesítést" mérnek eső tapén (lásd 08-17 §6/§7).
- **Univerzum-méret** — 226 → 380 → 765 → **1338** a vasárnapi Phase 1-3 frissítésekkel.
  ✅ **Nem halmozódás** (91 kiesett / 663 új / 0 duplikátum a 08-14→08-17 átmenetben) — valódi
  újra-szűrés. A **mérték** viszont megfigyelés-tárgy.
- **Ismert, nyitott defektek**: `exit_type` mező hibás (a `pending_exits` a kanonikus),
  `entry_price=planned` (§11.10).

## 5. Kritikus szabályok (NE sértsd meg)
- **PÉNZÜGYI rendszer — human-in-the-loop.** Semmi nem megy prodba jóváhagyás nélkül.
- **Push**: CC commitol, **Tamás pushol** — csak explicit jóváhagyással.
- **`git add` KIZÁRÓLAG explicit path-listával** — `git add -A` / `git add .` **TILOS**.
  Commit előtt **mindig** `git diff --cached --stat`.
- **Financial-ledger írás** (cumulative_pnl, pending_exits) — **Tamás futtatja a Mini terminálban**,
  nem az agent.
- **G1**: a kapu egyetlen inputja a pinned `signal_attribution.py` — a `scoring_validation.py`
  **nem** kapu-input (mindkét irányban).
- **G3**: **nincs jel-érvényességi nyelv** a kapu-futásig — csak leíró megfigyelés.
- **Értékelő-motor fix**: kizárólag a **pre-reg szöveghez igazításként**, a 4 kötelező kísérővel
  (pre-reg forrás megnevezése, érzékenységi ellenőrzés, regressziós teszt egy korábbi verdiktre,
  nincs újrafuttatás verdikt-generálásért).
- **`docs/analysis/`** gitignore-olt (a Mini generálja) — a `docs/review/` tracked.

## 6. Git állapot
- **HEAD**: `c6d587d` — 2026-08-17 daily review (Day 63)
- **1 commit vár pushra** (`c6d587d`); az azt megelőző 4 (`016a793`…`5372380`) **pusholva** 08-15-én.
- **A Mini pull-ja elmaradt** a 08-15-i push óta → **a Mini 5 commit-tal le van maradva**.
