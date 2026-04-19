# Operational Playbook — What to watch, when

**Utolsó frissítés:** 2026-04-17
**Célja:** Napi/heti sorvezető. Mikor mit nézzen Tamás, mikor mit mutasson nekem (Chat), mikor mi CC feladat.
**Frissítsd:** amikor a naptár tolódik vagy új folyamat jön.

---

## 1. A három szereplő és a felelősségek

| Szereplő | Mit csinál | Hogyan |
|----------|------------|--------|
| **Tamás** | manuális műveletek, jóváhagyás, futtatás Mac Mini-n | terminál + Claude chat |
| **Chat (én)** | stratégia, elemzés, napi log review, task-írás, doc-írás | ez a chat |
| **CC** | kód implementáció, tesztek, commit, push | VSCode extension, MacBook |

**Alapelv:** Tamás **soha nem ír/módosít kódot manuálisan**. Ha kell valami, CC csinálja. A Mac Mini `git pull` Tamás felelőssége, de a hozzá szükséges task-ot **én írom**, CC implementálja.

---

## 2. Napi rutin (hétfő-péntek)

### Reggel ~10:00-10:30 CEST — ellenőrzés

**Tamás csinálja magának (nem kell velem):**

```bash
# Legutóbbi cron log
ls -lt ~/SSH-Services/ifds/logs/ | head -3
# Legutóbbi intraday log böngészés
tail -100 ~/SSH-Services/ifds/logs/cron_intraday_*.log | grep -E "Phase|ERROR|Positions:"
```

Ha **ERROR** van a logban → küldd el nekem. Ha nincs, nem szükséges.

### Este ~22:10-22:30 CEST — napi log review (fixed)

**Tamás csinálja velem:**

Új chat üzenet: "piaczárás után vagyunk, itt a logok". Én olvasom:
- `logs/pt_events_YYYY-MM-DD.jsonl` (napi P&L, exit típusok)
- `state/daily_metrics/YYYY-MM-DD.json` (score distribution, slippage, commission)
- Ha van: `logs/cron_intraday_YYYY-MM-DD_161500.log` (pipeline szintű detail)

Én írok napi review-t: `docs/review/YYYY-MM-DD-daily-review.md`

**Mit figyelek minden nap:**
1. **Kumulatív P&L** — trend javul vagy romlik
2. **Új UW adatok jönnek-e** — a Snapshot Enrichment után a `dp_volume_dollars` értéket ellenőrzöm
3. **Anomáliák** — leftover, phantom, API error, új hiba
4. **Score range** — a BC23 után 90-95 szűk tartomány, figyelem a kiugró eseteket

Ha **specifikus** anomáliát látok (pl. BC23 post-deploy: 0% TP1 hit rate 10 napig), **felvetem** a napi review végén.

---

## 3. Heti rutin (péntek)

### Péntek 22:00 CEST — heti metrika

**Tamás parancsa:**
```bash
cd ~/SSH-Services/ifds && .venv/bin/python scripts/analysis/weekly_metrics.py
```

Output: `docs/analysis/weekly/2026-WXX.md` + `.csv`

**Tamás elküldi nekem a markdown tartalmát.** Én kiértékelem:
- Weekly P&L trend vs baseline (BC23 előtti -$60/nap alap)
- Excess return vs SPY — **ez a kritikus metrika** (a nyerő hét lehet csak a piac)
- Score→P&L korreláció — a BC23 után ez volt r=-0.414, nézem hogy javul-e
- TP1 hit rate — a BC23 után 0%, most 1.25×ATR-rel remélem 5%+
- Commission ratio — 4% vagy alacsonyabb a gross-hoz képest

Heti review-t **ne írjak**, ha nincs új információ. Csak **ha valami változik** (GO/NO-GO pont, új trend).

### Pénteken utána — a hétvége dokumentáció

A pénteki heti metrika után, ha valami új: frissítjük a STATUS.md-t (én írom a diff-et, CC vagy Tamás commit-ol).

---

## 4. A Mac Mini → Chat kommunikáció

**Alapelv:** én nem látom a Mac Mini filesystem-jét közvetlenül. A MacBook-on keresztül a `/Users/safrtam/SSH-Services/` mount read-only nekem. Ami ott van, olvasom.

**A logok feldolgozása:**

| Amit Tamás csinál | Amit én kapok |
|-------------------|---------------|
| Pipeline log fut Mac Mini-n | Tamás néha elküldi a log részleteit |
| Daily metrics `state/daily_metrics/` szinkronizálódik SSH-n | Én olvasom a MacBook-on mount-olt state mappából |
| Phase 4 snapshot `state/phase4_snapshots/` szinkronizálódik | Olvasom |
| Heti metrika parancs fut → fájl keletkezik | Tamás elküldi **copy-paste**, vagy feltölti az új chat üzenetben |

