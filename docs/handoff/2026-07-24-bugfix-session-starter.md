Status: OPEN
Updated: 2026-07-24
Note: Session-indító a BUGFIX-szálhoz — külön session. A review-flagged, freeze-safe javítások végrehajtása. A napi/heti review NEM ide tartozik (az a review-sessionben marad). NEM ez a FRL build-session sem (az külön szál, lásd lent).

# Bugfix Session — Session-indító (új session ezzel kezdjen)

## Mi ez

Ez egy **CC-bugfix session**: a napi review-sorozatban (2026-07-17 → 07-23) felszínre került, **freeze-safe
javítások** végrehajtása TDD-vel. A review-session (a másik szál) folytatja a napi/heti review-t; ez a
session **csak javít**, nem ír review-t.

**Fontos elhatárolás — három párhuzamos szál:**
1. **Review-session** (marad, ahol van): napi/heti v6 review + slippage-sorozat.
2. **FRL build-session** (külön, `docs/handoff/2026-07-21-frl-build-session-starter.md`): a Factor Research
   Loop toolingja. **NE keverd ezzel** — a FRL-tesztek (`test_frl_*`) már léteznek, az a másik szál dolga.
3. **Ez a bugfix-session**: a lenti javítások.

## Az ELSŐ és egyetlen kész feladat: pt_events test-izoláció (P1)

**Task:** `docs/tasks/2026-07-23-pt-events-test-isolation.md` — teljesen specifikált, gyökérok verifikálva,
TDD-terv kész. Ezzel kezdj.

**Egymondatos gyökérok:** a `PTEventLogger.__init__(log_dir="logs")` a production logba ír, és a
`close_positions`/`pt_monitor`/`submit_orders` **modul-szinten, importáláskor** példányosítja a
`evt = PTEventLogger()`-t → bármely teszt, ami a legacy circuit_breaker/trail kódutat exercise-eli, a valós
`logs/pt_events_{today}.jsonl`-be ír. 2026-07-23-án 176 teszt-esemény (AAA/BBB/CCC fixture) szennyezte a logot.

**A fix 4 lépése (a taskban részletezve):**
1. env-vezérelt `log_dir` (`os.environ.get("IFDS_PT_EVENT_DIR", "logs")`) — **viselkedés-invariáns**, ez a
   freeze-carve-out alapja (a d3fce73 precedens: default változatlan, ha az env var nincs).
2. `conftest.py` modul-tetős `IFDS_PT_EVENT_DIR` setdefault (a kollekció ELŐTT — a modul-szintű `evt` miatt
   fixture késő lenne).
3. `tests/test_pt_event_isolation.py` — mtime-invariancia guard + pozitív tmp-path + negatív default-védő.
4. a már szennyezett `logs/pt_events_2026-07-23.jsonl` szűrt cleanup-ja (backup KÖTELEZŐ; Mini + lokális).

**Miért P1:** a `pt_events` a v6 §5 ops-forrás ÉS az FRL loader rank-2 forrása (spec §4.1) — az FRL éles
indulásakor ez a szennyezés a dp_pct/AAPL-mock hibaosztályt ismételné. Ez a [[test-env-hygiene]] szabály
**3. rése** (phase4_snapshot/04-15, uw_shadow/05-19 után) — érdemes a végén körülnézni, van-e más patch-eletlen
sink (`runner.py`/`paper_trading` scriptek modul-szintű I/O példányosítása).

**Step-0 (a taskban, nem blokkoló a fixre):** a *trigger* azonosítása — mi futtatta a pytestet a Mini-n
16:34-16:51 CEST-kor (a `deploy_intraday.sh` 15:45-ös pre-flight? manuális run?). Ha cron pre-flight, akkor
minden nap szennyezne — a korábbi napok kis `pt_events`-e arra utal, hogy nem napi, de verifikáld
(`logs/pt_events_*.jsonl` méret-eloszlás).

## A többi review-flagged tétel disposition-je (NE javítsd freeze alatt)

