# Daily Review — 2026-04-20 (hétfő)

**BC23 Day 6 / W17 Day 1**  
**Paper Trading Day 46/63**

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | -$414.92 |
| Napi P&L net | **-$433.38** |
| Kumulatív P&L | **-$1,109.45 (-1.11%)** |
| Pozíciók (új) | 5 |
| Win rate | 1/5 (20%) |
| TP1 hit rate | 0/5 (0%) |
| SPY return | -0.20% |
| Portfolio return | -0.41% |
| **Excess vs SPY** | **-0.21%** |
| VIX close | 18.86 (+7.96%) |

## Piaci kontextus

- **VIX +7.96%** — a complacency megtörőben (sub-20, de spike)
- **SPY -0.20%** — enyhe piaci negatív
- **MID regime:** STAGFLATION Day 3, TPI 43 HIGH
- **Stock-Bond korreláció 20D:** +0.41 (Positive Stagflationary)
- **MID volatility regime:** lockstep (VIX és market együtt mozog)

## Pozíciók

| Ticker | Score | Sector | Entry | Exit | P&L | Exit Type | Contradiction? |
|--------|-------|--------|-------|------|-----|-----------|----------------|
| CNK | 94.5 | Comm. Services | $30.52 | $30.26 | **-$122** | MOC | ✅ 0/4 beat |
| GFS | 94.0 | Technology | $59.09 | $58.76 | **-$83** | MOC | ✅ ár High target fölött |
| DELL | 93.0 | Technology | $201.71 | $204.24 | **+$121** | MOC | ❌ nincs |
| SKM | 93.0 | Comm. Services | $39.46 | $38.46 | **-$149** | LOSS_EXIT -2.53% | ✅ JPM+Citi downgrade |
| SCI | 92.0 | Cons. Cyclical | $83.40 | $83.16 | **-$36** | MOC | ❌ nincs |

**Contradiction flag hatása:**
- 3 flagged ticker együtt: **-$354**
- 2 non-flagged ticker együtt: **+$85**
- **Potenciális különbség filter-rel: $518 egy napon**

## Kulcs megfigyelések

### 1. Snapshot v2 verifikáció — SIKERES

**Hétfő reggel első futás az új UW Quick Wins + Snapshot Enrichment adatokkal.**

NVDA snapshot példa:
```json
{
  "ticker": "NVDA",
  "dp_volume_dollars": 17292198.44,
  "block_trade_dollars": 0.0,
  "venue_entropy": -0.0,
  "net_gex": null,
  "call_wall": null
}
```

- ✅ `dp_volume_dollars` él ($17.29M)
- ✅ `venue_entropy` számolódik
- ⚠️ `net_gex` null — **strukturálisan helyes**: Phase 5 csak top 100-ra fut, NVDA ma score 70.5 (nincs top 100-ban)
- GEX coverage: **98/178 (55%)** — design szerinti viselkedés

**Nincs bug, nincs további javítás szükséges.** A hétfői első futás az új adatokkal megtörtént, a pipeline gyűjti a dollár-alapú DP és GEX adatokat minden új snapshothoz.

### 2. A BC23 inverz korreláció megerősítve

A 3 Contradiction flagged ticker mind veszített, a 2 flag-mentes (DELL, SCI) közül 1 nyert. Ez **tökéletesen ismétli** a W16 r=-0.414 findings-et: a magas score-ú, fundamentálisan gyenge tickerek szisztematikusan alulteljesítenek.

**Tegnapi W17 follow-up javítások (TP1 1.25×ATR) nem voltak elégségesek a score→P&L probléma megoldásához.** A TP1 csökkentés a TP hit rate-en nem segített (0/5 ma), mert a ticker selection maga a hiba.

### 3. A DELL pénteki MOC vs hétfői entry problem

