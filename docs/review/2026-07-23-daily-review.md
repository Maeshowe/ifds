# IFDS Daily Review — 2026-07-23 (csütörtök, Day 46/63 NYSE-count)

> Executor: **CC** (Fázis A, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett;
> IBKR MCP kereszt-ellenőrzés lefutott. Day 63 előtt nincs jel-ítélet.
> **Kontextus:** 07-22 teljes **outage-nap** (Mini FileVault-zárolás áramszünet után — lásd §6). A mai a
> helyreállás utáni első kereskedési nap.

## 1. Fejléc
- **Day 46/63** (NYSE-count) — `daily_metrics::day_number=46`. ⚠️ `cumulative_trading_days=39` (gap: outage-napok).
- **Realized net: −$531,32** (1 exit, komm. $1,12) — `cumulative_pnl` 07-23 sor. **Cumulative: −$423,70 (−0,424%)** — a pivot (05-18) óta **először negatív** a kumulatív.
- **Net Liq: $100 232,18** — IBKR `get_account_summary` ≡ `daily_equity` ✓; napi Δ a 07-21-es $100 364,55-höz mérve −$132,37 (a 07-22 outage-gapet fedi, nem egynapos).
- **Excess: +0,70%** — `daily_metrics::excess_return` (portfolio −0,53% vs SPY **−1,23%**). Risk-off nap (VIX 19,34, +16,23%), a könyv felülteljesített.
- **Nyitott pozíciók: 5** (`swing_positions` ≡ IBKR 5 ✓): GTES, JAZZ, PFGC, EQH, USFD (utóbbi ma újra belépve).

## 2. Exits (1) — típus: `pending_exits`; P&L: IBKR `get_account_trades` (broker)
| Idő (CEST) | Ticker | Típus | Qty | Entry(IBKR)→Exit | Broker realized | 07-21 §8 várt | Eltérés |
|---|---|---|---|---|---|---|---|
| 15:30 | USFD | MENTAL_SL | 56 | 102,60 → 93,13 | **−$531,32** | ~−$440 | **−$91** |

Az USFD-t a 07-21-i eod_eval flagelte (mark akkor 94,75); a végrehajtás 07-22-re volt ütemezve, de az
**outage-zárolás miatt 2 nap késéssel, ma 93,13-on** teljesült — a papír a késés alatt tovább esett
(→ a −$91 többletveszteség a becsléshez képest, §6). **3. dokumentált outage-késleltetett exit** (ITT/XPO, PFGC/BIRK után).

## 3. Entries (1) — `pt_events` 15:31 + `daily_metrics::execution`
| Ticker | Szektor | Qty | Planned→Fill | Slippage | Stop / TP1 / TP2 |
|---|---|---|---|---|---|
| USFD | Consumer Defensive | 56 | 96,06 → **94,24** | **−1,89%** (kedvező) | 89,85 / 100,71 / 105,37 |

⚠️ **Ugyanaz a név, ugyanaznap kilépve (15:30) ÉS visszavéve (15:31)** — self-reentry, lásd §6. A fill 94,24 a
tervezett 96,06 alatt (kedvező, −1,89%) — a slippage-sorozat első erősen kedvező printje.

## 4. Nyitott pozíciók (5) — `swing_positions` + IBKR `get_account_positions`
| Ticker | days_held | Mark | Unrealized | Stop-buffer | next_action |
|---|---|---|---|---|---|
| GTES | 4 | 27,25 | +$109,58 | 7,71% | HOLD |
| JAZZ | 3 | 250,90 | +$19,70 | 7,19% | HOLD |
| PFGC | 2 | 109,52 | −$55,00 | 5,49% | HOLD |
| EQH | 2 | 48,00 | −$71,30 | 5,56% | HOLD |
| USFD | 0 | 94,78 | +$29,24 | 5,20% | HOLD (re-entry) |

**Total unrealized: +$32,22** (IBKR). Gross position value $29 050,39; entry-bázisú notional **28,92% equity**;
nincs holnapra ütemezett exit-flag.

## 5. Ops-checklist
- ✓ **Reconcile 5/5 silent OK** — `pt_events` 22:15 `reconcile::no_divergence`.
- ✓ **Cron-lánc helyreállt** a 07-22 outage után: 14:30 intraday, 15:30 close (USFD MENTAL_SL), 15:31 submit (USFD re-entry), 22:00 eod_eval, 22:10 metrics, 22:20 review_data.
- ✓ **IBKR verifikáció**: NetLiq penny-egyezés; pozíció 5/5; a 2 mai USFD-láb (SELL 93,13 / BUY 94,24) verifikálva; a napi trades KIZÁRÓLAG USFD (nincs valós AAPL/teszt-order — lásd §6).
- 🔴 **`pt_events_2026-07-23.jsonl` SZENNYEZETT** — 176 legacy/teszt-esemény (§6/P1). A hiteles P&L-lánc (`pending_exits`→`daily_metrics`→`cumulative`) **NEM érintett**.

## 6. Anomáliák (új/változott/lezárt)
- **🔴 P1 (ÚJ) — production `pt_events` log-szennyezés teszt-futásból (test-env-hygiene, 3. előfordulás).**
  A `pt_events_2026-07-23.jsonl`-be **176 legacy esemény** íródott **16:34-16:51 CEST** között (a normál cronok
  UTÁN): `circuit_breaker cum_pnl=-6000`, `moc_submitted`, `trail_activated`, tickerek **AAA/BBB/CCC** (teszt-fixture
  nevek) + AAPL/LION/SDRL. Diagnózis: egy **pytest-futás** a Mini-n, ahol az event-logger (`evt.log`) nem volt
  mockolva — a swing-pivot óta halott legacy kódutak (circuit_breaker, AVWAP-trail) írták a valós logot.
  **Hatás: a hiteles P&L-lánc érintetlen** (IBKR trades ma csak USFD → nem adott be valós order), DE a `pt_events`
  a **v6 §5 ops-forrás ÉS az FRL loader rank-2 forrása** (spec §4.1) — az FRL éles indulásakor ez a szennyezés
  megismételné a dp_pct/AAPL-mock hibaosztályt. Ugyanaz az osztály, mint a `save_phase4_snapshot` (04-15) és a
  `write_shadow_snapshot` (05-19) — a szabály zártnak hitt, ez a 3. rés. **Gazda: CC-task** (az érintett tesztek
  event-logger-mockja; freeze-safe, teszt-only). Forrás: `logs/pt_events_2026-07-23.jsonl`.
- **P2 (n=2) — USFD self-reentry, ugyanaznapi stop↔belépő ellentmondás.** A MENTAL_SL 15:30-kor kiléptette
  (93,13), a belépő-jel 15:31-kor visszavette (94,24) — **$1,11/részvény magasabban, 26 mp-cel később** ≈
  −$62 + 2 komisszió ≈ **−$64 súrlódás**. A PFGC (07-21, max_hold) után a 2. self-reentry, de karakterében
  élesebb: itt a **stop-loss és a belépő-jel közvetlenül ellentmond egymásnak ugyanazon a napon**. Gazda:
  Day 63-input (stratégia-logika). Forrás: `pt_events`/`get_account_trades` 07-23.
- **P2 — 07-22 outage gyökérok: FileVault.** A Mini 07-22 09:30-kor bootolt, de **26 órán át a FileVault
  feloldó-képernyőn állt** (tailscaled `runs=1`, 07-23 11:58-i indulás = a feloldás pillanata); `fdesetup status`
  = On. A titkosított köteten a boot-idejű daemonok (sshd, tailscaled, cron) feloldás előtt nem indulnak → minden
  áramesemény kézi belépést igényel. Az UPS önmagában csak ritkítja, nem szünteti meg. Gazda: Tamás-döntés
  (FileVault OFF + auto power-on + auto-login). Referencia: [[mac-mini-connectivity]].

## 7. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **Next-day MKT fill slippage** — **n=5**: GTES −1,00% (07-17), JAZZ +1,00% (07-20), PFGC +1,01% / EQH +0,95% (07-21), **USFD −1,89% (07-23, első erősen KEDVEZŐ)**. |slippage| medián ≈ 1,00% (≈100 bp), előjel-vegyes. *(FRL `cost_model.json` input.)*
- **Self-reentry** — **n=2**: PFGC (07-21, max_hold), USFD (07-23, mental_sl↔belépő). Mindkettő nyitva; ROI-zárás még nincs.
- **Major risk-off excess** — ma **hozzáadva** (SPY −1,23% < küszöb): portfolio −0,53%, excess **+0,70%**. A könyv risk-off napon eddig konzisztensen felülteljesített (a sorozat n-je a vezetésből aktualizálandó).
- **TP-hit / pozitív-exit**: ma 1 exit, **0 pozitív** (USFD MENTAL_SL −$531).
- **Outage-késleltetett exit** — **n=3** (ITT/XPO 07-15, PFGC/BIRK 07-20, USFD 07-23): mindhárom a szándékolt időpontnál rosszabbul zárt; USFD-nél ~−$91 a becsléshez képest.

## 8. Holnap (péntek, 07-24) — várt + feltevés
- **Nincs ütemezett exit-flag** (`next_day_planned` üres) — hacsak a péntek eval új flaget nem tesz.
- **Péntek → heti zárás blokk** (W30) a napi review után.
- **Fókuszlista**: (1) a `pt_events` szennyezés CC-task nyitása (test-env-hygiene fix); (2) USFD self-reentry követése (day 1, +$29 unreal); (3) cumulative negatívba fordult (−$423,70) — irány-érzékeny; (4) FileVault-döntés (outage-ismétlődés megszüntetése); (5) slippage-sorozat n=5 → FRL cost-model.

## 9. Freeze-sor
**Paraméter-érintő változás ma: nincs.** A §6/P1 fix (teszt event-logger-mock) freeze-safe (teszt-only), külön CC-taskban. Freeze él Day 63-ig.

## 10. A nap egy mondatban
Risk-off nap (SPY −1,23%), az egyetlen esemény az USFD 2 nap késve, outage-terhelten végrehajtott mental-stopja (−$531,32, a kumulatív először negatív), amit 26 másodperccel később ugyanannak a névnek a visszavétele követett; a `pt_events` logot egy teszt-futás 176 legacy eseménnyel szennyezte (hiteles lánc érintetlen).
