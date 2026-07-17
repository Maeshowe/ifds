Status: OPEN
Updated: 2026-07-17
Note: TERV + build/teszt a freeze alatt engedélyezett; ÉLES DEPLOY (cron a Mini-n) KIZÁRÓLAG Day 63 után. Fázis A (CC interaktív review) párhuzamosan fut, ez váltja ki Day 63-ig.

# Automatizált napi v6 review a Mac Mini-n (`generate_review.py`)

## Probléma

A napi v6 log-review ma **kézzel** készül (korábban Chat, 2026-07-17-től CC interaktívan — lásd
[[division-of-labor-chat-cc]]). Cél: a review generálása **felügyelet nélkül fusson a Mini-n** a
piaczárás után, és állítsa elő a `docs/review/YYYY-MM-DD-daily-review.md`-t a v6 spec
(`docs/ifds-log-review-prompt-v6.md`) 10-pontos szerkezetében, anti-hallucináció-fegyelemmel.

A v6 spec 4. sora ezt kanonikusan engedi: *"Executor: Chat vagy CC — a review-automatizáció ezt a
fájlt tekinti kanonikus specnek."*

## Fő kockázat és a válasz rá (ez vezérli az architektúrát)

Egy felügyelet nélküli LLM, ami a **Day 63 kaput tápláló** review-t írja, **hallucinálhat számot**.
A válasz: **template-előbb, LLM csak a megítélésre**, + validációs kapu.

- A v6 §1–5 (fejléc, exits, entries, nyitott pozíciók) és §9 (freeze-sor) **determinisztikus tábla**
  a hitelesített adat-bundle-ből → **Python-sablon**, LLM nélkül. A számok soha nem az LLM-től jönnek.
- LLM (Claude API) **kizárólag**: §6 anomáliák (megítélés), §7 megfigyelés-sorozatok szövegezése
  (a számlálók determinisztikusak), §8 holnap, §10 egymondatos zárás. Az LLM inputja **csak** a
  kész, forrásolt bundle; instrukció a v6 anti-hallucináció + epistemikus guardrail szerint.
- **Validációs kapu**: a kész review-ban minden `$`-szám / darabszám vissza kell vezethető legyen a
  bundle-re (scan). Ha egy szám nem forrásolható → NEM final review, hanem `.draft` + WARNING-fejléc
  + Telegram-alert. Anomáliát **jelöl, nem kijelent**.

## Megközelítés — komponensek

| Komponens | Forrás / megjegyzés |
|---|---|
| Adat-bundle (számok ~80%-a) | ✅ már van: `generate_review_data` (1a) → `state/review_data/{date}.json` (22:20 cron). Bővítendő: `market` blokk (SPY/VIX a `daily_metrics`-ből), ops-log-scan összegzés. |
| IBKR-verifikáció | ⚠️ headless Mini-n **NEM** a claude.ai MCP-connector (interaktív-auth, cron-ban hiányzik) → a Mini **saját Gateway-én** (`ib_insync`, `lib/connection`), ahogy `eod_report`/`record_pending_exits`. **Új clientId=19** (10–18 foglalt). Lekérés: account summary (NetLiq), positions (unrealized), `fetch_today_executions` (fillek). |
| várt-vs-tény | tegnapi `docs/review/{prevdate}*.md` §8 „Holnap" sávjának beolvasása + $-eltérés. |
| LLM-kliens | ✅ `ANTHROPIC_API_KEY` a `.env`-ben + kész minta: `scripts/company_intel.py`. Messages API, 1 hívás/nap, kis output (~1–2k token). |
| Mentés | `docs/review/YYYY-MM-DD-daily-review.md`; ha létezik → `-v2` (v6 §Mentés). READ-ONLY máshol. |
| Péntek | heti zárás blokk (v6 §Heti zárás). |

## Implementációs terv (fájlok)

Új:
- `scripts/paper_trading/generate_review.py` — orchestrátor (bundle összerak → template → LLM →
  validációs kapu → mentés). CLI: `--date YYYY-MM-DD` (default: ma), `--dry-run`, `--no-llm`
  (csak a determinisztikus váz, offline teszthez).
- `scripts/paper_trading/lib/review_template.py` — determinisztikus v6 §1–5/§9 renderer
  (bundle+IBKR-verify dict → markdown). **Golden-file-tesztelhető, LLM nélkül.**
