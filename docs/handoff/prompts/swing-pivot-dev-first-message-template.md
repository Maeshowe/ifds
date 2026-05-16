# Swing Pivot Dev Chat — First Message Templates

> **Usage**: after pasting `swing-pivot-dev-prompt.md` as the first system-level
> prompt, send the Dev chat a **specific first message** that frames the
> session's focus. Below are templates for common starting situations.

---

## Template 1 — Phase 1 start (most likely first use, kb. máj 19)

```
Szia! Új Dev chat sessiont indítunk. A Day 63 outcome és a Fázis 1 cleanup
előtt vagyunk (W21 D1, 2026-05-19). Tamás megcsinálja az IBKR paper account
resetet ma reggel.

Olvasd be az onboarding prompt-ban felsorolt fájlokat (különösen a
2026-05-14-chat-handoff-day63-outcome.md handoff-ot — ott vannak a konkrét
következő lépések).

Az első konkrét feladat: írd meg az első CC task fájlt, az
**IBKR Gateway monitoring + Telegram alert** P1 backlog tételhez.

A task fájl helye: `docs/tasks/2026-05-19-ibkr-gateway-monitoring.md`

Várt tartalom:
- Probléma: 2026-05-11-i IBKR Gateway downtime kontextus (55 perc Tamás-vakság)
- Megközelítés: connection failure detection a submit_orders.py-ban +
  Telegram bot értesítés
- Implementáció: kód-szintű terv (függvények, paraméterek)
- Tesztelés: 2-3 unit teszt (mock IBKR connection failure, retry logic)
- Commit message: konvencionális formátum

Ha készen vagy a tervezett task fájllal, mutasd meg ide először review-ra,
mielőtt írod a filesystem-re. Ha kérdésed van, kérdezz.
```

---

## Template 2 — Phase 2 start (kb. jún 2, W23 D1)

```
Szia! Új Dev chat sessiont indítunk. A Fázis 1 cleanup lezárult (W22 vége),
a Fázis 2 analitikus és design fázis indul.

Olvasd be az onboarding prompt-ban felsorolt fájlokat, plus a legutóbbi
swing-dev-handoff-ot.

A Fázis 2 első prioritás-feladata: **Entry timing backtest design**.

A backtest célja: 4 alternatív entry időablakot (15:30, 16:20, 17:15, 18:30
CEST) összehasonlítani a 60+ napi minta on, hogy validáljuk a 15:30 CEST
entry-választást a swing pivot keretében.

Először írj egy design dokumentumot:
`docs/design/entry-timing-backtest-spec.md`

Tartalom:
- Hipotézis (15:30 jobb mint 16:20)
- Adatforrás (Polygon 1-min bars, 60 napi snapshot)
- Módszertan (P&L újrakalkulálás a tényleges exit-ekkel)
- Statisztikai keret (Bonferroni-korrekció a 4 időablakra)
- Aggregátum metrikák (total P&L, LOSS_EXIT trigger ráta, excess vs SPY)
- Várt kimenet (1-2 domináns időablak konkrét érveléssel)

Ha készen vagy, review-ra mutasd ide. Eztután CC implementálja.
```

---

## Template 3 — Sürgős P0 reagálás (ha a Log Review surfacelt valamit)

```
Szia! Sürgős kontextusban hívlak: a Log Review chat egy P0 (URGENT) jelölést
adott a 04-risks-and-open-questions.md-be.

Olvasd be először a 04-risks-and-open-questions.md tetején lévő P0 szekciót,
aztán a kapcsolódó daily review-t (YYYY-MM-DD-daily-review.md).

A többi onboarding olvasmányt ezután csináld meg.

Az első kérdés: a P0 ügy mit igényel?
- Azonnali CC task (most íratunk fix-et)?
- Vagy design-szintű revíziót (a swing pivot architektúra alapja érintve)?
- Vagy operacionális akció (Tamás kell hozzá a Mac Mini-n)?

Adj javaslatot a következő lépésre, várom a választ.
```

---

## Template 4 — Heti összefoglaló (Friday)

```
Szia! Pénteki összefoglaló session. A heti weekly_metrics.py már lefutott.

Olvasd be:
1. Az onboarding prompt-ban felsorolt fájlokat
2. A héten készült összes daily review-t (docs/review/2026-05-XX...)
3. A heti weekly metric output-ot (docs/analysis/weekly/2026-WXX.md, ha létezik)

Aztán adj:
1. 3-pontos összefoglalót a hétről (operacionális + stratégiai)
2. A swing pivot Fázis-szintű előrehaladásra vonatkozó update-et
3. A következő hét nyitott feladatait (a backlog alapján)

A session végén kérek egy handoff doc-ot a péntek esti weekly summary
formátumban (lásd handoff-append-prompt.md).
```

---

## Notes for Tamás

- A Template 1 az **első valódi használat** mintája (kb. máj 19-én).
- Minden új session-nél válassz egy template-et, és **módosítsd** az aktuális
  helyzetre (dátum, prioritás, kontextus).
- Ha bizonytalan vagy, hogy melyik template illik, kezdj egy üres "olvasd be
  az onboarding fájlokat, aztán adj 3-sentence orientation"-nal, és a Claude
  maga ajánl következő lépést.
- A Log Review chat-hez nem kell First Message — a chat eleve folytatólagos
  (napi review-k egymás után).