**Amikor kell nekem konkrét fájl:** kérem Tamástól a Chat üzenetben. Nem próbálok SSH-t vagy bash-t csinálni.

---

## 5. A bekövetkező 2-3 hét — idővonal

### W17 — ápr 20 (hétfő) — ápr 24 (péntek)

| Nap | Mit figyelünk | Kinek a feladata |
|-----|---------------|------------------|
| Hétfő (ápr 20) | **Első futás az új UW Quick Wins + Snapshot Enrichment adatokkal.** Az új snapshot tartalmaz-e `dp_volume_dollars`, `venue_entropy`, `net_gex` mezőket | Tamás figyeli a logot, én olvasom a daily_metrics-et |
| Hétfő este | Napi review + **dp_volume_dollars ellenőrzés** — van-e valódi $ érték a snapshot-okban | Chat |
| Kedd-csütörtök | Rutin napi review-k | Chat |
| **Péntek (ápr 24)** | **W17 heti metrika** — a BC23 **második** hete | Tamás fut, Chat elemez |

**Amiket a W17 mutathat:**
- TP1 hit rate: 0/18 → 5%+ (a 1.25×ATR javít-e)
- Score→P&L korreláció: -0.414 → közeledik 0-hoz?
- Excess return vs SPY: ha a hét bearish, pozitív excess = edge

### W18 — ápr 27 (hétfő) — május 1 (péntek)

| Nap | Mit csinálunk |
|-----|---------------|
| **Hétfő** | **Dollár-alapú ticker liquidity audit v3** futtatása. Kb. 10 nap új snapshot = elég adat. Tamás fut, én elemzem |
| W18 közepe | **BC24 Phase 0 design** — a v3 audit alapján eldől, mi az **Institutional Relevance Filter** küszöbe. Ebből BC24 univerzum definíció |
| Péntek | W18 heti metrika + **BC23 kumulatív értékelés** 3 hét alapján |

**W18 végén kritikus döntés:** ha a BC23 mechanika működik (TP1 hit rate ≥5%, score korreláció ≥0), akkor a BC24 felé megyünk. Ha nem → **újabb finomhangolás** a BC23-on (scoring súlyok, dynamic threshold).

### W19 — május 4-8

| Nap | Mit csinálunk |
|-----|---------------|
| Elején | **BC24 Phase 1 indulás** — ha GO döntés van a W18 végén |
| Közepén | Új endpoint integrációk (Flow Alerts, Market Tide) — csak IFDS oldal |
| Vége | MID BC indulás, ha Tamás belefér (ez a **MID** projektre át van adva, lásd `/mid/docs/planning/BC-etf-xray-institutional-13f-layer.md`) |

### W20+ — május 11-

- **Paper Trading Day 63** (~május 14): **éles/paper folytatás döntés**
- BC24 Phase 2+ integrációk
- IFDS Phase 3 ← MID CAS integráció (`future-2026-04-17-bc-ifds-phase3-from-mid.md`)

---

## 6. Mire figyelj kifejezetten a hétfői első futás után (ápr 20)

**Ez a legfontosabb ellenőrzés.** Új mezők kerülnek a snapshot-ba, először.

### Tamás megnézi (10-15 perc):

```bash
# Van-e az új snapshot
ls -la ~/SSH-Services/ifds/state/phase4_snapshots/2026-04-20.json.gz

# Mezőellenőrzés
cd ~/SSH-Services/ifds
zcat state/phase4_snapshots/2026-04-20.json.gz | jq '.[0] | keys' | grep -E "dp_volume_dollars|venue_entropy|net_gex|call_wall|zero_gamma"
# Várt: mind az 5 mező szerepel

# Egy példa rekord értékei
zcat state/phase4_snapshots/2026-04-20.json.gz | jq '.[0] | {ticker, dp_volume_dollars, block_trade_dollars, venue_entropy, net_gex}'
# Várt: dp_volume_dollars > 0 a likvid ticker-eknél
```

### Ha valami nem stimmel:

| Hiba | Oka lehet | Megoldás |
|------|-----------|----------|
| Nincs új snapshot fájl | Pipeline nem futott (cron probléma) | `tail logs/cron_intraday_20260420*.log` |
| Új mezők mind 0 vagy None | A Phase 4 `_analyze_flow()` nem kapja meg az adatokat az adapterből | Chat vizsgálja: melyik lépés ejti el |
| dp_volume_dollars = 0 mindenhol | Batch prefetch nem gyűjti a `premium`-ot | Debug script az `_aggregate_dp_records()`-ben |
| net_gex None mindenhol | Phase 5 nem futott vagy nem írja be | Chat vizsgálja Phase 5 logot |

**Kérlek küldj nekem egy snapshot példát** kedden reggelre — az ápr 20-as első tickerét a jq outputtal. Ebből azonnal látom, hogy minden rendben van-e.

---

## 7. Dokumentáció frissítés rutin

