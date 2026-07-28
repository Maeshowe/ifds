Status: DONE
Updated: 2026-07-28
Note: CROSS-FLAG a FRL build-sessiontől — NEM Support-feladat (a Support csak jelzi). A pt_events go-forward rés ZÁRVA (db95c13). Ez a historikus (múltbeli) szennyezés kezelése, ami FRL-loader-tétel. Forrás: pt_events P1 lezárás melléktalálata.

# CROSS-FLAG → FRL build-session: historikus pt_events fixture-szennyezés a rank-2 forrásban

## Miért kapod ezt

A `pt_events` az **FRL loader rank-2 forrása** (`docs/design/2026-07-21-factor-research-loop-spec.md`
§4.1). A pt_events test-env-hygiene P1 lezárásakor (Support, `db95c13`) kiderült: a **go-forward
rés zárva** (a teszt már nem szennyezi a logot), de a **múltbeli logok szennyezettek maradtak** —
és ezeket a loader visszamenőleg olvashatja. Ez a [[test-env-hygiene]] historikus lába; a Support
csak **jelzi**, a megoldás a loader felelőssége (nem destruktív log-átírás).

## A szennyezés pontos képe (verifikálva 2026-07-24)

A pytest fixture-blokk determinisztikus: `circuit_breaker` (`cum_pnl=-6000`), `moc_submitted`,
`trail_activated_a/b`, `tp1_detected`, `phantom_filtered` események **fixture-tickerekkel**
(AAA/BBB/CCC ÉS realisztikusak: LION/SDRL/AAPL/KMI/F/MSFT/BTU/CSGS/COP/LB). A tiszta ujjlenyomat:
a **47-soros / 7613-bájtos blokk**.

**Szennyezett napok (`logs/pt_events_*.jsonl`), 07-23 már cleanelve:**

| dátum | nap | jelleg |
|---|---|---|
| 2026-06-01 | Mon | mixed (valós + fixture) |
| 2026-06-03 | Wed | mixed |
| 2026-06-04 | Thu | mixed |
| 2026-06-06 | Sat | ~tiszta fixture (47) |
| 2026-06-07 | Sun | ~tiszta fixture (47) |
| 2026-06-11 | Thu | mixed |
| 2026-06-14 | Sun | mixed (141) |
| 2026-06-21 | Sun | ~tiszta fixture (47) |
| 2026-06-28 | Sun | ~tiszta fixture (47) |
| 2026-07-07 | Tue | mixed (154) |
| 2026-07-12 | Sun | ~tiszta fixture (47) |
| 2026-07-19 | Sun | ~tiszta fixture (47) |

**Fontos:** NEM csak vasárnapi cron — hétköznapi manuális pytest futások is (06-01/03/04/11, 07-07).
Tehát a szűrőnek **dátum-agnosztikusnak** kell lennie (nem elég a "vasárnapok kizárása").

## Javaslat (Support-ajánlás, a döntés a tiéd + Tamásé)

**(b) tartalom-alapú loader-szűrés** — NEM destruktív cleanup. A loader a rank-2 pt_events olvasásakor
dobja el a fixture-eseményeket a szignatúra alapján. Robusztus szűrő-jelöltek (kombináld, ne egyet):

1. `event == "circuit_breaker"` ÉS `cum_pnl == -6000` (a fixture konstans; valós circuit_breaker sosem
   pont −6000 kerek).
2. `ticker ∈ {AAA, BBB, CCC}` (tiszta fixture-tickerek, valós univerzumban nincsenek).
3. A **47-soros determinisztikus blokk** egészének detektálása (azonos `ts`-percre eső, azonos
   esemény-multiszettel — a fixture-dump egy wall-clock percen belül 47 sort ír).

⚠️ Az (1)+(2) önmagában **alulbecsül**: a 47-soros napokon csak ~5 az AAA/BBB/CCC, a többi 42 realisztikus
tickerrel megy. Ezért a **percenkénti-blokk heurisztika (3)** a legmegbízhatóbb: a valós swing-ops
percenként max néhány eseményt ír, a fixture-dump 47-et egy percbe.

