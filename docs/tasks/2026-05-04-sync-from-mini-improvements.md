# sync_from_mini.sh — Robustness & Coverage Improvements

**Status:** DONE
**Updated:** 2026-05-04
**Created:** 2026-05-02 (szombat délelőtt, Tamás utazás előtt)
**Priority:** **P3** — kis prioritású minőségjavítás, NEM blokkoló
**Estimated effort:** ~1-1.5h CC

**Depends on:**
- nincs

**NEM blokkolja:**
- A Contradiction Signal task (`2026-05-04-contradiction-signal-from-fmp.md`) — ennek a P1 task-nak elsőbbsége van

---

## Kontextus

A `scripts/sync_from_mini.sh` egyirányú rsync szinkron a Mac Mini (production) → MacBook Pro (development) között. A jelenlegi 5 mappa szinkronizálása **alapvetően jól működik**, és a daily review-k naponta sikeresen futnak az MacBook-on a frissített adatokra építve.

Két konkrét gyenge pontot **azonosítottunk** az utóbbi 5 napban:

### Gyenge pont 1: A `docs/analysis/` szinkronizálás hiánya

**Tünet:** 2026-05-02 (szombat) reggel a péntek esti `weekly_metrics.py` és `scoring_validation.py` outputjai a Mac Mini-n keletkeztek (`docs/analysis/weekly/2026-W18.md`, `docs/analysis/scoring-validation.md`, `docs/analysis/plots/*.png`). **Ezek nem kerültek a MacBook-ra automatikusan**, mert a `sync_from_mini.sh` nem szinkronizálja a `docs/` mappát.

**Manuális workaround történt:**
```bash
# Mac Mini-n
git add docs/analysis/
git commit -m "docs: W18 weekly metrics + scoring validation"
git push

# MacBook-on
git pull
```

**Probléma:** ez a workaround **5-6 manuális lépés**, és **könnyen elfelejthető** vasárnap reggel. A péntek esti analízisek **kötelezően** szükségesek a vasárnapi W18 elemzéshez.

### Gyenge pont 2: Adat-frissesség visszajelzés hiánya

**Tünet:** A `daily_review`-k során nem látható közvetlenül, **mikor** futott az utolsó sync. Az adat-frissesség kérdése **strukturális kockázat** (lásd 2026-04-29 chat: "ha a sync nem futott egy reggel, és én friss adatokat feltételezek a logokon, félrevezetlek").

**Jelenlegi állapot:** a `daily_metrics/YYYY-MM-DD.json` mtime-jából lehet következtetni a sync időpontjára, de:
- ez közvetett (a fájl mtime az rsync-időt tükrözi, nem feltétlen a sync-időt)
- nincs explicit "last sync timestamp" sehol

---

## A javasolt fejlesztések — 3 pont

### 1. ✅ A `docs/analysis/` szinkronizálás hozzáadása (KÖTELEZŐ)

**Hozzáadandó a `DIRS` listához:**

```bash
DIRS=(
    "data"
    "logs"
    "output"
    "scripts/paper_trading/logs"
    "state"
    "docs/analysis"  # ÚJ
)
```

**Miért csak `docs/analysis/` és nem `docs/`?**

- **`docs/analysis/`** automatikusan generált fájlok (weekly metrics, scoring validation, plots) — **rsync-szel** jól szinkronizálható, nincsenek konfliktusok
- **`docs/tasks/`, `docs/review/`, `docs/decisions/`, `docs/STATUS.md`** **emberi szerkesztéssel** változik (Chat ír, Tamás szerkeszt, CC ír) — **git-en** keresztül megy mindkét irányba (Mac Mini ↔ MacBook), **rsync nem alkalmas** mert kettős frissesség-rendszert termelne
- **`docs/planning/`, `docs/references/`** szintén git-only, ritkán változik

**Tehát a sync csak a "machine-generated outputs"-ot szinkronizálja** rsync-szel. Az emberi-szerkesztett tartalom git-en megy.

### 2. ⚠️ Adat-frissesség timestamp (AJÁNLOTT)

**Cél:** minden sync végén egy `state/.last_sync` fájl keletkezzen a sync időpontjával.

**Implementáció:** a script végéhez hozzáadni:

```bash
# Sync timestamp record
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${LOCAL_BASE}/state/.last_sync"
echo "Last sync recorded: $(cat ${LOCAL_BASE}/state/.last_sync)"
```

**Hatása:** a Chat (én) minden daily review elején meg tudom nézni a `state/.last_sync`-et:

```python
# Daily review elején, a Chat oldalán:
last_sync = read_text_file("state/.last_sync")  # "2026-05-02T07:15:30Z"
print(f"📊 Adat-frissesség: utolsó sync {last_sync}")
```

