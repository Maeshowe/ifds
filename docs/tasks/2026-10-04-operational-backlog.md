Status: OPEN
Updated: 2026-10-04
Note: A freeze alatt gyűlt operatív backlog. A 2026-10-04-i session a 3 ZÉRÓ-KOCKÁZATÚ tételt elvégezte (lásd §1); a maradék 3 TUDATOSAN ELHALASZTVA, mert production kereskedési kódutat érint és a session hosszú volt ([[long-session-degradation]]). Egyik sem sürgős: a kereskedés adatgyűjtési módban áll.

# Operatív backlog — a freeze utáni takarítás

## 1. ✅ ELVÉGEZVE (2026-10-04)

| Tétel | Mit | Hol |
|---|---|---|
| **`KNOWN_GAPS` elavult** | A batch 5 dokumentált outage-napot „nem dokumentált hiány"-ként jelzett (04-06, 04-07, 07-22, 08-07, 08-21) → a figyelmeztetés jel/zaj aránya elromlott, egy **valódi** új hézag elbújt volna köztük. Mind az 5 hozzáadva, forrás-hivatkozással; `nem várt: 12 → 0`. | `scripts/research/frl_config.py` + `TestKnownGapsCoverage` (13 teszt) |
| **Elavult score-formula docstring** | `_calculate_combined_score` 0.40/0.30/0.30-at írt; a valódi **0.60/0.10/0.30** BC23 óta. Elemzésben is idéztem, mielőtt elkaptam. Javítva + a `flow.rvol_score` 7-tagú összeg-természete kimondva. | `src/ifds/phases/phase4_stocks.py` |
| **Stale returns-cache** | `research/cache/returns.parquet` 2026-07-25-i volt (`fwd_ret_5` csak 07-17-ig) → a HYP-005 újrateszt hamis POZITÍV leletet adott. Újraépítve 162 napra. | `research/cache/` (gitignore-olt) |

**Lezárva, nincs tennivaló:** `docs/analysis/` sync-rés — már gitignore-olt
(`.gitignore:66`), a 2026-07-23-i aszimmetrikus feloldás (`8e0d296`) óta rendben.

---

## 2. ⏸ ELHALASZTVA — production kereskedési kódút

> **Egyik sem sürgős:** a kereskedés **adatgyűjtési módban** áll
> (`state/trading_enabled.json: enabled=false`), tehát egyik defekt sem termel új hibát.
> Mindhárom **akkor** válik esedékessé, ha élesítés merül fel — és akkor **új élő
> pre-reg** is kell, tehát együtt kezelendők.

### 2.1 §11.17 — `daily_metrics::exit_type` az ABLAK default címkéjét adja

**Diagnózis (kész, §11.17):** amikor a fill a várt időablakba esik, a mező **helyes**;
amikor nem (pl. a 08-21-i outage okozta 2h21m késés), **„MOC"-ra degradál**. Nem
általános romlás — ablak-feltételes.

**Miért halasztva:** a `daily_metrics.py` **éjjel fut és nincs guardolva** (szándékosan —
ő írja a kutatási adatfolyamot). Egy hiba itt **adatvesztés**, nem csak egy rossz címke.

**A fix iránya:** az `exit_type` ne az ablakból következtessen, hanem a
`state/pending_exits/{date}.json` kanonikus ledgerből olvasson (ez a
`signal_attribution` 2. invariánsa is). Guard-teszt: egy ablakon kívüli fill-timestamp
**ne** változtassa meg a címkét.

### 2.2 §11.18 — a napi szektor-cap flag néma marad, míg a cap köt

**Diagnózis (kész, §11.18):** a review `sector_cap_proximity` flagje a **jelenlegi**
kitettséget méri a 25%-os küszöbhöz, a Phase 6 korlátja viszont **előretekintő**
(`phase6_sizing.py:1581`: `new_sector_total > sector_cap_usd`). 2026-09-03-án a flag
hallgatott (21,86% < 25%), miközben a cap tényleg kizárt jelölteket.

**Miért halasztva:** review-pipeline kód, **zéró kereskedési kockázat** — de a
kereskedés áll, review nem generálódik, tehát most **nincs értéke**. Akkor kell, amikor
a review-stack újraindul.

### 2.3 `pt_monitor --mode=eod_eval` — a RÉGI `check_trading_day` bypass

**Diagnózis (kész):** a `--mode=eod_eval` **a guardok ELŐTT** dispatchel és korán
visszatér, tehát **mindig** megkerülte a `check_trading_day()`-t. A 2026-10-03-i D8
munkában a **saját** `check_trading_enabled()` guardomat a dispatch ELÉ tettem, a
meglévőt **tudatosan nem mozdítottam** (mandátumon kívül) — kódkomment jelzi.

**A fix:** a `check_trading_day()` is a dispatch elé. **Egysoros mozgatás**, de
production kereskedési script → tesztek kellenek mellé (nem-kereskedési napon az
`eod_eval` is cleanly exiteljen).

