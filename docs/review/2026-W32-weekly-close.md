# IFDS Heti zárás — 2026-W32 (Aug 03 – Aug 07) + biweekly scoring_validation

> Executor: **CC** (CC-only, [[division-of-labor-chat-cc]]). READ-ONLY; forrás minden szám mellett.
> **Önálló heti dokumentum**: a pénteki (08-07) napi review **nem készülhetett el** — a Mac Mini
> egész nap elérhetetlen volt (§1). Day 63 előtt nincs jel-ítélet.

## 1. 🔴 A 08-07-i kiesés — ismét FileVault, és egy beragadt exit

**Diagnózis (verifikált):**
```
Mini boot:            2026-08-07 10:46
tailscaled indulás:   2026-08-07 23:35   ← ~13 óra a FileVault feloldó-képernyőn
utolsó pt_event:      2026-08-07 10:10   (a monitor_positions, a leállás ELŐTT)
```
A Mini pénteken ~10:1x-kor leállt, 10:46-kor bootolt, majd **13 órán át zárolva állt**. Emiatt a
**14:30 intraday, 15:31 submit, 21:40 time_stop, 22:00 eod_eval és a teljes EOD-lánc kimaradt**.

**Ez a FileVault-gyökérok második előfordulása** (07-22 után), és összesen a **negyedik outage**
(06-29→07-07, 07-15/16 áramszünet, 07-22, 08-07). A [[mac-mini-connectivity]] 2026-07-23-i bejegyzése
pontosan ezt írta le: *„minden áramesemény kézi belépést igényel; az UPS csak ritkítja, nem szünteti meg."*

### ⚠️ Beragadt exit: DE TIME_STOP
A **DE** (10 db) 08-06-án day-5 max_hold TIME_STOP flaget kapott, végrehajtás **08-07 21:40** lett volna —
**kimaradt**. Állapot ma (08-08):
- `swing_positions`: DE `next_action=TIME_STOP` ✓ (a flag megmaradt)
- **state ≡ IBKR: 6/6** ✓ (DE, GTES, JAZZ, SAIC, SSNC, VLTO)
- **Végrehajtás: hétfő (08-10) 21:40**, azaz **1 trading nap késéssel**

**Ez a 4. outage-késleltetett exit** (ITT/XPO 07-15, PFGC/BIRK 07-20, USFD 07-23, most DE).
📌 **Az eddigiektől eltérően ez eddig KEDVEZ**: a DE a késés alatt emelkedett — 08-06 mark 613,71
(`várt` +$152) → ma **620,83** (**+$223,40** unrealized). **Ez szerencse, nem tervezés** — a korábbi
három késett exit mind rosszabbul zárt. Day 63-input: az outage-kontamináció **kétirányú**.

## 2. W32 heti eredmény — forrás: `docs/analysis/weekly/2026-W32.md`
**4 trading nap** (08-07 outage miatt kimaradt).

| Nap | Realized | Excess | SPY | Equity (EOD) |
|---|---|---|---|---|
| 08-03 (H) | $0,00 | −1,42% | +1,42% | $100 471,02 |
| 08-04 (K) | −$25,02 | −1,82% | +1,80% | $100 835,69 |
| 08-05 (Sze) | **+$91,29** | +0,29% | −0,20% | $100 353,03 |
| 08-06 (Cs) | **−$493,70** | −0,33% | −0,16% | $100 471,62 |
| 08-07 (P) | — | — | — | — (outage) |

- **Heti net: −$427,43** (gross −$420,77, komm. $6,66). **Cumulative: +$347,45 → −$79,98**.
- ⚠️ **Excess vs SPY: −3,28%** (portfolio −0,42% vs SPY **+2,86%**) — **a swing-éra legnagyobb heti
  lemaradása**. A SPY erős emelkedő hete volt, a könyv nem követte.
- **Exit-bontás**: 6 exit — 3 MOC (TIME_STOP), 2 SL (a CTAS/TTWO mental-stop), 1 TP1. **Win days 1/4**.
- **A hét karaktere (tényszerű)**: a 08-06-i két mental-stop (**−$493,70**) egyetlen nap alatt elvitte
  a teljes addigi pozitívumot. A könyv viszont **kitisztult** — a hét végén unrealized ≈ −$39, nincs
  kritikusan szűk stop-buffer.
- **NetLiq a héten**: $100 166,14 (07-31) → $100 471,62 (08-06) = **+$305,48** — a **negatív realizált
  ellenére emelkedett**, mert a két veszteséges tétel kikerült a könyvből.

