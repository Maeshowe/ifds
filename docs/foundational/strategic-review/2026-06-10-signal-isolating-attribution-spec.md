# Jel-izoláló attribúciós teszt — specifikáció

**Dátum**: 2026-06-10 (Day 17) · **Jelleg**: a `2026-06-10-edge-audit.md` §4.2/3
attribúciós tesztjének kiegészítése (NEM helyettesítése) · **Státusz**:
pre-regisztrált spec, Day 63 (~2026-08) és Day 126 (~2026-09-15) kötelező input ·
**Freeze-kompatibilis**: mérés/tracking, NEM kereskedési-viselkedés (§4.2/1)

---

## 0. A probléma egy mondatban

A §4.2/3 `ρ(S_j, realized_R)` azt méri, **megkerestük-e a pénzt** — de NEM azt,
hogy **a jel megjósolta-e a mozgást**. A `realized_R` az exit-policy (TP1 /
TIME_STOP MOC / mental stop) által *elkapott* hozam, ezért két, fizikailag
független dolgot confound-ol: (i) a jel prediktív erejét és (ii) az exit-réteg
elkapó/levágó hatását. Mivel az edge-audit az exit-réteget *erősnek*, a jelet
*kérdésnek* minősíti, a kettőt szét KELL választani — különben Day 126-on a
„mit mértünk" kérdésre confound-olt választ kapunk.

## 1. Kétszintű izoláció

A teszt **három** korrelációt számol minden lezárt swing-ügyletre, növekvő
izolációs szinttel:

| Szint | Mérőszám | Mit mér | Mit izolál |
|---|---|---|---|
| **L0** (a meglévő §4.2/3) | `ρ(S_j, R_realized)` | „megkerestük-e a pénzt" | semmit — exit + piac + szektor + jel együtt |
| **L1 — exit-izoláció** | `ρ(S_j, R_fixed(h))` | a jel nyers prediktív ereje a *szándékolt* horizonton | kiveszi az exit-policy-t |
| **L2 — szelekció-izoláció** | `ρ(S_j, R_fixed_resid(h))` | **stock-szelekciós alpha** | kiveszi az exit-policy-t ÉS a piac/szektor driftet |