Ez **explicit** jelzi, hogy mikor készült a friss adat — nem kell az mtime-okra építeni.

**Megjegyzés:** a `.last_sync` fájl `state/`-ben van, **nem** a repo gyökerében — mert a `state/` már része a sync target-nek, és a fájl rsync után rögtön íródik. **Nem kerül git-be** (`.gitignore`-ban már szerepelnie kell — ellenőrizendő).

### 3. ⚠️ Pre-flight validáció (OPCIONÁLIS)

**Cél:** a script futás előtt ellenőrizze, hogy:
- (a) az SSH kapcsolat a `negotium.ddns.net`-hez működik
- (b) a `~/SSH-Services/ifds/` létezik a Mac Mini-n
- (c) az 5+1 forrás-mappa létezik a Mac Mini-n

**Implementáció:**

```bash
# Pre-flight checks
echo "── Pre-flight checks ──"

# (a) SSH connectivity
if ! ssh -q -o ConnectTimeout=5 "${REMOTE}" "exit"; then
    echo "❌ ERROR: Cannot connect to ${REMOTE}"
    echo "   Check VPN, firewall, or DDNS resolution."
    exit 1
fi

# (b) Remote project root exists
if ! ssh "${REMOTE}" "test -d ${REMOTE_BASE}"; then
    echo "❌ ERROR: ${REMOTE_BASE} does not exist on ${REMOTE}"
    exit 1
fi

# (c) Source directories exist on remote
for dir in "${DIRS[@]}"; do
    if ! ssh "${REMOTE}" "test -d ${REMOTE_BASE}/${dir}"; then
        echo "⚠️  WARN: Remote dir missing: ${REMOTE_BASE}/${dir} (will skip)"
    fi
done

echo "✓ Pre-flight checks passed"
echo ""
```

**Hatás:** ha az SSH nem működik, a script **gyorsan** kilép egy érthető hibaüzenettel — nem fél óra rsync timeout-okat kapunk. Ha egy mappa hiányzik a Mac Mini-n (pl. új beállításnál), warning-ot ad, de a többi mappát szinkronizálja.

---

## Out of scope (explicit) — fontos!

A következőket **NE** módosítsa CC, ezek **szándékosak**:

- **`--delete` flag megőrzése** — a Mac Mini a master, a MacBook követi. Ha egy fájl törlődik a Mac Mini-n (pl. log rotáció, régi snapshot cleanup), akkor a MacBook-on is törlődnie kell. **Ez nem hiba, ez feature.**
- **`data/cache/` exclude megőrzése** — szándékosan kihagyott, mert stale forward-looking date ranges-et tartalmaz.
- **A docs/tasks/, docs/review/, docs/STATUS.md NEM kerül a sync-be** — git-en megy, **nem** rsync-en.
- **A sync IRÁNYA NEM változik** — egyirányú Mac Mini → MacBook. **NEM** kell oda-vissza sync.
- **NE adj hozzá Telegram értesítést** a sync végén — ez egy kézi futtatású script, közvetlen output van a terminálban.
- **NE rakjuk cron-ba a sync-et** — szándékosan manuális, hogy Tamás eldönthesse, mikor friss az adat (pl. utazás közben nem futtatja).

---

## Tesztek

**A `sync_from_mini.sh` egy bash script, ami SSH + rsync kombinációt használ.** Nincsenek unit tesztek hozzá — **integration test** a természetes módja:

### Manuális validáció (CC futtatja smoke teszt során)

**1. Dry-run a módosított scripttel:**
```bash
cd ~/SSH-Services/ifds  # vagy a MacBook-on bárhol
./scripts/sync_from_mini.sh --dry-run
```

**Várt:**
- Pre-flight checks passed
- 6 mappa szerepel a syncben (5 régi + új `docs/analysis/`)
- A `[DRY RUN]` kimenet jelez minden tervezett változást
- A script tisztán kilép `Sync complete` üzenettel

**2. Tényleges sync futtatás:**
```bash
./scripts/sync_from_mini.sh
```

**Várt:**
- A `state/.last_sync` fájl keletkezik egy ISO-8601 timestamp-pel
- A `docs/analysis/weekly/`, `docs/analysis/plots/`, és minden új analízis-fájl megjelenik a MacBook-on

**3. Hibakezelés ellenőrzése (opcionális):**
- VPN-t kikapcsolni vagy a DDNS-t félrekonfigurálni → script gyorsan kilép pre-flight error-ral

---

## Implementation order — ~1-1.5h CC

