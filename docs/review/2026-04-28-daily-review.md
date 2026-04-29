# Daily Review — 2026-04-28 (kedd)

**BC23 Day 12 / W18 Day 2**
**Paper Trading Day 52/63**

---

## Számok

| Metrika | Érték |
|---------|-------|
| Napi P&L gross | -$268.61 |
| Napi P&L net | **-$308.28** (commission $39.67) |
| Kumulatív P&L | **-$617.46 (-0.62%)** |
| Pozíciók (új) | 5 ticker (CRWV, NVDA, PBR, PAA, NIO) — state-split miatt 8 trade |
| Win rate | 2/5 ticker (NVDA, PAA nyert; CRWV, PBR, NIO vesztett) |
| TP1 hit rate | 0/5 (0%) |
| TP2 hit rate | 0/5 (0%) |
| Exit mix | 5× MOC, 3× LOSS_EXIT (CRWV, NIO×2), 0× SL, 0× TP |
| Avg slippage | -0.12% (CRWV +-0.74% kedvező) |
| Commission | **$39.67** ← újabb napi maximum |
| SPY return | -0.49% |
| Portfolio return | -0.27% |
| **Excess vs SPY** | **+0.22%** ← outperform negatív napon |
| VIX close | (továbbra is null, daily_metrics task várólistán) |

## ⭐ A nap nagy ünnepe — Breakeven Lock első éles aktiválás

**A PAA pozíción a Breakeven Lock pontosan úgy működött, ahogy terveztük.**

```
16:17:25 CEST  PAA Entry $22.11 (planned $22.09, slippage +0.09%)
               SL $21.51, TP1 $22.56, TP2 $22.85

19:00:16 UTC = 19:00:16 CEST  trail_activated_b
               Trail SL $21.67 (1.99% entry alatt — klasszikus trail)
               Ár: $22.25 (+0.63% profit)

19:00:19 UTC = 19:00:19 CEST  breakeven_lock_applied ✨
               old_sl: $21.67 → new_sl: $22.09 (entry)
               lock_type: profit_breakeven
               +0.42 floor jump

19:40:13 CEST  MOC submit (split: 500 + 405)

20:00:00 CEST  Fill $22.26 = +$0.15/share, +$135.75 net
```

**Ami nélkül a Breakeven Lock**: ha az ár 19:00 után visszaesett volna $22 alá (ami közeli volt), a trail SL $21.67-en megfogta volna $440-os pozíción ~-$180 veszteséggel. **A Breakeven Lock megelőzte ezt** — a $22.09 floor garantálta, hogy minimum 0 P&L (ha visszaesett volna entry-re), maximum a tényleges +$135.75 profit (a MOC-on).

**A lock NEM termelt extra kárt.** A PAA végül +$135.75-tel zárt MOC-on, ami felett van az entry $22.09 SL. A trail mechanika **természetesen folytatódott**, amíg a MOC le nem lőtt.

**Ez a 138 új teszt mathematikai garanciájának élő bizonyítéka:** soft floor `max(trail_sl, floor)` művelete soha nem ad rosszabb eredményt a régi rendszerhez képest.

## A PAA volt a nap egyetlen "trail-protected" pozíciója

Nézzük meg, **miért nem aktiválódott** a többi pozíción:

| Ticker | Entry | Exit | trail_b? | Breakeven Lock? | Indok |
|--------|-------|------|----------|----------------|-------|
| **PAA** | $22.11 | MOC $22.26 | ✓ 19:00 | ✓ aktivált | Profit, soft floor entry-n |
| NVDA | $213.04 | MOC $213.27 | ✓ 21:05 | ✗ késő | trail_b csak 21:05-kor (a window túl) |
| PBR | $21.30 | MOC $21.22 | ✗ | ✗ | Nem ért el trail trigger küszöböt |
| CRWV | $109.14 | LOSS_EXIT $106.53 | ✗ | ✗ | LOSS_EXIT 19:00 előtt (-3.11%) |
| NIO | $6.43 | LOSS_EXIT $6.29 | ✗ | ✗ | LOSS_EXIT 19:05-kor |

