# Task: Sector-Balanced Greedy — Sector Cap Hotfix (full portfolio scope)

Status: WONTFIX
Updated: 2026-05-21
Note: 2026-05-21 reggeli CC vizsgálat — mindkét feltételezett hipotézis (A: kód bug, B: config mismatch) HAMIS. A kód helyes (phase6_sizing.py:1321-1325 helyesen iterál open_positions-en), a spec érték is helyes (Day 63 decision §3.11 + 2026-05-17 swing-sizing task = 30% explicit). A 15%-os cap-feltételezés CSAK a daily review §0.6-ban jelenik meg post-hoc, semmilyen design dokumentumban nincs. Day 3 Healthcare 20.63% < 30% spec cap → NINCS megsértés. Tamás döntése (2026-05-21 reggel): spec érvényes marad, daily review §0.6 reklasszifikálva NOT A BUG. **NEM KELL KÓDVÁLTOZÁS.**

**Priority:** **P0 — HOTFIX** (deploy 15:30 CEST előtt, ma)
**Created:** 2026-05-21
**Owner:** Claude Code
**Estimated effort:** ~1-1.5h CC (investigation + fix + test + deploy)

**Source incident:** [`docs/review/2026-05-20-daily-review.md`](../review/2026-05-20-daily-review.md) §1, §4, §6 §0.6 — Day 3 (2026-05-20) Healthcare sector 20,63% > 15% cap.

**Source design:** [`docs/tasks/2026-05-17-swing-sizing-phase6.md`](2026-05-17-swing-sizing-phase6.md) §3 — `select_daily_entries()` sector-balanced greedy logika.

**Depends on:** —

---

## ⚠️ 2026-05-21 CC INVESTIGATION OUTCOME — WONTFIX

### Mindkét eredeti hipotézis HAMIS

**(A) `compute_sector_notionals` NEM iterál open_positions-on**:

CÁFOLAT — a kódban a függvény NEM létezik mint külön def. A sector accounting inline a `_select_swing_entries`-ben ([`phase6_sizing.py:1297-1378`](../../src/ifds/phases/phase6_sizing.py)), és **HELYESEN** iterál open_positions-en:

```python
# phase6_sizing.py:1320-1325
sector_notionals: dict[str, float] = {}
for pos in open_positions:                                          # ← TELJES open lista
    pos_notional = pos.quantity * pos.entry_price
    sector_notionals[pos.sector] = (
        sector_notionals.get(pos.sector, 0.0) + pos_notional
    )
```

Tehát a Day 3-i CNC entry-nél a `sector_notionals["Healthcare"]` = MASI $14,995 (a régi pozíció helyesen beleszámolva). Új CNC notional + meglévő MASI = $20,626 > $30,000 cap (30%) → CNC **átment** a cap-szűrőn — de nem azért, mert a kód hibás, hanem mert a cap **30%, NEM 15%**.

**(B) `swing_sector_cap_pct` config mismatch (0.30 vs 0.15)**:

CÁFOLAT — `swing_sector_cap_pct = 0.30` a [`defaults.py:342`](../../src/ifds/config/defaults.py)-en **PONTOSAN megfelel a Day 63 decision §3.11-nek és az eredeti 2026-05-17 swing-sizing task-nak**:

| Forrás | Sector cap érték |
|---|---|
| `defaults.py:342` `swing_sector_cap_pct` | **0.30** |
| `docs/decisions/2026-05-14-day63-decision-outcome.md` §3.11 | **30% notional/szektor** (4× explicit említés: line 40, 364, 374, 376) |
| `docs/tasks/2026-05-17-swing-sizing-phase6.md` (eredeti spec) | **30%** (line 23, 45, 59, 81, 87, 105, 115, 130, 177, 202, 210 — 11× explicit) |
| `docs/review/2026-05-20-daily-review.md` §0.6 | **15%** ⚠️ csak ITT, post-hoc, design dokumentumban nincs alapja |

A `daily_metrics.swing_state.sector_max_pct: 20.63` **számított display érték** ([`scripts/paper_trading/daily_metrics.py:159-162`](../../scripts/paper_trading/daily_metrics.py)) — a portfolio max sector arányát számítja, **NEM cap-érték**. A daily review §0.6 ezt félreértelmezte mint "15% cap".

### Helyes Day 3 értelmezés

