# Crowdedness Shadow Mode — Döntés-előkészítő anyag

**Dátum:** 2026-03-07
**Státusz:** DÖNTÉS SZÜKSÉGES — BC18A előtt
**Kapcsolódó Phase:** Phase_18A (EWMA + Crowdedness Shadow)
**MMS terminus:** `phase5_mms.py` — `MMSAnalysis`, `MMRegime`, `MMSStore`

---

## Kontextus: mi van már a kódban

Az MMS engine (`phase5_mms.py`) a következő napi adatokat tárolja és méri tickerenként:

| Feature | Mit mér |
|---------|---------|
| `dark_share` | Dark pool % a teljes volume-ból |
| `block_count` | Intézményi block trade-ek száma |
| `dex` | Net Dealer Delta Exposure (call vs put oldal) |
| `gex` | Net Gamma Exposure |
| `iv_rank` | ATM implied volatility |
| `venue_entropy` | Kereskedési helyszínek diverzitása |
| `iv_skew` | Put IV - Call IV (fear proxy) |

Mindezekre **z-score** számolódik 21 napos baseline után, és az **unusualness score** (0-100) ezek súlyozott kombinációja.

Jelenlegi MMS rezsimek (priority-ordered):
- **Γ⁺ (GAMMA_POSITIVE)** — volatility suppression
- **Γ⁻ (GAMMA_NEGATIVE)** — liquidity vacuum
- **DD (DARK_DOMINANT)** — institutional accumulation (dark_share > 0.70 + z_block > +1.0)
- **ABS (ABSORPTION)** — passive absorption (z_dex < -1.0 + return ≥ -0.5% + dark_share > 0.50)
- **DIST (DISTRIBUTION)** — distribution into strength
- **NEU (NEUTRAL)** — no rule matched
- **UND (UNDETERMINED)** — insufficient baseline

---

## Mit jelent a Crowdedness az IFDS kontextusában

**Definíció (Macrosynergy / Conlon, Cotter, Jain):**
A crowded trade olyan pozíció, ahol az aktív intézményi részvétel aránya magas a likviditáshoz képest — ez endogén piaci kockázat, nem fundamentumokból ered. A crowding tipikusan lefelé torzítja a kockázatot (downside skew).

**Az IFDS kérdése:** ha sok intézmény ugyanabba a tickerbe megy dark pool-on keresztül, az nekünk jó vagy rossz jel?

A jelenlegi MMS **nem különbözteti meg** az akkumuláló és a zsúfolt/kiszálló intézményi flow-t — mindkettő magas `dark_share` + `block_count`-ot produkál. A Crowdedness layer ezt a két esetet választja szét.

---

## Good Crowding — Trend erősítő

### Definíció
Koordinált intézményi akkumuláció, ahol a flow iránya megegyezik az árral, és az exit likviditás még elérhető.

### Jellemzők
- Magas `dark_share` (> küszöb) + magas `z_block` (> +1.0) → sok intézmény vásárol
- Emelkedő ár mellett növekvő dark pool aktivitás → akkumuláció, nem disztribúció
- `z_dex` negatív (< -0.5) → dealer short gamma, intézmények nettó vevők
- `iv_skew` alacsony (< median) → nincs fear hedge, az intézmények nem védik magukat
- MMS rezsim: **DD** vagy **ABS** — ezek a Good Crowding természetes megfelelői

### Logika (bővített)
```python
good_crowding = (
    dark_share > threshold          # magas DP jelenlét
    AND z_block > +1.0              # szokatlanul sok block
    AND daily_return > 0            # ár megy felfelé
    AND z_dex < -0.5                # intézmények nettó vevők
    AND iv_skew < median_iv_skew    # nincs fear
)
```

### Szakirodalmi alap
- Man AHL (Man Group): "Crowding may temporarily drive prices in the favour of momentum traders" — a Good Crowding átmenetileg erősíti a trendet
- InsiderFinance: "Heavy dark pool buying + rising call option volume = institutions and speculators aligning"
- Price stays above the dark pool print = akkumuláció (Accumulation pattern)

### Előnyök (IFDS-re)
- Az intézményi flow "húzza" az árat, mi mögé surfölhetünk
- A DD/ABS rezsim már detektálja, a Crowdedness layer finomítja
- Multiplier boost indokolt: az exit likviditás jó, a trend megerősített