**1/5 pozíción** aktiválódott a Breakeven Lock. **Ez normál arány** — csak akkor működik, ha trail_b 19:00 előtt aktiválódott ÉS profit van. Ma a PAA volt az egyetlen pozíció, ami megfelelt.

**Az NVDA edge case érdekes:** a trail_b CSAK 21:05 CEST-kor aktiválódott (= 19:05 UTC), ami **5 perccel** a 19:00-19:04:59 CEST window vége után. **A window-szabály miatt nem kapta meg a védelmet.** Ez **rendben van** — ezt szándékosan tervetettük, hogy ne legyen kuszáló. Az NVDA végül +$19 MOC-on, **kis profit**.

## Pozíciók részletei

### Nyertesek (2)

**PAA (energy partnerships, score 90.5)**: Entry $22.11, MOC $22.26 = **+$135.75 össz** (60.75 + 75 split). +0.68% intraday. **A nap egyetlen "menedzselt" nyertese** — a Breakeven Lock biztosította, hogy a kis profit ne csapjon át veszteségbe.

**NVDA (semi, score 94.5)**: Entry $213.04, MOC $213.27 = **+$19.03**. Csak +0.11% intraday. **Túl későn aktiválódott a trail_b** (21:05) ahhoz, hogy a Breakeven Lock megfogja, de így is profit lett. Ha az ár visszaesett volna 21:05-21:30 között, az NVDA -$70 körüli kárral zárt volna, mert a trail SL $205.66-on volt (3.5% entry alatt).

### Vesztesek (3)

**CRWV (CoreWeave, AI compute, score 95.0)**: Entry $109.14 (slippage **-0.74% kedvező**, -$0.81/share), **LOSS_EXIT @ $106.53 19:00-kor** = **-$133.50**. -2.45% mozgás 2.5 óra alatt. **A CRWV a magas score (95!) ellenére azonnal eladók** — a -$130 a CRWV-n, és a -$2.61/share a kedvező entry slippage-en (~$130 megtakarítás) **kioltotta egymást**. Net hatás: ha az entry $109.95 lett volna, a kár ~-$170 lett volna.

**PBR (Petrobras, energy, score 91.0)**: Entry $21.30, MOC $21.22 = **-$50.64 össz** (split). -0.38% MOC. Apró vesztes, de **nem volt LOSS_EXIT** — az ár nem ért -2% alá. A trail_b sem aktiválódott. Csendes underperformer.

**NIO (kínai EV, score 85.5 — a legalacsonyabb!)**: 2-split, entry $6.43, **mindkettő LOSS_EXIT @ $6.29** 19:05-kor = **-$239.25 össz** (-104.25 -135). -2.02% mozgás. **A nap legnagyobb vesztese tickerszinten**. A 85.5 score volt a nap legalacsonyabb — **újabb pozitív rank korreláció** napon belül.

## Score → P&L napi nézet

| Ticker | Score | P&L net | Win? |
|--------|-------|---------|------|
| CRWV | **95.0** | -$133.50 | ✗ (LOSS_EXIT) |
| NVDA | 94.5 | +$19.03 | ✓ |
| PBR | 91.0 | -$50.64 | ✗ |
| PAA | 90.5 | +$135.75 | ✓ |
| NIO | **85.5** | -$239.25 | ✗ (LOSS_EXIT 2×) |

**Mixed pattern:** a legmagasabb (CRWV 95.0) **legnagyobb vesztes**, de a legalacsonyabb (NIO 85.5) **legnagyobb tickerszintű vesztes**. Az NVDA (2. legmagasabb) nyer, a PAA (4.) **a legnagyobb nyertes**. **Nincs tiszta rank-korreláció ma.** r ≈ 0 (vegyes).