- Healthcare: MASI $14,995 + CNC $5,631 = **$20,626 = 20.63%** portfolio share
- Spec cap (30%): **$30,000**
- **20.63% < 30% → BENNE VAN a spec szerint, NINCS cap megsértés**

A `_select_swing_entries` line 1356-1357-en helyesen ellenőriz: `new_sector_total > sector_cap_usd` → $20,626 > $30,000? Nem. → CNC `selected.append(pos)` (line 1368). **Helyes viselkedés.**

### Cross-link

A daily review §0.6 reklasszifikálandó "NOT A BUG"-ra. A spec szerinti 30% cap **flexibility** szándékos — egy 10-12 concurrent + 4-5 közepes pozíció/szektor mintát támogat (lásd Day 63 decision §3.11 indoklást).

### Akció

NEM kell kódváltozás. A daily review §0.6 frissítve, ez a task fájl WONTFIX status-ban marad.

---

---

## 1. A probléma

Day 3 (2026-05-20) záró portfolio sector distribution szerint **a Healthcare szektor 20,63% notional** ($20 625,65), **5,63 százalékponttal magasabb** a 15% sector_max_pct cap-nél. Konkrét számok:

| Pozíció | Sector | Notional | Entry date |
|---------|--------|----------|------------|
| MASI | Healthcare | $14 995,00 (15,00% cap) | 2026-05-18 (Day 1) |
| **CNC** | Healthcare | $5 631 (5,63% **CAP MEGSÉRTÉS**) | 2026-05-20 (Day 3) |
| **Total Healthcare** | | **$20 626 (20,63%)** | |

**A CNC entry NEM kerülhetett volna be** a sector-balanced greedy logikával, ha az a teljes (régi + új) portfolio sector arányát ellenőrzi.

## 2. Root cause hipotézis

A `2026-05-17-swing-sizing-phase6.md` §3 implementáció szerint a `select_daily_entries()` függvény így működik:

```python
def select_daily_entries(scored_candidates, open_positions, config):
    sector_notionals = compute_sector_notionals(open_positions)  # <-- KULCS LÉPÉS
    ...
    for candidate in ranked:
        candidate_notional = compute_notional(candidate, config)
        new_sector_total = sector_notionals.get(candidate_sector, 0) + candidate_notional
        if new_sector_total > total_equity * sector_cap_pct:
            continue
        selected.append(candidate)
        sector_notionals[candidate_sector] = new_sector_total
```

**A hibahely 3 lehetséges helyen van:**

### (A) `compute_sector_notionals(open_positions)` NEM számolja a régi pozíciókat

Hipotézis: a függvény **az aznapi új entry-k egymáshoz képest** rangsorolja a sector-cap betartást, **NEM a teljes (régi + új) portfolio sector arányára** számol. Vagyis a CNC entry-nél (Day 3 reggel) a sector-balanced logika **csak az aznapi új entry-k** alapján döntött (VLO Energy + ON Technology + CNC Healthcare = mind különböző szektor, mind OK), és a **régi MASI Healthcare-jét NEM vette figyelembe**.

**Vizsgálandó:**
```bash
git grep -n "compute_sector_notionals" src/
git grep -n "def compute_sector_notionals" src/
```

Ha a függvény implementáció **NEM iterál `open_positions`-on** és visszaad egy üres dict-et / csak az új entry-k-et, akkor ez a bug.

### (B) `sector_cap_pct` config mismatch

Hipotézis: a `defaults.py`-ban a `swing_sector_cap_pct` érték **0.30** (a 2026-05-17 task design szerint), miközben a `daily_metrics.swing_state.sector_max_pct: 15.0` (a logging-ban 0.15-tel jelenik meg). Ha a sizing logika **0.30**-cal számol, akkor a Healthcare 20,63% **a régi cap alá esik** (még éppen), és a logging-felirat csak post-hoc 15%-ra módosított.

**Vizsgálandó:**
```bash
git grep -n "swing_sector_cap_pct" src/
git grep -n "sector_cap_pct" src/
git grep -n "sector_max_pct" src/
git grep -n "0.15\|0.30" src/ifds/config/defaults.py
```

### (C) `open_positions` paraméter NEM friss az új entry előtt

Hipotézis: a `select_daily_entries()` hívása előtt az `open_positions` lista **NEM tartalmazza a friss tegnapi pozíciókat** (esetleg cache-elt vagy stale state). Vagyis a Day 3 reggeli hívásnál a `open_positions = []` üres listával futott, és a sector-balanced greedy "tiszta lap"-pal indult.

