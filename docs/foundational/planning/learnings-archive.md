# IFDS — Learnings Archive

CONDUCTOR `project.db`-ből exportálva 2026-02-26-án (migráció).
Operatív szabályok: `.claude/rules/ifds-rules.md`

---

## BC14 állapot (discovery, 2026-02-11)

BC10: scoring calibration, BC11: circuit breakers + robustness,
BC12: signal dedup + monitoring CSV + async phases,
BC13: survivorship bias, telegram alerts, daily trade limits, notional caps,
BC14: sector breadth analysis (7 regimes, divergence detection, FMP ETF holdings).
636 tests. Breadth adj isolated from ticker scores — crowding stable at 43.

## BC18-prep tanulságok (discovery, 2026-02-21)

Trading calendar: `pandas_market_calendars` opcionális, weekday-only fallback-kel.
Danger zone filter: bottom-10% performers kizárása universe-ből.
FileCache TTL broken volt — mindig stale adatot adott vissza.

## BC19 SIM-L2 Mode 1 (discovery, 2026-02-21)

Parameter sweep engine Phase 4 snapshot persistence-szel.
Paired t-test comparison (scipy). SimVariant config overrides: tuning dict patches-ként.
Phase 4 snapshots: `output/snapshots/YYYY-MM-DD.json`.

## BC18 scope döntés (discovery, 2026-02-21)

IBKR Connection Hardening (retry 3x, 5s/15s timeout, Telegram alert) → BC18-ba kerül.
BC25 Auto Execution bővítve long-running mode-dal.

## Paper Trading PnL tracking (discovery, 2026-02-21)

`cumulative_pnl.json` vs IBKR Realized PnL eltérés: nuke.py előző nap záróárral számol,
nem tényleges fill árral. OBSIDIAN aktiválás NEM dátumfüggő: store entry count >= 21/ticker.

## AVWAP fallback MKT opció (idea, 2026-03-24)

NOG + EFXT unfill eset (Day 27): limit nem teljesült, AVWAP dip+cross sem triggerelt (ár végig AVWAP felett).
2/4 ticker maradt WATCHING → 0 fill. **Potenciális javítás:** ha az AVWAP window végéig (11:30 ET)
nem volt dip+cross, fallback MKT conversion. Kockázat: rosszabb entry-k, ha az ár az AVWAP felett
van de nem igazán erős. Döntés: egyelőre hagyjuk, 30+ nap adat kell a fill rate statisztikához.
Ha a fill rate tartósan <60%, érdemes bekapcsolni.

## STATUS.md — egyetlen igazságforrás Chat/CC/Cowork szinkronhoz (decision, 2026-03-28)

Chat, CC, és Cowork (claude.ai Projects) egyetlen fájlból olvassa a projekt
aktuális állapotát: `docs/STATUS.md`. Chat frissíti session végén (in-place),
CC frissíti `/wrap-up`-kor, Cowork csatolja egyszer.
Motivation: `development-backlog-YYYY-MM-DD.md` pattern stale snapshot-okat
halmozott fel; `CLAUDE.md` Aktuális Kontextus CC írta de Chat döntések nem
jelentek meg benne azonnal.
`CLAUDE.md` ettől stabil referencia marad (ritkán változik) — nem frissítjük
minden session végén.

## Nyitó MKT paper-fill anomália — WST (discovery, 2026-06-01)

Tamás megfigyelése (WST fill $324,33 vs ~$321,66 nyitás) nyomán Polygon 1-perces
vs IBKR `get_account_trades` összevetés 15 swing-era (5/18+) MKT-at-open belépőre.
**Eredmény: a nyitó MKT paper-fillek általában realisztikusak** — 14/15 a nyitó-ablak
high-ján belül vagy marginálisan (≤$0,18) fölötte (normál ask-oldali spread; néhány
kedvező: CDNS -0,06%, AKAM -1,38%, AMH -0,09%). **WST 6/01 az egyetlen valódi
anomália**: a teljes nyitó-ablak high-ja $321,65 volt (13:31-re Polygonban nincs is
print), mégis $324,33-on töltött → +$2,68 (+0,83%) a valós tape FÖLÖTT, ~$48 fantom
belépési költség 18 share-en. Ez **paper-sim artefakt** (IBKR paper szimulált ask
vékony/print-mentes nyitó-percben), NEM szisztematikus.

**Tanulság**: (1) a paper belépő-fillek alkalmanként felülbecslik a belépési költséget
→ a paper P&L ezeknél pesszimista-irányba torzít (ugyanaz a realizmus-kérdés, mint a
nuke-záró-áras cumulative disclaimer). (2) A MKT-at-open ki van téve a nyitó-volatilitásnak
+ paper-sim torzításnak; egy valódi LIMIT a tervezett áron (WST $322,81) itt jobban
töltött volna (~$321,65). **Megfontolandó belépő-timing finomítás** (post-auction MKT
pár perccel a nyitás után, vagy marketable LIMIT open+X bps) — NEM sürgős (1 anomália
13 nap alatt). Referencia: `docs/review/2026-06-01-daily-review.md` §2.

## reqExecutions realizedPNL aszinkron — settle kell (discovery, 2026-06-04)

A Part A első éles MULTI-exit napján (Day 13, 2026-06-03) az Option B recorder
mindhárom exitre **$0.00 realized**-et rögzített, pedig a valós Σ +$229.84 volt.
Gyökérok: `ib.reqExecutions(...)` azonnali olvasásánál a `commissionReport.realizedPNL`
mező **még 0** — a commissionReport ib_insync-ben **aszinkron event**-ként érkezik,
a reqExecutions visszatérésekor még nincs ott. Az `ib.fills()` (amit az eod_report
22:05-kor használ) és a connector `get_account_trades` viszont megkapja a settle után.

**Tanulság / szabály**:
1. Az IBKR realized P&L (`commissionReport.realizedPNL`) kiolvasásához **settle kell**:
   `reqExecutions → ib.sleep(3) → reqExecutions` (re-request), VAGY connect + sleep
   utáni `ib.fills()`. Az azonnali olvasás 0-t adhat.
2. **A 0.0 realized SLD-fillnél gyanús** (egy swing round-trip soha nem pont $0) →
   kezeld unavailable-ként → fallback + warning, NE rögzítsd némán 0-ként.
3. **Új rule-based flag / IBKR-integráció ELŐTT live smoke kell** a következő
   exit-napon — a single-exit (6/2 CDNS) elfedte a hibát, csak a multi-exit (6/3)
   hozta ki. Az 1a review-aggregátor flag-jei is élesben bukták ki a fals-pozitívot
   (days_held trading vs calendar) — a determinisztikus rule-set is élő-validálandó.

**Referencia**: incidens commit `ce3f129` (safety-fix + restatement), robusztus fix
`e3aca99` (settle), Day 14 task `docs/tasks/2026-06-04-recorder-robust-realized-capture.md`,
1a flag-fix `c63cf2f`.
