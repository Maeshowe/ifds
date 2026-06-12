# Handoff — IFDS, 2026-06-12 (swing pivot Day ~18-19)

Átadó dok a következő CC sessionnek. Másold be a friss `/continue` után.

---

## Élő státusz

- **Cumulative realized: +$1,735.02** (broker-authoritatív tracked, Mac Mini). A Day 18
  (6/11) mega exit-nap (VNO TP2 + társai) átlépte az $1,000-et, sőt felül.
- **Tesztek: 1953 (MacBook) / 1954 (Mac Mini, +Gate A)**, 0 failure, 0 warning.
- **Utolsó commit: `1abe3f0`** (push `..1abe3f0`). MacBook = Mac Mini = origin/master szinkronban
  (Mac Mini HEAD `ab689e5`-ön a Day 19 deploy után — a 2 záró docs-commit (`f8f5002`, `1abe3f0`)
  is felmehet pull-lal, de csak docs).
- **Élő trading érintetlen.** Nyitott pozíciók közt **2 új belépő ma (6/11)**: NSA (entry_score
  100.71), JAZZ (87.44) — ők már hordozzák az S_j-t.
- SSH: `ssh ifds-mini`.

## Mit végeztünk ebben a (több napos) sessionben

### Data-quality + execution fix-ek (mind DEPLOYOLVA + élesben verifikálva)
- **Data-quality fix-package #1-#6** (VIX→Polygon I:VIX, EOD timing, NYSE day-count, commission,
  weekly slippage, portfolio_return) — DONE, archiválva.
- **~$218 cumulative_drift FELOLDVA** — baseline-reset artifact (pre-pivot carry +$208.37 +
  accrued), `BASELINE_OFFSET_USD` a cross-checkbe. Nulla tracking-hiba.
- **1c autonóm review-pipeline** — `generate_review.py --ibkr-json` + `/daily-review` command.
- **daily-metrics-execution-fix #1/#2** (IBKR-fill slippage + trades.details MOC merge) — DONE,
  Day 17 élesben verifikálva, archiválva. Backfill (TKR/NSA) alkalmazva.
- **Task-index szűrőbug fix (B+A)**: `^Status:` horgony + DONE/REJECTED taskok `docs/tasks/archive/`-ba.

### Edge-audit + jel-izoláló attribúció (a session fő stratégiai vonala)
- A **`docs/foundational/strategic-review/2026-06-10-edge-audit.md`** (Chat, v1.2) a Day 63/126
  kiértékelés rögzített referenciája. **⚠️ Ez a fájl jelenleg UNTRACKED** — Chat commitolja
  (a `2026-05-22-bridgewater-janestreet-research.md` is). CC erre épített.
- **Jel-izoláló attribúciós spec** (`docs/foundational/strategic-review/2026-06-10-signal-isolating-attribution-spec.md`):
  L0/L1/L2 izoláció, **elsődleges döntési metrika = L2 Spearman, h=5, szektor-relatív**;
  §8 öt fegyelem-pont. A commit = pre-regisztrációs zár (az adat ELŐTT rögzítve).
- **`scripts/analysis/signal_attribution.py`** — tesztelt analízis-eszköz (numpy stats, scipy
  nélkül; L0/L1/L2 + Fisher-z CI + kvintilis + S_j-snapshot-recovery). +13 unit-teszt mock adaton.
  **Data-loader bekötése (ledger+snapshot+Polygon) Day 63 ELŐTT a hátralévő munka** (lásd lent).
- **S_j (entry_score) capture DEPLOYOLVA + verifikálva** (Day 19 reggel, a Day 18 mega exit-nap
  UTÁN, edge-audit §6): SwingPosition.entry_score mező + submit/close/pending_exits perzisztálás.
  **#1**: új belépők valós S_j-t rögzítenek (NSA 100.71, JAZZ 87.44). **#2**: a ledger hordozza
  az entry_score mezőt (0.0 a pre-deploy exitekre — helyes). Gate A (backward-compat) + Gate B
  (04-risks §11 freeze-amendment log) kész.

## NYITOTT TASK (1 db)

- **`docs/tasks/2026-06-10-eod-telegram-persisted-details.md`** (OPEN, P2) — az eod_report 22:11
  Telegram `Trades:` száma a clientId-12 saját fill-jeiből épül (cross-client MOC-ot nem látja;
  Day 17: `Trades: 1` vs valós 2). Fix: az eod a **már megírt** `daily_metrics/{date}.json`
  `trades.details`-ét olvassa. **Freeze-safe** (display-fix, edge-audit §4.2/1 engedi). ~1h.

## A KÖVETKEZŐ LÉPÉSEK (prioritás szerint)

1. **eod-telegram-persisted-details** (P2, freeze-safe) — az egyetlen nyitott task. Mehet bármikor.
2. **signal_attribution.py data-loader** (Day 63 ELŐTT, nem sürgős) — a ledger (entry_score, sector,
   exit_type) + Phase 4 snapshot (S_j fallback) + Polygon bars (forward return + szektor-ETF + SPY)
   bekötése a `main()`-be. A pure-computation mag már tesztelt; ez I/O-glue.
3. **Day 21 checkpoint** (~6/16): a −$1,500 küszöb — jelenleg ~$3,200 bufferben (cum +1,735).
   Plus az edge-audit §4.2/7 **halott-feed adatköltség-audit** (Day 21, ~6/14).
4. **Parameter freeze érvényben Day 63-ig** (edge-audit §4.2/1): csak bugfix + display/tracking-fix.
   Minden ilyen a `04-risks §11`-be logolva. Jel/scoring/sizing/exit változás TILOS.

## Kritikus kontextus / gotchák

- **Freeze**: Day 18 → Day 63 (~aug) paraméter-fagyasztás. Display/tracking-fix OK (logolva §11),
  trading-viselkedés NEM.
- **S_j Day 63-ra biztosított**: a Phase 4 snapshotok épek (recovery működik) ÉS a live capture
  rögzít — belt-and-suspenders. A non-zero end-to-end (ledgerben) majd amikor NSA/JAZZ kilép.
- **Attribúció elsődleges metrika = L2 Spearman h=5 szektor-relatív** (NEM L0/realized — az
  confound-olja az exit-réteget a jellel). Day 63 csak IRÁNY, Day 126 az első érdemi olvasat.
- **MID**: külön projekt = az adatforrás/API; a mathtech egy másik fogyasztó. A (b)-ág routing a
  MID API-t fogyasztaná (függőség: API stabilitás).
- **CC edit-stratégia** (új ifds-rule): kis egyenkénti `Edit`-ek a nagy multi-edit payload helyett
  (a szerkesztő-connector fagy nagy payloadnál).
- **Push policy**: CC commitol, Tamás jóváhagyja a push-t/deploy-t. Live trading-path változás
  (submit/close) Mac Mini deploy + Tamás-jóváhagyás + nappali, felügyelt deploy (NEM nagy nap előtt).

## Files / parancsok
- Tesztek: `IFDS_TELEGRAM_BOT_TOKEN= IFDS_TELEGRAM_CHAT_ID= python -m pytest tests/ -q` (baseline 1953)
- Nyitott taskok: `grep -lE "^Status:[[:space:]]*(OPEN|WIP)" docs/tasks/*.md`
- Attribúció (Day 63): `python scripts/analysis/signal_attribution.py --as-of YYYY-MM-DD` (data-loader után)