### Kockázatok
- Ha az intézményi exit megindul, a kiszállás nehéz (liquidity cliff)
- Momentum crowd → éles visszafordulás valószínű, ha a flow megfordul
- "Quant meltdown" mintázat: sok szereplő szimultán exit → árszakadás (Khandani & Lo, 2011)

---

## Bad Crowding — Zsúfolt trade, exit veszély

### Definíció
Sok intézmény ugyanabban a tickerben van, de a flow iránya divergál az ártól, vagy a likviditás már kimerülőben. Az exit nehéz, a stop könnyen üt.

### Jellemzők
- Magas `dark_share` + `z_block` (crowded), DE az ár NEM emelkedik (vagy esik)
- Magas `iv_skew` → az intézmények put-okkal védekeznek (saját pozíciójukat hedge-elik)
- `z_dex` pozitív (> +0.5) → dealer long gamma, intézmények nettó eladók
- MMS rezsim: **DIST** vagy **VOLATILE** — ezek a Bad Crowding természetes megfelelői
- Unusualness score magas (> 70), de negatív irányban

### Logika (bővített)
```python
bad_crowding = (
    dark_share > threshold          # magas DP jelenlét
    AND z_block > +1.0              # sok block trade
    AND (
        daily_return <= 0           # ár NEM megy fel
        OR z_dex > +0.5             # intézmények nettó eladók
        OR iv_skew > median_iv_skew # fear hedge aktív
    )
)
```

### Szakirodalmi alap
- Macrosynergy (Conlon, Cotter, Jain): "Funds with higher average investment weights in the most crowded stocks experienced more severe drawdowns"
- Man Group: "Crowding into momentum → sharp reversal once prices become dislocated"
- CFA Institute: "Crowded long-leg stocks → institutional crash risk exposure"
- Price stays BELOW the dark pool print = disztribúció (Distribution pattern)

### Kockázatok (IFDS-re)
- Ha mi is ebben a tickerben vagyunk, az exit nehéz és a stop könnyen üt
- A crowded pozíció likvidációja áreltorzulást okozhat (endogén kockázat)
- August 2007 quant crash minta: szimultán exit → mi is veszteséget szenvedünk

---

## Composite Crowdedness Score — javasolt formula

### Skála: [-1.0, +1.0]
```
+1.0 = erős Good Crowding (intézményi akkumuláció, trend erősítő)
 0.0 = semleges / nincs crowding
-1.0 = erős Bad Crowding (zsúfolt, exit veszély)
```

### Python implementáció (javaslat)
```python
def compute_crowding_score(
    dark_share: float,
    z_block: float | None,
    z_dex: float | None,
    iv_skew: float,
    median_iv_skew: float,
    daily_return: float,
    threshold_high: float = 0.45,   # ← DÖNTÉS SZÜKSÉGES
) -> float:
    """
    Crowdedness composite score ∈ [-1.0, +1.0].
    Shadow mode-ban logolódik, de sizing-ot NEM módosít.
    """
    if dark_share < threshold_high or z_block is None or z_block < 0.5:
        return 0.0  # nem elég crowded ahhoz, hogy számítson

    # Direction score: +1 ha akkumuláció, -1 ha disztribúció
    direction = 0.0
    if z_dex is not None:
        direction -= z_dex * 0.4        # negatív dex = Good Crowding
    direction += daily_return * 20       # pozitív return = Good (cap ±1)
    direction = max(-1.0, min(1.0, direction))

    # Fear score: magasabb iv_skew = rosszabb (Bad Crowding jele)
    fear = (iv_skew - median_iv_skew) * 5
    fear = max(-1.0, min(1.0, fear))

    # Crowd intensity: mennyire zsúfolt
    intensity = min(1.0, (dark_share - threshold_high) / 0.3 + z_block / 3.0)

    # Composite: direction vezet (60%), fear korrigál (40%), intensity skáláz
    raw = (direction * 0.6 - fear * 0.4) * intensity
    return max(-1.0, min(1.0, raw))
```

