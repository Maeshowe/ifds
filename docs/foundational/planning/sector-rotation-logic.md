# IFDS — Sector Rotation Logika

**Fájl:** `src/ifds/phases/phase3_sectors.py`  
**Utolsó frissítés:** 2026-03-18

---

## 1. Áttekintés

A Phase 3 célja: meghatározni, hogy az egyes szektorok **pénzbeáramlásban (inflow)
vagy kiáramlásban (outflow)** vannak-e, és ennek alapján szűrni az egyedi
részvény-universe-t (Phase 4 bemenete).

A rendszer 11 SPDR szektor ETF-et elemez:

| ETF | Szektor |
|-----|---------|
| XLK | Technology |
| XLF | Financials |
| XLE | Energy |
| XLV | Healthcare |
| XLI | Industrials |
| XLP | Consumer Defensive |
| XLY | Consumer Cyclical |
| XLB | Basic Materials |
| XLC | Communication Services |
| XLRE | Real Estate |
| XLU | Utilities |

Benchmark: **AGG** (kötvény ETF) — relatív teljesítmény mérése ellen.

---

## 2. Mennyi pénz áramlott be/ki egy ETF-ből egy nap?

### 2.1. Az alapgondolat

Egy ETF esetében a **napi tőkeáramlás (flow)** nem triviálisan olvasható le az
árfolyamból, mert az ETF ára akkor is változik, ha a bennlévő részvények
(a "kosár") mozog. Az igazán releváns kérdés:

> **Vásároltak-e többet az ETF-ből mint amennyit eladtak?**
> Azaz: nettó új tőke áramlott be, vagy a meglévő befektetők kivonulnak?

### 2.2. Közelítés 1 — AUM változás (napi flow proxy)

Az ETF-ek esetén a legpontosabb flow-mérés az **AUM (Assets Under Management)**
napi változása, korrigálva az árfolyamváltozással:

```
Flow_nap = AUM_ma - AUM_tegnap × (Ár_ma / Ár_tegnap)
```

**Értelmezés:**
- Ha az ETF 2%-ot emelkedett ÉS az AUM is pontosan 2%-kal nőtt → **nulla flow**
  (csak az árfolyamváltozás okozta az AUM növekedést, nem új tőke)
- Ha az AUM 5%-kal nőtt, de az ár csak 2%-kal → **pozitív flow** (új tőke áramlott be)
- Ha az AUM nem nőtt, de az ár 2%-ot emelkedett → **negatív flow** (kivonás volt)

**Képlet részletesen:**

```
Shares_outstanding_ma  = AUM_ma / NAV_ma
Shares_outstanding_tegnap = AUM_tegnap / NAV_tegnap

Flow_részvények = Shares_outstanding_ma - Shares_outstanding_tegnap
Flow_USD        = Flow_részvények × NAV_ma
```

Az outstanding shares változása közvetlenül megmutatja a nettó creation/redemption
aktivitást (az ETF mechanizmus lényege).

### 2.3. Közelítés 2 — Volume-alapú proxy (IFDS jelenlegi módszer)

Ha az AUM napi adatok nem érhetők el, a **volume × ár** közelítést alkalmazzuk:

```
Dollar_volume = volume × close_ár
```

Ez nem pontosan a flow, hanem a forgalom — de magas dollar volume erős
intézményi érdeklődést jelez. Az IFDS jelenleg ezt a megközelítést alkalmazza
az 5 napos momentum számítás kiegészítéseként.

### 2.4. Közelítés 3 — Unusual Whales ETF flow API (BC23 scope)

Az UW API `get_etf_in_outflow()` endpointja direkt napi flow adatot ad:

```python
# UW API endpoint (BC23 Phase_23A)
flow = uw_client.get_etf_in_outflow(etf="XLE", date="2026-03-18")
# Visszaad: {"inflow": 245_000_000, "outflow": 87_000_000, "net_flow": 158_000_000}
```

Ez a legpontosabb módszer — a BC23 scope-ban tervezett implementáció.

---

## 3. Jelenlegi IFDS implementáció — lépésről lépésre

### 3.1. Adatgyűjtés (Polygon API)