A review-k több megfigyelést is rögzítettek. Ezek **NEM** ennek a sessionnek a dolga, mert **entry/exit-logikát
érintenek = freeze-tiltott** Day 63-ig. Csak akkor nyúlj hozzájuk, ha explicit Tamás-utasítás jön; egyébként
Day 63-input marad:

| Tétel | Forrás | Miért NEM most |
|---|---|---|
| `entry_price` = tervezett, nem fill (state) | 07-17 §6/P3, 07-21 | a stop/TP a tervezett árból számítódik → **entry-logika**, freeze. §11.10-ben rögzítve. |
| max_hold self-reentry (PFGC 07-21, USFD 07-23, n=2) | 07-21/07-23 §6 | **exit+entry stratégia-logika** → Day 63-input, nem bug. |
| outage-késleltetett exitek (n=3) | 07-15/20/23 | operatív (FileVault), nem kód; lásd lent. |

**Ha a fix-session végzett a pt_events-szel és van kapacitás:** a lehetséges következő freeze-safe fix a
**más patch-eletlen teszt-sinkek auditja** (a test-env-hygiene 4. rés keresése) — de csak ha a pt_events
zöld és pushed.

## Nem-kód, Tamás-döntésre váró (NE csináld magadtól)

- **FileVault gyökérok** (07-22 outage): a Mini FileVault-tal titkosított → áramszünet után a boot-daemonok
  (sshd/tailscaled/cron) feloldás előtt nem indulnak → minden áramesemény kézi belépést igényel. Teljes
  autonómiához 3 együtt kell (FileVault OFF + auto power-on + auto-login). **Tamás-döntés**, a review-session
  viszi. Referencia: [[mac-mini-connectivity]] (2026-07-23 bejegyzés).

## Munkakörnyezet és szabályok

- **Freeze él Day 63-ig.** Csak viselkedés-invariáns / teszt-only / tracking-higiénia változás mehet
  ([[freeze-production-churn-rule]]). A pt_events fix ilyen (a production kódút a default env nélkül bitre azonos).
- **TDD kötelező**: teszt előbb (RED) → fix (GREEN). A baseline passing szám (a FRL build óta ≥1985, nőhetett)
  **csak nőhet**, 0 failure, 0 warning.
- **Mini-írás**: a cleanup a `logs/pt_events_2026-07-23.jsonl`-t érinti a Mini-n — az `ssh ifds-mini`
  allowlisttel megy, a log NEM pénzügyi ledger ([[mini-financial-write-guard]] nem tiltja), de **backup
  kötelező** (`.bak.pre_testclean`). Financial-ledger írást a szemantikai guard továbbra is blokkol.
- **Commit-konvenció**: `fix(test): …`; a task-fájlban megadott commit-üzenet. **Tamás pushol** (CC commitol).
- **Task-workflow**: a task megnyitásakor Status OPEN→WIP; commit után WIP→DONE + `git mv` az archive-ba.

## Első konkrét lépések

1. Olvasd el a `docs/tasks/2026-07-23-pt-events-test-isolation.md`-t teljesen + a
   `docs/review/2026-07-23-daily-review.md` §6/P1-et (a bizonyíték-lánc).
2. Status OPEN→WIP a task-fájlban.
3. TDD: előbb a `test_pt_event_isolation.py` (RED), majd a fix (env var + conftest) (GREEN).
4. Cleanup a 07-23 logon (backup + szűrt újraírás), verifikáld a megmaradó sorokat a review §2-§5 ellen.
5. Teljes suite zöld + a repo-gyökér `logs/pt_events_{today}` mtime-invariancia igazolása.
6. Commit (`fix(test): …`), Status→DONE, task archive-ba, docs (CHANGELOG.md).

## Referenciák

- Task: `docs/tasks/2026-07-23-pt-events-test-isolation.md`
- Bizonyíték: `docs/review/2026-07-23-daily-review.md` §6/P1
- Rokon precedens: `.claude/rules/ifds-rules.md` „Test environment higiénia" (d3fce73, phase4_snapshot;
  uw_shadow 2. előfordulás) — ez a 3. rés.
- Memória: [[test-env-hygiene]], [[freeze-production-churn-rule]], [[mini-financial-write-guard]],
  [[division-of-labor-chat-cc]].