## 3. Biweekly scoring_validation — forrás: `docs/analysis/scoring-validation.md` (regenerálva)
**484 trade** (+14 az előző, 07-25-i futáshoz képest), **484/484 SPY-joined**, 277 enriched.

**Headline**: total P&L −$1 243,64 | win rate 47,5% | score→excess Pearson **−0,150\*\*** (p=0,001).

### ⚠️ A G5 éra-bontás — a swing-hatás NEM tűnt el, nagyobb mintán is áll
| Éra | N | Pearson (score vs excess) | Változás az előző futáshoz |
|---|---|---|---|
| legacy | 442 | **+0,022** (p=0,651) | változatlan (null) |
| **swing** | **42** (volt 28) | **−0,393\*** (p=0,010) | volt −0,509\*\* (n=28) |
| pooled ⚠️ | 484 | −0,150\*\* (p=0,001) | volt −0,144\*\* |

**Leíró megfigyelés (G1/G3 — NEM jel-ítélet, NEM kapu-input):** a swing-éra negatív együttmozgása
**14 új trade-del is fennmaradt**, az együttható enyhén mérséklődött (−0,509 → −0,393), a szignifikancia
megmaradt (p=0,010). A legacy továbbra is tiszta null. **A „magas pontszám paradoxon" iránya tehát a
swing-érában konzisztens** — de a minta még mindig kicsi (n=42), és a kapu egyetlen inputja a
`signal_attribution.py` (pinned `c5e9ed0`), nem ez a riport.

## 4. STOP-trigger állás (D4: a `mean` az irányadó)
| Mutató | Érték | Küszöb | Státusz |
|---|---|---|---|
| `excess_10d_mean` | **−0,37%** | −1,0% | ✓ **nincs halt** (2,7× a küszöbtől) |
| `excess_15d_mean` | −0,23% | −1,0% | ✓ |
| `excess_10d_sum` | −3,72% | −1,0% | ⚠️ breach (megfigyelés, D4) |
| **`cum_30d`** | **−1,81%** | −3,0% | ✓, de **négy napja monoton romlik** |
| MTM-diagnosztika (10d) | −0,38% | — | ≈ egyezik a realized `mean`-nel |

**A `cum_30d` a fő követendő mutató**: −0,42% (08-03) → −1,08% → −1,32% → **−1,81%** (08-06),
a küszöb **60%-a**. A `mean` oldalazik. *(A 08-07-i outage-nap nem szerepel egyik ablakban sem —
nincs adata, nincs interpoláció.)*

## 5. Vasárnapi (08-09 22:00) Phase 1-3 futás — előfeltételek ✅
A 08-02-i futás FMP-kiesés miatt HALT-olt; ma ellenőriztem az előfeltételeket:
- ✓ **Cron ép**: `0 22 * * 0 … deploy_daily.sh --phases 1-3` + `0 23 * * 0 … check_phase13_freshness.py`
- ✓ **FMP egészséges**: `check_health` = **ok, 802 ms** (a 08-02-i 34 548 ms timeout után)
- ✓ **Mini fut és fel van oldva** (tailscaled 08-07 23:35 óta)
- ⚠️ **A context 87,5 órás** (08-04 19:32, a manuális futásom) — a vasárnapi futás frissíti
- 🔴 **A maradék kockázat: FileVault.** Ha a Mini vasárnap 22:00 ELŐTT újraindul és senki nem oldja fel,
  a futás **ismét kimarad**. Ez nem szoftveres kérdés — a [[mac-mini-connectivity]] szerinti
  3-elemű csomag (FileVault OFF + auto power-on + auto-login) oldaná meg véglegesen.

**Hétfő reggel ellenőrzendő**: futott-e a vasárnapi Phase 1-3 (context mtime), és lefut-e a hétfői
21:40-es DE TIME_STOP.

## 6. Következő hét
- **Hétfő 08-10**: DE TIME_STOP 21:40 (várt ≈ **+$223**, a mai markkal) — 1 nap késve.
- **Kapu: Day 63 ~2026-08-17 — 5 trading nap.** Akkor: **freeze feloldása + az ELSŐ leíró
  `signal_attribution` futás** (D1-döntés). A kizárási lista véglegesítendő előtte (a 08-07-i
  outage-nap és a DE késett exitje **hozzáadandó**).
- **Nyitott ops-döntés**: FileVault (Tamás) — a negyedik outage után.
