# IFDS Daily Review — 2026-09-01 (kedd, Day 74/63)

> Executor: **CC** (CC-only). READ-ONLY; forrás minden szám mellett.
> ⚠️ Az IBKR MCP connector továbbra sem elérhető — bróker-oldali kereszt-ellenőrzés **kimaradt**.
> Helyette: Mini `reconcile_state` **silent OK** (`state ≡ IBKR`), `pending_exits` feldolgozva,
> záró markok **Polygon**-ból.

## 1. Fejléc
- **Realized net: −$502,07** (gross −$498,73, komm. $3,34) — **3 exit, mind TIME_STOP MOC**.
- **Cumulative: −$2 277,01 (−2,28%)** — **először megy $2 000 alá**.
- **Net Liq: $97 844,87** — napi Δ **−$682,99**.
- **Excess: +0,19%** (portfolio −0,50% vs SPY −0,69%). **MTM: −0,00%** — gyakorlatilag nulla.
- **VIX 16,44 (+10,19%)**, SPY **−0,69%** — **éles risk-off**, a VIX legnagyobb egynapos ugrása hetek óta.
- **Nyitott pozíciók: 7** (10-ről).

## 2. 🔴 A NAP FŐ TÉTELE — a `cum_30d` a leállítási küszöb közelében

| | |
|---|---|
| **`cum_30d`** | **−2,77%** (−$2 768,35) |
| Pre-reg leállítási küszöb | **−3,0%** *(bármelyik trigger elég)* |
| **Távolság** | **0,23 pp = $231,65** |
| Előző nap | −2,27% |

**Ez a legszorosabb állás, amit bármely valódi trigger valaha elért** (az eddigi rekord 0,73 pp
volt, tegnap). ⚠️ **Ez NEM a `sum`-olvasat** (ami D4 szerint megfigyelés) — a `cum_30d`
**pre-regisztrált leállítási feltétel**.

**A gördülő ablak mechanikája (tényszerű, nem előrejelzés):**
- A jelenlegi ablak: **2026-07-20 → 09-01**.
- **Holnap a 07-20-i nap gördül ki, ami −$438,55 volt.**
- Aritmetika: ha a mai realizált **X**, az új érték `−$2 329,80 + X`.
  A **−3,0% küszöb** akkor sérülne, ha **X < −$670,20**.
- Ma **egy** flagelt exit van (NWBI TIME_STOP, a 08-31-i markon ≈ −$74).

📌 **A távolság riportálható, a kimenetel előrejelzése nem** (§3). A tény: a mutató **a küszöb
közelébe került**, és az ablak-gördülés holnap **matematikailag kedvező** irányba hat.
**Tamás figyelmébe ajánlott — a leállítás human-in-the-loop döntés, nem automatizmus.**

## 3. Exits (3) — mind TIME_STOP MOC
| Idő (UTC) | Ticker | Qty | Entry → Exit | Realized | Becslésem | Δ |
|---|---|---|---|---|---|---|
| 19:59:31 | MD | 183 | 26,63 → 26,47 | −$29,59 (−0,61%) | ≈ −$71 | +$41 |
| 19:59:32 | ELVN | 78 | 60,38 → 57,84 | −$197,89 (−4,20%) | ≈ −$192 | **−$6** ✓ |
| 19:59:30 | **RGEN** | 25 | 180,80 → **169,82** | **−$274,59 (−6,07%)** | ≈ **+$7** | **−$282** |
| **Σ** | | | | **−$502,07** | ≈ −$256 | **−$246** |

⚠️ **A Σ-hibát gyakorlatilag egyetlen tétel adja.** Az ELVN-becslés **$6-on belül** volt, az MD
$41-en belül — de az **RGEN egyetlen ülés alatt −6,07%-ot esett** (180,98 → 169,82), miközben az
SPY −0,69%-ot. **A legnagyobb egy-tételes becslési tévedésem** ($282). A módszer (tegnapi záró ≈
mai záró) **egyedi, nagy elmozdulásokra elvileg vak** — ezt a §8-ban következetesen jelzem.