| Lépés | Tartalom | Idő |
|-------|----------|-----|
| 1 | Olvasás: jelenlegi `sync_from_mini.sh` + a fenti task | 5 min |
| 2 | `docs/analysis/` hozzáadása a `DIRS` listához | 5 min |
| 3 | `state/.last_sync` timestamp record a script végén | 10 min |
| 4 | Pre-flight checks szekció (SSH + remote dirs) | 20 min |
| 5 | Lokális dry-run teszt | 10 min |
| 6 | Tényleges sync teszt + `state/.last_sync` ellenőrzés | 10 min |
| 7 | `.gitignore` frissítés (ha kell) — `state/.last_sync` | 5 min |
| 8 | Commit + push | 5 min |
| **Összesen** | | **~70-75 min** |

---

## Success criteria

1. **Dry-run** sikeresen lefut a módosított scripttel, **6 mappa** szerepel (eredeti 5 + `docs/analysis/`)
2. **Tényleges sync** után a `state/.last_sync` fájl tartalmaz egy érvényes ISO-8601 timestamp-et
3. **A `docs/analysis/weekly/2026-W18.md`** automatikusan megjelenik a MacBook-on a következő sync után (nem kell git pull)
4. **Pre-flight check** valamilyen hibás állapotot felismer (pl. lekapcsolt SSH-val) és érthető hibaüzenettel kilép
5. **A `.gitignore`** kizárja a `state/.last_sync` fájlt, ha jelenleg még nem zárja ki

---

## Risk

**Zéró.** Indoklás:

1. **Read-only sync (Mac Mini → MacBook)** — semmi sem változik a Mac Mini-n
2. **A pre-flight checks defenzívek** — hiba esetén gyorsan kilép, nem rontja a meglévő adatot
3. **A `docs/analysis/` mappa új a sync-ben**, **de** a Mac Mini-n már létezik (a scoring_validation.py és weekly_metrics.py oda írnak), és a MacBook-on rsync létrehozza ha hiányzik
4. **A `state/.last_sync` egy egysoros fájl**, nincs hatással semmilyen pipeline viselkedésre
5. **NEM érinti a daily review folyamatot** — a sync futás után minden ugyanúgy megy, csak gazdagabb tartalommal és jobb visszajelzéssel

---

## Commit message draft

```
chore(sync): improve sync_from_mini.sh — docs/analysis coverage + freshness timestamp

The sync script now covers docs/analysis/ (machine-generated weekly metrics,
scoring validation reports, plots) in addition to the existing 5 directories.
This eliminates the manual git add/commit/push/pull workaround required
after weekly_metrics.py or scoring_validation.py runs on the Mac Mini.

Adds a sync timestamp record (state/.last_sync) so daily reviews can verify
data freshness explicitly rather than relying on file mtime inference.

Adds pre-flight checks for SSH connectivity and remote directory existence
to fail fast with clear error messages when the Mac Mini is unreachable
(e.g. VPN down, DDNS resolution issue).

Excluded from sync (intentional, unchanged):
  - data/cache/ (stale forward-looking date ranges)
  - __pycache__/, .DS_Store
  - docs/tasks/, docs/review/, docs/STATUS.md (git-managed, bidirectional)
  - docs/planning/, docs/references/ (git-managed, low churn)

Verified manually:
  - Dry-run: 6 directories listed (original 5 + docs/analysis/)
  - Live run: state/.last_sync created with ISO-8601 timestamp
  - docs/analysis/weekly/2026-W18.md auto-syncs without manual git operations
  - Pre-flight check fails fast with disabled SSH

Updated .gitignore to exclude state/.last_sync.
```

---

## Kapcsolódó

- Jelenlegi script: `scripts/sync_from_mini.sh`
- 2026-04-29 chat: "MacBook ↔ Mac Mini különbség" tisztázás
- 2026-05-02 chat: az adat-frissesség kérdés explicit kommunikációja
- W18 weekly riport (a manuális workaround motivációja): `docs/analysis/weekly/2026-W18.md`
- Project instructions: "Kód: MacBook-on fejlesztés → push → Mac Mini-n fut" (architektúrális kontextus)

---

## Megjegyzés a Linda Raschke-elv kontextusban

Ez **NEM trading feature**, hanem **operatív infrastruktúra**. A Linda Raschke-elv szerint a **discretionary judgment** akkor működik, ha a **systematic adat megbízható és időben friss**. Egy hiányzó vagy elavult adat-szinkron **rontja** a Tamás reggeli helyzet-felismerési képességét.

A 3 javasolt fejlesztés mind **a friss adatok biztosítását szolgálja**:
- `docs/analysis/` automatizálás → kevesebb manuális lépés, kevesebb felejtés
- `state/.last_sync` → explicit visszajelzés mikor friss az adat
- Pre-flight checks → gyors hibafelismerés helyett hosszú timeout-ok

**Operatív megbízhatóság** == jobb döntéshozatal.

---

*Task előkészítve: 2026-05-02 szombat délelőtt, Chat (Tamás utazás előtt)*