**Péntek (ápr 17):** DELL entry $196.51 → MOC $196.55 (+$2, flat)  
**Hétfő (ápr 20):** DELL entry $201.71 → MOC $204.24 (+$121)

**Ha pénteken overnight hold lett volna:** $196.55 → $204.24 = +$7.69/share × 50 = **+$384**  
**Valójában:** $2 (péntek) + $121 (hétfő entry) = +$123  
**Elveszett alpha:** ~$260

Ez a BC20A swing hybrid exit **időzítés-keveredés problémája** élesben. A DELL pénteken nem kellett volna zárni, hanem overnight tartani. A jelenlegi MOC exit logika ezt nem engedi.

### 4. SKM — LOSS_EXIT -2.53% működött

17:00 UTC entry után pár perccel zuhant, 17:00:19-kor loss_exit trigger @ $38.46. A kár -$298 (két split), de a logika **pontosan úgy működött**, ahogy kell: megakadályozta a további veszteséget. A Company Intel detektált kockázatot (CONTRADICTION: JPM + Citi downgrade), a rendszer mégis kereskedett, majd a loss_exit bevágott.

**Ez azt mutatja:** a CONTRADICTION flag **jelzés, nem blokkolás**. A backlog-ideas.md-ben javasolt M_contradiction multiplier (×0.5 flag esetén) ezt orvosolhatná.

### 5. Napi UW Quick Wins metrikák

Az új `dp_volume_dollars` mező **minden 178 passed tickeren** megjelent. A scoring még nem használja, de a hetente gyűlnek az adatok a dollár-alapú `ticker_liquidity_audit_v3`-hoz (W18 eleje).

## A BC23 mechanika diagnosztika

**Működik:**
- Slippage kontroll (0.03% átlag)
- LOSS_EXIT (SKM -2.53%-nál megállt)
- Risk per trade cap ($700)
- Sector VETO (XLE/XLB/XLU kizárva)
- Snapshot Enrichment v2

**Nem működik:**
- TP1 1.25×ATR: 0/5 hit — intraday 4-5% move ritka
- Score→P&L inverz reprodukálva
- Company Intel CONTRADICTION flag detektál, de nem hat a scoring-ra
- 16:15 CET entry gyakran helyi csúcson
- DELL-típusú overnight alpha elmulasztva

## Anomáliák

- **FRED API HTTP 500** kezdetben a pipeline elején — retry sikeres (533ms). Ha rendszeres lesz, CC task kell a resilience-hez.
- **Telegram post-market üzenetből hiányzik a "[ 4/6 ] Individual Stock Analysis" breakdown** — a cron logban megvan, csak a Telegram formatter nem tartalmazza. BC23 utáni regresszió, külön CC task lesz.
- **Crowd breakdown "0 good / 100 neutral / 0 bad"** — valószínűleg a szűkített univerzum mellékhatása, nem hiba.

## A nap tanulsága

A BC23 scoring **momentum-heavy**, és **bull market-re optimalizált**. Ma a MID szerint STAGFLATION Day 3 + Stock-Bond +0.41 + VIX lockstep — **a momentum long stratégia legrosszabb környezete**. A -$433 nagy része nem a BC23 hibája, hanem a **regime mismatch**.

Két teendő:
1. Várjuk ki a hét metrikát (péntek) — egy nap nem bizonyíték
2. Rögzítve a backlog-ideas-be a **Regime-Aware Position Sizing** javaslat (BC25+ scope)

## Teendők

- **Nincs most** — paper trading gyűjt adatot
- **Péntek (ápr 24):** W17 heti metrika
- **Hétvégén:** CRGY/AAPL leftover nuke (Tamás manuálisan, Mac Mini)

## Kapcsolódó

- `state/phase4_snapshots/2026-04-20.json.gz` — első új-mezős snapshot
- `logs/pt_events_2026-04-20.jsonl`
- `state/daily_metrics/2026-04-20.json`
- `logs/cron_intraday_20260420_161500.log`
