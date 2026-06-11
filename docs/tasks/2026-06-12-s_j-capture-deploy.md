Status: OPEN
Updated: 2026-06-11
Note: Az S_j (entry_score) capture live-kód (commit 8b487c1) Mac Mini deploy-ja — SZÁNDÉKOSAN a Day 18 (6/11) mega exit-nap UTÁN, Day 19 (6/12) reggel, a 15:31 submit ELŐTT (edge-audit §6: production trading-path nem toljuk be határidő-nyomás alatt). Kód már origin-on (8b487c1 + Gate A/B edbca3f), Mac Mini még a régi a53a5a9-en. A snapshot-recovery miatt az analitikai veszteség a halasztásból nulla.

# S_j-capture Mac Mini deploy (Day 19 reggel, 15:31 ELŐTT)

**Cél**: az entry_score (S_j) perzisztálás élesítése a production trading-path-on
(`submit_orders.py` + `close_positions.py` + `swing_positions` state-séma +
`pending_exits` ledger), hogy a Day 19+ belépők és exitek hordozzák az
entry combined_score-t a jel-izoláló attribúciós teszthez.

**Előfeltétel-ellenőrzés (deploy ELŐTT)**:
- [ ] Idő < 15:31 CEST (teljes buffer a submit előtt), nappal, felügyelet mellett.
- [ ] `ssh ifds-mini 'cd ~/SSH-Services/ifds && git log --oneline -1'` → a53a5a9 (régi).

**Deploy lépések**:
1. **Pull**: `ssh ifds-mini 'cd ~/SSH-Services/ifds && git pull --ff-only origin master'`
   → várt: 8b487c1 + edbca3f (+ ami azóta jött).
2. **Gate A — ÉLES backward-compat smoke** (a 7 nyitott pozíció entry_score nélkül):
   ```
   ssh ifds-mini 'cd ~/SSH-Services/ifds && .venv/bin/python -c "
   import sys; sys.path.insert(0,\"src\")
   from ifds.state.swing_positions import load_swing_positions
   p = load_swing_positions(\"state/swing_positions.json\")
   print(\"loaded\", len(p), \"positions; entry_scores:\", [getattr(x,\"entry_score\",\"MISSING\") for x in p])
   "'
   ```
   → várt: betölt mind, entry_score=0.0 a meglévőkre, **nincs exception**.
3. **Pre-flight pytest** prod env-ben: `ssh ifds-mini 'cd ~/SSH-Services/ifds && .venv/bin/python -m pytest tests/ -q 2>&1 | tail -3'` → várt: ~1989 passing (baseline 1953 + Gate A; csak nőhet), 0 failure.
4. **Wiring-ellenőrzés**: `ssh ifds-mini 'cd ~/SSH-Services/ifds && grep -c entry_score scripts/paper_trading/submit_orders.py scripts/paper_trading/close_positions.py src/ifds/state/swing_positions.py scripts/paper_trading/lib/pending_exits.py'` → mindegyik ≥1.

**Verifikáció (Day 19 esti EOD után)**:
- [ ] A Day 19-i új belépő(k) a `state/swing_positions.json`-ban **entry_score ≠ 0** (a t["score"]-ból).
- [ ] Bármely Day 19-i exit `pending_exits/{date}.json` ledger-bejegyzése **entry_score**-t hordoz.
- [ ] A daily_metrics + reconcile változatlanul zöld (a változás tracking-only, nem érinti a P&L-t).

**Rollback** (ha bármi gond): `ssh ifds-mini 'cd ~/SSH-Services/ifds && git reset --hard a53a5a9'` (a kód additív + backward-compat, így rollback valószínűtlen, hogy kelljen).

**Lezárás**: deploy + Day 19 verifikáció után → Status DONE, `git mv` az archive-ba; a 04-risks §11.3 frissítése a deploy-dátummal.

## Kapcsolódó
- `docs/foundational/strategic-review/2026-06-10-signal-isolating-attribution-spec.md` (§5 adatrögzítés)
- `docs/master-reference/04-risks-and-open-questions.md` §11.3 (freeze-amendment)
- commit 8b487c1 (S_j-capture) + edbca3f (Gate A/B)
