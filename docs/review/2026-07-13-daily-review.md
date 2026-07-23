# IFDS Daily Review — 2026-07-13 (hétfő, Day 38/63 NYSE-count)

## 1. Fejléc
- **Day 38/63** (NYSE-count) — `daily_metrics::day_number=38` + `review_data::nyse_trading=38` + `pt_eod` „[Day 38/63]" ✓ egyező. ⚠️ `trading_days=33` (`cumulative_pnl.json`) ≠ 38 — az 5 outage-napos gap változatlan (07-07 §6.2, Dev-chat invariáns-döntés még nyitva)
- **Realized net: $0,00** (0 exit) — `daily_metrics`; **cumulative +$228,69 (+0,229%)** változatlan (`cumulative_pnl.json` + `daily_metrics` egyező)
- **Net Liq: $100 986,81** — forrás: `state/daily_equity.json["2026-07-13"]`. ⚠️ **Forrás-eltérés**: ugyanez a fájl a 07-10-es záróra $101 043,78-at ad, míg a 07-10-es review a chat-oldali IBKR MCP-vel verifikált $101 049,37-et jelentett — **$5,59 eltérés két forrás között, mindkettő riportálva, fel nem oldva**. (IBKR MCP live lekérdezés ezen a session-ön már 07-14-es, USFD-t is tartalmazó élő állapotot ad — pre-open tiszta ablak retroaktívan nem elérhető a 07-13-as záróra, ezért nem használható kereszt-ellenőrzésre.)
- **Excess: +0,77 pp** (portfolio 0,00% vs SPY −0,77%) — `daily_metrics::excess_return` — ⚠️ szemantika-megjegyzés érvényben (07-10 §6.4: realized-alapú, nem mark-to-market; Day 126 kapu-input, Dev-chat döntésre vár)
- **Nyitott pozíciók: 5** (0 új entry) — IBKR + `swing_positions` + reconcile egyező
- **VIX: 17,13 (close, +13,97%)** — `daily_metrics`; (intraday 14:30 CEST: 16,41, `cron_intraday` — eltérő időpont, nem konfliktus)

## 2. Exits (0)
- Tervezett exit nem volt, nem is történt — `pending_exits/2026-07-13.json` nem létezik ✓ konzisztens (0-exites nap mintája szerint helyes)

## 3. Entries (0) — forrás: `pt_submit` 15:31, `pt_events`
- 3 qualifikált jelölt (PFGC 86,2 / FWONK 81,8 / SLGN 81,6 a top-3-ban) — PFGC/SLGN/BIRK mind **skip** ("already has position or swing state", race-guard) — már nyitott pozíciók. FWONK nem került kiválasztásra (nem meglévő, de a top-3-on kívül nem szerepel indoklás a submit logban). **Submitted: 0 tickers**, qualifying 24/85+ küszöb felett
- Nincs slippage-adatpont ma (0 fill)

## 4. Nyitott pozíciók (5) — forrás: `state/review_data/2026-07-13.json` (1a)
| Ticker | days_held (trading) | Mark | Unrealized | Stop-buffer % | next_action |
|---|---|---|---|---|---|
| ITT | 4 | n/a (forrás hiányzik) | n/a (forrás hiányzik) | n/a | HOLD |
| XPO | 4 | n/a (forrás hiányzik) | n/a (forrás hiányzik) | n/a | HOLD |
| PFGC | 3 | n/a (forrás hiányzik) | n/a (forrás hiányzik) | n/a | HOLD |
| BIRK | 3 | n/a (forrás hiányzik) | n/a (forrás hiányzik) | n/a | HOLD |
| SLGN | 1 | n/a (forrás hiányzik) | n/a (forrás hiányzik) | n/a | HOLD |
| **Total unrealized** | | | **n/a (forrás hiányzik)** | | |

- Per-ticker mark/unrealized egyik forrásban sem szerepel 07-13-ra (a `daily_metrics` nem tartalmaz nyitott-pozíció marköt, az IBKR MCP csak élő — jelenleg 07-14-es — pillanatképet ad). **Nem becsülhető** — anti-hallucinációs szabály szerint üresen hagyva.
- Notional: $25 553,44 (equity 25,55%); szektor-max 9,28% (Industrials); Consumer Cyclical 9,11% (BIRK+SLGN); Consumer Defensive 7,16% (PFGC)
- ITT/XPO days_held_trading=4 — **holnap (07-14) éri el az 5-ös time-stop küszöböt** (lásd §8)