## 4. Entries (0) — 🔴 **VERIFIKÁLT OK: a szektor-cap MÁR KÖT**
64 ticker lépte át a küszöböt, **0 belépő**. A `submit` log szerint az execution plan
**mindössze 2 tickert** tartalmazott (IMAX, RCI) — és **mindkettő már tartott pozíció**
(`Skipping … already has position`), tehát 0 submit.

**Az ok NEM a submitban van, hanem a Phase 6-ban.** Az intraday cron log szó szerint:

```
Analyzed: 64 | Passed: 59 | Excluded (NEGATIVE regime): 5
Excluded — sector limit: 3  position limit: 54  risk limit: 0  exposure limit: 0
```

- **`sector limit: 3`** — a **szektor-cap ténylegesen kizárt 3 jelöltet.** A 08-28-án felvetett
  `sector_cap_proximity` figyelmeztetés ezzel **valódi korláttá vált**. A Financial Services
  **29,27%** a 30%-os cap ellenében; a top-3-ban ma **volt** nem-tartott jelölt (**SFNC 88,0,
  Financial Services**), és nem került a tervbe.
- **`position limit: 54`** — a **domináns szűrő**: az 59 jelöltből 54-et ez zárt ki.
- `risk limit: 0`, `exposure limit: 0` — a VaR/kitettség-guardok **nem** kötöttek.

📌 **Módszertani megjegyzés**: tegnap éppen azért vontam vissza egy öt napon át vitt
értelmezést, mert nem néztem a forráskódig. Ezt ma **a Phase 6 log alapján** állítom,
nem következtetésből. *(Hogy a 3 szektor-kizárt egyike konkrétan az SFNC volt-e, a log
nem bontja — a **szektor-limit kötése** viszont tényszerű.)*

## 5. Nyitott pozíciók (7) — 09-01 záró mark
| Ticker | Szektor | Bázis | Záró | Unrealized |
|---|---|---|---|---|
| AMR (TP1 után) | Energy | 219,00 | 233,41 | **+$100,87** |
| FBP | Fin. Services | 27,90 | 27,85 | −$18,95 |
| IMAX | Comm. Services | 52,48 | 51,13 | −$112,05 |
| RCI | Comm. Services | 36,87 | 36,41 | −$121,44 |
| CRBG | Fin. Services | 32,92 | 32,17 | −$152,25 |
| IMVT | Healthcare | 41,48 | 39,90 | −$175,38 |
| NWBI | Fin. Services | 15,39 | 15,14 | −$191,18 |
| **Σ** | | | | **−$670,38** |

A könyv **−$472,97 → −$670,38**; **1/7 pozitív** (csak az AMR). A kitettség **63,48% → 49,41%**
(a három exit után). **Healthcare 18 641,86 → 4 573,20** (csak az IMVT maradt);
**Financial Services 29,27%** — **változatlan, és most már a könyv 59%-a**.

## 6. Ops-checklist
- ✓ **Teljes cron-lánc lefutott**: 14:30 Phase 4-6, 15:31 submit (0 tétel), 21:40 time_stop (3 MOC),
  22:00–22:45 eod-lánc. `reconcile_silent_ok`.
- 🟡 **`sector_cap_proximity` P2, 3. nap** — és ma **ténylegesen kötött** (§4).
- ✓ **STOP-triggerek** (D4: a `mean` az irányadó):
  `excess_10d_mean` **−0,09%** ✓ | `excess_15d_mean` **−0,09%** ✓ | `excess_10d_sum` −0,89% ✓
- 🔴 **`cum_30d` −2,77%** — §2. **A legfontosabb nyitott tétel.**
- ⚠️ `excess_15d_sum` −1,32% BREACH (D4: megfigyelés).

## 7. Anomáliák (új/változott/lezárt)
- **🔴 A `cum_30d` a leállítási küszöb 0,23 pp-es közelében** — §2. Az egyetlen pre-reg
  leállítási feltétel, ami valaha ennyire megközelítette a küszöbét.