### Értelmezési tábla
| Score | Minősítés | IFDS akció (élesítés után) |
|-------|-----------|---------------------------|
| > +0.5 | Erős Good Crowding | multiplier boost (+10-15%) |
| +0.2 .. +0.5 | Mérsékelt Good | semleges / enyhe boost |
| -0.2 .. +0.2 | Semleges | nincs hatás |
| -0.2 .. -0.5 | Mérsékelt Bad | multiplier penalty (-10%) |
| < -0.5 | Erős Bad Crowding | kiszűrés VAGY erős penalty |

---

## MMS rezsim ↔ Crowdedness megfeleltetés

| MMS Rezsim | Várható Crowdedness | Magyarázat |
|------------|---------------------|------------|
| DD (Dark Dominant) | Good (+0.5..+1.0) | Tipikusan akkumuláció |
| ABS (Absorption) | Good (+0.3..+0.8) | Passív vétel, intézmény vevő |
| DIST (Distribution) | Bad (-0.5..-1.0) | Intézmény elad dark pool-on |
| VOLATILE | Bad (-0.3..-0.8) | Magas σ, bizonytalan irány |
| Γ⁺ (Gamma Positive) | Semleges | GEX domináns, crowd nem releváns |
| Γ⁻ (Gamma Negative) | Bad (-0.2..-0.6) | Liquidity vacuum, exit nehéz |
| NEU | Semleges (0.0) | Nincs crowding jel |

---

## Shadow Mode — hogyan működik

A shadow mode azt jelenti: a score **számolódik és logolódik**, de a Phase 6 sizing-ot **még nem módosítja**. 2 hétig gyűjtjük az adatot, aztán Phase_18A-ban döntünk az élesítésről.

**Log output (shadow, napi):**
```
[MMS Shadow] AAPL: crowding_score=+0.72 (GOOD) dark=0.61 z_block=+1.8 z_dex=-0.9 iv_skew=below_median
[MMS Shadow] NVDA: crowding_score=-0.55 (BAD)  dark=0.58 z_block=+2.1 z_dex=+1.3 iv_skew=elevated
[MMS Shadow] META: crowding_score=0.00 (NEUT)  dark=0.31 — below threshold
```

---

## ❓ Döntési pontok (Tamás válasza szükséges)

### 1. dark_share küszöb
A jelenlegi MMS DD küszöb: `dark_share > 0.70`
A Crowdedness shadow-hoz korábbi detektálás kell:

| Opció | Érték | Hatás |
|-------|-------|-------|
| **A** | `> 0.45` | Korán detektál, több ticker, shadow-ban biztonságos |
| **B** | `> 0.55` | Konzervatívabb, csak valóban crowded tickerek |
| **C** | `> 0.60` | Közel a DD küszöbhöz, legkevesebb false positive |

### 2. Bad Crowding élesítés utáni hatása (Phase_18A-ban)
| Opció | Leírás | Trade-off |
|-------|--------|-----------|
| **A — Kiszűrés** | score < -0.5 → ticker nem kerül execution planbe | Agresszív, de tiszta |
| **B — Penalty** | Multiplier csökken (×0.5), de a ticker bennmarad | Mérsékelt, megőrzi a flexibilitást |
| **C — Mindkettő** | Erős bad (< -0.7) kiszűr, közepes (-0.3..-0.7) penaltyzik | Legfinomabb, de komplexebb |

### 3. Good Crowding boost mértéke és viszonya az MMS multiplierhez
| Opció | Leírás |
|-------|--------|
| **A — Additív** | Crowdedness boost az MMS multiplier mellé (+0.1..+0.15) |
| **B — Override** | Crowdedness felváltja az MMS multiplier egy részét |
| **C — Csak Bad oldal** | Good Crowdingnál nincs boost, csak Bad oldal penaltyzik |

---

## Ajánlás (Chat véleménye)

- **dark_share küszöb:** `> 0.55` (B) — elég korai detektálás, kevesebb zaj
- **Bad Crowding hatás:** Opció C (Mindkettő) — a gradiens megközelítés illeszkedik az MMS filozófiájához
- **Good boost:** Opció A (Additív) — az MMS multiplier rendszer ne sérüljön, a Crowdedness legyen réteg felette

De ezek a döntések Tamásé — a shadow adatok 2 hét múlva árnyalhatják a preferenciát.