**Vizsgálandó:**
- A `state/swing_positions.json` betöltődik a Day 3 reggeli pipeline futáshoz?
- A `phase6_sizing.py` vagy hasonló hívja a `select_daily_entries()`-t hol? Hogyan tölti be az `open_positions` paramétert?

## 3. Javasolt hotfix

Bárhogyan is, a fix logika:

```python
def compute_sector_notionals(open_positions: list[SwingPosition]) -> dict[str, float]:
    """Compute current sector-level notional totals from the open positions list.

    CRITICAL: This function MUST iterate `open_positions` (the full live state from
    `state/swing_positions.json`), NOT only today's new entries.
    """
    sector_notionals = defaultdict(float)
    for pos in open_positions:
        # qty_remaining * entry_price (or current mark price)
        notional = pos.qty_remaining * pos.entry_price
        sector_notionals[pos.sector] += notional
    return dict(sector_notionals)


def select_daily_entries(
    scored_candidates: list[ScoredCandidate],
    open_positions: list[SwingPosition],  # <-- friss state, NEM stale cache
    config: dict,
) -> list[ScoredCandidate]:
    # CRITICAL: az `open_positions` MUST a friss state-ből
    sector_notionals = compute_sector_notionals(open_positions)

    total_equity = config["account_equity"]
    sector_cap_pct = config["swing_sector_cap_pct"]  # ELLENŐRIZZÜK: 0.15 a deployed value
    max_new = min(
        config["swing_max_daily_new"],
        config["swing_max_concurrent"] - len(open_positions),
    )

    ranked = sorted(scored_candidates, key=lambda t: -t.ewma_score)
    selected = []

    for candidate in ranked:
        if len(selected) >= max_new:
            break

        candidate_notional = compute_notional(candidate, config)
        candidate_sector = candidate.sector

        new_sector_total = sector_notionals.get(candidate_sector, 0) + candidate_notional
        if new_sector_total > total_equity * sector_cap_pct:
            logger.info(
                f"[SECTOR_CAP_SKIP] {candidate.ticker} ({candidate_sector}): "
                f"sector total ${sector_notionals[candidate_sector]:.0f} + "
                f"candidate ${candidate_notional:.0f} = ${new_sector_total:.0f} "
                f"> cap ${total_equity * sector_cap_pct:.0f} ({sector_cap_pct*100:.1f}%)"
            )
            continue

        selected.append(candidate)
        sector_notionals[candidate_sector] = new_sector_total

    return selected
```

**Plus a `defaults.py`-ban explicit ellenőrzés:**

```python
# swing pivot deploy 2026-05-18 — Day 63 decision outcome §3.11 szerint
"swing_sector_cap_pct": 0.15,  # NEM 0.30 a Day 63 decision-ben módosított érték
```

## 4. Test scenarios

A `tests/test_phase6_sizing.py`-ban (vagy hasonló) **új unit test**:

```python
def test_sector_cap_enforced_against_full_portfolio():
    """Day 3 2026-05-20 incident regression test.

    Setup: MASI Healthcare 15.00% open position from Day 1.
    Day 3 reggeli új candidates: VLO Energy, ON Technology, CNC Healthcare.
    Expected: CNC SKIPPED (Healthcare cap megsértés), VLO + ON kiválasztva.
    """
    open_positions = [
        SwingPosition(
            ticker="MASI",
            sector="Healthcare",
            entry_price=178.51,
            qty=84,
            qty_remaining=84,
            # ... egyéb mezők
        ),
    ]
    candidates = [
        ScoredCandidate(ticker="VLO", sector="Energy", ewma_score=73.1, ...),
        ScoredCandidate(ticker="ON", sector="Technology", ewma_score=70.2, ...),
        ScoredCandidate(ticker="CNC", sector="Healthcare", ewma_score=57.9, ...),
    ]
    config = {
        "account_equity": 100_000,
        "swing_sector_cap_pct": 0.15,
        "swing_max_daily_new": 3,
        "swing_max_concurrent": 12,
    }

    selected = select_daily_entries(candidates, open_positions, config)

    selected_tickers = [s.ticker for s in selected]
    assert "VLO" in selected_tickers, "VLO Energy should be selected"
    assert "ON" in selected_tickers, "ON Technology should be selected"
    assert "CNC" NOT in selected_tickers, "CNC Healthcare should be SKIPPED (cap)"
    assert len(selected) == 2, "Only 2 new entries on Day 3"


def test_sector_cap_15_percent_default():
    """Verify swing_sector_cap_pct default is 0.15 (NOT 0.30)."""
    from ifds.config.defaults import RUNTIME_DEFAULTS  # or whichever module
    assert RUNTIME_DEFAULTS["swing_sector_cap_pct"] == 0.15
```

