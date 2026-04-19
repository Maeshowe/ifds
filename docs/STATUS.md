# IFDS — Current Status
<!-- Frissíti: CC (/wrap-up), Chat (session végén) -->
<!-- Utolsó frissítés: 2026-04-17 Budapest, Chat -->

## Paper Trading
Day 45/63 | cum. PnL: **−$694.53 (−0.69%)** | IBKR DUH118657
**BC23 Scoring & Exit Redesign — első teljes hét (W16) DONE**
Heti bontás: W16 +$1,721 (+1.72% gross), de SPY +4.45% → excess -2.73%

## BC23 első hét (W16, ápr 13-17)

| Nap | Napi P&L | Win rate | Excess vs SPY |
|-----|---------|----------|---------------|
| ápr 13 (hétfő) | +$390 | 3/3 | -0.59% |
| ápr 14 (kedd) | +$191 | 2/3 | -1.03% |
| ápr 15 (szerda) | +$600 | 2/3 | -0.19% |
| ápr 16 (csütörtök) | +$577 | 4/4 | +0.33% (**első pozitív**) |
| ápr 17 (péntek) | -$37 | 2/4 | -1.25% (flat nap) |
| **W16 összesen** | **+$1,721** | **13/17 (76%)** | **-2.73%** |

**Kritikus jelek W16-ban:**
- TP1 hit rate: **0/18** (0%) — 1.5×ATR túl magas volt
- Score→P&L korreláció: **r = -0.414** (negatív, scoring edge még nem bizonyított)
- Abszolút P&L jó, de nagy része a bullish piacból jött, nem a ticker selection-ből

## W17 follow-up (2026-04-17 CC DONE, hétfőn élesedik)

| # | Változás | Fájl / commit |
|---|----------|---------------|
| 1 | TP1 1.5×ATR → **1.25×ATR** | `config/defaults.py` |
| 2 | `scoring_validation.py` rerun BC23 adatokon | `docs/analysis/scoring-validation-bc23-w16.md` |
| 3 | Flow component decomposition (232 trade) | `docs/analysis/flow-decomposition.md` |

**Flow findings (232 enriched trade, teljes history):**
- `pcr_score`: **+0.203** ** (p=0.002) — legerősebb pozitív prediktor
- `otm_score`: **−0.194** ** (p=0.003) — szignifikáns NEGATÍV (fordított jel)
- `rvol_score`: +0.147 * (p=0.026) — mérsékelt pozitív
- `dp_pct_score`: mindig 0 → **UW Quick Wins orvosolja** (lásd alább)
- `block_trade_score`, `buy_pressure_score`, `squat_bar_bonus`: zaj

## UW Client Quick Wins + Phase 4 Snapshot Enrichment (2026-04-17)

**Commits:** `533763b` (QW) + `97fbeda` (Snapshot Enrichment)

Három kritikus probléma egyszerre orvosolva a UW adapter rétegben:
1. `UW-CLIENT-API-ID: 100001` header hozzáadva (skill.md szerint kötelező)
2. `limit=200` → **500** a `/api/darkpool/{ticker}` hívásnál
3. `premium` mező aggregálása → `dp_volume_dollars`, `block_trade_dollars`

**Verifikáció (10 top liquid ticker):**
| Metrika | OLD | NEW | Δ |
|---------|-----|-----|---|
| DP trade count | 2000 | 5000 | +150% |
| DP $ forgalom | $5.5B | **$10.1B** | +84% |
| prem-coverage | 100% | 100% | nincs változás (mindig is volt) |
| NVDA egyedül | $118M | **$1.22B** | 10× |

**Snapshot Enrichment** (a Phase 4+5 mezők perzisztálódnak):
- Flow új mezők: `dp_volume_shares`, `total_volume`, `dp_volume_dollars`, `block_trade_dollars`, `venue_entropy`
- GEX új mezők (Phase 5 outputból): `net_gex`, `call_wall`, `put_wall`, `zero_gamma`

**Backward compat tesztelve:** 43 régi snapshot változatlanul olvasható, új mezők default értékkel (0 / None). BC20 Mód 2 re-score érintetlen.

## Élesben futó feature-ök

- Pipeline Split: Phase 1-3 (22:00 CEST) + Phase 4-6 (**16:15** CEST)
- MKT entry + VWAP guard (csak REJECT >2%)
- Swing Management: 5 napos hold, TP1 50% partial, TRAIL, breakeven SL, D+5 MOC
- Dynamic positions: **max 5**, score threshold 85
- **UW Client v2**: kötelező header, limit 500, premium aggregálás, dollár-alapú DP
- **Snapshot v2**: dollár + GEX mezők minden új snapshotban (**hétfőtől éles**)
- Cross-Asset Regime + Korrelációs Guard + Portfolio VaR 3%
- Company Intel: 16:15 submit után (friss tickerekre)
- EWMA simítás, M_target penalty, BMI momentum guard

## Shadow mode

| Feature | Shadow óta | Élesítés |
|---|---|---|
| Crowdedness composite | 2026-03-23 | TBD |
| Skip Day Shadow Guard | 2026-04-02 | Kiértékelés ~máj 2 |

## Következő (W17: ápr 20-24)

- **Hétfő (ápr 20):** első futás új adatokkal — **snapshot ellenőrzés kritikus** (új mezők jelen vannak-e, dollár értékekkel)
- Hétfő-péntek: napi review-k
- **Péntek (ápr 24):** W17 heti metrika → **BC23 2 hetes értékelés**

**W18 (ápr 27-):** dollár-alapú `ticker_liquidity_audit_v3` → BC24 ticker univerzum alap

## Tervezett BC-k (frissítve 2026-04-17)

- **BC24 Institutional Flow Intelligence** (~W19-W22, máj 4-29) — UW új endpoints integráció, dollar-weighted scoring — design: `docs/analysis/uw-api-inventory-v2.md`
- **BC25 IFDS Phase 3 ← MID CAS** (~W21+) — `docs/tasks/future-2026-04-17-bc-ifds-phase3-from-mid.md` (várakozik MID-re)
- **MID BC ETF X-Ray 13F Layer** (MID projekten belül, külön ütemezés) — `/mid/docs/planning/BC-etf-xray-institutional-13f-layer.md`
- **Paper Trading Day 63** (~máj 14): **éles/paper folytatás döntés**

## Tesztek

**1352 passing**, 0 failure

## Utolsó commitok

- `97fbeda` — feat(models+snapshot): enrich snapshots with dollar-weighted flow + GEX
- `533763b` — fix(uw-client): add required header, increase limit, aggregate premium
- `0b905e6` — BC23 Scoring & Exit Redesign deploy (2026-04-13)
- `1bffb57` — fix(cleanup): nuke.py log_path, FRED optional, phantom date guard

## Blokkolók

nincs
