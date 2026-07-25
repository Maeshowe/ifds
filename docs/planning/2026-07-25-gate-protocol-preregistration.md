Status: OPEN
Updated: 2026-07-25
Note: PRE-REGISZTRÁCIÓ — a kapu-végrehajtás rögzítése MIELŐTT az adat beérkezik. Két Tamás-döntést kér (D1 definíció, D2 dátum-bázis) + egy P1 hiányosságot jelez (nem monitorozott STOP-triggerek). CC nem módosít pre-reg kritériumot; ez a végrehajtás protokollja.

# Kapu-protokoll pre-regisztráció — Day 63 / Day 126

## Miért most

A napi review-k **Day 47/63**-nál tartanak, a freeze „Day 63-ig" szól — a mérföldkő
**~16 trading nap** múlva van. A kapu-végrehajtás részleteit **most kell rögzíteni**,
mert utólag, az eredmény ismeretében kritériumot vagy mintát választani pontosan az,
amit a pre-reg fegyelem tilt (a G1/§6.6 guardrail lényege).

---

## 1. A központi tisztázás: a „Day 63" a review-kban NEM a kapu

Ez a legfontosabb megállapítás, és eddig implicit maradt:

- A napi review fejlécének **„Day N/63"** egy **nap-számláló** (`daily_metrics::day_number`,
  NYSE trading nap a 2026-05-18-i swing pivot óta).
