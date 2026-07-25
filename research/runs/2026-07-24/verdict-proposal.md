# HYP-005 verdikt-javaslat — a második fordulat (2026-07-25, CC)

> **Leíró elemzés — Day 63 gate-input NEM (G1/G3).** A HYP-005 kifejezetten a
> `signal_attribution` kapu-teszt **leíró ikertestje**: az eredménye a Day 63
> deliberációban se pro, se kontra nem idézhető.

Batch: `research/runs/2026-07-24/report.md` (run_date 2026-07-24, attempt A-0005..A-0008).
Dev-ablak: swing **23 nap** (05-18..06-18), legacy üres (a faktor swing-only);
holdout-érintés **0**.

## VERDIKT-JAVASLAT: **PARK-until-swing-power** (családi szinten, a primary h=5 alapján)

**A ledger auto-verdiktje mind a 4 horizonton KILL** — de ez egy azonosított
**logikai rés** eredménye, nem a helyes családi verdikt. Lásd lent. A javasolt
emberi döntés a `confirm_decision` override-dal:

| Attempt | h | T_eff | mean IC | NW t | p | éra-bar | verdikt | **javaslat** |
|---|---|---|---|---|---|---|---|---|
| A-0005 | 1 | 23.0 | +0.0079 | 0.51 | 0.617 | 0.0311 | inconclusive | **KILL** (adekvát T_eff, valódi null) |
| A-0006 | 3 | 7.7 | +0.0235 | 1.01 | 0.347 | 0.0467 | inconclusive | **KILL** (T_eff≥6, valódi null) |
| A-0007 | **5** | **4.6** | **+0.0435** | **2.37** | 0.077 | 0.0367 | **mérhető** | **PARK** (alulfeszített, jó előjel) |
| A-0008 | 7 | 3.3 | +0.0522 | 3.54 | 0.071 | 0.0295 | mérhető | **PARK** (alulfeszített, jó előjel) |

Šidák-családi p (4 h-variáns, swing): **0.2564** — BH-fail (q=0.10). Half-life
**10.3 nap** (a HYP-004 2.4 napjának 4×-e — lassú faktor); implikált forgási
költség **4 750 bp/év** (a HYP-004 19 827-jének ¼-e).

## Miért PARK és nem KILL — a HYP-005 saját pre-reg (c) kritériuma

A hipotézis regisztrált kill/park-kritériuma: **(a)** családi Šidák p ≥ 0.10
**elégséges T_eff mellett** → KILL; **(b)** szignifikáns NEGATÍV előjel → KILL;
**(c) T_eff elégtelen → PARK-until-swing-power**.

- **Az előjel helyes** mind a 4 horizonton (pozitív, a mechanizmussal egyező),
  és a h-görbe **emelkedő** (0.008 → 0.052, h=1→7) — a mechanizmus keresztmetszeti
  formája irányban konzisztens. A (b) ág **nem** aktiválódott.
- **A primary horizont (h=5) T_eff = 4.6**, a h=7 pedig 3.3 — mindkettő a §5.5
  szerinti **detektálhatósági küszöb (≈6) alatt**. A családi p 0.2564-es bukása
  tehát **erő-korlátos, nem null-jelzés**. Ez pontosan a **(c) ág**.
- **Fegyelmi pont (a HYP-004-tükör):** a h=5 egyedi NW t=2.37 (p=0.077) önmagában
  majdnem szignifikáns, de **a cellakiemelés ellen a Šidák-családi p véd** — pont
  ahogy a HYP-004-nél a h=7-et nem emeltük ki. A PARK **nem** felülbírálja a
  deflációt; azt mondja, hogy a minta még nem elég nagy a döntéshez.

**A h=1/h=3 KILL indoka:** ott a T_eff **adekvát** (23, illetve 7.7 ≥ 6), és az IC
a bar alatt, statisztikailag null (NW t 0.51/1.01) — ezeken a horizontokon **van
elég erő**, és tiszta a bukás. Ez a (a) ág. Vagyis a család rövid horizontjain
nincs jel, a swing-horizonton (h=5) alulfeszítetten ígéretes → **a család PARK.**

## Költség-kapu — külön, jövőbeli akadály (nem a mostani döntés hajtója)

A cost-modell aktuális swing-értékén (97.0 bp/oldal) a **breakeven IC 0.15–0.18**
(h=5/h=7), a tényleges IC 0.04–0.05 — nettó mind a 8 cellában negatív. **De a
HYP-005 G1 szerint NEM tradeability-állítás** (leíró ikertest), ezért a
costed-fail **informatív, nem a verdikt-hajtó**. Ha a jel valaha megszilárdul,
a costed-IC egy **második, független kapu** lesz (a jelnek ~3×-ára kell nőnie).

## Azonosított logikai rés az auto-verdiktben (javítva: `<this commit>`)

**A rés:** a `promote_verdict` a `PARK_UNTIL_SWING_POWER`-t **csak** legacy-támogatás
mellett engedte. Egy **swing-only** faktornál (mint a HYP-005) nincs legacy láb →
`legacy_supports` mindig `False` → a PARK-út **soha nem tud tüzelni**, csak PROMOTE
vagy KILL. Ez **ellentmond a HYP-005 saját pre-reg (c) kritériumának**.

**A javítás (T_eff-adekvácia gate, §5.5):** a terminális KILL mostantól vagy
(b) előjel-ellentmondást, vagy (a) **adekvát T_eff (≥6) melletti tiszta bukást**
igényel. Ha az előjel helyes és minden éra alulfeszített → **(c) PARK**, a
swing-only faktorokra is. A HYP-004 KILL **változatlanul áll** (a legacy láb
T_eff=11.8 adekvát és bukott → KILL) — dedikált regressziós teszt védi.

**A ledger A-0005..A-0008 sorai auto-KILL-en maradnak** (nem futottam újra a batch-et,
hogy ne inflálódjon az attempt-szám); a javasolt verdiktek a `confirm_decision`
override-jával kerülnek be. A javított logika a **következő** batch-futásra natív.

## Ha PARK: mi történik ezután

- A `retest_due` a bar heti ~5 nappal lazuló szintjén automatikusan újraértékel;
  a h=5 T_eff a swing-minta növekedésével átlépheti a küszöböt.
- A holdout-touch **nem** költött (0 érintés) — a PARK ezt megőrzi.
- A v2 sáv (nyers PCR/OTM, HYP-001b/002b) ~szeptember közepén érik be; a HYP-005
  (transzform-szintű) és a v2 (nyers) együtt adja majd az a/b-képet.

## Tamásra vár

1. **Verdikt-döntés**: a fenti PARK(h5,h7)/KILL(h1,h3) javaslat elfogadása vagy
   módosítása. Megerősítés: `frl_ledger.confirm_decision(attempt_id, by="Tamás",
   decision=..., note=...)` — az auto-KILL `auto_decision`-ként megmarad.
2. **A logika-fix jóváhagyása** (governance-érintő): a T_eff-adekvácia gate
   ezentúl minden faktor verdiktjét befolyásolja.
