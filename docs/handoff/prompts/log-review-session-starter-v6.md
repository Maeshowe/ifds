# IFDS — Log Review Session-Indító (v6)

**Használat**: piaczárás után, a `scripts/sync_from_mini.sh` lefuttatását követően (22:16 CEST után, hogy a reconcile-log is szinkronizálódjon) ezt az üzenetet másold be a Log Review chat új sessionjébe. A dátumot írd át.

---

Napi log review — **2026-MM-DD** (Day N). A sync_from_mini.sh lefutott, a Mac Mini mai állapota a MacBooken van.

**Először olvasd be és kövesd szigorúan**: `docs/ifds-log-review-prompt-v6.md` — ez a kanonikus review-spec (anti-hallucinációs szabályok, epistemikus guardrail, kötelező szerkezet, forrás-hierarchia).

Ezután a menet:
1. **Tegnapi review** beolvasása (`docs/review/` legutóbbi fájl) — a várt-vs-tény visszaméréshez.
2. **Mai források** a v6 forrás-táblája szerint (pending_exits → swing_positions → daily_metrics → cumulative_pnl → pt_close/submit/monitor/reconcile/eod logok → cron log → uw_shadow).
3. **IBKR MCP verifikáció**: `get_account_summary` (Net Liq), `get_account_positions` (nyitott pozíciók + unrealized), `get_account_trades` (`TODAY`) — ez a végső igazságforrás; eltérésnél mindkét értéket riportáld ⚠️-gel.
4. **Review megírása** a v6 10-pontos szerkezetében → `docs/review/YYYY-MM-DD-daily-review.md` (ha létezik, nem felülírni: `-v2`).
5. Ha **péntek**: heti zárás blokk a v6 szerint.

Emlékeztetők:
- READ-ONLY: írás csak `docs/review/` és `docs/handoff/`. Fejlesztési igény → P-prioritású task-javaslat a review 6. szekciójában, implementáció CC-re vár.
- **Parameter freeze él Day 63-ig** — freeze-érintő javaslat csak „Day 63-input" címkével rögzíthető.
- Exit-típus forrása kizárólag `pending_exits/{date}.json` (a daily_metrics::exit_type és a Telegram-render a P1 fixig megbízhatatlan).
- Day 63 előtt jel-érvényességi ítélet nincs; statisztika csak n-nel; szuperlatívusz nélkül.
- ~75% kontextusnál: handoff-javaslat proaktívan.
