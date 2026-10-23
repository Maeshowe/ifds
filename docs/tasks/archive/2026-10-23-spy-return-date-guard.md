Status: DONE
Updated: 2026-10-23
Note: Implementálva 2026-10-23. A dátum-guard visszavezetéssel verifikálva (a vak `bars_sorted[-1]` visszaírásakor 2 teszt bukik). A null MEGMARAD a sémában (nem kimarad) — a weekly_metrics `[...]`-tel indexel, tehát a kulcs eltávolítása ott KeyError lenne; a stop_trigger_monitor viszont ugyanebben a változtatásban hagyja ki az ilyen napot. +15 teszt.

# `_fetch_spy_return` — kétrészes guard + a trigger-fogyasztó javítása

## 1. Probléma

`scripts/paper_trading/daily_metrics.py:589-617` a `bars_sorted[-1]`-et veszi **vakon**,
dátum-ellenőrzés nélkül — ellentétben a `_fetch_vix_from_polygon`-nal (`:509-565`), ami
`d == target` egyezést követel és különben `None`-t ad. Egy késleltetett csomagon a SPY
mező ezért **csendben rossz számmá** válhat, nem hiányzóvá.

**Ez döntési bemenet, nem díszítés.** A `spy_return_pct` fogyasztói:

| fájl:sor | mire |
|---|---|
| `scripts/analysis/stop_trigger_monitor.py:131` → `:214` | **az előre regisztrált leállítási trigger** mark-to-market excess-e (`mtm_pct - spy_return_pct`) |
| `scripts/analysis/weekly_metrics.py:72` | heti aggregátum |
| `scripts/analysis/scoring_validation.py:265` | validációs panel |
| `src/ifds/output/swing_telegram.py:152,283` | Telegram-kijelzés |
| `scripts/maintenance/backfill_portfolio_return.py:83` | retroaktív javítás |
| `scripts/paper_trading/pt_monitor.py:492` | **második író** (biztonságos: `today..today` tartomány) |

## 2. A csapda, amit a naiv javítás okozna

A `stop_trigger_monitor.py:131` így olvas:

```python
spy_return_pct=float((payload.get("market") or {}).get("spy_return_pct", 0.0)),
```

- **hiányzó mező** → `0.0`, azaz „a SPY lapos volt" — strukturális-nulla osztály;
- **jelen lévő `None`** → `float(None)` → **TypeError**, az egész elemzés összeomlik.

Tehát a null kiírása önmagában nem megoldás: a fogyasztót ugyanabban a változtatásban
kell javítani.

## 3. Implementációs terv

### 3.1 Kétrészes guard a `_fetch_spy_return`-ben

1. **Dátum-egyezés**, a VIX-minta szerint: dátum-kulcsolt lista, `d == target` követelmény
   a mai barra, a `prev` a target előtti utolsó bar. Nincs egyezés → `None`.
2. **Tolerancia-alapú teljességi padló**, mert a dátum-egyezés önmagában átenged egy
   **részleges** bart (mérve: 2026-10-23 09:42 ET-kor a mai bar már létezett, de
   `-0,484`-et adott, nem a valódi zárást):

   ```
   v >= 0.25 * median(a megelőző 20 bar v-je)
   ```

   **Kalibráció** (a ház szabálya: független forrásból, és verdikt-stabil tartomány
   belsejéből): 474 sessionön verifikálva a verdikt-stabil tartomány **[0,20; 0,40)** —
   0/474 teljes session esik ki benne. A 0,25 a tartomány belsejében van, és a gördülő
   volumen-eloszlásból jön, **nem** a védett mezőből.

   ⚠️ Ez a fele **nem** védi az I:VIX-et: minden index-bar `v=None`. A VIX-et a
   dátum-egyezés + a futási időpont védi (lásd a cron-tolás taskot).

### 3.2 Bukáskor: a sor megíródik, a mezők KIMARADNAK

- `market.spy_return_pct`, `excess_return.spy_return_pct`, `excess_return.excess_pct`
  **kulcsok nélkül** (nem `None` értékkel — lásd §2).
- `logger.warning` a VIX-ág stílusában, megnevezve a degradációt.
- Additív `data_quality: {"spy_return": "no_bar_for_target_date" | "partial_bar"}`.
  Additív top-level kulcs biztonságos: a `_retroreconcile_applied` precedens bizonyítja.

### 3.3 A fogyasztó javítása (KÖTELEZŐ kísérő)

`scripts/analysis/stop_trigger_monitor.py`: egy nap, aminek nincs `spy_return_pct`-je,
**kimaradjon** (`continue`), ne 0,0-ként olvasódjon. A `:125`-ös `excess_pct`-minta
(`if "excess_pct" not in excess_block: continue`) már pontosan ezt csinálja — ugyanaz a
forma kell a SPY-ra.

## 4. Tesztelés

Új `tests/test_spy_return_guard.py`, hermetikusan (nincs hálózat, nincs prod-state):

- mai bar hiányzik → `None` + `data_quality` ok;
- részleges bar (volumen a padló alatt) → `None` + `partial_bar`;
- teljes bar → érték, `data_quality` nélkül;
- a padló **tolerancia-alapú**, nem `== 0`;
- a `stop_trigger_monitor` a hiányzó mezős napot **kihagyja**, nem 0,0-nak olvassa
  (regressziós teszt a strukturális-nulla osztályra).

## 5. Commit üzenet

```
fix(daily_metrics): kétrészes guard a SPY-hozamra + a trigger-fogyasztó javítása

A _fetch_spy_return a bars_sorted[-1]-et vette vakon, dátum-ellenőrzés nélkül — a
VIX-ág ugyanitt d == target egyezést követel. Késleltetett csomagon ez csendben rossz
számot írna a kutatási adatfolyamba, és a spy_return_pct NEM díszítés: a
stop_trigger_monitor előre regisztrált leállítási triggere ebből számol excesst.

Dátum-egyezés + tolerancia-alapú teljességi padló (v >= 0.25 × a gördülő 20 bar
mediánja; 474 sessionön verdikt-stabil a [0,20; 0,40) tartományon, a választott érték
a belsejéből, a gördülő volumen-eloszlásból kalibrálva).

Bukáskor a sor megíródik, a mezők kimaradnak, data_quality rögzíti az okot. A
stop_trigger_monitor ugyanebben a változtatásban hagyja ki az ilyen napot — különben
a hiányzó mező 0,0-ként, azaz „lapos SPY"-ként olvasódna (strukturális-nulla osztály),
egy jelen lévő None pedig float(None)-nal összeomlasztaná az elemzést.
```