---

## 3. 🔑 TAMÁS-AKCIÓ (nem CC)

| Tétel | Mit |
|---|---|
| **UW `.env` kulcs rotáció** | A `IFDS_UW_API_KEY` még a `.env`-ben van, miközben a UW **kivezetve** (`docs/decisions/2026-08-18-uw-decommission.md`). Credential-rotációt CC nem végez. |
| **UW dormant kód eltávolítása** | **10 production modult** érint (`runner.py`, `phase4_stocks.py`, `phase5_gex.py`, `phase0_diagnostics.py`, `async_clients.py`, `unusual_whales.py`, `async_adapters.py`, `config/{loader,defaults}.py`, `models/market.py`). Ez **nagy refaktor**, és a stratégia jövője még nyitott → **érdemes kivárni** a HYP-006/007/008 dekompozíciót. Ha a jelcsalád leáll, a refaktor tárgytalanná válhat. |

---

## 4. Következő session teendő

Ha élesítés merül fel: a 2.1–2.3 **együtt**, TDD-vel, friss sessionben, és mellé
**új élő pre-reg** (a 2026-07-25-i protokoll nem újrahasznosítható).

Ha a HYP-006/007/008 dekompozíció mind a hármat kinullázza (C forgatókönyv), a 2.1–2.3
és a 3. pont **tárgytalan** — akkor nem javítunk egy leállított stratégia kódútját.


---

## 5. A 2026-10-04-i repo-audit maradéka (alacsony prioritás)

A 58-ügynökös, 6-dimenziós audit **32 leletet erősített meg** (20-at az adverzariális
verify elvetett). A HIGH és MEDIUM tételek ebben a sessionben elintézve
(`3c6ccee`, `f4c963a`, `457fb1b`, `eb9ae85`, `68f39d9`). Ami maradt:

| # | Lelet | Miért halasztva |
|---|---|---|
| **31** | A ledger-sorok csupasz `NaN` / `Infinity` literált szerializálnak (14/23 sor) — ez **nem érvényes RFC 8259 JSON**. A Python `json` alapból elfogadja, ezért a sáv saját eszköztára működik; egy szigorú parser (JS `JSON.parse`, Go `encoding/json`) elutasítja. | A `_write_ledger` **minden** `close_attempt`-kor újraírja a teljes fájlt, tehát a javítás az összes historikus sort is újra-szerializálja — a null-ra cserélés **információt veszítene** (a NaN "nincs adat", a 0.0 "mérve nulla"). Megfelelő fix: sentinel-objektum vagy `null` + külön `_nan_fields` lista, migrációval. Nem triviális, és a ledger az audit-lánc. |
| **24** | `04-risks` §12.2 azt írja, a költség-medián „stabil ~96 bp körül" — a 2026-09-22-i modell **83,5 bp**. | Kozmetikai; a §12.2 javított blokkja már a 83,5-öt idézi. |
| **25** | `docs/foundational/analysis/weekly/2026-W18-analysis.md` a BC23 előtti 0,40/0,30 súlyokat írja. | **Szándékosan nem javítom:** egy dátumozott historikus elemzés, ami a saját idejében pontos volt. Átírása ugyanaz a hiba lenne, mint a TRACKER dátumozott soraié. |
| **28/b** | A `panel_coverage()` most **kiírja** a derivált cache frissességét, de **nincs hard guard**, ami elbuktatná a futást, ha a panel elavult a `run_date`-hez képest. | A kiírás a szabály betűje, és a stale-cache epizód így is azonnal látszott volna. A hard guard küszöbe (hány nap elmaradás tiltó?) **nem kalibrálható független forrásból** — ugyanaz az indok, amiért a felbontás- és a horizont-kapu sem készült el. |

**A verify által ELVETETT 20 lelet** (pl. „header.tex korrupt duplikátum",
„négy halott .gitignore szabály", „a nyitott-task lekérdezés elrejt 2 WIP taskot")
szándékos állapotok vagy téves bizonyítékon álltak — nem kell velük tenni semmit.
Teljes kimenet: a session workflow-naplója.

### 5.1 Pre-existing lint (nem ebben a sessionben keletkezett)

`ruff check scripts/ tests/ src/` → **23 hiba, mind olyan fájlban, amit ez a session
nem érintett** (minden általa írt/módosított fájl tiszta, fájlonként verifikálva):

| Fájl | Hibák |
|---|---|
| `scripts/admin/retroactive_reconcile_w21.py` | F401 unused import, F841 unused var |
| `scripts/company_intel.py` | F841 unused var |
| **`scripts/paper_trading/eod_report.py:710`** | F841 `total_trades` — ⚠️ **production kereskedési script**, ezért a §2 szabály szerint elhalasztva |
| `src/ifds/**` | 11 további (nem auditált hatókör) |

Nincs lint-gate a CI-ban; ha lesz, ezeket előbb fel kell takarítani, különben a
gate első naptól piros.