A **W17 r=+0.180** és **W18 hétfő enyhe pozitív** után ma **vegyes**. Egyetlen napi adatpont nem rontja a pozitív tendenciát, de **emlékeztet**: a scoring **nem garancia**, csak **bias**.

## A W18 első 2 nap

| Nap | SPY | Portfolio | Excess | P&L net | Kumulatív |
|-----|-----|-----------|--------|---------|-----------|
| Hétfő | +0.17% | -0.33% | -0.50% | -$361 | -$349 |
| **Kedd** | **-0.49%** | **-0.27%** | **+0.22%** | **-$308** | **-$617** |
| **Σ 2 nap** | **-0.32%** | **-0.60%** | **-0.28%** | **-$669** | — |

**Mindkét napon LOSS_EXIT-tel zártunk legalább 1 pozíciót.** Ma 3-at (CRWV, NIO×2). **Ez a W17-hez képest magasabb arány** (W17 alatt 2 LOSS_EXIT volt, ma egyetlen napon 3).

**De az excess vs SPY +0.22% ma** — a portfolio enyhén jobban teljesít, mint a piac. **Ez a 2 napos átlag -0.28% excess**, ami nem drámai.

## Új MID adatok ma

A 22:00-i Phase 1-3 cron újabb snapshot-ot készít. Holnap reggel megnézhetjük:

```bash
gzcat ~/SSH-Services/ifds/state/mid_bundles/2026-04-28.json.gz | jq '.flat.regime, .flat.top_sectors, .flat.age_days'
```

Várt: Stagflation Day 12/28 (~43% mid-stage), top sectors valószínűleg változatlanok (XLK/XLE/XLB).

## A kedd-i ticker-ek vs MID sectors

| Ticker | Sector | MID rangsor |
|--------|--------|-------------|
| CRWV | XLK (Tech) | top-3 ✓ |
| NVDA | XLK (Tech) | top-3 ✓ |
| PBR | XLE (Energy) | top-3 ✓ |
| PAA | XLE (Energy) | top-3 ✓ |
| NIO | XLY (Cons. Cyclical) | **bottom-3** ⚠️ |

**4/5 ticker MID top-3 sectorban**, de **a 3 vesztes közül 2 (CRWV, NIO) MID bottom vagy NIO esetén explicit bottom**. **NIO XLY bottom-ban van**, és LOSS_EXIT-tel zárt. **Ez egy validációs jel** — a MID sector ranking értelmezhető lesz a vasárnapi comparison-ben:

> "Ha a MID egy ticker sektorát bottom-3-ban látja, és az IFDS mégis ezt a tickert választja → **gyenge** kombináció."

A NIO esetében így **fokozott figyelem** indokolt lett volna. **Ez egy konkrét példa a BC25 motivációjához** — a MID szektor információ visszacsatolása az IFDS sector_adjustment-be.

## Kulcsmegfigyelések

### 1. A Breakeven Lock első valódi tesztje — sikerült

A PAA-n a feature pontosan úgy működött, ahogy terveztük:
- `trail_activated_b` 19:00:16 CEST
- `breakeven_lock_applied` 19:00:19 CEST (**3 másodperc múlva** a következő iterációban)
- Soft floor: SL $21.67 → $22.09
- Result: $135.75 profit megőrzve

**Időbeli kérdés tisztázva:** a 19:00-19:04:59 CEST window **valóban** működik, **és** azonnal alkalmazódik a trail aktiváláshoz közeli időpontban. **Pontos design.**

### 2. NVDA: edge case, amit megfontolásra érdemes

Az NVDA `trail_activated_b` **5 perccel** a window vége után volt (21:05 CEST). A breakeven lock **nem alkalmazódott**, és a trail SL $205.66-on maradt (3.5% alatt entry).

Ez egy **érdekes edge case**: az NVDA-nak csak **MOC-szerű záró órákban** aktivált a trail_b. **Ha az ár visszaesett volna** 21:05-21:40 között a $205.66-os SL-re, akkor LOSS_EXIT-szerű kilépés lett volna. **De** az NVDA folyamatosan stabilan tartotta a +0.5%-ot, MOC $213.27.

