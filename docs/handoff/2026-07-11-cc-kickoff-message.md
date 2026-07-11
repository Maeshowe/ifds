# Kickoff — next IFDS session

Folytatás a 2026-07-11 CC-close után (`docs/handoff/2026-07-11-cc-close-handoff.md`).

**Állapot:** A Mini-outage utáni paper trading **stabil** (Mini up 3 nap, state≡IBKR
naponta). A trades-CSV korrupció **P1 fix deployolva** (`ee6b557`, §11.9), a review-data
1a **cron-integrálva** (22:20). Freeze Day 63-ig. **1985 passing.** origin naprakész.

**Nincs sürgős CC-munka.** A freeze alatt a napi rutin él:
- **Napi/heti**: reggeli `sync_from_mini.sh` + „szokásos ellenőrzés" (Mini uptime, EOD-lánc
  teljesség, state≡IBKR reconcile, 0 error) + IBKR MCP cross-check. A napi/heti **review
  Chaté** (v6 prompt); CC a syncet + a mechanikus 1a/1c előkészítést csinálja.
- **Weekly** (péntek zárás után): `weekly_metrics.py` a Mini-n. **Biweekly**:
  `scoring_validation.py` — **`set -a && source .env && set +a` prefixszel** (különben a
  Polygon-kulcs nem exportálódik → SPY-elemzés kimarad; lásd a 07-08/07-11 tanulságot).

**Következő érdemi mérföldkő: Day 63 kapu (≈W31)** — az első valódi `signal_attribution`
futás. Az eszköz + 3 invariáns pre-reg zárva (`c5e9ed0`); a minta nő, ahogy a tiszta,
restart-utáni pozíciók zárnak (az outage-kontamináltak kizárva, Day 126 replan §3 D2).

**Dev-chat-tételek (NEM CC-authored, csak jelzésre):**
1. 3 divergens historikus trades CSV (06-09/10/11) — verifikált regenerálás.
2. CSV-réteg deprecálás (B-megközelítés) — backlog Day 63 utánra.
3. `scoring_validation` swing-only szűrő (§6.6) — a pooled „alpha"-állítás visszavonandó.

**Ha nincs explicit task:** `/continue` → státusz; a freeze miatt valószínűleg csak
sync + ellenőrzés. **Production-kód-változás** (a display/tracking/output-invariáns
§4.2/1 carve-out-on kívül) Day 63-ig **NEM** — előbb 04-risks §11 + edge-audit §4.2/1.

**Mini-műveletek emlékeztető:** prod-pipeline-t SOHA foreground-SSH rövid timeouttal
(orphan-veszély) → `nohup`/háttér + `ps`-verify ([[ssh-prod-process-orphan]]). A crontab
backup: `~/crontab_backup_20260710.txt`. Ha a Mini elérhetetlen: mindkét út (Tailscale +
LAN) down = a Mini maga le (reboot); csak Tailscale = key/SSH-check ([[mac-mini-connectivity]]).
