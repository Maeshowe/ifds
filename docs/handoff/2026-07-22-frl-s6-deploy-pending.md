Status: OPEN
Updated: 2026-07-22
Note: Mini áramszünet (2026-07-22) miatt a deploy megszakadt. A CC-oldali munka KÉSZ; a folytatás Tamás push-jóváhagyásával indul, amint a Mini elérhető.

# Handoff — FRL S6 deploy félbeszakadva (Mini-outage, 2026-07-22)

## Egy mondatban

Az FRL teljes build-lane kész és commitolva (`c34c7a0`-ig, **2159 passing**); a v2
enrichment sink **deploy-ra kész**, az előfeltétel-1 bizonyítva — a 7 lépéses
deploy-szekvencia a **3. lépésnél** (Tamás push-jóváhagyás) áll, mert a Mini
2026-07-22-én áramszünet miatt nem elérhető.

## Hol tartunk pontosan

`docs/design/frl/TRACKER.md` az élő állapot. Röviden:

| Lépés | Állapot |
|---|---|
| S0–S5 | **DONE** — teljes FRL infra + a loop első fordulata lezárva (HYP-004 KILLED, Tamás megerősítve) |
| S6 build+teszt | **DONE** (`08d072d`) |
| S6 előfeltétel-1 | **BIZONYÍTVA** (`faa56d3`) — sentinel + negatív kontroll |
| **S6 deploy 3. lépés** | ⏳ **Tamás push-jóváhagyására vár** |
| S6 deploy 4–7. | Mini pull → első 14:30 cron → CC első-fájl verifikáció → `04-risks` §11.11 |

## A folytatás menete (holnap, amint a Mini él)

1. **Mini elérhetőség**: `ssh ifds-mini` (Tailscale `100.76.118.54`; LAN fallback
   `192.168.0.115`). Ha egyik sem megy → a Mini maga van lent (reboot kell).
   Lásd memory: [[mac-mini-connectivity]].
2. **Mini-restart utáni rutin** (a 07-07 és 07-15 outage tanulságai szerint):
   - `state` ≡ IBKR verify (**`qty_remaining`**, nem `qty` — a 07-07-i téves
     „desync"-riasztás ezen múlt)
   - SSH-orphan `deploy_daily.sh` processzek ellenőrzése (`ps`, PID-kill —
     **nem** `pkill -f`); lásd [[ssh-prod-process-orphan]]
   - elakadt max_hold/TIME_STOP exitek keresése (a 07-15-i ITT/XPO minta)
3. **Push-jóváhagyás** (Tamás) → Mini `git pull` → a következő 14:30 cron írja az
   első `state/research_cross_section/YYYY-MM-DD.json.gz` fájlt.
4. **Első-fájl verifikáció (CC)** — a task §Deploy-szekvencia 6. lépése:
   - sor-szám ≈ scan-matrix scored sorok (a mai szinten ~250–260)
   - nyers mezők nem null a pontozott sorokon (`pcr`, `otm_call_ratio`, `rvol`)
   - `swing_score` kitöltve, `legacy_composite` **null** (swing éra)
   - `scored: false` sorokon a score **null**, nem 0.0
5. **`04-risks` §11.11** sor (CC írja a verifikáció után, a 11.x formátumban).

## Az outage következménye a Day 63 edge-mintára

A 2026-07-22-i outage-nap ugyanúgy kezelendő, mint a 07-15/16 (§11.10) és a
06-29→07-06 Mini-outage: **kizárva az edge-mintából**, az FRL IC-idősorban
explicit NaN, nem interpoláció. Az `frl_config.KNOWN_GAPS` bővítése esedékes, ha
az outage több napra nyúlik — most szándékosan nem írtam bele, mert egy napos
kiesésnél a loader `unexpected_missing` mezője helyesen jelzi majd, és a döntés
Chat/Tamás lane.

## Nyitott tételek (nem blokkolók)

| # | Tétel | Lane |
|---|---|---|
| 1 | **Spec §8.2-csere + HYP-005/b vázak** — a Chat hivatkozott rájuk, de az üzenet az MCP-kimaradás miatt **nem érkezett meg CC-hez**; újraküldés kell | Chat |
| 2 | HYP-001a/002a/003a (transzform-szintű) tartalmak — a következő batch-fordulathoz | Chat |
| 3 | `2026-04-06`/`04-07` scan-matrix hiányzik (nem dokumentált gap) — a spec §4.5-be felvéve? | Chat |
| 4 | `execution_plan.py:179` Reason-felülírás — post-Day-63 fix-jelölt (`04-risks` §12.1) | CC, Day 63 után |

## Ellenőrzött állapot a session végén

- **2159 passing**, 0 failure; ruff/black tiszta az összes új fájlon
  (a `runner.py` 2 ruff-findingja **pre-existing**, freeze alatt nem nyúltam hozzá)
- `state/research_cross_section/` **nem létezik** — a sentinel törölve, az első
  fájlt a Mini cron hozza létre
- **Semmi nincs pusholva** — a git push policy szerint Tamás pushol
- Nyitott commitok origin felé: `43c07a5`, `3d50bb9`, `08d072d`, `faa56d3`, `c34c7a0`
  (+ a korábbi FRL-lánc `30b948c`-től)