Az **L2 a tényleges válasz a §3 routing kérdésére** („a stock-szelekciós jel
termel-e"), mert a stock-selection alpha **definíció szerint** a szektor/piac
által meg NEM magyarázott reziduum. (Ez fedi le a §6/4 csapdát: „ne fogadd el a
pozitív P&L-t a jel bizonyítékaként" — az L0/L1 lehet pozitív tisztán a piaci
rebound miatt; az L2 nem.)

## 2. Per-ügylet hozam-definíciók

Jelölés: egy lezárt ügylet `i` = (ticker `t_i`, entry-fill ár `P_i^0`,
entry-dátum `d_i`, entry-score `S_i`, exit-típus `e_i`, realizált hozam `R_i`).

### 2.1 L1 — fix-horizontú forward return (exit-független)

A `P_i^0` entry-fillből, Polygon **napi bar close**-okból, NEM a valós exitből:

```
R_fixed_i(h) = (close[t_i, d_i + h NYSE-nap] / P_i^0) − 1
```

`h ∈ {1, 3, 5}` NYSE trading nap (5 = a time-stop horizont; a pivot-tézis szerint
a jel `h=5`-nél erősebb, mint intraday — ez közvetlenül tesztelhető a horizont-
profilból). Ha a ticker `d_i + h` előtt delisting/halt miatt nincs bar → az
ügylet az adott `h`-ra kihagyva (logolva).

### 2.2 L2 — szektor-reziduális forward return (szelekció-izoláció)

Minden `h`-ra, kétféle benchmark-levonás (mindkettő riportolandó):

**(a) szektor-relatív** (elsődleges — konzisztens a Phase 3 szektor-réteggel):
```
R_fixed_resid_i(h) = R_fixed_i(h) − R_sectorETF[sec(t_i), d_i → d_i+h]
```
ahol `sec(t_i)` a ticker GICS-szektora, a benchmark a megfelelő SPDR szektor-ETF
(XLK/XLF/XLV/...) ugyanazon `[d_i, d_i+h]` ablakra (Polygon).

**(b) béta-korrigált** (másodlagos, robusztusság):
```
R_fixed_resid_i(h) = R_fixed_i(h) − β_i · R_SPY[d_i → d_i+h]
```
`β_i` = a ticker 60-napos napi-hozam regressziós bétája SPY-ra az entry ELŐTT
(look-ahead nélkül; ha <40 bar elérhető → β=1.0 fallback, logolva).

> **Miért szektor-relatív az elsődleges**: a swing-könyv szándékosan szektor-
> rotált (Phase 3), így a stock-szelekciós alpha = a szektoron-belüli relatív
> teljesítmény. A béta-korrekció a piac-szintű driftet veszi ki, de a szektor-
> tiltást nem — ezért másodlagos.

## 3. Statisztika (mindhárom szintre, minden `h`-ra)

1. **Pearson `ρ_P`** és **Spearman `ρ_S`** (`S_i` vs a hozam-mérőszám). A
   Spearman elsődleges az L1/L2-n (robusztus a fat-tail forward-return outlierekre
   és a nem-lineáris monotón jelre).
2. **95% CI** Fisher-z transzformációval mindkét ρ-ra.
3. **Exit-típus stratifikáció** (csak L0-n értelmes, de diagnosztikus): `ρ(S_j, R_realized)`
   külön a TP1 / TIME_STOP_MOC / mental-stop alcsoportokon — megmutatja, ha az L0
   korreláció egyetlen exit-módból jön (pl. csak a TP1-ek korrelálnak → a jel a
   TP1-küszöböt jelzi, nem a tartós mozgást).
4. **Kvintilis-monotonitás (L2-n)**: az ügyleteket `S_i` kvintilisbe sorolva,
   kvintilisenként az `R_fixed_resid(5)` átlaga + SE. **Monoton növekvő** minta
   erősebb evidencia, mint egyetlen ρ (elkapja a nem-lineáris, de monoton jelet,
   amit a Pearson elnyomna). Day 63-on tájékoztató, Day 126-on értelmezhető.

## 4. Értelmezési küszöbök (a power-táblához kötve, App A)

A küszöbök NEM mozognak az adat után. `n` = lezárt exit-szám.

| Horizont | n (becsült) | L1/L2 detektálható |ρ| | Olvasat |
|---|---|---|---|
| Day 63 | ~50–60 | ≥0.36–0.38 | **csak irány** (kis/közepes effekt nem látszik) |
| Day 126 | ~100–110 | ≈0.27 | első érdemi olvasat |
| Day 180 pooled | ≥180 | ≈0.21 | kis-közepes effekt |

**Routing-szabály (az edge-audit §3 + §4.3 kiegészítése, az L2 a döntő):**

| L2 `ρ_S(5)` 95% CI (Day 126) | Kumulatív P&L | Routing |
|---|---|---|
| 0-t kizárja, pozitív | bármi pozitív | **swing-tézis megerősítve** → (a) folytatás, skálázás |
| tartalmazza a 0-t | pozitív | **(b) ág evidencia**: a hordozó/risk/szektor termel, a stock-jel NEM → MID regime-overlay |
| tartalmazza a 0-t / negatív | negatív v. null | **(c) ág evidencia**: PCR/OTM stock-jel ebben a formában nem él |

A kulcs: **L0 pozitív + L2 ≈ 0 → a (b) ág** (nem a stock-jel termel, hanem a
hordozó). Ezt az L0 egyedül NEM tudja megkülönböztetni a valódi jeltől.

## 5. Adatrögzítési előfeltétel — MOST ellenőrizendő (kritikus)

A teszt Day 63-on **lefuttathatatlan**, ha a per-ügylet `S_i` (entry combined_score)
NINCS perzisztálva minden lezárt ügylethez. Ezért a freeze-ablakban (tracking-fix,
megengedett) verifikálni kell, hogy minden lezárt swing-ügylethez tárolva van:
**`entry_score (S_j)`, `entry_fill_price`, `entry_date`, `ticker`, `sector`,
`exit_type`, `realized_pnl`, `qty`**. Ha az `entry_score` nincs a trade-rekordban
(swing_positions / pending_exits ledger / daily_metrics) → **most pótolandó**,
mert visszamenőleg nem rekonstruálható megbízhatóan (a Phase 4 snapshot a score-t
tartja, de a ledger a kötés-azonosítást). Ez a #1 prioritás (lásd „következő lépés").

## 6. Implementáció

- **Script**: `scripts/analysis/signal_attribution.py` (read-only, analízis;
  semmit nem ír a trading state-be). Bemenet: a lezárt swing-ügyletek (ledger +
  Phase 4 snapshot a score-hoz) + Polygon napi bar-ok (ticker, szektor-ETF, SPY).
  Kimenet: `docs/analysis/signal-attribution-{date}.md` (L0/L1/L2 ρ-k, CI-k,
  stratifikáció, kvintilis-tábla, horizont-profil).
- **Tesztelhetőség most**: mock per-trade + mock bar adatokkal unit-tesztelhető
  (a Pearson/Spearman/Fisher-z/szektor-levonás/kvintilis logika), így Day 63-ra
  **bizonyítottan helyes** eszköz áll készen — n itt még 14, valós futás Day 63.
- **Freeze**: az egész mérés/tracking → §4.2/1 alatt megengedett.

### 6.1 Data-loader rögzítés (a wiring ELŐTT — ne improvizáljon CC)

Három invariáns, amit a loadernek be kell tartania (Chat, 2026-06-18):

1. **`entry_score` (S_j) hiány-kezelés.** `entry_score <= 0` → hiányzó érték →
   **snapshot-recovery** az adott ticker/dátumra (`recover_entry_score`). Ha a
   Phase 4 snapshot sem adja → a trade **kizárva** a mintából (exclusion-listával
   riportolva). A 6 örökölt pozíció `default-0.0` sentinelje **NEM valós score** —
   ez ne szivárogjon a ρ-ba.
2. **Exit-típus forrása kizárólag `state/pending_exits/{date}.json`** (a
   broker-autoritatív ledger). A `daily_metrics::exit_type` a P1-fixig
   megbízhatatlan (fill-timestamp-alapú) — a stratifikáció (L0/L1/L2 exit-bontás)
   **ebből** olvasson, ne a daily_metrics mezőből.
3. **Read-only + kettős minta-output.** A loader semmit nem ír a trading state-be.
   Két mintát ad, a §4.2/2-vel illeszkedve: (a) **teljes Day 1–63** és (b) **Day 9+
   clean-sample** (a korai napi-tracking torzítások után). Mindkettő külön ρ/CI.

## 7. Korlátok (őszinteség)

- A fix-horizontú forward return **nem azt méri, amit kerestünk** (a valós exit
  korábban/máshol zár) — ez szándékos: a *jel* tiszta erejét méri, nem a stratégiáét.
  Az L0 és L1 EGYÜTT olvasandó (L0 = stratégia, L1 = jel, L1−L0 különbség = exit-érték).
- `h=5` fix horizont nem fedi a változó tartási időt; ezért riportoljuk h∈{1,3,5}
  profilt, nem egyetlen számot.
- Day 63-on minden szint csak IRÁNY (power < a kis effektre). A spec ezt expliciten
  rögzíti, hogy szeptemberben ne lehessen „majdnem szignifikáns"-ként olvasni.

## 8. Öt fegyelem-pont (az edge-audit §4.2/3a-ból)

1. **Egyetlen, előre rögzített elsődleges döntési metrika**: **L2 Spearman, h=5,
   szektor-relatív**. A többi szint/horizont/Pearson DIAGNOSZTIKUS — a routing-ot
   (§4) kizárólag ez vezeti. (Nincs „válaszd a legszebb ρ-t" szabadság.)
2. **A stratifikáció (exit-típus szerint) csak LEÍRÓ**, nem döntési alap — annak
   diagnózisa, hogy az L0 korreláció egyetlen exit-módból jön-e.
3. **Kettős minta-output, mindig együtt riportolva**: a teljes Day 1–63 (hivatalos,
   bug-torzítással) ÉS a Day 9–63 (tiszta architektúra). Ha csak a tiszta teljesít,
   az NEM élesítési alap, hanem a DEFAULT-ág melletti érv (konzisztens az audit §4.2/2-vel).
4. **A commit = pre-regisztrációs zár**: a metrika-választás, a küszöbök és a
   minta-definíciók az ADAT ELŐTT, ezzel a commit-tal rögzülnek. Utólag szigorítani
   legitim, lazítani nem.
5. **A smoke-run kötelező címkéje**: `PLUMBING VALIDATION ONLY — NOT EVIDENCE`
   (n < 40 esetén automatikus a render-ben). Az n=14-es mai futás a pipeline-t
   validálja, NEM a jelet — a Day 126 kapu-kritériumok érintetlenek.