- **🔴 A szektor-cap ténylegesen köt** (`sector limit: 3`) — §4. A 08-28-i figyelmeztetés
  **korláttá vált**. Ez a **Phase 6 sizing viselkedését** érinti, és a jövő heti fókusz része.
  ⚠️ Kapu előtt **nem nyúlunk hozzá** (D6: prod fagyva 09-22-ig).
- **📌 A `position limit` a domináns szűrő** (54/59) — ez **nem** új defekt, hanem a jelenlegi
  konfiguráció következménye; **leíró rögzítés (G3)**, a D6 SIM-napirend potenciális tétele.
- **📌 A becslési módszer korlátja élesben** — az RGEN −6,07%-os egynapos esése $282-os tévedést
  okozott (§3). A „tegnapi záró ≈ mai záró" feltevés **egyedi sokkra vak**; a §8 „várt" oszlop
  **nagyságrend**.
- **✅ VÁLTOZATLAN**: `exit_type` ma helyes (normál ablak, §11.17), `swing_state.exits_today`
  félrenevezés (ma `{TIME_STOP:1}` ≡ a **mai** NWBI flag), `commission_total` csak exit-láb,
  `entry_price=planned`, `reconcile` csak ticker-halmaz, **FileVault**,
  **`docs/analysis/` sync-rés**, **§5.1/§5.2 döntések**.

## 8. Megfigyelés-sorozatok (kumulatív, következtetés NÉLKÜL)
- **TP1-sorozat** — n=4, mind pozitív; 3 ciklus lezárt (Σ +$453,35). Ma nem bővült.
- **Pozitív realizált nap** — 24/66 (ma nem).
- **Next-day MKT fill slippage** — CC-éra n=38, változatlan (ma 0 belépő).
- **Szektor-koncentráció** — Financial Services **29,27%**, 3. nap a flag-küszöb felett, **és ma kötött**.
- **Kitettség** — 49,41% (a 63,48%-os rekordról).
- **Rally/risk-off aszimmetria** — eső nap, realized szerint +0,19% felülteljesítés.
  Sorozat: 11 rally-lemaradás vs **12** eső-napi felülteljesítés.
- **Outage-késleltetett exit** — n=4 (+ a 08-21-i EQH/DLB **döntés alatt**, §5.2).
- **TP-hit / pozitív-exit**: **0/3**. **Várt-vs-tény**: **−$246**, gyakorlatilag egy tételből.

## 9. Ma (szerda, 09-02) — várt + feltevés
**Egy TIME_STOP 21:40 MOC**:

| Ticker | Qty | Bázis / záró | `várt` |
|---|---|---|---|
| NWBI | 780 | 15,39 / 15,14 | **≈ −$191** |

⚠️ **Nagyságrend, nem előrejelzés** — lásd §3 (az RGEN tegnap $282-t tévedett).
- **Fókuszlista**: (1) a **`cum_30d`** (−2,77%, §2) — a nap első száma; (2) a NWBI TIME_STOP;
  (3) a **szektor-cap** kötése (lesz-e ma belépő?); (4) a −$670-es könyv.

## 10. Freeze-sor
🔓 A freeze 08-17-én feloldódott — **de a D6 szerint a production konfiguráció FAGYVA marad
2026-09-22-ig**. A **G1/G3–G7 guardrailek élnek**. Ma **nem történt** production-kód változás.
**A kapuig 14 kereskedési nap.**

## 11. A nap egy mondatban
Három max_hold-exit **−$502,07**-tal a kumulatívat **először vitte $2 000 alá** (−$2 277,01) —
a hibát gyakorlatilag egyetlen tétel, az **egy ülés alatt −6,07%-ot eső RGEN** okozta —, miközben
két strukturális dolog is élesbe fordult: a **`cum_30d` −2,77%-ra, a −3,0%-os leállítási küszöb
0,23 pp-es közelébe** került (a valaha volt legszorosabb állás), és a **szektor-cap a Phase 6-ban
ténylegesen kizárt 3 jelöltet** — a 08-28-i figyelmeztetésből **valódi korlát** lett.