### Amikor `docs/STATUS.md` elavul

Új BC-deploy vagy Day-változás esetén **én írok javaslatot**, Tamás/CC commit-olja:

```
[Chat] "Itt az új STATUS.md diff, menjen egy dedikált commitba"
[Tamás] átadja CC-nek: "docs: STATUS.md W17 update"
[CC] commit + push
```

### Amikor `docs/planning/backlog.md` elavul

Új BC definíció, vagy BC lezárása esetén — **én írok diff-et**, CC commit-olja.

### Amikor a chat projekt instructions (system prompt) elavul

**Ez a Claude.ai project setting**, amit csak Tamás módosít manuálisan a Settings-ben. Én javaslatot írok, Tamás **copy-paste**-olja.

Mikor kell frissíteni:
- Napszámok jelentősen változnak (Day 30 → Day 60)
- Új BC neve vagy dátuma
- A "Következő BC mérföldkövek" lista elavul

---

## 8. CC feladat-átadási szabályok

**Amikor CC-nek szól a dolog:**

1. Én **megírom** a task fájlt: `docs/tasks/YYYY-MM-DD-{rövid-cím}.md`
2. Formátumszabály (a meglévő task fájlok követik):
   - Status: OPEN
   - Updated: YYYY-MM-DD
   - Priority: P0/P1/P2/P3
   - Effort: ~Xh CC
   - Depends on: (másik task referencia)
3. Tamás megnyitja, **átnézi**, majd CC-nek átadja ("implementáld")
4. CC dolgozik, commit-ol, push-ol
5. CC visszaad: "Kész. `commit-hash` pusholva. N passing tests."

**A kritikus dolog:** a task fájl ELÉG részletes legyen, CC-nek ne kelljen visszakérdeznie. Ha mégis kell, **felveszem és bővítem** a task fájlt, nem rögtönzöm.

---

## 9. Mit NE csinálj a saját szakálladra

- **Ne commit-olj dokumentációt** saját kézzel anélkül, hogy előbb nálam lett volna — a STATUS.md és a backlog.md két "source of truth", ezeket szinkronban kell tartani
- **Ne futtass analízis scriptet, aminek az outputja nem érkezik vissza nálam** — ha nekem nem kerül elém, a következtetéseket elveszítjük
- **Ne változtass paramétert (defaults.py, crontab)** CC nélkül — még ha triviális is, a teszt futtatás, validálás az ő felelőssége

---

## 10. Hetente egyszer — átolvasás

Javaslom, hogy **minden vasárnap délelőtt** 10-15 percet szánjál erre a fájlra + a legfrissebb STATUS.md-re + a backlog.md-re. Ha valami elavult → Chat üzenetben "frissítsünk" — én megcsinálom a diff-et.

Ha új BC nézete van, új stratégiai gondolat, új API ötlet — **ne gyűjtsd a fejedben**, dobd be egy chat üzenetbe, én eltárolom a megfelelő helyre (backlog, jövő BC, learnings-archive).

---

## Appendix A — Az én "napi check-list"-em

Amikor napi review-t írok, ezeket szoktam ellenőrizni:

- [ ] Kumulatív P&L változás (most: ~-$695)
- [ ] Napi win rate
- [ ] Excess return vs SPY
- [ ] TP1/SL/TRAIL/MOC arány (BC23 után: ~0/0/0/100% normális)
- [ ] Új ticker mezők valódi értékkel (hétfő ápr 20-tól)
- [ ] Anomáliák (leftover, phantom, API error)
- [ ] Score range és distribution
- [ ] Pipeline output (pass-ed tickers, sector VETO)

Ha valami nem világos — visszakérdezek tőled, nem ütőmbe.

---

## Appendix B — "Quick lookup" parancsok

Kedvenc parancsok a Mac Mini-n:

```bash
# Mai napi metrika
cat ~/SSH-Services/ifds/state/daily_metrics/$(date -v+0d +%Y-%m-%d).json | jq

# Az utolsó 3 napi P&L
for d in $(ls -t ~/SSH-Services/ifds/state/daily_metrics/ | head -3); do
  echo -n "$d: "
  cat ~/SSH-Services/ifds/state/daily_metrics/$d | jq -r '.pnl.net'
done

# Kumulatív P&L
cat ~/SSH-Services/ifds/scripts/paper_trading/logs/cumulative_pnl.json | jq '.cumulative_pnl'

# UW API hívás ellenőrzés (rate limit)
grep "unusual_whales" ~/SSH-Services/ifds/logs/cron_intraday_$(date +%Y%m%d)*.log | wc -l

# Utolsó commit
cd ~/SSH-Services/ifds && git log -3 --oneline

# Nyitott tesztek
cd ~/SSH-Services/ifds && .venv/bin/pytest --collect-only -q | tail -5
```

Ha ezek közül bármelyik output érdekes — küldd nekem.