- A **pre-regisztrált döntési kritériumok** viszont a **Day 126** keretre szólnak
  (`docs/decisions/2026-05-14-day63-decision-outcome.md` §3.14) — a régi Day 63 keretet
  ugyanez a dokumentum **elavultnak** nyilvánította (§7: *„az ÉLESÍTÉS küszöb (+30% annualizált)
  strukturálisan nem realisztikus… a keret revíziója szükséges"*).

**Következmény:** a közelgő swing Day 63 (~08-17) **nem go/no-go kapu**, hanem
— javaslat szerint — a **freeze feloldásának** pontja és az **első `signal_attribution`
futás** (leíró) alkalma. A tényleges élesítési/leállítási döntés a Day 126 kereté.

## 2. Két nyitott definíciós kérdés — TAMÁS-DÖNTÉS (D1, D2)

### D1 — Mi történik a swing Day 63-nál (~2026-08-17)?
Javaslat (CC): **(a) freeze feloldása** + **(b) első teljes `signal_attribution` futás,
leíró jelleggel** + **(c) a Day 126 kapu előkészítése** — de **NEM** élesítési/leállítási
döntés. Alternatíva, ha te másképp látod: a Day 63 maradjon önálló köztes kapu saját
(újra-pre-regisztrálandó) kritériumokkal.

### D2 — Dátum-bázis: a „Day 126 ≈ 2026-09-15" és a trading-nap-számolás nem egyezik
A `2026-07-01-day126-replan-proposal.md` §2.1 ezt már flagelte, és **máig nyitott**.
Az aritmetika (CC, 2026-07-25) egy valószínű magyarázatot ad — **egység-keveredés**:

| Olvasat | Számítás | Eredmény |
|---|---|---|
| Day 63 **trading** nap (a review-k számlálója) | 05-18 + 63 NYSE-nap | **~2026-08-17** |
| Day 126 **naptári** nap (az outcome doc olvasata) | 05-18 + 126 naptári nap | **~2026-09-21** (a doc „~09-15"-öt ír) |
| Day 126 **trading** nap | 05-18 + 126 NYSE-nap | ~2026-11 közepe |

A „Day 126 ≈ 09-15" tehát **naptári** számlálással konzisztens, a review-k viszont
**trading**-napot számolnak. **Ez a kétértelműség feloldandó, mielőtt a kapu esedékes.**
A kiesés-delta (07-15, 07-16, 07-22 + a 06-29→07-07 outage) **bármelyik bázisra ugyanaz**
(a kiesés *pause*, nem csökkenti a követelményt — replan §2.1).

## 3. A pre-regisztrált kritériumok (szó szerint, `2026-05-14…§3.14`) — NEM módosítható

**ÉLESÍTÉS — mind a három EGYIDEJŰLEG:**

| Kritérium | Küszöb |
|---|---|
| Kumulatív paper P&L | > **+$2,000** |
| Sharpe ratio (60 napi) | > **0.5** |
| Pozitív excess vs SPY napok | > **25 / 63 nap** (40%) |

**LEÁLLÍTÁS — bármelyik elég:**
- 10 napi excess vs SPY átlag < **−1.0%**
- VAGY 30 napi kumulatív < **−3.0%**
- VAGY 15 napi excess < **−1.0%**

**DEFAULT: PAPER FOLYTATÁS**, Day 180 újraértékelés.

> Jelenlegi állás (2026-07-24, tényszerű, **előrejelzés nélkül** — G3): cumulative
> **−$423.70 (−0.42%)**. A Sharpe és a pozitív-excess-nap számláló **nincs kiszámolva**
> (lásd §4). A kapu-kimenetel előrejelzése tilos; a távolság riportálható.

## 4. 🔴 P1 HIÁNYOSSÁG: a LEÁLLÍTÁS-triggereket SEMMI nem monitorozza

**Verifikálva (2026-07-25):** sem a `generate_review_data.py`, sem a `weekly_metrics.py`,
sem a review `flags` mezője nem számol **gördülő 10/15 napos excess-átlagot** vagy
**30 napos kumulatív drawdownt**. A daily review napi excesst ad, a heti report heti
excesst — a pre-reg trigger-ablakok egyike sem.

**Kockázat:** egy leállítási feltétel **retroaktívan** derülhet ki (hetekkel a tényleges
sérülés után) — pont az a hibaosztály, amit a projekt máshol szigorúan zár.

**Javaslat (freeze-safe, read-only, CC-task):** `stop_trigger_monitor` a napi
review-pipeline mellé (a `daily_equity` + `daily_metrics::excess_return` sorozatból):
- gördülő 10/15 napos excess-átlag + 30 napos kumulatív, **napi számolás**
- a **daily review §5 ops-checklist** kap egy kötelező sort: `STOP-triggerek: ✓ / ⚠️ <érték>`
- **kizárólag jelez**, nem cselekszik — a leállítás Tamás-döntés (human-in-the-loop)
- a kontamináció-kizárás (§5) itt is érvényes: az outage-napok nem számítanak bele

## 5. Minta-integritás — a kizárási lista (rögzített, bővíthető)

A kapu-futás **kizárja**:
- **Outage-napok**: 06-29→07-07 (Mini SSH-orphan), **07-15, 07-16** (áramszünet),
  **07-22** (FileVault-zárolás) — nincs pipeline-esemény.
- **Outage-késleltetett exitek (n=3)**: ITT/XPO (07-15), PFGC/BIRK (07-20), USFD (07-23)
  — a stratégia szándéka szerinti időpontnál 2 nappal később, mérhetően rosszabbul zártak
  (§11.10; az USFD-nél ~−$91 a becsléshez képest).
- Indoklás: `docs/planning/2026-07-01-day126-replan-proposal.md` §3 D2 (pause-and-resume,
  gate criteria UNCHANGED) + 04-risks §11.10.

**Nem zárjuk ki** (tényszerűen rögzítve, de a minta része): a self-reentry esetek
(PFGC 07-21, USFD 07-23) — ezek a stratégia normál működéséből fakadnak (max_hold ↔
belépő-jel ellentmondás), nem külső üzemzavarból. Day 63-input megfigyelésként.

## 6. A kapu-futás végrehajtási protokolja

1. **Eszköz**: `scripts/analysis/signal_attribution.py`, **pinned `c5e9ed0`** — az
   EGYETLEN kapu-input (G1). A pin nem változhat a futás előtt; ha változna, az
   új pin és az ok a 04-risks-be kerül a futás ELŐTT.
2. **Minta**: entry-alapú clean cut + a §5 kizárások. A `n` (included/excluded) a riport
   első sora.
3. **Sorrend**: előbb a minta-definíció és a kizárások fixálása → **utána** a futtatás.
   A futás után a mintán nem módosítunk.
4. **Output**: `docs/analysis/` (rsync territory) + a döntési rekord a
   `docs/decisions/`-be, a §3 kritériumok melletti tényszerű állással.
5. **Kettős futás tilos**: egyetlen futás, egyetlen riport. Ha technikai hiba miatt
   újra kell futtatni, az ok dokumentálandó (a „amíg jó nem jön ki" ellen).

## 7. Inadmissibilis a kapuba (G1, mindkét irányban)

- **Minden FRL-output** — a HYP-004 KILL, a HYP-005 PARK, az IC-becslések, a cost-model:
  **ÖRÖKRE leíró**. Sem pro, sem kontra nem idézhető a kapu-deliberációban.
- A napi/heti review-k **leíró** megfigyelései (slippage-sorozat, self-reentry n, excess-napok)
  — kontextus, nem kapu-input. A kapu-inputot kizárólag a §6/1 eszköz állítja elő.
- A `scoring_validation.py` biweekly riport — leíró, és jelenleg **éra-poolozott**
  (G5-sértés, ismert nyitott tétel), tehát végképp nem kapu-input.

## 8. Következő lépések

| # | Tétel | Kié | Mikor |
|---|---|---|---|
| D1 | „Mi a swing Day 63" — freeze-feloldás + leíró futás, vagy önálló kapu? | **Tamás** | Day 63 (~08-17) ELŐTT |
| D2 | Dátum-bázis feloldása (trading vs naptári nap) | **Tamás** | ugyanaz |
| P1 | STOP-trigger monitor implementálása (§4) | CC | **most** (freeze-safe) |
| — | A kizárási lista véglegesítése a kapu-futás előtt | CC + Tamás | Day 63 előtt |

**Ez a dokumentum a pre-regisztráció.** A §3 kritériumok nem módosíthatók; a D1/D2
döntés a *definíciót* tisztázza, nem a küszöböket. Minden későbbi változtatás
dátummal és indoklással ide kerül.