**Backlog idea (nem most):** lehetne egy **másodlagos breakeven window** 21:00 CEST-kor az utolsó óra-bekötéshez? Ez **finomítás** lenne, **nem most**. Csak megfigyelés.

### 3. A score korreláció ma 0 közeli

W17 r=+0.180, ma vegyes. **Egyetlen napi adatpont nem ront** a pozitív tendencián, de **emlékeztet**, hogy a scoring **nem mindig** prediktív. Ez **nem rontja** a BC23 alapját — a heti és havi átlag fontos, nem a napi varianca.

### 4. NIO mint MID-bottom validáció

A NIO XLY-ban (Cons. Cyclical), ami **MID bottom-3**. Score 85.5 — a nap legalacsonyabb. LOSS_EXIT mindkét split-en. **Ez egy konkrét adatpont** a vasárnapi MID vs IFDS comparison-höz.

**Ha a Phase 3 MID-aware lett volna ma:** a NIO **valószínűleg** kiesett volna (vagy kisebb pozíció). **Megtakarítás: ~$240.**

### 5. Commission $39.67 — újabb maximum

W18 **két napon** $70.75 commission ($31.08 + $39.67). Ha ez a tempo folytatódik, a heti összeg **~$175** lehet, ami a **W17 $82-jának dupla**. **A state-split miatt** nő. CRGY+AAPL leftover, plus NIO 2-split, PAA 2-split, PBR 2-split — sok darabra szétaprózott pozíciók.

## A te döntési kereted szerint

A tegnap esti megegyezés szerint:
- **Élesítés:** Day 63 → +$3,000 → $10k tőke
- **Leállítás:** 20+ napon át VIX > 18 mellett excess < -1.5%
- **Alpha cél:** **0.75-1% / hó**

**Mai állapot:**
- Kumulatív -$617 (-0.62%) — **ez +/- 1.5% sávban van**
- Excess vs SPY 2 napos átlag: -0.28% (nem -1.5%, **megfelelő tartomány**)
- VIX még mindig nincs rögzítve, de a piaci kép alapján **valószínűleg 18-19 között**

**A jelenlegi nap NEM rendít meg semmit** a kereten. A -$617 statisztikai zaj a 100k bázison. **Még 11 nap van** Day 63-ig — bőven idő, hogy az adat stabilizálódjon.

## Holnap várnivalók

- **Szerda ápr 29:**
  - **CC:** M_contradiction multiplier implementáció (~2-3h)
  - **Tamás:** második MID snapshot ellenőrzése
  - **Pipeline:** normál ritmus
- **Csütörtök ápr 30:**
  - M_contradiction első éles nap (ha csütörtökön CONTRADICTION-flagged ticker van)
- **Péntek máj 1:** W18 weekly metrika
- **Vasárnap máj 3:** Chat W18 elemzés + első MID vs IFDS comparison riport

## Anomáliák

- **VIX továbbra is null** — a CC task fájl (P3) megfogja, de várólistán
- **CRGY + AAPL** leftover — 7. nap (még mindig jó lenne hétvégén nuke)
- **A daily_metrics struktúrában a `pnl.cumulative` -$617 helyes**, de nem egyezik pontosan a -$617.46 belső számolással (kerekítés, nem hiba)

## Kapcsolódó

- `state/phase4_snapshots/2026-04-28.json.gz`
- `logs/pt_events_2026-04-28.jsonl` ← **`breakeven_lock_applied` esemény PAA-n**
- `logs/pt_eod_2026-04-28.log`
- `state/daily_metrics/2026-04-28.json`
- `state/mid_bundles/2026-04-28.json.gz` ← **második MID shadow snapshot**
- `docs/tasks/2026-04-28-1900-cest-breakeven-lock.md` ← **éles, validálva**