**Miért (b) és nem (a) destruktív cleanup:** a loader-nek úgyis robusztusnak kell lennie a historikus
szennyezésre (immutability — a historikus logokat ne írd át; a [[freeze-production-churn-rule]] és a
`sync --delete` konfliktus-osztály elkerülése). A precedens (07-23) időablak-szűrője **egy-napos, kézi**
volt; a historikus 12 napra általánosítani kockázatosabb, mint a loader-oldali szűrés.

## Ami már kész (ne csináld újra)

- Go-forward rés ZÁRVA: `db95c13` (`IFDS_PT_EVENT_DIR` + conftest izoláció).
- 07-23 log cleanelve (194 → 6 sor, backup `.bak.pre_testclean`, byte-azonos Mini+lokál).
- Ez a note csak **flag** — ha úgy döntesz, a saját FRL-taskodba emeld be és zárd itt (`REJECTED`/`DONE`).

## Referencia

- Precedens: `docs/tasks/archive/2026-07-23-pt-events-test-isolation.md`
- Loader spec: `docs/design/2026-07-21-factor-research-loop-spec.md` §4.1
- Detektáló egyszeri script: `scratchpad/clean_pt_events_0723.py` (időablak-szűrő, egynapos)


---

## Lezárás (2026-07-28) — a task PREMISSZÁJA HIBÁS VOLT

### A hiba

A cross-flag azt állította, hogy a `pt_events` az **FRL loader rank-2 forrása**, ezért a historikus
szennyezés a kutatási pipeline-t torzítaná. **Ez téves** (a hibát CC követte el a 2026-07-23 review
§6/P1-ben, majd a cross-flagben megismételte).

**Verifikáció (2026-07-28):** a `scripts/research/` fában **NULLA** hivatkozás van a `pt_events`-re.
A loader (`frl_loader.py`) a `full_scan_matrix_*.csv` (rank-1) és az `ifds_run_*.jsonl` (rank-2)
forrásokat olvassa — a spec §4.1 is ezt írja. **A pt_events nem FRL-forrás.**

**A valódi rank-2 forrás (`ifds_run_*.jsonl`) TISZTA** — ellenőrizve; az egyetlen gyanús találat
(`"CCC"`) egy **valódi ticker** (CCC Intelligent Solutions), nem teszt-fixture.

### Ami valóban történt, és amit tettünk

A szennyezés csak a `pt_events_*.jsonl`-t érintette (ops-review felület, nem kutatás):

- **5 fájl 100% teszt-output** (2026-06-07/06-21/06-28/07-12/07-19, mind vasárnap, 47 esemény,
  **azonos esemény-szignatúra** `403d7c0b…`, kizárólag fixture-tickerek: AAA/BBB/CCC/AAPL/MSFT/
  KMI/F/BTU/CSGS/COP/LB/LION/SDRL). Vasárnap nincs kereskedés → ezeknek létezniük sem kellene.
  **→ karanténba** (`logs/_quarantine_test_fixture_sundays/`, Mini + sync). Egyik napra sem
  készült review, tehát nulla downstream hatás.
- **~10 vegyes fájl** (valós kereskedési nap, valós esemény + fixture-blokk): **ÉRINTETLENÜL HAGYVA**.
  Indok: a takarítás során kiderült, hogy a „legacy esemény-név = fixture" detektor **hamis** — a
  `trade_closed` valódi swing-korszaki esemény (pl. 07-08 PFGC 63 @ 115.25→112.38 pnl −180; 06-10
  VNO; 05-20 VLO). Egy agresszívabb szűrő **valódi kereskedési történetet törölt volna**.
  Kockázat > haszon: a go-forward rés zárva (`db95c13`), a kutatási pipeline érintetlen.

### Következtetés

**Nincs szükség FRL-loader-szűrésre.** A task lezárva; a maradék historikus `pt_events` szennyezés
dokumentált, ismert korlát az ops-review felületén (nem torzít kapu-inputot és nem torzít FRL-adatot).

**Tanulság (a hibaosztály):** két egymást követő fals detektor (`"CCC"` mint fixture, `trade_closed`
mint legacy) — **grep-alapú szennyezés-detektor önmagában nem elég**; a törlés előtt a *tartalom*
(ticker-halmaz + esemény-szignatúra + valós P&L-mezők) verifikálandó. A biztonságos műveletet
(5 azonos-szignatúrájú, 0 valós tickeres fájl) elvégeztük, a bizonytalanhoz nem nyúltunk.