- `scripts/paper_trading/lib/review_llm.py` — vékony Claude API réteg §6/§7/§8/§10-hez +
  a validációs kapu (`assert_all_numbers_sourced(review_md, bundle) -> list[unsourced]`).

Újrahasznált (nincs új kód): `lib/connection` (Gateway), `lib/ibkr_reconciliation.fetch_today_executions`,
`generate_review_data` bundle, `lib/telegram_helper` (alert).

Módosítandó (deploy-fázisban, Day 63 után):
- `docs/crontab.md` + Mini crontab: `25 22 * * 1-5 … generate_review.py` (az 1a 22:20 UTÁN,
  trading-day guard). **Freeze alatt NEM kerül a Mini crontab-jába.**
- `CHANGELOG.md`, `docs/PIPELINE_LOGIC.md` (review-pipeline szekció) — deploy-kor.

## Tesztelés (TDD, a freeze alatt megírható+futtatható)

1. **Unit — template renderer**: fixture-bundle → v6 §1–5 markdown, golden-file összevetés
   (07-13-as nap rögzített bundle-jéből). Determinisztikus, hálózat nélkül.
2. **Unit — validációs kapu**: forrásolatlan `$`-számot tartalmazó LLM-output → a kapu elkapja
   (`unsourced != []`), a pipeline `.draft`-ot ír, nem final-t.
3. **Unit — IBKR-verify path mockolva**: NINCS élő connect a tesztben. **Kötelező** minden I/O-sink
   mock (a [[test-env-hygiene]] szabály: se `state/`, se `logs/`, se `docs/review/` prod-írás; csak
   `tmp_path`). Assert: a mock hívva volt (a „test mocked itself out" antipattern ellen).
4. **Unit — várt-vs-tény**: rögzített tegnapi review §8-ból a sávok kiolvasása + $-eltérés.
5. **Integráció — teljes futás fixture-napon** (`--no-llm`): a determinisztikus váz számai
   **egyezzenek a kézzel írt review számaival** (nem a prózával). LLM-mel: smoke, kis token.
6. Baseline: **1985 → nő**, 0 failure, 0 warning.

## Nyitott kérdések / kockázatok

- **Gateway mező-séma** (a [[live-api-schema-verify]] szabály): az `ib_insync` account
  summary/positions mezőnevei ≠ az MCP-connector mezői (ez utóbbit használtam interaktívan).
  **Első commit ELŐTT** élő diagnostic dump a Mini Gateway-en (NetLiq/unrealized/realized kulcsok).
- **clientId=19** — felvenni a CLAUDE.md clientId-táblájába; ütközés-guard (`ib.sleep` + status).
- **Költség**: 1 Claude API hívás/nap, elhanyagolható.
- **Hallucináció-maradvány**: a template-előbb + kapu után is: az első ~2 hét éles futását **CC
  utólag nézze át** (a generált review vs a nyers bundle), mielőtt teljesen „hands-off" lesz.
- **Freeze**: a script + tesztek a freeze alatt készülnek, de a **cron-bekötés a Mini-n csak Day 63
  után**. Addig Fázis A (CC interaktív) fut. Ez a task **Day 63-input** a deploy szempontjából.

## Deploy-kapu

**Day 63 (~2026-08-XX).** Előtte: build + teszt zöld + élő Gateway-séma-verifikáció megvan; a cron
bekötése és az első felügyelt éles futás a Day 63 kiértékelés UTÁN.

## Commit üzenet (build-fázis, deploy nélkül)

```
feat(review): automatizált v6 napi review-generátor (Mini) — template-előbb + vékony LLM

- generate_review.py orchestrátor + review_template.py (determinisztikus §1-5/§9)
  + review_llm.py (Claude API §6-8/10 + forrás-validációs kapu)
- IBKR-verify a Mini Gateway-én (clientId=19), nem MCP (headless)
- template-előbb: a számok a hitelesített bundle-ből, LLM csak megítélés
- validációs kapu: forrásolatlan szám → .draft + alert, nem final
- tesztek: template golden-file, kapu-reject, I/O-sink mock (test-env-hygiene)
- NINCS cron-bekötés (freeze) — deploy-gated Day 63; Fázis A (CC interaktív) fut addig
```
