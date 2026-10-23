Status: DONE
Updated: 2026-10-23
Note: Implementálva 2026-10-23. A tolerancia-guard visszavezetéssel verifikálva (az `s == 0` visszaírásakor 4 teszt bukik), és egy AST-sweep tiltja a formát a modulban. A lefedettség-diff a leminősítés utáni első futáskor futtatandó, TÖRÖLT opciós cache mellett. +41 teszt.

# Phase 5 — degeneráció-guard + lefedettség-kapu a leminősítés előtt

## 1. Probléma

### 1.1 A konstans feed átcsúszik (kisebbik kockázat)

`src/ifds/phases/phase5_mms.py:187` — `if s == 0: return None`. Egzakt egyenlőség, amit a
ház szabálya (`.claude/rules/ifds-rules.md`, „Statisztikai degeneráció-ellenőrzés —
tolerancia-alapú, SOHA `== 0`", 2026-07-21) kifejezetten tilt. Ha egy olcsóbb csomag
**konstans** greeks/IV-t adna vissza hiányzó helyett, a szórás ~1e-17, a guard nem tüzel,
és a z-score szemét lesz.

**Mérve (az adverzariális ellenőrzés, nem az első elemzés):** ez **csak a két átlag-alapú
feature-t** érinti — `iv_rank` és `iv_skew`, az MMS-súly **0,20**-a. Pinelt feeddel:
szórás `1,674e-17` és `2,367e-17`, `s == 0` hamis, `_z_score` 0,0-t ad.
A `gex` **összeg**, nem átlag, ezért konstrukció szerint nem tud így degenerálódni
(ugyanaz a pinelt feed: szórás 5,41e+06, CV 0,448).

→ Ebből következik, hogy **abszolút** tolerancia kell (`1e-12`), nem relatív: az érintett
feature-ök O(1) nagyságrendűek. A relatív forma pont az `iv_skew`-n bukna, aminek az
átlaga legitim módon átlendül a nullán.

### 1.2 A hiányzó mező NEM éri el a guardot (nagyobbik kockázat)

A `day.volume` **soha nem megy át** a `_z_score`-on. Ha a Starter univerzum-szinten
elejtené, a lánc ez:

```
day.volume hiányzik
  → phase4_stocks.py:842-861  pcr = None, otm_call_ratio = None  (MINDEN tickerre)
  → mindkét percentilis-univerzum kiürül
  → compute_percentile_score  bedrótozott 0.5-öt ad vissza
  → minden swing nyers pontszám AZONOS 0.0
```

`None` nélkül, kivétel nélkül, log nélkül. Ez a leminősítés valódi kockázata, és
**tolerancia nem véd ellene** — lefedettség-ellenőrzés kell.

## 2. Megközelítés

Három rész, ebben a sorrendben. Az 1-2. a billing ELŐTT, a 3. a billing UTÁNI első
futáskor.

## 3. Implementációs terv

### 3.1 Tolerancia-guard (`phase5_mms.py`)

```python
#: Abszolút, nem relatív: az érintett feature-ök (iv_rank, iv_skew) O(1) nagyságrendűek,
#: és a relatív forma az iv_skew-n bukna, aminek az átlaga legitim módon nullán megy át.
_DEGENERATE_STD = 1e-12
```

Érintett helyek: `:187`, és ugyanez az alak minden további szórás-alapú ágon
(`:322`, `:407-408`, `:509` — implementáláskor verifikálandó, hogy mind a négy
tényleg szórás-check). `None` visszatérés, nem `0.0` — ez a meglévő „insufficient data"
szemantika, ami a tickert PARTIAL/UNDETERMINED + 0,75-ös szorzóra viszi (fail-closed,
már tesztelt út).

### 3.2 Guard-teszt visszavezetéssel (`tests/test_phase5_degeneracy.py`)

- Konstans IV-láncot hajts a valódi `_compute_aggregate_iv` / `_compute_iv_skew`-n át,
  és állítsd, hogy a z-score `None`.
- **Verifikáció:** az `s == 0` visszaírásakor a tesztnek BUKNIA kell. Különben a teszt
  kimockolta magát (a ház antipattern-szabálya).
- A `test_bc15_mms.py:281` maradjon, de ne számítson lefedettségnek.

### 3.3 Lefedettség-diff (a leminősítés utáni első futás)

`scripts/analysis/options_coverage_diff.py` (új, read-only): a nap `state/mms/*.json` és
`state/phase4_snapshots/*.json.gz` feature-lefedettségét veti össze a rögzített
alapvonallal, és nem-nulla arányt **és** szórást jelent.

**Alapvonal (mérve 2026-10-23, Mini):**

| feature | nem-nulla |
|---|---:|
| `pcr` | 99,8% |
| `otm_call_ratio` | 99,8% |
| `gex` | 99,6% |
| `dex` | 99,6% |
| `iv_rank` | 93,1% |
| `iv_skew` | 91,7% |

⚠️ **A cache-t törölni kell az első futás előtt**: a `get_options_snapshot` *tegnapi*
dátum alatt cache-el (`polygon.py:98`), tehát egy degradált első válasz a futás
hátralévő részére is kiszolgálódna.

## 4. Tesztelés

- Új: `tests/test_phase5_degeneracy.py` — konstans feed → `None`, visszavezetéssel verifikálva.
- Meglévő: a teljes suite zöld marad.
- A lefedettség-diff script öntesztje fixture-adaton (hermetikus, nincs prod-olvasás).

## 5. Commit üzenet

```
fix(phase5): tolerancia-alapú degeneráció-guard + opciós lefedettség-diff

A phase5_mms.py:187 `s == 0` egzakt ellenőrzése konstans feedet nem fog ki (mérve:
szórás 1,674e-17 iv_rank-on, 2,367e-17 iv_skew-n, a guard nem tüzel). Abszolút
1e-12 toleranciára cserélve — abszolút, mert az érintett feature-ök O(1)-esek és a
relatív forma az iv_skew-n bukna, aminek az átlaga legitim módon nullán megy át.
A gex összeg, nem átlag, így nem érintett.

Mellé a valódi kockázat kezelése, ami NEM tolerancia-kérdés: a day.volume el sem éri
a guardot, és univerzum-szintű hiánya a compute_percentile_score bedrótozott 0.5-én
keresztül minden swing pontszámot azonos 0.0-ra lapítana, csendben. Erre
lefedettség-diff script készült, rögzített alapvonallal.
```
