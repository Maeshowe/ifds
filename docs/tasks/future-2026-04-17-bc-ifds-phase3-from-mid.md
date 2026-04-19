# BC (future) — IFDS Phase 3 ← MID ETF X-Ray consumption

**Status:** PLANNED — nem indítható, amíg a MID BC-ETF-Xray-Institutional-13F-Layer legalább Phase B nincs kész
**Created:** 2026-04-17
**Priority:** P3 — hosszabb távú integráció, nem a legközelebbi ciklus része
**Estimated effort:** ~2 nap (IFDS oldali)

---

## Kontextus

Az IFDS Phase 3 (sector rotation) jelenleg **saját szektor momentum számítást** végez (ETF price return + relative strength SPY-hoz). Ez működik, de:

1. **Redundáns** a MID ETF X-Ray CAS-szel — ugyanazt a kérdést két helyen számoljuk
2. **Korlátozott** — csak price momentum, nincs 13F institutional layer
3. **Szektor VETO** jelenleg napi momentum alapján dönt, a strukturális intézményi pozicionálást nem nézi

A MID ETF X-Ray **jelenleg** a CAS-szel ezt már jobban megadja. Ha a MID `BC-etf-xray-institutional-13f-layer` elkészül, a Phase 3 input **4 dimenzióssá** válik (Flow CAS + 13F weight + trajectory + constituent buckets).

## Függőség — mire vár ez a BC

Az IFDS oldali integráció **akkor indulhat**, amikor a MID BC legalább:

- **Phase A** (foundation) kész → minimum ETF CAS a MID API-n elérhető (ez már most is igaz!)
- **Phase B** (ticker ownership) kész → Dimension 2 (buckets) elérhető az IFDS számára

**Phase A önmagában is elég** egy minimális IFDS integrációhoz — csak a CAS-t konzumálni. De a **Phase B után** lesz igazán értékes: a ticker-level institutional layer megmondja, hogy egy adott szektoron belül **melyik constituent-ben** van a smart money flow.

## Tervezett változtatások

### 1. Új kliens: `src/ifds/data/mid_client.py`

```python
class MIDClient:
    """HTTP client for MID (Macro Intelligence Dashboard) API.
    
    Consumed in IFDS Phase 3 to replace self-computed sector rotation
    with MID ETF X-Ray CAS + institutional layer.
    """
    
    BASE_URL = "https://mid.ssh.services/api"
    # Or for same-machine: http://localhost:8000 if MID runs locally
    
    def get_etf_xray_snapshot(self) -> dict:
        """GET /api/etf-xray — full daily snapshot"""
    
    def get_institutional_pulse(self, etf: str) -> dict:
        """GET /api/etf-xray/institutional-pulse/{etf} — per-ETF full card"""
```

### 2. Phase 3 átalakítás

**Régi (`phase3_sector_rotation.py`):**
- Fetch 11 sector ETF OHLCV → compute momentum + RS → rank sectors
- Sector VETO: alulteljesítő szektorok kizárása
- Sector boost/penalty: scoring adjustment

**Új:**
- `MIDClient.get_etf_xray_snapshot()` → 11 sector state (OVERWEIGHT/ACCUMULATING/...)
- Sector VETO rules:
  - `UNDERWEIGHT` state → szektor kizárva
  - `DIVERGENT_SMART_SELL` (új, MID-ből) → szektor kizárva **még akkor is, ha a Flow CAS pozitív**
- Sector boost:
  - `CONVERGENT_BULL` (Flow + 13F egyezik) → +10 a score-hoz
  - `ACCUMULATING` önmagában → +5
  - `DIVERGENT_SMART_BUY` (retail sell-off de institutional buy) → +15 (contra-consensus reward)

### 3. Fallback

Ha a MID API nem elérhető (networkerror, 5xx, timeout):
- Fallback: jelenlegi lokális momentum számítás marad működőképes
- Telegram alert: "MID API unavailable, Phase 3 running in standalone mode"
- Nem blokkoló — a pipeline lefut, csak nem optimalis

### 4. Új metrika

A MID API response-ban kapott `consensus_state` kerüljön a Phase 3 outputba (`SectorRotationResult`) mint új mező — későbbi scoring integration és log-elemzés számára.

## Ami NEM változik

- Phase 1-2 és Phase 4-6 érintetlenek
- A sector sector-group-limitek (cyclical 5, defensive 4, ...) változatlanok
- A BMI regime + BMI momentum guard változatlan
- A jelenlegi scoring súlyok változatlanok

## Kockázat

| Kockázat | Mitigáció |
|----------|-----------|
| MID API nem elérhető | Fallback a jelenlegi logikára, Telegram alert |
| MID API response schema változik | Verzionált endpoint használata + schema validation a MIDClient-ben |
| Rate limit a MID backenden | A MID oldali 24h cache-e miatt nem kritikus |
| Network latency (ha remote) | 1-2 sec elfogadható Phase 3 számára — nem intraday kritikus |

## Siker kritériumok

- Phase 3 runtime <= jelenlegi (ne legyen regressziós lassulás)
- Minden sector VETO indoka logolva (OLD: "momentum < 0"; NEW: "CAS UNDERWEIGHT + DIVERGENT_SMART_SELL")
- W20+ paper trading: a CONVERGENT_BULL szektorokból választott tickerek átlag P&L vs. DIVERGENT-ből választottak P&L → mérhető különbség

## Timeline (várhatóan)

- **MID Phase A kész:** ~W18-W19 (~ápr 27-május 1)
- **MID Phase B kész:** ~W19-W20 (~május 4-8)
- **IFDS-oldali ez a BC:** W21 (~május 11-15) — legkorábban

Amikor a MID BC Phase B kész, **akkor tekintse át Tamás** ezt a taskot — addig csak tervezett állapotban áll.

## Referenciák

- MID BC: `/Users/safrtam/SSH-Services/mid/docs/planning/BC-etf-xray-institutional-13f-layer.md`
- MID meglévő ETF X-Ray engine: `/Users/safrtam/SSH-Services/mid/src/mid/engines/etf_xray/`
- IFDS jelenlegi Phase 3: `src/ifds/phases/phase3_sector_rotation.py`
