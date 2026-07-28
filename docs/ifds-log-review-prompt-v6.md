# IFDS — Daily Log Review Prompt v6 (swing pivot)

**Verzió**: v6 — 2026-06-11. A v5-öt (legacy intraday: bracket/AVWAP/BMI architektúra) teljes egészében leváltja; a v5 archiválandó.
**Executor**: **CC** (2026-07-25 óta az IFDS CC-only, egyelőre — a napi review + heti report + biweekly
scoring_validation mind CC-nél; korábban „Chat vagy CC", azonos szabályokkal). A review-automatizáció ezt a
fájlt tekinti kanonikus specnek.
**Hatókör**: READ-ONLY a production filesystemen; írás kizárólag `docs/review/` (+ `docs/handoff/`).

---

## Mi a review?

A napi review **mérési jegyzőkönyv, nem narratíva**. Három olvasója van: Tamás (napi operatív döntés), a Dev chat (backlog-input), és a Day 63/126 kiértékelés (amelynek ez nyers bemenete). A review értékét az adja, hogy hónapokkal később is pontosan rekonstruálható belőle, mi történt és mi volt akkor tudható — nem az, hogy milyen izgalmas.

**A három legfontosabb szabály:**
1. **Forrás nélkül nincs szám.**
2. **Day 63 előtt nincs jel-ítélet.**
3. **Minden tény pontosan egyszer szerepel.** Cél: ≤120 sor.

---

## Anti-hallucinációs szabályok (kötelező)

1. **Minden számszerű állítás mellé forrás** — fájl-útvonal vagy IBKR-hívás neve. Ha egy adat nem található: `n/a (forrás hiányzik)` — becslés jelöletlenül TILOS.
2. **Forrás-hierarchia ütközésnél**: IBKR API > `daily_metrics` / `cumulative_pnl.json` (broker-authoritative lánc) > `pending_exits` > `pt_*.log` > `trades_*.csv`. Ha két forrás eltér: **mindkettő riportálva + ⚠️ flag** — csendben választani tilos.
3. **Ismert hibás mezők** (a P1 fixek élesítéséig): a `daily_metrics::trades::details::exit_type` TP1/TP2-re megbízhatatlan (fill-timestamp-alapú) és a Telegram-render exit_type/P&L self-reentry esetén hibás. **Exit-típus forrása kizárólag: `state/pending_exits/{date}.json`.** Ezt a bekezdést a fixek éles verifikálása után törölni kell.
4. **Prognózis** megengedett, de mindig `várt` jelöléssel + a feltevéssel (pl. fill-szint). Másnap **kötelező a várt-vs-tény visszamérés** $-eltéréssel — ez a review-pipeline minőségmérője.
5. **Ok-feltételezés** (company-hír, szektor-hatás, makró-magyarázat) csak `hipotézis:` prefixszel + a megnevezett ellenőrzési lépéssel. Kijelentő módban tilos.
6. Ha egy log **hiányzik vagy üres**, az tényként rögzítendő — emlékezetből vagy mintázatból pótolni tilos.
7. A review **nem számol újra** broker-adatot saját képlettel; ha az ellenőrző összeg nem egyezik, az eltérés riportálandó, nem feloldandó.

---

## Epistemikus guardrail (Day 63-ig érvényes)

1. **Tiltott szavak jel-/tézis-állításra**: „validál(t)", „bizonyít(ott)", „igazolt", „edge megerősítve". Megengedett: „konzisztens vele", „iránymutató", „minta (n=X)".
2. **Minden statisztika n-nel** és definícióval (mit számolunk, mióta).
3. **Legacy-összevetés hányadosként tilos** (pl. „TP-hit 6,8× javulás") — a 6 órás bracket és az 5 napos mental-stop exit-ablak nem összemérhető. A swing-run statisztikák önállóan riportálandók.
4. **⭐, „TÖRTÉNELMI", szuperlatívuszok: nem használjuk.** A prioritást a P0–P3 jelzi, a nap karakterét egy tényszerű mondat zárja.
5. Jel-érvényességi következtetés a `signal_attribution.py` és a Day 63/126 kapuk dolga. **A review megfigyel és rögzít — nem ítél.** A kapu-kritériumokhoz képesti állás (buffer %) riportálható, de a kapu-kimenetel előrejelzése nem.

---

## Fájlforrások (swing pivot architektúra)

| Forrás | Mit ad |
|---|---|
| `state/swing_positions.json` | nyitott pozíciók, days_held, stop/TP szintek, EOD flagek |
| `state/pending_exits/{date}.json` | **exit_type kanonikus forrása**, processed státusz |
| `state/daily_metrics/{date}.json` | napi metrikák, commission, slippage_per_ticker, VIX |
| `scripts/paper_trading/logs/cumulative_pnl.json` | kumulatív P&L (broker-authoritative), tp1/tp2/moc számlálók |
| `logs/pt_submit_{date}.log` | entry-k, planned vs fill |
| `logs/pt_close_{date}.log` | 15:30 exitek + 21:40 MOC |
| `logs/pt_monitor_{date}.log` | EOD eval (22:00), flagek |
| `logs/pt_reconcile_{date}.log` | state↔IBKR reconcile (silent OK számít) |
| `logs/pt_eod_{date}.log` | Telegram-render (ellenőrizendő, nem forrás) |
| `logs/cron_{date}_*.log` | pipeline Phase-futás, ERROR/WARNING |
| `state/uw_shadow/{date}.json` | UW shadow (Day 90 auditig csak gyűjtés) |
| IBKR MCP: `get_account_summary`, `get_account_positions`, `get_account_trades` (`TODAY`/`DAYS_7`) | Net Liq, pozíciók, fillek — végső igazságforrás |

---

## Kötelező szerkezet (ebben a sorrendben)

**1. Fejléc** (max 6 sor): Day N/63 (NYSE-count) · realized net (gross; commission) · cumulative · Net Liq + napi Δ · excess % (a számítás szemantikájának megjelölésével) · nyitott pozíciók száma.

**2. Exits tábla**: idő · ticker · típus (pending_exits-ből) · qty · entry→fill · broker realized · előző napi `várt` · eltérés $.

**3. Entries tábla**: ticker · szektor · qty · planned→fill · slippage % · stop/TP1/TP2.

**4. Nyitott pozíciók tábla**: ticker · days_held · mark · unrealized · stop-buffer % · next_action (EOD flag). Összesítő sor: total unrealized.

**5. Ops-checklist** (soronként egy tétel, ✓/⚠️): reconcile N/N silent OK (futó számláló) · cron-időzítés-eltérések · ERROR/WARNING a logokban · Telegram-render egyezik-e a `daily_metrics`-szel (ha nem: ⚠️ + melyik mező) · **v2 enrichment sink** (KÖTELEZŐ, minden nap — FRL-5 deploy-előfeltétel 2): a
`state/research_cross_section/{date}.json.gz` `n_rows`/`n_scored` mezője egyezzen a napi `full_scan_matrix`
sor- és scored-számával. Eltérés → ⚠️ + §6-ba. *(Ellenőrzés: a gz `records` kulcsa a tábla; a `n_scored` a
nem-null score-ú sorok száma.)* · **STOP-triggerek** (KÖTELEZŐ, minden nap): a `python scripts/analysis/stop_trigger_monitor.py --review-line` kimenete szó szerint. A pre-reg halt-kritériumok (10/15 napi excess < −1.0%, 30 napi kumulatív < −3.0%; 2026-05-14 §3.14) folyamatos monitorozása — a monitor **csak jelez**, a leállítás Tamás-döntés. Breach esetén a §6-ba is P1-ként.

**6. Anomáliák** — **csak ÚJ vagy változott** tételek: P-prioritás · leírás · forrás-útvonal · javasolt gazda (CC-task / megfigyelés / Day 63-input). Ismert, visszatérő anomália: 1 sor + az első előfordulás dátum-hivatkozása. Tilos ugyanazt a findingot a review több pontján megismételni.

**7. Megfigyelés-sorozatok** (pre-regisztrált gyűjtések, következtetés NÉLKÜL, mindig kumulatív n-nel): next-day MKT fill eltérés (n, átlag %) · self-reentry esetek (n, entry-slippage, ROI ha zárult) · major risk-off napok excess (n, átlag) · TP-hit és pozitív-exit ráta (n exit) · daily-eval fordulatok (n). Új sorozat csak Dev chat jóváhagyással vehető fel.

**8. Holnap**: várt exitek sávval + feltevéssel · fókuszlista max 5 tétel.

**9. Freeze-sor** (kötelező, minden nap): `Paraméter-érintő változás ma: nincs` VAGY a tétel + a `04-risks` log-hivatkozás.

**10. A nap egy mondatban** — tényszerű, jelző-minimum, max 30 szó.

---

## Heti zárás (péntek, a napi review után)

Max +20 sor: 5 napos P&L-tábla · a heti várt-vs-tény pontosság összesítve · a megfigyelés-sorozatok heti állása · cross-chat sync tételek (ha a Dev chatnek szóló észrevétel született: `04-risks` vagy `backlog-ideas` bejegyzés + 1 soros jelzés).

---

## Mentés

```
Filesystem:write_file → docs/review/YYYY-MM-DD-daily-review.md
```
Ha a fájl már létezik: NEM felülírni — `-v2` suffix és a fejlécben az ok.

---

## Tiltások összefoglalva

Nem fejlesztünk, nem módosítunk production fájlt, nem javaslunk freeze-sértő változást (paraméter, scoring, exit-logika — ezek Day 63-input címkével a 6. szekcióba kerülnek), nem ítélünk jel-érvényességről, nem becslünk forrás nélkül, nem ismétlünk, nem használunk szuperlatívuszt. A review akkor jó, ha unalmas és visszakereshető.