```python
# Lookback: max(5, 20) + 15 = 35 naptári nap
# Endpoint: /v2/aggs/{ticker}/1/day/{from}/{to}
bars = polygon.get_aggregates(etf, from_date, to_date)
closes = [b["c"] for b in bars]
```

Minden ETF-re lekérjük az utolsó ~35 naptári nap OHLCV adatát.

### 3.2. Momentum számítás (5 napos relatív teljesítmény)

```
Momentum_5d = (Close_ma - Close_5_napja) / Close_5_napja × 100
```

**Példa (2026-03-18):**

| ETF | Close_ma | Close_5_napja | Momentum |
|-----|----------|---------------|----------|
| XLE | 94.23 | 89.47 | **+5.32%** |
| XLU | 68.11 | 67.29 | **+1.22%** |
| XLK | 232.45 | 232.83 | **−0.16%** |
| XLC | 85.67 | 87.12 | **−1.67%** |

Az 5 napos ablak elegendő a rövid távú rotációs dinamika megragadásához,
de nem reagál túl zajosan az egynapos kilengésekre.

### 3.3. Trend meghatározás (SMA20)

```
Trend = UP  ha Close_ma > SMA20
Trend = DOWN ha Close_ma ≤ SMA20
```

Az SMA20 az utolsó 20 kereskedési nap záróárának egyszerű átlaga.

### 3.4. Rangsorolás és besorolás

Az ETF-ek 5 napos momentum szerint csökkenő sorrendbe kerülnek:

```
Top 3 (leader_count=3)      → LEADER    (+15 score adjustment)
Középső 5                   → NEUTRAL   (0)
Bottom 3 (laggard_count=3)  → LAGGARD   (−25 penalty)
```

### 3.5. Szektor BMI rezsim

A Sector BMI (Big Money Index szektor szinten) a szektor részvényeinek
vételi/eladási arányát méri. Küszöbértékek ETF-enként:

```python
# config.tuning["sector_bmi_thresholds"]
{
  "XLE": (12, 80),   # oversold < 12%, overbought > 80%
  "XLK": (15, 75),
  ...
}
```

Három rezsim: `OVERSOLD` | `NEUTRAL` | `OVERBOUGHT`

### 3.6. Veto Matrix (LONG stratégia)

| Momentum | BMI Rezsim | Döntés | Score adj |
|----------|-----------|--------|-----------|
| LEADER | Bármely | ✅ ENGEDÉLYEZETT | +15 |
| NEUTRAL | NEUTRAL | ✅ ENGEDÉLYEZETT | 0 |
| NEUTRAL | OVERSOLD | ✅ ENGEDÉLYEZETT | 0 |
| NEUTRAL | OVERBOUGHT | ❌ VETO | — |
| LAGGARD | OVERSOLD | ✅ Mean Reversion | −5 |
| LAGGARD | NEUTRAL | ❌ VETO | — |
| LAGGARD | OVERBOUGHT | ❌ VETO | — |

A vetózott szektorok részvényei kiesnek a Phase 4 elemzésből.

### 3.7. Sector Breadth (BC14 — MAP-IT)

A breadth-analízis a szektor alkotóelemeinek (holdings) egészségét méri:

```
Breadth_score = 0.20 × %_above_SMA20
              + 0.50 × %_above_SMA50
              + 0.30 × %_above_SMA200
```

**Rezsim besorolás** (SMA50 × SMA200 mátrix):

| SMA50 | SMA200 | Rezsim |
|-------|--------|--------|
| >70% | >70% | STRONG |
| >70% | 30–70% | EMERGING |
| 30–70% | >70% | CONSOLIDATING |
| 30–70% | 30–70% | NEUTRAL |
| <30% | 30–70% | WEAKENING |
| <30% | <30% | WEAK |
| >50% | <30% | RECOVERY |

**Divergencia detektálás:**
- **Bearish divergencia:** ETF +5 napos mom > +2% ÉS breadth_momentum_SMA50 < −5 pont
- **Bullish divergencia:** ETF +5 napos mom < −2% ÉS breadth_momentum_SMA50 > +5 pont

Bearish divergencia esetén: −10 score adjustment a szektorra.

---

## 4. Napi output — amit a pipeline log mutat

