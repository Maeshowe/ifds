Status: DONE
Updated: 2026-07-21
Note: Struktúra: CC (freeze-safe, csak docs + könyvtár). Hipotézis-TARTALOM: Chat (Dev) írja — CC a template-et és a lint-et szállítja. Spec: docs/design/2026-07-21-factor-research-loop-spec.md (§8).

# FRL-3 — Hipotézis-registry bootstrap + template + lint

## Probléma

Az FRL 1. lépése (HYPOTHESIS) regisztrált, kötelező mezőkkel bíró hipotézis-fájlokat
igényel — teszt ELŐTT megírt mechanizmus-indoklással. Jelenleg nincs struktúra, template,
sem gépi ellenőrzés arra, hogy egy attempt csak regisztrált hipotézisre futhasson.

## Megközelítés

1. `docs/design/frl/hypotheses/` könyvtár + `_TEMPLATE.md` a spec §8.1 szerinti
   fejléccel (Status / Updated / Data-lane / Attempt-family) és kötelező szekciókkal
   (Mechanizmus, Várt előjel és horizont, Vesztes oldal / frikció, Költségprofil,
   Pre-reg metrika és kill-kritérium, Eredmény, KILL/PARK indoklás).
2. `scripts/research/frl_lint.py` — registry-lint:
   - minden HYP-fájl fejléce valid, kötelező szekciók nem üresek
   - **sanity-pár követelmény (R1#6):** REGISTERED státuszhoz a hivatkozott
     faktor-függvénynek létező és zölden futó `sanity()` párja kell — e nélkül
     a HYP nem léphet DRAFT-ból tovább
   - a `run_frl_batch.py` induláskor hívja: attempt csak olyan HYP-ra futhat,
     amelynek Status = REGISTERED vagy TESTED, és a Mechanizmus-szekció kitöltött
     (a hypothesis-first elv gépi kikényszerítése)
   - Status-átmenet szabályok ellenőrzése (pl. HOLDOUT-PASS csak PROMOTED-ból;
     SHADOW csak Day 63 után — dátum-guard)
3. Az első hipotézis-fájl VÁZAK létrehozása az R1#5 a/b szétválasztással
   (HYP-001a/b-pcr, HYP-002a/b-otm-inverse, HYP-003a/b-rvol — az a: transzform-szintű
   v1, a b: nyers v2, KÜLÖN attempt-család; + HYP-004-sector-relative-reversal) —
   a tartalmi szekciókat Chat tölti fel külön körben; addig Status: DRAFT, amit a
   lint futtatás-tiltással kezel. A template-be az a/b aszimmetria-szabály
   figyelmeztető sora (spec §8.2) bekerül.

## Implementációs terv (fájlok)

Új:
- `docs/design/frl/hypotheses/_TEMPLATE.md`
- `docs/design/frl/hypotheses/HYP-001..004-*.md` (váz, Status: DRAFT)
- `scripts/research/frl_lint.py`

Tesztek (`tests/test_frl_lint.py`):
- valid template átmegy; hiányzó Mechanizmus-szekció bukik
- DRAFT-ra attempt-futtatás tiltva
- illegális Status-átmenet detektálva; SHADOW dátum-guard

## Commit

`feat(research): FRL hypothesis registry structure + lint (hypothesis-first enforced)`

## Eredmény (2026-07-21, CC)

- `docs/design/frl/hypotheses/_TEMPLATE.md` + **7 hipotézis-fájl** (HYP-001a/b, 002a/b,
  003a/b, 004), mind `Status: DRAFT` — a lint futás-tiltással kezeli.
- **HYP-004 tartalma teljes** (Chat, 2026-07-21): mechanizmus (Jegadeesh/Lehmann +
  likviditás-nyújtás kompenzáció; a „magas pontszám paradoxon" tükörmérése a teljes
  keresztmetszeten), `expected_sign = -1`, h=3-5 maximum, magas turnover / half-life
  2-4 nap, 3 ágú kill/park-kritérium (a (c) ág: bruttó-pass + costed-IC ≤ 0 → PARK
  `execution-style-input` címkével). A `REGISTERED` átállítás Chat/Tamás lépése.
- `scripts/research/frl_lint.py`: fejléc-, szekció- és placeholder-ellenőrzés,
  Status-átmenet térkép (HOLDOUT-PASS csak PROMOTED-ból; SHADOW csak HOLDOUT-PASS-ból),
  **SHADOW dátum-guard** (Day 63 = 2026-08-17, NYSE-naptárból számolva),
  `assert_runnable()` + `assert_sanity_pair()`.
- **A batch gate-elve**: `run_frl_batch` a sanity-kapu UTÁN hívja az `assert_runnable`-t;
  DRAFT vagy hiányzó HYP → `BLOCKED` sor a riportban, **nincs ledger-sor**.
- Tesztek: +25 (`tests/test_frl_lint.py`) + 2 batch-gate teszt → **2109 passing**.
  A checked-in registry saját maga is lint-clean (regressziós teszt).