## 5. Risk if NOT deployed before 15:30 CEST

A Day 3 UW shadow log szerint **a CVS Healthcare ticker** (S_j 55,47) is a kvalifikáló pool-ban volt, csak `phase6_sized: false` (skipped). Ha Day 4 reggel **CVS újra a top S_j-ben**, a jelenlegi hibás logika **újra beengedheti** Healthcare-be:

| Forgatókönyv | Healthcare total | % portfolio | Megjegyzés |
|--------------|-------------------|-------------|------------|
| Day 3 záró | $20 626 | 20,63% | jelenlegi cap-megsértés |
| Day 4 + CVS ~$5 000 | $25 626 | **25,63%** | **70% cap-túllépés** |
| Day 4 + 2 új Healthcare | $30 000+ | **>30%** | strukturális ellentét |

**Konkrét adatpont a sürgősségre**: a `state/uw_shadow/2026-05-20.json`-ben CVS `combined_score: 55.47`, `phase4_passed: true` — vagyis **a Phase 4 átengedte**, csak a Phase 6 sector-balanced greedy szűrte ki. Ha a hibás logika **csak az aznapi új entry-k egymáshoz képest** ellenőriz, **CVS Day 4-en bekerülhet**.

**Strukturális hatás**: a Healthcare szektor 25%+ koncentrációja **strukturálisan exponálja a portfoliot** Healthcare-specifikus piaci eseményekre (pl. egy FDA döntés, ami a MASI + CNC + CVS egyszerre érinti).

## 6. Acceptance criteria

- [ ] Root cause azonosítva (A / B / C melyik?)
- [ ] `compute_sector_notionals()` függvény javítva (iterál `open_positions` listán)
- [ ] `swing_sector_cap_pct` config érték explicit 0.15 a `defaults.py`-ban
- [ ] Új regression test `test_sector_cap_enforced_against_full_portfolio()` PASSING
- [ ] Új config-test `test_sector_cap_15_percent_default()` PASSING
- [ ] Teljes pytest suite passing (no regression)
- [ ] Deploy Mac Mini-re **15:30 CEST előtt** (a Day 4 piacnyitás előtt)
- [ ] Day 4 záró `daily_metrics.swing_state.sector_max_pct ≤ 15.0` MIND a 4 szektorra

## 7. Commit message

```
fix(phase6): enforce sector cap against full portfolio, not only new entries

Day 3 (2026-05-20) revealed that the sector-balanced greedy logic
checked sector caps only across same-day new entries, ignoring
already-open positions. Result: CNC Healthcare entry pushed total
Healthcare notional to 20.63%, exceeding the 15% cap (MASI was
already at 15.00% from Day 1).

Fix: `compute_sector_notionals()` now iterates `open_positions`
(loaded from `state/swing_positions.json`) and the sector_balanced
greedy enforces the cap against (open + new) totals.

Also: explicit `swing_sector_cap_pct: 0.15` in defaults.py to match
the Day 63 decision outcome (was 0.30 in the original 2026-05-17
design, modified to 0.15 in the final deploy).

Regression test added: test_sector_cap_enforced_against_full_portfolio
covers the Day 3 incident scenario directly.

Refs: docs/review/2026-05-20-daily-review.md §6 §0.6
Refs: docs/tasks/2026-05-21-sector-cap-hotfix.md
```

## 8. Followup observation (informational, NOT in scope)

A `daily_metrics.swing_state.sector_max_pct` mező a Day 3 logban `20.63` értéket mutat — vagyis **a logging maga helyesen detektálta a cap-megsértést post-hoc**, de a sizing logika nem szűrte ki. Ez **NEM bug** a logging-ban, hanem **bizonyíték** arra, hogy a state-frissítés helyesen történik **az új entry-k után** (csak a pre-entry decision logika nem ellenőrizte). Tehát a hotfix scope **csak a `select_daily_entries()` döntési logikára vonatkozik**, NEM az utólagos state aggregátorra.
