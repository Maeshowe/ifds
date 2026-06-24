# Kickoff — next IFDS session

Folytatás a 2026-06-24 CC-close után (`docs/handoff/2026-06-24-cc-close-handoff.md`).

**Állapot:** Nincs nyitott IFDS-tétel. A UW-GEX flip **él és log-igazolt**
(Polygon-only GEX, a 06-24 14:30 runból verifikálva), a `signal_attribution.py`
eszköz **tesztelt + a 3 invariáns pinned** (Day 63-ra kész), a settings-footer
risk-display javítva. 3 commit (`c5e9ed0`, `ae72905`, `c5f1e0c`) **pusholva +
Mini-re deployolva**. Production-kód **fagyott Day 63-ig**. **1981 passing.**

**Nincs azonnali CC-munka.** A freeze alatt csak az adatgyűjtés él + a napi
review-k v6 szerint (`docs/ifds-log-review-prompt-v6.md`). A churn-vonal lezárva:
S_j-capture (§11.3) → UW-flag (§11.6) → flip (§11.7) → footer-fix (§11.8) → STOP.

**A következő érdemi mérföldkövek (előretekintő, nem most):**
1. **Day 63 kapu (≈W31)** — az első valódi `signal_attribution` futás a lezárt
   mintán. Most n=12 clean pozíció → ~40-45 Day 63-ra. Az eszköz + a metrika-választás
   (L2 Spearman h=5, szektor-relatív) + a küszöbök + minta-definíciók **pre-reg
   zárva** (`c5e9ed0`). A futtatás: `python scripts/analysis/signal_attribution.py`
   (Polygon-kulccsal, a forward-return fetch éles ott). Lásd spec §6.1 + a
   data-coverage doc (a 8 korai trade genuinely elveszett — `full` minta korai
   szakasza per-trade csonka, a tiszta per-trade attribúció Day 9-től él).
2. **Day 21 checkpoint (−$1,500 küszöb)** — opcionális köztes drawdown-olvasat, ha
   a P&L tovább esik (e heti cumulative 1716 → 555 négy nap alatt). A napi review-k
   tárgya, nem flip-ügy.
3. **Journal-szinkron (Chat)** — a `2026-06-24-session-close.md` "STEP 2 DONE" sora
   a verifikált rekordhoz igazítandó (§11.7+§11.8 a log-alátámasztott igazság).

**Ha a session elején nincs explicit task:** `/continue` → státusz, majd a freeze
miatt valószínűleg nincs kód-teendő. Bármilyen production-kód-változás (a display/
tracking/output-invariáns carve-out-on kívül) Day 63-ig **NEM** mehet — előbb a
`docs/master-reference/04-risks-and-open-questions.md` §11 + edge-audit §4.2/1.

**Mini-állapot (autoritatív, 06-24):** `state/prod_overrides.json =
{"tuning":{"uw_gex_fetch_enabled":false}}` (flip él), HEAD = `c5f1e0c`,
`IFDS_UW_API_KEY` kikommentelve a .env-ben (graceful, a 06-24 run igazolja).
Revert: `rm state/prod_overrides.json` a Mini-n → azonnali UW→Polygon fallback.
