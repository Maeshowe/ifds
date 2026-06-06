Autonóm napi P&L review generálás (1a → IBKR cross-check → 1c draft → LLM-narratíva).

A Chat-oldali manuális napi review kiváltása. CC futtatja end-to-end; csak a
stratégiai ítéletet (P0 flag) eszkalálja a Chat-nek.

**ARGUMENTS**: a review dátuma `YYYY-MM-DD` (default: tegnap, ha nincs megadva).

> **Előfeltétel**: az IBKR MCP connector elérhető (CC-ből). A cron `ib_insync`-je
> NEM éri el a connectort — ezért a snapshot-lekérés CC-oldali kézi lépés.

## 1. fázis — 1a determinisztikus aggregátum

```bash
python scripts/paper_trading/generate_review_data.py --date {date}
```
→ `state/review_data/{date}.json` (P&L, pozíciók, exits, flag-ek, UW shadow).
Ellenőrizd a kimenetet (a `pnl.cumulative`, `positions.detail`, `flags` mezőket).

## 2. fázis — IBKR snapshot a connectorból (CC hívja az MCP-t)

Hívd a connector tool-okat és állítsd össze a snapshot dict-et:
- `get_account_summary` → `net_liq` (`net_liquidation`)
- `get_account_positions` → `position_tickers` (a `contract_description`-ök),
  `unrealized` (a `unrealized_pnl`-ek összege)
- `get_account_trades` (period: `TODAY`, ha a review aznapról; különben `DAYS_7`
  és szűrj `trade_time[:10] == {date}`-re) → `realized_today` =
  a `{date}`-i SELL trade-ek `realized_pnl` összege

Írd ki egy temp fájlba (a `baseline_offset` default 208.37 — lásd lent):
```bash
cat > /tmp/ibkr_{date}.json <<'EOF'
{"realized_today": <X>, "position_tickers": [...], "net_liq": <Y>, "unrealized": <Z>}
EOF
```

> **baseline_offset (208.37)**: a pre-pivot cash carry (az IBKR account ~$100,208-ra
> resetelt 5/18-án, nem $100,000-ra) + accrued interest. A cross-check automatikusan
> levonja, így nem flagel false-positive driftet. Részletek:
> `docs/analysis/cumulative-drift-investigation-2026-06-08.md`. Ha a connector
> finomított offsetet ad, tedd be `baseline_offset` kulcsként a snapshotba.

## 3. fázis — 1c draft render (cross-check beépítve)

```bash
python scripts/paper_trading/generate_review.py --date {date} --ibkr-json /tmp/ibkr_{date}.json
```
→ `docs/review/{date}-daily-review.draft.md`. A log kiírja a cross-check flag-ek
számát + a P0-kat. A `build_cross_check_flags` automatikusan elkapja:
- `pnl_tracking_gap` — recorded realized vs broker realized (Day 13/14 incidens-fogó)
- `state_ibkr_divergence` — state pozíciók ≠ IBKR pozíciók
- `cumulative_drift` — cumulative vs NetLiq (baseline_offset levonva)

## 4. fázis — LLM-narratíva kitöltés (CC review-időben)

Olvasd be a draftot + a forrásokat, és töltsd ki a `<!-- LLM: ... -->`
placeholdereket prózával:
- §2 pozíció-narratíva + outlook, §3 pipeline log kulcssorok
  (`logs/pt_submit/close/monitor/reconcile/eod_{date}.log`), §8 strukturális tanulság.
- **Minden P0 flag-et tárgyalj ki** a §0-ban (gyökérok + akció). Ha a drift a
  ismert carry+accrued (≤ tolerancia), az nem P0 — a cross-check már nem flageli.

Mentsd a véglegeset: `docs/review/{date}-daily-review.md` (dobd a `.draft`-ot).

## 5. fázis — eszkaláció

- Ha **valódi P0** maradt (nem a baseline-carry) → jelezd Tamásnak + a review §0
  CHAT ESCALATION blokkban összegezd a stratégiai döntést igénylő pontot.
- Ha tiszta nap → rövid egy-soros összefoglaló a usernek.

## Output (max 8 sor)
- Dátum + NYSE Day-N
- Realized (broker) / cumulative / unrealized
- Cross-check: N flag (ebből P0: M) — ha P0, sorold fel
- Draft → végleges path
- Eszkaláció (ha van)