```
ETF   MOMENTUM STATUS   TREND  BMI  REGIME   B.SCR  B.REGIME   VETO
XLE   ^ +5.23%  Leader  UP     55%  NEUTRAL   91    STRONG
XLU   ^ +1.22%  Leader  UP     52%  NEUTRAL   88    STRONG
XLK   v -0.16%  Leader  DOWN   53%  NEUTRAL   39    NEUTRAL
XLC   v -1.71%  Laggard DOWN   50%  NEUTRAL   35    NEUTRAL    YES
```

- **MOMENTUM:** 5 napos relatív teljesítmény
- **STATUS:** Leader / Neutral / Laggard
- **TREND:** UP (ár > SMA20) / DOWN (ár < SMA20)
- **BMI:** Szektor Big Money Index % értéke
- **REGIME:** NEUTRAL / OVERSOLD / OVERBOUGHT
- **B.SCR:** Breadth score (0–100)
- **B.REGIME:** STRONG / EMERGING / NEUTRAL / WEAKENING / WEAK stb.
- **VETO:** Ha igen, a szektor részvényei kiesnek Phase 4-ből

---

## 5. Valós példa — 2026-03-18

Az iráni konfliktus / Hormuzi-szoros blokád hatása jól látható:

```
XLE  +5.23%  Leader   → Energy: háborús prémium, olaj $94+/hordó
XLU  +1.22%  Leader   → Utilities: defenzív rotáció, befektetők menekülnek
XLK  −0.16%  Leader   → Tech: momentum marad, de csökken
XLC  −1.71%  Laggard  → Comm Svc: VETO — eladói nyomás
XLI  −2.07%  Laggard  → Industrials: VETO — supply chain aggodalmak
XLV  −2.29%  Laggard  → Healthcare: VETO — legrosszabb teljesítő
```

**Rotáció iránya:** Cyclical → Defensive + Energy  
**Makro kontextus:** VIX=21.74 (csökkent), BMI=50.3% (YELLOW)

---

## 6. Tervezett fejlesztések

### BC18 — Phase_18A: EWMA Smoothing

Az 5 napos egyszerű momentum helyett EWMA (exponentially weighted):

```python
# span=10 → kb. 10 napos exponenciálisan súlyozott átlag
momentum_ewma = pd.Series(closes).ewm(span=10).mean().iloc[-1]
```

Az EWMA kevésbé érzékeny az egy kiugró napra, simább rotációs jelzést ad.

### BC23 — Phase_23A: Valódi ETF Flow API

Az UW `get_etf_in_outflow()` endpoint integrálása:

```python
# Napi nettó flow dollárban
net_flow = uw.get_etf_in_outflow(etf="XLE", date=today)
# net_flow > 0 → intézményi beáramlás
# net_flow < 0 → intézményi kiáramlás
```

Ez a legpontosabb módszer a "mennyi pénz áramlott be" kérdés megválaszolására
— nem proxy, hanem tényleges creation/redemption adat.

### BC23 — Phase_23B: L2 Szektoros finomítás (42 ETF)

A 11 SPDR ETF mellé 42 al-szektor ETF elemzése (pl. SKYY, HACK, XAR stb.)
a szektoron belüli finomabb rotáció detektálásához.

---

## 7. Összefoglalás — a három módszer összehasonlítása

| Módszer | Pontosság | Elérhetőség | IFDS státusz |
|---------|-----------|-------------|--------------|
| AUM / outstanding shares változás | ★★★★★ | Bloomberg, napi delay | Nem implementált |
| UW ETF inflow/outflow API | ★★★★☆ | UW Pro API | BC23 scope |
| Volume × ár (dollar volume proxy) | ★★★☆☆ | Polygon ingyenes tier | ✅ Aktív (közvetett) |
| 5 napos price momentum | ★★☆☆☆ | Polygon ingyenes tier | ✅ Aktív (elsődleges) |

A jelenlegi rendszer a **price momentum + breadth** kombinációt használja
mint a tőkeáramlás legjobb elérhető proxy-ja. A BC23-tól kezdve a tényleges
UW flow adatok erősítik meg vagy cáfolják a momentum jelzést.