## 5. Ops-checklist
- ✓ `pt_reconcile` 22:15:06 „Reconciliation OK", 5/5 ticker state≡IBKR (kumulatív számláló ezen review során nem újraszámolva)
- ✓ Teljes lánc normál időzítéssel: cron_intraday 14:30:00–14:31:25 (0 ERROR/WARNING), gateway health 15:25 OK, heartbeat submit 15:45 OK, submit 15:31 (0 új, 3 skip), 15:30 close „nothing to do", 21:40 close „nothing to do", monitor 22:00 (0 flag), daily_metrics 22:10, eod 22:11 (Day 38/63 ✓), reconcile 22:15
- ✓ Telegram-render (`pt_eod_2026-07-13.log`) egyezik a `daily_metrics`-szel (P&L $0,00, cumulative +$228,69/+0,23%, Day 38/63) — nincs eltérés
- ⚠️ **UW shadow forrás-eltérés (új, P3)**: `daily_metrics::uw_shadow_summary.tickers_logged = 24` (egyezik a Phase 5 cron-log "Analyzed: 24"-gyel), de `review_data(1a)::uw_shadow.tickers_logged = 3` — **két forrás, mindkettő riportálva**, fel nem oldva
- ✓ Ismert, változatlan: `BEALLITASOK` weights-display legacy (flow/funda/tech súlyok kiírása a swing PCR+OTM-inverse scoring mellett)

## 6. Anomáliák (új/változott/lezárt)
- **6.1 P3 ÚJ — Net Liq forrás-konfliktus**: `state/daily_equity.json["2026-07-10"]` = $101 043,78 vs a 07-10-es review chat-oldali IBKR-verifikált $101 049,37 — **$5,59 eltérés**, root cause ismeretlen (eltérő capture-időpont gyanú, `hipotézis:` ellenőrzés: a `daily_equity.json` írási időbélyege vs a chat IBKR-lekérdezés pontos időpontja). Nem befolyásolja a cumulative P&L-t (az realized-alapú, külön csatorna)
- **6.2 P3 ÚJ — UW shadow tickers_logged forrás-eltérés**: lásd §5. Feltételezett ok (`hipotézis:` ellenőrzés szükséges): a `review_data`(1a) más denominátort számol (pl. csak az új entry-jelöltekre szűkítve), mint a `daily_metrics::uw_shadow_summary` (teljes Phase 5 populáció)
- Ismert, változatlan: day-count gap 5 nap (§6.2 07-07); cumulative_drift −$282,66 reziduum (07-10 §6.1, statement-rekonsziliáció Tamásnál nyitva — ma nincs új adat, mert nincs mark-to-market forrás a reziduum újraszámolásához)

## 7. Megfigyelés-sorozatok (kumulatív, következtetés nélkül)
- **TP-hit / pozitív-exit**: változatlan (17/41; 23/41) — ma 0 exit
- **Next-day MKT fill (entry)**: változatlan (nincs új entry ma)
- **Re-entry család**: változatlan, n=2 (PFGC same-day, SLGN next-day)
- **Reziduum-sorozat**: 07-13-ra nem számolható újra (nincs mark-to-market forrás ehhez a naphoz) — utolsó ismert pont változatlanul +491 (07-10)
- **VIX**: 17,13 close (+13,97%) — emelkedő nap a 07-10-es 15,02 után

## 8. Holnap (07-14, kedd)
- **Várt**: ITT/XPO days_held_trading 4→5, eléri az 5 napos time-stop küszöböt — TIME_STOP flag várható a 22:00 EOD eval-nál, végrehajtás a következő close-ablakban. **Kontaminált-jelölt** (07-07 §6.4: az ITT/XPO 21:02 CEST-es entry-fill miatt) — a tp1_hit=false sorozat kezelése ennek fényében értékelendő, jel-ítélet nélkül
- PFGC stop-buffer követése folytatódik (utolsó ismert érték +3,0%, 07-10) — 07-13-ra nem frissíthető (nincs mark-forrás)
- Fókuszlista (max 5): (1) ITT/XPO TIME_STOP kontaminált-jelöltként kezelése; (2) Net Liq forrás-konfliktus tisztázása (§6.1); (3) UW shadow tickers_logged eltérés tisztázása (§6.2); (4) statement-rekonsziliáció státusza (Tamás, nyitott); (5) trading_days↔day_number invariáns-döntés (Dev-chat, nyitott)

## 9. Freeze-sor
Paraméter-érintő változás ma: **nincs**.

## 10. A nap egy mondatban
Csendes nulla-exit hétfő: 5 nyitott pozíció változatlan, 3 új jelölt (PFGC/SLGN/BIRK) meglévő pozícióval ütközve skip-elve, a lánc hibátlanul futott — az ITT/XPO time-stop holnapra esedékes, kontaminált-jelöltként kezelendő.
